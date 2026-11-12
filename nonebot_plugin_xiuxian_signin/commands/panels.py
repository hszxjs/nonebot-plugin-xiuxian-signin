"""面板渲染与发送（R-18）。

统一的「标题 + 分段内容 + 立绘/头像」出口：群聊面板、私聊面板、签到场次图片。
其他子模块只应通过本模块发消息，避免各自拼接渲染参数。"""
from __future__ import annotations

import re

from datetime import date, timedelta
from io import BytesIO

from nonebot import get_bot, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, MessageSegment
from nonebot.matcher import Matcher

from ..beast_realm_cards import render_beast_realm_panel
from ..cards import (
    render_fishing_card,
    render_in_thread,
    render_signin_calendar_card,
    render_signin_card,
    render_text_panel,
)
from ..domain import SigninResult
from ..net import fetch_avatar
from ..state import config, local_today
from .parsing import nickname_from_event
from .texts import MAKEUP_SIGN_PREFIXES, SIGNIN_CALENDAR_TEXTS


BEAST_REALM_ICON = "beast_realm"

def panel_accent(record=None) -> str:
    root = getattr(record, "root", None)
    return getattr(root, "color", "#3589d8") if root else "#3589d8"


def panel_segment(
    title: str,
    content: str | list[str],
    record=None,
    subtitle: str = "",
    icon: str = "scroll",
    footer: str = "",
) -> MessageSegment:
    if icon == BEAST_REALM_ICON:
        image_bytes = render_beast_realm_panel(
            title=title,
            content=content,
            subtitle=subtitle,
            width=config.xiuxian_signin_image_width,
            footer=footer,
        )
    else:
        image_bytes = render_text_panel(
            title=title,
            content=content,
            subtitle=subtitle,
            icon=icon,
            accent=panel_accent(record),
            width=config.xiuxian_signin_image_width,
            footer=footer,
        )
    return MessageSegment.image(BytesIO(image_bytes))


async def send_panel(
    matcher: Matcher,
    title: str,
    content: str | list[str],
    record=None,
    subtitle: str = "",
    icon: str = "scroll",
    footer: str = "",
) -> None:
    segment = await render_in_thread(panel_segment, title, content, record, subtitle, icon, footer)
    await matcher.send(segment)


async def finish_panel(
    matcher: Matcher,
    title: str,
    content: str | list[str],
    record=None,
    subtitle: str = "",
    icon: str = "scroll",
    footer: str = "",
) -> None:
    segment = await render_in_thread(panel_segment, title, content, record, subtitle, icon, footer)
    await matcher.finish(segment)


async def send_private_panel(
    user_id: str,
    title: str,
    content: str | list[str],
    record=None,
    subtitle: str = "",
    icon: str = "scroll",
    footer: str = "",
) -> bool:
    try:
        segment = await render_in_thread(panel_segment, title, content, record, subtitle, icon, footer)
        await get_bot().send_private_msg(
            user_id=int(user_id),
            message=segment,
        )
        return True
    except Exception as exc:
        logger.debug(f"发送私聊面板失败: {user_id} {title} {exc}")
        return False


async def finish_private_or_current_panel(
    matcher: Matcher,
    event: MessageEvent,
    title: str,
    content: str | list[str],
    record=None,
    subtitle: str = "",
    icon: str = "scroll",
    footer: str = "",
    group_success: str = "已通过私聊发送，请查看私聊。",
) -> None:
    if isinstance(event, GroupMessageEvent):
        sent = await send_private_panel(event.get_user_id(), title, content, record, subtitle, icon, footer)
        if sent:
            await finish_panel(matcher, title, group_success, record, icon=icon)
        await finish_panel(matcher, "私聊发送失败", f"{title}已生成，但私聊发送失败，请检查好友或临时会话权限。", record, icon="warning")
    await finish_panel(matcher, title, content, record, subtitle=subtitle, icon=icon, footer=footer)


async def send_image(matcher: Matcher, image_bytes: bytes) -> None:
    await matcher.send(MessageSegment.image(BytesIO(image_bytes)))


async def build_signin_image(event: MessageEvent, result: SigninResult) -> bytes:
    avatar = await fetch_avatar(event.get_user_id())
    return await render_in_thread(
        render_signin_card,
        result=result,
        nickname=nickname_from_event(event),
        avatar_bytes=avatar,
        width=config.xiuxian_signin_image_width,
    )


async def build_signin_calendar_image(
    user_id: str,
    record,
    nickname: str,
    year: int,
    month: int,
) -> bytes:
    """构造签到日历图（含头像）。"""
    avatar = await fetch_avatar(user_id)
    return await render_in_thread(
        render_signin_calendar_card,
        history=record.sign_history or {},
        nickname=nickname,
        avatar_bytes=avatar,
        year=year,
        month=month,
        today=local_today(),
        width=config.xiuxian_signin_image_width,
    )


def parse_calendar_target(text: str) -> tuple[int, int] | None:
    """解析日历翻月参数，返回 (year, month)；无参数返回当月，非法返回 None。"""
    today = local_today()
    normalized = text.strip()
    for word in sorted(SIGNIN_CALENDAR_TEXTS, key=len, reverse=True):
        if normalized.startswith(word):
            normalized = normalized[len(word):].strip()
            break
    if not normalized:
        return today.year, today.month
    if normalized in {"上月", "上个月", "前一个月"}:
        first = today.replace(day=1)
        prev = first - timedelta(days=1)
        return prev.year, prev.month
    if normalized in {"下月", "下个月"}:
        first = today.replace(day=1)
        nxt = (first + timedelta(days=32)).replace(day=1)
        return nxt.year, nxt.month
    match = re.fullmatch(r"(\d{4})[-/年](\d{1,2})月?", normalized)
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12:
            return year, month
    match = re.fullmatch(r"(\d{1,2})月?", normalized)
    if match:
        month = int(match.group(1))
        if 1 <= month <= 12:
            return today.year, month
    return None


def parse_makeup_target(text: str) -> date | None:
    """解析补签目标日期：支持「补签 15」「补签 10月15」；非法返回 None。"""
    normalized = text.strip()
    for prefix in MAKEUP_SIGN_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
            break
    today = local_today()
    match = re.fullmatch(r"(\d{1,2})月(\d{1,2})日?", normalized)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        try:
            return date(today.year, month, day)
        except ValueError:
            return None
    match = re.fullmatch(r"(\d{1,2})日?", normalized)
    if match:
        day = int(match.group(1))
        try:
            return date(today.year, today.month, day)
        except ValueError:
            return None
    return None


async def build_fishing_image(
    event: MessageEvent,
    record,
    rewards,
) -> bytes:
    avatar = await fetch_avatar(event.get_user_id())
    return await render_in_thread(
        render_fishing_card,
        record=record,
        rewards=rewards,
        nickname=nickname_from_event(event),
        avatar_bytes=avatar,
        width=config.xiuxian_signin_image_width,
    )
