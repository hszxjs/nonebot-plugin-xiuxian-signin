"""文本解析与群成员助手（R-18）。

把玩家输入的纯文本拆成结构化参数（下标、名称、数量、目标），
并负责群名片/昵称读取。全部为无状态函数，不注册 matcher。"""
from __future__ import annotations

import re

from typing import Optional

from nonebot import get_bot, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent

from ..state import local_today, store
from .texts import (
    ACQUIRED_ROOT_TEXTS,
    ALCHEMY_PREFIXES,
    ALCHEMY_TEXTS,
    ARRAY_DEDUCTION_PREFIXES,
    ARRAY_DEDUCTION_TEXTS,
    ARRAY_EQUIP_PREFIXES,
    ARTIFACT_ROOT_PREFIXES,
    ARTIFACT_SLOT_NAMES,
    BATCH_SELL_PREFIXES,
    BATCH_USE_ALL_WORDS,
    BUY_PREFIXES,
    CATALOG_QUERY_PREFIXES,
    COMMAND_PREFIX_CHARS,
    CURIO_USE_PREFIXES,
    DAN_ROOT_PREFIXES,
    DEMON_CORE_BATCH_USE_PREFIXES,
    DEMON_CORE_USE_PREFIXES,
    DUEL_PREFIXES,
    EQUIP_PREFIXES,
    EVIL_QUIT_TEXTS,
    EVIL_SELECT_TEXTS,
    FISHING_TEXTS,
    FOOD_BATCH_USE_PREFIXES,
    FOOD_USE_PREFIXES,
    IDENTITY_SELECT_PREFIXES,
    IMMORTAL_SEED_EQUIP_PREFIXES,
    IMMORTAL_SEED_TEXTS,
    LIFE_ARTIFACT_PREFIXES,
    LOW_REALM_ARTIFACT_BATCH_SELL_PREFIXES,
    MARKET_BUY_PREFIXES,
    MARKET_CANCEL_PREFIXES,
    MARKET_OFFER_PREFIXES,
    MARKET_TEXTS,
    METHOD_DETAIL_PREFIXES,
    METHOD_EQUIP_PREFIXES,
    MISC_USE_PREFIXES,
    NORMAL_DUEL_ACTION_SEGMENT_LABELS,
    NORMAL_DUEL_IGNORED_SEGMENT_TYPES,
    NORMAL_DUEL_TEXTS,
    PILL_BATCH_USE_PREFIXES,
    PILL_USE_PREFIXES,
    PLANT_EQUIP_PREFIXES,
    PUPPET_EQUIP_PREFIXES,
    REFINING_PREFIXES,
    REFINING_TEXTS,
    RESCUE_REQUEST_PREFIXES,
    RESCUE_TAKE_PREFIXES,
    ROUTE_SELECT_PREFIXES,
    ROUTE_TEXTS,
    SELL_PREFIXES,
    SHOP_TEXTS,
    SPECIAL_ABILITY_CATALOG_TEXTS,
    SPECIAL_ABILITY_LEARN_PREFIXES,
    SPECIAL_ABILITY_TEXTS,
    SPIRIT_LIQUID_USE_PREFIXES,
    STONE_BATCH_USE_PREFIXES,
    STONE_USE_PREFIXES,
    TALISMAN_DRAW_PREFIXES,
    TALISMAN_DRAW_TEXTS,
    TALISMAN_EQUIP_PREFIXES,
    TALISMAN_UNEQUIP_TEXTS,
    TALISMAN_USE_PREFIXES,
    TASK_COMPLETE_PREFIXES,
    TASK_TEXTS,
    TIANJI_MYSTIC_TEXTS,
    TRADE_ACCEPT_PREFIXES,
    TRADE_CANCEL_PREFIXES,
    TRADE_OFFER_PREFIXES,
    UNEQUIP_TEXTS,
)


def normalized_plain_text(event: MessageEvent) -> str:
    return event.message.extract_plain_text().strip().lstrip(COMMAND_PREFIX_CHARS).strip()


