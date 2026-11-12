from __future__ import annotations

# NoneBot plugins must be required before importing their dependent modules.
# ruff: noqa: E402

import asyncio
import sys
from collections import Counter
import random
import re
import time
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

try:
    import httpx
except ImportError:
    httpx = None

from nonebot import get_bot, get_driver, logger, on_message, require

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as localstore
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, MessageSegment, PrivateMessageEvent
from nonebot.exception import ActionFailed, IgnoredException, NetworkError
from nonebot.matcher import Matcher
from nonebot.message import event_preprocessor
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from . import beast_realm as beast_realm_game
from .cards import render_adventure_card, render_battle_card, render_fishing_card, render_in_thread, render_signin_calendar_card, render_signin_card, render_text_panel, set_font_paths
from .config import Config
from .domain import (
    CANCEL_WORDS,
    CONFIRM_WORDS,
    ARTIFACT_REFINING_RECIPES,
    IMMORTAL_SEED_INFOS,
    BREAKTHROUGH_REQUIREMENTS,
    FISHING_REWARDS,
    REALMS,
    RankReward,
    SigninResult,
    acquired_root_summary,
    acquired_root_text,
    alchemy_text,

    apply_chat_cultivation,

    apply_dual_cultivation,
    apply_fishing,
    apply_rank_reward,
    apply_signin,
    artifact_power,
    artifact_realm_catalog_summary_text,
    item_required_realm_index,
    array_layer,
    array_layer_cap_text,
    array_multiplier,
    array_proficiency_cap,
    array_proficiency_value,
    available_arrays,
    available_artifacts,

    available_materials,
    available_special_ability_items,
    available_curios,
    available_foods,
    available_methods,
    available_misc_items,
    available_pills,
    available_plants,
    available_puppets,
    available_spirit_stones,
    available_talismans,
    available_battle_techniques,
    battle_power,
    battle_summary,
    breakthrough_realm,
    breakthrough_requirement_key_for_realm_index,
    breakthrough_source_realm_index,
    breakthrough_target_realm,
    breakthrough_target_realm_index,
    breakthrough_item_quality_cap_text,
    breakthrough_quality_relation_text,
    breakthrough_status,
    catalog_item_detail_text,

    buy_shop_item,

    choose_cultivation_route,

    choose_evil_cultivation,

    choose_faction_identity,
    combat_max_mana,

    complete_daily_task,

    daily_tasks_text,
    draw_talisman_by_index,
    duel_records,
    equip_array,
    equip_artifact,
    equip_method,
    equip_puppet,
    equip_talisman,
    simulate_normal_duel,
    method_profile,
    format_method_detail,
    ensure_combat_profile,
    fishing_count_from_text,
    identify_misc_item,
    learn_special_ability,
    market_offer_price,
    method_power,
    technique_cooldown,
    technique_mana_cost,
    plant_spirit_plant,
    pop_reward_by_category_index,
    puppet_power,
    rank_reward_for,

    array_deduction_text,
    batch_sell_rewards,
    batch_sell_low_realm_artifacts,
    deduce_array,
    emperor_artifact_catalog_text,
    equip_immortal_seed,
    immortal_seed_text,
    is_unique_reward,
    make_unique_replica,
    refine_artifact_by_recipe,
    refining_text,
    set_life_artifact,
    refine_pill_by_recipe,
    refine_dan_root,
    refine_artifact_root,
    regress_cultivation,
    refine_spirit_stone,
    refine_demon_core,
    refine_spirit_stones_batch,
    refine_demon_cores_batch,
    refine_spirit_liquid,
    reward_display_name,

    route_status_text,

    sell_reward,

    shop_items_for_date,

    special_ability_catalog_text,
    special_ability_list_text,
    spirit_stone_text,
    makeup_price,
    makeup_sign,
    makeup_used_this_month,
    signin_streak,
    talisman_draw_text,
    unequip_artifact,
    unequip_talisman,
    use_curio,
    use_food,
    use_foods_batch,
    use_pill,
    use_pills_batch,
    use_talisman,
)
from .admin import AdminManager, install_admin_routes, start_admin_server
from .mystic_battle import MysticBattleService
from .mystic_cards import MysticMapRenderer, render_no_token_panel
from .mystic_dungeon import (
    DungeonMode,
    DungeonPhase,
    DungeonRisk,
    MysticDungeonService,
    MysticTemplateCatalog,
    active_mystic_gameplay_config,
    active_mystic_theme_ids,
    default_mystic_gameplay_config,
)
from .domain.rewards import reward_count_by_names
from .mystic_menu import MYSTIC_HELP_SUMMARY, MYSTIC_PICMENU_ENTRY
from .mystic_runtime import (
    DungeonEntryOffer,
    MysticCommandCoordinator,
    MysticCommandResult,
    parse_mystic_group_command,
    parse_mystic_private_command,
)
from .storage import InsufficientSpiritStones, JsonStore, MysticRescueRequest
from .net import close_shared_http_client
from .resource_pack import configure as configure_resource_pack
from .resource_pack import ensure_pack, pack_status as resource_pack_status
from . import state as _state  # 共享单例（config/store/admin_manager/mystic_coordinator 等）
from .state import (  # noqa: F401
    config, store, admin_manager, mystic_coordinator, mystic_catalog,
    local_now, local_today, get_data_dir,
    pending_fishing_users,
    normal_duel_queue, normal_duel_sessions,
    doudizhu_tables, beast_realm_tables, beast_realm_private_routes,
)

# 斗地主命令子模块（import 即注册 matcher）；提供 is_doudizhu_command_text 供兜底判定。
from .commands import doudizhu as _doudizhu_cmd_module  # noqa: E402,F401
from .commands.doudizhu import is_doudizhu_command_text  # noqa: E402
_doudizhu_cmd_module._g = sys.modules[__name__]  # noqa: E402  # 注入入口模块供延迟访问 helper

