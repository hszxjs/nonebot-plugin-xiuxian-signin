"""秘境：群聊/私聊入口、天机秘境与结果播报（R-18）。"""
from __future__ import annotations

from io import BytesIO

from nonebot import get_bot, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, MessageSegment, PrivateMessageEvent
from nonebot.exception import ActionFailed, NetworkError
from nonebot.matcher import Matcher

from ...domain.rewards import reward_count_by_names
from ...mystic_cards import render_no_token_panel
from ...mystic_dungeon import DungeonMode, DungeonRisk, active_mystic_theme_ids
from ...mystic_runtime import DungeonEntryOffer, MysticCommandResult
from ...state import (
    config,
    local_today,
    mystic_catalog,
    mystic_coordinator,
    store,
)
from ..duel import _mystic_prepare_info, send_mystic_prepare_cards
from ..mystic_result import finish_mystic_command_result
from ..matchers import mystic_group_cmd, mystic_private_cmd, tianji_mystic_cmd
from ..panels import finish_panel
from ..parsing import group_member_display_name, normalized_plain_text, remember_group_member


@mystic_group_cmd.handle()
async def handle_mystic_group(
    matcher: Matcher,
    event: GroupMessageEvent,
) -> None:
    user_id = event.get_user_id()
    nickname = await group_member_display_name(event, user_id)
    result = await mystic_coordinator.handle_group(
        str(event.group_id),
        user_id,
        normalized_plain_text(event),
        nickname=nickname,
    )
    await finish_mystic_command_result(matcher, user_id, result)


@mystic_private_cmd.handle()
async def handle_mystic_private(
    matcher: Matcher,
    event: PrivateMessageEvent,
) -> None:
    user_id = event.get_user_id()
    route = await mystic_coordinator.resolve_private_context(user_id)
    if route is None:
        await finish_panel(matcher, "秘境", "当前没有可操作的秘境。", icon="warning")
        return
    text = normalized_plain_text(event)
    if text in {"秘境状态", "秘境地图"}:
        result = await mystic_coordinator.handle_group(
            route.source_group_id,
            user_id,
            text,
        )
    else:
        result = await mystic_coordinator.handle_private(
            user_id,
            text,
            action_id=f"onebot:{event.message_id}",
        )
    await finish_mystic_command_result(matcher, user_id, result)


@tianji_mystic_cmd.handle()
async def handle_tianji_mystic(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    if not isinstance(event, GroupMessageEvent):
        await finish_panel(
            matcher,
            "天机秘境",
            "天机秘境需要在群聊中开启。",
            record,
            icon="warning",
        )
        return
    themes = sorted(
        (
            theme
            for theme in mystic_catalog.themes.values()
            if theme.risk is DungeonRisk.NORMAL
        ),
        key=lambda theme: theme.theme_id,
    )
    theme = themes[
        sum(f"{event.group_id}:{event.get_user_id()}:{local_today()}".encode("utf-8"))
        % len(themes)
    ]
    offer = DungeonEntryOffer(
        mode=DungeonMode.SOLO,
        risk=DungeonRisk.NORMAL,
        theme_id=theme.theme_id,
        boss_realm_index=record.realm_index,
        insight=True,
    )
    try:
        result = await mystic_coordinator.create_from_offer(
            str(event.group_id),
            event.get_user_id(),
            offer,
        )
    except (LookupError, PermissionError, ValueError) as exc:
        await finish_panel(matcher, "天机秘境", str(exc), record, icon="warning")
        return
    await finish_mystic_command_result(matcher, event.get_user_id(), result)
