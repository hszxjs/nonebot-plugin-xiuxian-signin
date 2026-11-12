"""御兽秘境：群聊开局与私聊任务堂（R-18）。"""
from __future__ import annotations

import time

from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
from nonebot.matcher import Matcher

from ...state import beast_realm_private_routes, beast_realm_tables, store
from ..beast import (
    beast_realm_group_key_from_event,
    cleanup_beast_realm_table,
    route_beast_realm_players,
    send_beast_realm_group_report,
    send_beast_realm_leader_panel,
    send_beast_realm_recruit_panels,
)
from ..matchers import beast_realm_group_cmd, beast_realm_private_cmd
from ..panels import BEAST_REALM_ICON, finish_panel, panel_segment
from ..parsing import nickname_from_event, normalized_plain_text, remember_group_member
from ..picmenu import command_hint
from ... import beast_realm as beast_realm_game
from ...runtime_state import interruption_notice


@beast_realm_group_cmd.handle()
async def handle_beast_realm_group(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    text_value = normalized_plain_text(event)
    group_key = beast_realm_group_key_from_event(event)

    # 上次停机时本群还有未结束的御兽局（R-21）：先补一句说明，再照常开新局。
    notice = interruption_notice("beast", group_key)
    if notice:
        await finish_panel(matcher, "御兽秘境", notice, record, icon="warning")

    if text_value == "御兽秘境帮助" or (text_value == "御兽秘境" and group_key not in beast_realm_tables):
        await finish_panel(matcher, "御兽秘境", beast_realm_game.help_text(), record, icon=BEAST_REALM_ICON, footer=command_hint("御兽秘境"))
    if text_value in {"御兽秘境图鉴", "御兽卡牌", "御兽卡牌图鉴"}:
        await finish_panel(matcher, "御兽秘境图鉴", beast_realm_game.catalog_text(), record, icon=BEAST_REALM_ICON, footer=command_hint("御兽秘境"))

    table = beast_realm_tables.get(group_key)
    if table and table.get("phase") == "lobby" and float(table.get("expires_at", 0)) < time.monotonic():
        cleanup_beast_realm_table(group_key)
        table = None

    if beast_realm_game.is_beast_realm_private_entry_command(text_value):
        await finish_panel(matcher, "御兽秘境1V2", "1V2单人PVE仅支持私聊开启，请私聊发送 御兽秘境1V2。", record, icon="warning")

    if text_value.startswith("御兽秘境开局") or text_value.startswith("开启御兽秘境") or text_value in {"御兽秘境PVE", "御兽秘境PVP"}:
        if table:
            await finish_panel(matcher, "御兽秘境", beast_realm_game.status_text(table), record, icon=BEAST_REALM_ICON)
        mode = beast_realm_game.parse_mode(text_value)
        if mode == "solo_pve":
            await finish_panel(matcher, "御兽秘境1V2", "1V2单人PVE仅支持私聊开启，请私聊发送 御兽秘境1V2。", record, icon="warning")
        table = beast_realm_game.create_table(group_key, user_id, nickname_from_event(event) or f"QQ {user_id}", mode)
        beast_realm_tables[group_key] = table
        route_beast_realm_players(table)
        host_player = beast_realm_game.table_player(table, user_id)
        sent = await send_beast_realm_leader_panel(table, host_player) if host_player else False
        hint = "\n\n峰主候选已发送到私聊，请发送 选择峰主 1/2/3。" if sent else "\n\n峰主候选私聊发送失败，请检查好友或临时会话权限；也可私聊发送 峰主 查看。"
        await finish_panel(matcher, "御兽秘境开局", beast_realm_game.lobby_text(table) + hint, record, icon=BEAST_REALM_ICON)

    if not table:
        await finish_panel(matcher, "御兽秘境", beast_realm_game.help_text(), record, icon=BEAST_REALM_ICON, footer=command_hint("御兽秘境"))

    if text_value in {"御兽秘境", "御兽秘境状态"}:
        await finish_panel(matcher, "御兽秘境状态", beast_realm_game.status_text(table), record, icon=BEAST_REALM_ICON, footer=command_hint("御兽秘境"))

    if text_value == "加入御兽秘境":
        ok, message = beast_realm_game.add_player(table, user_id, nickname_from_event(event) or f"QQ {user_id}")
        if ok:
            route_beast_realm_players(table)
            player = beast_realm_game.table_player(table, user_id)
            sent = await send_beast_realm_leader_panel(table, player) if player else False
            message += "\n\n峰主候选已发送到私聊，请发送 选择峰主 1/2/3。" if sent else "\n\n峰主候选私聊发送失败，请检查好友或临时会话权限；也可私聊发送 峰主 查看。"
        await finish_panel(matcher, "加入御兽秘境" if ok else "操作失败", message, record, icon=BEAST_REALM_ICON if ok else "warning")

    if text_value == "退出御兽秘境":
        ok, message = beast_realm_game.remove_player(table, user_id)
        if beast_realm_private_routes.get(user_id) == group_key:
            beast_realm_private_routes.pop(user_id, None)
        if ok and not beast_realm_game.active_human_players(table):
            cleanup_beast_realm_table(group_key)
        await finish_panel(matcher, "退出御兽秘境" if ok else "操作失败", message, record, icon=BEAST_REALM_ICON if ok else "warning")

    if text_value == "结束御兽秘境":
        player = beast_realm_game.table_player(table, user_id)
        if str(table.get("host_id")) != user_id and not player:
            await finish_panel(matcher, "操作失败", "只有峰主或本局修士可以结束御兽秘境。", record, icon="warning")
        cleanup_beast_realm_table(group_key)
        await finish_panel(matcher, "御兽秘境", "本群御兽秘境已结束。", record, icon=BEAST_REALM_ICON)

    if text_value == "开始御兽秘境":
        if str(table.get("host_id")) != user_id:
            await finish_panel(matcher, "操作失败", "只有峰主可以开始御兽秘境。", record, icon="warning")
        ok, message = beast_realm_game.start_table(table)
        if not ok:
            await finish_panel(matcher, "操作失败", message, record, icon="warning")
        await send_beast_realm_recruit_panels(table)
        await finish_panel(matcher, "御兽秘境", message, record, icon=BEAST_REALM_ICON)

    if text_value == "御兽结算":
        player = beast_realm_game.table_player(table, user_id)
        if str(table.get("host_id")) != user_id and not player:
            await finish_panel(matcher, "操作失败", "只有峰主或本局修士可以强制结算。", record, icon="warning")
        if table.get("phase") != "recruit":
            await finish_panel(matcher, "操作失败", "当前不在招募阶段。", record, icon="warning")
        report = beast_realm_game.resolve_round(table)
        await send_beast_realm_group_report(table, "御兽秘境战报", report)
        if table.get("phase") == "ended":
            cleanup_beast_realm_table(group_key)
        else:
            await send_beast_realm_recruit_panels(table)
        await matcher.finish()

    await finish_panel(matcher, "御兽秘境状态", beast_realm_game.status_text(table), record, icon=BEAST_REALM_ICON, footer=command_hint("御兽秘境"))


@beast_realm_private_cmd.handle()
async def handle_beast_realm_private(matcher: Matcher, event: PrivateMessageEvent) -> None:
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    text_value = normalized_plain_text(event)
    group_key = beast_realm_private_routes.get(user_id)
    table = beast_realm_tables.get(group_key or "")
    if (not group_key or not table) and beast_realm_game.is_beast_realm_private_entry_command(text_value):
        group_key = beast_realm_game.private_key(user_id)
        table = beast_realm_game.create_table(group_key, user_id, nickname_from_event(event) or f"QQ {user_id}", "solo_pve")
        beast_realm_tables[group_key] = table
        route_beast_realm_players(table)
        player = beast_realm_game.table_player(table, user_id)
        await finish_panel(matcher, "御兽秘境1V2", beast_realm_game.leader_choice_text(player), record, icon=BEAST_REALM_ICON, footer="选择峰主后发送“开始御兽秘境”，全流程在私聊完成。")
    if not group_key or not table or table.get("phase") not in {"lobby", "recruit"}:
        if group_key and not table:
            cleanup_beast_realm_table(group_key)
        await finish_panel(matcher, "御兽秘境", "当前没有可操作的御兽秘境。", record, icon="warning")
    player = beast_realm_game.table_player(table, user_id)
    if not player or player.get("bot"):
        await finish_panel(matcher, "御兽秘境", "没有找到你的御兽秘境席位。", record, icon="warning")

    was_ready = bool(player.get("ready"))
    if table.get("phase") == "lobby" and str(table.get("mode")) == "solo_pve" and text_value == "开始御兽秘境":
        ok, message = beast_realm_game.start_table(table)
        if not ok:
            await finish_panel(matcher, "操作失败", message, record, icon="warning")
        await matcher.send(panel_segment("御兽秘境1V2", message, record, icon=BEAST_REALM_ICON))
        await send_beast_realm_recruit_panels(table)
        return

    title, content = beast_realm_game.private_action(table, player, text_value)
    await matcher.send(panel_segment(title, content, record, icon=BEAST_REALM_ICON if title != "操作失败" else "warning"))
    if table.get("phase") == "lobby":
        return

    ready_command = text_value in {"完成招募", "结束招募", "准备"}
    if ready_command and not was_ready and beast_realm_game.all_humans_ready(table):
        report = beast_realm_game.resolve_round(table)
        if str(table.get("mode")) == "solo_pve":
            await matcher.send(panel_segment("御兽秘境战报", report, record, icon=BEAST_REALM_ICON))
        else:
            await send_beast_realm_group_report(table, "御兽秘境战报", report)
        if table.get("phase") == "ended":
            cleanup_beast_realm_table(group_key)
            return
        await send_beast_realm_recruit_panels(table)
