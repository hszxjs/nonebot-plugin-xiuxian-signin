from __future__ import annotations

import asyncio
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
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from .cards import render_battle_card, render_fishing_card, render_signin_card, render_text_panel, set_font_paths
from .config import Config
from .domain import (
    CANCEL_WORDS,
    CONFIRM_WORDS,
    BREAKTHROUGH_REQUIREMENTS,
    FISHING_REWARDS,
    REALMS,
    RankReward,
    SigninResult,
    alchemy_text,

    apply_chat_cultivation,

    apply_dual_cultivation,
    apply_fishing,
    apply_rank_reward,
    apply_signin,
    artifact_power,
    array_multiplier,
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
    breakthrough_status,

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
    simulate_normal_duel,
    method_profile,
    format_method_detail,
    ensure_combat_profile,
    explore_mystic_realm,
    fishing_count_from_text,
    identify_misc_item,
    learn_special_ability,
    method_power,
    technique_cooldown,
    technique_mana_cost,
    mystic_realm_options_text,
    mystic_realm_title_from_entry,
    plant_spirit_plant,
    puppet_power,
    rank_reward_for,

    refine_pill_by_recipe,
    regress_cultivation,
    refine_spirit_stone,
    reward_display_name,

    route_status_text,

    sell_reward,

    shop_items_for_date,

    special_ability_catalog_text,
    special_ability_list_text,
    spirit_stone_text,
    talisman_draw_text,
    start_mystic_realm,
    unequip_artifact,
    use_curio,
    use_food,
    use_pill,
    use_talisman,
)
from .storage import JsonStore

__version__ = "0.5.1"

PICMENU_NEXT_FUNCS = [
    {
        "func": "\u5f00\u59cb\u4fee\u4ed9",
        "trigger_method": "\u7b7e\u5230 / \u9762\u677f / \u5e2e\u52a9",
        "trigger_condition": "\u9996\u6b21\u7b7e\u5230\u4f1a\u62bd\u53d6\u7075\u6839\uff1b\u5e2e\u52a9\u4f1a\u6253\u5f00\u5185\u7f6e\u8bf4\u660e",
        "brief_des": "\u4ece\u7b7e\u5230\u3001\u4e2a\u4eba\u9762\u677f\u548c\u65b0\u624b\u8bf4\u660e\u5f00\u59cb",
        "detail_des": "`\u7b7e\u5230` \u6bcf\u65e5\u4fee\u70bc\u5e76\u83b7\u5f97 1 \u6b21\u5782\u9493\uff1b`\u9762\u677f` \u67e5\u770b\u4e2a\u4eba\u72b6\u6001\uff1b`\u5e2e\u52a9` \u67e5\u770b\u4fee\u4e3a\u63d0\u5347\u8def\u5f84\u4e0e\u5e38\u7528\u5165\u53e3\u3002",
    },
    {
        "func": "\u80cc\u5305\u4e0e\u56fe\u9274",
        "trigger_method": "\u80cc\u5305 / \u56fe\u9274 / \u7279\u6b8a\u80fd\u529b / \u7279\u6b8a\u80fd\u529b\u56fe\u9274 / \u9886\u609f\u7279\u6b8a\u80fd\u529b 1",
        "trigger_condition": "\u56fe\u9274\u65e0\u9700\u62e5\u6709\u7269\u54c1\uff0c\u53ef\u76f4\u63a5\u67e5\u770b",
        "brief_des": "\u67e5\u770b\u9053\u5177\u3001\u7279\u6b8a\u80fd\u529b\u3001\u4e39\u836f\u3001\u7b26\u7b93\u3001\u7075\u5668\u548c\u529f\u6cd5",
        "detail_des": "`\u80cc\u5305` \u67e5\u770b\u5df2\u83b7\u5f97\u7269\u54c1\uff1b`\u7279\u6b8a\u80fd\u529b` \u67e5\u770b\u5df2\u9886\u609f\u80fd\u529b\u548c\u4f20\u627f\u6750\u6599\uff1b`\u7279\u6b8a\u80fd\u529b\u56fe\u9274` \u67e5\u770b\u4e5d\u79d8\u3001\u516b\u7981\u3001\u795e\u7981\u7b49\u8ffd\u6c42\u8def\u5f84\u3002",
    },
    {
        "func": "\u7a81\u7834\u4e0e\u4fee\u4e3a",
        "trigger_method": "\u7a81\u7834 / \u6563\u529f / \u5883\u754c\u56fe\u9274 / \u7a81\u7834\u56fe\u9274",
        "trigger_condition": "\u5883\u754c\u5706\u6ee1\u540e\u8fdb\u5165\u74f6\u9888\uff0c\u9700\u7a81\u7834\u540e\u7ee7\u7eed\u589e\u957f\u4fee\u4e3a",
        "brief_des": "\u67e5\u770b\u5883\u754c\u74f6\u9888\u3001\u7a81\u7834\u6750\u6599\u548c\u91cd\u4fee\u673a\u4f1a",
        "detail_des": "\u74f6\u9888\u540e\u4fee\u4e3a\u4e0d\u4f1a\u7ee7\u7eed\u589e\u52a0\uff0c\u6ea2\u51fa\u4fee\u4e3a\u4f1a\u51dd\u6210\u7cbe\u7eaf\u7075\u6db2\uff1b\u6c89\u6dc0\u5929\u6570\u4f1a\u63d0\u9ad8\u5782\u9493\u83b7\u5f97\u9ad8\u9636\u9ad8\u54c1\u8d28\u7a81\u7834\u9053\u5177\u7684\u6982\u7387\u3002",
    },
    {
        "func": "\u5386\u7ec3\u4e0e\u88c5\u5907",
        "trigger_method": "\u5386\u7ec3 / \u7075\u5668 / \u529f\u6cd5 / \u9635\u76d8 / \u6218\u529b / \u6218\u529b\u699c",
        "trigger_condition": "\u7f16\u53f7\u6765\u81ea\u5bf9\u5e94\u9762\u677f",
        "brief_des": "\u88c5\u5907\u7075\u5668\u3001\u53c2\u609f\u529f\u6cd5\u3001\u5e03\u7f6e\u9635\u76d8\u5e76\u8ba1\u7b97\u6218\u529b",
        "detail_des": "`\u88c5\u5907\u7075\u5668 1`\u3001`\u53c2\u609f\u529f\u6cd5 1`\u3001`\u5e03\u7f6e\u9635\u76d8 1` \u7ba1\u7406\u5386\u7ec3\u914d\u7f6e\uff1b`\u7279\u6b8a\u80fd\u529b` \u67e5\u770b\u6597\u6cd5\u53ef\u89e6\u53d1\u7684\u795e\u901a\uff1b`pk @\u7fa4\u53cb` \u53ef\u8fdb\u884c\u5207\u78cb\u3002",
    },
    {
        "func": "\u79d8\u5883\u4e0e\u4efb\u52a1",
        "trigger_method": "\u79d8\u5883 / \u63a2\u7d22 1 / \u6bcf\u65e5\u4efb\u52a1 / \u5546\u5e97",
        "trigger_condition": "\u79d8\u5883\u5165\u53e3 60 \u79d2\u5185\u9009\u62e9\uff1b\u4efb\u52a1\u7b7e\u5230\u540e\u751f\u6210",
        "brief_des": "\u9650\u65f6\u79d8\u5883\u3001\u6bcf\u65e5\u4efb\u52a1\u548c\u6bcf\u65e5\u5546\u5e97",
        "detail_des": "`\u79d8\u5883` \u62bd\u53d6 3 \u4e2a\u5165\u53e3\uff0c\u8fdb\u5165\u540e 10 \u6b21\u63a2\u7d22\uff1b`\u6bcf\u65e5\u4efb\u52a1` \u67e5\u770b\u76ee\u6807\uff1b`\u5546\u5e97` \u4f7f\u7528\u7075\u77f3\u8d2d\u4e70\u6216\u51fa\u552e\u7269\u54c1\u3002",
    },
    {
        "func": "\u8def\u7ebf\u4e0e\u8eab\u4efd",
        "trigger_method": "\u8def\u7ebf / \u9009\u62e9\u8def\u7ebf \u5251\u4fee / \u9009\u62e9\u8eab\u4efd \u5929\u673a\u9601\u5f1f\u5b50 / \u9009\u62e9\u8eab\u4efd \u5408\u6b22\u5b97\u5f1f\u5b50",
        "trigger_condition": "\u4e3b\u8def\u7ebf\u540c\u4e00\u65f6\u95f4\u53ea\u80fd\u4e00\u79cd\uff1b\u90aa\u4fee\u53ef\u989d\u5916\u540c\u4fee",
        "brief_des": "\u9009\u62e9\u4e3b\u4fee\u8def\u7ebf\u3001\u90aa\u4fee\u540c\u4fee\u548c\u5b97\u95e8\u8eab\u4efd\u4ee4\u724c",
        "detail_des": "`\u8def\u7ebf` \u4f1a\u663e\u793a\u6240\u6709\u8def\u7ebf\u6548\u679c\u3001\u5929\u673a\u9601/\u5408\u6b22\u5b97\u8eab\u4efd\u95e8\u69db\u3001\u8eab\u4efd\u4ee4\u724c\u6b21\u6570\u548c\u793a\u4f8b\u6307\u4ee4\u3002",
    },
    {
        "func": "\u70bc\u4e39\u4e0e\u7b26\u7b93",
        "trigger_method": "\u70bc\u4e39 / \u70bc\u4e39 \u7b51\u57fa\u4e39 / \u7ed8\u5236\u7b26\u7b93 / \u7ed8\u5236\u7b26\u7b93 1",
        "trigger_condition": "\u70bc\u4e39\u9700\u70bc\u4e39\u5e08\u8def\u7ebf\uff1b\u7ed8\u5236\u7b26\u7b93\u9700\u4fee\u4e3a\u548c\u7075\u77f3",
        "brief_des": "\u70bc\u5236\u4e39\u836f\u3001\u67e5\u770b\u4e39\u65b9\u5e76\u7ed8\u5236\u7b26\u7b93",
        "detail_des": "\u6750\u6599\u54c1\u9636\u548c\u54c1\u8d28\u4f1a\u5f71\u54cd\u70bc\u4e39\u6210\u529f\u7387\u4e0e\u6210\u4e39\u54c1\u8d28\uff1b\u7a81\u7834\u7b26\u4ee4\u3001\u7b26\u8bcf\u548c\u6cd5\u65e8\u9700\u8981\u5bf9\u5e94\u5883\u754c\u5dc5\u5cf0\u624d\u53ef\u7ed8\u5236\u3002",
    },
    {
        "func": "\u6392\u884c",
        "trigger_method": "\u6392\u884c / \u4fee\u4e3a\u699c / \u6218\u529b\u699c",
        "trigger_condition": "\u7fa4\u804a\u5185\u4f7f\u7528",
        "brief_des": "\u67e5\u770b\u7fa4\u4fee\u4e3a\u699c\u3001\u6218\u529b\u699c\u548c\u6bcf\u65e5\u8bdd\u75e8\u7ed3\u7b97",
        "detail_des": "\u6bcf\u65e5 22:00 \u81ea\u52a8\u53d1\u5e03\u8bdd\u75e8\u699c\u5e76\u53d1\u5956\uff0c\u540c\u65f6\u540c\u6b65\u7fa4\u4fee\u4e3a\u699c\u548c\u7fa4\u6218\u529b\u699c\u3002",
    },
]

