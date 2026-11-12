"""玩家间交易：直交易、万宝楼、秘境救援，以及唯一道具归一化（R-18）。"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.matcher import Matcher

from ...domain import (
    is_unique_reward,
    make_unique_replica,
    market_offer_price,
    pop_reward_by_category_index,
    reward_display_name,
    spirit_stone_text,
)
from ...mystic_dungeon import DungeonPhase
from ...state import local_now, mystic_coordinator, store
from ...storage import InsufficientSpiritStones, MysticRescueRequest
from ..matchers import market_cmd, rescue_cmd, trade_cmd
from ..panels import finish_panel
from ..rewards import enforce_unique_rewards, normalize_unique_reward_for_user
from ..parsing import (
    at_user_ids,
    nickname_from_event,
    normalized_plain_text,
    parse_market_buy,
    parse_market_cancel,
    parse_market_offer,
    parse_rescue_request,
    parse_rescue_take,
    parse_trade_accept,
    parse_trade_cancel,
    parse_trade_offer,
    remember_group_member,
)
from ..picmenu import command_hint
from ..texts import MARKET_TEXTS
from ..mystic_result import finish_mystic_command_result


@trade_cmd.handle()
async def handle_trade(matcher: Matcher, event: MessageEvent) -> None:
    if not isinstance(event, GroupMessageEvent):
        await finish_panel(matcher, "\u73a9\u5bb6\u4ea4\u6613", "\u73a9\u5bb6\u4ea4\u6613\u4ec5\u652f\u6301\u7fa4\u804a\u4f7f\u7528\u3002", icon="warning")
    await remember_group_member(event)
    user_id = event.get_user_id()
    group_id = str(event.group_id)
    text = normalized_plain_text(event)
    record = await store.get_user(user_id)
    accept_id = parse_trade_accept(text)
    cancel_id = parse_trade_cancel(text)
    offer_data = parse_trade_offer(text)
    if text in {"\u4ea4\u6613\u5217\u8868", "\u6211\u7684\u4ea4\u6613"}:
        offers = await store.list_trade_offers(group_id, market=False)
        lines = ["\u3010\u73a9\u5bb6\u4ea4\u6613\u3011"]
        if not offers:
            lines.append("\u6682\u65e0\u6302\u5355\u3002")
        for offer in offers[:12]:
            item = offer.get("item", {})
            target = offer.get("target_id") or "\u5168\u7fa4"
            lines.append(f"{offer.get('id')}. {offer.get('seller_name')} \u51fa\u552e {reward_display_name(item)}\uff0c\u4ef7\u683c {spirit_stone_text(int(offer.get('price', 0)))}\uff0c\u5bf9\u8c61\uff1a{target}")
        lines.append("\u6302\u5355\uff1a\u4ea4\u6613 @\u5bf9\u65b9 \u7c7b\u522b \u7f16\u53f7 \u4ef7\u683c\uff1b\u63a5\u5355\uff1a\u63a5\u53d7\u4ea4\u6613 \u7f16\u53f7\uff1b\u64a4\u56de\uff1a\u53d6\u6d88\u4ea4\u6613 \u7f16\u53f7\u3002")
        await finish_panel(matcher, "\u73a9\u5bb6\u4ea4\u6613", "\n".join(lines), record, icon="shop")
    if accept_id is not None:
        offers = await store.list_trade_offers(group_id, market=False)
        preview = next((item for item in offers if str(item.get("id")) == str(accept_id)), None)
        if not preview:
            await finish_panel(matcher, "\u4ea4\u6613\u5931\u8d25", "\u6ca1\u6709\u627e\u5230\u8fd9\u7b14\u53ef\u63a5\u53d6\u4ea4\u6613\uff0c\u6216\u4ea4\u6613\u5bf9\u8c61\u4e0d\u662f\u4f60\u3002", record, icon="warning")
        target_id = str(preview.get("target_id") or "")
        if target_id and target_id != user_id:
            await finish_panel(matcher, "\u4ea4\u6613\u5931\u8d25", "\u8fd9\u7b14\u4ea4\u6613\u6307\u5b9a\u4e86\u5176\u4ed6\u4fee\u58eb\uff0c\u6682\u65f6\u65e0\u6cd5\u63a5\u53d6\u3002", record, icon="warning")
        price = int(preview.get("price", 0))
        if record.spirit_stones < price:
            await finish_panel(matcher, "\u4ea4\u6613\u5931\u8d25", f"\u7075\u77f3\u4e0d\u8db3\uff0c\u9700\u8981 {spirit_stone_text(price)}\u3002", record, icon="warning")
        offer = await store.take_trade_offer(group_id, str(accept_id), user_id)
        if not offer:
            await finish_panel(matcher, "\u4ea4\u6613\u5931\u8d25", "\u4ea4\u6613\u5df2\u88ab\u63a5\u53d6\u3001\u53d6\u6d88\u6216\u8fc7\u671f\u3002", record, icon="warning")
        seller_id = str(offer.get("seller_id"))
        item = dict(offer.get("item") or {})
        # 唯一道具归一化内部会取 store 锁，必须在原子事务之外完成。
        item, append_msg = await normalize_unique_reward_for_user(record, item, event)

        def settle_trade(records, buyer_id=user_id, seller_id=seller_id, price=price, item=item):
            # 余额校验与双方改动在同一把锁内，杜绝并发接单的重复扣款/凭空灵石。
            buyer = records[buyer_id]
            if buyer.spirit_stones < price:
                raise InsufficientSpiritStones(buyer_id, price, buyer.spirit_stones)
            buyer.spirit_stones -= price
            buyer.rewards = list(buyer.rewards or []) + [item]
            records[seller_id].spirit_stones += price

        try:
            settled = await store.apply_to_users([user_id, seller_id], settle_trade)
        except InsufficientSpiritStones:
            await store.reopen_trade_offer(group_id, str(accept_id))
            record = await store.get_user(user_id)
            await finish_panel(matcher, "\u4ea4\u6613\u5931\u8d25", f"\u7075\u77f3\u4e0d\u8db3\uff0c\u9700\u8981 {spirit_stone_text(price)}\u3002", record, icon="warning")
        record = settled[user_id]
        await finish_panel(matcher, "\u4ea4\u6613\u5b8c\u6210", f"\u83b7\u5f97 {reward_display_name(item)}\uff0c\u652f\u4ed8 {spirit_stone_text(price)}\u3002{append_msg}", record, icon="shop")
    if cancel_id is not None:
        offer = await store.cancel_trade_offer(group_id, str(cancel_id), user_id)
        if not offer:
            await finish_panel(matcher, "\u64a4\u9500\u5931\u8d25", "\u6ca1\u6709\u627e\u5230\u53ef\u64a4\u9500\u7684\u672c\u4eba\u6302\u5355\u3002", record, icon="warning")
        item = dict(offer.get("item") or {})

        def restore_item(rec, item=item):
            rec.rewards = list(rec.rewards or []) + [item]

        record = await store.apply_to_user(user_id, restore_item)
        await finish_panel(matcher, "\u4ea4\u6613\u64a4\u9500", f"\u5df2\u64a4\u56de {reward_display_name(item)}\u3002", record, icon="shop")
    if offer_data is None:
        await finish_panel(matcher, "\u73a9\u5bb6\u4ea4\u6613", "\u6302\u5355\u683c\u5f0f\uff1a\u4ea4\u6613 @\u5bf9\u65b9 \u7c7b\u522b \u7f16\u53f7 \u4ef7\u683c\uff0c\u4f8b\u5982\uff1a\u4ea4\u6613 @\u9053\u53cb \u7075\u5668 1 100\u3002", record, icon="shop")
    target_id, category, item_index, price = offer_data
    if not target_id:
        targets = at_user_ids(event)
        target_id = targets[0] if targets else ""
    result = pop_reward_by_category_index(record, category, item_index)
    if result is None:
        await finish_panel(matcher, "\u6302\u5355\u5931\u8d25", f"\u6ca1\u6709\u627e\u5230\u7b2c {item_index} \u4ef6{category}\u3002", record, icon="warning")
    await store.save_user(record)
    offer = await store.create_trade_offer(group_id, user_id, nickname_from_event(event), target_id, result, price)
    await finish_panel(matcher, "\u73a9\u5bb6\u4ea4\u6613", f"\u5df2\u6302\u5355 {offer.get('id')}\uff1a{reward_display_name(result)}\uff0c\u4ef7\u683c {spirit_stone_text(price)}\u3002", record, icon="shop")


@market_cmd.handle()
async def handle_market(matcher: Matcher, event: MessageEvent) -> None:
    if not isinstance(event, GroupMessageEvent):
        await finish_panel(matcher, "万宝楼", "万宝楼仅支持群聊使用。", icon="warning")
    await remember_group_member(event)
    user_id = event.get_user_id()
    group_id = str(event.group_id)
    text = normalized_plain_text(event)
    record = await store.get_user(user_id)
    buy_id = parse_market_buy(text)
    cancel_id = parse_market_cancel(text)
    offer_data = parse_market_offer(text)
    if text in MARKET_TEXTS:
        offers = await store.list_trade_offers(group_id, market=True)
        lines = ["【万宝楼】", "寄售定价：系统回收价 × 1.5。"]
        if not offers:
            lines.append("当前暂无寄售物品。")
        for offer in offers[:16]:
            item = dict(offer.get("item") or {})
            seller = offer.get("seller_name") or offer.get("seller_id")
            lines.append(f"{offer.get('id')}. {seller} 寄售 {reward_display_name(item)}｜{spirit_stone_text(int(offer.get('price', 0)))}")
        lines.append("挂售：万宝楼挂售 类别 编号；购买：万宝楼购买 编号；下架：万宝楼下架 编号。")
        await finish_panel(matcher, "万宝楼", "\n".join(lines), record, icon="shop", footer=command_hint("交易与商店"))
    if buy_id is not None:
        offers = await store.list_trade_offers(group_id, market=True)
        preview = next((item for item in offers if str(item.get("id")) == str(buy_id)), None)
        if not preview:
            await finish_panel(matcher, "购买失败", "没有找到这件万宝楼寄售物。", record, icon="warning")
        if str(preview.get("seller_id")) == user_id:
            await finish_panel(matcher, "购买失败", "不能购买自己寄售的物品，可使用“万宝楼下架 编号”撤回。", record, icon="warning")
        price = int(preview.get("price", 0))
        if record.spirit_stones < price:
            await finish_panel(matcher, "购买失败", f"灵石不足，需要 {spirit_stone_text(price)}。", record, icon="warning")
        offer = await store.take_trade_offer(group_id, str(buy_id), user_id)
        if not offer or not offer.get("market"):
            await finish_panel(matcher, "购买失败", "寄售已被购买、下架或状态变化。", record, icon="warning")
        seller_id = str(offer.get("seller_id"))
        item = dict(offer.get("item") or {})
        # 唯一道具归一化内部会取 store 锁，必须在原子事务之外完成。
        item, append_msg = await normalize_unique_reward_for_user(record, item, event)

        def settle_market(records, buyer_id=user_id, seller_id=seller_id, price=price, item=item):
            buyer = records[buyer_id]
            if buyer.spirit_stones < price:
                raise InsufficientSpiritStones(buyer_id, price, buyer.spirit_stones)
            buyer.spirit_stones -= price
            buyer.rewards = list(buyer.rewards or []) + [item]
            records[seller_id].spirit_stones += price

        try:
            settled = await store.apply_to_users([user_id, seller_id], settle_market)
        except InsufficientSpiritStones:
            await store.reopen_trade_offer(group_id, str(buy_id))
            record = await store.get_user(user_id)
            await finish_panel(matcher, "购买失败", f"灵石不足，需要 {spirit_stone_text(price)}。", record, icon="warning")
        record = settled[user_id]
        await finish_panel(matcher, "万宝楼成交", f"购得 {reward_display_name(item)}，支付 {spirit_stone_text(price)}。{append_msg}", record, icon="shop")
    if cancel_id is not None:
        offer = await store.cancel_trade_offer(group_id, str(cancel_id), user_id)
        if not offer or not offer.get("market"):
            await finish_panel(matcher, "下架失败", "没有找到可下架的本人寄售物。", record, icon="warning")
        item = dict(offer.get("item") or {})

        def restore_market_item(rec, item=item):
            rec.rewards = list(rec.rewards or []) + [item]

        record = await store.apply_to_user(user_id, restore_market_item)
        await finish_panel(matcher, "万宝楼下架", f"已下架 {reward_display_name(item)}。", record, icon="shop")
    if offer_data is None:
        await finish_panel(matcher, "万宝楼", "格式：万宝楼挂售 类别 编号，例如：万宝楼挂售 灵器 1。", record, icon="shop", footer=command_hint("交易与商店"))
    category, item_index = offer_data
    result = pop_reward_by_category_index(record, category, item_index)
    if result is None:
        await finish_panel(matcher, "挂售失败", f"没有找到第 {item_index} 件{category}。", record, icon="warning")
    if is_unique_reward(result):
        record.rewards = list(record.rewards or []) + [result]
        await store.save_user(record)
        await finish_panel(matcher, "挂售失败", "全局唯一道具暂不支持万宝楼寄售，避免本体归属错乱。", record, icon="warning")
    price = market_offer_price(result)
    await store.save_user(record)
    offer = await store.create_trade_offer(group_id, user_id, nickname_from_event(event), "", result, price, market=True)
    await finish_panel(matcher, "万宝楼挂售", f"已寄售 {offer.get('id')}：{reward_display_name(result)}，定价 {spirit_stone_text(price)}（系统回收价 × 1.5）。", record, icon="shop")


@rescue_cmd.handle()
async def handle_rescue(matcher: Matcher, event: MessageEvent) -> None:
    if not isinstance(event, GroupMessageEvent):
        await finish_panel(matcher, "\u79d8\u5883\u6551\u63f4", "\u79d8\u5883\u6551\u63f4\u4ec5\u652f\u6301\u7fa4\u804a\u4f7f\u7528\u3002", icon="warning")
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    group_id = str(event.group_id)
    text = normalized_plain_text(event)
    if text in {"\u6551\u63f4\u5217\u8868", "\u79d8\u5883\u6551\u63f4\u5217\u8868"}:
        requests = await store.list_rescue_requests(group_id)
        lines = ["\u3010\u79d8\u5883\u6551\u63f4\u3011"]
        if not requests:
            lines.append("\u6682\u65e0\u6551\u63f4\u59d4\u6258\u3002")
        for req in requests[:10]:
            lines.append(
                f"{req.request_id}\uff1a{req.requester_name} \u6c42\u63f4"
                f"\uff0c\u5269\u4f59\u751f\u547d {req.remaining_hp}"
                f"\uff0c\u916c\u52b3 {spirit_stone_text(req.reward_stones)}"
            )
        lines.append("\u53d1\u8d77\uff1a\u79d8\u5883\u6551\u63f4 1000\uff1b\u63a5\u53d6\uff1a\u6551\u63f4 \u59d4\u6258\u7f16\u53f7\u3002")
        await finish_panel(matcher, "\u79d8\u5883\u6551\u63f4", "\n".join(lines), record, icon="mystic")
    amount = parse_rescue_request(text)
    if amount is not None:
        if amount <= 0:
            await finish_panel(matcher, "\u79d8\u5883\u6551\u63f4", "\u8bf7\u5199\u660e\u6551\u63f4\u916c\u52b3\uff0c\u4f8b\u5982\uff1a\u79d8\u5883\u6551\u63f4 1000\u3002", record, icon="mystic")
        if record.spirit_stones < amount:
            await finish_panel(matcher, "\u6551\u63f4\u5931\u8d25", f"\u7075\u77f3\u4e0d\u8db3\uff0c\u5f53\u524d\u4ec5\u6709 {spirit_stone_text(record.spirit_stones)}\u3002", record, icon="warning")
        run_id = await store.find_active_mystic_run_id(event.get_user_id())
        run = await store.get_mystic_run(run_id or "")
        if (
            run is None
            or run.phase is not DungeonPhase.AWAITING_RESCUE
            or run.leader_id != event.get_user_id()
            or run.active_encounter_id is None
        ):
            await finish_panel(matcher, "\u6551\u63f4\u5931\u8d25", "\u5f53\u524d\u6ca1\u6709\u53ef\u59d4\u6258\u6551\u63f4\u7684\u65b0\u7248\u79d8\u5883\u906d\u9047\u3002", record, icon="warning")
        encounter = await store.get_mystic_encounter(run.active_encounter_id)
        if encounter is None or encounter.shared_monster_hp <= 0:
            await finish_panel(matcher, "\u6551\u63f4\u5931\u8d25", "\u79d8\u5883\u906d\u9047\u72b6\u6001\u7f3a\u5931\u3002", record, icon="warning")
        request = MysticRescueRequest(
            request_id=f"rescue:{run.run_id}:{run.revision}",
            run_id=run.run_id,
            encounter_id=encounter.encounter_id,
            group_id=group_id,
            requester_id=event.get_user_id(),
            requester_name=nickname_from_event(event),
            reward_stones=amount,
            monster_snapshot=encounter.monster_record,
            remaining_hp=encounter.shared_monster_hp,
            deadline=(
                local_now()
                + timedelta(
                    seconds=mystic_coordinator.battle_service.config.rescue_wait_seconds
                )
            ).isoformat(),
        )
        saved_request = await store.create_rescue_request(request)
        await finish_panel(matcher, "\u79d8\u5883\u6551\u63f4", f"\u5df2\u53d1\u5e03\u6551\u63f4\u59d4\u6258 {saved_request.request_id}\uff0c\u916c\u52b3 {spirit_stone_text(amount)}\u3002\u5176\u4ed6\u4fee\u58eb\u53ef\u53d1\u9001\uff1a\u6551\u63f4 {saved_request.request_id}\u3002", record, icon="mystic")
    take_id = parse_rescue_take(text)
    if take_id is not None:
        if not take_id:
            await finish_panel(matcher, "\u79d8\u5883\u6551\u63f4", "\u8bf7\u53d1\u9001\uff1a\u6551\u63f4 \u59d4\u6258\u7f16\u53f7\u3002", record, icon="mystic")
        result = await mystic_coordinator.take_rescue(
            group_id,
            take_id,
            event.get_user_id(),
        )
        await finish_mystic_command_result(matcher, event.get_user_id(), result)
