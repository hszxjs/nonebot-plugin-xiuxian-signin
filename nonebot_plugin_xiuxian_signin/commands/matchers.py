"""matcher 注册表（R-18）。

只做「把规则函数绑到 on_message」这一件事。规则本身在 rules.py，
handler 在 handlers/ 下。注册顺序即同优先级下的匹配顺序，改动前先看测试。"""
from __future__ import annotations

from nonebot import on_message
from nonebot.rule import Rule

from .rules import (
    is_acquired_root_message,
    is_adventure_message,
    is_alchemy_message,
    is_array_deduction_message,
    is_array_list_message,
    is_artifact_list_message,
    is_beast_realm_group_message,
    is_beast_realm_private_message,
    is_breakthrough_message,
    is_catalog_message,
    is_cultivation_rank_message,
    is_dual_cultivation_message,
    is_duel_message,
    is_emperor_catalog_message,
    is_equip_array_message,
    is_equip_artifact_message,
    is_equip_method_message,
    is_equip_puppet_message,
    is_equip_talisman_message,
    is_fishing_message,
    is_fishing_reply,
    is_group_chat_for_rank,
    is_help_message,
    is_immortal_seed_message,
    is_item_list_message,
    is_item_use_message,
    is_life_artifact_message,
    is_makeup_sign_message,
    is_market_message,
    is_method_detail_message,
    is_method_list_message,
    is_mystic_group_message,
    is_mystic_private_message,
    is_newbie_tutorial_message,
    is_normal_duel_apply_message,
    is_normal_duel_chat_message,
    is_plant_list_message,
    is_plant_message,
    is_power_message,
    is_power_rank_message,
    is_puppet_list_message,
    is_refining_message,
    is_rescue_message,
    is_route_message,
    is_shop_message,
    is_signin_calendar_message,
    is_signin_message,
    is_special_ability_learn_message,
    is_special_ability_message,
    is_spirit_liquid_use_message,
    is_status_message,
    is_talisman_draw_message,
    is_task_message,
    is_tianji_mystic_message,
    is_trade_message,
)


beast_realm_group_cmd = on_message(rule=Rule(is_beast_realm_group_message), priority=10, block=True)


beast_realm_private_cmd = on_message(rule=Rule(is_beast_realm_private_message), priority=7, block=True)


mystic_group_cmd = on_message(rule=Rule(is_mystic_group_message), priority=8, block=True)


mystic_private_cmd = on_message(rule=Rule(is_mystic_private_message), priority=6, block=True)


help_cmd = on_message(rule=Rule(is_help_message), priority=10, block=True)


newbie_tutorial_cmd = on_message(rule=Rule(is_newbie_tutorial_message), priority=10, block=True)


catalog_cmd = on_message(rule=Rule(is_catalog_message), priority=10, block=True)


signin = on_message(rule=Rule(is_signin_message), priority=10, block=True)


signin_calendar = on_message(rule=Rule(is_signin_calendar_message), priority=10, block=True)


makeup_sign_cmd = on_message(rule=Rule(is_makeup_sign_message), priority=10, block=True)


status = on_message(rule=Rule(is_status_message), priority=10, block=True)


breakthrough_cmd = on_message(rule=Rule(is_breakthrough_message), priority=10, block=True)


puppet_list = on_message(rule=Rule(is_puppet_list_message), priority=10, block=True)


plant_list = on_message(rule=Rule(is_plant_list_message), priority=10, block=True)


item_list = on_message(rule=Rule(is_item_list_message), priority=10, block=True)


special_ability_cmd = on_message(rule=Rule(is_special_ability_message), priority=10, block=True)


special_ability_learn_cmd = on_message(rule=Rule(is_special_ability_learn_message), priority=10, block=True)


route_cmd = on_message(rule=Rule(is_route_message), priority=10, block=True)


task_cmd = on_message(rule=Rule(is_task_message), priority=10, block=True)


shop_cmd = on_message(rule=Rule(is_shop_message), priority=10, block=True)


alchemy_cmd = on_message(rule=Rule(is_alchemy_message), priority=10, block=True)


refining_cmd = on_message(rule=Rule(is_refining_message), priority=10, block=True)


array_deduction_cmd = on_message(rule=Rule(is_array_deduction_message), priority=10, block=True)


life_artifact_cmd = on_message(rule=Rule(is_life_artifact_message), priority=10, block=True)


immortal_seed_cmd = on_message(rule=Rule(is_immortal_seed_message), priority=10, block=True)


emperor_catalog_cmd = on_message(rule=Rule(is_emperor_catalog_message), priority=10, block=True)


trade_cmd = on_message(rule=Rule(is_trade_message), priority=10, block=True)


market_cmd = on_message(rule=Rule(is_market_message), priority=10, block=True)


rescue_cmd = on_message(rule=Rule(is_rescue_message), priority=10, block=True)


talisman_draw_cmd = on_message(rule=Rule(is_talisman_draw_message), priority=10, block=True)


tianji_mystic_cmd = on_message(rule=Rule(is_tianji_mystic_message), priority=10, block=True)


dual_cultivation_cmd = on_message(rule=Rule(is_dual_cultivation_message), priority=10, block=True)


equip_puppet_cmd = on_message(rule=Rule(is_equip_puppet_message), priority=10, block=True)


plant_cmd = on_message(rule=Rule(is_plant_message), priority=10, block=True)


item_use_cmd = on_message(rule=Rule(is_item_use_message), priority=10, block=True)


acquired_root_cmd = on_message(rule=Rule(is_acquired_root_message), priority=10, block=True)


spirit_liquid_use_cmd = on_message(rule=Rule(is_spirit_liquid_use_message), priority=10, block=True)


fishing = on_message(rule=Rule(is_fishing_message), priority=10, block=True)


fishing_reply = on_message(rule=Rule(is_fishing_reply), priority=9, block=True)


cultivation_rank = on_message(rule=Rule(is_cultivation_rank_message), priority=10, block=True)


power_rank = on_message(rule=Rule(is_power_rank_message), priority=10, block=True)


power_status = on_message(rule=Rule(is_power_message), priority=10, block=True)


adventure = on_message(rule=Rule(is_adventure_message), priority=10, block=True)


artifact_list = on_message(rule=Rule(is_artifact_list_message), priority=10, block=True)


method_list = on_message(rule=Rule(is_method_list_message), priority=10, block=True)


method_detail_cmd = on_message(rule=Rule(is_method_detail_message), priority=10, block=True)


normal_duel_apply = on_message(rule=Rule(is_normal_duel_apply_message), priority=10, block=True)


normal_duel_chat = on_message(rule=Rule(is_normal_duel_chat_message), priority=8, block=False)


array_list = on_message(rule=Rule(is_array_list_message), priority=10, block=True)


equip_artifact_cmd = on_message(rule=Rule(is_equip_artifact_message), priority=10, block=True)


equip_talisman_cmd = on_message(rule=Rule(is_equip_talisman_message), priority=10, block=True)


equip_method_cmd = on_message(rule=Rule(is_equip_method_message), priority=10, block=True)


equip_array_cmd = on_message(rule=Rule(is_equip_array_message), priority=10, block=True)


duel = on_message(rule=Rule(is_duel_message), priority=10, block=True)


chat_rank_counter = on_message(rule=Rule(is_group_chat_for_rank), priority=99, block=False)
