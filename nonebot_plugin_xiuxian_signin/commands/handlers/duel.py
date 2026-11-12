"""普通斗法：申请、群内招式与结算（R-18）。"""
from __future__ import annotations

import asyncio
import time

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher

from ...domain import duel_records, ensure_combat_profile
from ...state import normal_duel_queue, normal_duel_sessions, store
from ..duel import (
    append_normal_duel_action,
    finish_normal_duel,
    group_duel_session,
    send_normal_duel_prepare_messages,
)
from ..formatting import format_duel_result
from ..matchers import duel, normal_duel_apply, normal_duel_chat
from ..panels import finish_panel
from ..parsing import (
    group_member_display_name,
    nickname_from_event,
    normal_duel_action_text,
    parse_duel_target,
    remember_group_member,
)
from ..texts import NORMAL_DUEL_DURATION_SECONDS, NORMAL_DUEL_PREPARE_SECONDS


@normal_duel_apply.handle()
async def handle_normal_duel_apply(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    group_id = str(event.group_id)
    user_id = event.get_user_id()
    if group_duel_session(group_id):
        await finish_panel(matcher, "\u666e\u901a\u6597\u6cd5", "\u672c\u7fa4\u5df2\u6709\u4e00\u573a\u666e\u901a\u6597\u6cd5\u8fdb\u884c\u4e2d\uff0c\u8bf7\u7a0d\u540e\u518d\u7533\u8bf7\u3002", icon="duel")
    name = nickname_from_event(event) or await group_member_display_name(event, user_id)
    queued = normal_duel_queue.get(group_id)
    if queued and float(queued.get("expires_at", 0)) < time.monotonic():
        normal_duel_queue.pop(group_id, None)
        queued = None
    if queued and str(queued.get("user_id")) == user_id:
        await finish_panel(matcher, "\u666e\u901a\u6597\u6cd5", "\u5df2\u5728\u5339\u914d\u961f\u5217\u4e2d\uff0c\u7b49\u5f85\u53e6\u4e00\u4f4d\u4fee\u58eb\u7533\u8bf7\u3002", icon="duel")
    if not queued:
        normal_duel_queue[group_id] = {
            "user_id": user_id,
            "name": name,
            "expires_at": time.monotonic() + 180,
        }
        record = await store.get_user(user_id)
        ensure_combat_profile(record)
        await store.save_user(record)
        await finish_panel(
            matcher,
            "\u666e\u901a\u6597\u6cd5",
            "\u5df2\u8fdb\u5165\u666e\u901a\u6597\u6cd5\u5339\u914d\u961f\u5217\u3002\n\u7fa4\u5185\u53e6\u4e00\u4f4d\u4fee\u58eb\u53d1\u9001\u201c\u7533\u8bf7\u666e\u901a\u6597\u6cd5\u201d\u540e\u5c06\u81ea\u52a8\u5f00\u6218\u3002",
            record,
            icon="duel",
        )
    left_id = str(queued.get("user_id"))
    left_name = str(queued.get("name") or left_id)
    right_id = user_id
    right_name = name
    normal_duel_queue.pop(group_id, None)
    start_at = time.monotonic() + NORMAL_DUEL_PREPARE_SECONDS
    session = {
        "left_id": left_id,
        "right_id": right_id,
        "left_name": left_name,
        "right_name": right_name,
        "created_at": time.monotonic(),
        "start_at": start_at,
        "end_at": start_at + NORMAL_DUEL_DURATION_SECONDS,
        "active": False,
        "actions": {left_id: [], right_id: []},
    }
    normal_duel_sessions[group_id] = session
    asyncio.create_task(send_normal_duel_prepare_messages(session))
    asyncio.create_task(finish_normal_duel(group_id, session))
    await finish_panel(
        matcher,
        "\u666e\u901a\u6597\u6cd5",
        f"\u5339\u914d\u6210\u529f\uff1a{left_name} \u5bf9\u9635 {right_name}\n\u5df2\u8fdb\u51651\u5206\u949f\u51c6\u5907\u671f\uff0c\u7cfb\u7edf\u5c06\u79c1\u804a\u53cc\u65b9\u53d1\u9001\u4fee\u4e3a\u3001\u6218\u6280\u3001\u9635\u76d8\u548c\u7b26\u7b93\u51c6\u5907\u5361\u3002\n\u5f00\u6218\u540e 60 \u79d2\u5185\u53d1\u9001\u6218\u6280\u3001\u795e\u901a\u3001\u8868\u60c5\u6216\u5373\u5174\u53f0\u8bcd\u3002",
        icon="duel",
    )


@normal_duel_chat.handle()
async def handle_normal_duel_chat(event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    text = normal_duel_action_text(event)
    append_normal_duel_action(event, text)


@duel.handle()
async def handle_duel(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    target_id = parse_duel_target(event)
    if not target_id:
        await finish_panel(matcher, "操作提示", "请发送“pk @对方”或“pk QQ号”。", icon="duel")
    if target_id == event.get_user_id():
        await finish_panel(matcher, "操作失败", "不能和自己切磋。", icon="warning")
    attacker = await store.get_user(event.get_user_id())
    defender = await store.get_user(target_id)
    result = duel_records(attacker, defender)
    attacker_name = nickname_from_event(event) or await group_member_display_name(event, event.get_user_id())
    defender_name = await group_member_display_name(event, target_id)
    await finish_panel(matcher, "历练切磋", format_duel_result(attacker_name, defender_name, result), attacker, icon="duel")
