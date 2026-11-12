"""消息判定规则与全局预处理器（R-18）。

is_*_message 把「这句话是不是某个命令」的判断集中在此，供 matchers.py 复用；
另含秘境战斗期间阻断其他插件的 event_preprocessor。"""
from __future__ import annotations

import time

from nonebot import get_bot, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, PrivateMessageEvent
from nonebot.exception import ActionFailed, IgnoredException, NetworkError
from nonebot.message import event_preprocessor

from ..domain import CANCEL_WORDS, CONFIRM_WORDS
from ..mystic_runtime import parse_mystic_group_command, parse_mystic_private_command
from ..state import (
    beast_realm_private_routes,
    beast_realm_tables,
    mystic_coordinator,
    pending_fishing_users,
    store,
)
from .beast import beast_realm_group_key_from_event
from .doudizhu import is_doudizhu_command_text
from .duel import group_duel_session
from .panels import panel_segment
from .parsing import (
    is_acquired_root_command_text,
    is_alchemy_command_text,
    is_array_deduction_command_text,
    is_dual_cultivation_command_text,
    is_duel_command_text,
    is_equip_array_command_text,
    is_equip_command_text,
    is_equip_method_command_text,
    is_equip_puppet_command_text,
    is_equip_talisman_command_text,
    is_immortal_seed_command_text,
    is_item_use_command_text,
    is_life_artifact_command_text,
    is_market_command_text,
    is_method_detail_command_text,
    is_normal_duel_apply_text,
    is_plant_command_text,
    is_refining_command_text,
    is_rescue_command_text,
    is_route_command_text,
    is_shop_command_text,
    is_special_ability_command_text,
    is_special_ability_learn_command_text,
    is_spirit_liquid_use_command_text,
    is_talisman_draw_command_text,
    is_task_command_text,
    is_tianji_mystic_command_text,
    is_trade_command_text,
    normal_duel_action_text,
    normalized_plain_text,
    parse_catalog_query,
    parse_fishing_arg,
)
from .texts import (
    ADVENTURE_TEXTS,
    ARRAY_LIST_TEXTS,
    ARTIFACT_LIST_TEXTS,
    BREAKTHROUGH_TEXTS,
    CATALOG_TEXTS,
    CULTIVATION_RANK_TEXTS,
    EMPEROR_CATALOG_TEXTS,
    HELP_TEXTS,
    ITEM_LIST_TEXTS,
    MAKEUP_SIGN_PREFIXES,
    METHOD_LIST_TEXTS,
    NEWBIE_TUTORIAL_TEXTS,
    PLANT_LIST_TEXTS,
    POWER_RANK_TEXTS,
    POWER_TEXTS,
    PUPPET_LIST_TEXTS,
    SIGNIN_CALENDAR_TEXTS,
    SIGNIN_TEXTS,
    STATUS_TEXTS,
    UNEQUIP_TEXTS,
)
from .. import beast_realm as beast_realm_game


def is_managed_command_text(text: str) -> bool:
    return (
        parse_mystic_group_command(text) is not None
        or text in SIGNIN_TEXTS
        or text in STATUS_TEXTS
        or text in HELP_TEXTS
        or text in NEWBIE_TUTORIAL_TEXTS
        or text in CATALOG_TEXTS
        or parse_catalog_query(text) is not None
        or text in BREAKTHROUGH_TEXTS
        or text in CULTIVATION_RANK_TEXTS
        or text in POWER_RANK_TEXTS
        or text in POWER_TEXTS
        or text in ADVENTURE_TEXTS
        or text in ARTIFACT_LIST_TEXTS
        or text in METHOD_LIST_TEXTS
        or text in ARRAY_LIST_TEXTS
        or text in PUPPET_LIST_TEXTS
        or text in PLANT_LIST_TEXTS
        or text in ITEM_LIST_TEXTS
        or is_acquired_root_command_text(text)
        or is_special_ability_command_text(text)
        or is_special_ability_learn_command_text(text)
        or is_route_command_text(text)
        or is_task_command_text(text)
        or is_shop_command_text(text)
        or is_alchemy_command_text(text)
        or is_refining_command_text(text)
        or is_array_deduction_command_text(text)
        or is_life_artifact_command_text(text)
        or is_immortal_seed_command_text(text)
        or text in EMPEROR_CATALOG_TEXTS
        or is_trade_command_text(text)
        or is_market_command_text(text)
        or is_rescue_command_text(text)
        or is_talisman_draw_command_text(text)
        or is_tianji_mystic_command_text(text)
        or is_doudizhu_command_text(text)
        or beast_realm_game.is_beast_realm_group_command(text)
        or beast_realm_game.is_beast_realm_private_command(text)
        or is_dual_cultivation_command_text(text)
        or text in UNEQUIP_TEXTS
        or is_equip_talisman_command_text(text)
        or parse_fishing_arg(text) is not None
        or is_equip_command_text(text)
        or is_equip_method_command_text(text)
        or is_method_detail_command_text(text)
        or is_normal_duel_apply_text(text)
        or is_equip_array_command_text(text)
        or is_equip_puppet_command_text(text)
        or is_plant_command_text(text)
        or is_item_use_command_text(text)
        or is_spirit_liquid_use_command_text(text)
        or is_duel_command_text(text)
    )

