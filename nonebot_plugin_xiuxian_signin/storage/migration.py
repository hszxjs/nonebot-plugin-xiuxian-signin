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
        "unique_artifacts": connection.execute("SELECT COUNT(*) FROM unique_artifacts").fetchone()[0],
        "trade_offers": connection.execute("SELECT COUNT(*) FROM trade_offers").fetchone()[0],
        "mystic_rescue": connection.execute("SELECT COUNT(*) FROM mystic_rescue").fetchone()[0],
        "mystic_runs": connection.execute("SELECT COUNT(*) FROM mystic_runs").fetchone()[0],
        "mystic_encounters": connection.execute("SELECT COUNT(*) FROM mystic_encounters").fetchone()[0],
        "mystic_active_by_user": connection.execute("SELECT COUNT(*) FROM mystic_active_by_user").fetchone()[0],
        "mystic_private_routes": connection.execute("SELECT COUNT(*) FROM mystic_private_routes").fetchone()[0],
    }


# --- 版本化结构步骤（R-36） --------------------------------------------------
#
# 阶段 3 的字段清理不再是「一次性脚本」：每个步骤有稳定 id，执行后记入 meta 的
# ``applied_schema_steps``，因此可以「现在清一部分、以后再追加一部分」，进程
# 重启或重复启动都不会重复执行，也不会要求第二次全量数据迁移。

_APPLIED_STEPS_META_KEY = "applied_schema_steps"


def _drop_last_tianji_mystic_date(connection) -> int:
    """R-41 前半：清掉已退役的 last_tianji_mystic_date 字段。

    该字段的写入方（坐堂分润 / 天机秘境冷却）已随 R-41 退役，不再有任何读写方，
    属纯历史残留；``faction_identity`` 与 ``identity_sign_days`` 一律不动。
    """
    rows = connection.execute("SELECT user_id, data FROM users").fetchall()
    changed = 0
    for row in rows:
        try:
            data = json.loads(row["data"])
        except json.JSONDecodeError:
            logger.warning(f"玩家 {row['user_id']} 存档损坏，跳过字段清理")
            continue
        if not isinstance(data, dict) or "last_tianji_mystic_date" not in data:
            continue
        data.pop("last_tianji_mystic_date", None)
        connection.execute(
            "UPDATE users SET data=? WHERE user_id=?",
            (json.dumps(data, ensure_ascii=False), row["user_id"]),
        )
        changed += 1
    return changed


_SCHEMA_STEPS: tuple[tuple[str, Any], ...] = (
    ("2026-11-r41-drop-last-tianji-mystic-date", _drop_last_tianji_mystic_date),
)

# 已下线子系统的旧存档：只改名归档，不删除，便于人工核查或回退。
_ARCHIVED_JSON_FILES = ("tianji_divination_hall.json",)


def _load_applied_steps(connection) -> set[str]:
    raw = db.get_meta(connection, _APPLIED_STEPS_META_KEY)
    if not raw:
        return set()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"{_APPLIED_STEPS_META_KEY} 内容不可解析，按未记录处理：{raw!r}")
        return set()
    return {str(item) for item in value} if isinstance(value, list) else set()


def apply_schema_steps(connection) -> list[str]:
    """执行尚未应用过的结构步骤；返回本次实际执行的 step id 列表。"""
    applied = _load_applied_steps(connection)
    pending = [(step_id, fn) for step_id, fn in _SCHEMA_STEPS if step_id not in applied]
    if not pending:
        return []
    executed: list[str] = []
    for step_id, fn in pending:
        with _txn_of(connection):
            changed = fn(connection)
            applied.add(step_id)
            db.set_meta(
                connection,
                _APPLIED_STEPS_META_KEY,
                json.dumps(sorted(applied), ensure_ascii=False),
            )
        executed.append(step_id)
        logger.info(f"存储结构步骤已执行：{step_id}（影响 {changed} 行）")
    return executed


def archive_retired_stores(data_dir: str | Path) -> list[str]:
    """把已下线子系统的旧存档改名为 ``*.archived.bak``（幂等，不删除数据）。"""
    data_dir = Path(data_dir)
    archived: list[str] = []
    for name in _ARCHIVED_JSON_FILES:
        source = data_dir / name
        if not source.is_file():
            continue
        target = source.with_name(source.name + ".archived.bak")
        if target.exists():
            logger.warning(f"归档目标已存在，保留原文件待人工处理：{source.name}")
            continue
        source.replace(target)
        archived.append(name)
    if archived:
        logger.info(f"已下线子系统的旧存档已归档（未删除）：{archived}")
    return archived


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
    """state.py 入口：建库 → 按需迁移 → 结构步骤 → 归档下线存档。"""
    store = SqliteStore(Path(data_dir))
    migrated = migrate_json_to_sqlite(data_dir, store)
    if migrated:
        logger.info("存储后端：SQLite（WAL），已完成 JSON 存档自动迁移")
    else:
        logger.info(f"存储后端：SQLite（WAL），库文件 {store.db_path}")
    apply_schema_steps(store._db)  # noqa: SLF001 - 同包协作
    archive_retired_stores(data_dir)
    return store