__plugin_meta__ = PluginMetadata(
    name="修仙签到",
    description="以图片面板输出的修仙签到、灵根抽取、特殊能力领悟、境界突破、历练道具、秘境探索与诸天万界垂钓插件。",
    usage=(
        "签到：每日签到，首次抽取灵根\n"
        "我的修为：查看当前修炼状态\n"
        "垂钓：消耗已有诸天万界垂钓次数\n"
        "每日话痨榜：群聊发言自动统计，每晚 22:00 发布并发奖\n"
        "修为榜：查看本群修为排行榜\n"
        "历练：装备灵器、参悟功法、布置阵盘、查看战力、PK 与战力榜\n"
        "突破/散功：突破境界瓶颈，或回退至上一境界后期重修\n"
        "背包：使用丹药、符箓、灵石、灵食、奇物和杂物\n"
        "特殊能力：查看九秘残页、八禁感悟、神禁烙印等传承材料；领悟特殊能力 1 进行参悟\n"
        "秘境：60秒限时入口，进入后发送 探索 1-5"
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
    "\u4e39\u836f\u56fe\u9274",
    "\u7b26\u7b93\u56fe\u9274",
    "\u6b66\u5668\u56fe\u9274",
    "\u7075\u5668\u56fe\u9274",
    "\u529f\u6cd5\u56fe\u9274",
    "\u9635\u76d8\u56fe\u9274",
    "\u6750\u6599\u56fe\u9274",
    "\u7279\u6b8a\u80fd\u529b\u56fe\u9274",
    "\u795e\u901a\u56fe\u9274",
    "\u7075\u6750\u56fe\u9274",
}
BREAKTHROUGH_TEXTS = {"\u7a81\u7834", "\u5883\u754c\u7a81\u7834", "\u7834\u5883", "\u67e5\u770b\u7a81\u7834", "\u7a81\u7834\u72b6\u6001", "\u6563\u529f", "\u91cd\u4fee", "\u81ea\u5e9f\u4fee\u4e3a"}
CULTIVATION_RANK_TEXTS = {"\u4fee\u4e3a\u699c", "\u7fa4\u4fee\u4e3a\u699c", "\u5883\u754c\u699c", "\u6392\u884c", "\u6392\u884c\u699c"}
POWER_RANK_TEXTS = {"战力榜", "群战力榜"}
POWER_TEXTS = {"战力", "我的战力"}
ADVENTURE_TEXTS = {"历练", "历练面板", "历练帮助"}
ARTIFACT_LIST_TEXTS = {"\u7075\u5668", "\u6211\u7684\u7075\u5668", "\u7075\u5668\u5217\u8868", "\u88c5\u5907\u5217\u8868", "\u6b66\u5668", "\u6211\u7684\u6b66\u5668", "\u6b66\u5668\u5217\u8868"}
METHOD_LIST_TEXTS = {"功法", "我的功法", "功法列表"}
ARRAY_LIST_TEXTS = {"阵盘", "我的阵盘", "阵盘列表", "阵法", "我的阵法"}
PUPPET_LIST_TEXTS = {"傀儡", "我的傀儡", "傀儡列表"}
PLANT_LIST_TEXTS = {"灵植", "我的灵植", "灵植列表"}
ITEM_LIST_TEXTS = {"\u9053\u5177", "\u6211\u7684\u9053\u5177", "\u80cc\u5305", "\u7269\u54c1", "\u6211\u7684\u7269\u54c1", "\u5305\u88f9"}
SPECIAL_ABILITY_TEXTS = {"特殊能力", "我的特殊能力", "神通", "我的神通"}
SPECIAL_ABILITY_CATALOG_TEXTS = {"特殊能力图鉴", "神通图鉴"}
ROUTE_TEXTS = {"\u4fee\u70bc\u8def\u7ebf", "\u8def\u7ebf", "\u8eab\u4efd", "\u8eab\u4efd\u4ee4\u724c", "\u5b97\u95e8\u8eab\u4efd"}
TASK_TEXTS = {"每日任务", "任务", "我的任务"}
SHOP_TEXTS = {"商店", "坊市", "每日商店"}
ALCHEMY_TEXTS = {"炼丹", "丹方"}
TALISMAN_DRAW_TEXTS = {"\u7ed8\u5236\u7b26\u7b93", "\u753b\u7b26", "\u5236\u7b26", "\u7b26\u7b93\u7ed8\u5236", "\u7ed8\u7b26"}
TIANJI_MYSTIC_TEXTS = {"天机秘境", "天机探索", "特殊秘境"}
MYSTIC_ENTRY_TEXTS = {"秘境", "查看秘境", "秘境入口", "探查秘境"}
UNEQUIP_TEXTS = {"卸下灵器", "卸下装备"}
EQUIP_PREFIXES = ("装备灵器", "装备")
METHOD_EQUIP_PREFIXES = ("参悟功法", "修炼功法", "装备功法")
METHOD_DETAIL_PREFIXES = ("学习功法", "查看功法", "功法详情", "功法页面")
ARRAY_EQUIP_PREFIXES = ("布置阵盘", "装备阵盘", "布阵", "布置阵法")
PUPPET_EQUIP_PREFIXES = ("装备傀儡", "唤醒傀儡", "启用傀儡")
PLANT_EQUIP_PREFIXES = ("栽种灵植", "种植灵植", "种灵植")
PILL_USE_PREFIXES = ("使用丹药", "服用丹药", "服丹", "吃丹药")
TALISMAN_USE_PREFIXES = ("使用符箓", "激发符箓", "用符")
STONE_USE_PREFIXES = ("炼化灵石", "使用灵石", "吸收灵石")
FOOD_USE_PREFIXES = ("使用灵食", "食用灵食", "吃灵食")
CURIO_USE_PREFIXES = ("使用奇物", "催动奇物", "参悟奇物")
MISC_USE_PREFIXES = ("鉴定杂物", "鉴定")
ROUTE_SELECT_PREFIXES = ("选择路线", "切换路线")
IDENTITY_SELECT_PREFIXES = ("选择身份", "加入身份", "晋升身份")
EVIL_SELECT_TEXTS = {"选择邪修", "加入邪修", "同修邪修"}
EVIL_QUIT_TEXTS = {"退出邪修", "脱离邪修"}
TASK_COMPLETE_PREFIXES = ("完成任务", "提交任务")
BUY_PREFIXES = ("购买", "买入")
SELL_PREFIXES = ("出售", "卖出")
ALCHEMY_PREFIXES = ("炼丹",)
TALISMAN_DRAW_PREFIXES = ("\u7ed8\u5236\u7b26\u7b93", "\u753b\u7b26", "\u5236\u7b26", "\u7ed8\u7b26")
SPECIAL_ABILITY_LEARN_PREFIXES = ("\u9886\u609f\u7279\u6b8a\u80fd\u529b", "\u9886\u609f\u795e\u901a", "\u53c2\u609f\u7279\u6b8a\u80fd\u529b")
MYSTIC_EXPLORE_PREFIXES = ("探索", "秘境探索")
DUEL_PREFIXES = ("pk", "PK", "切磋", "挑战")
NORMAL_DUEL_TEXTS = {"申请普通斗法", "普通斗法", "普通斗法申请", "申请斗法", "斗法匹配"}
FISHING_TEXTS = ("\u5782\u9493", "\u9493\u9c7c", "\u8bf8\u5929\u4e07\u754c\u5782\u9493")
COMMAND_PREFIX_CHARS = "/!！.。"
PENDING_FISHING_TTL = 120
MYSTIC_ENTRY_TTL = 60
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
normal_duel_queue: dict[str, dict[str, Any]] = {}
normal_duel_sessions: dict[str, dict[str, Any]] = {}
rank_scheduler_task: Optional[asyncio.Task] = None


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


def is_equip_command_text(text: str) -> bool:
    if text in UNEQUIP_TEXTS:
        return True
    if is_equip_method_command_text(text) or is_equip_array_command_text(text):
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


def is_item_use_command_text(text: str) -> bool:
    return any(
        is_prefixed_index_command(text, prefixes)
        for prefixes in (
            PILL_USE_PREFIXES,
            TALISMAN_USE_PREFIXES,
            STONE_USE_PREFIXES,
            FOOD_USE_PREFIXES,
            CURIO_USE_PREFIXES,
            MISC_USE_PREFIXES,
        )
    )


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
    return text in SHOP_TEXTS or parse_shop_buy_index(text) is not None or parse_sell_item(text) is not None


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


def is_dual_cultivation_command_text(text: str) -> bool:
    return text.startswith("双修") or text == "随机双修"


def parse_item_use(text: str) -> Optional[tuple[str, int]]:
    mapping = [
        ("丹药", PILL_USE_PREFIXES),
        ("符箓", TALISMAN_USE_PREFIXES),
        ("灵石", STONE_USE_PREFIXES),
        ("灵食", FOOD_USE_PREFIXES),
        ("奇物", CURIO_USE_PREFIXES),
        ("杂物", MISC_USE_PREFIXES),
    ]
    for category, prefixes in mapping:
        index = parse_prefixed_index(text, prefixes)
        if index is not None:
            return category, index
    return None


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
    categories = ("灵器", "功法", "丹药", "阵盘", "灵材", "符箓", "傀儡", "灵植", "灵石", "杂物", "奇物", "灵食", "特殊能力")
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
        or text in CATALOG_TEXTS
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
        or is_special_ability_command_text(text)
        or is_special_ability_learn_command_text(text)
        or text in MYSTIC_ENTRY_TEXTS
        or is_route_command_text(text)
        or is_task_command_text(text)
        or is_shop_command_text(text)
        or is_alchemy_command_text(text)
        or is_talisman_draw_command_text(text)
        or is_tianji_mystic_command_text(text)
        or is_dual_cultivation_command_text(text)
        or text in UNEQUIP_TEXTS
        or parse_fishing_arg(text) is not None
        or is_equip_command_text(text)
        or is_equip_method_command_text(text)
        or is_method_detail_command_text(text)
        or is_normal_duel_apply_text(text)
        or is_equip_array_command_text(text)
        or is_equip_puppet_command_text(text)
        or is_plant_command_text(text)
        or is_item_use_command_text(text)
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


async def send_image(matcher: Matcher, image_bytes: bytes) -> None:
    await matcher.send(MessageSegment.image(BytesIO(image_bytes)))


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
                    f"\u7279\u6b8a\u80fd\u529b\uff1a{abilities}",
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
                    "\u53ef\u7528\u7b26\u7b93\uff1a",
                    *talisman_lines,
                    "\u7b26\u7b93\u8bf7\u5728\u6597\u6cd5\u5916\u901a\u8fc7\u80cc\u5305/\u7b26\u7b93\u754c\u9762\u786e\u8ba4\uff1b\u672c\u573a\u666e\u901a\u6597\u6cd5\u4f1a\u4f18\u5148\u7ed3\u7b97\u6218\u6280\u3001\u7279\u6b8a\u80fd\u529b\u3001\u4f53\u672f\u548c\u4f53\u8d28\u7279\u6027\u3002",
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
                "\u6597\u6cd5\u5df2\u5f00\u59cb\uff0c60\u79d2\u5185\u53d1\u9001\u6218\u6280\u3001\u7279\u6b8a\u80fd\u529b\u3001\u8868\u60c5\u6216\u5373\u5174\u672f\u5f0f\u3002",
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
    lines = ["【我的灵器】"]
    lines.append(f"当前装备：{reward_display_name(record.equipped_artifact) if record.equipped_artifact else '未装备灵器'}")
    if not artifacts:
        lines.append("暂无可装备灵器，进行诸天万界垂钓有机会获得。")
        return "\n".join(lines)
    for index, artifact in enumerate(artifacts, start=1):
        required = artifact.get("required_attribute")
        compatible = "可装备" if not required or required in record.root_attributes else "灵根不契合"
        bonus = artifact_power(artifact, record)
        lines.append(
            f"{index}. {reward_display_name(artifact)}，需求{required or '无'}灵根，"
            f"{compatible}，战力+{bonus}"
        )
    lines.append("发送“装备灵器 编号”即可装备；发送“卸下灵器”可卸下当前灵器。")
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
            f"{index}. {reward_display_name(method)}\uff0c{profile['kind']}\uff0c\u7b2c{profile['layer']}\u5c42\uff0c"
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
        lines.append("暂无阵盘，进行诸天万界垂钓有机会获得。")
        return "\n".join(lines)
    for index, array in enumerate(arrays, start=1):
        lines.append(f"{index}. {reward_display_name(array)}")
    lines.append("发送“布置阵盘 编号”即可布置；阵法熟练度随签到和聊天修炼提升。")
    return "\n".join(lines)


def format_puppet_list(record) -> str:
    puppets = available_puppets(record)
    lines = ["【我的傀儡】"]
    lines.append(f"当前傀儡：{reward_display_name(record.equipped_puppet) if record.equipped_puppet else '未唤醒傀儡'}")
    if not puppets:
        lines.append("暂无傀儡，诸天万界垂钓或秘境探索有机会获得。")
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
        lines.append("暂无灵植，诸天万界垂钓或秘境探索有机会获得。")
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
            lines.append(f"{index}. {reward_display_name(item)}")
    lines.append(usage)


def format_item_list(record) -> str:
    lines = ["\u3010\u80cc\u5305\u9053\u5177\u3011"]
    summary = battle_summary(record)
    lines.append(f"\u7075\u77f3\u50a8\u5907\uff1a{spirit_stone_text(record.spirit_stones)}\uff1b\u5782\u9493\u6b21\u6570\uff1a{record.fishing_chances}")
    lines.append(f"\u7cbe\u7eaf\u7075\u6db2\uff1a{summary['spirit_liquid']}\uff1b\u74f6\u9888\u6c89\u6dc0\uff1a{summary['bottleneck_days']} \u5929")
    if summary.get("is_bottleneck"):
        lines.append(f"\u5f53\u524d\u74f6\u9888\uff1a\u9700 {summary['breakthrough_required']} \u624d\u80fd\u7a81\u7834\u3002")
    if summary.get("cultivation_lock"):
        lines.append(f"\u72b6\u6001\uff1a{summary['cultivation_lock']}")
    sections = [
        ("\u4e39\u836f", available_pills(record), "\u7528\u6cd5\uff1a\u4f7f\u7528\u4e39\u836f \u7f16\u53f7\uff1b\u7a81\u7834\u9053\u5177\u8bf7\u53d1\u9001\u201c\u7a81\u7834\u201d"),
        ("\u7b26\u7b93", available_talismans(record), "\u7528\u6cd5\uff1a\u4f7f\u7528\u7b26\u7b93 \u7f16\u53f7\uff1b\u7ed8\u5236\u7b26\u7b93 \u7f16\u53f7\u53ef\u81ea\u884c\u5236\u7b26"),
        ("\u7075\u77f3", available_spirit_stones(record), "\u7528\u6cd5\uff1a\u70bc\u5316\u7075\u77f3 \u7f16\u53f7\uff1b\u74f6\u9888\u65f6\u4f1a\u8f6c\u4e3a\u7cbe\u7eaf\u7075\u6db2"),
        ("\u7075\u6750", available_materials(record), "\u7528\u6cd5\uff1a\u70bc\u4e39\u6750\u6599\uff1b\u51fa\u552e\u7075\u6750 \u7f16\u53f7\u53ef\u6362\u7075\u77f3"),
        ("\u7279\u6b8a\u80fd\u529b", available_special_ability_items(record), "\u7528\u6cd5\uff1a\u9886\u609f\u7279\u6b8a\u80fd\u529b \u7f16\u53f7\uff1b\u53ef\u83b7\u5f97\u4e5d\u79d8\u3001\u516b\u7981\u3001\u795e\u7981\u7b49\u80fd\u529b"),
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
                lines.append(f"{index}. {reward_display_name(item)}")
        lines.append(usage)
    return "\n".join(lines)

def format_help_text() -> str:
    return "\n".join(
        [
            "\u3010\u4fee\u4ed9\u5e2e\u52a9\u3011",
            "\u5e38\u7528\u5165\u53e3\uff1a\u7b7e\u5230 / \u9762\u677f / \u80cc\u5305 / \u56fe\u9274 / \u5386\u7ec3 / \u79d8\u5883 / \u7a81\u7834 / \u6392\u884c / \u5546\u5e97",
            "",
            "\u3010\u4fee\u4e3a\u63d0\u5347\u8def\u5f84\u3011",
            "1. \u7b7e\u5230\uff1a\u6bcf\u65e5\u589e\u52a0\u4fee\u4e3a\uff0c\u9996\u6b21\u62bd\u53d6\u7075\u6839\uff0c\u6bcf\u6b21\u7b7e\u5230\u83b7\u5f97 1 \u6b21\u5782\u9493\u3002",
            "2. \u529f\u6cd5\uff1a\u53c2\u609f\u540e\u53ef\u63d0\u5347\u7b7e\u5230\u6536\u76ca\uff0c\u804a\u5929\u65f6\u4e5f\u80fd\u6309\u6761\u6570\u4ea7\u751f\u4fee\u4e3a\u3002",
            "3. \u7075\u690d/\u7075\u98df/\u4e39\u836f/\u7075\u77f3\uff1a\u5728\u80cc\u5305\u4e2d\u4f7f\u7528\uff0c\u6216\u7528\u4e8e\u70bc\u4e39\u3001\u7a81\u7834\u3002",
            "4. \u74f6\u9888\uff1a\u5883\u754c\u5706\u6ee1\u540e\u4fee\u4e3a\u4e0d\u518d\u589e\u957f\uff0c\u6ea2\u51fa\u4fee\u4e3a 50% \u4f1a\u51dd\u6210\u7cbe\u7eaf\u7075\u6db2\u3002",
            "5. \u6c89\u6dc0\uff1a\u74f6\u9888\u540e\u6bcf\u5929\u7b7e\u5230\u6c89\u6dc0\u4e00\u6b21\uff0c\u5782\u9493\u9ad8\u9636\u7a81\u7834\u9053\u5177\u6743\u91cd\u4f1a\u9010\u65e5\u63d0\u5347\u3002",
            "",
            "\u3010\u8def\u7ebf\u4e0e\u8eab\u4efd\u3011",
            "\u53d1\u9001\u201c\u8def\u7ebf\u201d\u67e5\u770b\u5251\u4fee\u3001\u672f\u4fee\u3001\u70bc\u4e39\u5e08\u3001\u9635\u6cd5\u5e08\u7684\u6548\u679c\uff0c\u4e5f\u4f1a\u663e\u793a\u5929\u673a\u9601\u4e0e\u5408\u6b22\u5b97\u8eab\u4efd\u7684\u95e8\u69db\u3002",
            "\u4e3b\u8def\u7ebf\u793a\u4f8b\uff1a\u9009\u62e9\u8def\u7ebf \u5251\u4fee\uff1b\u5b97\u95e8\u793a\u4f8b\uff1a\u9009\u62e9\u8eab\u4efd \u5929\u673a\u9601\u5f1f\u5b50\u3002",
            "",
            "\u3010\u56fe\u9274\u5165\u53e3\u3011",
            "\u56fe\u9274 / \u5883\u754c\u56fe\u9274 / \u7a81\u7834\u56fe\u9274 / \u4e39\u836f\u56fe\u9274 / \u7b26\u7b93\u56fe\u9274 / \u6b66\u5668\u56fe\u9274 / \u529f\u6cd5\u56fe\u9274 / \u7279\u6b8a\u80fd\u529b\u56fe\u9274",
            "\u3010\u7279\u6b8a\u80fd\u529b\u3011",
            "\u7279\u6b8a\u80fd\u529b / \u9886\u609f\u7279\u6b8a\u80fd\u529b 1 / \u7279\u6b8a\u80fd\u529b\u56fe\u9274\uff1a\u67e5\u770b\u3001\u9886\u609f\u5e76\u8ffd\u6c42\u4e5d\u79d8\u3001\u516b\u7981\u3001\u795e\u7981\u7b49\u80fd\u529b\u3002",
            "\u3010\u6597\u6cd5\u3011",
            "\u7533\u8bf7\u666e\u901a\u6597\u6cd5\uff1a\u4e24\u4eba\u5339\u914d\u540e 1 \u5206\u949f\u51c6\u5907\uff0c60 \u79d2\u5185\u53d1\u9001\u6218\u6280\u3001\u7279\u6b8a\u80fd\u529b\u6216\u5373\u5174\u53f0\u8bcd\uff0c\u7ed3\u675f\u540e\u8f93\u51fa\u6218\u62a5\u56fe\u3002",
        ]
    )


def reward_catalog_lines(category: str, title: str) -> list[str]:
    tier_order = ["\u5929\u9636", "\u5730\u9636", "\u7384\u9636", "\u9ec4\u9636", "\u51e1\u54c1"]
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
    if text in {"\u56fe\u9274", "\u56fe\u5f55"}:
        return "\n".join(
            [
                "\u3010\u5185\u7f6e\u56fe\u9274\u3011",
                "\u5883\u754c\u56fe\u9274\uff1a\u5883\u754c\u3001\u9636\u6bb5\u548c\u74f6\u9888\u8bf4\u660e\u3002",
                "\u7a81\u7834\u56fe\u9274\uff1a\u6bcf\u4e2a\u74f6\u9888\u9700\u8981\u7684\u4e39\u836f\u3001\u7b26\u4ee4\u3001\u610f\u5883\u6216\u6cd5\u65e8\u3002",
                "\u4e39\u836f\u56fe\u9274\uff1a\u4e39\u836f\u4e0e\u7a81\u7834\u4e39\u6536\u5f55\uff0c\u70bc\u4e39\u6750\u6599\u54c1\u8d28\u4f1a\u5f71\u54cd\u6210\u4e39\u3002",
                "\u7b26\u7b93\u56fe\u9274\uff1a\u666e\u901a\u7b26\u7b93\u4e0e\u7a81\u7834\u7b26\u4ee4\u3001\u7b26\u8bcf\u3001\u6cd5\u65e8\u3002",
                "\u6b66\u5668\u56fe\u9274\uff1a\u5404\u7cfb\u7075\u6839\u53ef\u7528\u7684\u7075\u5668\u3002",
                "\u529f\u6cd5\u56fe\u9274\uff1a\u4fee\u70bc\u7c7b\u3001\u6218\u6280\u7c7b\u7b49\u529f\u6cd5\u6536\u5f55\u3002",
                "\u6750\u6599\u56fe\u9274\uff1a\u7075\u6750\u3001\u7075\u690d\u548c\u70bc\u4e39\u6240\u9700\u539f\u6599\u3002",
                "\u7279\u6b8a\u80fd\u529b\u56fe\u9274\uff1a\u4e5d\u79d8\u3001\u516b\u7981\u3001\u795e\u7981\u548c\u5176\u4ed6\u4f20\u627f\u80fd\u529b\u3002",
            ]
        )
    if text == "\u5883\u754c\u56fe\u9274":
        lines = ["\u3010\u5883\u754c\u56fe\u9274\u3011", "\u9636\u6bb5\uff1a\u521d\u671f / \u4e2d\u671f30% / \u540e\u671f60% / \u5706\u6ee1100% / \u5dc5\u5cf0\uff08\u74f6\u9888\u672a\u7a81\u7834\uff09"]
        for index, realm in enumerate(REALMS, start=1):
            suffix = "\uff08\u6709\u74f6\u9888\uff09" if index - 1 in BREAKTHROUGH_REQUIREMENTS else ""
            lines.append(f"{index}. {realm}{suffix}")
        return "\n".join(lines)
    if text == "\u7a81\u7834\u56fe\u9274":
        lines = ["\u3010\u7a81\u7834\u56fe\u9274\u3011", "\u4fee\u4e3a\u8fbe\u5230\u5706\u6ee1\u540e\u4f1a\u8fdb\u5165\u74f6\u9888\uff0c\u9700\u6d88\u8017\u5bf9\u5e94\u9053\u5177\u624d\u80fd\u7a81\u7834\u3002"]
        for realm_index, requirement in BREAKTHROUGH_REQUIREMENTS.items():
            current = REALMS[realm_index]
            target = str(requirement.get("target", "\u4e0b\u4e00\u5883"))
            items = " / ".join(str(item) for item in requirement.get("items", []))
            lines.append(f"{current} -> {target}\uff1a{items}")
        lines.append("\u74f6\u9888\u65f6\u7b7e\u5230/\u5782\u9493\u83b7\u5f97\u7a81\u7834\u9053\u5177\u7684\u6982\u7387\u4f1a\u5927\u5e45\u63d0\u5347\u3002")
        return "\n".join(lines)
    if text in SPECIAL_ABILITY_CATALOG_TEXTS:
        return special_ability_catalog_text()
    category_map = {
        "\u4e39\u836f\u56fe\u9274": ("\u4e39\u836f", "\u4e39\u836f\u56fe\u9274"),
        "\u7b26\u7b93\u56fe\u9274": ("\u7b26\u7b93", "\u7b26\u7b93\u56fe\u9274"),
        "\u6b66\u5668\u56fe\u9274": ("\u7075\u5668", "\u7075\u5668/\u6b66\u5668\u56fe\u9274"),
        "\u7075\u5668\u56fe\u9274": ("\u7075\u5668", "\u7075\u5668/\u6b66\u5668\u56fe\u9274"),
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
        "特殊能力": "ability",
    }.get(category, "bag")


def format_mystic_entries(entries: list[dict[str, Any]]) -> str:
    lines = ["叮！目前为宿主查找到以下秘境："]
    for index, entry in enumerate(entries, start=1):
        title = mystic_realm_title_from_entry(entry)
        recommended = str(entry.get("recommended") or "未知")
        lines.append(f"{index}、{title}（推荐修为：{recommended}）")
    if any(entry.get("insight") for entry in entries):
        lines.append("天机示警已开启：进入后会标出坏结局选项。")
    lines.append("（请在60s内回复，超时恐被其他修士捷足先登）")
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
        f"\u7075\u5668\uff1a{summary['artifact']}",
        f"\u529f\u6cd5\uff1a{summary['method']}",
        f"\u9635\u76d8\uff1a{summary['array']}\uff08{summary['array_multiplier']:.1f}x\uff09",
        f"\u5080\u5121\uff1a{summary['puppet']}\uff08\u6218\u529b+{summary['puppet_power']}\uff09",
        f"\u7075\u690d\uff1a{summary['plant']}",
        f"\u7075\u77f3\u50a8\u5907\uff1a{summary['spirit_stones_text']}",
        f"\u4fee\u70bc\u8def\u7ebf\uff1a{summary['route']}",
        f"\u8eab\u4efd\u4ee4\u724c\uff1a{summary['identity']}",
        f"\u7279\u6b8a\u80fd\u529b\uff1a{len(summary['special_abilities'])} \u9879\uff1b\u4f20\u627f\u6750\u6599\uff1a{summary['special_ability_materials']} \u4efd\uff1b\u6218\u529b+{summary['special_ability_power']}",
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
            f"\u5f53\u524d\u6218\u529b\uff1a{summary['power']}\uff1b\u7075\u529b\u4e0a\u9650\uff1a{summary['mana']}",
            f"\u5f53\u524d\u7075\u5668\uff1a{summary['artifact']}",
            f"\u5f53\u524d\u529f\u6cd5\uff1a{summary['method']}",
            f"\u5f53\u524d\u9635\u76d8\uff1a{summary['array']}\uff08{summary['array_multiplier']:.1f}x\uff09",
            f"\u5f53\u524d\u5080\u5121\uff1a{summary['puppet']}",
            f"\u5f53\u524d\u7075\u690d\uff1a{summary['plant']}",
            f"\u7075\u77f3\u50a8\u5907\uff1a{summary['spirit_stones_text']}",
            f"\u7cbe\u7eaf\u7075\u6db2\uff1a{summary['spirit_liquid']}\uff1b\u74f6\u9888\u6c89\u6dc0\uff1a{summary['bottleneck_days']} \u5929",
            f"\u4fee\u70bc\u8def\u7ebf\uff1a{summary['route']}",
            f"\u8eab\u4efd\u4ee4\u724c\uff1a{summary['identity']}\uff08\u5929\u673a\u79d8\u5883\uff1a{summary['tianji_status']}\uff0c\u53cc\u4fee\uff1a{summary['hehuan_remaining']}\uff09",
            f"\u7279\u6b8a\u80fd\u529b\uff1a{len(summary['special_abilities'])} \u9879\uff1b\u4f20\u627f\u6750\u6599\uff1a{summary['special_ability_materials']} \u4efd",
            "\u8def\u7ebf / \u9009\u62e9\u8def\u7ebf \u5251\u4fee / \u9009\u62e9\u8eab\u4efd \u5929\u673a\u9601\u5f1f\u5b50 / \u9009\u62e9\u8eab\u4efd \u5408\u6b22\u5b97\u5f1f\u5b50",
            "\u6bcf\u65e5\u4efb\u52a1 / \u5b8c\u6210\u4efb\u52a1 1 / \u5546\u5e97 / \u8d2d\u4e70 1 / \u51fa\u552e \u4e39\u836f 1",
            "\u70bc\u4e39 / \u70bc\u4e39 \u7b51\u57fa\u4e39 / \u5929\u673a\u79d8\u5883 / \u53cc\u4fee@\u7fa4\u53cb / \u968f\u673a\u53cc\u4fee",
            "\u7075\u5668 / \u529f\u6cd5 / \u9635\u76d8 / \u7279\u6b8a\u80fd\u529b\uff1a\u67e5\u770b\u53ef\u7528\u914d\u7f6e",
            "\u5080\u5121 / \u7075\u690d / \u80cc\u5305\uff1a\u67e5\u770b\u5386\u7ec3\u8d44\u6e90",
            "\u88c5\u5907\u7075\u5668 1 / \u53c2\u609f\u529f\u6cd5 1 / \u5e03\u7f6e\u9635\u76d8 1",
            "\u79d8\u5883\uff1a\u67e5\u770b60\u79d2\u9650\u65f6\u79d8\u5883\u5165\u53e3\uff1b\u63a2\u7d22 1\uff1a\u63a8\u8fdb\u5f53\u524d\u79d8\u5883",
            "\u7a81\u7834\uff1a\u5883\u754c\u5706\u6ee1\u540e\u4f7f\u7528\u7a81\u7834\u9053\u5177\uff1b\u6563\u529f\uff1a\u56de\u9000\u91cd\u4fee\u6539\u5584\u54c1\u76f8",
            "\u6218\u529b / pk @\u5bf9\u65b9 / \u7533\u8bf7\u666e\u901a\u6597\u6cd5 / \u6218\u529b\u699c\uff1a\u67e5\u770b\u6218\u529b\u4e0e\u5207\u78cb",
        ]
    )

