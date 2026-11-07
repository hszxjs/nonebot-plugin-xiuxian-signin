"""R-16：SQLite 后端专项——迁移幂等、admin 同步桥、事务回滚、备份、秘境语义。"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

import pytest

from nonebot_plugin_xiuxian_signin.mystic_dungeon import (
    DungeonPhase,
    DungeonRisk,
    MysticDungeonRun,
    MysticDungeonService,
    MysticTemplateCatalog,
)
from nonebot_plugin_xiuxian_signin.storage import (
    JsonStore,
    MysticRescueRequest,
    MysticRunConflict,
)
from nonebot_plugin_xiuxian_signin.storage.migration import (
    ensure_sqlite_backend,
    migrate_json_to_sqlite,
)
from nonebot_plugin_xiuxian_signin.storage.sqlite_store import SqliteStore

NOW = datetime(2026, 7, 16, 12, 0, 0)


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture(scope="module")
def catalog() -> MysticTemplateCatalog:
    return MysticTemplateCatalog.from_files()


def _seed_json_users(data_dir: Path, players: dict[str, dict]) -> None:
    (data_dir / "users.json").write_text(
        json.dumps(players, ensure_ascii=False), encoding="utf-8"
    )


def test_migration_imports_all_files_and_renames(data_dir: Path) -> None:
    _seed_json_users(
        data_dir,
        {
            "10001": {"user_id": "10001", "spirit_stones": 500},
            "10002": {"user_id": "10002", "spirit_stones": 20},
        },
    )
    (data_dir / "trade_offers.json").write_text(
        json.dumps(
            {
                "next_id": 3,
                "g1": {
                    "1": {"id": "1", "status": "open", "price": 10, "market": False},
                    "2": {"id": "2", "status": "taken", "price": 5, "market": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (data_dir / "mystic_dungeons.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "runs": {"run-1": {"run_id": "run-1"}},
                "encounters": {"enc-1": {"encounter_id": "enc-1"}},
                "active_by_user": {"10001": "run-1"},
                "private_routes": {"10001": {"run_id": "run-1", "group_id": "g1"}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    store = ensure_sqlite_backend(data_dir)

    # 字段逐条一致
    users = store.read_users_sync()
    assert users["10001"]["spirit_stones"] == 500
    assert users["10002"]["spirit_stones"] == 20
    offers = asyncio.run(store.list_trade_offers("g1"))
    assert {offer["id"] for offer in offers} == {"1"}
    # next_id 保留：下一张挂单 id=3
    created = asyncio.run(store.create_trade_offer("g1", "s", "卖家", "", {"name": "x"}, 1))
    assert created["id"] == "3"
    # 原文件改名保留，未删除
    assert (data_dir / "users.json.migrated.bak").is_file()
    assert (data_dir / "mystic_dungeons.json.migrated.bak").is_file()
    assert not (data_dir / "users.json").exists()


def test_migration_is_idempotent_when_db_already_has_users(data_dir: Path) -> None:
    _seed_json_users(data_dir, {"10001": {"user_id": "10001", "spirit_stones": 1}})
    store = ensure_sqlite_backend(data_dir)
    # 二次调用：库已有数据 → 不再迁移、不覆盖
    assert migrate_json_to_sqlite(data_dir, store) is False
    (data_dir / "users.json").write_text(
        json.dumps({"99999": {"user_id": "99999", "spirit_stones": 999}}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert migrate_json_to_sqlite(data_dir, store) is False
    assert "99999" not in store.read_users_sync()


def test_admin_sync_bridge_on_sqlite_backend(data_dir: Path) -> None:
    store = ensure_sqlite_backend(data_dir)
    # 与 admin.py 相同的调用形态（独立线程视角）
    users = store.read_users_sync()
    users["10001"] = {"user_id": "10001", "spirit_stones": 7, "custom_note": "后台写入"}

    def _merge(records: dict) -> dict:
        records["10001"] = {"user_id": "10001", "spirit_stones": 8, "custom_note": "第二次"}
        return records["10001"]

    result = store.update_users_sync(_merge, ["10001"])
    assert result["spirit_stones"] == 8
    assert store.read_users_sync()["10001"]["spirit_stones"] == 8
    assert store.read_group_members_sync() == {}
    snapshot = store.snapshot_users(reason="admin")
    assert snapshot is not None and snapshot.is_file()
    backup = store.backup_users_snapshot(data_dir / "backups")
    assert backup.is_file() and backup.suffix == ".db"


def test_cross_table_transaction_rolls_back_completely(data_dir: Path) -> None:
    """救援创建中途失败（灵石不足）→ users 与 rescue 两表都必须整体回滚。"""
    store = SqliteStore(data_dir)

    async def seed() -> None:
        record = await store.get_user("10001")
        record.spirit_stones = 5
        await store.save_user(record)

    asyncio.run(seed())

    request = MysticRescueRequest(
        request_id="r1",
        run_id="run-1",
        encounter_id="enc-1",
        group_id="g1",
        requester_id="10001",
        requester_name="玩家一",
        reward_stones=100,  # 超过余额 5
        monster_snapshot={},
        remaining_hp=10,
        deadline="2026-12-01T00:00",
    )
    with pytest.raises(ValueError):
        asyncio.run(store.create_rescue_request(request))

    assert asyncio.run(store.get_user("10001")).spirit_stones == 5
    assert asyncio.run(store.list_rescue_requests("g1")) == []


def _started_solo_run(catalog: MysticTemplateCatalog, run_id: str = "run-1") -> MysticDungeonRun:
    service = MysticDungeonService(catalog, now=lambda: NOW)
    run = service.create_lobby(run_id, "100", "leader", DungeonRisk.NORMAL)
    service.join_lobby(run, "member-2")
    service.set_ready(run, "leader", True)
    service.set_ready(run, "member-2", True)
    service.start_run(run, boss_realm_index=4, map_seed=7, content_seed=11)
    run.revision = 0
    return run


def test_run_revision_conflict_survives_sqlite_backend(
    data_dir: Path, catalog: MysticTemplateCatalog
) -> None:
    store = SqliteStore(data_dir)
    run = _started_solo_run(catalog)
    with store._txn() as connection:
        store._upsert(connection, "mystic_runs", "run_id", run.run_id, run.to_dict())

    def bump(item):
        item.revision_note = (getattr(item, "revision_note", "") or "") + "x"
        return item

    updated = asyncio.run(store.update_mystic_run(run.run_id, 0, bump))
    assert updated.revision == 1

    with pytest.raises(MysticRunConflict):
        asyncio.run(store.update_mystic_run(run.run_id, 0, bump))


def test_creating_run_recovery_on_sqlite_backend(data_dir: Path) -> None:
    """CREATING 预写恢复语义在 SQLite 后端保持（崩溃后读时修复）。"""
    store = SqliteStore(data_dir)
    service = MysticDungeonService(
        MysticTemplateCatalog.from_files(), now=lambda: NOW
    )
    lobby = service.create_lobby("run-2", "100", "leader", DungeonRisk.NORMAL)
    creating = service.prepare_run(lobby) if hasattr(service, "prepare_run") else lobby
    creating.phase = DungeonPhase.CREATING
    with store._txn() as connection:
        store._upsert(connection, "mystic_runs", "run_id", creating.run_id, creating.to_dict())
        # 领队没有 entry:<run_id> 结算记录 → 读时应被清理
        store._upsert(
            connection,
            "users",
            "user_id",
            "leader",
            {"user_id": "leader", "mystic_settlement_ids": []},
        )

    assert asyncio.run(store.get_mystic_run("run-2")) is None
    assert asyncio.run(store.find_active_mystic_run_id("leader")) is None


def test_both_backends_isolated_in_same_process(tmp_path: Path) -> None:
    """同进程两个后端各自独立（切换场景的隔离性）。"""
    json_store = JsonStore(tmp_path / "json-home")
    sqlite_store = SqliteStore(tmp_path / "sqlite-home")
    asyncio.run(json_store.get_user("1"))
    asyncio.run(sqlite_store.get_user("1"))
    assert (tmp_path / "sqlite-home" / "xiuxian.db").is_file()
    assert not (tmp_path / "json-home" / "xiuxian.db").exists()
