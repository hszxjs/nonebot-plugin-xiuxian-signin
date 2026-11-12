"""群内排行的取数与格式化（R-18）。

修为榜、战力榜的分组取数、结算时刻判定与榜单文本。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..domain import battle_power
from ..state import store
from .parsing import short_name
from .texts import RANK_SETTLE_HOUR, RANK_SETTLE_MINUTE


def is_settle_time(now: datetime) -> bool:
    return (now.hour, now.minute) >= (RANK_SETTLE_HOUR, RANK_SETTLE_MINUTE)


def rank_entries_from_group(group_data: dict[str, Any]) -> list[dict[str, Any]]:
    users = group_data.get("users", {})
    if not isinstance(users, dict):
        return []
    entries = [entry for entry in users.values() if isinstance(entry, dict)]
    entries.sort(key=lambda item: int(item.get("count", 0)), reverse=True)
    return entries


async def group_cultivation_rank_entries(group_id: str) -> list[dict[str, Any]]:
    entries = await store.get_group_user_records(group_id)
    entries = [
        entry
        for entry in entries
        if entry["record"].root is not None
        or entry["record"].total_exp > 0
        or entry["record"].pending_exp > 0
    ]
    entries.sort(
        key=lambda item: (
            item["record"].total_exp + item["record"].pending_exp,
            item["record"].realm_index,
            item["record"].realm_exp,
        ),
        reverse=True,
    )
    return entries


async def group_power_rank_entries(group_id: str) -> list[dict[str, Any]]:
    entries = await store.get_group_user_records(group_id)
    entries = [
        entry
        for entry in entries
        if entry["record"].root is not None
        or entry["record"].total_exp > 0
        or entry["record"].equipped_artifact
        or entry["record"].equipped_method
        or entry["record"].equipped_array
        or entry["record"].equipped_puppet
        or entry["record"].planted_spirit_plant
    ]
    entries.sort(key=lambda item: battle_power(item["record"]), reverse=True)
    return entries


def format_cultivation_rank(entries: list[dict[str, Any]], title: str) -> str:
    lines = [title]
    if not entries:
        lines.append("暂无入榜修士。")
        return "\n".join(lines)
    for index, entry in enumerate(entries[:10], start=1):
        record = entry["record"]
        nickname = short_name(str(entry.get("nickname") or entry.get("user_id")))
        score = record.total_exp + record.pending_exp
        pending = f"，待领 {record.pending_exp}" if record.pending_exp else ""
        realm = record.realm if record.root else "未入门"
        lines.append(f"{index}. {nickname}：{realm}，修为 {score}{pending}")
    return "\n".join(lines)


def format_power_rank(entries: list[dict[str, Any]], title: str) -> str:
    lines = [title]
    if not entries:
        lines.append("暂无入榜修士。")
        return "\n".join(lines)
    for index, entry in enumerate(entries[:10], start=1):
        record = entry["record"]
        nickname = short_name(str(entry.get("nickname") or entry.get("user_id")))
        artifact = record.equipped_artifact
        puppet = record.equipped_puppet
        artifact_name = str(artifact.get("name")) if artifact else "未装备灵器"
        puppet_name = str(puppet.get("name")) if puppet else "未唤醒傀儡"
        lines.append(f"{index}. {nickname}：战力 {battle_power(record)}，{artifact_name}，{puppet_name}")
    return "\n".join(lines)
