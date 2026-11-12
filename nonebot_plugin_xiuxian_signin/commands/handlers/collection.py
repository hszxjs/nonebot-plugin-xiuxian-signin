"""查询类命令：帮助、新手教程、图鉴、各类列表与排行（R-18）。"""
from __future__ import annotations

from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, PrivateMessageEvent
from nonebot.matcher import Matcher

from ...domain import (
    acquired_root_text,
    apply_chat_cultivation,
    ensure_combat_profile,
    format_method_detail,
    learn_special_ability,
    refine_artifact_root,
    refine_dan_root,
    special_ability_catalog_text,
    special_ability_list_text,
)
from ...state import local_today, store
from ..formatting import (
    format_array_list,
    format_artifact_list,
    format_catalog_text,
    format_help_text,
    format_item_list,
    format_method_list,
    format_newbie_tutorial_text,
    format_plant_list,
    format_puppet_list,
)
from ..matchers import (
    acquired_root_cmd,
    array_list,
    artifact_list,
    catalog_cmd,
    chat_rank_counter,
    cultivation_rank,
    help_cmd,
    item_list,
    method_detail_cmd,
    method_list,
    newbie_tutorial_cmd,
    plant_list,
    power_rank,
    puppet_list,
    special_ability_cmd,
    special_ability_learn_cmd,
)
from ..panels import finish_panel
from ..parsing import (
    nickname_from_event,
    normalized_plain_text,
    parse_acquired_root_command,
    parse_prefixed_index,
    remember_group_member,
)
from ..picmenu import command_hint
from ..ranking import (
    format_cultivation_rank,
    format_power_rank,
    group_cultivation_rank_entries,
    group_power_rank_entries,
)
from ..texts import (
    METHOD_DETAIL_PREFIXES,
    SPECIAL_ABILITY_CATALOG_TEXTS,
    SPECIAL_ABILITY_LEARN_PREFIXES,
)


@help_cmd.handle()
async def handle_help(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    await finish_panel(matcher, "\u4fee\u4ed9\u5e2e\u52a9", format_help_text(), icon="scroll", footer=command_hint("入门与状态"))


@newbie_tutorial_cmd.handle()
async def handle_newbie_tutorial(matcher: Matcher, event: PrivateMessageEvent) -> None:
    record = await store.get_user(event.get_user_id())
    await finish_panel(
        matcher,
        "新手教程",
        format_newbie_tutorial_text(record, nickname_from_event(event)),
        record,
        icon="scroll",
        footer="以后在私聊发送“新手教程”，可随时重新打开这份引导。",
    )


@catalog_cmd.handle()
async def handle_catalog(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    if text in SPECIAL_ABILITY_CATALOG_TEXTS:
        ensure_combat_profile(record)
        await store.save_user(record)
        await finish_panel(matcher, "\u795e\u901a\u56fe\u9274", special_ability_catalog_text(record), record, icon="ability", footer=command_hint("背包与图鉴"))
    await finish_panel(matcher, "\u4fee\u4ed9\u56fe\u9274", format_catalog_text(text), record, icon="catalog", footer=command_hint("背包与图鉴"))


@puppet_list.handle()
async def handle_puppet_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "我的傀儡", format_puppet_list(record), record, icon="puppet", footer=command_hint("背包与图鉴"))


@plant_list.handle()
async def handle_plant_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "我的灵植", format_plant_list(record), record, icon="plant", footer=command_hint("背包与图鉴"))


@item_list.handle()
async def handle_item_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "背包道具", format_item_list(record), record, icon="bag", footer=command_hint("背包与图鉴"))