def normal_duel_action_text(event: MessageEvent) -> str:
    text = normalized_plain_text(event)
    if text:
        return text
    labels: list[str] = []
    for segment in event.message:
        segment_type = str(getattr(segment, "type", "") or "")
        if not segment_type or segment_type in NORMAL_DUEL_IGNORED_SEGMENT_TYPES:
            continue
        label = NORMAL_DUEL_ACTION_SEGMENT_LABELS.get(segment_type)
        if not label:
            continue
        data = getattr(segment, "data", None) or {}
        if segment_type == "face":
            face_id = str(data.get("id") or data.get("face_id") or "").strip()
            if face_id:
                label = f"{label}{face_id}"
        elif segment_type == "mface":
            summary = str(data.get("summary") or data.get("text") or data.get("name") or "").strip()
            if summary:
                label = f"{label}{summary[:12]}"
        labels.append(label)
    return "\u3001".join(labels).strip()


def parse_fishing_arg(text: str) -> Optional[str]:
    for command in FISHING_TEXTS:
        if text == command:
            return ""
        if text.startswith(command):
            return text[len(command):].strip()
    return None








# 头像获取收敛到 net.py：共享 httpx 客户端 + 带 TTL 的字节 LRU（R-13）。
from ..net import close_shared_http_client, fetch_avatar


def nickname_from_event(event: MessageEvent) -> str:
    sender = getattr(event, "sender", None)
    if sender:
        card = getattr(sender, "card", "") or ""
        nickname = getattr(sender, "nickname", "") or ""
        return card or nickname
    return ""


def short_name(name: str, limit: int = 12) -> str:
    name = name.strip()
    if len(name) <= limit:
        return name
    return f"{name[:limit - 1]}…"


async def remember_group_member(event: MessageEvent) -> None:
    if not isinstance(event, GroupMessageEvent):
        return
    await store.touch_group_member(
        group_id=str(event.group_id),
        user_id=event.get_user_id(),
        date_text=local_today().isoformat(),
        nickname=nickname_from_event(event),
    )


async def group_member_display_name(event: GroupMessageEvent, user_id: str) -> str:
    group_id = str(event.group_id)
    cached = await store.get_group_member_nickname(group_id, user_id)
    if cached:
        return cached
    try:
        bot = get_bot()
        info = await bot.get_group_member_info(
            group_id=int(event.group_id),
            user_id=int(user_id),
            no_cache=False,
        )
        name = str(info.get("card") or info.get("nickname") or "").strip()
        if name:
            await store.touch_group_member(group_id, user_id, local_today().isoformat(), name)
            return name
    except Exception as exc:
        logger.debug(f"获取群成员昵称失败: {exc}")
    return f"QQ {user_id}"


def at_user_ids(event: MessageEvent) -> list[str]:
    result = []
    for segment in event.message:
        if segment.type != "at":
            continue
        user_id = str(segment.data.get("qq", ""))
        if user_id and user_id != "all":
            result.append(user_id)
    return result


def parse_artifact_slot(text: str) -> Optional[str]:
    for slot in ARTIFACT_SLOT_NAMES:
        if slot in text:
            return "护甲" if slot == "护盾" else slot
    return None


def is_equip_command_text(text: str) -> bool:
    if text in UNEQUIP_TEXTS:
        return True
    if any(text.startswith(f"{prefix} ") or text.startswith(f"{prefix}　") for prefix in UNEQUIP_TEXTS):
        return parse_artifact_slot(text) is not None
    if is_equip_method_command_text(text) or is_equip_array_command_text(text) or is_equip_talisman_command_text(text):
        return False
    for prefix in EQUIP_PREFIXES:
        if text == prefix:
            return False
        if text.startswith(prefix):
            rest = text[len(prefix):].strip()
            return bool(re.search(r"\d+", rest))
    return False


def parse_equip_index(text: str) -> Optional[int]:
    for prefix in EQUIP_PREFIXES:
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix):].strip()
        match = re.search(r"\d+", rest)
        if match:
            return int(match.group(0))
    return None


