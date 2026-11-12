"""唯一道具归一化（R-18）。

交易、万宝楼、垂钓等多条链路都会产出奖励，唯一道具（全服仅存一件）
必须在这里统一收敛，避免各 handler 各写一份判定。"""
from __future__ import annotations

from typing import Any

from nonebot.adapters.onebot.v11 import MessageEvent

from ..domain import (
    is_unique_reward,
    make_unique_replica,
)
from ..state import store
from .parsing import (
    nickname_from_event,
)


async def enforce_unique_rewards(record, event: MessageEvent) -> str:
    notes = []
    changed = False
    rewards = []
    for reward in record.rewards or []:
        if is_unique_reward(reward):
            claimed, owner = await store.claim_unique_artifact(reward.get("name", ""), record.user_id, nickname_from_event(event) or record.user_id)
            if not claimed or str(owner.get("user_id")) != record.user_id:
                rewards.append(make_unique_replica(reward))
                notes.append(f"{reward.get('name')}\u672c\u4f53\u5df2\u7531 {owner.get('nickname') or owner.get('user_id')} \u6301\u6709\uff0c\u672c\u6b21\u8f6c\u5316\u4e3a\u4eff\u5236\u54c1\u3002")
                changed = True
                continue
        rewards.append(reward)
    if changed:
        record.rewards = rewards
    return "\n".join(notes)


async def normalize_unique_reward_for_user(record, reward: dict[str, Any], event: MessageEvent) -> tuple[dict[str, Any], str]:
    if not is_unique_reward(reward):
        return reward, ""
    claimed, owner = await store.claim_unique_artifact(reward.get("name", ""), record.user_id, nickname_from_event(event) or record.user_id)
    if claimed and str(owner.get("user_id")) == record.user_id:
        return reward, f"\n\u552f\u4e00\u9053\u5177\u5df2\u8bb0\u5f55\u62e5\u6709\u8005\uff1a{owner.get('nickname') or record.user_id}\u3002"
    replica = make_unique_replica(reward)
    return replica, f"\n{reward.get('name')}\u672c\u4f53\u5df2\u7531 {owner.get('nickname') or owner.get('user_id')} \u6301\u6709\uff0c\u672c\u6b21\u8f6c\u5316\u4e3a\u4eff\u5236\u54c1\u3002"
