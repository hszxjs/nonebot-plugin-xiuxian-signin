"""SQLite(WAL) 连接与 schema（重构计划 R-16）。

设计要点：

- **JSON-per-row**：玩家存档整行一个 JSON 文本列（``users(user_id, data)``）。
  单玩家读写 O(1)，``UserRecord.from_dict`` 解析逻辑零改动，存档结构演进
  不需要改表——定稿裁决的形态（31 人规模，后期要查列再演进）。
- **同步 sqlite3 而非 aiosqlite**：全库存储 API 本就是「async 方法里的同步
  IO」（原 JsonStore 同款模式），行级操作亚毫秒；同步连接让 49 个方法签名
  与 admin 线程同步桥原样复用。写入串行由调用方的 ``threading.RLock``
  （``_FILE_LOCK``）+ SQLite 自身锁共同保证。
- **WAL**：读写不互斥——机器人主循环写、admin 线程读可并发；
  ``synchronous=NORMAL``：WAL 提交不逐次 fsync（崩溃只丢最后事务，
  换取热路径吞吐；对游戏存档是正确取舍）。
- **mystic_dungeons.json 拆四表**：runs/encounters/active_by_user/
  private_routes；阶段 6（Q4=C）秘境重建前先直译平移，revision 语义保留。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_FILE_NAME = "xiuxian.db"
STORAGE_SCHEMA_VERSION = 1

_SCHEMA_STATEMENTS = (
    "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS chat_rank (group_id TEXT PRIMARY KEY, data TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS group_members (group_id TEXT PRIMARY KEY, data TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS unique_artifacts (item_name TEXT PRIMARY KEY, data TEXT NOT NULL)",
    """
    CREATE TABLE IF NOT EXISTS trade_offers (
        offer_id TEXT PRIMARY KEY,
        group_id TEXT NOT NULL,
        data TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_trade_offers_group ON trade_offers(group_id)",
    """
    CREATE TABLE IF NOT EXISTS mystic_rescue (
        request_id TEXT PRIMARY KEY,
        group_id TEXT NOT NULL,
        data TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_mystic_rescue_group ON mystic_rescue(group_id)",
    "CREATE TABLE IF NOT EXISTS mystic_runs (run_id TEXT PRIMARY KEY, data TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS mystic_encounters (encounter_id TEXT PRIMARY KEY, data TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS mystic_active_by_user (user_id TEXT PRIMARY KEY, run_id TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS mystic_private_routes (user_id TEXT PRIMARY KEY, data TEXT NOT NULL)",
)


def db_path(data_dir: str | Path) -> Path:
    return Path(data_dir) / DB_FILE_NAME


def connect(data_dir: str | Path) -> sqlite3.Connection:
    """打开（必要时创建）存储库并应用 PRAGMA 与 schema。

    ``isolation_level=None``（autocommit）：事务边界由调用方显式控制
    （``BEGIN IMMEDIATE`` / ``COMMIT``），避免隐式事务悬挂不提交。
    """
    path = db_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=OFF")
    for statement in _SCHEMA_STATEMENTS:
        connection.execute(statement)
    set_meta(connection, "storage_schema_version", str(STORAGE_SCHEMA_VERSION))
    return connection


def set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_meta(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row["value"])