def parse_equip_artifact_command(text: str) -> tuple[Optional[int], Optional[str]]:
    return parse_equip_index(text), parse_artifact_slot(text)


def parse_unequip_artifact_slot(text: str) -> Optional[str]:
    return parse_artifact_slot(text)


def is_prefixed_index_command(text: str, prefixes: tuple[str, ...]) -> bool:
    for prefix in prefixes:
        if text == prefix:
            return False
        if text.startswith(prefix):
            rest = text[len(prefix):].strip()
            return bool(re.search(r"\d+", rest))
    return False


def parse_prefixed_index(text: str, prefixes: tuple[str, ...]) -> Optional[int]:
    for prefix in prefixes:
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix):].strip()
        match = re.search(r"\d+", rest)
        if match:
            return int(match.group(0))
    return None


def parse_spirit_liquid_use(text: str) -> Optional[int]:
    for prefix in SPIRIT_LIQUID_USE_PREFIXES:
        if text == prefix:
            return None
        if text.startswith(prefix):
            rest = text[len(prefix):].strip()
            if not rest or rest in {"\u5168\u90e8", "all", "ALL"}:
                return None
            match = re.search(r"\d+", rest)
            if match:
                return int(match.group(0))
            return 0
    return None


def is_spirit_liquid_use_command_text(text: str) -> bool:
    return any(text == prefix or text.startswith(prefix) for prefix in SPIRIT_LIQUID_USE_PREFIXES)


def is_item_use_command_text(text: str) -> bool:
    if parse_batch_item_use(text) is not None:
        return True
    return any(
        is_prefixed_index_command(text, prefixes)
        for prefixes in (
            PILL_USE_PREFIXES,
            TALISMAN_USE_PREFIXES,
            STONE_USE_PREFIXES,
            FOOD_USE_PREFIXES,
            CURIO_USE_PREFIXES,
            MISC_USE_PREFIXES,
            DEMON_CORE_USE_PREFIXES,
        )
    )


def is_equip_talisman_command_text(text: str) -> bool:
    return text in TALISMAN_UNEQUIP_TEXTS or is_prefixed_index_command(text, TALISMAN_EQUIP_PREFIXES)


def parse_equip_talisman_index(text: str) -> Optional[int]:
    return parse_prefixed_index(text, TALISMAN_EQUIP_PREFIXES)


def is_equip_puppet_command_text(text: str) -> bool:
    return is_prefixed_index_command(text, PUPPET_EQUIP_PREFIXES)


def is_plant_command_text(text: str) -> bool:
    return is_prefixed_index_command(text, PLANT_EQUIP_PREFIXES)


def is_route_command_text(text: str) -> bool:
    return (
        text in ROUTE_TEXTS
        or parse_prefixed_name(text, ROUTE_SELECT_PREFIXES) is not None
        or parse_prefixed_name(text, IDENTITY_SELECT_PREFIXES) is not None
        or text in EVIL_SELECT_TEXTS
        or text in EVIL_QUIT_TEXTS
    )


def is_task_command_text(text: str) -> bool:
    return text in TASK_TEXTS or is_prefixed_index_command(text, TASK_COMPLETE_PREFIXES)


def is_shop_command_text(text: str) -> bool:
    return (
        text in SHOP_TEXTS
        or parse_shop_buy_index(text) is not None
        or parse_sell_item(text) is not None
        or parse_low_realm_artifact_batch_sell(text) is not None
        or parse_batch_sell(text) is not None
    )


def is_alchemy_command_text(text: str) -> bool:
    return text in ALCHEMY_TEXTS or parse_alchemy_name(text) is not None


def is_talisman_draw_command_text(text: str) -> bool:
    return parse_talisman_draw_index(text) is not None


def is_special_ability_command_text(text: str) -> bool:
    return text in SPECIAL_ABILITY_TEXTS or text in SPECIAL_ABILITY_CATALOG_TEXTS