async def is_help_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in HELP_TEXTS


async def is_newbie_tutorial_message(event: MessageEvent) -> bool:
    return isinstance(event, PrivateMessageEvent) and normalized_plain_text(event) in NEWBIE_TUTORIAL_TEXTS

async def is_catalog_message(event: MessageEvent) -> bool:
    text = normalized_plain_text(event)
    return text in CATALOG_TEXTS or parse_catalog_query(text) is not None


async def is_signin_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in SIGNIN_TEXTS


async def is_signin_calendar_message(event: MessageEvent) -> bool:
    text = normalized_plain_text(event)
    if text in SIGNIN_CALENDAR_TEXTS:
        return True
    return any(text.startswith(word) for word in SIGNIN_CALENDAR_TEXTS)


async def is_makeup_sign_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event).startswith(MAKEUP_SIGN_PREFIXES)


async def is_status_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in STATUS_TEXTS


async def is_breakthrough_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in BREAKTHROUGH_TEXTS


async def is_puppet_list_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in PUPPET_LIST_TEXTS


async def is_plant_list_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in PLANT_LIST_TEXTS


async def is_item_list_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in ITEM_LIST_TEXTS


async def is_special_ability_message(event: MessageEvent) -> bool:
    return is_special_ability_command_text(normalized_plain_text(event))


async def is_special_ability_learn_message(event: MessageEvent) -> bool:
    return is_special_ability_learn_command_text(normalized_plain_text(event))


async def is_route_message(event: MessageEvent) -> bool:
    return is_route_command_text(normalized_plain_text(event))


async def is_task_message(event: MessageEvent) -> bool:
    return is_task_command_text(normalized_plain_text(event))


async def is_shop_message(event: MessageEvent) -> bool:
    return is_shop_command_text(normalized_plain_text(event))


async def is_alchemy_message(event: MessageEvent) -> bool:
    return is_alchemy_command_text(normalized_plain_text(event))



async def is_refining_message(event: MessageEvent) -> bool:
    return is_refining_command_text(normalized_plain_text(event))


async def is_array_deduction_message(event: MessageEvent) -> bool:
    return is_array_deduction_command_text(normalized_plain_text(event))


async def is_life_artifact_message(event: MessageEvent) -> bool:
    return is_life_artifact_command_text(normalized_plain_text(event))


async def is_immortal_seed_message(event: MessageEvent) -> bool:
    return is_immortal_seed_command_text(normalized_plain_text(event))


async def is_emperor_catalog_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in EMPEROR_CATALOG_TEXTS


async def is_trade_message(event: MessageEvent) -> bool:
    return is_trade_command_text(normalized_plain_text(event))


async def is_market_message(event: MessageEvent) -> bool:
    return is_market_command_text(normalized_plain_text(event))


async def is_rescue_message(event: MessageEvent) -> bool:
    return is_rescue_command_text(normalized_plain_text(event))

async def is_talisman_draw_message(event: MessageEvent) -> bool:
    return is_talisman_draw_command_text(normalized_plain_text(event))


async def is_tianji_mystic_message(event: MessageEvent) -> bool:
    return is_tianji_mystic_command_text(normalized_plain_text(event))


async def is_mystic_group_message(event: MessageEvent) -> bool:
    return (
        isinstance(event, GroupMessageEvent)
        and parse_mystic_group_command(normalized_plain_text(event)) is not None
    )


async def is_mystic_private_message(event: MessageEvent) -> bool:
    if not isinstance(event, PrivateMessageEvent):
        return False
    return await mystic_coordinator.accepts_private_message(
        event.get_user_id(),
        normalized_plain_text(event),
    )


@event_preprocessor
async def block_other_plugins_during_mystic_battle(event: MessageEvent) -> None:
    """秘境战斗进行时，屏蔽其它插件对该玩家私聊指令的响应。

    NoneBot 没有“全局暂停其它插件”的 API，这里用事件预处理器实现：在所有
    matcher 运行前检查——若该玩家正处于秘境战斗相关阶段，且本次私聊不是秘境
    自己的指令，就给一条提示并抛 IgnoredException 终止事件传播，避免签到、
    装备、炼化等指令在战斗中途打断状态。秘境自己的指令正常放行。
    """
    if not isinstance(event, PrivateMessageEvent):
        return
    user_id = event.get_user_id()
    try:
        in_battle = await mystic_coordinator.is_in_mystic_battle(user_id)
    except Exception as exc:  # noqa: BLE001 — 预处理器异常会丢弃整条事件，必须失败放行
        logger.warning(f"秘境战斗屏蔽检查失败，放行事件：{exc!r}")
        return
    if not in_battle:
        return
    text = normalized_plain_text(event)
    # 是秘境自己的私聊指令 → 放行，交给 mystic_private_cmd 处理
    if parse_mystic_private_command(text) is not None:
        return
    try:
        await get_bot().send_private_msg(
            user_id=int(user_id),
            message=panel_segment(
                "秘境战斗中",
                "你正在进行秘境战斗，请先完成当前战斗（确认配装 / 普通攻击 / 秘境技能 / 自动战斗）。\n如需查看状态，发送“秘境状态”。",
                icon="mystic",
            ),
        )
    except (ActionFailed, NetworkError, RuntimeError, ValueError):
        logger.debug(f"秘境战斗拦截提示发送失败: {user_id}")
    raise IgnoredException("玩家正在进行秘境战斗，已拦截其它私聊指令")


