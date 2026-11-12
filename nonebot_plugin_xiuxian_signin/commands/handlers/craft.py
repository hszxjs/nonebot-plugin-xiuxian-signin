"""生产与抽取：商店、炼丹、炼器、阵法推演、本命灵器、仙源、绘符（R-18）。"""
from __future__ import annotations

from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.matcher import Matcher

from ...domain import (
    alchemy_text,
    array_deduction_text,
    batch_sell_low_realm_artifacts,
    batch_sell_rewards,
    buy_shop_item,
    deduce_array,
    draw_talisman_by_index,
    emperor_artifact_catalog_text,
    equip_immortal_seed,
    immortal_seed_text,
    refine_artifact_by_recipe,
    refine_pill_by_recipe,
    refining_text,
    sell_reward,
    set_life_artifact,
    spirit_stone_text,
    talisman_draw_text,
)
from ...state import local_today, store
from ..formatting import format_shop_panel, item_icon_for_category
from ..matchers import (
    alchemy_cmd,
    array_deduction_cmd,
    emperor_catalog_cmd,
    immortal_seed_cmd,
    life_artifact_cmd,
    refining_cmd,
    shop_cmd,
    talisman_draw_cmd,
)
from ..panels import finish_panel
from ..parsing import (
    normalized_plain_text,
    parse_alchemy_name,
    parse_array_deduction_index,
    parse_batch_sell,
    parse_immortal_seed_equip_index,
    parse_life_artifact_index,
    parse_low_realm_artifact_batch_sell,
    parse_refining_name,
    parse_sell_item,
    parse_shop_buy_index,
    parse_talisman_draw_index,
    remember_group_member,
)
from ..picmenu import command_hint
from ..texts import ALCHEMY_TEXTS, SHOP_TEXTS


@shop_cmd.handle()
async def handle_shop(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    if text in SHOP_TEXTS:
        await finish_panel(matcher, "\u6bcf\u65e5\u5546\u5e97", format_shop_panel(record, local_today().isoformat()), record, icon="shop", footer=command_hint("交易与商店"))
    buy_index = parse_shop_buy_index(text)
    if buy_index is not None:
        success, message = buy_shop_item(record, buy_index, local_today().isoformat())
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "\u6bcf\u65e5\u5546\u5e97" if success else "\u8d2d\u4e70\u5931\u8d25", message, record, icon="shop" if success else "warning")
    sale = parse_sell_item(text)
    if sale is not None:
        category, item_index = sale
        success, message = sell_reward(record, category, item_index)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "\u51fa\u552e\u7269\u54c1" if success else "\u51fa\u552e\u5931\u8d25", message, record, icon=item_icon_for_category(category) if success else "warning")
    low_artifact_limit = parse_low_realm_artifact_batch_sell(text)
    if low_artifact_limit is not None:
        success, message = batch_sell_low_realm_artifacts(record, low_artifact_limit)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "批量出售低阶灵器" if success else "出售失败", message, record, icon=item_icon_for_category("灵器") if success else "warning")
    batch_sale = parse_batch_sell(text)
    if batch_sale is not None:
        category, limit = batch_sale
        success, message = batch_sell_rewards(record, category, limit)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "\u6279\u91cf\u51fa\u552e" if success else "\u51fa\u552e\u5931\u8d25", message, record, icon=item_icon_for_category(category) if success else "warning")
    await finish_panel(matcher, "\u6bcf\u65e5\u5546\u5e97", format_shop_panel(record, local_today().isoformat()), record, icon="shop", footer=command_hint("交易与商店"))


