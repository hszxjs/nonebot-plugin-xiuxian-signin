from __future__ import annotations

import asyncio
from collections import Counter
import random
import re
import time
from datetime import date, datetime
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
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from . import beast_realm as beast_realm_game
from .cards import render_adventure_card, render_battle_card, render_fishing_card, render_signin_card, render_text_panel, set_font_paths
from .character_assets import beast_portrait_bytes
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
    draw_mystic_entrances,

    draw_talisman_by_index,
    draw_tianji_mystic_entrances,
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
    explore_mystic_realm,
    fishing_count_from_text,
    identify_misc_item,
    learn_special_ability,
    market_offer_price,
    method_power,
    technique_cooldown,
    technique_mana_cost,
    mystic_realm_options_text,
    mystic_realm_title_from_entry,
    plant_spirit_plant,
    pop_reward_by_category_index,
    puppet_power,
    rank_reward_for,

    array_deduction_text,
    batch_sell_rewards,
    deduce_array,
    divine_ability_catalog_text,
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
    talisman_draw_text,
    tianji_divination_text,
    start_mystic_realm,
    unequip_artifact,
    unequip_talisman,
    use_curio,
    use_food,
    use_foods_batch,
    use_pill,
    use_pills_batch,
    use_talisman,
)
from .admin import AdminManager, start_admin_server
from .storage import JsonStore

__version__ = "0.5.1"

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
    {
        'func': '秘境与任务',
        'trigger_method': '秘境 / 探索 1 / 天机秘境 / 每日任务 / 秘境救援 1000',
        'trigger_condition': '秘境入口 60 秒内选择；任务每日签到后生成',
        'brief_des': '探索秘境、挑战首领、完成任务并处理反噬救援',
        'detail_des': '`秘境` 抽取限时入口；进入后发送 `探索 编号`；首领挑战胜利可折算多次探索奖励并获得妖丹；失败后可发布 `秘境救援 金额`。',
    },
    {
        'func': '御兽秘境',
        'trigger_method': '御兽秘境开局 PVE / 御兽秘境开局 PVP / 加入御兽秘境 / 御兽秘境图鉴',
        'trigger_condition': '群聊开局，私聊在任务堂招募随从；PVP/PVE均需4人，单人1V2在私聊开启',
        'brief_des': '类酒馆战棋的4人排位斗兽、4V4秘境演武与单人1V2试炼',
        'detail_des': '`御兽秘境开局 PVE` 开启4名修士对4名bot代理的秘境演武；`御兽秘境开局 PVP` 开启4人排位战，每回合随机两场1V1。私聊 `御兽秘境1V2` 可开启单人PVE。开始后系统私聊任务堂，使用 `购买 1`、`施法 1 2`、`升堂`、`完成招募` 完成每回合操作。',
    },
    {
        'func': '路线与身份',
        'trigger_method': '修炼路线 / 选择路线 剑修 / 选择身份 天机阁弟子 / 双修 @群友',
        'trigger_condition': '主路线同一时间只能选择一种；身份有境界和签到天数门槛',
        'brief_des': '选择剑修、术修、炼丹师、炼器师、阵法师和身份令牌',
        'detail_des': '`修炼路线` 查看效果；`选择路线 名称` 切换主路线；天机阁提供秘境示警和占卜坐堂，合欢宗提供双修次数。',
    },
    {
        'func': '交易与商店',
        'trigger_method': '商店 / 购买 1 / 出售 丹药 1 / 批量出售 杂物 20 / 万宝楼 / 交易 @对方 灵器 1 100',
        'trigger_condition': '交易、万宝楼和排行榜主要在群聊使用',
        'brief_des': '购买、出售、公开寄售和玩家间交易',
        'detail_des': '`商店` 每日刷新；`万宝楼挂售 类别 编号` 公开寄售；`交易 @对方 类别 编号 价格` 指定交易；唯一装备不会被批量出售。',
    },
    {
        'func': '休闲与排行',
        'trigger_method': '天机占卜 / 坐堂 / 斗地主 / 斗地主帮助 / 排行 / 战力榜',
        'trigger_condition': '休闲玩法不影响主线修炼；斗地主需群聊',
        'brief_des': '问卦、斗地主、修为榜、战力榜和每日话痨榜',
        'detail_des': '`天机占卜` 需要本群有天机阁门人坐堂；`斗地主帮助` 查看牌局规则；`排行`、`战力榜` 查看群内排名。',
    },
    {
        'func': '后台管理',
        'trigger_method': '浏览器访问 /xiuxian-admin',
        'trigger_condition': '服主需要在 NoneBot 后端启用管理页，可配置管理 Token',
        'brief_des': '查看和修改玩家档案、物品属性、灵器规则、秘境掉落配置',
        'detail_des': '后台可备份 users.json，编辑玩家记录，查看全部物品用途、故事、获取途径，并调整灵器境界限制与秘境掉落权重。',
    },
]


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
        "秘境：秘境 / 探索 1 / 天机秘境 / 秘境救援 1000，探索、挑战首领和处理反噬\n"
        "御兽秘境：御兽秘境开局 PVE / PVP，私聊任务堂招募随从，群聊播报战报\n"
        "交易：商店 / 万宝楼 / 交易 @对方 灵器 1 100 / 批量出售 杂物 20\n"
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

SIGNIN_TEXTS = {"签到", "修仙签到", "每日签到"}
STATUS_TEXTS = {"\u6211\u7684\u4fee\u4e3a", "\u4fee\u4e3a", "\u5883\u754c", "\u7075\u6839", "\u9762\u677f", "\u4e2a\u4eba\u9762\u677f"}
HELP_TEXTS = {"\u5e2e\u52a9", "\u4fee\u4ed9\u5e2e\u52a9", "\u6307\u4ee4", "\u8bf4\u660e", "\u73a9\u6cd5", "\u83dc\u5355"}
CATALOG_TEXTS = {
    "\u56fe\u9274",
    "\u56fe\u5f55",
    "\u5883\u754c\u56fe\u9274",
    "\u7a81\u7834\u56fe\u9274",
    "\u54c1\u76f8\u56fe\u9274",
    "\u7a81\u7834\u54c1\u76f8\u56fe\u9274",
    "\u9053\u5177\u54c1\u76f8\u56fe\u9274",
    "\u4e39\u836f\u56fe\u9274",
    "\u7b26\u7b93\u56fe\u9274",
    "\u7075\u5668\u56fe\u9274",
    "\u529f\u6cd5\u56fe\u9274",
    "\u9635\u76d8\u56fe\u9274",
    "\u6750\u6599\u56fe\u9274",
    "\u795e\u901a\u56fe\u9274",
    "\u7075\u6750\u56fe\u9274",
}
CATALOG_QUERY_PREFIXES = ("图鉴", "图录", "查看图鉴")
BREAKTHROUGH_TEXTS = {"\u7a81\u7834", "\u5883\u754c\u7a81\u7834", "\u7834\u5883", "\u67e5\u770b\u7a81\u7834", "\u7a81\u7834\u72b6\u6001", "\u6563\u529f", "\u91cd\u4fee", "\u81ea\u5e9f\u4fee\u4e3a"}
CULTIVATION_RANK_TEXTS = {"\u4fee\u4e3a\u699c", "\u7fa4\u4fee\u4e3a\u699c", "\u5883\u754c\u699c", "\u6392\u884c", "\u6392\u884c\u699c"}
POWER_RANK_TEXTS = {"战力榜", "群战力榜"}
POWER_TEXTS = {"战力", "我的战力"}
ADVENTURE_TEXTS = {"历练", "历练面板", "历练帮助"}
NEWBIE_TUTORIAL_TEXTS = {"新手教程"}
ARTIFACT_LIST_TEXTS = {"\u7075\u5668", "\u6211\u7684\u7075\u5668", "\u7075\u5668\u5217\u8868", "\u88c5\u5907\u5217\u8868"}
METHOD_LIST_TEXTS = {"功法", "我的功法", "功法列表"}
ARRAY_LIST_TEXTS = {"阵盘", "我的阵盘", "阵盘列表", "阵法", "我的阵法"}
PUPPET_LIST_TEXTS = {"傀儡", "我的傀儡", "傀儡列表"}
PLANT_LIST_TEXTS = {"灵植", "我的灵植", "灵植列表"}
ITEM_LIST_TEXTS = {"\u9053\u5177", "\u6211\u7684\u9053\u5177", "\u80cc\u5305", "\u7269\u54c1", "\u6211\u7684\u7269\u54c1", "\u5305\u88f9"}
ACQUIRED_ROOT_TEXTS = {"\u540e\u5929\u7075\u6839", "\u4e39\u7075\u6839", "\u5668\u7075\u6839", "\u70bc\u5316\u7075\u6839", "\u4e94\u884c\u8865\u5168"}
SPECIAL_ABILITY_TEXTS = {"神通", "我的神通"}
SPECIAL_ABILITY_CATALOG_TEXTS = {"神通图鉴"}
ROUTE_TEXTS = {"\u4fee\u70bc\u8def\u7ebf", "\u8def\u7ebf", "\u8eab\u4efd", "\u8eab\u4efd\u4ee4\u724c", "\u5b97\u95e8\u8eab\u4efd"}
TASK_TEXTS = {"每日任务", "任务", "我的任务", "今日任务", "接取任务", "领取任务"}
SHOP_TEXTS = {"商店", "坊市", "每日商店"}
ALCHEMY_TEXTS = {"炼丹", "丹方"}
REFINING_TEXTS = {'炼器', '炼器图鉴', '炼器帮助'}
ARRAY_DEDUCTION_TEXTS = {'阵法推演', '推演阵法'}
IMMORTAL_SEED_TEXTS = {'仙源', '我的仙源', '仙源图鉴', '仙种', '我的仙种', '仙种图鉴'}
EMPEROR_CATALOG_TEXTS = {'唯一装备图鉴'}
TALISMAN_DRAW_TEXTS = {"\u7ed8\u5236\u7b26\u7b93", "\u753b\u7b26", "\u5236\u7b26", "\u7b26\u7b93\u7ed8\u5236", "\u7ed8\u7b26"}
TIANJI_MYSTIC_TEXTS = {"天机秘境", "天机探索", "天机示警"}
DIVINATION_TEXTS = {"\u5929\u673a\u5360\u535c", "\u5360\u535c", "\u7b97\u547d", "\u95ee\u5366", "\u8d77\u5366", "\u535c\u5366"}
TIANJI_SIT_TEXTS = {"\u5750\u5802", "\u5929\u673a\u5750\u5802", "\u7533\u8bf7\u5750\u5802"}
DOUDIZHU_HELP_TEXTS = {"斗地主帮助", "斗地主规则", "斗牌帮助"}
DOUDIZHU_TEXTS = {
    "斗地主",
    "斗地主开桌",
    "加入斗地主",
    "退出斗地主",
    "开始斗地主",
    "人机斗地主",
    "手牌",
    "提示",
    "托管",
    "结束斗地主",
    "叫地主",
    "不叫",
    "抢地主",
    "不抢",
    "施加威压",
    "保留地主",
    "放弃地主",
    "加倍",
    "不加倍",
    "不要",
} | DOUDIZHU_HELP_TEXTS
DOUDIZHU_PLAY_PREFIXES = ("出牌", "打牌")
DOUDIZHU_BID_PREFIXES = ("叫分",)
MYSTIC_ENTRY_TEXTS = {"秘境", "查看秘境", "秘境入口", "探查秘境"}
UNEQUIP_TEXTS = {"卸下灵器", "卸下装备"}
EQUIP_PREFIXES = ("装备灵器", "装备")
ARTIFACT_SLOT_NAMES = ("主手", "副手", "护甲", "护盾")
TALISMAN_EQUIP_PREFIXES = ("装备符箓", "佩戴符箓", "符箓栏")
TALISMAN_UNEQUIP_TEXTS = {"卸下符箓", "卸下符箓栏"}
METHOD_EQUIP_PREFIXES = ("参悟功法", "修炼功法", "装备功法")
METHOD_DETAIL_PREFIXES = ("学习功法", "查看功法", "功法详情", "功法页面")
ARRAY_EQUIP_PREFIXES = ("布置阵盘", "装备阵盘", "布阵", "布置阵法")
PUPPET_EQUIP_PREFIXES = ("装备傀儡", "唤醒傀儡", "启用傀儡")
PLANT_EQUIP_PREFIXES = ("栽种灵植", "种植灵植", "种灵植")
PILL_USE_PREFIXES = ("使用丹药", "服用丹药", "服丹", "吃丹药")
PILL_BATCH_USE_PREFIXES = ("批量使用丹药", "批量服用丹药", "批量服丹", "一键服丹", "一键使用丹药")
TALISMAN_USE_PREFIXES = ("使用符箓", "激发符箓", "用符")
STONE_USE_PREFIXES = ("炼化灵石", "使用灵石", "吸收灵石")
STONE_BATCH_USE_PREFIXES = ("批量炼化灵石", "批量使用灵石", "批量吸收灵石", "一键炼化灵石", "一键使用灵石")
DEMON_CORE_USE_PREFIXES = ("炼化妖丹", "吸收妖丹", "使用妖丹")
DEMON_CORE_BATCH_USE_PREFIXES = ("批量炼化妖丹", "批量吸收妖丹", "一键炼化妖丹", "一键吸收妖丹")
SPIRIT_LIQUID_USE_PREFIXES = ("炼化灵液", "炼化精纯灵液", "吸收灵液", "吸收精纯灵液", "使用灵液", "使用精纯灵液")
FOOD_USE_PREFIXES = ("使用灵食", "食用灵食", "吃灵食")
FOOD_BATCH_USE_PREFIXES = ("批量使用灵食", "批量食用灵食", "批量吃灵食", "一键吃灵食", "一键使用灵食")
BATCH_USE_ALL_WORDS = {"全部", "全", "all", "ALL", "All"}
CURIO_USE_PREFIXES = ("使用奇物", "催动奇物", "参悟奇物")
MISC_USE_PREFIXES = ("鉴定杂物", "鉴定")
DAN_ROOT_PREFIXES = ("\u70bc\u5316\u4e39\u7075\u6839", "\u51dd\u7ec3\u4e39\u7075\u6839", "\u8865\u5168\u4e39\u7075\u6839")
ARTIFACT_ROOT_PREFIXES = ("\u70bc\u5316\u5668\u7075\u6839", "\u51dd\u7ec3\u5668\u7075\u6839", "\u8865\u5168\u5668\u7075\u6839", "\u70bc\u5668\u4e3a\u6839")
ROUTE_SELECT_PREFIXES = ("选择路线", "切换路线")
IDENTITY_SELECT_PREFIXES = ("选择身份", "加入身份", "晋升身份")
EVIL_SELECT_TEXTS = {"选择邪修", "加入邪修", "同修邪修"}
EVIL_QUIT_TEXTS = {"退出邪修", "脱离邪修"}
TASK_COMPLETE_PREFIXES = ("完成任务", "提交任务")
BUY_PREFIXES = ("购买", "买入")
SELL_PREFIXES = ("出售", "卖出")
ALCHEMY_PREFIXES = ("炼丹",)
REFINING_PREFIXES = ('炼器',)
ARRAY_DEDUCTION_PREFIXES = ('阵法推演', '推演阵法')
LIFE_ARTIFACT_PREFIXES = ('祭炼本命灵器', '本命灵器', '祭炼本命')
IMMORTAL_SEED_EQUIP_PREFIXES = ('装备仙源', '纳入仙源', '装备仙种', '纳入仙种')
BATCH_SELL_PREFIXES = ('批量出售', '批量卖出', '一键出售')
TRADE_OFFER_PREFIXES = ('交易', '出售给')
TRADE_ACCEPT_PREFIXES = ('接受交易', '购买交易')
TRADE_CANCEL_PREFIXES = ('取消交易', '撤销交易')
MARKET_TEXTS = {'万宝楼', '万宝楼列表', '万宝阁', '寄售列表'}
MARKET_OFFER_PREFIXES = ('万宝楼挂售', '万宝楼寄售', '挂售', '寄售')
MARKET_BUY_PREFIXES = ('万宝楼购买', '万宝楼买入', '购买万宝楼')
MARKET_CANCEL_PREFIXES = ('万宝楼下架', '下架寄售', '下架')
RESCUE_REQUEST_PREFIXES = ('秘境救援', '发起救援')
RESCUE_TAKE_PREFIXES = ('救援', '接受救援')
TALISMAN_DRAW_PREFIXES = ("\u7ed8\u5236\u7b26\u7b93", "\u753b\u7b26", "\u5236\u7b26", "\u7ed8\u7b26")
SPECIAL_ABILITY_LEARN_PREFIXES = ("\u9886\u609f\u795e\u901a", "\u53c2\u609f\u795e\u901a")
MYSTIC_EXPLORE_PREFIXES = ("探索", "秘境探索")
DIVINATION_PREFIXES = ("\u5929\u673a\u5360\u535c", "\u5360\u535c", "\u7b97\u547d", "\u95ee\u5366", "\u8d77\u5366", "\u535c\u5366")
DUEL_PREFIXES = ("pk", "PK", "切磋", "挑战")
NORMAL_DUEL_TEXTS = {"申请普通斗法", "普通斗法", "普通斗法申请", "申请斗法", "斗法匹配"}
FISHING_TEXTS = ("\u5782\u9493", "\u9493\u9c7c", "\u8bf8\u5929\u4e07\u754c\u5782\u9493")
COMMAND_PREFIX_CHARS = "/!！.。"
PENDING_FISHING_TTL = 120
MYSTIC_ENTRY_TTL = 60
DIVINATION_PENDING_TTL = 60
TIANJI_HALL_IDENTITIES = {"\u5929\u673a\u9601\u5f1f\u5b50", "\u5929\u673a\u9601\u957f\u8001", "\u5929\u673a\u9601\u592a\u4e0a\u957f\u8001"}
DIVINATION_SITTER_INCOME = 8
NORMAL_DUEL_PREPARE_SECONDS = 60
NORMAL_DUEL_DURATION_SECONDS = 60
NORMAL_DUEL_ACTION_SEGMENT_LABELS = {
    "face": "\u8868\u60c5\u672f\u5f0f",
    "mface": "\u6536\u85cf\u8868\u60c5\u672f\u5f0f",
    "image": "\u5f71\u50cf\u672f\u5f0f",
    "record": "\u97f3\u6d6a\u672f\u5f0f",
    "video": "\u955c\u5f71\u672f\u5f0f",
    "dice": "\u9ab0\u7075\u672f\u5f0f",
    "rps": "\u62f3\u4ee4\u672f\u5f0f",
    "poke": "\u6307\u52b2\u672f\u5f0f",
    "share": "\u501f\u52bf\u672f\u5f0f",
    "json": "\u5f02\u6587\u672f\u5f0f",
    "xml": "\u5f02\u6587\u672f\u5f0f",
}
NORMAL_DUEL_IGNORED_SEGMENT_TYPES = {"at", "reply", "node"}
RANK_SETTLE_HOUR = 22
RANK_SETTLE_MINUTE = 0
pending_fishing_users: dict[str, float] = {}
pending_mystic_entries: dict[str, dict[str, Any]] = {}
pending_divinations: dict[str, dict[str, Any]] = {}
normal_duel_queue: dict[str, dict[str, Any]] = {}
normal_duel_sessions: dict[str, dict[str, Any]] = {}
doudizhu_tables: dict[str, dict[str, Any]] = {}
beast_realm_tables: dict[str, dict[str, Any]] = {}
beast_realm_private_routes: dict[str, str] = {}
rank_scheduler_task: Optional[asyncio.Task] = None
admin_http_server = None


async def send_mystic_timeout_notice(
    key: str,
    expected_expires_at: float,
    user_id: str,
    group_id: Optional[str] = None,
) -> None:
    await asyncio.sleep(max(0.0, expected_expires_at - time.monotonic()))
    pending = pending_mystic_entries.get(key)
    if pending is None or float(pending.get("expires_at", 0)) != expected_expires_at:
        return
    pending_mystic_entries.pop(key, None)
    try:
        record = await store.get_user(user_id)
        message = panel_segment("秘境入口", "已超时，如有需求系统将为宿主重新抽取。", record, icon="warning")
        bot = get_bot()
        if group_id is not None:
            await bot.send_group_msg(group_id=int(group_id), message=message)
        else:
            await bot.send_private_msg(user_id=int(user_id), message=message)
    except Exception:
        logger.exception("发送秘境入口超时提示失败")