def is_special_ability_learn_command_text(text: str) -> bool:
    return is_prefixed_index_command(text, SPECIAL_ABILITY_LEARN_PREFIXES)


def is_tianji_mystic_command_text(text: str) -> bool:
    return text in TIANJI_MYSTIC_TEXTS



def parse_refining_name(text: str) -> Optional[str]:
    stripped = text.strip()
    if stripped in REFINING_TEXTS:
        return ""
    for prefix in REFINING_PREFIXES:
        if stripped.startswith(f"{prefix} "):
            return stripped[len(prefix):].strip()
    return None


def parse_array_deduction_index(text: str) -> Optional[int]:
    if text in ARRAY_DEDUCTION_TEXTS:
        return 0
    return parse_prefixed_index(text, ARRAY_DEDUCTION_PREFIXES)


def parse_life_artifact_index(text: str) -> Optional[int]:
    return parse_prefixed_index(text, LIFE_ARTIFACT_PREFIXES)


def parse_immortal_seed_equip_index(text: str) -> Optional[int]:
    return parse_prefixed_index(text, IMMORTAL_SEED_EQUIP_PREFIXES)


def parse_batch_sell(text: str) -> Optional[tuple[str, int]]:
    for prefix in BATCH_SELL_PREFIXES:
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix):].strip()
        if not rest:
            return None
        parts = rest.split()
        category = parts[0]
        limit = 999
        if len(parts) > 1 and parts[1].isdigit():
            limit = int(parts[1])
        return category, limit
    return None


def parse_low_realm_artifact_batch_sell(text: str) -> Optional[int]:
    for prefix in LOW_REALM_ARTIFACT_BATCH_SELL_PREFIXES:
        if text == prefix:
            return 999
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix):].strip()
        if not rest or rest in BATCH_USE_ALL_WORDS:
            return 999
        if rest.isdigit():
            return int(rest)
    return None


TRADE_CATEGORIES = ("仙缘", "灵器", "功法", "丹药", "阵盘", "灵材", "符箓", "傀儡", "灵植", "灵石", "杂物", "奇物", "神通", "灵食", "仙源", "仙种")


def parse_catalog_query(text: str) -> Optional[str]:
    stripped = text.strip()
    for prefix in CATALOG_QUERY_PREFIXES:
        if stripped == prefix:
            return None
        if stripped.startswith(prefix):
            rest = stripped[len(prefix):].strip()
            return rest or None
    return None


def parse_trade_offer(text: str) -> Optional[tuple[str, str, int, int]]:
    for prefix in TRADE_OFFER_PREFIXES:
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix):].strip()
        match = re.search(r"(\d{5,})", rest)
        target_id = ""
        if match:
            target_id = match.group(1)
            rest = (rest[:match.start()] + rest[match.end():]).strip()
        for category in TRADE_CATEGORIES:
            if category not in rest:
                continue
            tail = rest.split(category, 1)[1]
            nums = [int(item) for item in re.findall(r"\d+", tail)]
            if len(nums) >= 2:
                return target_id, category, nums[0], nums[1]
    return None


def parse_trade_accept(text: str) -> Optional[int]:
    return parse_prefixed_index(text, TRADE_ACCEPT_PREFIXES)


def parse_trade_cancel(text: str) -> Optional[int]:
    return parse_prefixed_index(text, TRADE_CANCEL_PREFIXES)


def parse_market_offer(text: str) -> Optional[tuple[str, int]]:
    for prefix in MARKET_OFFER_PREFIXES:
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix):].strip()
        for category in TRADE_CATEGORIES:
            if category not in rest:
                continue
            tail = rest.split(category, 1)[1]
            nums = [int(item) for item in re.findall(r"\d+", tail)]
            if nums:
                return category, nums[0]
    return None


def parse_market_buy(text: str) -> Optional[int]:
    return parse_prefixed_index(text, MARKET_BUY_PREFIXES)


def parse_market_cancel(text: str) -> Optional[int]:
    return parse_prefixed_index(text, MARKET_CANCEL_PREFIXES)


