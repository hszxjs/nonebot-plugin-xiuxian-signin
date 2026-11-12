"""装备与消耗品：灵器/符箓/功法/阵盘装卸，丹药、灵液、灵植（R-18）。"""
from __future__ import annotations

from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.matcher import Matcher

from ...domain import (
    battle_power,
    equip_array,
    equip_artifact,
    equip_method,
    equip_puppet,
    equip_talisman,
    identify_misc_item,
    plant_spirit_plant,
    refine_demon_core,
    refine_demon_cores_batch,
    refine_spirit_liquid,
    refine_spirit_stone,
    refine_spirit_stones_batch,
    unequip_artifact,
    unequip_talisman,
    use_curio,
    use_food,
    use_foods_batch,
    use_pill,
    use_pills_batch,
    use_talisman,
)
from ...state import local_today, store
from ..formatting import item_icon_for_category
from ..matchers import (
    equip_array_cmd,
    equip_artifact_cmd,
    equip_method_cmd,
    equip_puppet_cmd,
    equip_talisman_cmd,
    item_use_cmd,
    plant_cmd,
    spirit_liquid_use_cmd,
)
from ..panels import finish_panel
from ..parsing import (
    normalized_plain_text,
    parse_batch_item_use,
    parse_equip_artifact_command,
    parse_equip_talisman_index,
    parse_item_use,
    parse_prefixed_index,
    parse_spirit_liquid_use,
    parse_unequip_artifact_slot,
    remember_group_member,
)
from ..texts import (
    ARRAY_EQUIP_PREFIXES,
    METHOD_EQUIP_PREFIXES,
    PLANT_EQUIP_PREFIXES,
    PUPPET_EQUIP_PREFIXES,
    TALISMAN_UNEQUIP_TEXTS,
    UNEQUIP_TEXTS,
)


