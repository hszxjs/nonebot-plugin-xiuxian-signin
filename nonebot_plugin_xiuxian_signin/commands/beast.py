"""御兽秘境的分组播报（R-18）。

群聊键解析、峰主面板、招募面板与战报播报。"""
from __future__ import annotations

from typing import Any

from nonebot import get_bot, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from ..state import beast_realm_private_routes, beast_realm_tables, store
from .panels import BEAST_REALM_ICON, panel_segment, send_private_panel
from .. import beast_realm as beast_realm_game


def beast_realm_group_key_from_event(event: GroupMessageEvent) -> str:
    return beast_realm_game.group_key(str(event.group_id))


def beast_realm_group_id_from_key(group_key: str) -> str:
    return str(group_key).split(":", 1)[-1]


def cleanup_beast_realm_table(group_key: str) -> None:
    table = beast_realm_tables.pop(group_key, None)
    if not table:
        return
    for player in beast_realm_game.active_human_players(table):
        user_id = str(player.get("id"))
        if beast_realm_private_routes.get(user_id) == group_key:
            beast_realm_private_routes.pop(user_id, None)


def route_beast_realm_players(table: dict[str, Any]) -> None:
    group_key = str(table.get("group_id"))
    for player in beast_realm_game.active_human_players(table):
        beast_realm_private_routes[str(player.get("id"))] = group_key


async def send_beast_realm_leader_panel(table: dict[str, Any], player: dict[str, Any]) -> bool:
    route_beast_realm_players(table)
    user_id = str(player.get("id"))
    record = await store.get_user(user_id)
    return await send_private_panel(
        user_id,
        "峰主选择",
        beast_realm_game.leader_choice_text(player),
        record,
        icon=BEAST_REALM_ICON,
        footer="开局前发送“选择峰主 1/2/3”。所有修士选定峰主后，群聊由峰主发送“开始御兽秘境”。",
    )


async def send_beast_realm_recruit_panels(table: dict[str, Any]) -> None:
    route_beast_realm_players(table)
    group_key = str(table.get("group_id"))
    mode = str(table.get("mode", "pve"))
    footer = (
        "私聊完成招募后发送“完成招募”，会立即结算本回合1V2战报。"
        if mode == "solo_pve"
        else "私聊完成招募后发送“完成招募”，全员准备后群聊自动播报战报。"
    )
    failed: list[str] = []
    for player in beast_realm_game.live_human_players(table):
        user_id = str(player.get("id"))
        record = await store.get_user(user_id)
        sent = await send_private_panel(
            user_id,
            "任务堂",
            beast_realm_game.player_text(player, table),
            record,
            icon=BEAST_REALM_ICON,
            footer=footer,
        )
        if not sent:
            failed.append(str(player.get("name") or user_id))
    if failed and group_key.startswith("group:"):
        try:
            await get_bot().send_group_msg(
                group_id=int(beast_realm_group_id_from_key(group_key)),
                message=panel_segment(
                    "任务堂私聊失败",
                    "、".join(failed) + " 的任务堂私聊发送失败，请检查好友或临时会话权限。",
                    icon="warning",
                ),
            )
        except Exception:
            logger.debug("发送任务堂私聊失败提示失败")


async def send_beast_realm_group_report(table: dict[str, Any], title: str, content: str) -> None:
    group_key = str(table.get("group_id"))
    if not group_key.startswith("group:"):
        return
    await get_bot().send_group_msg(
        group_id=int(beast_realm_group_id_from_key(group_key)),
        message=panel_segment(title, content, icon=BEAST_REALM_ICON),
    )
