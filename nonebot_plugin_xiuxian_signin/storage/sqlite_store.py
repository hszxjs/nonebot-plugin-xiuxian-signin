"""SQLite(WAL) 存储后端（重构计划 R-16）。

与 :class:`~storage.JsonStore` 公共 API 完全一致的后端实现——调用点零改动，
``state.py`` 按配置二选一构造。差异只在持久化层：

- 玩家面是**行级**读写（``users`` 表整行 JSON），不再是全文件读改写；
- 跨文件写（救援、结算、开局扣令牌等）在**同一个事务**内提交，不再有
  「两个各自原子的文件写」之间的不一致窗口；
- 小表（trade/rescue/mystic）在事务内整表重写——表小、且原子性优先；
  ``users`` 是唯一的大表，严格走单行 UPSERT。

锁模型与 JsonStore 相同：异步方法持有 ``self._lock``（asyncio.Lock），所有
持久化又都经进程级 ``_FILE_LOCK``（RLock）——admin 独立线程的同步桥与主循
环天然互斥，sqlite 连接自身不再需要额外串行化。

快照/审计保持文件形态（snapshots/、audit.log）；``users.json`` 的写前快照
职责由 WAL + ``VACUUM INTO`` 备份接管。
"""

from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from nonebot import logger

from . import (
    ChatCountAggregatorMixin,
    DungeonEncounter,
    DungeonPhase,
    EncounterPhase,
    InsufficientSpiritStones,
    MysticDungeonRun,
    MysticEncounterConflict,
    MysticRescueRequest,
    MysticRunConflict,
    MysticRunNotFound,
    MysticSettlement,
    MysticStateCorrupt,
    MysticTokenMissingError,
    MYSTIC_TERMINAL_PHASES,
    UserRecord,
    _FILE_LOCK,
    apply_mystic_rewards,
    audit as _audit_log,
    consume_reward_by_names,
    normalize_mystic_settlement_ids,
    read_audit as _read_audit_log,
    sanitize_user_record_data,
)
from . import db
from .db import get_meta

_EMPTY_MYSTRIC_STATE = {
    "schema_version": 1,
    "runs": {},
    "encounters": {},
    "active_by_user": {},
    "private_routes": {},
}


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _loads(text: str) -> Any:
    return json.loads(text)