async def send_divination_timeout_notice(
    key: str,
    expected_expires_at: float,
    user_id: str,
    group_id: Optional[str] = None,
) -> None:
    await asyncio.sleep(max(0.0, expected_expires_at - time.monotonic()))
    pending = pending_divinations.get(key)
    if pending is None or float(pending.get("expires_at", 0)) != expected_expires_at:
        return
    pending_divinations.pop(key, None)
    try:
        record = await store.get_user(user_id)
        message = panel_segment(
            "\u5929\u673a\u5360\u535c",
            "\u5366\u706b\u5df2\u706d\uff0c\u672c\u6b21\u95ee\u5366\u5df2\u8d85\u65f6\u3002\u5982\u9700\u518d\u95ee\uff0c\u8bf7\u91cd\u65b0\u53d1\u9001\u201c\u5929\u673a\u5360\u535c\u201d\u3002",
            record,
            icon="warning",
        )
        bot = get_bot()
        if group_id is not None:
            await bot.send_group_msg(group_id=int(group_id), message=message)
        else:
            await bot.send_private_msg(user_id=int(user_id), message=message)
    except Exception:
        logger.exception("\u53d1\u9001\u5929\u673a\u5360\u535c\u8d85\u65f6\u63d0\u793a\u5931\u8d25")


def load_config() -> Config:
    data = driver.config.model_dump() if hasattr(driver.config, "model_dump") else driver.config.dict()
    if hasattr(Config, "model_validate"):
        return Config.model_validate(data)
    return Config.parse_obj(data)


config = load_config()
set_font_paths(config.xiuxian_signin_font_path, config.xiuxian_signin_bold_font_path)


def get_data_dir() -> Path:
    if config.xiuxian_signin_data_dir:
        return Path(config.xiuxian_signin_data_dir)
    return localstore.get_plugin_data_dir()


store = JsonStore(get_data_dir())
admin_manager = AdminManager(store, get_data_dir(), config.xiuxian_signin_admin_token or "")


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


def local_now() -> datetime:
    try:
        return datetime.now(ZoneInfo(config.xiuxian_signin_timezone))
    except Exception:
        return datetime.now()


def local_today() -> date:
    return local_now().date()


async def fetch_avatar(user_id: str) -> Optional[bytes]:
    if httpx is None:
        return None
    url = f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=config.xiuxian_signin_avatar_timeout,
        ) as client:
            response = await client.get(url)
        if response.status_code == 200 and response.content:
            return response.content
    except Exception as exc:
        logger.debug(f"获取 QQ 头像失败: {exc}")
    return None


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


def is_mystic_explore_command_text(text: str) -> bool:
    return is_prefixed_index_command(text, MYSTIC_EXPLORE_PREFIXES)


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
    return text in SHOP_TEXTS or parse_shop_buy_index(text) is not None or parse_sell_item(text) is not None or parse_batch_sell(text) is not None


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


def parse_divination_question(text: str) -> Optional[str]:
    stripped = text.strip()
    for prefix in DIVINATION_PREFIXES:
        if stripped == prefix:
            return ""
        if stripped.startswith(prefix):
            rest = stripped[len(prefix):].strip()
            return rest.lstrip(" \t:：，,。").strip()
    return None


def is_divination_command_text(text: str) -> bool:
    return parse_divination_question(text) is not None


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


def mystic_pending_key(event: MessageEvent) -> str:
    if isinstance(event, GroupMessageEvent):
        return f"group:{event.group_id}:{event.get_user_id()}"
    return f"private:{event.get_user_id()}"


def divination_pending_key(event: MessageEvent) -> str:
    return mystic_pending_key(event)


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


def is_managed_command_text(text: str) -> bool:
    return (
        text in SIGNIN_TEXTS
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
        or text in MYSTIC_ENTRY_TEXTS
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
        or is_divination_command_text(text)
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
        or is_mystic_explore_command_text(text)
        or is_duel_command_text(text)
    )


def panel_accent(record=None) -> str:
    root = getattr(record, "root", None)
    return getattr(root, "color", "#3589d8") if root else "#3589d8"


def panel_segment(
    title: str,
    content: str | list[str],
    record=None,
    subtitle: str = "",
    icon: str = "scroll",
    footer: str = "",
) -> MessageSegment:
    image_bytes = render_text_panel(
        title=title,
        content=content,
        subtitle=subtitle,
        icon=icon,
        accent=panel_accent(record),
        width=config.xiuxian_signin_image_width,
        footer=footer,
    )
    return MessageSegment.image(BytesIO(image_bytes))


async def send_panel(
    matcher: Matcher,
    title: str,
    content: str | list[str],
    record=None,
    subtitle: str = "",
    icon: str = "scroll",
    footer: str = "",
) -> None:
    await matcher.send(panel_segment(title, content, record, subtitle, icon, footer))


async def finish_panel(
    matcher: Matcher,
    title: str,
    content: str | list[str],
    record=None,
    subtitle: str = "",
    icon: str = "scroll",
    footer: str = "",
) -> None:
    await matcher.finish(panel_segment(title, content, record, subtitle, icon, footer))


async def send_private_panel(
    user_id: str,
    title: str,
    content: str | list[str],
    record=None,
    subtitle: str = "",
    icon: str = "scroll",
    footer: str = "",
) -> bool:
    try:
        await get_bot().send_private_msg(
            user_id=int(user_id),
            message=panel_segment(title, content, record, subtitle, icon, footer),
        )
        return True
    except Exception as exc:
        logger.debug(f"发送私聊面板失败: {user_id} {title} {exc}")
        return False


async def finish_private_or_current_panel(
    matcher: Matcher,
    event: MessageEvent,
    title: str,
    content: str | list[str],
    record=None,
    subtitle: str = "",
    icon: str = "scroll",
    footer: str = "",
    group_success: str = "已通过私聊发送，请查看私聊。",
) -> None:
    if isinstance(event, GroupMessageEvent):
        sent = await send_private_panel(event.get_user_id(), title, content, record, subtitle, icon, footer)
        if sent:
            await finish_panel(matcher, title, group_success, record, icon=icon)
        await finish_panel(matcher, "私聊发送失败", f"{title}已生成，但私聊发送失败，请检查好友或临时会话权限。", record, icon="warning")
    await finish_panel(matcher, title, content, record, subtitle=subtitle, icon=icon, footer=footer)


async def send_image(matcher: Matcher, image_bytes: bytes) -> None:
    await matcher.send(MessageSegment.image(BytesIO(image_bytes)))


def is_tianji_hall_identity(record: Any) -> bool:
    return str(getattr(record, "faction_identity", "") or "") in TIANJI_HALL_IDENTITIES


def tianji_sitters(hall: dict[str, Any]) -> list[dict[str, str]]:
    raw_sitters = hall.get("sitters")
    if not isinstance(raw_sitters, list) or not raw_sitters:
        primary_id = str(hall.get("sitter_id") or "")
        if not primary_id:
            return []
        raw_sitters = [{"user_id": primary_id, "nickname": str(hall.get("sitter_name") or primary_id)}]
    result: list[dict[str, str]] = []
    seen = set()
    for item in raw_sitters:
        if not isinstance(item, dict):
            continue
        sitter_id = str(item.get("user_id") or "")
        if not sitter_id or sitter_id in seen:
            continue
        seen.add(sitter_id)
        result.append({"user_id": sitter_id, "nickname": str(item.get("nickname") or f"QQ {sitter_id}")})
    return result


def tianji_sitter_names(hall: dict[str, Any], limit: int = 4) -> str:
    sitters = tianji_sitters(hall)
    names = [str(item.get("nickname") or item.get("user_id")) for item in sitters]
    if not names:
        return "天机阁门人"
    if len(names) > limit:
        return "、".join(names[:limit]) + f"等{len(names)}人"
    return "、".join(names)


async def require_tianji_hall(matcher: Matcher, event: MessageEvent, record: Any) -> dict[str, Any]:
    if not isinstance(event, GroupMessageEvent):
        await finish_panel(
            matcher,
            "\u5929\u673a\u5360\u535c",
            "\u5929\u673a\u5360\u535c\u9700\u5728\u7fa4\u5185\u7531\u5929\u673a\u9601\u95e8\u4eba\u5750\u5802\u540e\u5f00\u542f\uff0c\u8bf7\u5230\u7fa4\u804a\u4e2d\u4f7f\u7528\u3002",
            record,
            icon="divination",
        )
        return {}
    hall = await store.get_tianji_hall(str(event.group_id), local_today().isoformat())
    if not hall:
        await finish_panel(
            matcher,
            "\u5929\u673a\u5360\u535c",
            "\u4eca\u65e5\u5c1a\u65e0\u5929\u673a\u9601\u5f1f\u5b50\u5750\u5802\uff0c\u65e0\u6cd5\u5f00\u542f\u5360\u535c\u3002\n\u8bf7\u7b49\u5f85\u672c\u7fa4\u7b2c\u4e00\u4f4d\u5929\u673a\u9601\u95e8\u4eba\u7b7e\u5230\u5750\u5802\uff0c\u518d\u6765\u95ee\u5366\u3002",
            record,
            icon="warning",
        )
        return {}
    return hall


async def settle_divination_income(event: MessageEvent, viewer_record: Any = None) -> str:
    if not isinstance(event, GroupMessageEvent):
        return ""
    hall = await store.add_tianji_divination_income(
        str(event.group_id),
        local_today().isoformat(),
        DIVINATION_SITTER_INCOME,
    )
    if not hall:
        return ""
    sitters = tianji_sitters(hall)
    if not sitters:
        return ""
    base_share = DIVINATION_SITTER_INCOME // len(sitters)
    remainder = DIVINATION_SITTER_INCOME % len(sitters)
    shares: list[tuple[dict[str, str], int]] = []
    for index, sitter in enumerate(sitters):
        amount = base_share + (1 if index < remainder else 0)
        if amount > 0:
            shares.append((sitter, amount))

    for sitter, amount in shares:
        sitter_id = str(sitter.get("user_id") or "")
        if not sitter_id:
            continue

        def updater(record: Any, gain: int = amount) -> None:
            record.spirit_stones = int(getattr(record, "spirit_stones", 0)) + gain

        await store.apply_to_user(sitter_id, updater)
        if viewer_record is not None and str(getattr(viewer_record, "user_id", "")) == sitter_id:
            viewer_record.spirit_stones = int(getattr(viewer_record, "spirit_stones", 0)) + amount

    count = int(hall.get("divination_count", 0))
    income = int(hall.get("income", 0))
    share_text = "\u3001".join(
        f"{sitter.get('nickname') or sitter.get('user_id')}+{spirit_stone_text(amount)}"
        for sitter, amount in shares
    )
    return (
        f"\n\n\u3010\u5750\u5802\u6da6\u8d44\u3011\u672c\u6b21\u5171 {spirit_stone_text(DIVINATION_SITTER_INCOME)}\uff0c"
        f"\u7531 {len(sitters)} \u4f4d\u5929\u673a\u9601\u95e8\u4eba\u5e73\u5206\uff1a{share_text}\u3002"
        f"\n\u4eca\u65e5\u5df2\u5360 {count} \u5366\uff0c\u5750\u5802\u7d2f\u8ba1 {spirit_stone_text(income)}\u3002"
    )


async def build_signin_image(event: MessageEvent, result: SigninResult) -> bytes:
    avatar = await fetch_avatar(event.get_user_id())
    return render_signin_card(
        result=result,
        nickname=nickname_from_event(event),
        avatar_bytes=avatar,
        width=config.xiuxian_signin_image_width,
    )


async def build_fishing_image(
    event: MessageEvent,
    record,
    rewards,
) -> bytes:
    avatar = await fetch_avatar(event.get_user_id())
    return render_fishing_card(
        record=record,
        rewards=rewards,
        nickname=nickname_from_event(event),
        avatar_bytes=avatar,
        width=config.xiuxian_signin_image_width,
    )




def normal_duel_prepare_cards(record, nickname: str) -> list[tuple[str, str, str]]:
    ensure_combat_profile(record)
    techniques = available_battle_techniques(record)
    technique_lines = []
    for index, tech in enumerate(techniques[:6], start=1):
        technique_lines.append(f"{index}. {tech}\uff1a\u8017\u7075{technique_mana_cost(record, tech)}\uff0cCD{technique_cooldown(tech)}\u606f")
    if not technique_lines:
        technique_lines.append("\u6682\u65e0\u6218\u6280\uff0c\u53ef\u53d1\u9001\u8868\u60c5\u6216\u5373\u5174\u53f0\u8bcd\u5c1d\u8bd5\u7275\u52a8\u57fa\u7840\u672f\u5f0f\u3002")
    abilities = "\u3001".join(record.special_abilities or []) or "\u6682\u65e0\u663e\u5316"
    talismans = available_talismans(record)
    talisman_lines = []
    for index, talisman in enumerate(talismans[:6], start=1):
        talisman_lines.append(f"{index}. {reward_display_name(talisman)}")
    if not talisman_lines:
        talisman_lines.append("\u6682\u65e0\u53ef\u7528\u7b26\u7b93\uff1b\u672c\u573a\u53ef\u4f9d\u9760\u6218\u6280\u3001\u795e\u901a\u3001\u4f53\u672f\u548c\u4f53\u8d28\u7279\u6027\u3002")
    equipped_talisman = reward_display_name(record.equipped_talisman) if record.equipped_talisman else "\u672a\u88c5\u5907\u7b26\u7b93"
    array_text = reward_display_name(record.equipped_array) if record.equipped_array else "\u672a\u5e03\u7f6e\u9635\u76d8"
    cards = [
        (
            "\u6597\u6cd5\u51c6\u5907\u00b7\u4fee\u4e3a\u786e\u8ba4",
            "\n".join(
                [
                    f"{nickname or '\u5bbf\u4e3b'}\uff0c\u666e\u901a\u6597\u6cd5\u5c06\u572860\u79d2\u540e\u5f00\u59cb\u3002",
                    f"\u5883\u754c\uff1a{record.realm if record.root else '\u672a\u5165\u95e8'}",
                    f"\u5883\u754c\u54c1\u76f8\uff1a{record.realm_quality}",
                    f"\u6218\u529b\uff1a{battle_power(record)}",
                    f"\u7075\u529b\u4e0a\u9650\uff1a{combat_max_mana(record)}",
                    f"\u7075\u6839\uff1a{record.root_summary}",
                    f"\u79cd\u65cf\uff1a{record.combat_race or '\u672a\u8bb0\u5f55'}",
                    f"\u4f53\u8d28\uff1a{record.physique or '\u672a\u8bb0\u5f55'}",
                ]
            ),
            "realm",
        ),
        (
            "\u6597\u6cd5\u51c6\u5907\u00b7\u6218\u6280\u914d\u7f6e",
            "\n".join(
                [
                    f"\u5f53\u524d\u529f\u6cd5\uff1a{reward_display_name(record.equipped_method) if record.equipped_method else '\u672a\u53c2\u609f\u529f\u6cd5'}",
                    "\u53ef\u7528\u6218\u6280\uff1a",
                    *technique_lines,
                    f"\u795e\u901a\uff1a{abilities}",
                    "\u6218\u6280\u4f1a\u6d88\u8017\u7075\u529b\u5e76\u8fdb\u5165CD\uff1b\u672a\u547d\u4e2d\u7684\u53d1\u8a00\u4f1a\u4f5c\u4e3a\u5373\u5174\u672f\u5f0f\u3002",
                ]
            ),
            "method",
        ),
        (
            "\u6597\u6cd5\u51c6\u5907\u00b7\u9635\u76d8\u914d\u7f6e",
            "\n".join(
                [
                    f"\u5f53\u524d\u9635\u76d8\uff1a{array_text}",
                    f"\u9635\u6cd5\u500d\u7387\uff1a{array_multiplier(record):.1f}x",
                    "\u9635\u76d8\u4f1a\u5f71\u54cd\u529f\u6cd5\u6536\u76ca\u4e0e\u90e8\u5206\u6218\u6597\u9762\u677f\u8ba1\u7b97\uff1b\u719f\u7ec3\u5ea6\u8d8a\u9ad8\u8d8a\u7a33\u5b9a\u3002",
                ]
            ),
            "array",
        ),
        (
            "\u6597\u6cd5\u51c6\u5907\u00b7\u7b26\u7b93\u51c6\u5907",
            "\n".join(
                [
                    f"\u5f53\u524d\u7b26\u7b93\u680f\uff1a{equipped_talisman}",
                    "\u53ef\u7528\u7b26\u7b93\uff1a",
                    *talisman_lines,
                    "\u53d1\u9001\u201c\u88c5\u5907\u7b26\u7b93 \u7f16\u53f7\u201d\u53ef\u653e\u5165\u7b26\u7b93\u680f\uff1b\u666e\u901a\u6597\u6cd5\u751f\u6548\u4e14\u4e0d\u6d88\u8017\u3002",
                    "\u53d1\u9001\u201c\u4f7f\u7528\u7b26\u7b93 \u7f16\u53f7\u201d\u4ecd\u4f1a\u4f5c\u4e3a\u4e00\u6b21\u6027\u7b26\u7b93\u6fc0\u53d1\u5e76\u6d88\u8017\u3002",
                ]
            ),
            "talisman",
        ),
    ]
    return cards


async def send_normal_duel_prepare_cards(user_id: str, record, nickname: str) -> None:
    bot = get_bot()
    for title, content, icon in normal_duel_prepare_cards(record, nickname):
        try:
            await bot.send_private_msg(
                user_id=int(user_id),
                message=panel_segment(title, content, record, icon=icon),
            )
        except Exception as exc:
            logger.debug(f"\u53d1\u9001\u6597\u6cd5\u51c6\u5907\u79c1\u804a\u5931\u8d25: {user_id} {exc}")


async def send_normal_duel_prepare_messages(session: dict[str, Any]) -> None:
    left_id = str(session.get("left_id"))
    right_id = str(session.get("right_id"))
    left_record, right_record = await asyncio.gather(store.get_user(left_id), store.get_user(right_id))
    ensure_combat_profile(left_record)
    ensure_combat_profile(right_record)
    await asyncio.gather(store.save_user(left_record), store.save_user(right_record))
    await asyncio.gather(
        send_normal_duel_prepare_cards(left_id, left_record, str(session.get("left_name") or left_id)),
        send_normal_duel_prepare_cards(right_id, right_record, str(session.get("right_name") or right_id)),
    )


async def send_mystic_boss_duel_report(user_id: str, record, result: dict[str, Any]) -> bool:
    if not result:
        return False
    try:
        left = result.get("left", {})
        right = result.get("right", {})
        left_avatar = await fetch_avatar(str(left.get("user_id") or user_id))
        right_avatar = beast_portrait_bytes(str(right.get("nickname") or ""))
        image = render_battle_card(
            result,
            left_avatar=left_avatar,
            right_avatar=right_avatar,
            width=config.xiuxian_signin_image_width,
        )
        await get_bot().send_private_msg(user_id=int(user_id), message=MessageSegment.image(BytesIO(image)))
        return True
    except Exception as exc:
        logger.debug(f"发送秘境首领斗法私聊战报失败: {user_id} {exc}")
        try:
            await get_bot().send_private_msg(
                user_id=int(user_id),
                message=panel_segment("秘境首领斗法", "斗法战报生成完成，但图片私聊发送失败，请检查好友或临时会话权限。", record, icon="warning"),
            )
        except Exception:
            logger.debug(f"发送秘境首领斗法失败提示失败: {user_id}")
        return False


async def build_normal_duel_image(result: dict[str, Any]) -> bytes:
    left = result.get("left", {})
    right = result.get("right", {})
    left_avatar, right_avatar = await asyncio.gather(
        fetch_avatar(str(left.get("user_id", ""))),
        fetch_avatar(str(right.get("user_id", ""))),
    )
    return render_battle_card(
        result,
        left_avatar=left_avatar,
        right_avatar=right_avatar,
        width=config.xiuxian_signin_image_width,
    )


def group_duel_session(group_id: str) -> Optional[dict[str, Any]]:
    session = normal_duel_sessions.get(group_id)
    if not session:
        return None
    now = time.monotonic()
    if now > float(session.get("end_at", 0)) + 10:
        normal_duel_sessions.pop(group_id, None)
        return None
    return session


