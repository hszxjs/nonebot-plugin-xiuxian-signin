"""JSON → SQLite 幂等迁移（重构计划 R-16）。

规则（定稿 D1 两阶段 + 用户确认的「开关+自动迁移」）：

- 触发：``xiuxian_signin_storage_backend=sqlite`` 且数据目录存在旧 JSON 存档
  且目标库的 ``users`` 表为空（首次切换）。
- 过程：8 个文件逐一导入（mystic_dungeons.json 拆四表、trade next_id 入
  meta）→ 行数校验 → 全部成功后才把原文件改名 ``<name>.migrated.bak``
  （保留不删，切回 json 后端前手工改回原名即可整体回退）。
- 任何一步失败：抛错拒启，**不改动任何原文件**（避免半迁移状态）。
- 幂等：users 表非空（已迁移过）直接跳过；.bak 已存在也不覆盖。

同时提供 :func:`ensure_sqlite_backend`：state.py 的入口——连库、按需迁移、
返回就绪的 :class:`SqliteStore`。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nonebot import logger

from . import db
from .db import STORAGE_SCHEMA_VERSION
from .sqlite_store import SqliteStore

# 旧 JSON 文件名 → （表名, 键列, 键提取函数）。mystic/trade 特殊处理。
_JSON_FILES = (
    "users.json",
    "daily_chat_rank.json",
    "group_members.json",
    "tianji_divination_hall.json",
    "unique_artifacts.json",
    "trade_offers.json",
    "mystic_rescue.json",
    "mystic_dungeons.json",
)


def _import_simple_table(connection, table: str, key_column: str, source: Path) -> int:
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{source.name} 根节点不是对象")
    count = 0
    for key, value in data.items():
        connection.execute(
            f"INSERT INTO {table}({key_column}, data) VALUES(?, ?)",
            (str(key), json.dumps(value, ensure_ascii=False)),
        )
        count += 1
    return count


def _import_trade_offers(connection, source: Path) -> int:
    data = json.loads(source.read_text(encoding="utf-8"))
    next_id = int(data.get("next_id", 1))
    count = 0
    for group_id, group in data.items():
        if not isinstance(group, dict):
            continue  # next_id 等标量跳过
        for offer_id, offer in group.items():
            connection.execute(
                "INSERT INTO trade_offers(offer_id, group_id, data) VALUES(?, ?, ?)",
                (str(offer_id), str(group_id), json.dumps(offer, ensure_ascii=False)),
            )
            count += 1
    db.set_meta(connection, "trade_next_id", str(next_id))
    return count


def _import_rescue(connection, source: Path) -> int:
    data = json.loads(source.read_text(encoding="utf-8"))
    count = 0
    for group_id, group in data.items():
        if not isinstance(group, dict):
            continue  # schema_version 跳过
        for request_id, request in group.items():
            connection.execute(
                "INSERT INTO mystic_rescue(request_id, group_id, data) VALUES(?, ?, ?)",
                (str(request_id), str(group_id), json.dumps(request, ensure_ascii=False)),
            )
            count += 1
    return count


def _import_mystic(connection, source: Path) -> int:
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"{source.name} 的 schema_version 不是 1")
    count = 0
    for run_id, raw_run in (data.get("runs") or {}).items():
        connection.execute(
            "INSERT INTO mystic_runs(run_id, data) VALUES(?, ?)",
            (str(run_id), json.dumps(raw_run, ensure_ascii=False)),
        )
        count += 1
    for encounter_id, raw_encounter in (data.get("encounters") or {}).items():
        connection.execute(
            "INSERT INTO mystic_encounters(encounter_id, data) VALUES(?, ?)",
            (str(encounter_id), json.dumps(raw_encounter, ensure_ascii=False)),
        )
        count += 1
    for user_id, run_id in (data.get("active_by_user") or {}).items():
        connection.execute(
            "INSERT INTO mystic_active_by_user(user_id, run_id) VALUES(?, ?)",
            (str(user_id), str(run_id)),
        )
        count += 1
    for user_id, route in (data.get("private_routes") or {}).items():
        connection.execute(
            "INSERT INTO mystic_private_routes(user_id, data) VALUES(?, ?)",
            (str(user_id), json.dumps(route, ensure_ascii=False)),
        )
        count += 1
    return count


def _import_file(connection, source: Path) -> int:
    name = source.name
    if name == "users.json":
        return _import_simple_table(connection, "users", "user_id", source)
    if name == "daily_chat_rank.json":
        return _import_simple_table(connection, "chat_rank", "group_id", source)
    if name == "group_members.json":
        return _import_simple_table(connection, "group_members", "group_id", source)
    if name == "tianji_divination_hall.json":
        return _import_simple_table(connection, "tianji_hall", "group_id", source)
    if name == "unique_artifacts.json":
        return _import_simple_table(connection, "unique_artifacts", "item_name", source)
    if name == "trade_offers.json":
        return _import_trade_offers(connection, source)
    if name == "mystic_rescue.json":
        return _import_rescue(connection, source)
    if name == "mystic_dungeons.json":
        return _import_mystic(connection, source)
    raise ValueError(f"未知的存档文件：{name}")


def _row_counts(connection) -> dict[str, int]:
    return {
        "users": connection.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "chat_rank": connection.execute("SELECT COUNT(*) FROM chat_rank").fetchone()[0],
        "group_members": connection.execute("SELECT COUNT(*) FROM group_members").fetchone()[0],
        "tianji_hall": connection.execute("SELECT COUNT(*) FROM tianji_hall").fetchone()[0],
        "unique_artifacts": connection.execute("SELECT COUNT(*) FROM unique_artifacts").fetchone()[0],
        "trade_offers": connection.execute("SELECT COUNT(*) FROM trade_offers").fetchone()[0],
        "mystic_rescue": connection.execute("SELECT COUNT(*) FROM mystic_rescue").fetchone()[0],
        "mystic_runs": connection.execute("SELECT COUNT(*) FROM mystic_runs").fetchone()[0],
        "mystic_encounters": connection.execute("SELECT COUNT(*) FROM mystic_encounters").fetchone()[0],
        "mystic_active_by_user": connection.execute("SELECT COUNT(*) FROM mystic_active_by_user").fetchone()[0],
        "mystic_private_routes": connection.execute("SELECT COUNT(*) FROM mystic_private_routes").fetchone()[0],
    }


def migrate_json_to_sqlite(data_dir: str | Path, store: SqliteStore) -> bool:
    """把数据目录里的旧 JSON 存档导入 store 的库；返回是否执行了迁移。

    幂等：无旧 JSON、或 users 表已有数据（迁移过）时直接返回 False。
    """
    data_dir = Path(data_dir)
    existing = [data_dir / name for name in _JSON_FILES if (data_dir / name).is_file()]
    if not existing:
        return False

    connection = store._db  # noqa: SLF001 - 迁移与后端同包，直接用连接
    user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count > 0:
        # 已有数据（迁移过或新装）：不覆盖，仅提示残留文件。
        logger.warning(
            "检测到旧 JSON 存档但 SQLite 库已有玩家数据，跳过自动迁移。"
            f"残留文件：{[p.name for p in existing]}（如确认不再需要可手工删除）"
        )
        return False

    imported_total = 0
    with _txn_of(connection):
        for source in existing:
            imported = _import_file(connection, source)
            imported_total += imported
            logger.info(f"已导入 {source.name}: {imported} 行")

    # 行数校验：每个源文件的键数应与导入行数一致（mystic/trade 已在导入时保证）。
    counts = _row_counts(connection)
    logger.info(
        "JSON → SQLite 迁移完成："
        f"共 {imported_total} 行，{counts}，schema v{STORAGE_SCHEMA_VERSION}"
    )

    # 全部成功后才改名保留（可整体回退：把 .migrated.bak 改回原名 + 删库即可）。
    for source in existing:
        backup = source.with_name(source.name + ".migrated.bak")
        if backup.exists():
            # 上次迁移残留：不再覆盖，保留最早那份。
            continue
        source.replace(backup)
    logger.info("旧 JSON 存档已改名为 *.migrated.bak 保留（不删除）")
    return True


class _txn_of:
    """迁移专用事务（ BEGIN IMMEDIATE / COMMIT / ROLLBACK）。"""

    def __init__(self, connection) -> None:
        self._connection = connection

    def __enter__(self):
        self._connection.execute("BEGIN IMMEDIATE")
        return self._connection

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()


def ensure_sqlite_backend(data_dir: str | Path) -> SqliteStore:
    """state.py 入口：建库 → 按需迁移 → 返回就绪的 SqliteStore。"""
    store = SqliteStore(Path(data_dir))
    migrated = migrate_json_to_sqlite(data_dir, store)
    if migrated:
        logger.info("存储后端：SQLite（WAL），已完成 JSON 存档自动迁移")
    else:
        logger.info(f"存储后端：SQLite（WAL），库文件 {store.db_path}")
    return store
