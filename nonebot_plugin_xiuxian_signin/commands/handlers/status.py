"""个人状态与成长：面板、突破/散功、修炼路线、每日任务、战力、历练（R-18）。"""
from __future__ import annotations

import random

from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.matcher import Matcher

from ..matchers import dual_cultivation_cmd
from ..parsing import at_user_ids, group_member_display_name
from ...cards import render_adventure_card, render_in_thread
from ...domain import (
    apply_dual_cultivation,
    SigninResult,
    breakthrough_realm,
    breakthrough_status,
    choose_cultivation_route,
    choose_evil_cultivation,
    choose_faction_identity,
    complete_daily_task,
    daily_tasks_text,
    regress_cultivation,
    route_status_text,
)
from ...state import config, local_today, store
from ..formatting import format_power_status
from ..matchers import (
    adventure,
    breakthrough_cmd,
    power_status,
    route_cmd,
    status,
    task_cmd,
)
from ..panels import build_signin_image, finish_panel, finish_private_or_current_panel, send_image
from ..parsing import (
    nickname_from_event,
    normalized_plain_text,
    parse_prefixed_index,
    parse_prefixed_name,
    remember_group_member,
)
from ..picmenu import command_hint
from ..texts import (
    EVIL_QUIT_TEXTS,
    EVIL_SELECT_TEXTS,
    IDENTITY_SELECT_PREFIXES,
    ROUTE_SELECT_PREFIXES,
    ROUTE_TEXTS,
    TASK_COMPLETE_PREFIXES,
    TASK_TEXTS,
)


@breakthrough_cmd.handle()
async def handle_breakthrough(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    if text in {"\u6563\u529f", "\u91cd\u4fee", "\u81ea\u5e9f\u4fee\u4e3a"}:
        success, message = regress_cultivation(record)
        if success:
            await store.save_user(record)
        await finish_panel(
            matcher,
            "\u6563\u529f\u91cd\u4fee" if success else "\u6563\u529f\u5931\u8d25",
            message,
            record,
            icon="breakthrough" if success else "warning",
        )
    if text in {"\u7a81\u7834", "\u5883\u754c\u7a81\u7834", "\u7834\u5883"}:
        success, message = breakthrough_realm(record)
        if success:
            await store.save_user(record)
        await finish_panel(
            matcher,
            "\u5883\u754c\u7a81\u7834" if success else "\u7a81\u7834\u72b6\u6001",
            message,
            record,
            icon="breakthrough" if success else "warning",
        )
    await finish_panel(matcher, "\u7a81\u7834\u72b6\u6001", breakthrough_status(record), record, icon="breakthrough", footer=command_hint("修为与突破"))


@route_cmd.handle()
async def handle_route(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    if text in ROUTE_TEXTS:
        await finish_panel(matcher, "修炼路线", route_status_text(record), record, icon="token", footer=command_hint("路线与身份"))
    route_name = parse_prefixed_name(text, ROUTE_SELECT_PREFIXES)
    if route_name is not None:
        if not route_name:
            await finish_panel(matcher, "修炼路线", route_status_text(record), record, icon="token", footer=command_hint("路线与身份"))
        success, message = choose_cultivation_route(record, route_name)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "修炼路线" if success else "选择失败", message, record, icon="token" if success else "warning")
    identity_name = parse_prefixed_name(text, IDENTITY_SELECT_PREFIXES)
    if identity_name is not None:
        if not identity_name:
            await finish_panel(matcher, "身份令牌", route_status_text(record), record, icon="token", footer=command_hint("路线与身份"))
        success, message = choose_faction_identity(record, identity_name)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "身份令牌" if success else "选择失败", message, record, icon="token" if success else "warning")
    if text in EVIL_SELECT_TEXTS or text in EVIL_QUIT_TEXTS:
        success, message = choose_evil_cultivation(record, text in EVIL_SELECT_TEXTS)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "邪修路线", message, record, icon="token")
    await finish_panel(matcher, "修炼路线", route_status_text(record), record, icon="token", footer=command_hint("路线与身份"))


@task_cmd.handle()
async def handle_daily_task(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    today = local_today()
    if text in TASK_TEXTS:
        content = daily_tasks_text(record, today)
        await store.save_user(record)
        await finish_private_or_current_panel(
            matcher,
            event,
            "每日任务",
            content,
            record,
            icon="task",
            group_success="今日任务已接取，任务详情已通过私聊发送。",
        )
    task_index = parse_prefixed_index(text, TASK_COMPLETE_PREFIXES)
    if task_index is None:
        content = daily_tasks_text(record, today)
        await store.save_user(record)
        await finish_private_or_current_panel(
            matcher,
            event,
            "每日任务",
            content,
            record,
            icon="task",
            group_success="今日任务已接取，任务详情已通过私聊发送。",
        )
    success, message = complete_daily_task(record, task_index, today)
    content = message
    if success:
        content = f"{message}\n\n{daily_tasks_text(record, today)}"
    await store.save_user(record)
    await finish_private_or_current_panel(
        matcher,
        event,
        "每日任务完成" if success else "任务失败",
        content,
        record,
        icon="task" if success else "warning",
        group_success="任务结算结果已通过私聊发送。" if success else "任务处理结果已通过私聊发送。",
    )


@status.handle()
async def handle_status(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    if record.root is None:
        await finish_panel(matcher, "尚未入门", "尚未踏入修行路，发送“签到”即可抽取灵根。", record, icon="realm")
    result = SigninResult(record=record, is_first=False, already_signed=True)
    image = await build_signin_image(event, result)
    await send_image(matcher, image)


@power_status.handle()
async def handle_power_status(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "个人战力", format_power_status(record, nickname_from_event(event)), record, icon="power", footer=command_hint("灵器与战力"))


@adventure.handle()
async def handle_adventure(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    image = await render_in_thread(
        render_adventure_card,
        record=record,
        nickname=nickname_from_event(event),
        width=config.xiuxian_signin_image_width,
    )
    await send_image(matcher, image)


@dual_cultivation_cmd.handle()
async def handle_dual_cultivation(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    text = normalized_plain_text(event)
    target_id = None
    targets = at_user_ids(event)
    if targets:
        target_id = targets[0]
    elif text == "随机双修":
        members = await store.get_group_user_records(str(event.group_id))
        candidates = [entry for entry in members if str(entry.get("user_id")) != event.get_user_id()]
        if candidates:
            target_id = str(random.choice(candidates).get("user_id"))
    if not target_id:
        await finish_panel(matcher, "双修", "请发送“双修 @群成员”或“随机双修”。", icon="token")
    if target_id == event.get_user_id():
        await finish_panel(matcher, "双修失败", "不可与自己双修。", icon="warning")
    actor = await store.get_user(event.get_user_id())
    target = await store.get_user(target_id)
    success, message = apply_dual_cultivation(actor, target, local_today())
    if success:
        await store.save_user(actor)
        await store.save_user(target)
    actor_name = nickname_from_event(event) or await group_member_display_name(event, event.get_user_id())
    target_name = await group_member_display_name(event, target_id)
    await finish_panel(
        matcher,
        "合欢宗双修" if success else "双修失败",
        f"{actor_name} 与 {target_name}\n{message}",
        actor,
        icon="token" if success else "warning",
    )