async def finish_normal_duel(group_id: str, session: dict[str, Any]) -> None:
    try:
        await asyncio.sleep(max(0.0, float(session["start_at"]) - time.monotonic()))
        session["active"] = True
        bot = get_bot()
        await bot.send_group_msg(
            group_id=int(group_id),
            message=panel_segment(
                "\u666e\u901a\u6597\u6cd5",
                "\u6597\u6cd5\u5df2\u5f00\u59cb\uff0c60\u79d2\u5185\u53d1\u9001\u6218\u6280\u3001\u795e\u901a\u3001\u8868\u60c5\u6216\u5373\u5174\u672f\u5f0f\u3002",
                icon="duel",
            ),
        )
        await asyncio.sleep(max(0.0, float(session["end_at"]) - time.monotonic()))
        current = normal_duel_sessions.get(group_id)
        if current is not session:
            return
        left_id = str(session["left_id"])
        right_id = str(session["right_id"])
        left_record, right_record = await asyncio.gather(store.get_user(left_id), store.get_user(right_id))
        ensure_combat_profile(left_record)
        ensure_combat_profile(right_record)
        result = simulate_normal_duel(
            left_record,
            right_record,
            str(session.get("left_name") or left_id),
            str(session.get("right_name") or right_id),
            list(session.get("actions", {}).get(left_id, [])),
            list(session.get("actions", {}).get(right_id, [])),
            NORMAL_DUEL_DURATION_SECONDS,
        )
        await store.save_user(left_record)
        await store.save_user(right_record)
        image = await build_normal_duel_image(result)
        await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(BytesIO(image)))
    except Exception:
        logger.exception("\u666e\u901a\u6597\u6cd5\u7ed3\u7b97\u5931\u8d25")
    finally:
        if normal_duel_sessions.get(group_id) is session:
            normal_duel_sessions.pop(group_id, None)


def append_normal_duel_action(event: GroupMessageEvent, text: str) -> bool:
    group_id = str(event.group_id)
    session = group_duel_session(group_id)
    if not session or not session.get("active"):
        return False
    now = time.monotonic()
    if now < float(session.get("start_at", 0)) or now > float(session.get("end_at", 0)):
        return False
    user_id = event.get_user_id()
    if user_id not in {str(session.get("left_id")), str(session.get("right_id"))}:
        return False
    actions = session.setdefault("actions", {}).setdefault(user_id, [])
    actions.append({"text": text, "time": now})
    return True


DDZ_RANKS = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "小王", "大王"]
DDZ_VALUES = {rank: index for index, rank in enumerate(DDZ_RANKS)}
DDZ_HUMAN_WAIT_SECONDS = 120


def doudizhu_group_key(event: GroupMessageEvent) -> str:
    return str(event.group_id)


def is_doudizhu_play_text(text: str) -> bool:
    return any(text == prefix or text.startswith(prefix) for prefix in DOUDIZHU_PLAY_PREFIXES)


def is_doudizhu_bid_text(text: str) -> bool:
    return text in {"叫地主", "不叫"} or any(text == prefix or text.startswith(prefix) for prefix in DOUDIZHU_BID_PREFIXES)


def is_doudizhu_command_text(text: str) -> bool:
    return (
        text in DOUDIZHU_TEXTS
        or is_doudizhu_play_text(text)
        or is_doudizhu_bid_text(text)
    )


def is_doudizhu_entry_text(text: str) -> bool:
    return text in DOUDIZHU_HELP_TEXTS or text in {"\u6597\u5730\u4e3b", "\u6597\u5730\u4e3b\u5f00\u684c", "\u4eba\u673a\u6597\u5730\u4e3b"}


def doudizhu_help_text() -> str:
    return "\n".join(
        [
            "【斗地主帮助】",
            "开桌流程：斗地主开桌 -> 加入斗地主 -> 开始斗地主；也可直接人机斗地主。",
            "手牌会私聊发送，群内发送手牌可重新查看。",
            "叫分阶段：叫分 1/2/3，或发送叫地主 / 不叫。分数最高者进入抢地主阶段。",
            "抢地主阶段：其他玩家可发送抢地主 / 不抢。高修为玩家可发送施加威压提高抢夺概率。",
            "威压成功后，原定地主可以发送保留地主 / 放弃地主。若保留，牌局结束后强制进行普通斗法。",
            "地主确定后进入加倍阶段，发送加倍 / 不加倍；每次加倍会翻倍最终倍数。",
            "出牌：出牌 34567、出牌 3334、出牌 小王大王；跟不上发送不要。",
            "修仙牌型：炸弹显示为雷劫，王炸显示为天罚雷劫，触发后都会让当前倍数翻倍。",
            "春天 / 反春天已实装：达成条件时会在结算面板中标记，并再翻倍。",
            "其他指令：提示 / 托管 / 结束斗地主。",
        ]
    )


def ddz_new_deck() -> list[str]:
    deck = []
    for rank in DDZ_RANKS[:-2]:
        deck.extend([rank] * 4)
    deck.extend(["小王", "大王"])
    random.shuffle(deck)
    return deck


def ddz_sort_cards(cards: list[str]) -> list[str]:
    return sorted(cards, key=lambda card: (DDZ_VALUES.get(card, -1), card))


def ddz_cards_text(cards: list[str]) -> str:
    return " ".join(ddz_sort_cards(list(cards))) or "无"


def ddz_parse_cards(text: str) -> list[str]:
    stripped = text.strip()
    for prefix in DOUDIZHU_PLAY_PREFIXES:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):].strip()
            break
    stripped = stripped.replace("王炸", "小王 大王").replace("双王", "小王 大王").replace("天罚雷劫", "小王 大王")
    for sep in [",", "，", "、", ";", "；", "|", "/"]:
        stripped = stripped.replace(sep, " ")
    result: list[str] = []
    index = 0
    compact = "".join(stripped.split())
    while index < len(compact):
        matched = None
        for token in ("小王", "大王", "10", "J", "Q", "K", "A", "2", "3", "4", "5", "6", "7", "8", "9"):
            if compact.startswith(token, index):
                matched = token
                break
        if matched is None:
            return []
        result.append(matched)
        index += len(matched)
    return result


def ddz_has_cards(hand: list[str], cards: list[str]) -> bool:
    hand_counter = Counter(hand)
    for card, count in Counter(cards).items():
        if hand_counter[card] < count:
            return False
    return True


def ddz_remove_cards(hand: list[str], cards: list[str]) -> None:
    for card in cards:
        hand.remove(card)


def ddz_is_consecutive(ranks: list[str]) -> bool:
    values = [DDZ_VALUES[rank] for rank in ranks]
    return all(values[i] + 1 == values[i + 1] for i in range(len(values) - 1))


def ddz_no_high_sequence(ranks: list[str]) -> bool:
    return all(rank not in {"2", "小王", "大王"} for rank in ranks)


