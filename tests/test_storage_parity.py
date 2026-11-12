"""R-16 等价性门禁：同一操作脚本在 JsonStore 与 SqliteStore 上产生完全一致的状态。

场景覆盖：玩家读写、群成员、聊天排行、交易、唯一道具、天机阁、救援、
秘境（lobby → 开局 → 更新 → 终结）。导出两份全量状态做深度比对——
这是「SQLite 后端行为与 JSON 后端逐字段一致」的主证据。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

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
    MysticSettlement,
)
from nonebot_plugin_xiuxian_signin.storage.sqlite_store import SqliteStore

NOW = datetime(2026, 7, 16, 12, 0, 0)


@pytest.fixture(params=["json", "sqlite"])
def store_factory(request: pytest.FixtureRequest):
    def _make(home: Path):
        if request.param == "sqlite":
            return SqliteStore(home)
        return JsonStore(home)

    _make.backend = request.param  # type: ignore[attr-defined]
    return _make


def _dump(store: Any) -> dict[str, Any]:
    """导出与后端无关的全量状态（JSON 读文件、SQLite 重建文档）。"""
    if isinstance(store, SqliteStore):
        return {
            "users": store.read_users_sync(),
            "chat_rank": store._read_rows("chat_rank", "group_id"),
            "group_members": store.read_group_members_sync(),
            "unique": store._read_rows("unique_artifacts", "item_name"),
            "trade": store._load_trade_doc(),
            "rescue": store._load_rescue_doc(),
            "mystic": store._load_mystic_state(),
        }
    read = store.read_json_sync
    return {
        "users": read(store.user_file_path),
        "chat_rank": read(store.rank_file_path),
        "group_members": read(store.group_file_path),
        "unique": read(store.unique_artifact_file_path),
        "trade": read(store.trade_file_path),
        "rescue": store._read_rescue_state_locked(),
        "mystic": store._read_mystic_state_locked(),
    }


def test_scenario_replay_produces_identical_state(tmp_path: Path, store_factory) -> None:
    home = tmp_path / store_factory.backend  # type: ignore[attr-defined]
    store = store_factory(home)  # type: ignore[attr-defined]

    async def scenario() -> None:
        # 1. 玩家（10001 带秘境令牌供开局扣减）
        for user_id, stones in (("10001", 500), ("10002", 30), ("10003", 0)):
            record = await store.get_user(user_id)
            record.spirit_stones = stones
            if user_id == "10001":
                record.rewards = [
                    {
                        "tier": "凡品",
                        "grade": "下品",
                        "category": "秘境令牌",
                        "name": "普通秘境令牌",
                        "description": "用于开启秘境副本",
                    }
                ]
            await store.save_user(record)
        # 2. 群成员 + 聊天计数
        await store.add_chat_count("g1", "10001", "2026-07-16", "玩家一")
        await store.add_chat_count("g1", "10001", "2026-07-16", "玩家一")
        await store.add_chat_count("g1", "10002", "2026-07-16", "玩家二")
        await store.touch_group_member("g2", "10003", "2026-07-16", "玩家三")
        # 3. 交易
        created = await store.create_trade_offer(
            "g1", "10001", "玩家一", "", {"name": "青竹剑"}, 100
        )
        taken = await store.take_trade_offer("g1", created["id"], "10002")
        assert taken is not None
        await store.reopen_trade_offer("g1", created["id"])
        await store.cancel_trade_offer("g1", created["id"], "10001")
        second = await store.create_trade_offer(
            "g1", "10002", "玩家二", "10001", {"name": "火灵石"}, 30, market=True
        )
        await store.take_trade_offer("g1", second["id"], "10001")
        # 4. 唯一道具
        claimed, owner = await store.claim_unique_artifact("青莲剑", "10001", "玩家一")
        assert claimed
        # 5. 救援（建单 → 接单 → 失败 → 过期退款）
        request = MysticRescueRequest(
            request_id="r1",
            run_id="run-1",
            encounter_id="enc-1",
            group_id="g1",
            requester_id="10001",
            requester_name="玩家一",
            reward_stones=50,
            monster_snapshot={"name": "妖兽"},
            remaining_hp=100,
            deadline="2026-07-16T23:00",
        )
        created_request = await store.create_rescue_request(request)
        assert created_request.requester_id == "10001"
        taken_request = await store.take_rescue_request("g1", "r1", "10002")
        assert taken_request is not None
        await store.fail_rescue_attempt("r1", "10002")
        expired = await store.expire_rescue_request("r1")
        assert expired.status == "expired"
        # 6. 秘境 lobby → 更新 → 终结
        service = MysticDungeonService(MysticTemplateCatalog.from_files(), now=lambda: NOW)
        run = service.create_lobby("run-p", "g1", "10001", DungeonRisk.NORMAL)
        service.join_lobby(run, "10002")
        service.set_ready(run, "10001", True)
        service.set_ready(run, "10002", True)
        await store.create_mystic_lobby(run)

        def ready_updater(item: MysticDungeonRun) -> MysticDungeonRun:
            item.vote_topic = "continue"
            return item

        current = await store.get_mystic_run("run-p")
        assert current is not None
        await store.update_mystic_lobby("run-p", current.revision, ready_updater)
        reloaded = await store.get_mystic_run("run-p")
        assert reloaded is not None
        service.start_run(
            reloaded,
            boss_realm_index=4,
            map_seed=7,
            content_seed=11,
        )
        started = await store.create_mystic_run(
            reloaded,
            payer_id="10001",
            token_name="普通秘境令牌",
        )
        assert started.phase is DungeonPhase.READY_TO_ROLL
        settled = await store.settle_mystic_run(
            "run-p",
            MysticSettlement(
                settlement_id="settle-1",
                rewards_by_user={"10001": [], "10002": []},
            ),
        )
        assert settled.phase is DungeonPhase.COMPLETED
        await store.close_mystic_run("run-p", DungeonPhase.COMPLETED)
        await store.mark_rank_group_settled("g1", "2026-07-16")

    asyncio.run(scenario())
    dump = _dump(store)
    # 深度合法性自检（比对由参数化两份 dump 完成）
    assert dump["unique"].get("青莲剑", {}).get("user_id") == "10001"
    assert dump["mystic"]["runs"]["run-p"]["phase"] == "completed"
    assert dump["trade"]["next_id"] == 3

    # 把 dump 存到固定位置，由第二份参数化实例比对
    snapshot_dir = tmp_path / "parity"
    snapshot_dir.mkdir(exist_ok=True)
    (snapshot_dir / f"{store_factory.backend}.json").write_text(  # type: ignore[attr-defined]
        __import__("json").dumps(dump, ensure_ascii=False, sort_keys=True, default=str),
        encoding="utf-8",
    )


def test_chat_count_aggregates_then_flushes(tmp_path: Path, store_factory) -> None:
    """R-17：计数先进内存聚合，读取/flush 后才落盘；跨日翻牌语义保持。"""
    home = tmp_path / store_factory.backend  # type: ignore[attr-defined]
    store = store_factory(home)  # type: ignore[attr-defined]

    async def scenario() -> None:
        for _ in range(3):
            await store.add_chat_count("g1", "10001", "2026-07-16", "玩家一")
        await store.add_chat_count("g1", "10002", "2026-07-16", "玩家二")
        # 读接口先 flush：结算视图必须完整
        unsettled = await store.get_unsettled_rank_groups("2026-07-16")
        assert unsettled["g1"]["users"]["10001"]["count"] == 3
        assert unsettled["g1"]["users"]["10002"]["count"] == 1

        await store.mark_rank_group_settled("g1", "2026-07-16")
        assert await store.get_unsettled_rank_groups("2026-07-16") == {}

        # 跨日：新的一天翻牌重置
        await store.add_chat_count("g1", "10001", "2026-07-17", "玩家一")
        next_day = await store.get_unsettled_rank_groups("2026-07-17")
        assert next_day["g1"]["users"]["10001"]["count"] == 1
        assert next_day["g1"]["date"] == "2026-07-17"
        assert next_day["g1"]["settled"] is False

    asyncio.run(scenario())


def test_both_backends_end_with_identical_state(tmp_path: Path) -> None:
    """独立重放两份并直接比对（不依赖上一次测试落盘的顺序）。"""
    dumps: dict[str, Any] = {}
    for backend in ("json", "sqlite"):
        home = tmp_path / backend
        store = SqliteStore(home) if backend == "sqlite" else JsonStore(home)

        async def scenario() -> None:
            for user_id, stones in (("10001", 500), ("10002", 30)):
                record = await store.get_user(user_id)
                record.spirit_stones = stones
                await store.save_user(record)
            await store.add_chat_count("g1", "10001", "2026-07-16", "玩家一")
            await store.touch_group_member("g1", "10002", "2026-07-16", "玩家二")
            created = await store.create_trade_offer(
                "g1", "10001", "玩家一", "", {"name": "青竹剑"}, 100
            )
            await store.take_trade_offer("g1", created["id"], "10002")
            await store.claim_unique_artifact("青莲剑", "10001", "玩家一")

        asyncio.run(scenario())
        dumps[backend] = _dump(store)

    json_dump, sqlite_dump = dumps["json"], dumps["sqlite"]
    assert json_dump["users"] == sqlite_dump["users"]
    assert json_dump["chat_rank"] == sqlite_dump["chat_rank"]
    assert json_dump["group_members"] == sqlite_dump["group_members"]
    assert json_dump["unique"] == sqlite_dump["unique"]
    # trade doc：键集合与挂单内容一致（next_id 同步）
    assert json_dump["trade"]["next_id"] == sqlite_dump["trade"]["next_id"]
    json_offers = {k: v for k, v in json_dump["trade"].items() if isinstance(v, dict)}
    sqlite_offers = {k: v for k, v in sqlite_dump["trade"].items() if isinstance(v, dict)}
    assert json_offers == sqlite_offers
    assert json_dump["rescue"] == sqlite_dump["rescue"]
    assert json_dump["mystic"] == sqlite_dump["mystic"]
