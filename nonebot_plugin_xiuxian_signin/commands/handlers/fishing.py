"""灵河垂钓：触发、续接与结算（R-18）。"""
from __future__ import annotations

from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.matcher import Matcher

from ...domain import CANCEL_WORDS, apply_fishing, fishing_count_from_text
from ...state import pending_fishing_users, store
from ..matchers import fishing, fishing_reply
from ..panels import build_fishing_image, finish_panel, send_image, send_panel
from ..parsing import normalized_plain_text, parse_fishing_arg, remember_group_member
from ..rewards import enforce_unique_rewards


@fishing.handle()
async def handle_fishing_command(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    if record.fishing_chances <= 0:
        await finish_panel(matcher, "灵河垂钓", "宿主暂无灵河垂钓次数，每次签到可获得 1 次。", record, icon="fishing")
    text = normalized_plain_text(event)
    arg = parse_fishing_arg(text) or ""
    count = fishing_count_from_text(arg, record.fishing_chances)
    await do_fishing(matcher, event, count)


@fishing_reply.handle()
async def handle_fishing_reply(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    user_id = event.get_user_id()
    text = normalized_plain_text(event).lower()
    record = await store.get_user(user_id)
    if text in CANCEL_WORDS:
        pending_fishing_users.pop(user_id, None)
        await finish_panel(matcher, "灵河垂钓", "已收起钓竿，灵河垂钓次数仍为你保留。", record, icon="fishing")
    count = fishing_count_from_text(text, record.fishing_chances)
    await do_fishing(matcher, event, count)


async def do_fishing(matcher: Matcher, event: MessageEvent, count: int) -> None:
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    if record.fishing_chances <= 0:
        pending_fishing_users.pop(user_id, None)
        await finish_panel(matcher, "灵河垂钓", "宿主暂无灵河垂钓次数。", record, icon="fishing")
    count = max(1, min(count, record.fishing_chances, 10))
    await send_panel(matcher, "灵河垂钓", f"正在为宿主进行{count}次垂钓。", record, icon="fishing")
    rewards = apply_fishing(record, count)
    await enforce_unique_rewards(record, event)
    pending_fishing_users.pop(user_id, None)
    await store.save_user(record)
    image = await build_fishing_image(event, record, rewards)
    await send_image(matcher, image)