async def is_dual_cultivation_message(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) and is_dual_cultivation_command_text(normalized_plain_text(event))


async def is_equip_puppet_message(event: MessageEvent) -> bool:
    return is_equip_puppet_command_text(normalized_plain_text(event))


async def is_plant_message(event: MessageEvent) -> bool:
    return is_plant_command_text(normalized_plain_text(event))


async def is_item_use_message(event: MessageEvent) -> bool:
    return is_item_use_command_text(normalized_plain_text(event))


async def is_acquired_root_message(event: MessageEvent) -> bool:
    return is_acquired_root_command_text(normalized_plain_text(event))


async def is_spirit_liquid_use_message(event: MessageEvent) -> bool:
    return is_spirit_liquid_use_command_text(normalized_plain_text(event))


async def is_fishing_message(event: MessageEvent) -> bool:
    return parse_fishing_arg(normalized_plain_text(event)) is not None


async def is_fishing_reply(event: MessageEvent) -> bool:
    user_id = event.get_user_id()
    expires_at = pending_fishing_users.get(user_id)
    if expires_at is None:
        return False
    if expires_at < time.monotonic():
        pending_fishing_users.pop(user_id, None)
        return False
    text = normalized_plain_text(event).lower()
    if text not in CONFIRM_WORDS and text not in CANCEL_WORDS:
        return False
    record = await store.get_user(user_id)
    if record.fishing_chances <= 0:
        pending_fishing_users.pop(user_id, None)
        return False
    return True


async def is_group_chat_for_rank(event: MessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    text = normalized_plain_text(event)
    if not text:
        return False
    return not is_managed_command_text(text)


async def is_cultivation_rank_message(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) and normalized_plain_text(event) in CULTIVATION_RANK_TEXTS


async def is_power_rank_message(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) and normalized_plain_text(event) in POWER_RANK_TEXTS


async def is_power_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in POWER_TEXTS


async def is_adventure_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in ADVENTURE_TEXTS


async def is_artifact_list_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in ARTIFACT_LIST_TEXTS


async def is_method_list_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in METHOD_LIST_TEXTS


async def is_array_list_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in ARRAY_LIST_TEXTS


async def is_equip_artifact_message(event: MessageEvent) -> bool:
    return is_equip_command_text(normalized_plain_text(event))


async def is_equip_talisman_message(event: MessageEvent) -> bool:
    return is_equip_talisman_command_text(normalized_plain_text(event))


async def is_equip_method_message(event: MessageEvent) -> bool:
    return is_equip_method_command_text(normalized_plain_text(event))


async def is_method_detail_message(event: MessageEvent) -> bool:
    return is_method_detail_command_text(normalized_plain_text(event))


async def is_normal_duel_apply_message(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) and is_normal_duel_apply_text(normalized_plain_text(event))


async def is_normal_duel_chat_message(event: MessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    plain_text = normalized_plain_text(event)
    action_text = normal_duel_action_text(event)
    if not action_text:
        return False
    if plain_text and is_managed_command_text(plain_text):
        return False
    session = group_duel_session(str(event.group_id))
    if not session or not session.get("active"):
        return False
    return event.get_user_id() in {str(session.get("left_id")), str(session.get("right_id"))}


async def is_equip_array_message(event: MessageEvent) -> bool:
    return is_equip_array_command_text(normalized_plain_text(event))




async def is_duel_message(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) and is_duel_command_text(normalized_plain_text(event))



async def is_beast_realm_group_message(event: MessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    text = normalized_plain_text(event)
    if not text:
        return False
    group_key = beast_realm_group_key_from_event(event)
    return beast_realm_game.is_beast_realm_group_command(text) or (
        group_key in beast_realm_tables and beast_realm_game.is_beast_realm_group_command(text)
    )


async def is_beast_realm_private_message(event: MessageEvent) -> bool:
    if not isinstance(event, PrivateMessageEvent):
        return False
    text = normalized_plain_text(event)
    if beast_realm_game.is_beast_realm_private_entry_command(text):
        return True
    if not beast_realm_game.is_beast_realm_private_command(text):
        return False
    group_key = beast_realm_private_routes.get(event.get_user_id())
    if not group_key:
        return False
    table = beast_realm_tables.get(group_key)
    if not table or table.get("phase") not in {"lobby", "recruit"}:
        return False
    player = beast_realm_game.table_player(table, event.get_user_id())
    return bool(player and not player.get("bot"))
