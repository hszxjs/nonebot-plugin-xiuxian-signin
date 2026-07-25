from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .domain import (
    UserRecord,
    append_reward,
    apply_exp,
    consume_reward_by_names,
    normalize_mystic_settlement_ids,
    sanitize_user_record_data,
)
from .mystic_battle import DungeonEncounter, EncounterPhase
from .mystic_dungeon import DungeonPhase, MysticDungeonRun


MYSTIC_TERMINAL_PHASES = {
    DungeonPhase.COMPLETED,
    DungeonPhase.FAILED,
    DungeonPhase.ABANDONED,
}


class MysticRunConflict(RuntimeError):
    """Raised when a persisted run revision changed before update."""


class MysticRunNotFound(LookupError):
    """Raised when a requested persisted run does not exist."""


class MysticEncounterConflict(RuntimeError):
    """Raised when a persisted encounter revision changed before update."""


class MysticStateCorrupt(ValueError):
    """Raised when the persistent dungeon document cannot be validated."""


@dataclass(frozen=True)
class MysticSettlement:
    settlement_id: str
    rewards_by_user: dict[str, list[dict[str, Any]]]


@dataclass
class MysticRescueRequest:
    request_id: str
    run_id: str
    encounter_id: str
    group_id: str
    requester_id: str
    requester_name: str
    reward_stones: int
    monster_snapshot: dict[str, Any]
    remaining_hp: int
    deadline: str
    status: str = "open"
    active_rescuer_id: str | None = None
    attempted_rescuer_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.monster_snapshot = dict(self.monster_snapshot)
        self.attempted_rescuer_ids = list(dict.fromkeys(self.attempted_rescuer_ids))
        if not all(
            (
                self.request_id,
                self.run_id,
                self.encounter_id,
                self.group_id,
                self.requester_id,
                self.deadline,
            )
        ):
            raise ValueError("mystic rescue identifiers and deadline must not be empty")
        if self.reward_stones <= 0 or self.remaining_hp <= 0:
            raise ValueError("mystic rescue reward and remaining HP must be positive")
        if self.status not in {"open", "taken", "completed", "expired"}:
            raise ValueError("mystic rescue status is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "run_id": self.run_id,
            "encounter_id": self.encounter_id,
            "group_id": self.group_id,
            "requester_id": self.requester_id,
            "requester_name": self.requester_name,
            "reward_stones": self.reward_stones,
            "monster_snapshot": dict(self.monster_snapshot),
            "remaining_hp": self.remaining_hp,
            "deadline": self.deadline,
            "status": self.status,
            "active_rescuer_id": self.active_rescuer_id,
            "attempted_rescuer_ids": list(self.attempted_rescuer_ids),
        }

    @classmethod
    def from_dict(cls, value: Any) -> MysticRescueRequest:
        if not isinstance(value, dict):
            raise ValueError("mystic rescue request must be an object")
        raw_monster_snapshot = value.get("monster_snapshot")
        return cls(
            request_id=str(value.get("request_id") or ""),
            run_id=str(value.get("run_id") or ""),
            encounter_id=str(value.get("encounter_id") or ""),
            group_id=str(value.get("group_id") or ""),
            requester_id=str(value.get("requester_id") or ""),
            requester_name=str(value.get("requester_name") or ""),
            reward_stones=int(value.get("reward_stones") or 0),
            monster_snapshot=(
                dict(raw_monster_snapshot)
                if isinstance(raw_monster_snapshot, dict)
                else {}
            ),
            remaining_hp=int(value.get("remaining_hp") or 0),
            deadline=str(value.get("deadline") or ""),
            status=str(value.get("status") or "open"),
            active_rescuer_id=(
                str(value["active_rescuer_id"])
                if value.get("active_rescuer_id") is not None
                else None
            ),
            attempted_rescuer_ids=[
                str(item)
                for item in value.get("attempted_rescuer_ids", [])
                if str(item)
            ],
        )