def format_shop_panel(record, date_text: str) -> str:
    items = shop_items_for_date(date_text)
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
    global rank_scheduler_task
    rank_scheduler_task = asyncio.create_task(rank_scheduler())



async def is_help_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in HELP_TEXTS


async def is_catalog_message(event: MessageEvent) -> bool:
    return normalized_plain_text(event) in CATALOG_TEXTS


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


async def is_talisman_draw_message(event: MessageEvent) -> bool:
    return is_talisman_draw_command_text(normalized_plain_text(event))


async def is_tianji_mystic_message(event: MessageEvent) -> bool:
    return is_tianji_mystic_command_text(normalized_plain_text(event))


async def is_dual_cultivation_message(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) and is_dual_cultivation_command_text(normalized_plain_text(event))


async def is_equip_puppet_message(event: MessageEvent) -> bool:
    return is_equip_puppet_command_text(normalized_plain_text(event))


async def is_plant_message(event: MessageEvent) -> bool:
    return is_plant_command_text(normalized_plain_text(event))


async def is_item_use_message(event: MessageEvent) -> bool:
    return is_item_use_command_text(normalized_plain_text(event))


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


help_cmd = on_message(rule=Rule(is_help_message), priority=10, block=True)
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
talisman_draw_cmd = on_message(rule=Rule(is_talisman_draw_message), priority=10, block=True)
tianji_mystic_cmd = on_message(rule=Rule(is_tianji_mystic_message), priority=10, block=True)
dual_cultivation_cmd = on_message(rule=Rule(is_dual_cultivation_message), priority=10, block=True)
equip_puppet_cmd = on_message(rule=Rule(is_equip_puppet_message), priority=10, block=True)
plant_cmd = on_message(rule=Rule(is_plant_message), priority=10, block=True)
item_use_cmd = on_message(rule=Rule(is_item_use_message), priority=10, block=True)
mystic_entry_reply = on_message(rule=Rule(is_mystic_entry_reply), priority=8, block=True)
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
equip_method_cmd = on_message(rule=Rule(is_equip_method_message), priority=10, block=True)
equip_array_cmd = on_message(rule=Rule(is_equip_array_message), priority=10, block=True)
duel = on_message(rule=Rule(is_duel_message), priority=10, block=True)
chat_rank_counter = on_message(rule=Rule(is_group_chat_for_rank), priority=99, block=False)