# --- 命令子模块（R-18 拆分）-------------------------------------------------
# 入口只保留插件元数据、matcher 注册与生命周期钩子，具体实现按域放在
# commands/ 下。此处集中回导，供本文件剩余的 handler 与 commands/doudizhu.py
# 的延迟引用（_g）继续使用；handler 全部迁出后这组回导可以整段删除。
from .commands.texts import (  # noqa: F401
    ACQUIRED_ROOT_TEXTS,
    ADVENTURE_TEXTS,
    ALCHEMY_PREFIXES,
    ALCHEMY_TEXTS,
    ARRAY_DEDUCTION_PREFIXES,
    ARRAY_DEDUCTION_TEXTS,
    ARRAY_EQUIP_PREFIXES,
    ARRAY_LIST_TEXTS,
    ARTIFACT_LIST_TEXTS,
    ARTIFACT_ROOT_PREFIXES,
    ARTIFACT_SLOT_NAMES,
    BATCH_SELL_PREFIXES,
    BATCH_USE_ALL_WORDS,
    BREAKTHROUGH_TEXTS,
    BUY_PREFIXES,
    CATALOG_QUERY_PREFIXES,
    CATALOG_TEXTS,
    COMMAND_PREFIX_CHARS,
    CULTIVATION_RANK_TEXTS,
    CURIO_USE_PREFIXES,
    DAN_ROOT_PREFIXES,
    DEMON_CORE_BATCH_USE_PREFIXES,
    DEMON_CORE_USE_PREFIXES,
    DUEL_PREFIXES,
    EMPEROR_CATALOG_TEXTS,
    EQUIP_PREFIXES,
    EVIL_QUIT_TEXTS,
    EVIL_SELECT_TEXTS,
    FISHING_TEXTS,
    FOOD_BATCH_USE_PREFIXES,
    FOOD_USE_PREFIXES,
    HELP_TEXTS,
    IDENTITY_SELECT_PREFIXES,
    IMMORTAL_SEED_EQUIP_PREFIXES,
    IMMORTAL_SEED_TEXTS,
    ITEM_LIST_TEXTS,
    LIFE_ARTIFACT_PREFIXES,
    LOW_REALM_ARTIFACT_BATCH_SELL_PREFIXES,
    MAKEUP_SIGN_PREFIXES,
    MARKET_BUY_PREFIXES,
    MARKET_CANCEL_PREFIXES,
    MARKET_OFFER_PREFIXES,
    MARKET_TEXTS,
    METHOD_DETAIL_PREFIXES,
    METHOD_EQUIP_PREFIXES,
    METHOD_LIST_TEXTS,
    MISC_USE_PREFIXES,
    NEWBIE_TUTORIAL_TEXTS,
    NORMAL_DUEL_ACTION_SEGMENT_LABELS,
    NORMAL_DUEL_DURATION_SECONDS,
    NORMAL_DUEL_IGNORED_SEGMENT_TYPES,
    NORMAL_DUEL_PREPARE_SECONDS,
    NORMAL_DUEL_TEXTS,
    PENDING_FISHING_TTL,
    PILL_BATCH_USE_PREFIXES,
    PILL_USE_PREFIXES,
    PLANT_EQUIP_PREFIXES,
    PLANT_LIST_TEXTS,
    POWER_RANK_TEXTS,
    POWER_TEXTS,
    PUPPET_EQUIP_PREFIXES,
    PUPPET_LIST_TEXTS,
    RANK_SETTLE_HOUR,
    RANK_SETTLE_MINUTE,
    REFINING_PREFIXES,
    REFINING_TEXTS,
    RESCUE_REQUEST_PREFIXES,
    RESCUE_TAKE_PREFIXES,
    ROUTE_SELECT_PREFIXES,
    ROUTE_TEXTS,
    SELL_PREFIXES,
    SHOP_TEXTS,
    SIGNIN_CALENDAR_TEXTS,
    SIGNIN_TEXTS,
    SPECIAL_ABILITY_CATALOG_TEXTS,
    SPECIAL_ABILITY_LEARN_PREFIXES,
    SPECIAL_ABILITY_TEXTS,
    SPIRIT_LIQUID_USE_PREFIXES,
    STATUS_TEXTS,
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
from .commands.parsing import (  # noqa: F401
    TRADE_CATEGORIES,
    at_user_ids,
    conversation_pending_key,
    group_member_display_name,
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
    is_prefixed_index_command,
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
    nickname_from_event,
    normal_duel_action_text,
    normalized_plain_text,
    parse_acquired_root_command,
    parse_alchemy_name,
    parse_array_deduction_index,
    parse_artifact_slot,
    parse_batch_item_use,
    parse_batch_sell,
    parse_batch_use_limit,
    parse_catalog_query,
    parse_duel_target,
    parse_equip_artifact_command,
    parse_equip_index,
    parse_equip_talisman_index,
    parse_fishing_arg,
    parse_immortal_seed_equip_index,
    parse_item_use,
    parse_life_artifact_index,
    parse_low_realm_artifact_batch_sell,
    parse_market_buy,
    parse_market_cancel,
    parse_market_offer,
    parse_prefixed_index,
    parse_prefixed_name,
    parse_refining_name,
    parse_rescue_request,
    parse_rescue_take,
    parse_sell_item,
    parse_shop_buy_index,
    parse_short_index_text,
    parse_spirit_liquid_use,
    parse_talisman_draw_index,
    parse_trade_accept,
    parse_trade_cancel,
    parse_trade_offer,
    parse_unequip_artifact_slot,
    remember_group_member,
    short_name,
)
from .commands.panels import (  # noqa: F401
    BEAST_REALM_ICON,
    build_fishing_image,
    build_signin_calendar_image,
    build_signin_image,
    finish_panel,
    finish_private_or_current_panel,
    panel_accent,
    panel_segment,
    parse_calendar_target,
    parse_makeup_target,
    send_image,
    send_panel,
    send_private_panel,
)
from .commands.duel import (  # noqa: F401
    _mystic_prepare_info,
    append_normal_duel_action,
    build_normal_duel_image,
    finish_normal_duel,
    group_duel_session,
    mystic_prepare_cards,
    normal_duel_prepare_cards,
    send_mystic_prepare_cards,
    send_normal_duel_prepare_cards,
    send_normal_duel_prepare_messages,
)
from .commands.ranking import (  # noqa: F401
    format_cultivation_rank,
    format_power_rank,
    group_cultivation_rank_entries,
    group_power_rank_entries,
    is_settle_time,
    rank_entries_from_group,
)
from .commands.formatting import (  # noqa: F401
    _is_likely_sent_despite_error,
    append_item_lines,
    format_adventure_panel,
    format_array_list,
    format_artifact_list,
    format_catalog_text,
    format_duel_result,
    format_help_text,
    format_item_list,
    format_method_list,
    format_newbie_tutorial_text,
    format_plant_list,
    format_power_status,
    format_puppet_list,
    format_rank_message,
    format_shop_panel,
    item_icon_for_category,
    item_list_display,
    reward_catalog_lines,
)
from .commands.beast import (  # noqa: F401
    beast_realm_group_id_from_key,
    beast_realm_group_key_from_event,
    cleanup_beast_realm_table,
    route_beast_realm_players,
    send_beast_realm_group_report,
    send_beast_realm_leader_panel,
    send_beast_realm_recruit_panels,
)
from .commands.rules import (  # noqa: F401
    block_other_plugins_during_mystic_battle,
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
    is_managed_command_text,
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

__version__ = "0.6.0"

PICMENU_NEXT_FUNCS = [
    {
        'func': '入门与状态',
        'trigger_method': '签到 / 面板 / 新手教程 / 帮助',
        'trigger_condition': '首次签到会抽取灵根；每天签到获得修为和 1 次垂钓',
        'brief_des': '开始修炼，查看个人境界、灵根、资源和新手说明',
        'detail_des': '`签到` 获得每日修为和灵河垂钓次数；`面板` 查看境界、灵根、修为、灵石和当前装备；私聊 `新手教程` 打开入门引导；`帮助` 查看完整说明。',
    },
    {
        'func': '历练面板',
        'trigger_method': '历练 / 历练面板 / 战力 / 灵器 / 功法 / 阵盘 / 神通',
        'trigger_condition': '签到入门后可查看；灵器、功法、阵盘、符箓和神通会影响战力',
        'brief_des': '汇总战力、装备槽位、功法阵盘、符箓、神通和常用历练入口',
        'detail_des': '`历练` 或 `历练面板` 会输出专用图片面板，集中展示主手、副手、护甲、本命灵器、功法、阵盘、傀儡、符箓、仙源、境界品相、神通与常用装备指令；`战力` 查看文字版战力计算。',
    },
    {
        'func': '背包与图鉴',
        'trigger_method': '背包 / 图鉴 / 神通 / 神通图鉴 / 灵器图鉴 / 功法图鉴 / 唯一装备图鉴',
        'trigger_condition': '图鉴无需拥有物品；背包编号以当前面板为准',
        'brief_des': '查看物品、用途、获取途径和已领悟神通',
        'detail_des': '`背包` 管理丹药、符箓、灵石、妖丹、灵食、奇物和材料；`图鉴 名称` 查询用途和故事；`神通` 查看传承材料；`神通图鉴` 查看可领悟路线。',
    },
    {
        'func': '修为与突破',
        'trigger_method': '突破 / 炼化灵液 / 炼化妖丹 1 / 后天灵根 / 散功',
        'trigger_condition': '境界圆满后进入瓶颈，需要对应突破道具',
        'brief_des': '处理瓶颈、灵液、妖丹和五行补全',
        'detail_des': '瓶颈后多余修为会凝成精纯灵液；`炼化灵液` 转回修为；`炼化妖丹 编号` 获得修为；化神破炼虚需要五行补全，可用 `后天灵根` 查看丹灵根和器灵根。',
    },
    {
        'func': '灵器与战力',
        'trigger_method': '灵器 / 装备灵器 1 主手 / 卸下灵器 / 祭炼本命灵器 1 / 战力',
        'trigger_condition': '灵器按境界绑定；同境界内凡品到天阶均可存在',
        'brief_des': '管理主手、副手、护甲、本命灵器和战力榜',
        'detail_des': '低境界只能装备本境界能驾驭的灵器；假仙后可获得仙器；仙帝兵和其他唯一装备归入唯一装备体系。发送 `战力` 查看当前计算。',
    },
    {
        'func': '功法与阵盘',
        'trigger_method': '功法 / 学习功法 1 / 参悟功法 1 / 阵盘 / 布置阵盘 1 / 阵法推演 1',
        'trigger_condition': '重复获得同名功法或阵盘会转为推演成长',
        'brief_des': '提升签到收益、技能倍率、阵法倍率和熟练度上限',
        'detail_des': '功法唯一存在，重复获得会推演升层；阵盘可升品升阶，熟练度继承。仙阶极品后可以继续无限推演。',
    },
    {
        'func': '炼丹炼器与符箓',
        'trigger_method': '炼丹 / 炼丹 筑基丹 / 炼器 / 炼器图鉴 / 绘制符箓 1',
        'trigger_condition': '炼丹师、炼器师等路线会开放对应制作能力',
        'brief_des': '制作丹药、灵器、阵盘、傀儡和符箓',
        'detail_des': '材料品阶和品质会影响成品；`炼器图鉴` 查看配方；`绘制符箓` 可制作普通符箓和突破符令。',
    },
    dict(MYSTIC_PICMENU_ENTRY),
    {
        'func': '御兽秘境',
        'trigger_method': '御兽秘境开局 PVE / 御兽秘境开局 PVP / 加入御兽秘境 / 御兽秘境图鉴',
        'trigger_condition': '群聊开局，私聊在任务堂招募随从；PVP/PVE均需4人，单人1V2在私聊开启',
        'brief_des': '类酒馆战棋的4人排位斗兽、4V4秘境演武与单人1V2试炼',
        'detail_des': '新版秘境固定地图按骰子前进，普通战斗在私聊中进行，Boss 以队伍人数分段并支持续战投票；战斗失败后可发布秘境救援。',
    },
    {
        'func': '路线与身份',
        'trigger_method': '修炼路线 / 选择路线 剑修 / 选择身份 天机阁弟子 / 双修 @群友',
        'trigger_condition': '主路线同一时间只能选择一种；身份有境界和签到天数门槛',
        'brief_des': '选择剑修、术修、炼丹师、炼器师、阵法师和身份令牌',
        'detail_des': '新版秘境固定地图按骰子前进，普通战斗在私聊中进行，Boss 以队伍人数分段并支持续战投票；战斗失败后可发布秘境救援。',
    },
    {
        'func': '交易与商店',
        'trigger_method': '商店 / 购买 1 / 出售 丹药 1 / 批量出售 杂物 20 / 批量出售低阶灵器 / 万宝楼 / 交易 @对方 灵器 1 100',
        'trigger_condition': '交易、万宝楼和排行榜主要在群聊使用',
        'brief_des': '购买、出售、公开寄售和玩家间交易',
        'detail_des': '`商店` 每日刷新；`批量出售低阶灵器` 会出售背包中低于自身境界的非唯一灵器，不影响已装备灵器；`万宝楼挂售 类别 编号` 公开寄售；`交易 @对方 类别 编号 价格` 指定交易；唯一装备不会被批量出售。',
    },
    {
        'func': '休闲与排行',
        'trigger_method': '斗地主 / 斗地主帮助 / 排行 / 战力榜',
        'trigger_condition': '休闲玩法不影响主线修炼；斗地主需群聊',
        'brief_des': '斗地主、修为榜、战力榜和每日话痨榜',
        'detail_des': '`斗地主帮助` 查看牌局规则；`排行`、`战力榜` 查看群内排名。',
    },
    {
        'func': '后台管理',
        'trigger_method': '浏览器访问 /xiuxian-admin',
        'trigger_condition': '服主需要在 NoneBot 后端启用管理页，可配置管理 Token',
        'brief_des': '查看和修改玩家档案、物品属性、灵器规则、秘境掉落配置',
        'detail_des': '新版秘境固定地图按骰子前进，普通战斗在私聊中进行，Boss 以队伍人数分段并支持续战投票；战斗失败后可发布秘境救援。',
    },
]


def command_hint(func: str) -> str:
    """根据功能分类名，返回底部命令提示文案。

    从 PICMENU_NEXT_FUNCS 中查找对应分组的 trigger_method，统一加上“可发送：”
    前缀，供查看类面板的 footer 使用，让玩家知道下一步可以发什么命令。
    """
    for entry in PICMENU_NEXT_FUNCS:
        if entry.get("func") == func:
            method = str(entry.get("trigger_method") or "").strip()
            if method:
                return f"可发送：{method}"
            break
    return ""


__plugin_meta__ = PluginMetadata(
    name="修仙签到",
    description="以图片面板输出的修仙签到、境界突破、灵器战力、功法阵盘、神通、秘境探索、交易和后台管理插件。",
    usage=(
        "入门：签到 / 面板 / 历练 / 新手教程 / 帮助，首次签到抽取灵根，每天获得修为和 1 次灵河垂钓\n"
        "修为：突破 / 炼化灵液 / 炼化妖丹 1 / 后天灵根，处理瓶颈、灵液、妖丹和五行补全\n"
        "背包：背包 / 图鉴 / 图鉴 名称，查看物品用途、故事、获取方式和制作素材\n"
        "灵器：灵器 / 装备灵器 1 主手 / 战力，灵器按境界绑定，假仙后可获得仙器\n"
        "功法阵盘：功法 / 参悟功法 1 / 阵法推演 1，重复获得会推演升层或升品\n"
        "神通：神通 / 神通图鉴 / 领悟神通 1，查看传承材料并在斗法中触发\n"
        "秘境：秘境 / 秘境帮助 / 创建单人秘境 普通 / 创建秘境队伍 普通 / 投骰 / 秘境地图 / 秘境救援 1000\n"
        "御兽秘境：御兽秘境开局 PVE / PVP，私聊任务堂招募随从，群聊播报战报\n"
        "交易：商店 / 万宝楼 / 交易 @对方 灵器 1 100 / 批量出售 杂物 20 / 批量出售低阶灵器\n"
        "后台：浏览器访问 /xiuxian-admin，可查看玩家档案、物品属性、灵器规则和秘境掉落配置"
    ),
    type="application",
    homepage="https://github.com/hszxjs/nonebot-plugin-xiuxian-signin",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "fallen_rainy",
        "version": __version__,
        "pmn": {
            "hidden": False,
            "markdown": True,
            "template": None,
        },
        "funcs": PICMENU_NEXT_FUNCS,
        "menu_data": PICMENU_NEXT_FUNCS,
    },
)

driver = get_driver()

# 共享可变状态（钓鱼待结算、斗法队列、牌桌等）统一定义在 state.py，
# 此处只沿用上方 `from .state import ...` 的引用。曾经在这里重新赋值为新的
# 空字典，导致入口模块与 commands/ 子模块各持一份、互不可见（F811）。
rank_scheduler_task: Optional[asyncio.Task] = None
mystic_recovery_task: Optional[asyncio.Task] = None
# 秘境背景图外置包的后台下载任务（R-09）：不阻塞启动，失败只降级为占位背景。
asset_download_task: Optional[asyncio.Task] = None
admin_http_server = None






















































































































async def settle_daily_chat_ranks() -> None:
    now = local_now()
    if not is_settle_time(now):
        return
    date_text = now.date().isoformat()
    groups = await store.get_unsettled_rank_groups(date_text)
    for group_id, group_data in groups.items():
        entries = rank_entries_from_group(group_data)
        if not entries:
            await store.mark_rank_group_settled(group_id, date_text)
            continue
        rewards: dict[str, RankReward] = {}
        for index, entry in enumerate(entries[:10], start=1):
            exp, fishing_chances = rank_reward_for(index)
            if exp <= 0 and fishing_chances <= 0:
                continue
            user_id = str(entry.get("user_id", ""))

            def updater(record, rank=index, reward_map=rewards):
                reward_map[record.user_id] = apply_rank_reward(record, rank)

            await store.apply_to_user(user_id, updater)
        cultivation_entries = await group_cultivation_rank_entries(group_id)
        power_entries = await group_power_rank_entries(group_id)
        message = format_rank_message(
            group_id,
            date_text,
            entries,
            rewards,
            cultivation_entries,
            power_entries,
        )
        try:
            bot = get_bot()
            await bot.send_group_msg(
                group_id=int(group_id),
                message=await render_in_thread(panel_segment, "每日话痨榜", message, icon="rank"),
            )
        except Exception as exc:
            logger.exception(f"发送群 {group_id} 每日话痨榜失败")
            # NapCat/QQ 内核 ACK 超时（retcode=1200）时，消息实际往往已送达。
            # 无论真假失败，都标记已结算，否则 get_unsettled_rank_groups 会反复
            # 取到该群导致无限重发（群里疯狂刷屏话痨榜）。
            if _is_likely_sent_despite_error(exc):
                logger.warning("话痨榜发送超时但可能已送达（retcode=1200），标记已结算避免重复发送")
        # 无论发送成功还是失败，都标记已结算（避免无限重发 > 单次失败的容错）
        try:
            await store.mark_rank_group_settled(group_id, date_text)
        except Exception:
            logger.exception("标记话痨榜已结算失败")

async def rank_scheduler() -> None:
    while True:
        try:
            await settle_daily_chat_ranks()
        except Exception:
            logger.exception("每日话痨榜结算任务失败")
        await asyncio.sleep(60)


async def recover_mystic_dungeons() -> None:
    try:
        recovered = await mystic_coordinator.recover_active_runs()
        logger.info(
            "秘境状态恢复完成："
            f"应战超时 {recovered.response_expirations}，"
            f"投票超时 {recovered.vote_expirations}，"
            f"恢复截止时间 {recovered.scheduled_deadline_count}"
        )
    except Exception:
        logger.exception("秘境状态恢复失败")


async def mystic_recovery_sweep() -> None:
    """周期性巡检进行中的秘境，兜底重建丢失的截止时间任务。

    秘境的截止时间建在内存 asyncio task 上，进程异常或任务抛出非冲突异常
    时可能丢失，导致秘境卡在某个阶段不推进。recover_active_runs 本身幂等
    （deadline 在未来就重建 task，已过期就立即推进），故可安全地周期调用。
    """
    while True:
        try:
            await mystic_coordinator.recover_active_runs()
        except Exception:
            logger.exception("秘境周期巡检失败")
        await asyncio.sleep(60)


@driver.on_startup
async def start_rank_scheduler() -> None:
    global admin_http_server, rank_scheduler_task, mystic_recovery_task, asset_download_task
    admin_ready = False
    if config.xiuxian_signin_admin_enabled:
        # fail-closed：账号初始化失败（数据目录不可写、凭据文件损坏）时
        # 直接不启动后台，而不是启动一个没人能登录、或没人需要登录的后台。
        try:
            admin_manager.auth.ensure_initialized()
            admin_ready = True
        except Exception:
            logger.exception(
                "后台账号初始化失败，本次不启动后台。"
                "请检查数据目录写权限，或删除 admin_auth.json 后重启重建。"
            )
    if admin_ready:
        mounted = False
        try:
            # 首选：把后台路由挂到 NoneBot driver 的 FastAPI server_app 上。
            # 这样后台与命令处理共用同一个事件循环，且不额外占用端口，
            # 从结构上消除"主循环 + 独立 uvicorn 线程"两个写者的局面。
            mounted = install_admin_routes(driver, admin_manager, config.xiuxian_signin_admin_path)
        except Exception:
            logger.exception("修仙签到后台挂载到 driver 失败，回退独立端口")
            mounted = False
        if mounted:
            logger.info(f"修仙签到后台已挂载到 driver：{config.xiuxian_signin_admin_path}")
        else:
            try:
                admin_http_server = start_admin_server(
                    admin_manager,
                    config.xiuxian_signin_admin_host,
                    config.xiuxian_signin_admin_port,
                    config.xiuxian_signin_admin_path,
                )
                logger.info(
                    "修仙签到后台已启动："
                    f"http://{admin_http_server.host}:{admin_http_server.port}{admin_http_server.base_path}"
                )
            except Exception:
                logger.exception(
                    f"修仙签到后台启动失败：{config.xiuxian_signin_admin_host}:{config.xiuxian_signin_admin_port}"
                )
                admin_manager.apply_config()
    else:
        admin_manager.apply_config()
    await recover_mystic_dungeons()
    rank_scheduler_task = asyncio.create_task(rank_scheduler())
    mystic_recovery_task = asyncio.create_task(mystic_recovery_sweep())
    global chat_flush_task
    chat_flush_task = asyncio.create_task(chat_flush_loop())

    # 秘境背景图（202 MB）不进 wheel，启动后再后台拉取：先让机器人可用，
    # 下载期间出图用程序化占位背景，完成即切换到真图（resolve_background 每次解析）。
    configure_resource_pack(get_data_dir())
    if config.xiuxian_signin_asset_auto_download:
        asset_download_task = asyncio.create_task(
            ensure_asset_pack(data_dir=get_data_dir(), url=config.xiuxian_signin_asset_url)
        )


async def ensure_asset_pack(*, data_dir, url: Optional[str]) -> None:
    """后台准备秘境资源包；任何失败都只告警，不影响机器人运行。"""
    status = resource_pack_status(data_dir)
    if status.complete:
        logger.info(f"秘境资源包已就绪：{status.summary()}")
        return
    logger.info(f"秘境资源包不完整：{status.summary()}")
    await ensure_pack(data_dir=data_dir, url=url)


async def chat_flush_loop() -> None:
    """R-17：每 30s 把内存中聚合的聊天计数批量落盘。"""
    while True:
        await asyncio.sleep(30)
        try:
            applied = await store.flush_chat_counts()
            if applied:
                logger.debug(f"聊天计数已批量落盘 {applied} 条")
        except Exception:
            logger.exception("聊天计数批量落盘失败")


@driver.on_shutdown
async def stop_admin_http_server() -> None:
    global admin_http_server, mystic_recovery_task, rank_scheduler_task, asset_download_task, chat_flush_task
    # 停机前先冲掉未落盘的聊天计数，再取消任务。
    try:
        await store.flush_chat_counts()
    except Exception:
        logger.exception("停机时冲刷聊天计数失败")
    if admin_http_server is not None:
        admin_http_server.stop()
        admin_http_server = None
    await close_shared_http_client()
    # SQLite 后端：关闭连接，清理 WAL/-shm 文件。
    if hasattr(store, "close"):
        store.close()
    # 后台任务都必须取消并 await，否则停机后仍有协程在写存档 / 下载资源。
    pending = [
        task
        for task in (mystic_recovery_task, rank_scheduler_task, asset_download_task, chat_flush_task)
        if task is not None
    ]
    for task in pending:
        task.cancel()
    for task in pending:
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("后台任务在停机时抛出异常")
    mystic_recovery_task = None
    rank_scheduler_task = None
    asset_download_task = None
    chat_flush_task = None



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




def _collect_theme_display_names(risk: DungeonRisk) -> tuple[str, ...]:
    """收集某风险等级下已启用主题的展示名(按 theme_id 排序),用于缺令牌提示图。"""
    enabled_ids = active_mystic_theme_ids(risk)
    themes = sorted(
        (t for t in mystic_catalog.themes.values() if t.risk is risk),
        key=lambda t: t.theme_id,
    )
    if enabled_ids:
        enabled_set = set(enabled_ids)
        themes = [t for t in themes if t.theme_id in enabled_set]
    return tuple(t.display_name for t in themes)


async def finish_mystic_command_result(
    matcher: Matcher,
    user_id: str,
    result: MysticCommandResult,
) -> None:
    record = await store.get_user(user_id)
    if result.token_missing_risk is not None:
        # 缺少秘境令牌:渲染专属提示图(含令牌图标、持有数、获取途径、可进入秘境)
        normal_count = reward_count_by_names(record, ["普通秘境令牌"])
        high_count = reward_count_by_names(record, ["高风险秘境令牌"])
        try:
            image_bytes = render_no_token_panel(
                normal_count=normal_count,
                high_count=high_count,
                normal_theme_names=_collect_theme_display_names(DungeonRisk.NORMAL),
                high_theme_names=_collect_theme_display_names(DungeonRisk.HIGH),
                width=config.xiuxian_signin_image_width,
            )
            await matcher.send(MessageSegment.image(BytesIO(image_bytes)))
            await matcher.finish()
            return
        except (ActionFailed, NetworkError, OSError, RuntimeError, ValueError):
            # 图片发送失败时回退到通用 warning 面板
            await finish_panel(matcher, "秘境操作失败", result.error or "令牌不足", record, icon="warning")
            return
    if result.error:
        await finish_panel(matcher, "秘境操作失败", result.error, record, icon="warning")
        return
    # 准备阶段倒计时 + 神识探查敌方情报：从当前秘境遭遇读取，一并带进战备面板，
    # 让玩家知道还剩多少秒调整装备、以及要面对什么样的敌人。仅计算一次。
    prepare_hint = ""
    monster_info = ""
    if any(text == "秘境配装" for _, text in result.private_messages):
        prepare_hint, monster_info = await _mystic_prepare_info(result.run)
    for target_user_id, private_text in result.private_messages:
        try:
            if private_text == "秘境配装":
                # 战斗准备阶段：原先只发“秘境配装”四个字，没有任何战斗信息。
                # 这里加载目标玩家存档，发送与斗法一致的战备面板（修为/战技/阵盘/符箓），
                # 让玩家在确认配装前能看到自己的配置。
                target_record = await store.get_user(target_user_id)
                await send_mystic_prepare_cards(
                    target_user_id,
                    target_record,
                    "",
                    prepare_hint,
                    monster_info,
                )
            else:
                await get_bot().send_private_msg(
                    user_id=int(target_user_id),
                    message=private_text,
                )
        except (ActionFailed, NetworkError, RuntimeError, ValueError):
            logger.debug(f"发送秘境私聊提示失败: {target_user_id}")
    if result.image_bytes is not None:
        try:
            await matcher.send(MessageSegment.image(BytesIO(result.image_bytes)))
        except (ActionFailed, NetworkError, OSError, RuntimeError, ValueError):
            await finish_panel(
                matcher,
                "秘境地图",
                result.message or "地图图片发送失败，请稍后重试。",
                record,
                icon="mystic",
            )
            return
        await matcher.finish()
        return
    await finish_panel(
        matcher,
        "秘境",
        result.message or "秘境状态已更新。",
        record,
        icon=result.panel_icon or "mystic",
    )


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


@beast_realm_group_cmd.handle()
async def handle_beast_realm_group(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    text_value = normalized_plain_text(event)
    group_key = beast_realm_group_key_from_event(event)

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


@breakthrough_cmd.handle()
async def handle_breakthrough(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    if text in {"\u6563\u529f", "\u91cd\u4fee", "\u81ea\u5e9f\u4fee\u4e3a"}:
        success, message = regress_cultivation(record)
        if success:
            await store.save_user(record)
        await finish_panel(
            matcher,
            "\u6563\u529f\u91cd\u4fee" if success else "\u6563\u529f\u5931\u8d25",
            message,
            record,
            icon="breakthrough" if success else "warning",
        )
    if text in {"\u7a81\u7834", "\u5883\u754c\u7a81\u7834", "\u7834\u5883"}:
        success, message = breakthrough_realm(record)
        if success:
            await store.save_user(record)
        await finish_panel(
            matcher,
            "\u5883\u754c\u7a81\u7834" if success else "\u7a81\u7834\u72b6\u6001",
            message,
            record,
            icon="breakthrough" if success else "warning",
        )
    await finish_panel(matcher, "\u7a81\u7834\u72b6\u6001", breakthrough_status(record), record, icon="breakthrough", footer=command_hint("修为与突破"))


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


@route_cmd.handle()
async def handle_route(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    if text in ROUTE_TEXTS:
        await finish_panel(matcher, "修炼路线", route_status_text(record), record, icon="token", footer=command_hint("路线与身份"))
    route_name = parse_prefixed_name(text, ROUTE_SELECT_PREFIXES)
    if route_name is not None:
        if not route_name:
            await finish_panel(matcher, "修炼路线", route_status_text(record), record, icon="token", footer=command_hint("路线与身份"))
        success, message = choose_cultivation_route(record, route_name)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "修炼路线" if success else "选择失败", message, record, icon="token" if success else "warning")
    identity_name = parse_prefixed_name(text, IDENTITY_SELECT_PREFIXES)
    if identity_name is not None:
        if not identity_name:
            await finish_panel(matcher, "身份令牌", route_status_text(record), record, icon="token", footer=command_hint("路线与身份"))
        success, message = choose_faction_identity(record, identity_name)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "身份令牌" if success else "选择失败", message, record, icon="token" if success else "warning")
    if text in EVIL_SELECT_TEXTS or text in EVIL_QUIT_TEXTS:
        success, message = choose_evil_cultivation(record, text in EVIL_SELECT_TEXTS)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "邪修路线", message, record, icon="token")
    await finish_panel(matcher, "修炼路线", route_status_text(record), record, icon="token", footer=command_hint("路线与身份"))


@task_cmd.handle()
async def handle_daily_task(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    today = local_today()
    if text in TASK_TEXTS:
        content = daily_tasks_text(record, today)
        await store.save_user(record)
        await finish_private_or_current_panel(
            matcher,
            event,
            "每日任务",
            content,
            record,
            icon="task",
            group_success="今日任务已接取，任务详情已通过私聊发送。",
        )
    task_index = parse_prefixed_index(text, TASK_COMPLETE_PREFIXES)
    if task_index is None:
        content = daily_tasks_text(record, today)
        await store.save_user(record)
        await finish_private_or_current_panel(
            matcher,
            event,
            "每日任务",
            content,
            record,
            icon="task",
            group_success="今日任务已接取，任务详情已通过私聊发送。",
        )
    success, message = complete_daily_task(record, task_index, today)
    content = message
    if success:
        content = f"{message}\n\n{daily_tasks_text(record, today)}"
    await store.save_user(record)
    await finish_private_or_current_panel(
        matcher,
        event,
        "每日任务完成" if success else "任务失败",
        content,
        record,
        icon="task" if success else "warning",
        group_success="任务结算结果已通过私聊发送。" if success else "任务处理结果已通过私聊发送。",
    )


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




async def enforce_unique_rewards(record, event: MessageEvent) -> str:
    notes = []
    changed = False
    rewards = []
    for reward in record.rewards or []:
        if is_unique_reward(reward):
            claimed, owner = await store.claim_unique_artifact(reward.get("name", ""), record.user_id, nickname_from_event(event) or record.user_id)
            if not claimed or str(owner.get("user_id")) != record.user_id:
                rewards.append(make_unique_replica(reward))
                notes.append(f"{reward.get('name')}\u672c\u4f53\u5df2\u7531 {owner.get('nickname') or owner.get('user_id')} \u6301\u6709\uff0c\u672c\u6b21\u8f6c\u5316\u4e3a\u4eff\u5236\u54c1\u3002")
                changed = True
                continue
        rewards.append(reward)
    if changed:
        record.rewards = rewards
    return "\n".join(notes)

async def normalize_unique_reward_for_user(record, reward: dict[str, Any], event: MessageEvent) -> tuple[dict[str, Any], str]:
    if not is_unique_reward(reward):
        return reward, ""
    claimed, owner = await store.claim_unique_artifact(reward.get("name", ""), record.user_id, nickname_from_event(event) or record.user_id)
    if claimed and str(owner.get("user_id")) == record.user_id:
        return reward, f"\n\u552f\u4e00\u9053\u5177\u5df2\u8bb0\u5f55\u62e5\u6709\u8005\uff1a{owner.get('nickname') or record.user_id}\u3002"
    replica = make_unique_replica(reward)
    return replica, f"\n{reward.get('name')}\u672c\u4f53\u5df2\u7531 {owner.get('nickname') or owner.get('user_id')} \u6301\u6709\uff0c\u672c\u6b21\u8f6c\u5316\u4e3a\u4eff\u5236\u54c1\u3002"


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


@dual_cultivation_cmd.handle()
async def handle_dual_cultivation(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    text = normalized_plain_text(event)
    target_id = None
    targets = at_user_ids(event)
    if targets:
        target_id = targets[0]
    elif text == "随机双修":
        members = await store.get_group_user_records(str(event.group_id))
        candidates = [entry for entry in members if str(entry.get("user_id")) != event.get_user_id()]
        if candidates:
            target_id = str(random.choice(candidates).get("user_id"))
    if not target_id:
        await finish_panel(matcher, "双修", "请发送“双修 @群成员”或“随机双修”。", icon="token")
    if target_id == event.get_user_id():
        await finish_panel(matcher, "双修失败", "不可与自己双修。", icon="warning")
    actor = await store.get_user(event.get_user_id())
    target = await store.get_user(target_id)
    success, message = apply_dual_cultivation(actor, target, local_today())
    if success:
        await store.save_user(actor)
        await store.save_user(target)
    actor_name = nickname_from_event(event) or await group_member_display_name(event, event.get_user_id())
    target_name = await group_member_display_name(event, target_id)
    await finish_panel(
        matcher,
        "合欢宗双修" if success else "双修失败",
        f"{actor_name} 与 {target_name}\n{message}",
        actor,
        icon="token" if success else "warning",
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

@signin.handle()
async def handle_signin(matcher: Matcher, event: MessageEvent) -> None:
    user_id = event.get_user_id()
    await remember_group_member(event)
    record = await store.get_user(user_id)
    result = apply_signin(record, local_today())
    await store.save_user(result.record)

    if result.is_first and not result.already_signed:
        root = result.record.root
        await send_panel(matcher, "天赋抽取", "检测到宿主首次签到，正在进行天赋抽取。", result.record, icon="realm")
        if root:
            await send_panel(
                matcher,
                "灵根觉醒",
                f"叮！抽到{root.display_name}，{result.record.realm}进度{result.record.realm_exp}/{result.record.progress_required}",
                result.record,
                icon="realm",
            )
        if isinstance(event, GroupMessageEvent):
            await send_panel(
                matcher,
                "私聊提醒",
                "首次入门完成。若要接收每日任务、秘境战报等私聊提醒，并打开新手教程，请先主动私聊 Bot 发送任意消息或“新手教程”。",
                result.record,
                icon="warning",
            )

    if result.pending_exp_applied:
        await send_panel(matcher, "日榜奖励", f"日榜暂存修为已汇入丹田，修炼进度+{result.pending_exp_applied}", result.record, icon="rank")

    if result.breakthrough_reward:
        await send_panel(matcher, "瓶颈机缘", f"额外获得 {reward_display_name(result.breakthrough_reward)}。", result.record, icon="breakthrough")

    if result.encounter and result.encounter.happened:
        await send_panel(matcher, "今日奇遇", result.encounter.message, result.record, icon="mystic")

    image = await build_signin_image(event, result)
    await send_image(matcher, image)

    if not result.already_signed:
        # 签到成功后附上当月签到日历（仅当天首次签到发，重复签到不重发）
        try:
            today = local_today()
            calendar_image = await build_signin_calendar_image(
                user_id,
                result.record,
                nickname_from_event(event),
                today.year,
                today.month,
            )
            await send_image(matcher, calendar_image)
        except (ActionFailed, NetworkError, OSError, RuntimeError, ValueError):
            logger.debug(f"签到日历发送失败: {user_id}")

    if result.is_first and not result.already_signed and isinstance(event, PrivateMessageEvent):
        await send_panel(
            matcher,
            "新手教程",
            format_newbie_tutorial_text(result.record, nickname_from_event(event)),
            result.record,
            icon="scroll",
            footer="以后在私聊发送“新手教程”，可随时重新打开这份引导。",
        )

    if not result.already_signed and result.daily_tasks:
        task_content = daily_tasks_text(result.record, local_today())
        if isinstance(event, GroupMessageEvent):
            sent = await send_private_panel(user_id, "每日任务", task_content, result.record, icon="task")
            await send_panel(
                matcher,
                "每日任务",
                "今日任务已接取，任务详情已通过私聊发送。" if sent else "今日任务已接取，但私聊发送失败，请检查好友或临时会话权限。",
                result.record,
                icon="task" if sent else "warning",
            )
        else:
            await send_panel(matcher, "每日任务", task_content, result.record, icon="task")

    if not result.already_signed and result.record.fishing_chances > 0:
        pending_fishing_users[user_id] = time.monotonic() + PENDING_FISHING_TTL
        await send_panel(
            matcher,
            "灵河垂钓",
            f"检测到宿主有 {result.record.fishing_chances} 次灵河垂钓次数，是否垂钓？可累加进行 10 连抽。回复 是/好/y/十连。",
            result.record,
            icon="fishing",
        )


@signin_calendar.handle()
async def handle_signin_calendar(matcher: Matcher, event: MessageEvent) -> None:
    user_id = event.get_user_id()
    await remember_group_member(event)
    record = await store.get_user(user_id)
    target = parse_calendar_target(normalized_plain_text(event))
    if target is None:
        await finish_panel(
            matcher,
            "签到日历",
            "月份格式不对，可用「签到日历」「签到日历 上月」「签到日历 2026-09」。",
            record,
            icon="warning",
        )
    year, month = target
    image = await build_signin_calendar_image(
        user_id,
        record,
        nickname_from_event(event),
        year,
        month,
    )
    await send_image(matcher, image)


@makeup_sign_cmd.handle()
async def handle_makeup_sign(matcher: Matcher, event: MessageEvent) -> None:
    user_id = event.get_user_id()
    await remember_group_member(event)
    record = await store.get_user(user_id)
    if record.root is None:
        await finish_panel(matcher, "尚未入门", "尚未踏入修行路，发送“签到”即可抽取灵根。", record, icon="realm")
    target = parse_makeup_target(normalized_plain_text(event))
    if target is None:
        await finish_panel(
            matcher,
            "补签",
            "用法：补签 15（补本月 15 日）或 补签 10月15。",
            record,
            icon="warning",
        )
    today = local_today()
    success, message = makeup_sign(record, target, today)
    if success:
        await store.save_user(record)
    # 无论成败都回一张当月日历，让玩家直接看到结果（成功日会盖青色补签印）
    await send_panel(matcher, "补签" if success else "补签失败", message, record, icon="realm" if success else "warning")
    image = await build_signin_calendar_image(
        user_id,
        record,
        nickname_from_event(event),
        today.year,
        today.month,
    )
    await send_image(matcher, image)


@status.handle()
async def handle_status(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    if record.root is None:
        await finish_panel(matcher, "尚未入门", "尚未踏入修行路，发送“签到”即可抽取灵根。", record, icon="realm")
    result = SigninResult(record=record, is_first=False, already_signed=True)
    image = await build_signin_image(event, result)
    await send_image(matcher, image)


@fishing.handle()
async def handle_fishing_command(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    if record.fishing_chances <= 0:
        await finish_panel(matcher, "灵河垂钓", "宿主暂无灵河垂钓次数，每次签到可获得 1 次。", record, icon="fishing")
    text = normalized_plain_text(event)
    arg = parse_fishing_arg(text) or ""
    count = fishing_count_from_text(arg, record.fishing_chances)
    await do_fishing(matcher, event, count)


@fishing_reply.handle()
async def handle_fishing_reply(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    user_id = event.get_user_id()
    text = normalized_plain_text(event).lower()
    record = await store.get_user(user_id)
    if text in CANCEL_WORDS:
        pending_fishing_users.pop(user_id, None)
        await finish_panel(matcher, "灵河垂钓", "已收起钓竿，灵河垂钓次数仍为你保留。", record, icon="fishing")
    count = fishing_count_from_text(text, record.fishing_chances)
    await do_fishing(matcher, event, count)


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


@power_status.handle()
async def handle_power_status(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "个人战力", format_power_status(record, nickname_from_event(event)), record, icon="power", footer=command_hint("灵器与战力"))


@adventure.handle()
async def handle_adventure(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    image = await render_in_thread(
        render_adventure_card,
        record=record,
        nickname=nickname_from_event(event),
        width=config.xiuxian_signin_image_width,
    )
    await send_image(matcher, image)


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


@normal_duel_apply.handle()
async def handle_normal_duel_apply(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    group_id = str(event.group_id)
    user_id = event.get_user_id()
    if group_duel_session(group_id):
        await finish_panel(matcher, "\u666e\u901a\u6597\u6cd5", "\u672c\u7fa4\u5df2\u6709\u4e00\u573a\u666e\u901a\u6597\u6cd5\u8fdb\u884c\u4e2d\uff0c\u8bf7\u7a0d\u540e\u518d\u7533\u8bf7\u3002", icon="duel")
    name = nickname_from_event(event) or await group_member_display_name(event, user_id)
    queued = normal_duel_queue.get(group_id)
    if queued and float(queued.get("expires_at", 0)) < time.monotonic():
        normal_duel_queue.pop(group_id, None)
        queued = None
    if queued and str(queued.get("user_id")) == user_id:
        await finish_panel(matcher, "\u666e\u901a\u6597\u6cd5", "\u5df2\u5728\u5339\u914d\u961f\u5217\u4e2d\uff0c\u7b49\u5f85\u53e6\u4e00\u4f4d\u4fee\u58eb\u7533\u8bf7\u3002", icon="duel")
    if not queued:
        normal_duel_queue[group_id] = {
            "user_id": user_id,
            "name": name,
            "expires_at": time.monotonic() + 180,
        }
        record = await store.get_user(user_id)
        ensure_combat_profile(record)
        await store.save_user(record)
        await finish_panel(
            matcher,
            "\u666e\u901a\u6597\u6cd5",
            "\u5df2\u8fdb\u5165\u666e\u901a\u6597\u6cd5\u5339\u914d\u961f\u5217\u3002\n\u7fa4\u5185\u53e6\u4e00\u4f4d\u4fee\u58eb\u53d1\u9001\u201c\u7533\u8bf7\u666e\u901a\u6597\u6cd5\u201d\u540e\u5c06\u81ea\u52a8\u5f00\u6218\u3002",
            record,
            icon="duel",
        )
    left_id = str(queued.get("user_id"))
    left_name = str(queued.get("name") or left_id)
    right_id = user_id
    right_name = name
    normal_duel_queue.pop(group_id, None)
    start_at = time.monotonic() + NORMAL_DUEL_PREPARE_SECONDS
    session = {
        "left_id": left_id,
        "right_id": right_id,
        "left_name": left_name,
        "right_name": right_name,
        "created_at": time.monotonic(),
        "start_at": start_at,
        "end_at": start_at + NORMAL_DUEL_DURATION_SECONDS,
        "active": False,
        "actions": {left_id: [], right_id: []},
    }
    normal_duel_sessions[group_id] = session
    asyncio.create_task(send_normal_duel_prepare_messages(session))
    asyncio.create_task(finish_normal_duel(group_id, session))
    await finish_panel(
        matcher,
        "\u666e\u901a\u6597\u6cd5",
        f"\u5339\u914d\u6210\u529f\uff1a{left_name} \u5bf9\u9635 {right_name}\n\u5df2\u8fdb\u51651\u5206\u949f\u51c6\u5907\u671f\uff0c\u7cfb\u7edf\u5c06\u79c1\u804a\u53cc\u65b9\u53d1\u9001\u4fee\u4e3a\u3001\u6218\u6280\u3001\u9635\u76d8\u548c\u7b26\u7b93\u51c6\u5907\u5361\u3002\n\u5f00\u6218\u540e 60 \u79d2\u5185\u53d1\u9001\u6218\u6280\u3001\u795e\u901a\u3001\u8868\u60c5\u6216\u5373\u5174\u53f0\u8bcd\u3002",
        icon="duel",
    )


@normal_duel_chat.handle()
async def handle_normal_duel_chat(event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    text = normal_duel_action_text(event)
    append_normal_duel_action(event, text)


@array_list.handle()
async def handle_array_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "我的阵盘", format_array_list(record), record, icon="array", footer=command_hint("功法与阵盘"))


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


@duel.handle()
async def handle_duel(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    target_id = parse_duel_target(event)
    if not target_id:
        await finish_panel(matcher, "操作提示", "请发送“pk @对方”或“pk QQ号”。", icon="duel")
    if target_id == event.get_user_id():
        await finish_panel(matcher, "操作失败", "不能和自己切磋。", icon="warning")
    attacker = await store.get_user(event.get_user_id())
    defender = await store.get_user(target_id)
    result = duel_records(attacker, defender)
    attacker_name = nickname_from_event(event) or await group_member_display_name(event, event.get_user_id())
    defender_name = await group_member_display_name(event, target_id)
    await finish_panel(matcher, "历练切磋", format_duel_result(attacker_name, defender_name, result), attacker, icon="duel")


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


async def do_fishing(matcher: Matcher, event: MessageEvent, count: int) -> None:
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    if record.fishing_chances <= 0:
        pending_fishing_users.pop(user_id, None)
        await finish_panel(matcher, "灵河垂钓", "宿主暂无灵河垂钓次数。", record, icon="fishing")
    count = max(1, min(count, record.fishing_chances, 10))
    await send_panel(matcher, "灵河垂钓", f"正在为宿主进行{count}次垂钓。", record, icon="fishing")
    rewards = apply_fishing(record, count)
    await enforce_unique_rewards(record, event)
    pending_fishing_users.pop(user_id, None)
    await store.save_user(record)
    image = await build_fishing_image(event, record, rewards)
    await send_image(matcher, image)