@acquired_root_cmd.handle()
async def handle_acquired_root(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    parsed = parse_acquired_root_command(normalized_plain_text(event))
    if parsed is None or parsed[0] == "status":
        await finish_panel(matcher, "后天灵根", acquired_root_text(record), record, icon="realm", footer=command_hint("修为与突破"))
    kind, index = parsed
    if index is None:
        await finish_panel(matcher, "后天灵根", acquired_root_text(record), record, icon="realm", footer=command_hint("修为与突破"))
    if kind == "dan":
        changed, message = refine_dan_root(record, int(index))
    else:
        changed, message = refine_artifact_root(record, int(index))
    if changed:
        await store.save_user(record)
    summary_line = acquired_root_text(record).splitlines()[1].replace("当前：", "")
    await finish_panel(
        matcher,
        "后天灵根炼化" if changed else "操作失败",
        f"{message}\n当前后天灵根：{summary_line}",
        record,
        icon="realm" if changed else "warning",
    )


@special_ability_cmd.handle()
async def handle_special_ability(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    ensure_combat_profile(record)
    text = normalized_plain_text(event)
    if text in SPECIAL_ABILITY_CATALOG_TEXTS:
        await store.save_user(record)
        await finish_panel(matcher, "神通图鉴", special_ability_catalog_text(record), record, icon="ability", footer=command_hint("背包与图鉴"))
    await store.save_user(record)
    await finish_panel(matcher, "我的神通", special_ability_list_text(record), record, icon="ability", footer=command_hint("背包与图鉴"))


@special_ability_learn_cmd.handle()
async def handle_special_ability_learn(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    item_index = parse_prefixed_index(normalized_plain_text(event), SPECIAL_ABILITY_LEARN_PREFIXES)
    if item_index is None:
        await finish_panel(matcher, "操作提示", "请发送“领悟神通 1”。", record, icon="ability")
    success, message = learn_special_ability(record, item_index)
    if success:
        await store.save_user(record)
    await finish_panel(matcher, "神通领悟" if success else "领悟失败", message, record, icon="ability" if success else "warning")


@cultivation_rank.handle()
async def handle_cultivation_rank(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    entries = await group_cultivation_rank_entries(str(event.group_id))
    await finish_panel(matcher, "群修为榜", format_cultivation_rank(entries, "【群修为榜】"), icon="rank")


@power_rank.handle()
async def handle_power_rank(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    entries = await group_power_rank_entries(str(event.group_id))
    await finish_panel(matcher, "群战力榜", format_power_rank(entries, "【群战力榜】"), icon="rank")


@artifact_list.handle()
async def handle_artifact_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "我的灵器", format_artifact_list(record), record, icon="artifact", footer=command_hint("灵器与战力"))


@method_list.handle()
async def handle_method_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "我的功法", format_method_list(record), record, icon="method", footer=command_hint("功法与阵盘"))


@method_detail_cmd.handle()
async def handle_method_detail(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    ensure_combat_profile(record)
    method_index = parse_prefixed_index(normalized_plain_text(event), METHOD_DETAIL_PREFIXES)
    if method_index is None:
        await finish_panel(matcher, "\u64cd\u4f5c\u63d0\u793a", "\u8bf7\u53d1\u9001\u201c\u5b66\u4e60\u529f\u6cd5 1\u201d\u6216\u201c\u529f\u6cd5\u8be6\u60c5 1\u201d\u3002", record, icon="method")
    success, message = format_method_detail(record, method_index)
    await store.save_user(record)
    await finish_panel(matcher, "\u529f\u6cd5\u9875" if success else "\u64cd\u4f5c\u5931\u8d25", message, record, icon="method" if success else "warning")


@array_list.handle()
async def handle_array_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "我的阵盘", format_array_list(record), record, icon="array", footer=command_hint("功法与阵盘"))


@chat_rank_counter.handle()
async def handle_chat_rank_counter(event: GroupMessageEvent) -> None:
    await store.add_chat_count(
        group_id=str(event.group_id),
        user_id=event.get_user_id(),
        date_text=local_today().isoformat(),
        nickname=nickname_from_event(event),
    )
    record = await store.get_user(event.get_user_id())
    applied_exp, leveled = apply_chat_cultivation(record, 1)
    if applied_exp or leveled:
        await store.save_user(record)
