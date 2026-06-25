from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from .domain import UserRecord


class JsonStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.user_file_path = data_dir / "users.json"
        self.rank_file_path = data_dir / "daily_chat_rank.json"
        self.group_file_path = data_dir / "group_members.json"
        self.tianji_hall_file_path = data_dir / "tianji_divination_hall.json"
        self._lock = asyncio.Lock()

    async def get_user(self, user_id: str) -> UserRecord:
        async with self._lock:
            data = self._read_json(self.user_file_path)
            user_data = data.get(user_id)
            if user_data is None:
                return UserRecord(user_id=user_id)
            return UserRecord.from_dict(user_data)

    async def save_user(self, record: UserRecord) -> None:
        async with self._lock:
            data = self._read_json(self.user_file_path)
            data[record.user_id] = record.to_dict()
            self._write_json(self.user_file_path, data)

    async def touch_group_member(
        self,
        group_id: str,
        user_id: str,
        date_text: str,
        nickname: str = "",
    ) -> None:
        async with self._lock:
            self._touch_group_member_locked(group_id, user_id, date_text, nickname)

    async def add_chat_count(
        self,
        group_id: str,
        user_id: str,
        date_text: str,
        nickname: str,
    ) -> None:
        async with self._lock:
            data = self._read_json(self.rank_file_path)
            group_data = data.setdefault(group_id, {})
            if group_data.get("date") != date_text:
                group_data.clear()
                group_data["date"] = date_text
                group_data["settled"] = False
                group_data["users"] = {}
            users = group_data.setdefault("users", {})
            user_data = users.setdefault(
                user_id,
                {
                    "user_id": user_id,
                    "nickname": nickname,
                    "count": 0,
                },
            )
            user_data["nickname"] = nickname or user_data.get("nickname") or user_id
            user_data["count"] = int(user_data.get("count", 0)) + 1
            self._write_json(self.rank_file_path, data)
            self._touch_group_member_locked(group_id, user_id, date_text, nickname)

    async def register_tianji_sitter(
        self,
        group_id: str,
        user_id: str,
        date_text: str,
        nickname: str = "",
    ) -> tuple[bool, dict[str, Any]]:
        async with self._lock:
            data = self._read_json(self.tianji_hall_file_path)
            group_data = data.get(group_id)
            if not isinstance(group_data, dict) or group_data.get("date") != date_text:
                sitter = {"user_id": user_id, "nickname": nickname or user_id}
                group_data = {
                    "date": date_text,
                    "sitter_id": user_id,
                    "sitter_name": nickname or user_id,
                    "sitters": [sitter],
                    "divination_count": 0,
                    "income": 0,
                }
                data[group_id] = group_data
                self._write_json(self.tianji_hall_file_path, data)
                return True, dict(group_data)
            return False, dict(group_data)

    async def join_tianji_sitter(
        self,
        group_id: str,
        user_id: str,
        date_text: str,
        nickname: str = "",
    ) -> tuple[bool, dict[str, Any] | None]:
        async with self._lock:
            data = self._read_json(self.tianji_hall_file_path)
            group_data = data.get(group_id)
            if not isinstance(group_data, dict) or group_data.get("date") != date_text:
                return False, None
            sitters = group_data.get("sitters")
            if not isinstance(sitters, list) or not sitters:
                primary_id = str(group_data.get("sitter_id") or user_id)
                sitters = [
                    {
                        "user_id": primary_id,
                        "nickname": str(group_data.get("sitter_name") or primary_id),
                    }
                ]
            normalized = []
            seen = set()
            for item in sitters:
                if not isinstance(item, dict):
                    continue
                sitter_id = str(item.get("user_id") or "")
                if not sitter_id or sitter_id in seen:
                    continue
                seen.add(sitter_id)
                normalized.append({"user_id": sitter_id, "nickname": str(item.get("nickname") or sitter_id)})
            if user_id in seen:
                group_data["sitters"] = normalized
                data[group_id] = group_data
                self._write_json(self.tianji_hall_file_path, data)
                return False, dict(group_data)
            normalized.append({"user_id": user_id, "nickname": nickname or user_id})
            group_data["sitters"] = normalized
            data[group_id] = group_data
            self._write_json(self.tianji_hall_file_path, data)
            return True, dict(group_data)

    async def get_tianji_hall(self, group_id: str, date_text: str) -> dict[str, Any] | None:
        async with self._lock:
            group_data = self._read_json(self.tianji_hall_file_path).get(group_id)
            if not isinstance(group_data, dict) or group_data.get("date") != date_text:
                return None
            return dict(group_data)

    async def add_tianji_divination_income(
        self,
        group_id: str,
        date_text: str,
        amount: int,
    ) -> dict[str, Any] | None:
        async with self._lock:
            data = self._read_json(self.tianji_hall_file_path)
            group_data = data.get(group_id)
            if not isinstance(group_data, dict) or group_data.get("date") != date_text:
                return None
            group_data["divination_count"] = int(group_data.get("divination_count", 0)) + 1
            group_data["income"] = int(group_data.get("income", 0)) + max(0, int(amount))
            data[group_id] = group_data
            self._write_json(self.tianji_hall_file_path, data)
            return dict(group_data)

    async def get_group_member_nickname(self, group_id: str, user_id: str) -> str:
        async with self._lock:
            group_data = self._read_json(self.group_file_path).get(group_id, {})
            if not isinstance(group_data, dict):
                return ""
            users = group_data.get("users", {})
            if not isinstance(users, dict):
                return ""
            user_data = users.get(user_id)
            if not isinstance(user_data, dict):
                return ""
            nickname = str(user_data.get("nickname") or "")
            return "" if nickname == user_id else nickname


    async def get_group_user_records(self, group_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            group_data = self._read_json(self.group_file_path).get(group_id, {})
            if not isinstance(group_data, dict):
                return []
            members = group_data.get("users", {})
            if not isinstance(members, dict):
                return []

            users = self._read_json(self.user_file_path)
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

    async def get_unsettled_rank_groups(self, date_text: str) -> dict[str, dict[str, Any]]:
        async with self._lock:
            data = self._read_json(self.rank_file_path)
            result = {}
            for group_id, group_data in data.items():
                if not isinstance(group_data, dict):
                    continue
                if group_data.get("date") != date_text or group_data.get("settled"):
                    continue
                result[group_id] = group_data
            return result

    async def mark_rank_group_settled(self, group_id: str, date_text: str) -> None:
        async with self._lock:
            data = self._read_json(self.rank_file_path)
            group_data = data.get(group_id)
            if isinstance(group_data, dict) and group_data.get("date") == date_text:
                group_data["settled"] = True
                self._write_json(self.rank_file_path, data)

    async def apply_to_user(self, user_id: str, updater) -> UserRecord:
        async with self._lock:
            data = self._read_json(self.user_file_path)
            user_data = data.get(user_id)
            record = (
                UserRecord.from_dict(user_data)
                if isinstance(user_data, dict)
                else UserRecord(user_id=user_id)
            )
            updater(record)
            data[user_id] = record.to_dict()
            self._write_json(self.user_file_path, data)
            return record

    def _touch_group_member_locked(
        self,
        group_id: str,
        user_id: str,
        date_text: str,
        nickname: str = "",
    ) -> None:
        data = self._read_json(self.group_file_path)
        group_data = data.setdefault(group_id, {"users": {}})
        users = group_data.setdefault("users", {})
        user_data = users.setdefault(user_id, {"user_id": user_id})
        user_data["nickname"] = nickname or user_data.get("nickname") or user_id
        user_data["last_seen_date"] = date_text
        self._write_json(self.group_file_path, data)

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        temp_path.replace(path)