def parse_rescue_request(text: str) -> Optional[int]:
    for prefix in RESCUE_REQUEST_PREFIXES:
        if text == prefix:
            return 0
        if text.startswith(prefix):
            match = re.search(r"\d+", text[len(prefix):])
            return int(match.group(0)) if match else 0
    return None


def parse_rescue_take(text: str) -> Optional[str]:
    for prefix in RESCUE_TAKE_PREFIXES:
        if text == prefix:
            return ""
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return None


def is_refining_command_text(text: str) -> bool:
    return parse_refining_name(text) is not None


def is_array_deduction_command_text(text: str) -> bool:
    return parse_array_deduction_index(text) is not None


def is_life_artifact_command_text(text: str) -> bool:
    return parse_life_artifact_index(text) is not None


def is_immortal_seed_command_text(text: str) -> bool:
    return text in IMMORTAL_SEED_TEXTS or parse_immortal_seed_equip_index(text) is not None


def is_trade_command_text(text: str) -> bool:
    return parse_trade_offer(text) is not None or parse_trade_accept(text) is not None or parse_trade_cancel(text) is not None or text in {"\u4ea4\u6613\u5217\u8868", "\u6211\u7684\u4ea4\u6613"}


def is_market_command_text(text: str) -> bool:
    return text in MARKET_TEXTS or parse_market_offer(text) is not None or parse_market_buy(text) is not None or parse_market_cancel(text) is not None


def is_rescue_command_text(text: str) -> bool:
    return parse_rescue_request(text) is not None or parse_rescue_take(text) is not None or text in {"\u6551\u63f4\u5217\u8868", "\u79d8\u5883\u6551\u63f4\u5217\u8868"}


def is_dual_cultivation_command_text(text: str) -> bool:
    return text.startswith("双修") or text == "随机双修"


def parse_batch_use_limit(rest: str) -> Optional[int]:
    stripped = str(rest or "").strip()
    if not stripped or stripped in BATCH_USE_ALL_WORDS:
        return 999
    if any(word in stripped for word in BATCH_USE_ALL_WORDS):
        return 999
    match = re.search(r"\d+", stripped)
    if match:
        return max(1, min(999, int(match.group(0))))
    return None


def parse_batch_item_use(text: str) -> Optional[tuple[str, int]]:
    mapping = [
        ("丹药", PILL_BATCH_USE_PREFIXES),
        ("灵石", STONE_BATCH_USE_PREFIXES),
        ("灵食", FOOD_BATCH_USE_PREFIXES),
        ("妖丹", DEMON_CORE_BATCH_USE_PREFIXES),
    ]
    for category, prefixes in mapping:
        for prefix in prefixes:
            if text == prefix:
                return category, 999
            if text.startswith(prefix):
                limit = parse_batch_use_limit(text[len(prefix):])
                if limit is not None:
                    return category, limit
    direct_mapping = [
        ("丹药", PILL_USE_PREFIXES),
        ("灵石", STONE_USE_PREFIXES),
        ("灵食", FOOD_USE_PREFIXES),
        ("妖丹", DEMON_CORE_USE_PREFIXES),
    ]
    for category, prefixes in direct_mapping:
        for prefix in prefixes:
            if not text.startswith(prefix):
                continue
            rest = text[len(prefix):].strip()
            if rest and any(word in rest for word in BATCH_USE_ALL_WORDS):
                return category, 999
    return None


def parse_item_use(text: str) -> Optional[tuple[str, int]]:
    mapping = [
        ("丹药", PILL_USE_PREFIXES),
        ("符箓", TALISMAN_USE_PREFIXES),
        ("灵石", STONE_USE_PREFIXES),
        ("灵食", FOOD_USE_PREFIXES),
        ("妖丹", DEMON_CORE_USE_PREFIXES),
        ("奇物", CURIO_USE_PREFIXES),
        ("杂物", MISC_USE_PREFIXES),
    ]
    for category, prefixes in mapping:
        index = parse_prefixed_index(text, prefixes)
        if index is not None:
            return category, index
    return None