@equip_puppet_cmd.handle()
async def handle_equip_puppet(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    puppet_index = parse_prefixed_index(normalized_plain_text(event), PUPPET_EQUIP_PREFIXES)
    if puppet_index is None:
        await finish_panel(matcher, "操作提示", "请发送“装备傀儡 编号”，例如：装备傀儡 1。", record, icon="puppet")
    success, message = equip_puppet(record, puppet_index)
    if not success:
        await finish_panel(matcher, "操作失败", message, record, icon="warning")
    await store.save_user(record)
    await finish_panel(matcher, "傀儡唤醒", f"{message}\n当前战力：{battle_power(record)}", record, icon="puppet")


@plant_cmd.handle()
async def handle_plant(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    plant_index = parse_prefixed_index(normalized_plain_text(event), PLANT_EQUIP_PREFIXES)
    if plant_index is None:
        await finish_panel(matcher, "操作提示", "请发送“栽种灵植 编号”，例如：栽种灵植 1。", record, icon="plant")
    success, message = plant_spirit_plant(record, plant_index)
    if not success:
        await finish_panel(matcher, "操作失败", message, record, icon="warning")
    await store.save_user(record)
    await finish_panel(matcher, "灵植栽种", message, record, icon="plant")


@item_use_cmd.handle()
async def handle_item_use(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    batch_parsed = parse_batch_item_use(text)
    if batch_parsed is not None:
        category, limit = batch_parsed
        batch_handlers = {
            "丹药": use_pills_batch,
            "灵石": refine_spirit_stones_batch,
            "灵食": use_foods_batch,
            "妖丹": refine_demon_cores_batch,
        }
        success, message = batch_handlers[category](record, limit)
        if success:
            await store.save_user(record)
        await finish_panel(
            matcher,
            f"批量{category}炼化" if category == "妖丹" and success else (f"批量{category}使用" if success else "操作失败"),
            f"{message}\n当前境界：{record.realm if record.root else '未入门'}\n当前战力：{battle_power(record)}",
            record,
            icon=item_icon_for_category(category) if success else "warning",
        )
        return
    parsed = parse_item_use(text)
    if parsed is None:
        await finish_panel(matcher, "操作提示", "请发送“使用丹药 1 / 批量使用丹药 10 / 使用符箓 1 / 炼化灵石 1 / 批量炼化灵石 全部 / 炼化妖丹 1 / 批量炼化妖丹 全部 / 使用灵食 1”等格式。", record, icon="bag")
    category, item_index = parsed
    handlers = {
        "丹药": use_pill,
        "符箓": use_talisman,
        "灵石": refine_spirit_stone,
        "灵食": use_food,
        "妖丹": refine_demon_core,
        "奇物": use_curio,
        "杂物": identify_misc_item,
    }
    success, message = handlers[category](record, item_index)
    if success:
        await store.save_user(record)
    await finish_panel(
        matcher,
        f"{category}炼化" if category == "妖丹" and success else (f"{category}使用" if success else "操作失败"),
        f"{message}\n当前境界：{record.realm if record.root else '未入门'}\n当前战力：{battle_power(record)}",
        record,
        icon=item_icon_for_category(category) if success else "warning",
    )


@spirit_liquid_use_cmd.handle()
async def handle_spirit_liquid_use(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    amount = parse_spirit_liquid_use(normalized_plain_text(event))
    success, message = refine_spirit_liquid(record, amount, local_today())
    if success:
        await store.save_user(record)
    await finish_panel(
        matcher,
        "灵液炼化" if success else "炼化失败",
        f"{message}\n剩余精纯灵液：{record.spirit_liquid}\n当前境界：{record.realm if record.root else '未入门'}",
        record,
        icon="stone" if success else "warning",
    )


@equip_artifact_cmd.handle()
async def handle_equip_artifact(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    text = normalized_plain_text(event)
    if text in UNEQUIP_TEXTS or any(text.startswith(f"{prefix} ") or text.startswith(f"{prefix}　") for prefix in UNEQUIP_TEXTS):
        message = unequip_artifact(record, parse_unequip_artifact_slot(text))
    else:
        artifact_index, slot = parse_equip_artifact_command(text)
        if artifact_index is None:
            await finish_panel(matcher, "操作提示", "请发送“装备灵器 编号 槽位”，例如：装备灵器 1 主手 / 装备灵器 2 副手 / 装备灵器 3 护甲。", record, icon="artifact")
        success, message = equip_artifact(record, artifact_index, slot)
        if not success:
            await finish_panel(matcher, "操作失败", message, record, icon="warning")
    await store.save_user(record)
    await finish_panel(matcher, "灵器装备", f"{message}\n当前战力：{battle_power(record)}", record, icon="artifact")


@equip_talisman_cmd.handle()
async def handle_equip_talisman(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    text = normalized_plain_text(event)
    if text in TALISMAN_UNEQUIP_TEXTS:
        message = unequip_talisman(record)
    else:
        talisman_index = parse_equip_talisman_index(text)
        if talisman_index is None:
            await finish_panel(matcher, "操作提示", "请发送“装备符箓 编号”，例如：装备符箓 1；卸下则发送“卸下符箓”。", record, icon="talisman")
        success, message = equip_talisman(record, talisman_index)
        if not success:
            await finish_panel(matcher, "操作失败", message, record, icon="warning")
    await store.save_user(record)
    await finish_panel(matcher, "符箓栏", f"{message}\n当前战力：{battle_power(record)}", record, icon="talisman")


@equip_method_cmd.handle()
async def handle_equip_method(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    method_index = parse_prefixed_index(normalized_plain_text(event), METHOD_EQUIP_PREFIXES)
    if method_index is None:
        await finish_panel(matcher, "操作提示", "请发送“参悟功法 编号”，例如：参悟功法 1。", record, icon="method")
    success, message = equip_method(record, method_index)
    if not success:
        await finish_panel(matcher, "操作失败", message, record, icon="warning")
    await store.save_user(record)
    await finish_panel(matcher, "功法参悟", f"{message}\n当前战力：{battle_power(record)}", record, icon="method")


@equip_array_cmd.handle()
async def handle_equip_array(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    array_index = parse_prefixed_index(normalized_plain_text(event), ARRAY_EQUIP_PREFIXES)
    if array_index is None:
        await finish_panel(matcher, "操作提示", "请发送“布置阵盘 编号”，例如：布置阵盘 1。", record, icon="array")
    success, message = equip_array(record, array_index)
    if not success:
        await finish_panel(matcher, "操作失败", message, record, icon="warning")
    await store.save_user(record)
    await finish_panel(matcher, "阵盘布置", f"{message}\n当前战力：{battle_power(record)}", record, icon="array")