class SqliteStore(ChatCountAggregatorMixin):
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.user_file_path = self.data_dir / "users.json"
        self.rank_file_path = self.data_dir / "daily_chat_rank.json"
        self.group_file_path = self.data_dir / "group_members.json"
        self.unique_artifact_file_path = self.data_dir / "unique_artifacts.json"
        self.trade_file_path = self.data_dir / "trade_offers.json"
        self.rescue_file_path = self.data_dir / "mystic_rescue.json"
        self.mystic_file_path = self.data_dir / "mystic_dungeons.json"
        self.db_path = db.db_path(self.data_dir)
        self._db = db.connect(self.data_dir)
        self._lock = asyncio.Lock()
        self._init_chat_aggregator()

    def close(self) -> None:
        """关闭连接（WAL/-shm 文件随之清理）；仅停机钩子调用。"""
        with _FILE_LOCK:
            self._db.close()

    # --- 事务与行读写基座 ---------------------------------------------------
    @contextmanager
    def _txn(self):
        """进程锁 + 显式事务；异常整体回滚。"""
        with _FILE_LOCK:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db
            except BaseException:
                self._db.rollback()
                raise
            else:
                self._db.commit()

    def _read_rows(self, table: str, key_column: str) -> dict[str, Any]:
        rows = self._db.execute(f"SELECT {key_column}, data FROM {table}").fetchall()
        return {str(row[0]): _loads(row[1]) for row in rows}

    def _upsert(self, connection, table: str, key_column: str, key: str, value: Any) -> None:
        connection.execute(
            f"INSERT INTO {table}({key_column}, data) VALUES(?, ?) "
            f"ON CONFLICT({key_column}) DO UPDATE SET data=excluded.data",
            (key, _dumps(value)),
        )

    # --- 快照与审计（与 JsonStore 同款；config 快照仍是文件形态） ------------
    def snapshot_directory(self, path: Path) -> Path:
        return self.data_dir / "snapshots" / Path(path).name

    def list_snapshots(self, path: Path) -> list[Path]:
        directory = self.snapshot_directory(path)
        if not directory.is_dir():
            return []
        return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix == Path(path).suffix)

    def audit(self, event: str, **fields: Any) -> None:
        _audit_log(self.data_dir, event, **fields)

    def read_audit(self, limit: int = 200) -> list[dict[str, Any]]:
        return _read_audit_log(self.data_dir, limit=limit)

    # --- 玩家（行级读写） ----------------------------------------------------
    async def get_user(self, user_id: str) -> UserRecord:
        with _FILE_LOCK:
            row = self._db.execute(
                "SELECT data FROM users WHERE user_id=?", (str(user_id),)
            ).fetchone()
        if row is None:
            return UserRecord(user_id=str(user_id))
        return UserRecord.from_dict(_loads(row["data"]))

    async def save_user(self, record: UserRecord) -> None:
        payload = sanitize_user_record_data(record.to_dict())
        with self._txn() as connection:
            self._upsert(connection, "users", "user_id", record.user_id, payload)

    async def apply_to_user(self, user_id: str, updater) -> UserRecord:
        def _apply(data: dict[str, Any]) -> UserRecord:
            user_data = data.get(str(user_id))
            record = (
                UserRecord.from_dict(user_data)
                if isinstance(user_data, dict)
                else UserRecord(user_id=str(user_id))
            )
            updater(record)
            data[str(user_id)] = sanitize_user_record_data(record.to_dict())
            return record

        return self.update_users_sync(_apply, [str(user_id)])  # type: ignore[return-value]

    async def apply_to_users(self, user_ids: Iterable[str], updater) -> dict[str, UserRecord]:
        """一次事务内处理多个用户；updater 抛异常整批不落盘（语义同 JsonStore）。"""
        unique_ids = [str(uid) for uid in dict.fromkeys(str(uid) for uid in user_ids)]
        if not unique_ids:
            raise ValueError("apply_to_users requires at least one user id")

        def _apply(data: dict[str, Any]) -> dict[str, UserRecord]:
            records: dict[str, UserRecord] = {}
            for uid in unique_ids:
                user_data = data.get(uid)
                records[uid] = (
                    UserRecord.from_dict(user_data)
                    if isinstance(user_data, dict)
                    else UserRecord(user_id=uid)
                )
            updater(records)
            for uid in unique_ids:
                data[uid] = sanitize_user_record_data(records[uid].to_dict())
            return records

        return self.update_users_sync(_apply, unique_ids)  # type: ignore[return-value]

    async def transfer_spirit_stones(
        self,
        from_user_id: str,
        to_user_id: str,
        amount: int,
    ) -> dict[str, UserRecord]:
        amount = int(amount)
        if amount <= 0:
            raise ValueError("transfer amount must be positive")
        payer_id = str(from_user_id)
        payee_id = str(to_user_id)

        def _transfer(records: dict[str, UserRecord]) -> None:
            payer = records[payer_id]
            if payer.spirit_stones < amount:
                raise InsufficientSpiritStones(payer_id, amount, payer.spirit_stones)
            payer.spirit_stones -= amount
            records[payee_id].spirit_stones += amount

        return await self.apply_to_users([payer_id, payee_id], _transfer)

    async def get_group_user_records(self, group_id: str) -> list[dict[str, Any]]:
        with _FILE_LOCK:
            group_row = self._db.execute(
                "SELECT data FROM group_members WHERE group_id=?", (str(group_id),)
            ).fetchone()
            members: dict[str, Any] = {}
            if group_row is not None:
                group_data = _loads(group_row["data"])
                members = group_data.get("users") or {}
            users = self._read_rows("users", "user_id")
        result = []
        for user_id, member_data in members.items():
            if not isinstance(member_data, dict):
                continue
            record_data = users.get(str(user_id))
            record = (
                UserRecord.from_dict(record_data)
                if isinstance(record_data, dict)
                else UserRecord(user_id=str(user_id))
            )
            result.append(
                {
                    "user_id": str(user_id),
                    "nickname": member_data.get("nickname") or str(user_id),
                    "record": record,
                }
            )
        return result

    # --- 群成员 --------------------------------------------------------------
    async def touch_group_member(
        self,
        group_id: str,
        user_id: str,
        date_text: str,
        nickname: str = "",
    ) -> None:
        with self._txn() as connection:
            self._touch_group_member_txn(connection, group_id, user_id, date_text, nickname)

    def _touch_group_member_txn(
        self,
        connection,
        group_id: str,
        user_id: str,
        date_text: str,
        nickname: str = "",
    ) -> None:
        row = connection.execute(
            "SELECT data FROM group_members WHERE group_id=?", (str(group_id),)
        ).fetchone()
        group_data = _loads(row["data"]) if row is not None else {"users": {}}
        users = group_data.setdefault("users", {})
        user_data = users.setdefault(user_id, {"user_id": user_id})
        user_data["nickname"] = nickname or user_data.get("nickname") or user_id
        user_data["last_seen_date"] = date_text
        self._upsert(connection, "group_members", "group_id", str(group_id), group_data)

    async def get_group_member_nickname(self, group_id: str, user_id: str) -> str:
        with _FILE_LOCK:
            row = self._db.execute(
                "SELECT data FROM group_members WHERE group_id=?", (str(group_id),)
            ).fetchone()
        if row is None:
            return ""
        group_data = _loads(row["data"])
        users = group_data.get("users") or {}
        user_data = users.get(user_id)
        if not isinstance(user_data, dict):
            return ""
        nickname = str(user_data.get("nickname") or "")
        return "" if nickname == user_id else nickname

    # --- 聊天排行（R-17 内存聚合 + 批量落盘） --------------------------------
    async def add_chat_count(
        self,
        group_id: str,
        user_id: str,
        date_text: str,
        nickname: str,
    ) -> None:
        self._aggregate_chat_count(group_id, user_id, date_text, nickname)

    async def _apply_chat_count(
        self,
        group_id: str,
        user_id: str,
        date_text: str,
        nickname: str,
        count: int,
    ) -> None:
        with self._txn() as connection:
            row = connection.execute(
                "SELECT data FROM chat_rank WHERE group_id=?", (str(group_id),)
            ).fetchone()
            group_data = _loads(row["data"]) if row is not None else {}
            if group_data.get("date") != date_text:
                group_data = {"date": date_text, "settled": False, "users": {}}
            users = group_data.setdefault("users", {})
            user_data = users.setdefault(
                user_id,
                {"user_id": user_id, "nickname": nickname, "count": 0},
            )
            user_data["nickname"] = nickname or user_data.get("nickname") or user_id
            user_data["count"] = int(user_data.get("count", 0)) + count
            self._upsert(connection, "chat_rank", "group_id", str(group_id), group_data)
            self._touch_group_member_txn(connection, group_id, user_id, date_text, nickname)

    async def get_unsettled_rank_groups(self, date_text: str) -> dict[str, dict[str, Any]]:
        await self.flush_chat_counts()
        with _FILE_LOCK:
            rows = self._db.execute("SELECT group_id, data FROM chat_rank").fetchall()
        result = {}
        for row in rows:
            group_data = _loads(row["data"])
            if not isinstance(group_data, dict):
                continue
            if group_data.get("date") != date_text or group_data.get("settled"):
                continue
            result[str(row["group_id"])] = group_data
        return result

    async def mark_rank_group_settled(self, group_id: str, date_text: str) -> None:
        await self.flush_chat_counts()
        with self._txn() as connection:
            row = connection.execute(
                "SELECT data FROM chat_rank WHERE group_id=?", (str(group_id),)
            ).fetchone()
            if row is None:
                return
            group_data = _loads(row["data"])
            if isinstance(group_data, dict) and group_data.get("date") == date_text:
                group_data["settled"] = True
                self._upsert(connection, "chat_rank", "group_id", str(group_id), group_data)

    # --- 唯一道具 -------------------------------------------------------------
    async def get_unique_artifacts(self) -> dict[str, Any]:
        with _FILE_LOCK:
            return self._read_rows("unique_artifacts", "item_name")

    async def claim_unique_artifact(self, item_name: str, user_id: str, nickname: str = "") -> tuple[bool, dict[str, Any]]:
        with self._txn() as connection:
            row = connection.execute(
                "SELECT data FROM unique_artifacts WHERE item_name=?", (str(item_name),)
            ).fetchone()
            if row is not None:
                current = _loads(row["data"])
                return str(current.get("user_id")) == user_id, dict(current)
            owner = {"user_id": user_id, "nickname": nickname or user_id}
            self._upsert(connection, "unique_artifacts", "item_name", str(item_name), owner)
            return True, dict(owner)

    async def unique_owner_name(self, item_name: str) -> str:
        with _FILE_LOCK:
            row = self._db.execute(
                "SELECT data FROM unique_artifacts WHERE item_name=?", (str(item_name),)
            ).fetchone()
        if row is None:
            return ""
        owner = _loads(row["data"])
        if not isinstance(owner, dict):
            return ""
        return str(owner.get("nickname") or owner.get("user_id") or "")

    # --- 交易（整表重写实现跨行原子） -----------------------------------------
    def _load_trade_doc(self) -> dict[str, Any]:
        rows = self._db.execute("SELECT offer_id, group_id, data FROM trade_offers").fetchall()
        data: dict[str, Any] = {"next_id": int(get_meta(self._db, "trade_next_id") or 1)}
        for row in rows:
            group = data.setdefault(str(row["group_id"]), {})
            group[str(row["offer_id"])] = _loads(row["data"])
        return data

    def _save_trade_doc(self, connection, data: dict[str, Any]) -> None:
        connection.execute("DELETE FROM trade_offers")
        for group_id, group in data.items():
            if not isinstance(group, dict):
                continue
            for offer_id, offer in group.items():
                connection.execute(
                    "INSERT INTO trade_offers(offer_id, group_id, data) VALUES(?, ?, ?)",
                    (str(offer_id), str(group_id), _dumps(offer)),
                )
        db.set_meta(connection, "trade_next_id", str(int(data.get("next_id", 1))))

    async def create_trade_offer(
        self,
        group_id: str,
        seller_id: str,
        seller_name: str,
        target_id: str,
        item: dict[str, Any],
        price: int,
        market: bool = False,
    ) -> dict[str, Any]:
        with self._txn() as connection:
            data = self._load_trade_doc()
            offers = data.setdefault(str(group_id), {})
            next_id = int(data.get("next_id", 1))
            data["next_id"] = next_id + 1
            offer = {
                "id": str(next_id),
                "group_id": str(group_id),
                "seller_id": str(seller_id),
                "seller_name": seller_name or str(seller_id),
                "target_id": str(target_id or ""),
                "item": item,
                "price": int(price),
                "status": "open",
                "market": bool(market),
            }
            offers[str(next_id)] = offer
            self._save_trade_doc(connection, data)
            return dict(offer)

    async def list_trade_offers(self, group_id: str, market: bool | None = None) -> list[dict[str, Any]]:
        with _FILE_LOCK:
            data = self._load_trade_doc()
        group = data.get(str(group_id), {})
        if not isinstance(group, dict):
            return []
        offers = [dict(item) for item in group.values() if isinstance(item, dict) and item.get("status") == "open"]
        if market is None:
            return offers
        return [item for item in offers if bool(item.get("market")) is bool(market)]

    async def take_trade_offer(self, group_id: str, offer_id: str, buyer_id: str) -> dict[str, Any] | None:
        with self._txn() as connection:
            data = self._load_trade_doc()
            group = data.get(str(group_id), {})
            if not isinstance(group, dict):
                return None
            offer = group.get(str(offer_id))
            if not isinstance(offer, dict) or offer.get("status") != "open":
                return None
            target_id = str(offer.get("target_id") or "")
            if target_id and target_id != str(buyer_id):
                return None
            offer["status"] = "taken"
            offer["buyer_id"] = str(buyer_id)
            group[str(offer_id)] = offer
            data[str(group_id)] = group
            self._save_trade_doc(connection, data)
            return dict(offer)

    async def reopen_trade_offer(self, group_id: str, offer_id: str) -> bool:
        with self._txn() as connection:
            data = self._load_trade_doc()
            group = data.get(str(group_id), {})
            if not isinstance(group, dict):
                return False
            offer = group.get(str(offer_id))
            if not isinstance(offer, dict) or offer.get("status") != "taken":
                return False
            offer["status"] = "open"
            offer.pop("buyer_id", None)
            group[str(offer_id)] = offer
            data[str(group_id)] = group
            self._save_trade_doc(connection, data)
            return True

    async def cancel_trade_offer(self, group_id: str, offer_id: str, seller_id: str) -> dict[str, Any] | None:
        with self._txn() as connection:
            data = self._load_trade_doc()
            group = data.get(str(group_id), {})
            if not isinstance(group, dict):
                return None
            offer = group.get(str(offer_id))
            if not isinstance(offer, dict) or str(offer.get("seller_id")) != str(seller_id) or offer.get("status") != "open":
                return None
            offer["status"] = "cancelled"
            group[str(offer_id)] = offer
            data[str(group_id)] = group
            self._save_trade_doc(connection, data)
            return dict(offer)

    # --- 救援（users 行 + rescue 行同事务） -----------------------------------
    def _load_rescue_doc(self) -> dict[str, Any]:
        rows = self._db.execute("SELECT request_id, group_id, data FROM mystic_rescue").fetchall()
        data: dict[str, Any] = {"schema_version": 2}
        for row in rows:
            group = data.setdefault(str(row["group_id"]), {})
            group[str(row["request_id"])] = _loads(row["data"])
        return data

    def _save_rescue_doc(self, connection, data: dict[str, Any]) -> None:
        connection.execute("DELETE FROM mystic_rescue")
        for group_id, group in data.items():
            if not isinstance(group, dict):
                continue
            for request_id, request in group.items():
                connection.execute(
                    "INSERT INTO mystic_rescue(request_id, group_id, data) VALUES(?, ?, ?)",
                    (str(request_id), str(group_id), _dumps(request)),
                )

    def _rescue_from_doc(
        self,
        data: dict[str, Any],
        request_id: str,
    ) -> tuple[dict[str, Any], MysticRescueRequest]:
        for group_id, raw_group in data.items():
            if not isinstance(raw_group, dict):
                continue
            raw_request = raw_group.get(str(request_id))
            if not isinstance(raw_request, dict):
                continue
            request = MysticRescueRequest.from_dict(raw_request)
            if request.group_id != str(group_id):
                raise MysticStateCorrupt("mystic rescue group key does not match payload")
            return raw_group, request
        raise LookupError(f"mystic rescue request {request_id!r} was not found")

    async def create_rescue_request(
        self,
        request: MysticRescueRequest,
    ) -> MysticRescueRequest:
        with self._txn() as connection:
            data = self._load_rescue_doc()
            group = data.setdefault(request.group_id, {})
            if request.request_id in group:
                return MysticRescueRequest.from_dict(group[request.request_id])
            users = self._read_rows("users", "user_id")
            requester_data = users.get(request.requester_id)
            requester = (
                UserRecord.from_dict(requester_data)
                if isinstance(requester_data, dict)
                else UserRecord(user_id=request.requester_id)
            )
            if requester.spirit_stones < request.reward_stones:
                raise ValueError("requester does not have enough spirit stones")
            requester.spirit_stones -= request.reward_stones
            requester.mystic_settlement_ids = normalize_mystic_settlement_ids(
                [
                    *(requester.mystic_settlement_ids or []),
                    f"rescue:{request.request_id}:funded",
                ]
            )
            users[request.requester_id] = sanitize_user_record_data(requester.to_dict())
            group[request.request_id] = request.to_dict()
            self._upsert(connection, "users", "user_id", request.requester_id, users[request.requester_id])
            self._save_rescue_doc(connection, data)
            return MysticRescueRequest.from_dict(request.to_dict())

    async def list_rescue_requests(self, group_id: str) -> list[MysticRescueRequest]:
        with _FILE_LOCK:
            data = self._load_rescue_doc()
        group = data.get(str(group_id), {})
        if not isinstance(group, dict):
            return []
        return sorted(
            (
                MysticRescueRequest.from_dict(item)
                for item in group.values()
                if isinstance(item, dict) and item.get("status") == "open"
            ),
            key=lambda item: item.request_id,
        )

    async def get_rescue_request(self, request_id: str) -> MysticRescueRequest | None:
        with _FILE_LOCK:
            data = self._load_rescue_doc()
        try:
            _, request = self._rescue_from_doc(data, request_id)
        except LookupError:
            return None
        return request

    async def find_active_rescue_for_user(self, rescuer_id: str) -> MysticRescueRequest | None:
        with _FILE_LOCK:
            data = self._load_rescue_doc()
        matches: list[MysticRescueRequest] = []
        for raw_group in data.values():
            if not isinstance(raw_group, dict):
                continue
            for raw_request in raw_group.values():
                if not isinstance(raw_request, dict):
                    continue
                request = MysticRescueRequest.from_dict(raw_request)
                if request.status == "taken" and request.active_rescuer_id == rescuer_id:
                    matches.append(request)
        return min(matches, key=lambda item: item.request_id) if matches else None

    async def take_rescue_request(
        self,
        group_id: str,
        request_id: str,
        rescuer_id: str,
    ) -> MysticRescueRequest | None:
        with self._txn() as connection:
            data = self._load_rescue_doc()
            group = data.get(str(group_id), {})
            if not isinstance(group, dict):
                return None
            raw_request = group.get(str(request_id))
            if not isinstance(raw_request, dict):
                return None
            request = MysticRescueRequest.from_dict(raw_request)
            if (
                request.status != "open"
                or request.requester_id == str(rescuer_id)
                or str(rescuer_id) in request.attempted_rescuer_ids
            ):
                return None
            request.status = "taken"
            request.active_rescuer_id = str(rescuer_id)
            group[str(request_id)] = request.to_dict()
            data[str(group_id)] = group
            self._save_rescue_doc(connection, data)
            return MysticRescueRequest.from_dict(request.to_dict())

    async def fail_rescue_attempt(self, request_id: str, rescuer_id: str) -> MysticRescueRequest:
        with self._txn() as connection:
            data = self._load_rescue_doc()
            group, request = self._rescue_from_doc(data, request_id)
            if request.status != "taken" or request.active_rescuer_id != rescuer_id:
                raise ValueError("rescuer does not own the active rescue attempt")
            request.attempted_rescuer_ids.append(rescuer_id)
            request.attempted_rescuer_ids = list(dict.fromkeys(request.attempted_rescuer_ids))
            request.active_rescuer_id = None
            request.status = "open"
            group[request_id] = request.to_dict()
            self._save_rescue_doc(connection, data)
            return MysticRescueRequest.from_dict(request.to_dict())

    async def complete_rescue_request(self, request_id: str, rescuer_id: str) -> MysticRescueRequest:
        with self._txn() as connection:
            data = self._load_rescue_doc()
            group, request = self._rescue_from_doc(data, request_id)
            settlement_id = f"rescue:{request_id}:complete"
            state, users = self._load_mystic_state_with_recovery(connection)
            rescuer_data = users.get(rescuer_id)
            rescuer = (
                UserRecord.from_dict(rescuer_data)
                if isinstance(rescuer_data, dict)
                else UserRecord(user_id=rescuer_id)
            )
            already_paid = settlement_id in (rescuer.mystic_settlement_ids or [])
            if request.status == "completed":
                if not already_paid:
                    raise MysticStateCorrupt("completed rescue is missing its settlement")
                return request
            if request.status != "taken" or request.active_rescuer_id != rescuer_id:
                raise ValueError("rescuer does not own the active rescue attempt")
            if not already_paid:
                rescuer.spirit_stones += request.reward_stones
                rescuer.mystic_settlement_ids = normalize_mystic_settlement_ids(
                    [*(rescuer.mystic_settlement_ids or []), settlement_id]
                )
                users[rescuer_id] = sanitize_user_record_data(rescuer.to_dict())
            runs = state["runs"]
            run = self._run_from_doc(runs, request.run_id)
            if run.current_node_id not in run.cleared_node_ids:
                run.cleared_node_ids.append(run.current_node_id)
            run.active_encounter_id = None
            run.phase = DungeonPhase.READY_TO_ROLL
            run.revision += 1
            runs[run.run_id] = run.to_dict()
            request.status = "completed"
            request.active_rescuer_id = rescuer_id
            group[request_id] = request.to_dict()
            self._upsert(connection, "users", "user_id", rescuer_id, users[rescuer_id])
            self._save_mystic_state(connection, state)
            self._save_rescue_doc(connection, data)
            return MysticRescueRequest.from_dict(request.to_dict())

    async def expire_rescue_request(self, request_id: str) -> MysticRescueRequest:
        with self._txn() as connection:
            data = self._load_rescue_doc()
            group, request = self._rescue_from_doc(data, request_id)
            if request.status == "completed":
                return request
            users = self._read_rows("users", "user_id")
            requester_data = users.get(request.requester_id)
            requester = (
                UserRecord.from_dict(requester_data)
                if isinstance(requester_data, dict)
                else UserRecord(user_id=request.requester_id)
            )
            refund_id = f"rescue:{request_id}:refund"
            if refund_id not in (requester.mystic_settlement_ids or []):
                requester.spirit_stones += request.reward_stones
                requester.mystic_settlement_ids = normalize_mystic_settlement_ids(
                    [*(requester.mystic_settlement_ids or []), refund_id]
                )
                users[request.requester_id] = sanitize_user_record_data(requester.to_dict())
                self._upsert(
                    connection, "users", "user_id", request.requester_id, users[request.requester_id]
                )
            request.status = "expired"
            request.active_rescuer_id = None
            group[request_id] = request.to_dict()
            self._save_rescue_doc(connection, data)
            return MysticRescueRequest.from_dict(request.to_dict())

    # --- 秘境（四表直译；阶段 6 Q4=C 重建前的过渡实现） ------------------------
    def _load_mystic_state(self) -> dict[str, Any]:
        state = {
            "schema_version": 1,
            "runs": self._read_rows("mystic_runs", "run_id"),
            "encounters": self._read_rows("mystic_encounters", "encounter_id"),
            "active_by_user": {
                user_id: run_id
                for user_id, run_id in self._db.execute(
                    "SELECT user_id, run_id FROM mystic_active_by_user"
                ).fetchall()
            },
            "private_routes": self._read_rows("mystic_private_routes", "user_id"),
        }
        if get_meta(self._db, "mystic_schema_version") not in (None, "1"):
            raise MysticStateCorrupt("unsupported mystic dungeon state schema")
        return state

    def _save_mystic_state(self, connection, state: dict[str, Any]) -> None:
        connection.execute("DELETE FROM mystic_runs")
        connection.execute("DELETE FROM mystic_encounters")
        connection.execute("DELETE FROM mystic_active_by_user")
        connection.execute("DELETE FROM mystic_private_routes")
        for run_id, raw_run in state["runs"].items():
            connection.execute(
                "INSERT INTO mystic_runs(run_id, data) VALUES(?, ?)",
                (str(run_id), _dumps(raw_run)),
            )
        for encounter_id, raw_encounter in state["encounters"].items():
            connection.execute(
                "INSERT INTO mystic_encounters(encounter_id, data) VALUES(?, ?)",
                (str(encounter_id), _dumps(raw_encounter)),
            )
        for user_id, run_id in state["active_by_user"].items():
            connection.execute(
                "INSERT INTO mystic_active_by_user(user_id, run_id) VALUES(?, ?)",
                (str(user_id), str(run_id)),
            )
        for user_id, route in state["private_routes"].items():
            connection.execute(
                "INSERT INTO mystic_private_routes(user_id, data) VALUES(?, ?)",
                (str(user_id), _dumps(route)),
            )
        db.set_meta(connection, "mystic_schema_version", "1")

    def _load_mystic_state_with_recovery(self, connection) -> tuple[dict[str, Any], dict[str, Any]]:
        state = self._load_mystic_state()
        users = self._read_rows("users", "user_id")
        if self._recover_creating_runs_locked(state, users):

            def apply(c) -> None:
                self._save_users_rows(c, users)
                self._save_mystic_state(c, state)

            if connection.in_transaction:
                apply(connection)
            else:
                # 只读路径上的惰性恢复：单独开一个事务保证原子。
                with self._txn() as txn_connection:
                    apply(txn_connection)
        return state, users

    def _save_users_rows(self, connection, users: dict[str, Any]) -> None:
        for user_id, user_data in users.items():
            self._upsert(connection, "users", "user_id", str(user_id), user_data)

    def _recover_creating_runs_locked(
        self,
        state: dict[str, Any],
        users: dict[str, Any],
    ) -> bool:
        changed = False
        runs = state["runs"]
        active_by_user = state["active_by_user"]
        routes = state["private_routes"]
        for run_id, raw_run in list(runs.items()):
            run = self._decode_mystic_run(raw_run, run_id)
            if run.phase is not DungeonPhase.CREATING:
                continue
            leader_data = users.get(run.leader_id)
            leader = (
                UserRecord.from_dict(leader_data)
                if isinstance(leader_data, dict)
                else UserRecord(user_id=run.leader_id)
            )
            if f"entry:{run_id}" not in (leader.mystic_settlement_ids or []):
                runs.pop(run_id, None)
                for user_id in run.member_ids:
                    if active_by_user.get(user_id) == run_id:
                        active_by_user.pop(user_id, None)
                    route = routes.get(user_id)
                    if isinstance(route, dict) and route.get("run_id") == run_id:
                        routes.pop(user_id, None)
                    user_data = users.get(user_id)
                    if isinstance(user_data, dict):
                        record = UserRecord.from_dict(user_data)
                        if record.active_mystic_run_id == run_id:
                            record.active_mystic_run_id = None
                            users[user_id] = sanitize_user_record_data(record.to_dict())
                changed = True
                continue

            run.phase = DungeonPhase.READY_TO_ROLL
            runs[run_id] = run.to_dict()
            for user_id in run.member_ids:
                active_by_user[user_id] = run_id
                user_data = users.get(user_id)
                record = (
                    UserRecord.from_dict(user_data)
                    if isinstance(user_data, dict)
                    else UserRecord(user_id=user_id)
                )
                record.active_mystic_run_id = run_id
                users[user_id] = sanitize_user_record_data(record.to_dict())
            changed = True
        return changed

    def _decode_mystic_run(self, raw_run: Any, run_id: str) -> MysticDungeonRun:
        if not isinstance(raw_run, dict):
            raise MysticStateCorrupt(f"mystic run {run_id!r} must be an object")
        try:
            run = MysticDungeonRun.from_dict(raw_run)
        except (TypeError, ValueError) as exc:
            raise MysticStateCorrupt(f"mystic run {run_id!r} is corrupt") from exc
        if run.run_id != run_id:
            raise MysticStateCorrupt(f"mystic run key {run_id!r} does not match its payload")
        return run

    def _run_from_doc(self, runs: dict[str, Any], run_id: str) -> MysticDungeonRun:
        raw_run = runs.get(str(run_id))
        if raw_run is None:
            raise MysticRunNotFound(f"mystic run {run_id!r} was not found")
        return self._decode_mystic_run(raw_run, str(run_id))

    def _decode_mystic_encounter(self, raw_encounter: Any, encounter_id: str) -> Any:
        if not isinstance(raw_encounter, dict):
            raise MysticStateCorrupt(f"mystic encounter {encounter_id!r} must be an object")
        try:
            encounter = DungeonEncounter.from_dict(raw_encounter)
        except (TypeError, ValueError) as exc:
            raise MysticStateCorrupt(f"mystic encounter {encounter_id!r} is corrupt") from exc
        if encounter.encounter_id != encounter_id:
            raise MysticStateCorrupt(f"mystic encounter key {encounter_id!r} does not match its payload")
        return encounter

    def _encounter_from_doc(self, encounters: dict[str, Any], encounter_id: str) -> Any:
        raw_encounter = encounters.get(str(encounter_id))
        if raw_encounter is None:
            raise LookupError(f"mystic encounter {encounter_id!r} was not found")
        return self._decode_mystic_encounter(raw_encounter, str(encounter_id))

    def _cleanup_mystic_run(
        self,
        state: dict[str, Any],
        users: dict[str, Any],
        run: MysticDungeonRun,
    ) -> bool:
        changed = False
        active_by_user = state["active_by_user"]
        routes = state["private_routes"]
        for user_id in run.member_ids:
            if active_by_user.get(user_id) == run.run_id:
                active_by_user.pop(user_id, None)
                changed = True
            route = routes.get(user_id)
            if isinstance(route, dict) and route.get("run_id") == run.run_id:
                routes.pop(user_id, None)
                changed = True
            user_data = users.get(user_id)
            if not isinstance(user_data, dict):
                continue
            record = UserRecord.from_dict(user_data)
            if record.active_mystic_run_id == run.run_id:
                record.active_mystic_run_id = None
                users[user_id] = sanitize_user_record_data(record.to_dict())
                changed = True
        return changed

    async def get_mystic_run(self, run_id: str) -> MysticDungeonRun | None:
        with _FILE_LOCK:
            state, _ = self._load_mystic_state_with_recovery(self._db)
            raw_run = state["runs"].get(str(run_id))
            if raw_run is None:
                return None
            return self._decode_mystic_run(raw_run, str(run_id))

    async def list_active_mystic_runs(self) -> list[MysticDungeonRun]:
        with _FILE_LOCK:
            state, _ = self._load_mystic_state_with_recovery(self._db)
        active_runs = []
        for run_id, raw_run in state["runs"].items():
            run = self._decode_mystic_run(raw_run, run_id)
            if run.phase not in MYSTIC_TERMINAL_PHASES:
                active_runs.append(run)
        return sorted(active_runs, key=lambda item: item.run_id)

    async def find_active_mystic_run_id(self, user_id: str) -> str | None:
        with _FILE_LOCK:
            state, _ = self._load_mystic_state_with_recovery(self._db)
        run_id = state["active_by_user"].get(str(user_id))
        return str(run_id) if run_id else None

    async def create_mystic_lobby(self, run: MysticDungeonRun) -> MysticDungeonRun:
        with self._txn() as connection:
            if run.mode.value != "team" or run.phase is not DungeonPhase.LOBBY:
                raise ValueError("mystic lobby must be a team run in lobby phase")
            state, users = self._load_mystic_state_with_recovery(connection)
            runs = state["runs"]
            active_by_user = state["active_by_user"]
            if run.run_id in runs:
                raise ValueError(f"mystic run {run.run_id!r} already exists")
            for user_id in run.member_ids:
                active_run_id = active_by_user.get(user_id)
                user_data = users.get(user_id)
                record = (
                    UserRecord.from_dict(user_data)
                    if isinstance(user_data, dict)
                    else UserRecord(user_id=user_id)
                )
                if active_run_id or record.active_mystic_run_id:
                    raise ValueError(f"user {user_id!r} already has an active mystic run")
            saved = MysticDungeonRun.from_dict(run.to_dict())
            runs[saved.run_id] = saved.to_dict()
            for user_id in saved.member_ids:
                active_by_user[user_id] = saved.run_id
                user_data = users.get(user_id)
                record = (
                    UserRecord.from_dict(user_data)
                    if isinstance(user_data, dict)
                    else UserRecord(user_id=user_id)
                )
                record.active_mystic_run_id = saved.run_id
                users[user_id] = sanitize_user_record_data(record.to_dict())
            self._save_users_rows(connection, users)
            self._save_mystic_state(connection, state)
            return saved

    async def create_mystic_run(
        self,
        run: MysticDungeonRun,
        payer_id: str,
        token_name: str,
    ) -> MysticDungeonRun:
        with self._txn() as connection:
            if run.phase is not DungeonPhase.READY_TO_ROLL:
                raise ValueError("mystic run must be ready_to_roll before persistence")
            if payer_id != run.leader_id:
                raise ValueError("only the dungeon leader can pay the entry token")
            if not token_name:
                raise ValueError("mystic token name must not be empty")

            state, users = self._load_mystic_state_with_recovery(connection)
            runs = state["runs"]
            active_by_user = state["active_by_user"]
            existing_lobby_payload = runs.get(run.run_id)
            existing_lobby = None
            if existing_lobby_payload is not None:
                existing_lobby = self._decode_mystic_run(existing_lobby_payload, run.run_id)
                if existing_lobby.phase is not DungeonPhase.LOBBY:
                    raise ValueError(f"mystic run {run.run_id!r} already exists")
                if existing_lobby.mode is not run.mode or existing_lobby.member_ids != run.member_ids:
                    raise ValueError("mystic lobby changed before start")
                if existing_lobby.source_group_id != run.source_group_id:
                    raise ValueError("mystic lobby group changed before start")
                if run.revision != existing_lobby.revision + 1:
                    raise MysticRunConflict(f"mystic lobby {run.run_id!r} changed before start")
            for user_id in run.member_ids:
                active_run_id = active_by_user.get(user_id)
                user_data = users.get(user_id)
                record = (
                    UserRecord.from_dict(user_data)
                    if isinstance(user_data, dict)
                    else UserRecord(user_id=user_id)
                )
                if (
                    (active_run_id and active_run_id != run.run_id)
                    or (
                        record.active_mystic_run_id
                        and record.active_mystic_run_id != run.run_id
                    )
                ):
                    raise ValueError(f"user {user_id!r} already has an active mystic run")

            payer_data = users.get(payer_id)
            payer = (
                UserRecord.from_dict(payer_data)
                if isinstance(payer_data, dict)
                else UserRecord(user_id=payer_id)
            )
            if consume_reward_by_names(payer, [token_name]) is None:
                raise MysticTokenMissingError(run.risk, token_name)

            entry_id = f"entry:{run.run_id}"
            payer.mystic_settlement_ids = normalize_mystic_settlement_ids(
                [*(payer.mystic_settlement_ids or []), entry_id]
            )
            for user_id in run.member_ids:
                if user_id == payer_id:
                    record = payer
                else:
                    user_data = users.get(user_id)
                    record = (
                        UserRecord.from_dict(user_data)
                        if isinstance(user_data, dict)
                        else UserRecord(user_id=user_id)
                    )
                record.active_mystic_run_id = run.run_id
                users[user_id] = sanitize_user_record_data(record.to_dict())
                active_by_user[user_id] = run.run_id

            saved = MysticDungeonRun.from_dict(run.to_dict())
            runs[run.run_id] = saved.to_dict()
            self._save_users_rows(connection, users)
            self._save_mystic_state(connection, state)
            return saved

    async def update_mystic_lobby(
        self,
        run_id: str,
        expected_revision: int,
        updater: Callable[[MysticDungeonRun], MysticDungeonRun | None],
    ) -> MysticDungeonRun:
        with self._txn() as connection:
            state, users = self._load_mystic_state_with_recovery(connection)
            runs = state["runs"]
            active_by_user = state["active_by_user"]
            current = self._run_from_doc(runs, run_id)
            if current.phase is not DungeonPhase.LOBBY:
                raise ValueError("mystic lobby is no longer open")
            if current.revision != expected_revision:
                raise MysticRunConflict(
                    f"mystic lobby {run_id!r} revision is {current.revision}, expected {expected_revision}"
                )
            candidate = updater(current)
            updated = current if candidate is None else candidate
            if not isinstance(updated, MysticDungeonRun):
                raise TypeError("mystic lobby updater must return MysticDungeonRun or None")
            if updated.run_id != run_id or updated.source_group_id != current.source_group_id:
                raise ValueError("mystic lobby identity cannot change")
            if updated.mode.value != "team" or updated.phase is not DungeonPhase.LOBBY:
                raise ValueError("mystic lobby updater must keep the lobby phase")
            original_member_ids = set(current.member_ids)
            updated_member_ids = set(updated.member_ids)
            for user_id in updated_member_ids - original_member_ids:
                active_run_id = active_by_user.get(user_id)
                user_data = users.get(user_id)
                record = (
                    UserRecord.from_dict(user_data)
                    if isinstance(user_data, dict)
                    else UserRecord(user_id=user_id)
                )
                if (
                    (active_run_id and active_run_id != run_id)
                    or (
                        record.active_mystic_run_id
                        and record.active_mystic_run_id != run_id
                    )
                ):
                    raise ValueError(f"user {user_id!r} already has an active mystic run")
            for user_id in original_member_ids - updated_member_ids:
                if active_by_user.get(user_id) == run_id:
                    active_by_user.pop(user_id, None)
                user_data = users.get(user_id)
                if isinstance(user_data, dict):
                    record = UserRecord.from_dict(user_data)
                    if record.active_mystic_run_id == run_id:
                        record.active_mystic_run_id = None
                        users[user_id] = sanitize_user_record_data(record.to_dict())
            updated.revision = expected_revision + 1
            validated = MysticDungeonRun.from_dict(updated.to_dict())
            runs[run_id] = validated.to_dict()
            for user_id in validated.member_ids:
                active_by_user[user_id] = run_id
                user_data = users.get(user_id)
                record = (
                    UserRecord.from_dict(user_data)
                    if isinstance(user_data, dict)
                    else UserRecord(user_id=user_id)
                )
                record.active_mystic_run_id = run_id
                users[user_id] = sanitize_user_record_data(record.to_dict())
            self._save_users_rows(connection, users)
            self._save_mystic_state(connection, state)
            return validated

    async def update_mystic_run(
        self,
        run_id: str,
        expected_revision: int,
        updater: Callable[[MysticDungeonRun], MysticDungeonRun | None],
    ) -> MysticDungeonRun:
        with self._txn() as connection:
            state, _ = self._load_mystic_state_with_recovery(connection)
            runs = state["runs"]
            run = self._run_from_doc(runs, run_id)
            if run.revision != expected_revision:
                raise MysticRunConflict(
                    f"mystic run {run_id!r} revision is {run.revision}, expected {expected_revision}"
                )
            original_member_ids = run.member_ids
            candidate = updater(run)
            updated = run if candidate is None else candidate
            if not isinstance(updated, MysticDungeonRun):
                raise TypeError("mystic run updater must return MysticDungeonRun or None")
            if updated.run_id != run_id:
                raise ValueError("mystic run updater cannot change run_id")
            if updated.member_ids != original_member_ids:
                raise ValueError("mystic run updater cannot change the fixed roster")
            updated.revision = expected_revision + 1
            validated = MysticDungeonRun.from_dict(updated.to_dict())
            runs[run_id] = validated.to_dict()
            self._save_mystic_state(connection, state)
            return validated

    async def bind_mystic_private_routes(self, run: MysticDungeonRun) -> None:
        with self._txn() as connection:
            state, _ = self._load_mystic_state_with_recovery(connection)
            persisted = self._run_from_doc(state["runs"], run.run_id)
            if persisted.phase in MYSTIC_TERMINAL_PHASES:
                raise ValueError("cannot bind private routes for a terminal mystic run")
            routes = state["private_routes"]
            for user_id in persisted.member_ids:
                routes[user_id] = {
                    "run_id": persisted.run_id,
                    "group_id": persisted.source_group_id,
                }
            self._save_mystic_state(connection, state)

    async def resolve_mystic_private_route(self, user_id: str) -> tuple[str, str] | None:
        with _FILE_LOCK:
            state, _ = self._load_mystic_state_with_recovery(self._db)
        raw_route = state["private_routes"].get(str(user_id))
        if raw_route is None:
            return None
        if not isinstance(raw_route, dict):
            raise MysticStateCorrupt("mystic private route must be an object")
        run_id = str(raw_route.get("run_id") or "")
        group_id = str(raw_route.get("group_id") or "")
        if not run_id or not group_id:
            raise MysticStateCorrupt("mystic private route is missing run_id or group_id")
        return run_id, group_id

    async def close_mystic_run(self, run_id: str, terminal_phase: DungeonPhase) -> MysticDungeonRun:
        with self._txn() as connection:
            try:
                phase = DungeonPhase(terminal_phase)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"unknown terminal mystic phase {terminal_phase!r}") from exc
            if phase not in MYSTIC_TERMINAL_PHASES:
                raise ValueError("close_mystic_run requires a terminal phase")
            state, users = self._load_mystic_state_with_recovery(connection)
            runs = state["runs"]
            run = self._run_from_doc(runs, run_id)
            if run.phase is not phase:
                run.phase = phase
                run.revision += 1
            if phase is not DungeonPhase.COMPLETED:
                run.temporary_rewards_by_user = {}
            run.active_vote = None
            run.active_encounter_id = None
            self._cleanup_mystic_run(state, users, run)
            runs[run_id] = run.to_dict()
            self._save_users_rows(connection, users)
            self._save_mystic_state(connection, state)
            return MysticDungeonRun.from_dict(run.to_dict())

    async def settle_mystic_run(self, run_id: str, settlement: MysticSettlement) -> MysticDungeonRun:
        with self._txn() as connection:
            settlement_id = str(settlement.settlement_id or "").strip()
            if not settlement_id:
                raise ValueError("mystic settlement id must not be empty")
            state, users = self._load_mystic_state_with_recovery(connection)
            runs = state["runs"]
            run = self._run_from_doc(runs, run_id)
            users_changed = False
            for user_id, rewards in settlement.rewards_by_user.items():
                user_data = users.get(user_id)
                record = (
                    UserRecord.from_dict(user_data)
                    if isinstance(user_data, dict)
                    else UserRecord(user_id=user_id)
                )
                settlement_ids = list(record.mystic_settlement_ids or [])
                if settlement_id in settlement_ids:
                    continue
                apply_mystic_rewards(record, rewards)
                record.mystic_settlement_ids = normalize_mystic_settlement_ids(
                    [*settlement_ids, settlement_id]
                )
                users[user_id] = sanitize_user_record_data(record.to_dict())
                users_changed = True

            run_changed = run.phase is not DungeonPhase.COMPLETED
            if run_changed:
                run.phase = DungeonPhase.COMPLETED
                run.revision += 1
            cleanup_changed = self._cleanup_mystic_run(state, users, run)
            if users_changed or cleanup_changed:
                self._save_users_rows(connection, users)
            if run_changed or cleanup_changed:
                runs[run_id] = run.to_dict()
                self._save_mystic_state(connection, state)
            return MysticDungeonRun.from_dict(run.to_dict())

    async def get_mystic_encounter(self, encounter_id: str) -> Any | None:
        with _FILE_LOCK:
            state, _ = self._load_mystic_state_with_recovery(self._db)
        raw_encounter = state["encounters"].get(str(encounter_id))
        if raw_encounter is None:
            return None
        return self._decode_mystic_encounter(raw_encounter, str(encounter_id))

    async def list_active_mystic_encounters(self) -> list[Any]:
        with _FILE_LOCK:
            state, _ = self._load_mystic_state_with_recovery(self._db)
        encounters = []
        for encounter_id, raw_encounter in state["encounters"].items():
            encounter = self._decode_mystic_encounter(raw_encounter, encounter_id)
            if encounter.phase not in {EncounterPhase.COMPLETED, EncounterPhase.FAILED}:
                encounters.append(encounter)
        return sorted(encounters, key=lambda item: item.encounter_id)

    async def create_mystic_encounter_and_update_run(
        self,
        run_id: str,
        expected_run_revision: int,
        encounter: Any,
        run_updater: Callable[[MysticDungeonRun], MysticDungeonRun | None],
    ) -> tuple[MysticDungeonRun, Any]:
        with self._txn() as connection:
            state, _ = self._load_mystic_state_with_recovery(connection)
            runs = state["runs"]
            encounters = state["encounters"]
            run = self._run_from_doc(runs, run_id)
            if run.revision != expected_run_revision:
                raise MysticRunConflict(
                    f"mystic run {run_id!r} revision is {run.revision}, expected {expected_run_revision}"
                )
            if encounter.run_id != run_id:
                raise ValueError("mystic encounter run_id does not match run")
            if encounter.encounter_id in encounters:
                raise ValueError(f"mystic encounter {encounter.encounter_id!r} already exists")

            original_member_ids = run.member_ids
            candidate_run = run_updater(run)
            updated_run = run if candidate_run is None else candidate_run
            if not isinstance(updated_run, MysticDungeonRun):
                raise TypeError("mystic run updater must return MysticDungeonRun or None")
            if updated_run.run_id != run_id:
                raise ValueError("mystic run updater cannot change run_id")
            if updated_run.member_ids != original_member_ids:
                raise ValueError("mystic run updater cannot change the fixed roster")
            if updated_run.active_encounter_id != encounter.encounter_id:
                raise ValueError("mystic run must bind the created encounter")
            updated_run.revision = expected_run_revision + 1
            validated_run = MysticDungeonRun.from_dict(updated_run.to_dict())
            validated_encounter = DungeonEncounter.from_dict(encounter.to_dict())

            runs[run_id] = validated_run.to_dict()
            encounters[validated_encounter.encounter_id] = validated_encounter.to_dict()
            self._save_mystic_state(connection, state)
            return validated_run, validated_encounter

    async def update_mystic_run_and_encounter(
        self,
        run_id: str,
        expected_run_revision: int,
        encounter_id: str,
        expected_encounter_revision: int,
        run_updater: Callable[[MysticDungeonRun], MysticDungeonRun | None],
        encounter_updater: Callable[[Any], Any | None],
    ) -> tuple[MysticDungeonRun, Any]:
        with self._txn() as connection:
            state, _ = self._load_mystic_state_with_recovery(connection)
            runs = state["runs"]
            encounters = state["encounters"]
            run = self._run_from_doc(runs, run_id)
            encounter = self._encounter_from_doc(encounters, encounter_id)
            if run.revision != expected_run_revision:
                raise MysticRunConflict(
                    f"mystic run {run_id!r} revision is {run.revision}, expected {expected_run_revision}"
                )
            if encounter.revision != expected_encounter_revision:
                raise MysticEncounterConflict(
                    f"mystic encounter {encounter_id!r} revision is "
                    f"{encounter.revision}, expected {expected_encounter_revision}"
                )
            if encounter.run_id != run_id:
                raise ValueError("mystic encounter run_id does not match run")

            original_member_ids = run.member_ids
            original_run_payload = run.to_dict()
            original_encounter_payload = encounter.to_dict()
            candidate_encounter = encounter_updater(encounter)
            candidate_run = run_updater(run)
            updated_run = run if candidate_run is None else candidate_run
            updated_encounter = encounter if candidate_encounter is None else candidate_encounter
            if not isinstance(updated_run, MysticDungeonRun):
                raise TypeError("mystic run updater must return MysticDungeonRun or None")
            if not isinstance(updated_encounter, DungeonEncounter):
                raise TypeError("mystic encounter updater must return DungeonEncounter or None")
            if updated_run.run_id != run_id:
                raise ValueError("mystic run updater cannot change run_id")
            if updated_run.member_ids != original_member_ids:
                raise ValueError("mystic run updater cannot change the fixed roster")
            if updated_encounter.encounter_id != encounter_id:
                raise ValueError("mystic encounter updater cannot change encounter_id")
            if updated_encounter.run_id != run_id:
                raise ValueError("mystic encounter updater cannot change run_id")

            run_changed = updated_run.to_dict() != original_run_payload
            encounter_changed = updated_encounter.to_dict() != original_encounter_payload
            updated_run.revision = (
                expected_run_revision + 1 if run_changed else expected_run_revision
            )
            updated_encounter.revision = (
                expected_encounter_revision + 1 if encounter_changed else expected_encounter_revision
            )
            validated_run = MysticDungeonRun.from_dict(updated_run.to_dict())
            validated_encounter = DungeonEncounter.from_dict(updated_encounter.to_dict())
            runs[run_id] = validated_run.to_dict()
            encounters[encounter_id] = validated_encounter.to_dict()
            self._save_mystic_state(connection, state)
            return validated_run, validated_encounter

    async def create_mystic_encounter(self, encounter: Any) -> Any:
        with self._txn() as connection:
            state, _ = self._load_mystic_state_with_recovery(connection)
            encounters = state["encounters"]
            if encounter.encounter_id in encounters:
                raise ValueError(f"mystic encounter {encounter.encounter_id!r} already exists")
            saved = DungeonEncounter.from_dict(encounter.to_dict())
            encounters[saved.encounter_id] = saved.to_dict()
            self._save_mystic_state(connection, state)
            return saved

    async def update_mystic_encounter(
        self,
        encounter_id: str,
        expected_revision: int,
        updater: Callable[[Any], Any | None],
    ) -> Any:
        with self._txn() as connection:
            state, _ = self._load_mystic_state_with_recovery(connection)
            encounters = state["encounters"]
            encounter = self._encounter_from_doc(encounters, encounter_id)
            if encounter.revision != expected_revision:
                raise MysticEncounterConflict(
                    f"mystic encounter {encounter_id!r} revision is {encounter.revision}, "
                    f"expected {expected_revision}"
                )
            candidate = updater(encounter)
            updated = encounter if candidate is None else candidate
            if not isinstance(updated, DungeonEncounter):
                raise TypeError("mystic encounter updater must return DungeonEncounter or None")
            if updated.encounter_id != encounter_id:
                raise ValueError("mystic encounter updater cannot change encounter_id")
            updated.revision = expected_revision + 1
            validated = DungeonEncounter.from_dict(updated.to_dict())
            encounters[encounter_id] = validated.to_dict()
            self._save_mystic_state(connection, state)
            return validated

    async def delete_mystic_encounter(self, encounter_id: str) -> None:
        with self._txn() as connection:
            state, _ = self._load_mystic_state_with_recovery(connection)
            if state["encounters"].pop(str(encounter_id), None) is not None:
                self._save_mystic_state(connection, state)

    # --- admin 同步桥（后端无关契约，JsonStore 侧在同名方法中实现） -----------
    def read_users_sync(self) -> dict[str, Any]:
        with _FILE_LOCK:
            return self._read_rows("users", "user_id")

    def read_group_members_sync(self) -> dict[str, Any]:
        with _FILE_LOCK:
            return self._read_rows("group_members", "group_id")

    def update_users_sync(
        self,
        mutator: Callable[[dict[str, Any]], Any],
        user_ids: Iterable[str] | None = None,
    ) -> Any:
        """同一把锁 + 同一事务内「读-改-写」。

        ``user_ids`` 指定本次真正可能被改动的键（只回写这些行，保持 O(改动量)）；
        缺省回写全量（仅限调用方明确要全量重写的场景）。
        """
        with self._txn() as connection:
            data = self._read_rows("users", "user_id")
            result = mutator(data)
            targets = [str(uid) for uid in user_ids] if user_ids is not None else list(data)
            for user_id in targets:
                if user_id in data:
                    self._upsert(connection, "users", "user_id", user_id, data[user_id])
            return result

    def backup_users_snapshot(self, dest_dir: Path) -> Path:
        """SQLite 形态的玩家备份：``VACUUM INTO``（WAL 一致性快照）。"""
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        destination = dest_dir / f"users_{stamp}.db"
        self._db.execute("VACUUM INTO ?", (str(destination),))
        return destination

    def snapshot_users(self, reason: str = "admin") -> Path | None:
        """后台改存档前留可回退版本；SQLite 下等价于一次完整库备份。"""
        try:
            return self.backup_users_snapshot(self.data_dir / "backups")
        except Exception as exc:  # 快照失败不阻断写入（与 snapshots.py 同一哲学）
            logger.warning(f"SQLite 用户快照失败（已忽略）：{exc}")
            return None
