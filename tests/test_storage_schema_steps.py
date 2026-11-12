"""R-36：版本化存储结构步骤的幂等性与数据保全测试。

覆盖三点：
1. 结构步骤只清退役字段，身份（faction_identity / identity_sign_days）必须原样保留；
2. 步骤执行后记入 meta，重复调用不重复执行、不重复改写数据；
3. 已下线子系统的旧存档只改名归档，且归档本身幂等。
"""

from __future__ import annotations

import json
from pathlib import Path

from nonebot_plugin_xiuxian_signin.storage import db
from nonebot_plugin_xiuxian_signin.storage.migration import (
    _APPLIED_STEPS_META_KEY,
    apply_schema_steps,
    archive_retired_stores,
    ensure_sqlite_backend,
)
from nonebot_plugin_xiuxian_signin.storage.sqlite_store import SqliteStore

STEP_ID = "2026-11-r41-drop-last-tianji-mystic-date"

LEGACY_RECORD = {
    "user_id": "10001",
    "spirit_stones": 500,
    "faction_identity": "天机阁长老",
    "identity_sign_days": {"天机阁长老": 76},
    "last_tianji_mystic_date": "2026-11-01",
}


def _insert_raw(store: SqliteStore, user_id: str, payload: dict) -> None:
    """直接写库，模拟升级前的历史存档（此时 UserRecord 已无该字段）。"""
    store._db.execute(  # noqa: SLF001 - 测试需要构造历史数据
        "INSERT INTO users(user_id, data) VALUES(?, ?)",
        (user_id, json.dumps(payload, ensure_ascii=False)),
    )


def _read_raw(store: SqliteStore, user_id: str) -> dict:
    row = store._db.execute(  # noqa: SLF001
        "SELECT data FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    assert row is not None
    return json.loads(row["data"])


def test_schema_step_drops_retired_field_and_keeps_identity(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path)
    _insert_raw(store, "10001", dict(LEGACY_RECORD))

    executed = apply_schema_steps(store._db)

    assert executed == [STEP_ID]
    stored = _read_raw(store, "10001")
    assert "last_tianji_mystic_date" not in stored
    assert stored["faction_identity"] == "天机阁长老"
    assert stored["identity_sign_days"] == {"天机阁长老": 76}
    assert stored["spirit_stones"] == 500
    assert STEP_ID in json.loads(db.get_meta(store._db, _APPLIED_STEPS_META_KEY) or "[]")


def test_schema_step_is_idempotent(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path)
    _insert_raw(store, "10001", dict(LEGACY_RECORD))

    assert apply_schema_steps(store._db) == [STEP_ID]
    first = _read_raw(store, "10001")

    # 第二次启动：不得重复执行，也不得改写任何数据
    assert apply_schema_steps(store._db) == []
    assert _read_raw(store, "10001") == first


def test_schema_step_skips_players_without_retired_field(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path)
    _insert_raw(store, "10002", {"user_id": "10002", "spirit_stones": 7})

    assert apply_schema_steps(store._db) == [STEP_ID]
    assert _read_raw(store, "10002") == {"user_id": "10002", "spirit_stones": 7}


def test_schema_step_survives_corrupt_record(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path)
    _insert_raw(store, "10001", dict(LEGACY_RECORD))
    store._db.execute(  # noqa: SLF001
        "INSERT INTO users(user_id, data) VALUES(?, ?)", ("10003", "{not json")
    )

    # 单条损坏不得让整批步骤回滚（否则每次启动都会失败）
    assert apply_schema_steps(store._db) == [STEP_ID]
    assert "last_tianji_mystic_date" not in _read_raw(store, "10001")


def test_schema_steps_run_after_json_migration(tmp_path: Path) -> None:
    (tmp_path / "users.json").write_text(
        json.dumps({"10001": dict(LEGACY_RECORD)}, ensure_ascii=False), encoding="utf-8"
    )

    store = ensure_sqlite_backend(tmp_path)

    stored = _read_raw(store, "10001")
    assert "last_tianji_mystic_date" not in stored
    assert stored["faction_identity"] == "天机阁长老"
    # 旧 JSON 仍按约定改名保留，可整体回退
    assert (tmp_path / "users.json.migrated.bak").is_file()


def test_archive_retired_stores_is_idempotent(tmp_path: Path) -> None:
    legacy = tmp_path / "tianji_divination_hall.json"
    legacy.write_text(json.dumps({"g1": {"date": "2026-11-01"}}), encoding="utf-8")

    assert archive_retired_stores(tmp_path) == ["tianji_divination_hall.json"]
    archived = tmp_path / "tianji_divination_hall.json.archived.bak"
    assert archived.is_file()
    assert not legacy.exists()
    assert json.loads(archived.read_text(encoding="utf-8"))["g1"]["date"] == "2026-11-01"

    # 已归档过：保持原样，不覆盖、不报错
    assert archive_retired_stores(tmp_path) == []
    assert archived.is_file()