@help_cmd.handle()
async def handle_help(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    await finish_panel(matcher, "\u4fee\u4ed9\u5e2e\u52a9", format_help_text(), icon="scroll")


@catalog_cmd.handle()
async def handle_catalog(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    if text in SPECIAL_ABILITY_CATALOG_TEXTS:
        ensure_combat_profile(record)
        await store.save_user(record)
        await finish_panel(matcher, "\u7279\u6b8a\u80fd\u529b\u56fe\u9274", special_ability_catalog_text(record), record, icon="ability")
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


@special_ability_cmd.handle()
async def handle_special_ability(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    ensure_combat_profile(record)
    text = normalized_plain_text(event)
    if text in SPECIAL_ABILITY_CATALOG_TEXTS:
        await store.save_user(record)
        await finish_panel(matcher, "特殊能力图鉴", special_ability_catalog_text(record), record, icon="ability")
    await store.save_user(record)
    await finish_panel(matcher, "我的特殊能力", special_ability_list_text(record), record, icon="ability")


@special_ability_learn_cmd.handle()
async def handle_special_ability_learn(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    item_index = parse_prefixed_index(normalized_plain_text(event), SPECIAL_ABILITY_LEARN_PREFIXES)
    if item_index is None:
        await finish_panel(matcher, "操作提示", "请发送“领悟特殊能力 1”。", record, icon="ability")
    success, message = learn_special_ability(record, item_index)
    if success:
        await store.save_user(record)
    await finish_panel(matcher, "特殊能力领悟" if success else "领悟失败", message, record, icon="ability" if success else "warning")


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
    if text in TASK_TEXTS:
        await finish_panel(matcher, "每日任务", daily_tasks_text(record, local_today()), record, icon="task")
    task_index = parse_prefixed_index(text, TASK_COMPLETE_PREFIXES)
    if task_index is None:
        await finish_panel(matcher, "每日任务", daily_tasks_text(record, local_today()), record, icon="task")
    success, message = complete_daily_task(record, task_index, local_today())
    if success:
        await store.save_user(record)
    await finish_panel(matcher, "每日任务" if success else "任务失败", message, record, icon="task" if success else "warning")


@shop_cmd.handle()
async def handle_shop(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    if text in SHOP_TEXTS:
        await finish_panel(matcher, "每日商店", format_shop_panel(record, local_today().isoformat()), record, icon="shop")
    buy_index = parse_shop_buy_index(text)
    if buy_index is not None:
        success, message = buy_shop_item(record, buy_index, local_today().isoformat())
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "每日商店" if success else "购买失败", message, record, icon="shop" if success else "warning")
    sale = parse_sell_item(text)
    if sale is not None:
        category, item_index = sale
        success, message = sell_reward(record, category, item_index)
        if success:
            await store.save_user(record)
        await finish_panel(matcher, "出售物品" if success else "出售失败", message, record, icon=item_icon_for_category(category) if success else "warning")
    await finish_panel(matcher, "每日商店", format_shop_panel(record, local_today().isoformat()), record, icon="shop")


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
    parsed = parse_item_use(normalized_plain_text(event))
    if parsed is None:
        await finish_panel(matcher, "操作提示", "请发送“使用丹药 1 / 使用符箓 1 / 炼化灵石 1 / 使用奇物 1”等格式。", record, icon="bag")
    category, item_index = parsed
    handlers = {
        "丹药": use_pill,
        "符箓": use_talisman,
        "灵石": refine_spirit_stone,
        "灵食": use_food,
        "奇物": use_curio,
        "杂物": identify_misc_item,
    }
    success, message = handlers[category](record, item_index)
    if success:
        await store.save_user(record)
    await finish_panel(
        matcher,
        f"{category}使用" if success else "操作失败",
        f"{message}\n当前境界：{record.realm if record.root else '未入门'}\n当前战力：{battle_power(record)}",
        record,
        icon=item_icon_for_category(category) if success else "warning",
    )


@mystic_entry.handle()
async def handle_mystic_entry(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    if record.mystic_realm:
        await finish_panel(matcher, "秘境探索", mystic_realm_options_text(record), record, icon="mystic")
    entries = draw_mystic_entrances(record)
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
    success, message = explore_mystic_realm(record, option_index, local_now())
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

    if result.pending_exp_applied:
        await send_panel(matcher, "日榜奖励", f"日榜暂存修为已汇入丹田，修炼进度+{result.pending_exp_applied}", result.record, icon="rank")

    if result.breakthrough_reward:
        await send_panel(matcher, "瓶颈机缘", f"额外获得 {reward_display_name(result.breakthrough_reward)}。", result.record, icon="breakthrough")

    if result.encounter and result.encounter.happened:
        await send_panel(matcher, "今日奇遇", result.encounter.message, result.record, icon="mystic")

    image = await build_signin_image(event, result)
    await send_image(matcher, image)

    if not result.already_signed and result.daily_tasks:
        await send_panel(matcher, "每日任务", daily_tasks_text(result.record, local_today()), result.record, icon="task")

    if not result.already_signed and result.record.fishing_chances > 0:
        pending_fishing_users[user_id] = time.monotonic() + PENDING_FISHING_TTL
        await send_panel(
            matcher,
            "诸天万界垂钓",
            f"检测到宿主有 {result.record.fishing_chances} 次诸天万界垂钓次数，是否垂钓？可累加进行 10 连抽。回复 是/好/y/十连。",
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
        await finish_panel(matcher, "诸天万界垂钓", "宿主暂无诸天万界垂钓次数，每次签到可获得 1 次。", record, icon="fishing")
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
        await finish_panel(matcher, "诸天万界垂钓", "已收起钓竿，诸天万界垂钓次数仍为你保留。", record, icon="fishing")
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
    await finish_panel(matcher, "历练面板", format_adventure_panel(record), record, icon="adventure")


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
        f"\u5339\u914d\u6210\u529f\uff1a{left_name} \u5bf9\u9635 {right_name}\n\u5df2\u8fdb\u51651\u5206\u949f\u51c6\u5907\u671f\uff0c\u7cfb\u7edf\u5c06\u79c1\u804a\u53cc\u65b9\u53d1\u9001\u4fee\u4e3a\u3001\u6218\u6280\u3001\u9635\u76d8\u548c\u7b26\u7b93\u51c6\u5907\u5361\u3002\n\u5f00\u6218\u540e 60 \u79d2\u5185\u53d1\u9001\u6218\u6280\u3001\u7279\u6b8a\u80fd\u529b\u3001\u8868\u60c5\u6216\u5373\u5174\u53f0\u8bcd\u3002",
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
    if text in UNEQUIP_TEXTS:
        message = unequip_artifact(record)
    else:
        artifact_index = parse_equip_index(text)
        if artifact_index is None:
            await finish_panel(matcher, "操作提示", "请发送“装备灵器 编号”，例如：装备灵器 1。", record, icon="artifact")
        success, message = equip_artifact(record, artifact_index)
        if not success:
            await finish_panel(matcher, "操作失败", message, record, icon="warning")
    await store.save_user(record)
    await finish_panel(matcher, "灵器装备", f"{message}\n当前战力：{battle_power(record)}", record, icon="artifact")


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
        await finish_panel(matcher, "诸天万界垂钓", "宿主暂无诸天万界垂钓次数。", record, icon="fishing")
    count = max(1, min(count, record.fishing_chances, 10))
    await send_panel(matcher, "诸天万界垂钓", f"正在为宿主进行{count}次垂钓。", record, icon="fishing")
    rewards = apply_fishing(record, count)
    pending_fishing_users.pop(user_id, None)
    await store.save_user(record)
    image = await build_fishing_image(event, record, rewards)
    await send_image(matcher, image)