def ddz_analyze_cards(cards: list[str]) -> Optional[dict[str, Any]]:
    if not cards:
        return None
    cards = ddz_sort_cards(cards)
    total = len(cards)
    counts = Counter(cards)
    count_values = sorted(counts.values(), reverse=True)
    ranks = sorted(counts, key=lambda rank: DDZ_VALUES[rank])
    if total == 2 and set(cards) == {"小王", "大王"}:
        return {"type": "rocket", "main": DDZ_VALUES["大王"], "length": 2, "label": "天罚雷劫"}
    if total == 4 and len(counts) == 1:
        return {"type": "bomb", "main": DDZ_VALUES[ranks[0]], "length": 4, "label": f"{ranks[0]}重雷劫"}
    if total == 1:
        return {"type": "single", "main": DDZ_VALUES[cards[0]], "length": 1, "label": "单牌"}
    if total == 2 and len(counts) == 1:
        return {"type": "pair", "main": DDZ_VALUES[ranks[0]], "length": 1, "label": "对子"}
    if total == 3 and len(counts) == 1:
        return {"type": "triple", "main": DDZ_VALUES[ranks[0]], "length": 1, "label": "三同"}
    if total == 4 and count_values == [3, 1]:
        triple = next(rank for rank, count in counts.items() if count == 3)
        return {"type": "triple_single", "main": DDZ_VALUES[triple], "length": 1, "label": "三带一"}
    if total == 5 and count_values == [3, 2]:
        triple = next(rank for rank, count in counts.items() if count == 3)
        return {"type": "triple_pair", "main": DDZ_VALUES[triple], "length": 1, "label": "三带一对"}
    if total >= 5 and len(counts) == total and ddz_no_high_sequence(ranks) and ddz_is_consecutive(ranks):
        return {"type": "straight", "main": DDZ_VALUES[ranks[-1]], "length": total, "label": f"{total}连顺"}
    if total >= 6 and total % 2 == 0 and all(count == 2 for count in counts.values()) and ddz_no_high_sequence(ranks) and ddz_is_consecutive(ranks):
        return {"type": "pair_chain", "main": DDZ_VALUES[ranks[-1]], "length": total // 2, "label": f"{total // 2}连对"}
    triple_ranks = sorted([rank for rank, count in counts.items() if count == 3], key=lambda rank: DDZ_VALUES[rank])
    if len(triple_ranks) >= 2 and ddz_no_high_sequence(triple_ranks) and ddz_is_consecutive(triple_ranks):
        wings = total - len(triple_ranks) * 3
        if wings == 0:
            return {"type": "airplane", "main": DDZ_VALUES[triple_ranks[-1]], "length": len(triple_ranks), "label": f"飞舟{len(triple_ranks)}舱"}
        if wings == len(triple_ranks):
            return {"type": "airplane_single", "main": DDZ_VALUES[triple_ranks[-1]], "length": len(triple_ranks), "label": f"飞舟带翼{len(triple_ranks)}舱"}
        if wings == len(triple_ranks) * 2:
            pair_wings = [rank for rank, count in counts.items() if count == 2]
            if len(pair_wings) == len(triple_ranks):
                return {"type": "airplane_pair", "main": DDZ_VALUES[triple_ranks[-1]], "length": len(triple_ranks), "label": f"飞舟载侣{len(triple_ranks)}舱"}
    return None


def ddz_can_beat(play: dict[str, Any], last_play: Optional[dict[str, Any]]) -> bool:
    if not last_play:
        return True
    if play["type"] == "rocket":
        return last_play["type"] != "rocket"
    if play["type"] == "bomb" and last_play["type"] not in {"bomb", "rocket"}:
        return True
    if play["type"] != last_play["type"]:
        return False
    if int(play.get("length", 0)) != int(last_play.get("length", 0)):
        return False
    return int(play["main"]) > int(last_play["main"])


def ddz_player(table: dict[str, Any], user_id: str) -> Optional[dict[str, Any]]:
    for player in table.get("players", []):
        if str(player.get("id")) == str(user_id):
            return player
    return None


def ddz_current_player(table: dict[str, Any]) -> dict[str, Any]:
    return table["players"][int(table.get("current", 0)) % len(table["players"])]


def ddz_next_turn(table: dict[str, Any]) -> None:
    table["current"] = (int(table.get("current", 0)) + 1) % len(table["players"])


def ddz_player_line(player: dict[str, Any], table: dict[str, Any]) -> str:
    role = "地主" if str(player.get("id")) == str(table.get("landlord")) else "散修"
    bot = "机关傀儡" if player.get("bot") else ""
    doubled = "已加倍" if str(player.get("id")) in set(table.get("double_votes", [])) else "未加倍"
    return f"{player.get('name')}｜{role}{bot}｜剩{len(player.get('hand', []))}张｜{doubled}"


def ddz_table_text(table: dict[str, Any], extra: str = "") -> str:
    lines = ["【斗地主牌局】", f"阶段：{table.get('phase_text', table.get('phase', '未知'))}"]
    if table.get("landlord"):
        landlord = ddz_player(table, str(table.get("landlord")))
        lines.append(f"地主：{landlord.get('name') if landlord else table.get('landlord')}｜倍数 {table.get('multiplier', 1)}x")
    if table.get("bottom"):
        lines.append(f"底牌：{ddz_cards_text(list(table.get('bottom', [])))}")
    if table.get("last_play"):
        last_player = ddz_player(table, str(table.get("last_player")))
        lines.append(f"上一手：{last_player.get('name') if last_player else '未知'} {table['last_play']['label']} [{ddz_cards_text(table['last_play']['cards'])}]")
    lines.append("玩家：")
    for player in table.get("players", []):
        marker = " ->" if player is ddz_current_player(table) and table.get("phase") == "playing" else ""
        lines.append(f"{marker}{ddz_player_line(player, table)}")
    if extra:
        lines.append("")
        lines.extend(str(extra).splitlines())
    return "\n".join(lines)


def ddz_hand_text(player: dict[str, Any], table: dict[str, Any]) -> str:
    lines = [f"【{player.get('name')}的手牌】", ddz_cards_text(list(player.get("hand", [])))]
    if table.get("phase") == "playing":
        current = ddz_current_player(table)
        lines.append(f"当前出牌：{current.get('name')}")
    if table.get("last_play"):
        lines.append(f"上一手：{table['last_play']['label']} [{ddz_cards_text(table['last_play']['cards'])}]")
    lines.append("指令：出牌 34567 / 不要 / 提示")
    return "\n".join(lines)


def ddz_deal(table: dict[str, Any]) -> None:
    deck = ddz_new_deck()
    for index, player in enumerate(table["players"]):
        player["hand"] = ddz_sort_cards(deck[index * 17:(index + 1) * 17])
        player["bid"] = None
    table["bottom"] = ddz_sort_cards(deck[51:54])
    table["phase"] = "bidding"
    table["phase_text"] = "叫分"
    table["current"] = random.randrange(0, 3)
    table["highest_bid"] = 0
    table["landlord_candidate"] = None
    table["original_landlord"] = None
    table["bid_count"] = 0
    table["rob_passes"] = set()
    table["double_responses"] = set()
    table["double_votes"] = set()
    table["multiplier"] = 1
    table["last_play"] = None
    table["last_player"] = None
    table["pass_count"] = 0
    table["landlord_play_count"] = 0
    table["farmer_play_count"] = 0
    table["pressure_duel"] = None


def ddz_finalize_landlord(table: dict[str, Any], landlord_id: str) -> None:
    table["landlord"] = str(landlord_id)
    table["original_landlord"] = table.get("original_landlord") or str(landlord_id)
    landlord = ddz_player(table, str(landlord_id))
    if landlord:
        landlord["hand"] = ddz_sort_cards(list(landlord.get("hand", [])) + list(table.get("bottom", [])))
    table["phase"] = "double"
    table["phase_text"] = "加倍"
    table["double_responses"] = set()
    table["double_votes"] = set()


def ddz_start_play(table: dict[str, Any]) -> None:
    landlord_id = str(table.get("landlord"))
    table["phase"] = "playing"
    table["phase_text"] = "出牌"
    for idx, player in enumerate(table["players"]):
        if str(player.get("id")) == landlord_id:
            table["current"] = idx
            break


def ddz_bid_status(table: dict[str, Any]) -> str:
    current = ddz_current_player(table)
    lines = ["【叫分阶段】", f"当前轮到：{current.get('name')}", f"当前最高分：{table.get('highest_bid', 0)}"]
    lines.append("可发送：叫分 1 / 叫分 2 / 叫分 3 / 叫地主 / 不叫")
    return "\n".join(lines)


def ddz_begin_rob_text(table: dict[str, Any]) -> str:
    candidate = ddz_player(table, str(table.get("landlord_candidate")))
    names = [p.get("name") for p in table["players"] if str(p.get("id")) != str(table.get("landlord_candidate"))]
    return "\n".join([
        "【抢地主阶段】",
        f"候选地主：{candidate.get('name') if candidate else '未知'}",
        f"可抢修士：{'、'.join(names)}",
        "修为越高，抢夺成功率越高；施加威压会额外提升概率。",
        "可发送：抢地主 / 不抢 / 施加威压",
    ])


def ddz_pressure_chance(actor_power: int, target_power: int, pressure: bool = False) -> float:
    diff = actor_power - target_power
    chance = 0.35 + max(-0.25, min(0.25, diff / max(1, target_power + actor_power) * 1.6))
    if pressure:
        chance += 0.20
    return max(0.10, min(0.85, chance))


def ddz_generate_basic_candidates(hand: list[str]) -> list[list[str]]:
    counter = Counter(hand)
    candidates: list[list[str]] = []
    for rank in DDZ_RANKS:
        if counter[rank] >= 1:
            candidates.append([rank])
    for rank in DDZ_RANKS:
        if counter[rank] >= 2:
            candidates.append([rank, rank])
    for rank in DDZ_RANKS:
        if counter[rank] >= 3:
            candidates.append([rank, rank, rank])
    for rank in DDZ_RANKS:
        if counter[rank] >= 4:
            candidates.append([rank, rank, rank, rank])
    if counter["小王"] and counter["大王"]:
        candidates.append(["小王", "大王"])
    return candidates


def ddz_find_hint(hand: list[str], last_play: Optional[dict[str, Any]]) -> Optional[list[str]]:
    for cards in ddz_generate_basic_candidates(hand):
        analyzed = ddz_analyze_cards(cards)
        if analyzed and ddz_can_beat(analyzed, last_play):
            return cards
    return None


def ddz_bot_should_double(player: dict[str, Any]) -> bool:
    hand = list(player.get("hand", []))
    counter = Counter(hand)
    bombs = sum(1 for rank, count in counter.items() if count == 4)
    jokers = int(counter["小王"] > 0 and counter["大王"] > 0)
    high_cards = sum(1 for card in hand if DDZ_VALUES.get(card, 0) >= DDZ_VALUES["A"])
    return bombs + jokers > 0 or high_cards >= 6


def ddz_bot_play(player: dict[str, Any], table: dict[str, Any]) -> tuple[bool, str]:
    last_play = table.get("last_play") if str(table.get("last_player")) != str(player.get("id")) else None
    cards = ddz_find_hint(list(player.get("hand", [])), last_play)
    if not cards:
        return False, f"{player.get('name')} 选择不出"
    analyzed = ddz_analyze_cards(cards)
    if not analyzed:
        return False, f"{player.get('name')} 选择不出"
    ddz_remove_cards(player["hand"], cards)
    table["last_play"] = {**analyzed, "cards": cards}
    table["last_player"] = str(player.get("id"))
    table["pass_count"] = 0
    if analyzed["type"] in {"bomb", "rocket"}:
        table["multiplier"] = int(table.get("multiplier", 1)) * 2
    if str(player.get("id")) == str(table.get("landlord")):
        table["landlord_play_count"] = int(table.get("landlord_play_count", 0)) + 1
    else:
        table["farmer_play_count"] = int(table.get("farmer_play_count", 0)) + 1
    return True, f"{player.get('name')} 打出 {analyzed['label']}：{ddz_cards_text(cards)}"


async def ddz_send_hand(player: dict[str, Any], table: dict[str, Any], group_id: Optional[str] = None) -> None:
    if player.get("bot"):
        return
    bot = get_bot()
    record = await store.get_user(str(player.get("id")))
    message = panel_segment("斗地主手牌", ddz_hand_text(player, table), record, icon="poker")
    try:
        await bot.send_private_msg(user_id=int(player["id"]), message=message)
    except Exception as exc:
        logger.debug(f"发送斗地主手牌私聊失败: {player.get('id')} {exc}")
        if group_id:
            await bot.send_group_msg(group_id=int(group_id), message=panel_segment("斗地主手牌", "私聊手牌发送失败，请检查好友或临时会话权限。", record, icon="warning"))


async def ddz_send_all_hands(table: dict[str, Any], group_id: str) -> None:
    await asyncio.gather(*(ddz_send_hand(player, table, group_id) for player in table.get("players", []) if not player.get("bot")))


async def start_forced_normal_duel(group_id: str, left_id: str, right_id: str, left_name: str, right_name: str) -> str:
    if group_duel_session(group_id):
        return "本群已有普通斗法进行中，威压约战暂时顺延。"
    start_at = time.monotonic() + NORMAL_DUEL_PREPARE_SECONDS
    session = {
        "left_id": str(left_id),
        "right_id": str(right_id),
        "left_name": left_name,
        "right_name": right_name,
        "created_at": time.monotonic(),
        "start_at": start_at,
        "end_at": start_at + NORMAL_DUEL_DURATION_SECONDS,
        "active": False,
        "actions": {str(left_id): [], str(right_id): []},
    }
    normal_duel_sessions[group_id] = session
    asyncio.create_task(send_normal_duel_prepare_messages(session))
    asyncio.create_task(finish_normal_duel(group_id, session))
    return f"威压结算：{left_name} 与 {right_name} 将在 1 分钟后强制进行普通斗法。"


async def ddz_finish_game(group_id: str, table: dict[str, Any], winner_id: str) -> str:
    landlord_id = str(table.get("landlord"))
    landlord_win = str(winner_id) == landlord_id
    winner = ddz_player(table, str(winner_id))
    landlord = ddz_player(table, landlord_id)
    spring = False
    spring_name = ""
    if landlord_win and int(table.get("farmer_play_count", 0)) == 0:
        spring = True
        spring_name = "春天"
    elif not landlord_win and int(table.get("landlord_play_count", 0)) <= 1:
        spring = True
        spring_name = "反春天"
    if spring:
        table["multiplier"] = int(table.get("multiplier", 1)) * 2
    lines = ["【斗地主结算】"]
    lines.append(f"胜方：{'地主' if landlord_win else '农家'}｜定胜修士：{winner.get('name') if winner else winner_id}")
    lines.append(f"地主：{landlord.get('name') if landlord else landlord_id}")
    lines.append(f"最终倍数：{table.get('multiplier', 1)}x" + (f"｜{spring_name}" if spring else ""))
    lines.append("剩余手牌：")
    for player in table.get("players", []):
        lines.append(f"{player.get('name')}｜剩{len(player.get('hand', []))}张｜[{ddz_cards_text(list(player.get('hand', [])))}]")
    duel_info = table.get("pressure_duel")
    if duel_info:
        duel_message = await start_forced_normal_duel(
            group_id,
            str(duel_info.get("left_id")),
            str(duel_info.get("right_id")),
            str(duel_info.get("left_name")),
            str(duel_info.get("right_name")),
        )
        lines.append("")
        lines.append(duel_message)
    doudizhu_tables.pop(group_id, None)
    return "\n".join(lines)


def ddz_hand_strength(hand: list[str]) -> int:
    counter = Counter(hand)
    score = sum(DDZ_VALUES.get(card, 0) for card in hand)
    score += sum(16 for _rank, count in counter.items() if count == 4)
    if counter["小王"] and counter["大王"]:
        score += 24
    score += sum(5 for card in hand if card in {"2", "小王", "大王"})
    return score


def ddz_bot_bid_value(player: dict[str, Any], highest: int) -> int:
    strength = ddz_hand_strength(list(player.get("hand", [])))
    wanted = 0
    if strength >= 145:
        wanted = 3
    elif strength >= 126:
        wanted = 2
    elif strength >= 108:
        wanted = 1
    return wanted if wanted > highest else 0


def ddz_apply_bid(table: dict[str, Any], player: dict[str, Any], bid: int) -> str:
    table["bid_count"] = int(table.get("bid_count", 0)) + 1
    player["bid"] = bid
    if bid > int(table.get("highest_bid", 0)):
        table["highest_bid"] = bid
        table["landlord_candidate"] = str(player.get("id"))
        return f"{player.get('name')} 叫分 {bid}"
    return f"{player.get('name')} 不叫"


def ddz_after_bid(table: dict[str, Any]) -> Optional[str]:
    if int(table.get("highest_bid", 0)) >= 3 or int(table.get("bid_count", 0)) >= len(table.get("players", [])):
        if not table.get("landlord_candidate"):
            ddz_deal(table)
            return "无人叫地主，重新洗牌。\n" + ddz_bid_status(table)
        table["phase"] = "rob"
        table["phase_text"] = "抢地主"
        table["original_landlord"] = str(table.get("landlord_candidate"))
        table["rob_passes"] = set()
        return ddz_begin_rob_text(table)
    ddz_next_turn(table)
    return None


async def ddz_process_bot_bidding(group_id: str, table: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    while table.get("phase") == "bidding" and ddz_current_player(table).get("bot"):
        player = ddz_current_player(table)
        bid = ddz_bot_bid_value(player, int(table.get("highest_bid", 0)))
        logs.append(ddz_apply_bid(table, player, bid))
        result = ddz_after_bid(table)
        if result:
            logs.append(result)
            break
    if table.get("phase") == "rob":
        logs.extend(await ddz_process_bot_rob(group_id, table))
    return logs


async def ddz_process_bot_rob(group_id: str, table: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    candidate = str(table.get("landlord_candidate"))
    for player in table.get("players", []):
        player_id = str(player.get("id"))
        if player_id == candidate or player_id in set(table.get("rob_passes", set())):
            continue
        if not player.get("bot"):
            continue
        table.setdefault("rob_passes", set()).add(player_id)
        logs.append(f"{player.get('name')} 不抢")
    needed = {str(p.get("id")) for p in table.get("players", []) if str(p.get("id")) != candidate}
    if needed and needed.issubset(set(table.get("rob_passes", set()))):
        logs.append(await ddz_finalize_and_advance(group_id, table, candidate))
    return logs


def ddz_parse_bid(text: str, highest: int) -> Optional[int]:
    stripped = text.strip()
    if stripped == "不叫":
        return 0
    if stripped == "叫地主":
        return min(3, max(1, highest + 1))
    match = re.search(r"(\d+)", stripped)
    if match and stripped.startswith("叫分"):
        return int(match.group(1))
    return None


def ddz_rob_needed_done(table: dict[str, Any]) -> bool:
    candidate = str(table.get("landlord_candidate"))
    needed = {str(p.get("id")) for p in table.get("players", []) if str(p.get("id")) != candidate}
    return bool(needed) and needed.issubset(set(table.get("rob_passes", set())))


def ddz_user_can_act(table: dict[str, Any], user_id: str) -> bool:
    return ddz_current_player(table).get("id") == user_id


async def ddz_process_bot_steps(group_id: str, table: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    while table.get("phase") == "double":
        pending = [p for p in table["players"] if str(p.get("id")) not in set(table.get("double_responses", set()))]
        bot_pending = [p for p in pending if p.get("bot")]
        if not bot_pending:
            break
        for player in bot_pending:
            table.setdefault("double_responses", set()).add(str(player.get("id")))
            if ddz_bot_should_double(player):
                table.setdefault("double_votes", set()).add(str(player.get("id")))
                table["multiplier"] = int(table.get("multiplier", 1)) * 2
                logs.append(f"{player.get('name')} 选择加倍")
            else:
                logs.append(f"{player.get('name')} 不加倍")
        if len(table.get("double_responses", set())) >= len(table["players"]):
            ddz_start_play(table)
            logs.append("加倍阶段结束，地主先出牌。")
            await ddz_send_all_hands(table, group_id)
    while table.get("phase") == "playing" and ddz_current_player(table).get("bot"):
        player = ddz_current_player(table)
        if table.get("last_play") and str(table.get("last_player")) != str(player.get("id")):
            played, line = ddz_bot_play(player, table)
            logs.append(line)
            if not played:
                table["pass_count"] = int(table.get("pass_count", 0)) + 1
                if int(table.get("pass_count", 0)) >= 2:
                    last = ddz_player(table, str(table.get("last_player")))
                    logs.append(f"一轮跟牌结束，{last.get('name') if last else '上家'} 重新领牌。")
                    for idx, candidate in enumerate(table["players"]):
                        if str(candidate.get("id")) == str(table.get("last_player")):
                            table["current"] = idx
                            break
                    table["last_play"] = None
                    table["pass_count"] = 0
                    continue
        else:
            played, line = ddz_bot_play(player, table)
            logs.append(line)
        if not player.get("hand"):
            logs.append(await ddz_finish_game(group_id, table, str(player.get("id"))))
            break
        ddz_next_turn(table)
    return logs


async def ddz_finalize_and_advance(group_id: str, table: dict[str, Any], landlord_id: str) -> str:
    ddz_finalize_landlord(table, landlord_id)
    await ddz_send_all_hands(table, group_id)
    logs = [ddz_table_text(table, "地主已定，请发送 加倍 / 不加倍")]
    logs.extend(await ddz_process_bot_steps(group_id, table))
    if table.get("phase") == "playing":
        logs.append(ddz_table_text(table, "牌局开始，地主先出牌。"))
    return "\n".join(logs)


def ddz_create_human_player(event: GroupMessageEvent) -> dict[str, Any]:
    return {"id": event.get_user_id(), "name": nickname_from_event(event) or f"QQ {event.get_user_id()}", "bot": False, "hand": []}


def ddz_create_bot_player(index: int) -> dict[str, Any]:
    return {"id": f"bot-{index}", "name": f"机关修士{index}", "bot": True, "hand": []}


def ddz_lobby_text(table: dict[str, Any]) -> str:
    lines = ["【斗地主等待房】", f"桌主：{table.get('host_name')}", f"人数：{len(table.get('players', []))}/3"]
    lines.extend(f"{idx}. {player.get('name')}" for idx, player in enumerate(table.get("players", []), start=1))
    lines.append("发送 加入斗地主 入座；满3人后由桌主发送 开始斗地主。")
    return "\n".join(lines)


def is_settle_time(now: datetime) -> bool:
    return (now.hour, now.minute) >= (RANK_SETTLE_HOUR, RANK_SETTLE_MINUTE)


def rank_entries_from_group(group_data: dict[str, Any]) -> list[dict[str, Any]]:
    users = group_data.get("users", {})
    if not isinstance(users, dict):
        return []
    entries = [entry for entry in users.values() if isinstance(entry, dict)]
    entries.sort(key=lambda item: int(item.get("count", 0)), reverse=True)
    return entries


async def group_cultivation_rank_entries(group_id: str) -> list[dict[str, Any]]:
    entries = await store.get_group_user_records(group_id)
    entries = [
        entry
        for entry in entries
        if entry["record"].root is not None
        or entry["record"].total_exp > 0
        or entry["record"].pending_exp > 0
    ]
    entries.sort(
        key=lambda item: (
            item["record"].total_exp + item["record"].pending_exp,
            item["record"].realm_index,
            item["record"].realm_exp,
        ),
        reverse=True,
    )
    return entries


async def group_power_rank_entries(group_id: str) -> list[dict[str, Any]]:
    entries = await store.get_group_user_records(group_id)
    entries = [
        entry
        for entry in entries
        if entry["record"].root is not None
        or entry["record"].total_exp > 0
        or entry["record"].equipped_artifact
        or entry["record"].equipped_method
        or entry["record"].equipped_array
        or entry["record"].equipped_puppet
        or entry["record"].planted_spirit_plant
    ]
    entries.sort(key=lambda item: battle_power(item["record"]), reverse=True)
    return entries


def format_cultivation_rank(entries: list[dict[str, Any]], title: str) -> str:
    lines = [title]
    if not entries:
        lines.append("暂无入榜修士。")
        return "\n".join(lines)
    for index, entry in enumerate(entries[:10], start=1):
        record = entry["record"]
        nickname = short_name(str(entry.get("nickname") or entry.get("user_id")))
        score = record.total_exp + record.pending_exp
        pending = f"，待领 {record.pending_exp}" if record.pending_exp else ""
        realm = record.realm if record.root else "未入门"
        lines.append(f"{index}. {nickname}：{realm}，修为 {score}{pending}")
    return "\n".join(lines)


def format_power_rank(entries: list[dict[str, Any]], title: str) -> str:
    lines = [title]
    if not entries:
        lines.append("暂无入榜修士。")
        return "\n".join(lines)
    for index, entry in enumerate(entries[:10], start=1):
        record = entry["record"]
        nickname = short_name(str(entry.get("nickname") or entry.get("user_id")))
        artifact = record.equipped_artifact
        puppet = record.equipped_puppet
        artifact_name = str(artifact.get("name")) if artifact else "未装备灵器"
        puppet_name = str(puppet.get("name")) if puppet else "未唤醒傀儡"
        lines.append(f"{index}. {nickname}：战力 {battle_power(record)}，{artifact_name}，{puppet_name}")
    return "\n".join(lines)


def format_artifact_list(record) -> str:
    artifacts = available_artifacts(record)
    summary = battle_summary(record)
    lines = ["\u3010\u6211\u7684\u7075\u5668\u3011"]
    lines.append(f"\u5f53\u524d\u69fd\u4f4d\uff1a{summary['artifact_slots']}")
    lines.append("\u69fd\u4f4d\u8bf4\u660e\uff1a\u4e3b\u624b100%\u6218\u529b\uff0c\u526f\u624b65%\u6218\u529b\uff0c\u62a4\u7532/\u62a4\u76fe85%\u6218\u529b\uff1b\u540c\u540d\u7075\u5668\u4e0d\u53ef\u53cc\u6301\uff0c\u62a4\u7532\u69fd\u53ea\u63a5\u53d7\u62a4\u7532/\u62a4\u76fe\u7c7b\u7075\u5668\u3002")
    if not artifacts:
        lines.append("\u6682\u65e0\u53ef\u88c5\u5907\u7075\u5668\uff0c\u8fdb\u884c\u8bf8\u5929\u4e07\u754c\u5782\u9493\u3001\u79d8\u5883\u6216\u5546\u5e97\u6709\u673a\u4f1a\u83b7\u5f97\u3002")
        return "\n".join(lines)
    for index, artifact in enumerate(artifacts, start=1):
        required = artifact.get("required_attribute")
        required_realm = item_required_realm_index(artifact)
        realm_text = REALMS[required_realm] if required_realm < len(REALMS) else "未知"
        realm_ok = record.realm_index >= required_realm
        compatible = "\u53ef\u88c5\u5907" if realm_ok and (not required or required in record.root_attributes) else ("\u4fee\u4e3a\u672a\u8db3" if not realm_ok else "\u7075\u6839\u4e0d\u5951\u5408")
        bonus = artifact_power(artifact, record)
        default_slot = parse_artifact_slot(str(artifact.get("name") or "")) or "\u4e3b\u624b"
        lines.append(
            f"{index}. {reward_display_name(artifact)}\uff0c\u9ed8\u8ba4{default_slot}\uff0c\u9700\u6c42{required or '\u65e0'}\u7075\u6839\uff0c"
            f"\u6700\u4f4e{realm_text}\uff0c{compatible}\uff0c\u57fa\u7840\u6218\u529b+{bonus}"
        )
    lines.append("\u53d1\u9001\u201c\u88c5\u5907\u7075\u5668 \u7f16\u53f7 \u4e3b\u624b/\u526f\u624b/\u62a4\u7532\u201d\u88c5\u5907\u5230\u6307\u5b9a\u69fd\uff1b\u4e0d\u5199\u69fd\u4f4d\u4f1a\u6309\u7075\u5668\u7c7b\u578b\u81ea\u52a8\u5224\u65ad\u3002\u5929\u9636\u7075\u5668\u9700\u81f3\u5c11\u5316\u795e\u671f\u624d\u80fd\u9a7e\u9a6d\uff1b\u975e\u5251\u5929\u9636\u7075\u5668\u5df2\u6309\u5668\u578b\u8865\u8db3\u6218\u529b\u3002")
    lines.append("\u53d1\u9001\u201c\u5378\u4e0b\u7075\u5668 \u526f\u624b\u201d\u53ef\u5378\u4e0b\u6307\u5b9a\u69fd\uff1b\u53d1\u9001\u201c\u5378\u4e0b\u7075\u5668\u201d\u5378\u4e0b\u5168\u90e8\u7075\u5668\u3002")
    return "\n".join(lines)


def format_method_list(record) -> str:
    ensure_combat_profile(record)
    methods = available_methods(record)
    lines = ["\u3010\u6211\u7684\u529f\u6cd5\u3011"]
    lines.append(f"\u5f53\u524d\u529f\u6cd5\uff1a{reward_display_name(record.equipped_method) if record.equipped_method else '\u672a\u53c2\u609f\u529f\u6cd5'}")
    if not methods:
        lines.append("\u6682\u65e0\u529f\u6cd5\uff0c\u8fdb\u884c\u8bf8\u5929\u4e07\u754c\u5782\u9493\u3001\u79d8\u5883\u6216\u5546\u5e97\u6709\u673a\u4f1a\u83b7\u5f97\u3002")
        return "\n".join(lines)
    for index, method in enumerate(methods, start=1):
        required = method.get("required_attribute")
        compatible = "\u53ef\u53c2\u609f" if not required or required in record.root_attributes else "\u7075\u6839\u4e0d\u5951\u5408"
        bonus = method_power(method, record)
        profile = method_profile(method, record)
        tech_count = len(profile.get("techniques", []))
        lines.append(
            f"{index}. {reward_display_name(method)}\uff0c{profile['kind']}\uff0c\u7b2c{profile['layer']}/{profile['max_layer_text']}\u5c42\uff0c"
            f"\u6218\u6280{tech_count}\u5f0f\uff0c\u9700\u6c42{required or '\u65e0'}\u7075\u6839\uff0c{compatible}\uff0c\u6218\u529b+{bonus}"
        )
    lines.append("\u53d1\u9001\u201c\u5b66\u4e60\u529f\u6cd5 \u7f16\u53f7\u201d\u67e5\u770b\u529f\u6cd5\u9875\uff1b\u53d1\u9001\u201c\u53c2\u609f\u529f\u6cd5 \u7f16\u53f7\u201d\u8bbe\u4e3a\u5f53\u524d\u529f\u6cd5\u3002")
    return "\n".join(lines)


def format_array_list(record) -> str:
    arrays = available_arrays(record)
    lines = ["【我的阵盘】"]
    lines.append(f"当前阵盘：{reward_display_name(record.equipped_array) if record.equipped_array else '未布置阵盘'}")
    lines.append(f"当前阵法倍率：{array_multiplier(record):.1f}x")
    if not arrays:
        lines.append("暂无阵盘，进行灵河垂钓、秘境探索或交易有机会获得。")
        return "\n".join(lines)
    for index, array in enumerate(arrays, start=1):
        layer = array_layer(record, array)
        proficiency = array_proficiency_value(record, array)
        cap = array_proficiency_cap(array, layer)
        lines.append(
            f"{index}. {reward_display_name(array)}，第{layer}/{array_layer_cap_text(array)}层，熟练度 {proficiency}/{cap}，倍率上限约{1 + cap / 100:.1f}x"
        )
    lines.append("发送“布置阵盘 编号”即可布置；重复获得同名阵盘会自动推演，仙阶极品后可无限提升。")
    return "\n".join(lines)

def format_puppet_list(record) -> str:
    puppets = available_puppets(record)
    lines = ["【我的傀儡】"]
    lines.append(f"当前傀儡：{reward_display_name(record.equipped_puppet) if record.equipped_puppet else '未唤醒傀儡'}")
    if not puppets:
        lines.append("暂无傀儡，灵河垂钓、炼器或秘境探索有机会获得。")
        return "\n".join(lines)
    for index, puppet in enumerate(puppets, start=1):
        lines.append(f"{index}. {reward_display_name(puppet)}，战力+{puppet_power(puppet, record)}")
    lines.append("发送“装备傀儡 编号”或“唤醒傀儡 编号”即可启用。")
    return "\n".join(lines)


def format_plant_list(record) -> str:
    plants = available_plants(record)
    lines = ["【我的灵植】"]
    lines.append(f"当前灵植：{reward_display_name(record.planted_spirit_plant) if record.planted_spirit_plant else '未栽种灵植'}")
    if not plants:
        lines.append("暂无灵植，灵河垂钓、秘境探索或商店刷新有机会获得。")
        return "\n".join(lines)
    for index, plant in enumerate(plants, start=1):
        lines.append(f"{index}. {reward_display_name(plant)}，栽种后签到修为获得灵植加成")
    lines.append("发送“栽种灵植 编号”即可移入洞府。")
    return "\n".join(lines)


def append_item_lines(lines: list[str], title: str, items: list[dict[str, Any]], usage: str) -> None:
    lines.append(f"【{title}】")
    if not items:
        lines.append("暂无")
    else:
        for index, item in enumerate(items, start=1):
            lines.append(f"{index}. {item_list_display(item)}")
    lines.append(usage)


def item_list_display(item: dict[str, Any]) -> str:
    title = reward_display_name(item)
    if str(item.get("category")) == "\u7075\u6750" and "\u5996\u4e39" in str(item.get("name", "")):
        exp = item.get("cultivation_exp") or item.get("exp")
        realm = item.get("beast_realm") or "\u672a\u77e5"
        element = item.get("element") or item.get("required_attribute") or "\u672a\u5b9a"
        if exp:
            title += f"｜{element}行{realm}，炼化修为+{exp}"
    return title

def format_item_list(record) -> str:
    lines = ["\u3010\u80cc\u5305\u9053\u5177\u3011"]
    summary = battle_summary(record)
    lines.append(f"\u7075\u77f3\u50a8\u5907\uff1a{spirit_stone_text(record.spirit_stones)}\uff1b\u5782\u9493\u6b21\u6570\uff1a{record.fishing_chances}")
    lines.append(f"\u7cbe\u7eaf\u7075\u6db2\uff1a{summary['spirit_liquid']}\uff1b\u74f6\u9888\u6c89\u6dc0\uff1a{summary['bottleneck_days']} \u5929")
    lines.append(f"\u540e\u5929\u7075\u6839\uff1a{acquired_root_summary(record, limit=3)}")
    lines.append("\u7528\u6cd5\uff1a\u70bc\u5316\u7075\u6db2 \u53ef\u5168\u90e8\u8f6c\u4e3a\u4fee\u4e3a\uff1b\u70bc\u5316\u7075\u6db2 100 \u53ef\u6307\u5b9a\u6570\u91cf\u3002")
    if summary.get("is_bottleneck"):
        lines.append(f"\u5f53\u524d\u74f6\u9888\uff1a\u9700 {summary['breakthrough_required']} \u624d\u80fd\u7a81\u7834\u3002")
    if summary.get("cultivation_lock"):
        lines.append(f"\u72b6\u6001\uff1a{summary['cultivation_lock']}")
    sections = [
        ("\u4e39\u836f", available_pills(record), "\u7528\u6cd5\uff1a\u4f7f\u7528\u4e39\u836f \u7f16\u53f7\uff1b\u7a81\u7834\u9053\u5177\u8bf7\u53d1\u9001\u201c\u7a81\u7834\u201d"),
        ("\u7b26\u7b93", available_talismans(record), "\u7528\u6cd5\uff1a\u88c5\u5907\u7b26\u7b93 \u7f16\u53f7 \u653e\u5165\u7b26\u7b93\u680f\uff0c\u666e\u901a\u6597\u6cd5\u751f\u6548\u4e14\u4e0d\u6d88\u8017\uff1b\u4f7f\u7528\u7b26\u7b93 \u7f16\u53f7 \u4e3a\u4e00\u6b21\u6027\u6fc0\u53d1\uff1b\u7ed8\u5236\u7b26\u7b93 \u7f16\u53f7\u53ef\u81ea\u884c\u5236\u7b26"),
        ("\u7075\u77f3", available_spirit_stones(record), "\u7528\u6cd5\uff1a\u70bc\u5316\u7075\u77f3 \u7f16\u53f7\uff1b\u74f6\u9888\u65f6\u4f1a\u8f6c\u4e3a\u7cbe\u7eaf\u7075\u6db2"),
        ("\u7075\u6750", available_materials(record), "\u7528\u6cd5\uff1a\u70bc\u4e39\u6750\u6599\uff1b\u5996\u4e39\u53ef\u53d1\u9001\u201c\u70bc\u5316\u5996\u4e39 \u7f16\u53f7\u201d\u63d0\u5347\u4fee\u4e3a\uff0c\u6216\u201c\u70bc\u5316\u4e39\u7075\u6839 \u7f16\u53f7\u201d\u8865\u5168\u4e94\u884c\uff1b\u51fa\u552e\u7075\u6750 \u7f16\u53f7\u53ef\u6362\u7075\u77f3"),
        ("\u795e\u901a", available_special_ability_items(record), "\u7528\u6cd5\uff1a\u9886\u609f\u795e\u901a \u7f16\u53f7\uff1b\u53ef\u83b7\u5f97星律、初阈、重阈、归极域等能力"),
        ("\u7075\u98df", available_foods(record), "\u7528\u6cd5\uff1a\u4f7f\u7528\u7075\u98df \u7f16\u53f7\uff1b\u74f6\u9888\u65f6\u4f1a\u8f6c\u4e3a\u7cbe\u7eaf\u7075\u6db2"),
        ("\u5947\u7269", available_curios(record), "\u7528\u6cd5\uff1a\u4f7f\u7528\u5947\u7269 \u7f16\u53f7\uff1b\u53ef\u80fd\u5f97\u5230\u4fee\u4e3a\u3001\u5782\u9493\u6216\u5939\u5c42\u9053\u5177"),
        ("\u6742\u7269", available_misc_items(record), "\u7528\u6cd5\uff1a\u9274\u5b9a\u6742\u7269 \u7f16\u53f7\uff1b\u53ef\u80fd\u9274\u51fa\u7269\u54c1\u6216\u6b8b\u4f59\u7075\u6c14"),
    ]
    for title, items, usage in sections:
        lines.append("")
        lines.append(f"\u3010{title}\uff08{len(items)}\uff09\u3011")
        if not items:
            lines.append("\u6682\u65e0")
        else:
            for index, item in enumerate(items, start=1):
                lines.append(f"{index}. {item_list_display(item)}")
        lines.append(usage)
    return "\n".join(lines)

def format_help_text() -> str:
    return "\n".join(
        [
            "【修仙帮助】",
            "新手三步：1. 发送 签到 入门；2. 发送 面板 和 历练 看状态；3. 发送 背包 和 图鉴 了解物品用途。",
            "每天建议：签到 -> 灵河垂钓 -> 背包处理资源 -> 历练查看配置 -> 突破或秘境。",
            "",
            "【修为与突破】",
            "突破：境界圆满后发送 突破，系统会提示需要的道具。",
            "灵液：瓶颈后多余修为会变成精纯灵液，突破后发送 炼化灵液。",
            "妖丹：发送 炼化妖丹 1 或 批量炼化妖丹 全部，可按妖丹参数获得修为。",
            "五行：化神破炼虚需要五行补全，发送 后天灵根 查看丹灵根和器灵根。",
            "",
            "【物品与图鉴】",
            "背包：查看丹药、符箓、灵石、妖丹、灵食、奇物、材料和神通传承。",
            "图鉴：发送 图鉴 查看分类入口；发送 图鉴 物品名 查看用途、故事、来源和配方。",
            "常用分类：境界图鉴 / 突破图鉴 / 品相图鉴 / 灵器图鉴 / 功法图鉴 / 阵盘图鉴 / 神通图鉴 / 唯一装备图鉴。",
            "",
            "【灵器与战力】",
            "灵器按境界绑定：元婴只能装备元婴修士能驾驭的灵器，同阶内也有凡品到天阶。",
            "装备：灵器 / 装备灵器 1 主手 / 装备灵器 2 副手 / 装备灵器 3 护甲 / 卸下灵器。",
            "成长：祭炼本命灵器 1 可设为本命；假仙后可获得仙器；仙帝兵和其他唯一装备可看 唯一装备图鉴。",
            "历练面板：发送 历练 或 历练面板，可查看灵器槽位、功法、阵盘、符箓、神通、战力和常用入口。",
            "",
            "【功法、阵盘、神通】",
            "功法：功法 / 学习功法 1 / 参悟功法 1。功法唯一存在，重复获得会推演升层。",
            "阵盘：阵盘 / 布置阵盘 1 / 阵法推演 1。重复阵盘可升品升阶，熟练度继承。",
            "神通：神通 / 神通图鉴 / 领悟神通 1。斗法中可发送神通名或新别名，如 开启初阈、星律流影、风掣疾行。",
            "",
            "【秘境、任务、路线】",
            "秘境：发送 秘境 抽入口，60 秒内选 1-3；进入后发送 探索 1。首领挑战胜利会给多次探索奖励和妖丹。",
            "救援：秘境反噬后可发送 秘境救援 1000，其他玩家可接取。",
            "任务：每日任务 / 接取任务 / 完成任务 1。路线：修炼路线 / 选择路线 剑修 / 选择身份 天机阁弟子。",
            "御兽秘境：群聊发送 御兽秘境开局 PVE 或 御兽秘境开局 PVP；开始后私聊任务堂购买随从、施放法术、升堂并完成招募。",
            "",
            "【交易、休闲、后台】",
            "商店：商店 / 购买 1 / 出售 丹药 1 / 批量出售 杂物 20。",
            "万宝楼：万宝楼 / 万宝楼挂售 灵器 1 / 万宝楼购买 1 / 万宝楼下架 1。",
            "休闲：天机占卜 / 坐堂 / 斗地主 / 斗地主帮助 / 御兽秘境 / 排行 / 战力榜。",
            "后台：服主可在浏览器访问 /xiuxian-admin，查看玩家档案、物品属性、灵器规则和秘境掉落配置。",
        ]
    )

def format_newbie_tutorial_text(record=None, nickname: str = "") -> str:
    if record is not None and getattr(record, "root", None):
        status = f"当前状态：{nickname or '宿主'}已入门，境界为{record.realm}，进度{record.realm_exp}/{record.progress_required}。"
    else:
        status = "当前状态：尚未入门，先私聊发送 签到，即可抽取灵根并获得第一份修为。"
    return "\n".join(
        [
            "【新手教程】",
            "这是一套慢慢养成的修仙小游戏：每天签到拿修为，修为满了突破境界，物品和装备会让你更容易变强。",
            status,
            "私聊发送 新手教程 可随时重复打开；大多数玩法也可以在群聊使用。",
            "",
            "【先认识三个数】",
            "修为：可以理解为经验值。签到、丹药、灵石、妖丹、灵食、秘境和任务都可能增加修为。",
            "境界：可以理解为等级。修为进度满后会进入瓶颈，发送 突破 查看所需道具。",
            "灵根：开局天赋和属性，首次签到抽取；它影响每日修为收益和面板配色。",
            "",
            "【第一天推荐】",
            "1. 签到：抽取灵根，获得修为和 1 次灵河垂钓。",
            "2. 面板：查看境界、灵根、修为、灵石、装备和当前进度。",
            "3. 灵河垂钓：签到后会提示是否垂钓，回复 是/好/y/十连 即可抽取资源。",
            "4. 背包：查看钓到或获得的丹药、符箓、灵石、妖丹、材料和奇物。",
            "5. 图鉴：不知道物品用途时，发送 图鉴 或 图鉴 物品名。",
            "",
            "【接下来做什么】",
            "历练面板：发送 历练 或 历练面板，查看战力、灵器槽位、功法、阵盘、符箓、神通和常用入口。",
            "突破：境界满了发送 突破；缺道具时看 突破图鉴 或继续垂钓、秘境。",
            "装备：发送 灵器、功法、阵盘、神通 查看可用内容，再按面板编号装备或领悟。",
            "秘境和任务：发送 秘境、每日任务，可获得更多资源；失败反噬时可使用 秘境救援。",
            "",
            "【不确定时】",
            "编号永远以当前面板为准；刚看完 背包/灵器/功法 后再操作最稳。",
            "常用求助：帮助 / 图鉴 / 新手教程。先每天签到和垂钓，后面的系统会自然接上。",
        ]
    )
def reward_catalog_lines(category: str, title: str) -> list[str]:
    tier_order = ["仙帝兵", "仙阶", "\u5929\u9636", "\u5730\u9636", "\u7384\u9636", "\u9ec4\u9636", "\u51e1\u54c1"]
    seen: dict[str, set[str]] = {tier: set() for tier in tier_order}
    for tier, _grade, item_category, name, _desc, _weight in FISHING_REWARDS:
        if item_category == category:
            seen.setdefault(tier, set()).add(name)
    lines = [f"\u3010{title}\u3011", "\u6309\u54c1\u9636\u6536\u5f55\u5df2\u52a0\u5165\u5782\u9493\u3001\u79d8\u5883\u3001\u5546\u5e97\u6216\u70bc\u5236\u4f53\u7cfb\u7684\u7269\u54c1\u3002"]
    for tier in tier_order:
        names = sorted(seen.get(tier, set()))
        if not names:
            continue
        lines.append(f"\u3010{tier}\u3011")
        lines.append("\u3001".join(names))
    return lines


def format_catalog_text(text: str) -> str:
    query = parse_catalog_query(text)
    if query:
        detail = catalog_item_detail_text(query)
        if detail:
            return detail
        return f"【{query}图鉴】\n暂未收录这个条目的图鉴。可尝试发送“丹药图鉴 / 符箓图鉴 / 材料图鉴 / 唯一装备图鉴”查看完整分类。"
    if text in {"\u56fe\u9274", "\u56fe\u5f55"}:
        return "\n".join(
            [
                "【图鉴入口】",
                "图鉴 名称：查询单个物品的类型、品阶、用途、故事、获取方式和制作素材。",
                "境界图鉴：查看所有境界、阶段和瓶颈位置。",
                "突破图鉴：查看每个瓶颈需要的突破道具。",
                "品相图鉴：查看突破道具名与突破品相上限。",
                "丹药图鉴 / 符箓图鉴 / 材料图鉴：查看消耗品、制作材料和使用方式。",
                "灵器图鉴：查看普通灵器、仙器和境界装备规则。",
                "功法图鉴 / 阵盘图鉴：查看可获得功法、阵盘和成长方式。",
                "神通图鉴：查看星律、初阈、重阈、归极域和其他神通传承。",
                "仙源图鉴 / 唯一装备图鉴：查看真仙后仙源、仙帝兵和其他唯一装备。",
            ]
        )
    if text == "\u5883\u754c\u56fe\u9274":
        lines = ["\u3010\u5883\u754c\u56fe\u9274\u3011", "\u9636\u6bb5\uff1a\u521d\u671f / \u4e2d\u671f30% / \u540e\u671f60% / \u5706\u6ee1100% / \u5dc5\u5cf0\uff08\u74f6\u9888\u672a\u7a81\u7834\uff09"]
        for index, realm in enumerate(REALMS, start=1):
            requirement_key = breakthrough_requirement_key_for_realm_index(index - 1)
            suffix = "\uff08\u6709\u74f6\u9888\uff09" if requirement_key in BREAKTHROUGH_REQUIREMENTS else ""
            lines.append(f"{index}. {realm}{suffix}")
        return "\n".join(lines)
    if text in {"品相图鉴", "突破品相图鉴", "道具品相图鉴"}:
        return breakthrough_quality_relation_text()
    if text == "\u7a81\u7834\u56fe\u9274":
        lines = ["\u3010\u7a81\u7834\u56fe\u9274\u3011", "\u4fee\u4e3a\u8fbe\u5230\u5706\u6ee1\u540e\u4f1a\u8fdb\u5165\u74f6\u9888\uff0c\u9700\u6d88\u8017\u5bf9\u5e94\u9053\u5177\u624d\u80fd\u7a81\u7834\u3002", "\u9053\u5177\u540d\u79f0\u51b3\u5b9a\u54c1\u76f8\u4e0a\u9650\uff1b\u54c1\u9636/\u54c1\u8d28\u53ea\u5728\u8be5\u4e0a\u9650\u5185\u63d0\u5347\u7ed3\u679c\uff0c\u57fa\u7840\u9053\u5177\u5373\u4f7f\u62bd\u5230\u5929\u9636\u4e5f\u4e0d\u4f1a\u76f4\u63a5\u89e3\u9501\u6700\u9ad8\u54c1\u76f8\u3002"]
        for realm_index, requirement in BREAKTHROUGH_REQUIREMENTS.items():
            source_index = breakthrough_source_realm_index(realm_index)
            target_index = breakthrough_target_realm_index(realm_index)
            current = REALMS[source_index]
            target = breakthrough_target_realm(realm_index, requirement)
            items = " / ".join(
                f"{item}\uff08{breakthrough_item_quality_cap_text(str(item), target_index)}\uff09"
                for item in requirement.get("items", [])
            )
            lines.append(f"{current} -> {target}\uff1a{items}")
        lines.append("\u5047\u4ed9\u5883\u662f\u6e21\u52ab\u540e\u7684\u4e03\u65e5\u4ed9\u5143\u529b\u8f6c\u5316\u9636\u6bb5\uff0c\u4e0d\u989d\u5916\u6d88\u8017\u7a81\u7834\u9053\u5177\uff1b\u5b8c\u6210\u540e\u8fdb\u5165\u771f\u4ed9\u5883\u3002")
        lines.append("\u74f6\u9888\u65f6\u7b7e\u5230/\u5782\u9493\u83b7\u5f97\u7a81\u7834\u9053\u5177\u7684\u6982\u7387\u4f1a\u5927\u5e45\u63d0\u5347\uff0c\u4f46\u6700\u7ec8\u54c1\u76f8\u9700\u540c\u65f6\u770b\u9053\u5177\u540d\u79f0\u3001\u54c1\u9636\u548c\u54c1\u8d28\u3002")
        return "\n".join(lines)
    if text in SPECIAL_ABILITY_CATALOG_TEXTS:
        return special_ability_catalog_text()
    if text in EMPEROR_CATALOG_TEXTS:
        return emperor_artifact_catalog_text()
    if text == "\u70bc\u5668\u56fe\u9274":
        lines = ["\u3010\u70bc\u5668\u56fe\u9274\u3011", "\u70bc\u5668\u5e08\u53ef\u6309\u914d\u65b9\u6d88\u8017\u7075\u6750\u548c\u7075\u77f3\u70bc\u5236\u7075\u5668\uff1b\u6750\u6599\u54c1\u8d28\u4f1a\u5f71\u54cd\u6210\u54c1\u54c1\u8d28\u3002"]
        for name, recipe in ARTIFACT_REFINING_RECIPES.items():
            mats = "\u3001".join(recipe["materials"][:8])
            if len(recipe["materials"]) > 8:
                mats += f"\u7b49{len(recipe['materials'])}\u4ef6"
            lines.append(f"{name}\uff1a{recipe['tier']}{recipe['grade']}{recipe.get('category', '\u7075\u5668')}\uff5c\u9700{REALMS[int(recipe.get('required_realm', 0))]}\uff5c\u6750\u6599\uff1a{mats}")
        return "\n".join(lines)
    if text in {"仙源图鉴", "仙种图鉴"}:
        lines = ["【仙源图鉴】", "仙源主要来自高危险秘境和真仙后机缘，真仙境后可纳入；部分仙源具有全局唯一性。"]
        for name, info in IMMORTAL_SEED_INFOS.items():
            lines.append(f"{name}\uff1a{info.get('effect', '')}")
        return "\n".join(lines)
    category_map = {
        "\u4e39\u836f\u56fe\u9274": ("\u4e39\u836f", "\u4e39\u836f\u56fe\u9274"),
        "\u7b26\u7b93\u56fe\u9274": ("\u7b26\u7b93", "\u7b26\u7b93\u56fe\u9274"),
        "\u7075\u5668\u56fe\u9274": ("\u7075\u5668", "\u7075\u5668\u56fe\u9274"),
        "\u529f\u6cd5\u56fe\u9274": ("\u529f\u6cd5", "\u529f\u6cd5\u56fe\u9274"),
        "\u9635\u76d8\u56fe\u9274": ("\u9635\u76d8", "\u9635\u76d8\u56fe\u9274"),
        "\u6750\u6599\u56fe\u9274": ("\u7075\u6750", "\u7075\u6750/\u6750\u6599\u56fe\u9274"),
        "\u7075\u6750\u56fe\u9274": ("\u7075\u6750", "\u7075\u6750/\u6750\u6599\u56fe\u9274"),
    }
    category, title = category_map.get(text, ("", "\u56fe\u9274"))
    if category:
        lines = reward_catalog_lines(category, title)
        if category == "\u4e39\u836f":
            lines.append("\u7528\u6cd5\uff1a\u4f7f\u7528\u4e39\u836f \u7f16\u53f7\uff1b\u7a81\u7834\u4e39\u8bf7\u5728\u74f6\u9888\u65f6\u53d1\u9001\u201c\u7a81\u7834\u201d\u3002")
        if category == "\u7b26\u7b93":
            lines.append("\u7528\u6cd5\uff1a\u4f7f\u7528\u7b26\u7b93 \u7f16\u53f7\uff1b\u7ed8\u5236\u7b26\u7b93 \u7f16\u53f7\u53ef\u81ea\u884c\u5236\u7b26\u3002")
        if category == "\u7075\u5668":
            lines.append("\u7528\u6cd5\uff1a\u7075\u5668 / \u88c5\u5907\u7075\u5668 \u7f16\u53f7\uff1b\u7075\u6839\u5951\u5408\u624d\u80fd\u88c5\u5907\u90e8\u5206\u7075\u5668\u3002")
            lines.append(artifact_realm_catalog_summary_text())
        if category == "\u529f\u6cd5":
            lines.append("\u7528\u6cd5\uff1a\u529f\u6cd5 / \u5b66\u4e60\u529f\u6cd5 \u7f16\u53f7 / \u53c2\u609f\u529f\u6cd5 \u7f16\u53f7\uff1b\u529f\u6cd5\u4f1a\u5f71\u54cd\u4fee\u4e3a\u3001\u8840\u91cf\u3001\u795e\u9b42\u611f\u77e5\u548c\u6597\u6cd5\u6218\u6280\u3002")
        return "\n".join(lines)
    return format_catalog_text("\u56fe\u9274")


def item_icon_for_category(category: str) -> str:
    return {
        "灵器": "artifact",
        "功法": "method",
        "阵盘": "array",
        "傀儡": "puppet",
        "灵植": "plant",
        "丹药": "pill",
        "符箓": "talisman",
        "灵石": "stone",
        "灵食": "food",
        "奇物": "curio",
        "灵材": "stone",
        "杂物": "misc",
        "神通": "ability",
    }.get(category, "bag")


def format_mystic_entries(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "当前后台未开启任何秘境入口。"
    lines = ["当前发现以下秘境入口："]
    for index, entry in enumerate(entries, start=1):
        title = mystic_realm_title_from_entry(entry)
        recommended = str(entry.get("recommended") or "未知")
        lines.append(f"{index}、{title}（推荐修为：{recommended}）")
    if any(entry.get("insight") for entry in entries):
        lines.append("天机示警已开启：进入后会标出坏结局选项。")
    lines.append("请在 60 秒内回复入口编号，超时后入口会关闭。")
    return "\n".join(lines)


def format_power_status(record, nickname: str) -> str:
    summary = battle_summary(record)
    lines = [
        f"\u3010{nickname or '\u5bbf\u4e3b'}\u7684\u6218\u529b\u3011",
        f"\u6218\u529b\uff1a{summary['power']}",
        f"\u7075\u529b\u4e0a\u9650\uff1a{summary['mana']}",
        f"\u5883\u754c\uff1a{summary['realm']}",
        f"\u5883\u754c\u54c1\u76f8\uff1a{summary['realm_quality']}",
        f"\u7d2f\u8ba1\u4fee\u4e3a\uff1a{summary['total_exp']}",
        f"\u7cbe\u7eaf\u7075\u6db2\uff1a{summary['spirit_liquid']}",
        f"\u74f6\u9888\u6c89\u6dc0\uff1a{summary['bottleneck_days']} \u5929",
        f"\u7075\u5668\u69fd\uff1a{summary['artifact_slots']}",
        f"\u7b26\u7b93\u680f\uff1a{summary['talisman']}\uff08\u6218\u529b+{summary['talisman_power']}\uff09",
        f"\u529f\u6cd5\uff1a{summary['method']}",
        f"\u9635\u76d8\uff1a{summary['array']}\uff08{summary['array_multiplier']:.1f}x\uff09",
        f"\u5080\u5121\uff1a{summary['puppet']}\uff08\u6218\u529b+{summary['puppet_power']}\uff09",
        f"\u7075\u690d\uff1a{summary['plant']}",
        f"\u7075\u77f3\u50a8\u5907\uff1a{summary['spirit_stones_text']}",
        f"\u4fee\u70bc\u8def\u7ebf\uff1a{summary['route']}",
        f"\u8eab\u4efd\u4ee4\u724c\uff1a{summary['identity']}",
        f"\u795e\u901a\uff1a{len(summary['special_abilities'])} \u9879\uff1b\u4f20\u627f\u6750\u6599\uff1a{summary['special_ability_materials']} \u4efd\uff1b\u6218\u529b+{summary['special_ability_power']}",
        f"\u5929\u673a\u79d8\u5883\uff1a{summary['tianji_status']}\uff1b\u53cc\u4fee\u6b21\u6570\uff1a{summary['hehuan_remaining']}",
        f"\u79d8\u5883\uff1a{summary['mystic_realm']}",
        f"\u88c5\u5907\u52a0\u6210\uff1a{summary['equipment_power']}",
    ]
    if summary.get("is_bottleneck"):
        lines.append(f"\u5f53\u524d\u74f6\u9888\uff1a\u9700 {summary['breakthrough_required']} \u624d\u80fd\u7a81\u7834")
    if summary.get("cultivation_lock"):
        lines.append(f"\u7981\u4fee\u72b6\u6001\uff1a{summary['cultivation_lock']}")
    return "\n".join(lines)

def format_adventure_panel(record) -> str:
    summary = battle_summary(record)
    return "\n".join(
        [
            "\u3010\u5386\u7ec3\u3011",
            f"\u5f53\u524d\u6218\u529b\uff1a{summary['power']}\uff1b{summary['mana_label']}\u4e0a\u9650\uff1a{summary['mana']}",
            f"\u5f53\u524d\u7075\u5668\u69fd\uff1a{summary['artifact_slots']}",
            f"\u672c\u547d\u7075\u5668\uff1a{summary['life_artifact']}",
            f"仙源：{summary['immortal_seed']}（战力+{summary['immortal_seed_power']}）",
            f"\u5f53\u524d\u7b26\u7b93\u680f\uff1a{summary['talisman']}\uff08\u6218\u529b+{summary['talisman_power']}\uff09",
            f"\u5f53\u524d\u529f\u6cd5\uff1a{summary['method']}",
            f"\u5f53\u524d\u9635\u76d8\uff1a{summary['array']}\uff08{summary['array_multiplier']:.1f}x\uff09",
            f"\u5f53\u524d\u5080\u5121\uff1a{summary['puppet']}",
            f"\u5f53\u524d\u7075\u690d\uff1a{summary['plant']}",
            f"\u7075\u77f3\u50a8\u5907\uff1a{summary['spirit_stones_text']}",
            f"\u7cbe\u7eaf\u7075\u6db2\uff1a{summary['spirit_liquid']}\uff1b\u74f6\u9888\u6c89\u6dc0\uff1a{summary['bottleneck_days']} \u5929",
            f"\u4fee\u70bc\u8def\u7ebf\uff1a{summary['route']}",
            f"\u8eab\u4efd\u4ee4\u724c\uff1a{summary['identity']}\uff08\u5929\u673a\u79d8\u5883\uff1a{summary['tianji_status']}\uff0c\u53cc\u4fee\uff1a{summary['hehuan_remaining']}\uff09",
            f"\u795e\u901a\uff1a{len(summary['special_abilities'])} \u9879\uff1b\u4f20\u627f\u6750\u6599\uff1a{summary['special_ability_materials']} \u4efd",
            "\u8def\u7ebf / \u9009\u62e9\u8def\u7ebf \u5251\u4fee / \u9009\u62e9\u8def\u7ebf \u70bc\u5668\u5e08 / \u9009\u62e9\u8eab\u4efd \u5929\u673a\u9601\u5f1f\u5b50",
            "\u6bcf\u65e5\u4efb\u52a1 / \u5b8c\u6210\u4efb\u52a1 1 / \u5546\u5e97 / \u8d2d\u4e70 1 / \u51fa\u552e \u4e39\u836f 1",
            "\u70bc\u4e39 / \u70bc\u5668 / \u70bc\u5668\u56fe\u9274 / \u9635\u6cd5\u63a8\u6f14 1 / \u796d\u70bc\u672c\u547d\u7075\u5668 1",
            "\u7075\u5668 / \u529f\u6cd5 / \u9635\u76d8 / \u795e\u901a / \u4ed9\u79cd / \u552f\u4e00\u88c5\u5907\u56fe\u9274\uff1a\u67e5\u770b\u53ef\u7528\u914d\u7f6e",
            "\u5080\u5121 / \u7075\u690d / \u80cc\u5305\uff1a\u67e5\u770b\u5386\u7ec3\u8d44\u6e90",
            "\u88c5\u5907\u7075\u5668 1 \u4e3b\u624b / \u88c5\u5907\u7075\u5668 2 \u526f\u624b / \u88c5\u5907\u7075\u5668 3 \u62a4\u7532 / \u88c5\u5907\u7b26\u7b93 1",
            "\u53c2\u609f\u529f\u6cd5 1 / \u5e03\u7f6e\u9635\u76d8 1 / \u88c5\u5907\u4ed9\u79cd 1 / \u5378\u4e0b\u7075\u5668 \u526f\u624b",
            "\u4ea4\u6613\u5217\u8868 / \u4ea4\u6613 @\u5bf9\u65b9 \u7075\u5668 1 100 / \u6279\u91cf\u51fa\u552e \u6742\u7269 20 / \u79d8\u5883\u6551\u63f4 1000",
            "\u79d8\u5883\uff1a\u67e5\u770b60\u79d2\u9650\u65f6\u79d8\u5883\u5165\u53e3\uff1b\u9ad8\u5371\u9669\u5730\u6709\u66f4\u5c11\u751f\u8def\u4e14\u65e0\u9996\u9886\u6311\u6218\uff1b\u666e\u901a\u79d8\u5883\u9996\u9886\u80dc\u5229\u53ef\u6298\u7b9710\u6b21\u63a2\u7d22\u5956\u52b1",
            "\u7a81\u7834\uff1a\u5883\u754c\u5706\u6ee1\u540e\u4f7f\u7528\u7a81\u7834\u9053\u5177\uff1b\u6563\u529f\uff1a\u56de\u9000\u91cd\u4fee\u6539\u5584\u54c1\u76f8",
            "\u6218\u529b / pk @\u5bf9\u65b9 / \u7533\u8bf7\u666e\u901a\u6597\u6cd5 / \u6218\u529b\u699c\uff1a\u67e5\u770b\u6218\u529b\u4e0e\u5207\u78cb",
        ]
    )

def format_shop_panel(record, date_text: str) -> str:
    items = shop_items_for_date(date_text, record)
    lines = ["【每日商店】", f"今日灵石：{spirit_stone_text(record.spirit_stones)}"]
    for index, item in enumerate(items, start=1):
        price = int(item.get("price", 0))
        required = item.get("required_attribute")
        extra = f"，需{required}灵根" if required else ""
        lines.append(f"{index}. {reward_display_name(item)}：{spirit_stone_text(price)}{extra}")
    lines.append("发送“购买 编号”购买；发送“出售 类别 编号”出售背包物品。")
    return "\n".join(lines)


def format_duel_result(attacker_name: str, defender_name: str, result) -> str:
    winner = attacker_name if result.attacker_win else defender_name
    chance = int(result.chance * 100)
    return "\n".join(
        [
            "【历练切磋】",
            f"{attacker_name} 战力 {result.attacker_power}",
            f"{defender_name} 战力 {result.defender_power}",
            f"胜者：{winner}",
            f"推演胜率：{chance}%",
            result.detail,
            "切磋不消耗修为，也不会损毁灵器。",
        ]
    )


def format_rank_message(
    group_id: str,
    date_text: str,
    entries: list[dict[str, Any]],
    rewards: dict[str, RankReward],
    cultivation_entries: list[dict[str, Any]],
    power_entries: list[dict[str, Any]],
) -> str:
    lines = [
        f"【每日话痨榜】{date_text}",
        f"群 {group_id} 今日修炼热度结算：",
    ]
    for index, entry in enumerate(entries[:10], start=1):
        user_id = str(entry.get("user_id", ""))
        nickname = str(entry.get("nickname") or user_id)
        count = int(entry.get("count", 0))
        reward = rewards.get(user_id)
        reward_text = reward.label if reward else "无奖励"
        lines.append(f"{index}. {nickname}：{count} 句，{reward_text}")
    lines.append("")
    lines.append("奖励已发放；未觉醒灵根者的修为会暂存到首次签到后领取。")
    lines.append("")
    lines.append(format_cultivation_rank(cultivation_entries, "【群修为榜】"))
    lines.append("")
    lines.append(format_power_rank(power_entries, "【群战力榜】"))
    return "\n".join(lines)

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
            await bot.send_group_msg(group_id=int(group_id), message=panel_segment("每日话痨榜", message, icon="rank"))
            await store.mark_rank_group_settled(group_id, date_text)
        except Exception:
            logger.exception(f"发送群 {group_id} 每日话痨榜失败")

async def rank_scheduler() -> None:
    while True:
        try:
            await settle_daily_chat_ranks()
        except Exception:
            logger.exception("每日话痨榜结算任务失败")
        await asyncio.sleep(60)


@driver.on_startup
async def start_rank_scheduler() -> None:
    global admin_http_server, rank_scheduler_task
    if config.xiuxian_signin_admin_enabled:
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
    rank_scheduler_task = asyncio.create_task(rank_scheduler())


@driver.on_shutdown
async def stop_admin_http_server() -> None:
    global admin_http_server
    if admin_http_server is not None:
        admin_http_server.stop()
        admin_http_server = None


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
        icon="mystic",
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
            icon="mystic",
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
        message=panel_segment(title, content, icon="mystic"),
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


async def is_divination_message(event: MessageEvent) -> bool:
    return is_divination_command_text(normalized_plain_text(event))


async def is_tianji_sit_message(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) and normalized_plain_text(event) in TIANJI_SIT_TEXTS


async def is_divination_reply(event: MessageEvent) -> bool:
    key = divination_pending_key(event)
    pending = pending_divinations.get(key)
    if pending is None:
        return False
    if float(pending.get("expires_at", 0)) < time.monotonic():
        pending_divinations.pop(key, None)
        return False
    text = normalized_plain_text(event)
    if not text or is_managed_command_text(text):
        return False
    return True


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


async def is_mystic_entry_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in MYSTIC_ENTRY_TEXTS


async def is_mystic_entry_reply(event: MessageEvent) -> bool:
    pending = pending_mystic_entries.get(mystic_pending_key(event))
    if pending is None:
        return False
    return parse_short_index_text(normalized_plain_text(event)) is not None


async def is_mystic_explore_message(event: MessageEvent) -> bool:
    return is_mystic_explore_command_text(normalized_plain_text(event))


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


async def is_doudizhu_message(event: MessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    text = normalized_plain_text(event)
    return is_doudizhu_entry_text(text) or (doudizhu_group_key(event) in doudizhu_tables and is_doudizhu_command_text(text))


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

beast_realm_group_cmd = on_message(rule=Rule(is_beast_realm_group_message), priority=10, block=True)
beast_realm_private_cmd = on_message(rule=Rule(is_beast_realm_private_message), priority=7, block=True)
help_cmd = on_message(rule=Rule(is_help_message), priority=10, block=True)
newbie_tutorial_cmd = on_message(rule=Rule(is_newbie_tutorial_message), priority=10, block=True)
catalog_cmd = on_message(rule=Rule(is_catalog_message), priority=10, block=True)
signin = on_message(rule=Rule(is_signin_message), priority=10, block=True)
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
divination_cmd = on_message(rule=Rule(is_divination_message), priority=10, block=True)
tianji_sit_cmd = on_message(rule=Rule(is_tianji_sit_message), priority=10, block=True)
dual_cultivation_cmd = on_message(rule=Rule(is_dual_cultivation_message), priority=10, block=True)
equip_puppet_cmd = on_message(rule=Rule(is_equip_puppet_message), priority=10, block=True)
plant_cmd = on_message(rule=Rule(is_plant_message), priority=10, block=True)
item_use_cmd = on_message(rule=Rule(is_item_use_message), priority=10, block=True)
acquired_root_cmd = on_message(rule=Rule(is_acquired_root_message), priority=10, block=True)
spirit_liquid_use_cmd = on_message(rule=Rule(is_spirit_liquid_use_message), priority=10, block=True)
mystic_entry_reply = on_message(rule=Rule(is_mystic_entry_reply), priority=8, block=True)
divination_reply = on_message(rule=Rule(is_divination_reply), priority=8, block=True)
mystic_entry = on_message(rule=Rule(is_mystic_entry_message), priority=10, block=True)
mystic_explore = on_message(rule=Rule(is_mystic_explore_message), priority=10, block=True)
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
doudizhu_cmd = on_message(rule=Rule(is_doudizhu_message), priority=10, block=True)
chat_rank_counter = on_message(rule=Rule(is_group_chat_for_rank), priority=99, block=False)




@beast_realm_group_cmd.handle()
async def handle_beast_realm_group(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    text_value = normalized_plain_text(event)
    group_key = beast_realm_group_key_from_event(event)

    if text_value == "御兽秘境帮助" or (text_value == "御兽秘境" and group_key not in beast_realm_tables):
        await finish_panel(matcher, "御兽秘境", beast_realm_game.help_text(), record, icon="mystic")
    if text_value in {"御兽秘境图鉴", "御兽卡牌", "御兽卡牌图鉴"}:
        await finish_panel(matcher, "御兽秘境图鉴", beast_realm_game.catalog_text(), record, icon="mystic")

    table = beast_realm_tables.get(group_key)
    if table and table.get("phase") == "lobby" and float(table.get("expires_at", 0)) < time.monotonic():
        cleanup_beast_realm_table(group_key)
        table = None

    if beast_realm_game.is_beast_realm_private_entry_command(text_value):
        await finish_panel(matcher, "御兽秘境1V2", "1V2单人PVE仅支持私聊开启，请私聊发送 御兽秘境1V2。", record, icon="warning")

    if text_value.startswith("御兽秘境开局") or text_value.startswith("开启御兽秘境") or text_value in {"御兽秘境PVE", "御兽秘境PVP"}:
        if table:
            await finish_panel(matcher, "御兽秘境", beast_realm_game.status_text(table), record, icon="mystic")
        mode = beast_realm_game.parse_mode(text_value)
        if mode == "solo_pve":
            await finish_panel(matcher, "御兽秘境1V2", "1V2单人PVE仅支持私聊开启，请私聊发送 御兽秘境1V2。", record, icon="warning")
        table = beast_realm_game.create_table(group_key, user_id, nickname_from_event(event) or f"QQ {user_id}", mode)
        beast_realm_tables[group_key] = table
        route_beast_realm_players(table)
        host_player = beast_realm_game.table_player(table, user_id)
        sent = await send_beast_realm_leader_panel(table, host_player) if host_player else False
        hint = "\n\n峰主候选已发送到私聊，请发送 选择峰主 1/2/3。" if sent else "\n\n峰主候选私聊发送失败，请检查好友或临时会话权限；也可私聊发送 峰主 查看。"
        await finish_panel(matcher, "御兽秘境开局", beast_realm_game.lobby_text(table) + hint, record, icon="mystic")

    if not table:
        await finish_panel(matcher, "御兽秘境", beast_realm_game.help_text(), record, icon="mystic")

    if text_value in {"御兽秘境", "御兽秘境状态"}:
        await finish_panel(matcher, "御兽秘境状态", beast_realm_game.status_text(table), record, icon="mystic")

    if text_value == "加入御兽秘境":
        ok, message = beast_realm_game.add_player(table, user_id, nickname_from_event(event) or f"QQ {user_id}")
        if ok:
            route_beast_realm_players(table)
            player = beast_realm_game.table_player(table, user_id)
            sent = await send_beast_realm_leader_panel(table, player) if player else False
            message += "\n\n峰主候选已发送到私聊，请发送 选择峰主 1/2/3。" if sent else "\n\n峰主候选私聊发送失败，请检查好友或临时会话权限；也可私聊发送 峰主 查看。"
        await finish_panel(matcher, "加入御兽秘境" if ok else "操作失败", message, record, icon="mystic" if ok else "warning")

    if text_value == "退出御兽秘境":
        ok, message = beast_realm_game.remove_player(table, user_id)
        if beast_realm_private_routes.get(user_id) == group_key:
            beast_realm_private_routes.pop(user_id, None)
        if ok and not beast_realm_game.active_human_players(table):
            cleanup_beast_realm_table(group_key)
        await finish_panel(matcher, "退出御兽秘境" if ok else "操作失败", message, record, icon="mystic" if ok else "warning")

    if text_value == "结束御兽秘境":
        player = beast_realm_game.table_player(table, user_id)
        if str(table.get("host_id")) != user_id and not player:
            await finish_panel(matcher, "操作失败", "只有峰主或本局修士可以结束御兽秘境。", record, icon="warning")
        cleanup_beast_realm_table(group_key)
        await finish_panel(matcher, "御兽秘境", "本群御兽秘境已结束。", record, icon="mystic")

    if text_value == "开始御兽秘境":
        if str(table.get("host_id")) != user_id:
            await finish_panel(matcher, "操作失败", "只有峰主可以开始御兽秘境。", record, icon="warning")
        ok, message = beast_realm_game.start_table(table)
        if not ok:
            await finish_panel(matcher, "操作失败", message, record, icon="warning")
        await send_beast_realm_recruit_panels(table)
        await finish_panel(matcher, "御兽秘境", message, record, icon="mystic")

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

    await finish_panel(matcher, "御兽秘境状态", beast_realm_game.status_text(table), record, icon="mystic")


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
        await finish_panel(matcher, "御兽秘境1V2", beast_realm_game.leader_choice_text(player), record, icon="mystic", footer="选择峰主后发送“开始御兽秘境”，全流程在私聊完成。")
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
        await matcher.send(panel_segment("御兽秘境1V2", message, record, icon="mystic"))
        await send_beast_realm_recruit_panels(table)
        return

    title, content = beast_realm_game.private_action(table, player, text_value)
    await matcher.send(panel_segment(title, content, record, icon="mystic" if title != "操作失败" else "warning"))
    if table.get("phase") == "lobby":
        return

    ready_command = text_value in {"完成招募", "结束招募", "准备"}
    if ready_command and not was_ready and beast_realm_game.all_humans_ready(table):
        report = beast_realm_game.resolve_round(table)
        if str(table.get("mode")) == "solo_pve":
            await matcher.send(panel_segment("御兽秘境战报", report, record, icon="mystic"))
        else:
            await send_beast_realm_group_report(table, "御兽秘境战报", report)
        if table.get("phase") == "ended":
            cleanup_beast_realm_table(group_key)
            return
        await send_beast_realm_recruit_panels(table)
@help_cmd.handle()
async def handle_help(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    await finish_panel(matcher, "\u4fee\u4ed9\u5e2e\u52a9", format_help_text(), icon="scroll")

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
        await finish_panel(matcher, "\u795e\u901a\u56fe\u9274", special_ability_catalog_text(record), record, icon="ability")
    await finish_panel(matcher, "\u4fee\u4ed9\u56fe\u9274", format_catalog_text(text), record, icon="catalog")


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
    await finish_panel(matcher, "\u7a81\u7834\u72b6\u6001", breakthrough_status(record), record, icon="breakthrough")


@puppet_list.handle()
async def handle_puppet_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "我的傀儡", format_puppet_list(record), record, icon="puppet")


@plant_list.handle()
async def handle_plant_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "我的灵植", format_plant_list(record), record, icon="plant")


@item_list.handle()
async def handle_item_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "背包道具", format_item_list(record), record, icon="bag")


@acquired_root_cmd.handle()
async def handle_acquired_root(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    parsed = parse_acquired_root_command(normalized_plain_text(event))
    if parsed is None or parsed[0] == "status":
        await finish_panel(matcher, "后天灵根", acquired_root_text(record), record, icon="realm")
    kind, index = parsed
    if index is None:
        await finish_panel(matcher, "后天灵根", acquired_root_text(record), record, icon="realm")
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
        await finish_panel(matcher, "神通图鉴", special_ability_catalog_text(record), record, icon="ability")
    await store.save_user(record)
    await finish_panel(matcher, "我的神通", special_ability_list_text(record), record, icon="ability")


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
        await finish_panel(matcher, "修炼路线", route_status_text(record), record, icon="token")
    route_name = parse_prefixed_name(text, ROUTE_SELECT_PREFIXES)
    if route_name is not None:
        if not route_name:
            await finish_panel(matcher, "修炼路线", route_status_text(record), record, icon="token")
        success, message = choose_cultivation_route(record, route_name)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "修炼路线" if success else "选择失败", message, record, icon="token" if success else "warning")
    identity_name = parse_prefixed_name(text, IDENTITY_SELECT_PREFIXES)
    if identity_name is not None:
        if not identity_name:
            await finish_panel(matcher, "身份令牌", route_status_text(record), record, icon="token")
        success, message = choose_faction_identity(record, identity_name)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "身份令牌" if success else "选择失败", message, record, icon="token" if success else "warning")
    if text in EVIL_SELECT_TEXTS or text in EVIL_QUIT_TEXTS:
        success, message = choose_evil_cultivation(record, text in EVIL_SELECT_TEXTS)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "邪修路线", message, record, icon="token")
    await finish_panel(matcher, "修炼路线", route_status_text(record), record, icon="token")


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
        await finish_panel(matcher, "\u6bcf\u65e5\u5546\u5e97", format_shop_panel(record, local_today().isoformat()), record, icon="shop")
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
    batch_sale = parse_batch_sell(text)
    if batch_sale is not None:
        category, limit = batch_sale
        success, message = batch_sell_rewards(record, category, limit)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "\u6279\u91cf\u51fa\u552e" if success else "\u51fa\u552e\u5931\u8d25", message, record, icon=item_icon_for_category(category) if success else "warning")
    await finish_panel(matcher, "\u6bcf\u65e5\u5546\u5e97", format_shop_panel(record, local_today().isoformat()), record, icon="shop")


@alchemy_cmd.handle()
async def handle_alchemy(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    pill_name = parse_alchemy_name(text)
    if text in ALCHEMY_TEXTS or pill_name == "":
        await finish_panel(matcher, "炼丹", alchemy_text(record), record, icon="alchemy")
    if pill_name is None:
        await finish_panel(matcher, "炼丹", alchemy_text(record), record, icon="alchemy")
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
        await finish_panel(matcher, "\u70bc\u5668", refining_text(record), record, icon="alchemy")
    success, message = refine_artifact_by_recipe(record, name)
    await store.save_user(record)
    await finish_panel(matcher, "\u70bc\u5668\u6210\u529f" if success else "\u70bc\u5668\u5931\u8d25", message, record, icon="alchemy" if success else "warning")


@array_deduction_cmd.handle()
async def handle_array_deduction(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    index = parse_array_deduction_index(normalized_plain_text(event))
    if not index:
        await finish_panel(matcher, "\u9635\u6cd5\u63a8\u6f14", array_deduction_text(record), record, icon="array")
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
        await finish_panel(matcher, "仙源", immortal_seed_text(record), record, icon="ability")
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
        record.spirit_stones -= price
        item, append_msg = await normalize_unique_reward_for_user(record, item, event)
        record.rewards = list(record.rewards or []) + [item]
        await store.save_user(record)

        def seller_gain(seller, gain=price):
            seller.spirit_stones += gain

        await store.apply_to_user(seller_id, seller_gain)
        await finish_panel(matcher, "\u4ea4\u6613\u5b8c\u6210", f"\u83b7\u5f97 {reward_display_name(item)}\uff0c\u652f\u4ed8 {spirit_stone_text(price)}\u3002{append_msg}", record, icon="shop")
    if cancel_id is not None:
        offer = await store.cancel_trade_offer(group_id, str(cancel_id), user_id)
        if not offer:
            await finish_panel(matcher, "\u64a4\u9500\u5931\u8d25", "\u6ca1\u6709\u627e\u5230\u53ef\u64a4\u9500\u7684\u672c\u4eba\u6302\u5355\u3002", record, icon="warning")
        item = dict(offer.get("item") or {})
        record.rewards = list(record.rewards or []) + [item]
        await store.save_user(record)
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
        await finish_panel(matcher, "万宝楼", "\n".join(lines), record, icon="shop")
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
        record.spirit_stones -= price
        item, append_msg = await normalize_unique_reward_for_user(record, item, event)
        record.rewards = list(record.rewards or []) + [item]
        await store.save_user(record)

        def seller_gain(seller, gain=price):
            seller.spirit_stones += gain

        await store.apply_to_user(seller_id, seller_gain)
        await finish_panel(matcher, "万宝楼成交", f"购得 {reward_display_name(item)}，支付 {spirit_stone_text(price)}。{append_msg}", record, icon="shop")
    if cancel_id is not None:
        offer = await store.cancel_trade_offer(group_id, str(cancel_id), user_id)
        if not offer or not offer.get("market"):
            await finish_panel(matcher, "下架失败", "没有找到可下架的本人寄售物。", record, icon="warning")
        item = dict(offer.get("item") or {})
        record.rewards = list(record.rewards or []) + [item]
        await store.save_user(record)
        await finish_panel(matcher, "万宝楼下架", f"已下架 {reward_display_name(item)}。", record, icon="shop")
    if offer_data is None:
        await finish_panel(matcher, "万宝楼", "格式：万宝楼挂售 类别 编号，例如：万宝楼挂售 灵器 1。", record, icon="shop")
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
            realm = req.get("realm", {})
            lines.append(f"{req.get('id')}\uff1a{req.get('requester_name')} \u6c42\u63f4 {realm.get('title') or realm.get('type')}\uff0c\u916c\u52b3 {spirit_stone_text(int(req.get('reward_stones', 0)))}")
        lines.append("\u53d1\u8d77\uff1a\u79d8\u5883\u6551\u63f4 1000\uff1b\u63a5\u53d6\uff1a\u6551\u63f4 \u59d4\u6258\u7f16\u53f7\u3002")
        await finish_panel(matcher, "\u79d8\u5883\u6551\u63f4", "\n".join(lines), record, icon="mystic")
    amount = parse_rescue_request(text)
    if amount is not None:
        if amount <= 0:
            await finish_panel(matcher, "\u79d8\u5883\u6551\u63f4", "\u8bf7\u5199\u660e\u6551\u63f4\u916c\u52b3\uff0c\u4f8b\u5982\uff1a\u79d8\u5883\u6551\u63f4 1000\u3002", record, icon="mystic")
        if record.spirit_stones < amount:
            await finish_panel(matcher, "\u6551\u63f4\u5931\u8d25", f"\u7075\u77f3\u4e0d\u8db3\uff0c\u5f53\u524d\u4ec5\u6709 {spirit_stone_text(record.spirit_stones)}\u3002", record, icon="warning")
        if not record.last_failed_mystic_realm:
            await finish_panel(matcher, "\u6551\u63f4\u5931\u8d25", "\u5f53\u524d\u6ca1\u6709\u53ef\u59d4\u6258\u6551\u63f4\u7684\u5931\u8d25\u79d8\u5883\u8bb0\u5f55\u3002", record, icon="warning")
        record.spirit_stones -= amount
        request = await store.create_rescue_request(group_id, event.get_user_id(), nickname_from_event(event), record.last_failed_mystic_realm, amount)
        await store.save_user(record)
        await finish_panel(matcher, "\u79d8\u5883\u6551\u63f4", f"\u5df2\u53d1\u5e03\u6551\u63f4\u59d4\u6258 {request.get('id')}\uff0c\u916c\u52b3 {spirit_stone_text(amount)}\u3002\u5176\u4ed6\u4fee\u58eb\u53ef\u53d1\u9001\uff1a\u6551\u63f4 {request.get('id')}\u3002", record, icon="mystic")
    take_id = parse_rescue_take(text)
    if take_id is not None:
        if not take_id:
            await finish_panel(matcher, "\u79d8\u5883\u6551\u63f4", "\u8bf7\u53d1\u9001\uff1a\u6551\u63f4 \u59d4\u6258\u7f16\u53f7\u3002", record, icon="mystic")
        request = await store.take_rescue_request(group_id, take_id, event.get_user_id())
        if not request:
            await finish_panel(matcher, "\u63a5\u53d6\u5931\u8d25", "\u6ca1\u6709\u627e\u5230\u8fd9\u6761\u53ef\u63a5\u53d6\u6551\u63f4\uff0c\u6216\u4e0d\u80fd\u6551\u63f4\u81ea\u5df1\u3002", record, icon="warning")
        realm = dict(request.get("realm") or {})
        realm["rescued_from"] = request.get("requester_id")
        record.mystic_realm = realm
        record.spirit_stones += int(request.get("reward_stones", 0))
        await store.save_user(record)
        await finish_panel(matcher, "\u79d8\u5883\u6551\u63f4", f"\u5df2\u63a5\u53d6 {request.get('requester_name')} \u7684\u6551\u63f4\u59d4\u6258\uff0c\u83b7\u5f97\u916c\u52b3 {spirit_stone_text(int(request.get('reward_stones', 0)))}\u3002\n{mystic_realm_options_text(record)}", record, icon="mystic")


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
    success, message, entries = draw_tianji_mystic_entrances(record, local_today())
    if not success:
        await finish_panel(matcher, "天机秘境", message, record, icon="mystic")
    key = mystic_pending_key(event)
    expires_at = time.monotonic() + MYSTIC_ENTRY_TTL
    pending_mystic_entries[key] = {"expires_at": expires_at, "entries": entries}
    asyncio.create_task(
        send_mystic_timeout_notice(
            key,
            expires_at,
            event.get_user_id(),
            str(event.group_id) if isinstance(event, GroupMessageEvent) else None,
        )
    )
    await finish_panel(
        matcher,
        "天机秘境",
        f"{message}\n{format_mystic_entries(entries)}",
        record,
        subtitle="60秒内回复编号",
        icon="mystic",
    )


@tianji_sit_cmd.handle()
async def handle_tianji_sit(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    user_id = event.get_user_id()
    record = await store.get_user(user_id)
    if not is_tianji_hall_identity(record):
        await finish_panel(matcher, "天机阁坐堂", "只有天机阁弟子、长老或太上长老可以坐堂分润占卜收益。", record, icon="warning")
    hall = await store.get_tianji_hall(str(event.group_id), local_today().isoformat())
    if not hall:
        await finish_panel(
            matcher,
            "天机阁坐堂",
            "今日尚无首位天机阁门人签到开堂。\n请先由任意天机阁门人完成今日签到，再发送“坐堂”加入分润。",
            record,
            icon="warning",
        )
    joined, updated_hall = await store.join_tianji_sitter(
        str(event.group_id),
        user_id,
        local_today().isoformat(),
        nickname_from_event(event) or f"QQ {user_id}",
    )
    updated_hall = updated_hall or hall
    title = "坐堂成功" if joined else "已在坐堂"
    message = (
        f"当前坐堂天机阁门人：{tianji_sitter_names(updated_hall, limit=8)}\n"
        f"人数：{len(tianji_sitters(updated_hall))}人。本群今日占卜收益将按次平分，不可整除时由先坐堂者优先得一枚余数灵石。\n"
        f"今日已占：{int(updated_hall.get('divination_count', 0))}卦，累计润资：{spirit_stone_text(int(updated_hall.get('income', 0)))}。"
    )
    await finish_panel(matcher, title, message, record, icon="divination")

@divination_cmd.handle()
async def handle_divination_cmd(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    hall = await require_tianji_hall(matcher, event, record)
    question = parse_divination_question(normalized_plain_text(event))
    if question:
        income_text = await settle_divination_income(event, record)
        await finish_panel(
            matcher,
            "\u5929\u673a\u5360\u535c",
            tianji_divination_text(record, question, local_today()) + income_text,
            record,
            icon="divination",
        )
    key = divination_pending_key(event)
    expires_at = time.monotonic() + DIVINATION_PENDING_TTL
    pending_divinations[key] = {
        "expires_at": expires_at,
        "group_id": str(event.group_id) if isinstance(event, GroupMessageEvent) else "",
        "sitter_id": str(hall.get("sitter_id") or ""),
    }
    asyncio.create_task(
        send_divination_timeout_notice(
            key,
            expires_at,
            event.get_user_id(),
            str(event.group_id) if isinstance(event, GroupMessageEvent) else None,
        )
    )
    sitter_name = tianji_sitter_names(hall)
    await finish_panel(
        matcher,
        "\u5929\u673a\u5360\u535c",
        f"\u4eca\u65e5\u5750\u5802\uff1a{sitter_name}\n\u5929\u673a\u672a\u660e\uff0c\u8bf7\u5bbf\u4e3b\u5728 60 \u79d2\u5185\u8bf4\u51fa\u6240\u95ee\u4e4b\u4e8b\u3002\n\u793a\u4f8b\uff1a\u4eca\u65e5\u4fee\u884c\u662f\u5426\u987a\u5229\uff1f\n\u4e5f\u53ef\u76f4\u63a5\u53d1\u9001\uff1a\u5360\u535c \u4eca\u65e5\u8fd0\u52bf",
        record,
        subtitle="60\u79d2\u5185\u56de\u590d\u95ee\u9898",
        icon="divination",
    )


@divination_reply.handle()
async def handle_divination_reply(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    key = divination_pending_key(event)
    pending_divinations.pop(key, None)
    record = await store.get_user(event.get_user_id())
    await require_tianji_hall(matcher, event, record)
    question = normalized_plain_text(event)
    income_text = await settle_divination_income(event, record)
    await finish_panel(
        matcher,
        "\u5929\u673a\u5360\u535c",
        tianji_divination_text(record, question, local_today()) + income_text,
        record,
        icon="divination",
    )


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

@mystic_entry.handle()
async def handle_mystic_entry(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    if record.mystic_realm:
        await finish_panel(matcher, "秘境探索", mystic_realm_options_text(record), record, icon="mystic")
    entries = draw_mystic_entrances(record)
    if not entries:
        await finish_panel(matcher, "秘境入口", "当前后台未开启任何秘境入口。", record, icon="mystic")
    key = mystic_pending_key(event)
    expires_at = time.monotonic() + MYSTIC_ENTRY_TTL
    pending_mystic_entries[key] = {
        "expires_at": expires_at,
        "entries": entries,
    }
    asyncio.create_task(
        send_mystic_timeout_notice(
            key,
            expires_at,
            event.get_user_id(),
            str(event.group_id) if isinstance(event, GroupMessageEvent) else None,
        )
    )
    await finish_panel(
        matcher,
        "秘境入口",
        format_mystic_entries(entries),
        record,
        subtitle="60秒内回复编号",
        icon="mystic",
    )


@mystic_entry_reply.handle()
async def handle_mystic_entry_reply(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    key = mystic_pending_key(event)
    pending = pending_mystic_entries.get(key)
    record = await store.get_user(event.get_user_id())
    if pending is None or float(pending.get("expires_at", 0)) < time.monotonic():
        pending_mystic_entries.pop(key, None)
        await finish_panel(matcher, "秘境入口", "已超时，如有需求系统将为宿主重新抽取。", record, icon="warning")
    index = parse_short_index_text(normalized_plain_text(event))
    entries = list(pending.get("entries", []))
    if index is None or index < 1 or index > len(entries):
        await finish_panel(matcher, "秘境入口", f"请选择 1-{len(entries)} 之间的秘境入口。", record, icon="warning")
    entry = entries[index - 1]
    success, message = start_mystic_realm(record, str(entry.get("type", "")), local_today(), entry)
    pending_mystic_entries.pop(key, None)
    if success:
        await store.save_user(record)
    await finish_panel(
        matcher,
        "秘境探索" if success else "进入失败",
        f"正在进入，传送中——\n{message}" if success else message,
        record,
        icon="mystic" if success else "warning",
    )


@mystic_explore.handle()
async def handle_mystic_explore(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    option_index = parse_prefixed_index(normalized_plain_text(event), MYSTIC_EXPLORE_PREFIXES)
    if option_index is None:
        await finish_panel(matcher, "操作提示", "请发送“探索 编号”，例如：探索 1。", record, icon="mystic")
    record.combat_nickname = nickname_from_event(event) or f"QQ {event.get_user_id()}"
    success, message = explore_mystic_realm(record, option_index, local_now())
    boss_duel = getattr(record, "last_mystic_boss_duel", None)
    if boss_duel:
        sent = await send_mystic_boss_duel_report(event.get_user_id(), record, boss_duel)
        record.last_mystic_boss_duel = None
        if not sent:
            message = f"{message}\n私聊战报发送失败，请检查好友或临时会话权限。"
    unique_note = await enforce_unique_rewards(record, event) if success else ""
    if unique_note:
        message = f"{message}\n{unique_note}"
    if success:
        await store.save_user(record)
    await finish_panel(matcher, "秘境探索" if success else "操作失败", message, record, icon="mystic" if success else "warning")


@signin.handle()
async def handle_signin(matcher: Matcher, event: MessageEvent) -> None:
    user_id = event.get_user_id()
    await remember_group_member(event)
    record = await store.get_user(user_id)
    result = apply_signin(record, local_today())
    await store.save_user(result.record)

    if not result.already_signed and isinstance(event, GroupMessageEvent) and is_tianji_hall_identity(result.record):
        sitter_name = nickname_from_event(event) or f"QQ {user_id}"
        created, hall = await store.register_tianji_sitter(
            str(event.group_id),
            user_id,
            local_today().isoformat(),
            sitter_name,
        )
        if created:
            await send_panel(
                matcher,
                "\u5929\u673a\u9601\u5750\u5802",
                (
                    f"\u4eca\u65e5\u7b2c\u4e00\u4f4d\u5929\u673a\u9601\u95e8\u4eba\u5df2\u5750\u5802\uff1a{sitter_name}\u3002\n"
                    f"\u672c\u7fa4\u4eca\u65e5\u5929\u673a\u5360\u535c\u5c06\u7531\u5176\u6267\u638c\uff0c"
                    f"\u6bcf\u5b8c\u6210\u4e00\u5366\u83b7\u5f97 {spirit_stone_text(DIVINATION_SITTER_INCOME)} \u6da6\u8d44\u3002\n"
                    f"\u5f53\u524d\u5750\u5802\u8bb0\u5f55\uff1a{tianji_sitter_names(hall)}"
                ),
                result.record,
                icon="divination",
            )

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
    await finish_panel(matcher, "个人战力", format_power_status(record, nickname_from_event(event)), record, icon="power")


@adventure.handle()
async def handle_adventure(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    image = render_adventure_card(
        record=record,
        nickname=nickname_from_event(event),
        width=config.xiuxian_signin_image_width,
    )
    await send_image(matcher, image)


@artifact_list.handle()
async def handle_artifact_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "我的灵器", format_artifact_list(record), record, icon="artifact")


@method_list.handle()
async def handle_method_list(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    await finish_panel(matcher, "我的功法", format_method_list(record), record, icon="method")





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
    await finish_panel(matcher, "我的阵盘", format_array_list(record), record, icon="array")


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


@doudizhu_cmd.handle()
async def handle_doudizhu(matcher: Matcher, event: GroupMessageEvent) -> None:
    await remember_group_member(event)
    group_id = doudizhu_group_key(event)
    user_id = event.get_user_id()
    text_value = normalized_plain_text(event)
    record = await store.get_user(user_id)

    if text_value in DOUDIZHU_HELP_TEXTS:
        await finish_panel(matcher, "\u6597\u5730\u4e3b\u5e2e\u52a9", doudizhu_help_text(), record, icon="poker")

    table = doudizhu_tables.get(group_id)
    if table and table.get("phase") == "lobby" and float(table.get("expires_at", 0)) < time.monotonic():
        doudizhu_tables.pop(group_id, None)
        table = None

    if text_value == "\u6597\u5730\u4e3b" and not table:
        await finish_panel(matcher, "\u6597\u5730\u4e3b", doudizhu_help_text(), record, icon="poker")

    if text_value == "\u6597\u5730\u4e3b\u5f00\u684c":
        if table:
            content = ddz_table_text(table) if table.get("phase") != "lobby" else ddz_lobby_text(table)
            await finish_panel(matcher, "\u6597\u5730\u4e3b", content, record, icon="poker")
        table = {
            "phase": "lobby",
            "phase_text": "\u7b49\u4eba",
            "host_id": user_id,
            "host_name": nickname_from_event(event) or f"QQ {user_id}",
            "players": [ddz_create_human_player(event)],
            "created_at": time.monotonic(),
            "expires_at": time.monotonic() + DDZ_HUMAN_WAIT_SECONDS,
        }
        doudizhu_tables[group_id] = table
        await finish_panel(matcher, "\u6597\u5730\u4e3b\u5f00\u684c", ddz_lobby_text(table), record, icon="poker")

    if text_value == "\u4eba\u673a\u6597\u5730\u4e3b":
        if table:
            await finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u672c\u7fa4\u5df2\u6709\u6597\u5730\u4e3b\u724c\u684c\uff0c\u8bf7\u5148\u7ed3\u675f\u6597\u5730\u4e3b\u3002", record, icon="warning")
        table = {
            "phase": "lobby",
            "phase_text": "\u7b49\u4eba",
            "host_id": user_id,
            "host_name": nickname_from_event(event) or f"QQ {user_id}",
            "players": [ddz_create_human_player(event), ddz_create_bot_player(1), ddz_create_bot_player(2)],
            "created_at": time.monotonic(),
        }
        doudizhu_tables[group_id] = table
        ddz_deal(table)
        await ddz_send_all_hands(table, group_id)
        logs = ["\u4eba\u673a\u6597\u5730\u4e3b\u5df2\u5f00\u5c40", ddz_bid_status(table)]
        logs.extend(await ddz_process_bot_bidding(group_id, table))
        await finish_panel(matcher, "\u6597\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    if not table:
        await finish_panel(matcher, "\u6597\u5730\u4e3b", "\u6682\u65e0\u6597\u5730\u4e3b\u724c\u684c\uff0c\u53ef\u53d1\u9001 \u6597\u5730\u4e3b\u5f00\u684c \u6216 \u4eba\u673a\u6597\u5730\u4e3b\u3002", record, icon="poker")

    player = ddz_player(table, user_id)

    if text_value == "\u6597\u5730\u4e3b":
        content = ddz_lobby_text(table) if table.get("phase") == "lobby" else ddz_table_text(table)
        await finish_panel(matcher, "\u6597\u5730\u4e3b", content, record, icon="poker")

    if text_value == "\u7ed3\u675f\u6597\u5730\u4e3b":
        if not player and str(table.get("host_id")) != user_id:
            await finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u53ea\u6709\u724c\u5c40\u73a9\u5bb6\u6216\u684c\u4e3b\u53ef\u4ee5\u7ed3\u675f\u6597\u5730\u4e3b\u3002", record, icon="warning")
        doudizhu_tables.pop(group_id, None)
        await finish_panel(matcher, "\u6597\u5730\u4e3b", "\u724c\u684c\u5df2\u7ed3\u675f\u3002", record, icon="poker")

    if text_value == "\u52a0\u5165\u6597\u5730\u4e3b":
        if table.get("phase") != "lobby":
            await finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u724c\u5c40\u5df2\u5f00\u59cb\uff0c\u65e0\u6cd5\u4e2d\u9014\u5165\u5ea7\u3002", record, icon="warning")
        if player:
            await finish_panel(matcher, "\u6597\u5730\u4e3b", "\u4f60\u5df2\u7ecf\u5728\u8fd9\u5f20\u724c\u684c\u4e0a\u3002", record, icon="poker")
        if len(table.get("players", [])) >= 3:
            await finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u724c\u684c\u5df2\u6ee1\u5458\u3002", record, icon="warning")
        table["players"].append(ddz_create_human_player(event))
        hint = "\n\u4eba\u6ee1\u4e86\uff0c\u53ef\u7531\u684c\u4e3b\u53d1\u9001 \u5f00\u59cb\u6597\u5730\u4e3b\u3002" if len(table["players"]) == 3 else ""
        await finish_panel(matcher, "\u52a0\u5165\u6597\u5730\u4e3b", ddz_lobby_text(table) + hint, record, icon="poker")

    if text_value == "\u9000\u51fa\u6597\u5730\u4e3b":
        if table.get("phase") != "lobby":
            await finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u724c\u5c40\u5df2\u5f00\u59cb\uff0c\u4e0d\u80fd\u9000\u51fa\uff0c\u53ef\u53d1\u9001\u6258\u7ba1\u3002", record, icon="warning")
        if not player:
            await finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u4f60\u4e0d\u5728\u8fd9\u5f20\u724c\u684c\u4e0a\u3002", record, icon="warning")
        table["players"] = [item for item in table["players"] if str(item.get("id")) != user_id]
        if not table["players"]:
            doudizhu_tables.pop(group_id, None)
            await finish_panel(matcher, "\u6597\u5730\u4e3b", "\u724c\u684c\u5df2\u89e3\u6563\u3002", record, icon="poker")
        if str(table.get("host_id")) == user_id:
            table["host_id"] = str(table["players"][0].get("id"))
            table["host_name"] = str(table["players"][0].get("name"))
        await finish_panel(matcher, "\u6597\u5730\u4e3b\u7b49\u5f85\u623f", ddz_lobby_text(table), record, icon="poker")

    if text_value == "\u5f00\u59cb\u6597\u5730\u4e3b":
        if table.get("phase") != "lobby":
            await finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u724c\u5c40\u5df2\u7ecf\u5f00\u59cb\u3002", record, icon="warning")
        if str(table.get("host_id")) != user_id:
            await finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u53ea\u6709\u684c\u4e3b\u53ef\u4ee5\u5f00\u59cb\u724c\u5c40\u3002", record, icon="warning")
        if len(table.get("players", [])) != 3:
            await finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u9700\u8981 3 \u4f4d\u73a9\u5bb6\u624d\u80fd\u5f00\u59cb\u3002", record, icon="warning")
        ddz_deal(table)
        await ddz_send_all_hands(table, group_id)
        logs = ["\u6597\u5730\u4e3b\u5f00\u5c40", ddz_bid_status(table)]
        logs.extend(await ddz_process_bot_bidding(group_id, table))
        await finish_panel(matcher, "\u6597\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    if not player:
        await finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u4f60\u8fd8\u6ca1\u6709\u5165\u5ea7\u8fd9\u5f20\u6597\u5730\u4e3b\u724c\u684c\u3002", record, icon="warning")

    if text_value == "\u624b\u724c":
        await ddz_send_hand(player, table, group_id)
        await finish_panel(matcher, "\u6597\u5730\u4e3b\u624b\u724c", "\u5df2\u5c1d\u8bd5\u79c1\u804a\u53d1\u9001\u624b\u724c\u3002", record, icon="poker")

    if text_value == "\u6258\u7ba1":
        player["bot"] = True
        logs = [f"{player.get('name')} \u5df2\u8fdb\u5165\u6258\u7ba1"]
        logs.extend(await ddz_process_bot_steps(group_id, table))
        await finish_panel(matcher, "\u6597\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    if table.get("phase") == "bidding" and is_doudizhu_bid_text(text_value):
        if not ddz_user_can_act(table, user_id):
            await finish_panel(matcher, "\u7b49\u5f85\u51fa\u624b", f"\u5f53\u524d\u8f6e\u5230 {ddz_current_player(table).get('name')} \u53eb\u5206\u3002", record, icon="warning")
        bid = ddz_parse_bid(text_value, int(table.get("highest_bid", 0)))
        if bid is None or bid < 0 or bid > 3:
            await finish_panel(matcher, "\u53eb\u5206\u5931\u8d25", "\u8bf7\u53d1\u9001\uff1a\u53eb\u5206 1 / \u53eb\u5206 2 / \u53eb\u5206 3 / \u53eb\u5730\u4e3b / \u4e0d\u53eb", record, icon="warning")
        if bid and bid <= int(table.get("highest_bid", 0)):
            await finish_panel(matcher, "\u53eb\u5206\u5931\u8d25", f"\u5fc5\u987b\u9ad8\u4e8e\u5f53\u524d\u6700\u9ad8\u5206 {table.get('highest_bid', 0)}\u3002", record, icon="warning")
        logs = [ddz_apply_bid(table, player, bid)]
        result = ddz_after_bid(table)
        if result:
            logs.append(result)
        else:
            logs.append(ddz_bid_status(table))
        logs.extend(await ddz_process_bot_bidding(group_id, table))
        await finish_panel(matcher, "\u6597\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    if table.get("phase") == "rob" and text_value in {"\u62a2\u5730\u4e3b", "\u4e0d\u62a2", "\u65bd\u52a0\u5a01\u538b"}:
        candidate_id = str(table.get("landlord_candidate"))
        if user_id == candidate_id:
            await finish_panel(matcher, "\u62a2\u5730\u4e3b", "\u5019\u9009\u5730\u4e3b\u4e0d\u80fd\u81ea\u5df1\u62a2\u81ea\u5df1\u3002", record, icon="warning")
        if user_id in set(table.get("rob_passes", set())):
            await finish_panel(matcher, "\u62a2\u5730\u4e3b", "\u4f60\u5df2\u7ecf\u8868\u6001\u8fc7\u4e86\u3002", record, icon="warning")
        if text_value == "\u4e0d\u62a2":
            table.setdefault("rob_passes", set()).add(user_id)
            logs = [f"{player.get('name')} \u4e0d\u62a2"]
            if ddz_rob_needed_done(table):
                logs.append(await ddz_finalize_and_advance(group_id, table, candidate_id))
            else:
                logs.append(ddz_begin_rob_text(table))
            logs.extend(await ddz_process_bot_rob(group_id, table))
            await finish_panel(matcher, "\u62a2\u5730\u4e3b", "\n".join(logs), record, icon="poker")
        pressure = text_value == "\u65bd\u52a0\u5a01\u538b"
        candidate = ddz_player(table, candidate_id)
        challenger_record = await store.get_user(user_id)
        candidate_record = await store.get_user(candidate_id) if candidate and not candidate.get("bot") else None
        actor_power = battle_power(challenger_record)
        target_power = battle_power(candidate_record) if candidate_record else 1
        chance = ddz_pressure_chance(actor_power, target_power, pressure)
        success = random.random() < chance
        action_name = "\u65bd\u52a0\u5a01\u538b\u62a2\u5730\u4e3b" if pressure else "\u62a2\u5730\u4e3b"
        logs = [f"{player.get('name')} {action_name}\uff0c\u6210\u529f\u7387 {int(chance * 100)}%\u3002"]
        if success:
            if pressure:
                table["phase"] = "retain"
                table["phase_text"] = "\u5a01\u538b\u4fdd\u7559"
                table["pending_pressure"] = {
                    "original_id": candidate_id,
                    "original_name": candidate.get("name") if candidate else candidate_id,
                    "challenger_id": user_id,
                    "challenger_name": player.get("name"),
                }
                logs.append(f"\u5a01\u538b\u6210\u529f\uff01{candidate.get('name') if candidate else candidate_id} \u53ef\u56de\u590d \u4fdd\u7559\u5730\u4e3b / \u653e\u5f03\u5730\u4e3b\u3002")
            else:
                table["landlord_candidate"] = user_id
                table["original_landlord"] = table.get("original_landlord") or candidate_id
                logs.append(await ddz_finalize_and_advance(group_id, table, user_id))
        else:
            table.setdefault("rob_passes", set()).add(user_id)
            logs.append("\u62a2\u5730\u4e3b\u5931\u8d25\u3002")
            if ddz_rob_needed_done(table):
                logs.append(await ddz_finalize_and_advance(group_id, table, candidate_id))
            else:
                logs.append(ddz_begin_rob_text(table))
            logs.extend(await ddz_process_bot_rob(group_id, table))
        await finish_panel(matcher, "\u62a2\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    if table.get("phase") == "retain" and text_value in {"\u4fdd\u7559\u5730\u4e3b", "\u653e\u5f03\u5730\u4e3b"}:
        pending = dict(table.get("pending_pressure") or {})
        if user_id != str(pending.get("original_id")):
            await finish_panel(matcher, "\u5a01\u538b\u4fdd\u7559", "\u53ea\u6709\u539f\u5b9a\u5730\u4e3b\u53ef\u4ee5\u51b3\u5b9a\u662f\u5426\u4fdd\u7559\u3002", record, icon="warning")
        if text_value == "\u4fdd\u7559\u5730\u4e3b":
            table["pressure_duel"] = {
                "left_id": pending.get("original_id"),
                "left_name": pending.get("original_name"),
                "right_id": pending.get("challenger_id"),
                "right_name": pending.get("challenger_name"),
            }
            content = await ddz_finalize_and_advance(group_id, table, str(pending.get("original_id")))
            await finish_panel(matcher, "\u4fdd\u7559\u5730\u4e3b", content + "\n\u724c\u5c40\u7ed3\u675f\u540e\u5c06\u5f3a\u5236\u89e6\u53d1\u666e\u901a\u6597\u6cd5\u3002", record, icon="poker")
        content = await ddz_finalize_and_advance(group_id, table, str(pending.get("challenger_id")))
        await finish_panel(matcher, "\u653e\u5f03\u5730\u4e3b", content, record, icon="poker")

    if table.get("phase") == "double" and text_value in {"\u52a0\u500d", "\u4e0d\u52a0\u500d"}:
        responses = table.setdefault("double_responses", set())
        if user_id in responses:
            await finish_panel(matcher, "\u52a0\u500d\u9636\u6bb5", "\u4f60\u5df2\u7ecf\u8868\u6001\u8fc7\u4e86\u3002", record, icon="warning")
        responses.add(user_id)
        logs = []
        if text_value == "\u52a0\u500d":
            table.setdefault("double_votes", set()).add(user_id)
            table["multiplier"] = int(table.get("multiplier", 1)) * 2
            logs.append(f"{player.get('name')} \u9009\u62e9\u52a0\u500d")
        else:
            logs.append(f"{player.get('name')} \u4e0d\u52a0\u500d")
        logs.extend(await ddz_process_bot_steps(group_id, table))
        if table.get("phase") == "double" and len(table.get("double_responses", set())) >= len(table.get("players", [])):
            ddz_start_play(table)
            await ddz_send_all_hands(table, group_id)
            logs.append("\u52a0\u500d\u9636\u6bb5\u7ed3\u675f\uff0c\u5730\u4e3b\u5148\u51fa\u724c\u3002")
        logs.extend(await ddz_process_bot_steps(group_id, table))
        if group_id in doudizhu_tables:
            logs.append(ddz_table_text(table))
        await finish_panel(matcher, "\u52a0\u500d\u9636\u6bb5", "\n".join(logs), record, icon="poker")

    if table.get("phase") == "playing" and text_value == "\u63d0\u793a":
        if not ddz_user_can_act(table, user_id):
            await finish_panel(matcher, "\u7b49\u5f85\u51fa\u624b", f"\u5f53\u524d\u8f6e\u5230 {ddz_current_player(table).get('name')}\u3002", record, icon="warning")
        last_play = table.get("last_play") if str(table.get("last_player")) != user_id else None
        hint = ddz_find_hint(list(player.get("hand", [])), last_play)
        await finish_panel(matcher, "\u51fa\u724c\u63d0\u793a", f"\u5efa\u8bae\uff1a{''.join(hint) if hint else '\u6682\u65e0\u53ef\u538b\u8fc7\u7684\u724c\uff0c\u53ef\u53d1\u9001 \u4e0d\u8981'}", record, icon="poker")

    if table.get("phase") == "playing" and (is_doudizhu_play_text(text_value) or text_value == "\u4e0d\u8981"):
        if not ddz_user_can_act(table, user_id):
            await finish_panel(matcher, "\u7b49\u5f85\u51fa\u624b", f"\u5f53\u524d\u8f6e\u5230 {ddz_current_player(table).get('name')}\u3002", record, icon="warning")
        logs = []
        if text_value == "\u4e0d\u8981":
            if not table.get("last_play") or str(table.get("last_player")) == user_id:
                await finish_panel(matcher, "\u51fa\u724c\u5931\u8d25", "\u4f60\u662f\u5f53\u524d\u9886\u724c\u8005\uff0c\u5fc5\u987b\u51fa\u724c\u3002", record, icon="warning")
            table["pass_count"] = int(table.get("pass_count", 0)) + 1
            logs.append(f"{player.get('name')} \u4e0d\u8981")
            if int(table.get("pass_count", 0)) >= 2:
                last = ddz_player(table, str(table.get("last_player")))
                logs.append(f"\u4e00\u8f6e\u8ddf\u724c\u7ed3\u675f\uff0c{last.get('name') if last else '\u4e0a\u5bb6'} \u91cd\u65b0\u9886\u724c\u3002")
                for idx, candidate in enumerate(table["players"]):
                    if str(candidate.get("id")) == str(table.get("last_player")):
                        table["current"] = idx
                        break
                table["last_play"] = None
                table["pass_count"] = 0
            else:
                ddz_next_turn(table)
        else:
            cards = ddz_parse_cards(text_value)
            if not cards:
                await finish_panel(matcher, "\u51fa\u724c\u5931\u8d25", "\u672a\u8bc6\u522b\u724c\u9762\uff0c\u4f8b\u5982\uff1a\u51fa\u724c 34567 / \u51fa\u724c 3334 / \u51fa\u724c \u5c0f\u738b\u5927\u738b\u3002", record, icon="warning")
            if not ddz_has_cards(list(player.get("hand", [])), cards):
                await finish_panel(matcher, "\u51fa\u724c\u5931\u8d25", f"\u624b\u724c\u4e2d\u6ca1\u6709\uff1a{ddz_cards_text(cards)}", record, icon="warning")
            analyzed = ddz_analyze_cards(cards)
            if not analyzed:
                await finish_panel(matcher, "\u51fa\u724c\u5931\u8d25", "\u8fd9\u7ec4\u724c\u4e0d\u7b26\u5408\u5f53\u524d\u6597\u5730\u4e3b\u724c\u578b\u3002", record, icon="warning")
            last_play = table.get("last_play") if str(table.get("last_player")) != user_id else None
            if not ddz_can_beat(analyzed, last_play):
                await finish_panel(matcher, "\u51fa\u724c\u5931\u8d25", "\u538b\u4e0d\u8fc7\u4e0a\u4e00\u624b\u724c\u3002", record, icon="warning")
            ddz_remove_cards(player["hand"], cards)
            table["last_play"] = {**analyzed, "cards": cards}
            table["last_player"] = user_id
            table["pass_count"] = 0
            if analyzed["type"] in {"bomb", "rocket"}:
                table["multiplier"] = int(table.get("multiplier", 1)) * 2
                logs.append("\u96f7\u52ab\u964d\u4e34\uff01\u5f53\u524d\u500d\u6570\u7ffb\u500d\u3002")
            if user_id == str(table.get("landlord")):
                table["landlord_play_count"] = int(table.get("landlord_play_count", 0)) + 1
            else:
                table["farmer_play_count"] = int(table.get("farmer_play_count", 0)) + 1
            logs.append(f"{player.get('name')} \u6253\u51fa {analyzed['label']}\uff1a{ddz_cards_text(cards)}")
            if not player.get("hand"):
                logs.append(await ddz_finish_game(group_id, table, user_id))
                await finish_panel(matcher, "\u6597\u5730\u4e3b\u7ed3\u7b97", "\n".join(logs), record, icon="poker")
            ddz_next_turn(table)
        logs.extend(await ddz_process_bot_steps(group_id, table))
        if group_id in doudizhu_tables:
            logs.append(ddz_table_text(table))
        await finish_panel(matcher, "\u6597\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    await finish_panel(matcher, "\u6597\u5730\u4e3b", ddz_table_text(table), record, icon="poker")


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
    unique_note = await enforce_unique_rewards(record, event)
    pending_fishing_users.pop(user_id, None)
    await store.save_user(record)
    image = await build_fishing_image(event, record, rewards)
    await send_image(matcher, image)
