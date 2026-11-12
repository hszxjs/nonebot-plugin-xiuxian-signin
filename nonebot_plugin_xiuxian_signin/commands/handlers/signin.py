"""签到、签到日历与补签（R-18）。"""
from __future__ import annotations

import time

from nonebot import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, PrivateMessageEvent
from nonebot.exception import ActionFailed, NetworkError
from nonebot.matcher import Matcher

from ...domain import apply_signin, daily_tasks_text, makeup_sign, reward_display_name
from ...state import local_today, pending_fishing_users, store
from ..formatting import format_newbie_tutorial_text
from ..matchers import makeup_sign_cmd, signin, signin_calendar
from ..panels import (
    build_signin_calendar_image,
    build_signin_image,
    finish_panel,
    parse_calendar_target,
    parse_makeup_target,
    send_image,
    send_panel,
    send_private_panel,
)
from ..parsing import nickname_from_event, normalized_plain_text, remember_group_member
from ..texts import PENDING_FISHING_TTL


@signin.handle()
async def handle_signin(matcher: Matcher, event: MessageEvent) -> None:
    user_id = event.get_user_id()
    await remember_group_member(event)
    record = await store.get_user(user_id)
    result = apply_signin(record, local_today())
    await store.save_user(result.record)

    if result.is_first and not result.already_signed:
        root = result.record.root
        await send_panel(matcher, "天赋抽取", "检测到宿主首次签到，正在进行天赋抽取。", result.record, icon="realm")
        if root:
            await send_panel(
                matcher,
                "灵根觉醒",
                f"叮！抽到{root.display_name}，{result.record.realm}进度{result.record.realm_exp}/{result.record.progress_required}",
                result.record,
                icon="realm",
            )
        if isinstance(event, GroupMessageEvent):
            await send_panel(
                matcher,
                "私聊提醒",
                "首次入门完成。若要接收每日任务、秘境战报等私聊提醒，并打开新手教程，请先主动私聊 Bot 发送任意消息或“新手教程”。",
                result.record,
                icon="warning",
            )

    if result.pending_exp_applied:
        await send_panel(matcher, "日榜奖励", f"日榜暂存修为已汇入丹田，修炼进度+{result.pending_exp_applied}", result.record, icon="rank")

    if result.breakthrough_reward:
        await send_panel(matcher, "瓶颈机缘", f"额外获得 {reward_display_name(result.breakthrough_reward)}。", result.record, icon="breakthrough")

    if result.encounter and result.encounter.happened:
        await send_panel(matcher, "今日奇遇", result.encounter.message, result.record, icon="mystic")

    image = await build_signin_image(event, result)
    await send_image(matcher, image)

    if not result.already_signed:
        # 签到成功后附上当月签到日历（仅当天首次签到发，重复签到不重发）
        try:
            today = local_today()
            calendar_image = await build_signin_calendar_image(
                user_id,
                result.record,
                nickname_from_event(event),
                today.year,
                today.month,
            )
            await send_image(matcher, calendar_image)
        except (ActionFailed, NetworkError, OSError, RuntimeError, ValueError):
            logger.debug(f"签到日历发送失败: {user_id}")

    if result.is_first and not result.already_signed and isinstance(event, PrivateMessageEvent):
        await send_panel(
            matcher,
            "新手教程",
            format_newbie_tutorial_text(result.record, nickname_from_event(event)),
            result.record,
            icon="scroll",
            footer="以后在私聊发送“新手教程”，可随时重新打开这份引导。",
        )

    if not result.already_signed and result.daily_tasks:
        task_content = daily_tasks_text(result.record, local_today())
        if isinstance(event, GroupMessageEvent):
            sent = await send_private_panel(user_id, "每日任务", task_content, result.record, icon="task")
            await send_panel(
                matcher,
                "每日任务",
                "今日任务已接取，任务详情已通过私聊发送。" if sent else "今日任务已接取，但私聊发送失败，请检查好友或临时会话权限。",
                result.record,
                icon="task" if sent else "warning",
            )
        else:
            await send_panel(matcher, "每日任务", task_content, result.record, icon="task")

    if not result.already_signed and result.record.fishing_chances > 0:
        pending_fishing_users[user_id] = time.monotonic() + PENDING_FISHING_TTL
        await send_panel(
            matcher,
            "灵河垂钓",
            f"检测到宿主有 {result.record.fishing_chances} 次灵河垂钓次数，是否垂钓？可累加进行 10 连抽。回复 是/好/y/十连。",
            result.record,
            icon="fishing",
        )


@signin_calendar.handle()
async def handle_signin_calendar(matcher: Matcher, event: MessageEvent) -> None:
    user_id = event.get_user_id()
    await remember_group_member(event)
    record = await store.get_user(user_id)
    target = parse_calendar_target(normalized_plain_text(event))
    if target is None:
        await finish_panel(
            matcher,
            "签到日历",
            "月份格式不对，可用「签到日历」「签到日历 上月」「签到日历 2026-09」。",
            record,
            icon="warning",
        )
    year, month = target
    image = await build_signin_calendar_image(
        user_id,
        record,
        nickname_from_event(event),
        year,
        month,
    )
    await send_image(matcher, image)


@makeup_sign_cmd.handle()
async def handle_makeup_sign(matcher: Matcher, event: MessageEvent) -> None:
    user_id = event.get_user_id()
    await remember_group_member(event)
    record = await store.get_user(user_id)
    if record.root is None:
        await finish_panel(matcher, "尚未入门", "尚未踏入修行路，发送“签到”即可抽取灵根。", record, icon="realm")
    target = parse_makeup_target(normalized_plain_text(event))
    if target is None:
        await finish_panel(
            matcher,
            "补签",
            "用法：补签 15（补本月 15 日）或 补签 10月15。",
            record,
            icon="warning",
        )
    today = local_today()
    success, message = makeup_sign(record, target, today)
    if success:
        await store.save_user(record)
    # 无论成败都回一张当月日历，让玩家直接看到结果（成功日会盖青色补签印）
    await send_panel(matcher, "补签" if success else "补签失败", message, record, icon="realm" if success else "warning")
    image = await build_signin_calendar_image(
        user_id,
        record,
        nickname_from_event(event),
        today.year,
        today.month,
    )
    await send_image(matcher, image)