def parse_acquired_root_command(text: str) -> Optional[tuple[str, Optional[int]]]:
    if text in ACQUIRED_ROOT_TEXTS:
        return ("status", None)
    dan_index = parse_prefixed_index(text, DAN_ROOT_PREFIXES)
    if dan_index is not None:
        return ("dan", dan_index)
    artifact_index = parse_prefixed_index(text, ARTIFACT_ROOT_PREFIXES)
    if artifact_index is not None:
        return ("artifact", artifact_index)
    return None


def is_acquired_root_command_text(text: str) -> bool:
    return parse_acquired_root_command(text) is not None


def parse_prefixed_name(text: str, prefixes: tuple[str, ...]) -> Optional[str]:
    for prefix in prefixes:
        if text == prefix:
            return ""
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return None


def parse_shop_buy_index(text: str) -> Optional[int]:
    return parse_prefixed_index(text, BUY_PREFIXES)


def parse_sell_item(text: str) -> Optional[tuple[str, int]]:
    categories = ("灵器", "功法", "丹药", "阵盘", "灵材", "符箓", "傀儡", "灵植", "灵石", "杂物", "奇物", "灵食", "神通")
    for prefix in SELL_PREFIXES:
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix):].strip()
        for category in categories:
            if rest.startswith(category):
                match = re.search(r"\d+", rest[len(category):].strip())
                if match:
                    return category, int(match.group(0))
    return None


def parse_alchemy_name(text: str) -> Optional[str]:
    stripped = text.strip()
    if stripped == "炼丹":
        return ""
    for prefix in ALCHEMY_PREFIXES:
        if stripped.startswith(f"{prefix} "):
            return stripped[len(prefix):].strip()
    return None


def parse_talisman_draw_index(text: str) -> Optional[int]:
    stripped = text.strip()
    if stripped in TALISMAN_DRAW_TEXTS:
        return 0
    for prefix in TALISMAN_DRAW_PREFIXES:
        if not stripped.startswith(prefix):
            continue
        rest = stripped[len(prefix):].strip()
        if not rest:
            return 0
        match = re.search(r"\d+", rest)
        if match:
            return int(match.group(0))
    return None


def parse_short_index_text(text: str) -> Optional[int]:
    aliases = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
    stripped = text.strip()
    if stripped in aliases:
        return aliases[stripped]
    if re.fullmatch(r"\d+", stripped):
        return int(stripped)
    match = re.fullmatch(r"(?:选择|进入|秘境)\s*(\d+|[一二三四五])", stripped)
    if not match:
        return None
    token = match.group(1)
    return aliases.get(token, int(token) if token.isdigit() else None)


def conversation_pending_key(event: MessageEvent) -> str:
    if isinstance(event, GroupMessageEvent):
        return f"group:{event.group_id}:{event.get_user_id()}"
    return f"private:{event.get_user_id()}"


def is_equip_method_command_text(text: str) -> bool:
    return is_prefixed_index_command(text, METHOD_EQUIP_PREFIXES)


def is_method_detail_command_text(text: str) -> bool:
    return is_prefixed_index_command(text, METHOD_DETAIL_PREFIXES)


def is_normal_duel_apply_text(text: str) -> bool:
    return text.strip() in NORMAL_DUEL_TEXTS


def is_equip_array_command_text(text: str) -> bool:
    return is_prefixed_index_command(text, ARRAY_EQUIP_PREFIXES)


def is_duel_command_text(text: str) -> bool:
    stripped = text.strip()
    lowered = stripped.lower()
    return lowered.startswith("pk") or any(stripped.startswith(prefix) for prefix in DUEL_PREFIXES[2:])


def parse_duel_target(event: MessageEvent) -> Optional[str]:
    targets = at_user_ids(event)
    if targets:
        return targets[0]
    text = normalized_plain_text(event)
    match = re.search(r"(?:pk|PK|切磋|挑战)\s*(\d{5,})", text)
    return match.group(1) if match else None