def apply_mystic_rewards(record: UserRecord, rewards: list[dict[str, Any]]) -> None:
    for raw_reward in rewards:
        reward = dict(raw_reward)
        try:
            amount = int(reward.get("amount", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("mystic reward amount must be an integer") from exc
        if amount <= 0:
            continue
        category = str(reward.get("category") or "").strip()
        name = str(reward.get("name") or "").strip()
        if category in {"灵石", "spirit_stones"} or name == "灵石":
            record.spirit_stones += amount
            continue
        if category in {"修为", "修为经验", "cultivation_exp"} or name in {"修为", "修为经验"}:
            apply_exp(record, amount)
            continue
        if category in {"垂钓次数", "fishing_chances"} or name == "垂钓次数":
            record.fishing_chances += amount
            continue
        reward.pop("amount", None)
        for _ in range(amount):
            append_reward(record, dict(reward))


class JsonStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.user_file_path = data_dir / "users.json"
        self.rank_file_path = data_dir / "daily_chat_rank.json"
        self.group_file_path = data_dir / "group_members.json"
        self.tianji_hall_file_path = data_dir / "tianji_divination_hall.json"
        self.unique_artifact_file_path = data_dir / "unique_artifacts.json"
        self.trade_file_path = data_dir / "trade_offers.json"
        self.rescue_file_path = data_dir / "mystic_rescue.json"
        self.mystic_file_path = data_dir / "mystic_dungeons.json"
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
            data[record.user_id] = sanitize_user_record_data(record.to_dict())
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
            data[user_id] = sanitize_user_record_data(record.to_dict())
            self._write_json(self.user_file_path, data)
            return record


    async def get_unique_artifacts(self) -> dict[str, Any]:
        async with self._lock:
            return dict(self._read_json(self.unique_artifact_file_path))

    async def claim_unique_artifact(self, item_name: str, user_id: str, nickname: str = "") -> tuple[bool, dict[str, Any]]:
        async with self._lock:
            data = self._read_json(self.unique_artifact_file_path)
            current = data.get(item_name)
            if isinstance(current, dict):
                return str(current.get("user_id")) == user_id, dict(current)
            owner = {"user_id": user_id, "nickname": nickname or user_id}
            data[item_name] = owner
            self._write_json(self.unique_artifact_file_path, data)
            return True, dict(owner)

    async def unique_owner_name(self, item_name: str) -> str:
        async with self._lock:
            owner = self._read_json(self.unique_artifact_file_path).get(item_name)
            if not isinstance(owner, dict):
                return ""
            return str(owner.get("nickname") or owner.get("user_id") or "")

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
        async with self._lock:
            data = self._read_json(self.trade_file_path)
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
            self._write_json(self.trade_file_path, data)
            return dict(offer)

    async def list_trade_offers(self, group_id: str, market: bool | None = None) -> list[dict[str, Any]]:
        async with self._lock:
            group = self._read_json(self.trade_file_path).get(str(group_id), {})
            if not isinstance(group, dict):
                return []
            offers = [dict(item) for item in group.values() if isinstance(item, dict) and item.get("status") == "open"]
            if market is None:
                return offers
            return [item for item in offers if bool(item.get("market")) is bool(market)]

    async def take_trade_offer(self, group_id: str, offer_id: str, buyer_id: str) -> dict[str, Any] | None:
        async with self._lock:
            data = self._read_json(self.trade_file_path)
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
            self._write_json(self.trade_file_path, data)
            return dict(offer)

    async def cancel_trade_offer(self, group_id: str, offer_id: str, seller_id: str) -> dict[str, Any] | None:
        async with self._lock:
            data = self._read_json(self.trade_file_path)
            group = data.get(str(group_id), {})
            if not isinstance(group, dict):
                return None
            offer = group.get(str(offer_id))
            if not isinstance(offer, dict) or str(offer.get("seller_id")) != str(seller_id) or offer.get("status") != "open":
                return None
            offer["status"] = "cancelled"
            group[str(offer_id)] = offer
            data[str(group_id)] = group
            self._write_json(self.trade_file_path, data)
            return dict(offer)

    async def create_rescue_request(
        self,
        request: MysticRescueRequest,
    ) -> MysticRescueRequest:
        async with self._lock:
            data = self._read_rescue_state_locked()
            group = data.setdefault(request.group_id, {})
            if request.request_id in group:
                return MysticRescueRequest.from_dict(group[request.request_id])
            users = self._read_json(self.user_file_path)
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
            self._write_json(self.user_file_path, users)
            self._write_json(self.rescue_file_path, data)
            return MysticRescueRequest.from_dict(request.to_dict())

    async def list_rescue_requests(
        self,
        group_id: str,
    ) -> list[MysticRescueRequest]:
        async with self._lock:
            group = self._read_rescue_state_locked().get(str(group_id), {})
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

    async def get_rescue_request(
        self,
        request_id: str,
    ) -> MysticRescueRequest | None:
        async with self._lock:
            data = self._read_rescue_state_locked()
            try:
                _, request = self._rescue_from_state(data, request_id)
            except LookupError:
                return None
            return request

    async def find_active_rescue_for_user(
        self,
        rescuer_id: str,
    ) -> MysticRescueRequest | None:
        async with self._lock:
            data = self._read_rescue_state_locked()
            matches: list[MysticRescueRequest] = []
            for raw_group in data.values():
                if not isinstance(raw_group, dict):
                    continue
                for raw_request in raw_group.values():
                    if not isinstance(raw_request, dict):
                        continue
                    request = MysticRescueRequest.from_dict(raw_request)
                    if (
                        request.status == "taken"
                        and request.active_rescuer_id == rescuer_id
                    ):
                        matches.append(request)
            return min(matches, key=lambda item: item.request_id) if matches else None

    async def take_rescue_request(
        self,
        group_id: str,
        request_id: str,
        rescuer_id: str,
    ) -> MysticRescueRequest | None:
        async with self._lock:
            data = self._read_rescue_state_locked()
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
            self._write_json(self.rescue_file_path, data)
            return MysticRescueRequest.from_dict(request.to_dict())

    async def fail_rescue_attempt(
        self,
        request_id: str,
        rescuer_id: str,
    ) -> MysticRescueRequest:
        async with self._lock:
            data = self._read_rescue_state_locked()
            group, request = self._rescue_from_state(data, request_id)
            if request.status != "taken" or request.active_rescuer_id != rescuer_id:
                raise ValueError("rescuer does not own the active rescue attempt")
            request.attempted_rescuer_ids.append(rescuer_id)
            request.attempted_rescuer_ids = list(dict.fromkeys(request.attempted_rescuer_ids))
            request.active_rescuer_id = None
            request.status = "open"
            group[request_id] = request.to_dict()
            self._write_json(self.rescue_file_path, data)
            return MysticRescueRequest.from_dict(request.to_dict())

    async def complete_rescue_request(
        self,
        request_id: str,
        rescuer_id: str,
    ) -> MysticRescueRequest:
        async with self._lock:
            data = self._read_rescue_state_locked()
            group, request = self._rescue_from_state(data, request_id)
            settlement_id = f"rescue:{request_id}:complete"
            state, users = self._read_mystic_state_with_recovery_locked()
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
            runs = self._mystic_section(state, "runs")
            run = self._run_from_state(runs, request.run_id)
            if run.current_node_id not in run.cleared_node_ids:
                run.cleared_node_ids.append(run.current_node_id)
            run.active_encounter_id = None
            run.phase = DungeonPhase.READY_TO_ROLL
            run.revision += 1
            runs[run.run_id] = run.to_dict()
            request.status = "completed"
            request.active_rescuer_id = rescuer_id
            group[request_id] = request.to_dict()
            self._write_json(self.user_file_path, users)
            self._write_json(self.mystic_file_path, state)
            self._write_json(self.rescue_file_path, data)
            return MysticRescueRequest.from_dict(request.to_dict())

    async def expire_rescue_request(
        self,
        request_id: str,
    ) -> MysticRescueRequest:
        async with self._lock:
            data = self._read_rescue_state_locked()
            group, request = self._rescue_from_state(data, request_id)
            if request.status == "completed":
                return request
            users = self._read_json(self.user_file_path)
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
                users[request.requester_id] = sanitize_user_record_data(
                    requester.to_dict()
                )
            request.status = "expired"
            request.active_rescuer_id = None
            group[request_id] = request.to_dict()
            self._write_json(self.user_file_path, users)
            self._write_json(self.rescue_file_path, data)
            return MysticRescueRequest.from_dict(request.to_dict())

    async def get_mystic_run(self, run_id: str) -> MysticDungeonRun | None:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            raw_run = self._mystic_section(state, "runs").get(str(run_id))
            if raw_run is None:
                return None
            return self._decode_mystic_run(raw_run, str(run_id))

    async def list_active_mystic_runs(self) -> list[MysticDungeonRun]:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            active_runs = []
            for run_id, raw_run in self._mystic_section(state, "runs").items():
                run = self._decode_mystic_run(raw_run, run_id)
                if run.phase not in MYSTIC_TERMINAL_PHASES:
                    active_runs.append(run)
            return sorted(active_runs, key=lambda item: item.run_id)

    async def find_active_mystic_run_id(self, user_id: str) -> str | None:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            run_id = self._mystic_section(state, "active_by_user").get(str(user_id))
            return str(run_id) if run_id else None

    async def create_mystic_lobby(
        self,
        run: MysticDungeonRun,
    ) -> MysticDungeonRun:
        async with self._lock:
            if run.mode.value != "team" or run.phase is not DungeonPhase.LOBBY:
                raise ValueError("mystic lobby must be a team run in lobby phase")
            state, users = self._read_mystic_state_with_recovery_locked()
            runs = self._mystic_section(state, "runs")
            active_by_user = self._mystic_section(state, "active_by_user")
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
            self._write_json(self.user_file_path, users)
            self._write_json(self.mystic_file_path, state)
            return saved

    async def create_mystic_run(
        self,
        run: MysticDungeonRun,
        payer_id: str,
        token_name: str,
    ) -> MysticDungeonRun:
        async with self._lock:
            if run.phase is not DungeonPhase.READY_TO_ROLL:
                raise ValueError("mystic run must be ready_to_roll before persistence")
            if payer_id != run.leader_id:
                raise ValueError("only the dungeon leader can pay the entry token")
            if not token_name:
                raise ValueError("mystic token name must not be empty")

            state, users = self._read_mystic_state_with_recovery_locked()
            runs = self._mystic_section(state, "runs")
            active_by_user = self._mystic_section(state, "active_by_user")
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
                    raise MysticRunConflict(
                        f"mystic lobby {run.run_id!r} changed before start"
                    )
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

            creating = MysticDungeonRun.from_dict(run.to_dict())
            creating.phase = DungeonPhase.CREATING
            runs[run.run_id] = creating.to_dict()
            self._write_json(self.mystic_file_path, state)

            payer_data = users.get(payer_id)
            payer = (
                UserRecord.from_dict(payer_data)
                if isinstance(payer_data, dict)
                else UserRecord(user_id=payer_id)
            )
            if consume_reward_by_names(payer, [token_name]) is None:
                if existing_lobby_payload is None:
                    runs.pop(run.run_id, None)
                else:
                    runs[run.run_id] = existing_lobby_payload
                self._write_json(self.mystic_file_path, state)
                raise ValueError(f"payer does not have required mystic token {token_name!r}")

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
            self._write_json(self.user_file_path, users)
            self._write_json(self.mystic_file_path, state)
            return saved

    async def update_mystic_lobby(
        self,
        run_id: str,
        expected_revision: int,
        updater: Callable[[MysticDungeonRun], MysticDungeonRun | None],
    ) -> MysticDungeonRun:
        async with self._lock:
            state, users = self._read_mystic_state_with_recovery_locked()
            runs = self._mystic_section(state, "runs")
            active_by_user = self._mystic_section(state, "active_by_user")
            current = self._run_from_state(runs, run_id)
            if current.phase is not DungeonPhase.LOBBY:
                raise ValueError("mystic lobby is no longer open")
            if current.revision != expected_revision:
                raise MysticRunConflict(
                    f"mystic lobby {run_id!r} revision is "
                    f"{current.revision}, expected {expected_revision}"
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
            self._write_json(self.user_file_path, users)
            self._write_json(self.mystic_file_path, state)
            return validated

    async def update_mystic_run(
        self,
        run_id: str,
        expected_revision: int,
        updater: Callable[[MysticDungeonRun], MysticDungeonRun | None],
    ) -> MysticDungeonRun:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            runs = self._mystic_section(state, "runs")
            run = self._run_from_state(runs, run_id)
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
            self._write_json(self.mystic_file_path, state)
            return validated

    async def bind_mystic_private_routes(self, run: MysticDungeonRun) -> None:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            persisted = self._run_from_state(self._mystic_section(state, "runs"), run.run_id)
            if persisted.phase in MYSTIC_TERMINAL_PHASES:
                raise ValueError("cannot bind private routes for a terminal mystic run")
            routes = self._mystic_section(state, "private_routes")
            for user_id in persisted.member_ids:
                routes[user_id] = {
                    "run_id": persisted.run_id,
                    "group_id": persisted.source_group_id,
                }
            self._write_json(self.mystic_file_path, state)

    async def resolve_mystic_private_route(self, user_id: str) -> tuple[str, str] | None:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            raw_route = self._mystic_section(state, "private_routes").get(str(user_id))
            if raw_route is None:
                return None
            if not isinstance(raw_route, dict):
                raise MysticStateCorrupt("mystic private route must be an object")
            run_id = str(raw_route.get("run_id") or "")
            group_id = str(raw_route.get("group_id") or "")
            if not run_id or not group_id:
                raise MysticStateCorrupt("mystic private route is missing run_id or group_id")
            return run_id, group_id

    async def close_mystic_run(
        self,
        run_id: str,
        terminal_phase: DungeonPhase,
    ) -> MysticDungeonRun:
        async with self._lock:
            try:
                phase = DungeonPhase(terminal_phase)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"unknown terminal mystic phase {terminal_phase!r}") from exc
            if phase not in MYSTIC_TERMINAL_PHASES:
                raise ValueError("close_mystic_run requires a terminal phase")
            state, users = self._read_mystic_state_with_recovery_locked()
            runs = self._mystic_section(state, "runs")
            run = self._run_from_state(runs, run_id)
            if run.phase is not phase:
                run.phase = phase
                run.revision += 1
            if phase is not DungeonPhase.COMPLETED:
                run.temporary_rewards_by_user = {}
            run.active_vote = None
            run.active_encounter_id = None
            self._cleanup_mystic_run_locked(state, users, run)
            runs[run_id] = run.to_dict()
            self._write_json(self.user_file_path, users)
            self._write_json(self.mystic_file_path, state)
            return MysticDungeonRun.from_dict(run.to_dict())

    async def settle_mystic_run(
        self,
        run_id: str,
        settlement: MysticSettlement,
    ) -> MysticDungeonRun:
        async with self._lock:
            settlement_id = str(settlement.settlement_id or "").strip()
            if not settlement_id:
                raise ValueError("mystic settlement id must not be empty")
            state, users = self._read_mystic_state_with_recovery_locked()
            runs = self._mystic_section(state, "runs")
            run = self._run_from_state(runs, run_id)
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
            cleanup_changed = self._cleanup_mystic_run_locked(state, users, run)
            if users_changed or cleanup_changed:
                self._write_json(self.user_file_path, users)
            if run_changed or cleanup_changed:
                runs[run_id] = run.to_dict()
                self._write_json(self.mystic_file_path, state)
            return MysticDungeonRun.from_dict(run.to_dict())

    async def get_mystic_encounter(
        self,
        encounter_id: str,
    ) -> DungeonEncounter | None:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            raw_encounter = self._mystic_section(state, "encounters").get(str(encounter_id))
            if raw_encounter is None:
                return None
            return self._decode_mystic_encounter(raw_encounter, str(encounter_id))

    async def list_active_mystic_encounters(self) -> list[DungeonEncounter]:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            encounters = []
            for encounter_id, raw_encounter in self._mystic_section(state, "encounters").items():
                encounter = self._decode_mystic_encounter(raw_encounter, encounter_id)
                if encounter.phase not in {EncounterPhase.COMPLETED, EncounterPhase.FAILED}:
                    encounters.append(encounter)
            return sorted(encounters, key=lambda item: item.encounter_id)

    async def create_mystic_encounter_and_update_run(
        self,
        run_id: str,
        expected_run_revision: int,
        encounter: DungeonEncounter,
        run_updater: Callable[[MysticDungeonRun], MysticDungeonRun | None],
    ) -> tuple[MysticDungeonRun, DungeonEncounter]:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            runs = self._mystic_section(state, "runs")
            encounters = self._mystic_section(state, "encounters")
            run = self._run_from_state(runs, run_id)
            if run.revision != expected_run_revision:
                raise MysticRunConflict(
                    f"mystic run {run_id!r} revision is "
                    f"{run.revision}, expected {expected_run_revision}"
                )
            if encounter.run_id != run_id:
                raise ValueError("mystic encounter run_id does not match run")
            if encounter.encounter_id in encounters:
                raise ValueError(
                    f"mystic encounter {encounter.encounter_id!r} already exists"
                )

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
            self._write_json(self.mystic_file_path, state)
            return validated_run, validated_encounter

    async def update_mystic_run_and_encounter(
        self,
        run_id: str,
        expected_run_revision: int,
        encounter_id: str,
        expected_encounter_revision: int,
        run_updater: Callable[[MysticDungeonRun], MysticDungeonRun | None],
        encounter_updater: Callable[[DungeonEncounter], DungeonEncounter | None],
    ) -> tuple[MysticDungeonRun, DungeonEncounter]:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            runs = self._mystic_section(state, "runs")
            encounters = self._mystic_section(state, "encounters")
            run = self._run_from_state(runs, run_id)
            encounter = self._encounter_from_state(encounters, encounter_id)
            if run.revision != expected_run_revision:
                raise MysticRunConflict(
                    f"mystic run {run_id!r} revision is "
                    f"{run.revision}, expected {expected_run_revision}"
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
            updated_encounter = (
                encounter if candidate_encounter is None else candidate_encounter
            )
            if not isinstance(updated_run, MysticDungeonRun):
                raise TypeError("mystic run updater must return MysticDungeonRun or None")
            if not isinstance(updated_encounter, DungeonEncounter):
                raise TypeError(
                    "mystic encounter updater must return DungeonEncounter or None"
                )
            if updated_run.run_id != run_id:
                raise ValueError("mystic run updater cannot change run_id")
            if updated_run.member_ids != original_member_ids:
                raise ValueError("mystic run updater cannot change the fixed roster")
            if updated_encounter.encounter_id != encounter_id:
                raise ValueError("mystic encounter updater cannot change encounter_id")
            if updated_encounter.run_id != run_id:
                raise ValueError("mystic encounter updater cannot change run_id")

            run_changed = updated_run.to_dict() != original_run_payload
            encounter_changed = (
                updated_encounter.to_dict() != original_encounter_payload
            )
            updated_run.revision = (
                expected_run_revision + 1
                if run_changed
                else expected_run_revision
            )
            updated_encounter.revision = (
                expected_encounter_revision + 1
                if encounter_changed
                else expected_encounter_revision
            )
            validated_run = MysticDungeonRun.from_dict(updated_run.to_dict())
            validated_encounter = DungeonEncounter.from_dict(
                updated_encounter.to_dict()
            )
            runs[run_id] = validated_run.to_dict()
            encounters[encounter_id] = validated_encounter.to_dict()
            self._write_json(self.mystic_file_path, state)
            return validated_run, validated_encounter

    async def create_mystic_encounter(
        self,
        encounter: DungeonEncounter,
    ) -> DungeonEncounter:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            encounters = self._mystic_section(state, "encounters")
            if encounter.encounter_id in encounters:
                raise ValueError(f"mystic encounter {encounter.encounter_id!r} already exists")
            saved = DungeonEncounter.from_dict(encounter.to_dict())
            encounters[saved.encounter_id] = saved.to_dict()
            self._write_json(self.mystic_file_path, state)
            return saved

    async def update_mystic_encounter(
        self,
        encounter_id: str,
        expected_revision: int,
        updater: Callable[[DungeonEncounter], DungeonEncounter | None],
    ) -> DungeonEncounter:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            encounters = self._mystic_section(state, "encounters")
            encounter = self._encounter_from_state(encounters, encounter_id)
            if encounter.revision != expected_revision:
                raise MysticEncounterConflict(
                    f"mystic encounter {encounter_id!r} revision is "
                    f"{encounter.revision}, expected {expected_revision}"
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
            self._write_json(self.mystic_file_path, state)
            return validated

    async def delete_mystic_encounter(self, encounter_id: str) -> None:
        async with self._lock:
            state, _ = self._read_mystic_state_with_recovery_locked()
            encounters = self._mystic_section(state, "encounters")
            if encounters.pop(str(encounter_id), None) is not None:
                self._write_json(self.mystic_file_path, state)

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

    def _empty_mystic_state(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "runs": {},
            "encounters": {},
            "active_by_user": {},
            "private_routes": {},
        }

    def _read_mystic_state_locked(self) -> dict[str, Any]:
        if not self.mystic_file_path.exists():
            return self._empty_mystic_state()
        try:
            with self.mystic_file_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
        except (OSError, json.JSONDecodeError) as exc:
            raise MysticStateCorrupt("mystic dungeon state JSON is unreadable") from exc
        if not isinstance(data, dict):
            raise MysticStateCorrupt("mystic dungeon state root must be an object")
        expected_keys = {
            "schema_version",
            "runs",
            "encounters",
            "active_by_user",
            "private_routes",
        }
        if set(data) != expected_keys:
            raise MysticStateCorrupt("mystic dungeon state has invalid root keys")
        if data.get("schema_version") != 1:
            raise MysticStateCorrupt("unsupported mystic dungeon state schema")
        for section_name in ("runs", "encounters", "active_by_user", "private_routes"):
            section = data.get(section_name)
            if not isinstance(section, dict) or not all(isinstance(key, str) for key in section):
                raise MysticStateCorrupt(f"mystic dungeon section {section_name!r} must be an object")
        return data

    def _read_mystic_state_with_recovery_locked(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        state = self._read_mystic_state_locked()
        users = self._read_json(self.user_file_path)
        if self._recover_creating_runs_locked(state, users):
            self._write_json(self.user_file_path, users)
            self._write_json(self.mystic_file_path, state)
        return state, users

    def _recover_creating_runs_locked(
        self,
        state: dict[str, Any],
        users: dict[str, Any],
    ) -> bool:
        changed = False
        runs = self._mystic_section(state, "runs")
        active_by_user = self._mystic_section(state, "active_by_user")
        routes = self._mystic_section(state, "private_routes")
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

    def _mystic_section(self, state: dict[str, Any], name: str) -> dict[str, Any]:
        section = state.get(name)
        if not isinstance(section, dict):
            raise MysticStateCorrupt(f"mystic dungeon section {name!r} must be an object")
        return section

    def _rescue_from_state(
        self,
        state: dict[str, Any],
        request_id: str,
    ) -> tuple[dict[str, Any], MysticRescueRequest]:
        for group_id, raw_group in state.items():
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

    def _read_rescue_state_locked(self) -> dict[str, Any]:
        data = self._read_json(self.rescue_file_path)
        if data.get("schema_version") != 2:
            return {"schema_version": 2}
        return data

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

    def _run_from_state(
        self,
        runs: dict[str, Any],
        run_id: str,
    ) -> MysticDungeonRun:
        raw_run = runs.get(str(run_id))
        if raw_run is None:
            raise MysticRunNotFound(f"mystic run {run_id!r} was not found")
        return self._decode_mystic_run(raw_run, str(run_id))

    def _decode_mystic_encounter(
        self,
        raw_encounter: Any,
        encounter_id: str,
    ) -> DungeonEncounter:
        if not isinstance(raw_encounter, dict):
            raise MysticStateCorrupt(
                f"mystic encounter {encounter_id!r} must be an object"
            )
        try:
            encounter = DungeonEncounter.from_dict(raw_encounter)
        except (TypeError, ValueError) as exc:
            raise MysticStateCorrupt(
                f"mystic encounter {encounter_id!r} is corrupt"
            ) from exc
        if encounter.encounter_id != encounter_id:
            raise MysticStateCorrupt(
                f"mystic encounter key {encounter_id!r} does not match its payload"
            )
        return encounter

    def _encounter_from_state(
        self,
        encounters: dict[str, Any],
        encounter_id: str,
    ) -> DungeonEncounter:
        raw_encounter = encounters.get(str(encounter_id))
        if raw_encounter is None:
            raise LookupError(f"mystic encounter {encounter_id!r} was not found")
        return self._decode_mystic_encounter(raw_encounter, str(encounter_id))

    def _cleanup_mystic_run_locked(
        self,
        state: dict[str, Any],
        users: dict[str, Any],
        run: MysticDungeonRun,
    ) -> bool:
        changed = False
        active_by_user = self._mystic_section(state, "active_by_user")
        routes = self._mystic_section(state, "private_routes")
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