@alchemy_cmd.handle()
async def handle_alchemy(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    pill_name = parse_alchemy_name(text)
    if text in ALCHEMY_TEXTS or pill_name == "":
        await finish_panel(matcher, "炼丹", alchemy_text(record), record, icon="alchemy", footer=command_hint("炼丹炼器与符箓"))
    if pill_name is None:
        await finish_panel(matcher, "炼丹", alchemy_text(record), record, icon="alchemy", footer=command_hint("炼丹炼器与符箓"))
    success, message = refine_pill_by_recipe(record, pill_name)
    if success:
        await store.save_user(record)
    await finish_panel(matcher, "炼丹" if success else "炼丹失败", message, record, icon="alchemy" if success else "warning")


@refining_cmd.handle()
async def handle_refining(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    name = parse_refining_name(normalized_plain_text(event))
    if name is None or name == "":
        await finish_panel(matcher, "\u70bc\u5668", refining_text(record), record, icon="alchemy", footer=command_hint("炼丹炼器与符箓"))
    success, message = refine_artifact_by_recipe(record, name)
    await store.save_user(record)
    await finish_panel(matcher, "\u70bc\u5668\u6210\u529f" if success else "\u70bc\u5668\u5931\u8d25", message, record, icon="alchemy" if success else "warning")


@array_deduction_cmd.handle()
async def handle_array_deduction(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    index = parse_array_deduction_index(normalized_plain_text(event))
    if not index:
        await finish_panel(matcher, "\u9635\u6cd5\u63a8\u6f14", array_deduction_text(record), record, icon="array", footer=command_hint("功法与阵盘"))
    success, message = deduce_array(record, index)
    await store.save_user(record)
    await finish_panel(matcher, "\u63a8\u6f14\u6210\u529f" if success else "\u63a8\u6f14\u5931\u8d25", message, record, icon="array" if success else "warning")


@life_artifact_cmd.handle()
async def handle_life_artifact(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    index = parse_life_artifact_index(normalized_plain_text(event))
    if index is None:
        await finish_panel(matcher, "\u672c\u547d\u7075\u5668", "\u8bf7\u53d1\u9001\uff1a\u796d\u70bc\u672c\u547d\u7075\u5668 1", record, icon="artifact")
    success, message = set_life_artifact(record, index)
    await store.save_user(record)
    await finish_panel(matcher, "\u672c\u547d\u7075\u5668" if success else "\u796d\u70bc\u5931\u8d25", message, record, icon="artifact" if success else "warning")


@immortal_seed_cmd.handle()
async def handle_immortal_seed(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    index = parse_immortal_seed_equip_index(text)
    if index is None:
        await finish_panel(matcher, "仙源", immortal_seed_text(record), record, icon="ability", footer=command_hint("炼丹炼器与符箓"))
    success, message = equip_immortal_seed(record, index)
    await store.save_user(record)
    await finish_panel(matcher, "仙源" if success else "纳入失败", message, record, icon="ability" if success else "warning")


@emperor_catalog_cmd.handle()
async def handle_emperor_catalog(matcher: Matcher, event: MessageEvent) -> None:
    owners = await store.get_unique_artifacts()
    owner_lookup = {name: str(info.get("nickname") or info.get("user_id") or "") for name, info in owners.items() if isinstance(info, dict)}
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "\u552f\u4e00\u88c5\u5907\u56fe\u9274", emperor_artifact_catalog_text(owner_lookup), record, icon="artifact")


@talisman_draw_cmd.handle()
async def handle_talisman_draw(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    index = parse_talisman_draw_index(normalized_plain_text(event))
    if index is None or index == 0:
        await finish_panel(matcher, "\u7ed8\u5236\u7b26\u7b93", talisman_draw_text(record), record, icon="talisman")
    success, message = draw_talisman_by_index(record, index)
    if success:
        await store.save_user(record)
    await finish_panel(
        matcher,
        "\u7b26\u7b93\u7ed8\u5236" if success else "\u7ed8\u5236\u5931\u8d25",
        f"{message}\n\u5f53\u524d\u7075\u77f3\uff1a{spirit_stone_text(record.spirit_stones)}",
        record,
        icon="talisman" if success else "warning",
    )
