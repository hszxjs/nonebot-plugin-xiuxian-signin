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

from nonebot import get_bot, get_driver, logger, on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from .cards import render_fishing_card, render_signin_card, render_text_panel, set_font_paths
from .config import Config
from .domain import (
    CANCEL_WORDS,
    CONFIRM_WORDS,
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
    available_curios,
    available_foods,
    available_methods,
    available_misc_items,
    available_pills,
    available_plants,
    available_puppets,
    available_spirit_stones,
    available_talismans,
    battle_power,
    battle_summary,
    breakthrough_realm,
    breakthrough_status,

    buy_shop_item,

    choose_cultivation_route,

    choose_evil_cultivation,

    choose_faction_identity,

    complete_daily_task,

    daily_tasks_text,
    draw_mystic_entrances,

    draw_tianji_mystic_entrances,
    duel_records,
    equip_array,
    equip_artifact,
    equip_method,
    equip_puppet,
    explore_mystic_realm,
    fishing_count_from_text,
    identify_misc_item,
    method_power,
    mystic_realm_options_text,
    mystic_realm_title_from_entry,
    plant_spirit_plant,
    puppet_power,
    rank_reward_for,

    refine_pill_by_recipe,
    refine_spirit_stone,
    reward_display_name,

    route_status_text,

    sell_reward,

    shop_items_for_date,

    spirit_stone_text,
    start_mystic_realm,
    unequip_artifact,
    use_curio,
    use_food,
    use_pill,
    use_talisman,
)
from .storage import JsonStore

__version__ = "0.5.0"

PICMENU_NEXT_FUNCS = [
    {
        "func": "每日签到",
        "trigger_method": "签到 / 修仙签到 / 每日签到",
        "trigger_condition": "每日一次，首次签到会自动抽取个人灵根",
        "brief_des": "抽灵根、涨修为、查看境界经验条",
        "detail_des": (
            "发送 `签到` 后，机器人会以图片卡片返回 QQ 头像、签到次数、"
            "当前境界与经验进度。\n\n"
            "首次签到会抽取灵根，灵根由品阶、品质、属性组成；属性会影响卡片强调色，"
            "品阶和品质会影响升级所需经验与每日修炼涨幅。"
        ),
    },
    {
        "func": "我的修为",
        "trigger_method": "我的修为 / 修为 / 境界 / 灵根",
        "trigger_condition": "已完成至少一次签到",
        "brief_des": "查看当前灵根、境界、签到次数与经验进度",
        "detail_des": (
            "发送 `我的修为` 可查看当前修炼状态，不会消耗当天签到次数，"
            "也不会增加修炼进度。若还没有签到，日榜奖励会先暂存到待领取修为。"
        ),
    },
    {
        "func": "诸天万界垂钓",
        "trigger_method": "垂钓 / 垂钓 十连 / 签到后回复 是、好、y、十连",
        "trigger_condition": "每次成功签到获得 1 次垂钓机会，最多单次 10 连",
        "brief_des": "抽取灵器、丹药、功法、阵盘、灵材等修仙奖励",
        "detail_des": (
            "当宿主拥有垂钓次数时，可发送 `垂钓` 消耗 1 次，也可以发送 `垂钓 十连` "
            "一次消耗最多 10 次。\n\n"
            "功法与灵器会带有需求灵根；若宿主拥有对应主灵根或额外灵根，则显示契合。"
        ),
    },
    {
        "func": "每日话痨榜",
        "trigger_method": "群聊普通发言自动统计，每晚 22:00 自动发布",
        "trigger_condition": "群内当日有成员发言且尚未结算",
        "brief_des": "根据每日聊天次数排名发放修为和垂钓奖励",
        "detail_des": (
            "插件会按群分别统计每日发言次数。每天 22:00 后自动发布榜单并发奖："
            "第 1 名 +36 修为与 2 次垂钓，第 2 名 +28 修为与 1 次垂钓，"
            "第 3 名 +22 修为与 1 次垂钓，第 4-5 名 +16 修为，"
            "第 6-10 名 +10 修为。未觉醒灵根者会暂存修为，首次签到后领取。"
        ),
    },
    {
        "func": "群修为排行榜",
        "trigger_method": "修为榜 / 群修为榜",
        "trigger_condition": "群聊内使用；每天 22:00 话痨榜结算后也会同步发布",
        "brief_des": "查看本群修士按总修为排序的排行榜",
        "detail_des": (
            "插件会记录群内使用过修仙功能或参与日常聊天统计的成员。发送 `修为榜` 可查看本群总修为前十。"
            "每天 22:00 发布每日话痨榜并发奖后，会同步附带最新群修为榜。"
        ),
    },
    {
        "func": "历练与战力",
        "trigger_method": "历练 / 我的灵器 / 我的功法 / 我的阵盘 / 装备灵器 1 / 参悟功法 1 / 布置阵盘 1 / 战力 / pk @某人 / 战力榜",
        "trigger_condition": "灵器、功法、阵盘来自诸天万界垂钓；灵器与功法需求灵根必须契合",
        "brief_des": "装备灵器、参悟功法、布置阵盘、计算战力与战力榜",
        "detail_des": (
            "发送 `我的灵器` 查看可装备灵器，发送 `装备灵器 编号` 装备。灵器会按品阶、品质和灵根契合度提供战力。"
            "发送 `战力` 查看个人战力，发送 `pk @某人` 进行群内切磋，发送 `战力榜` 查看本群战力前十。"
        ),
    },

    {
        "func": "境界突破",
        "trigger_method": "突破 / 境界突破 / 查看突破",
        "trigger_condition": "境界达到圆满或巅峰，且背包中拥有对应突破道具",
        "brief_des": "使用筑基丹、小还丹、大还丹、元婴丹等道具突破瓶颈",
        "detail_des": (
            "发送 `突破` 会检查当前瓶颈道具并以图片面板返回结果。"
            "突破成功后会凝成境界品相，例如天道筑基、一品金丹等。"
        ),
    },
    {
        "func": "背包道具",
        "trigger_method": "背包 / 我的道具 / 使用丹药 1 / 使用符箓 1 / 炼化灵石 1 / 使用奇物 1",
        "trigger_condition": "道具来自垂钓、秘境、榜单奖励或突破机缘",
        "brief_des": "查看和使用丹药、符箓、灵石、灵食、奇物、杂物",
        "detail_des": (
            "背包会按类别以图片面板展示道具。丹药、灵食、灵石可增长修为；"
            "符箓按境界限制使用；奇物可能增加垂钓、修为或开出奖励。"
        ),
    },
    {
        "func": "秘境探索",
        "trigger_method": "秘境 / 查看秘境 / 回复 1-3 / 探索 1",
        "trigger_condition": "查看入口后 60 秒内选择，进入后共 10 次探索机会",
        "brief_des": "限时进入上古宗门遗址、兽潮或上古大能洞府",
        "detail_des": (
            "发送 `秘境` 会随机生成三个入口，60 秒内回复编号进入。"
            "进入后每次生成 5 个选项，发送 `探索 编号` 推进。坏结局会进入一天禁修期。"
        ),
    },
    {
        "func": "修炼路线与身份",
        "trigger_method": "修炼路线 / 选择路线 剑修 / 选择身份 天机阁弟子 / 选择身份 合欢宗弟子 / 选择邪修",
        "trigger_condition": "宗门身份分天机阁与合欢宗两系，弟子、长老、太上长老均有境界和身份签到天数门槛",
        "brief_des": "选择主修路线、邪修同修，以及天机阁或合欢宗身份令牌",
        "detail_des": (
            "发送 `修炼路线` 查看当前状态。身份选择格式：`选择身份 天机阁弟子`、`选择身份 天机阁长老`、"
            "`选择身份 天机阁太上长老`、`选择身份 合欢宗弟子`、`选择身份 合欢宗长老`、"
            "`选择身份 合欢宗太上长老`。天机阁提供天机秘境示警；合欢宗提供每日双修次数。"
        ),
    },
    {
        "func": "每日任务",
        "trigger_method": "每日任务 / 完成任务 1",
        "trigger_condition": "每天签到后自动生成 5 个任务",
        "brief_des": "完成每日任务获取修为、灵石与少量垂钓次数",
        "detail_des": "任务内容按当前境界生成，发送 `每日任务` 查看，发送 `完成任务 编号` 领取奖励。禁修期无法通过任务提升修为。",
    },
    {
        "func": "坊市商店与灵石",
        "trigger_method": "商店 / 购买 1 / 出售 丹药 1",
        "trigger_condition": "商店每日全服共通刷新 8 格商品",
        "brief_des": "使用灵石购买或出售背包道具，自动折算下品到极品灵石",
        "detail_des": "所有垂钓物品均有灵石价格。购买高于自身两大境界以上的物品会被限制；出售道具可回收部分灵石。",
    },
    {
        "func": "炼丹、天机秘境与双修",
        "trigger_method": "炼丹 / 炼丹 筑基丹 / 天机秘境 / 双修 @群成员 / 随机双修",
        "trigger_condition": "炼丹需炼丹师路线；天机秘境和双修需对应身份令牌",
        "brief_des": "炼制丹药、开启带坏结局提示的秘境、进行合欢宗特殊修炼",
        "detail_des": "炼丹消耗灵材、灵植和灵石；天机阁身份可按冷却开启特殊秘境；合欢宗身份每天拥有不同次数的双修机会。",
    },
    {
        "func": "每日奇遇",
        "trigger_method": "每日签到时自动判定",
        "trigger_condition": "每名宿主每天最多判定一次",
        "brief_des": "低概率改善资质或觉醒额外灵根",
        "detail_des": (
            "未到天阶极品前，每天有 1/365 概率经历奇遇；奇遇出现后有 50% 概率提升一档资质，"
            "优先提升品质，极品后升阶到上一阶下品。\n\n"
            "到达天阶极品后，每天改为以 `(1+n)/999` 概率觉醒一条随机额外灵根，"
            "`n` 为当前额外灵根数量。"
        ),
    },
]

__plugin_meta__ = PluginMetadata(
    name="修仙签到",
    description="以图片面板输出的修仙签到、灵根抽取、境界突破、历练道具、秘境探索与诸天万界垂钓插件。",
    usage=(
        "签到：每日签到，首次抽取灵根\n"
        "我的修为：查看当前修炼状态\n"
        "垂钓：消耗已有诸天万界垂钓次数\n"
        "每日话痨榜：群聊发言自动统计，每晚 22:00 发布并发奖\n"
        "修为榜：查看本群修为排行榜\n"
        "历练：装备灵器、参悟功法、布置阵盘、查看战力、PK 与战力榜\n"
        "背包：使用丹药、符箓、灵石、灵食、奇物和杂物\n"
        "秘境：60秒限时入口，进入后发送 探索 1-5"
    ),
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
STATUS_TEXTS = {"我的修为", "修为", "境界", "灵根"}
BREAKTHROUGH_TEXTS = {"突破", "境界突破", "破境", "查看突破", "突破状态"}
CULTIVATION_RANK_TEXTS = {"修为榜", "群修为榜", "境界榜"}
POWER_RANK_TEXTS = {"战力榜", "群战力榜"}
POWER_TEXTS = {"战力", "我的战力"}
ADVENTURE_TEXTS = {"历练", "历练面板", "历练帮助"}
ARTIFACT_LIST_TEXTS = {"灵器", "我的灵器", "灵器列表", "装备列表"}
METHOD_LIST_TEXTS = {"功法", "我的功法", "功法列表"}
ARRAY_LIST_TEXTS = {"阵盘", "我的阵盘", "阵盘列表", "阵法", "我的阵法"}
PUPPET_LIST_TEXTS = {"傀儡", "我的傀儡", "傀儡列表"}
PLANT_LIST_TEXTS = {"灵植", "我的灵植", "灵植列表"}
ITEM_LIST_TEXTS = {"道具", "我的道具", "背包", "物品", "我的物品"}
ROUTE_TEXTS = {"修炼路线", "路线", "身份", "身份令牌"}
TASK_TEXTS = {"每日任务", "任务", "我的任务"}
SHOP_TEXTS = {"商店", "坊市", "每日商店"}
ALCHEMY_TEXTS = {"炼丹", "丹方"}
TIANJI_MYSTIC_TEXTS = {"天机秘境", "天机探索", "特殊秘境"}
MYSTIC_ENTRY_TEXTS = {"秘境", "查看秘境", "秘境入口", "探查秘境"}
UNEQUIP_TEXTS = {"卸下灵器", "卸下装备"}
EQUIP_PREFIXES = ("装备灵器", "装备")
METHOD_EQUIP_PREFIXES = ("参悟功法", "修炼功法", "装备功法")
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
MYSTIC_EXPLORE_PREFIXES = ("探索", "秘境探索")
DUEL_PREFIXES = ("pk", "PK", "切磋", "挑战")
FISHING_TEXTS = ("诸天万界垂钓", "垂钓")
COMMAND_PREFIX_CHARS = "/!！.。"
PENDING_FISHING_TTL = 120
MYSTIC_ENTRY_TTL = 60
RANK_SETTLE_HOUR = 22
RANK_SETTLE_MINUTE = 0
pending_fishing_users: dict[str, float] = {}
pending_mystic_entries: dict[str, dict[str, Any]] = {}
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
    return Path(__file__).parent / "data"


store = JsonStore(get_data_dir())


def normalized_plain_text(event: MessageEvent) -> str:
    return event.message.extract_plain_text().strip().lstrip(COMMAND_PREFIX_CHARS).strip()


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
    categories = ("灵器", "功法", "丹药", "阵盘", "灵材", "符箓", "傀儡", "灵植", "灵石", "杂物", "奇物", "灵食")
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
        or text in MYSTIC_ENTRY_TEXTS
        or is_route_command_text(text)
        or is_task_command_text(text)
        or is_shop_command_text(text)
        or is_alchemy_command_text(text)
        or is_tianji_mystic_command_text(text)
        or is_dual_cultivation_command_text(text)
        or text in UNEQUIP_TEXTS
        or parse_fishing_arg(text) is not None
        or is_equip_command_text(text)
        or is_equip_method_command_text(text)
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
    methods = available_methods(record)
    lines = ["【我的功法】"]
    lines.append(f"当前功法：{reward_display_name(record.equipped_method) if record.equipped_method else '未参悟功法'}")
    if not methods:
        lines.append("暂无功法，进行诸天万界垂钓有机会获得。")
        return "\n".join(lines)
    for index, method in enumerate(methods, start=1):
        required = method.get("required_attribute")
        compatible = "可参悟" if not required or required in record.root_attributes else "灵根不契合"
        bonus = method_power(method, record)
        lines.append(
            f"{index}. {reward_display_name(method)}，需求{required or '无'}灵根，"
            f"{compatible}，战力+{bonus}"
        )
    lines.append("发送“参悟功法 编号”即可生效；功法会提升签到和聊天获取修为。")
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
    lines = ["【背包道具】"]
    lines.append(f"灵石储备：{spirit_stone_text(record.spirit_stones)}；垂钓次数：{record.fishing_chances}")
    summary = battle_summary(record)
    if summary.get("cultivation_lock"):
        lines.append(f"状态：{summary['cultivation_lock']}")
    sections = [
        ("丹药", available_pills(record), "用法：使用丹药 编号；突破道具请发送“突破”"),
        ("符箓", available_talismans(record), "用法：使用符箓 编号"),
        ("灵石", available_spirit_stones(record), "用法：炼化灵石 编号"),
        ("灵材", available_materials(record), "用法：炼丹材料，可通过炼丹消耗；出售灵材 编号可换灵石"),
        ("灵食", available_foods(record), "用法：使用灵食 编号"),
        ("奇物", available_curios(record), "用法：使用奇物 编号；突破道具请发送“突破”"),
        ("杂物", available_misc_items(record), "用法：鉴定杂物 编号"),
    ]
    for title, items, usage in sections:
        lines.append("")
        append_item_lines(lines, title, items, usage)
    return "\n".join(lines)


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
        f"【{nickname or '宿主'}的战力】",
        f"战力：{summary['power']}",
        f"境界：{summary['realm']}",
        f"境界品相：{summary['realm_quality']}",
        f"累计修为：{summary['total_exp']}",
        f"灵器：{summary['artifact']}",
        f"功法：{summary['method']}",
        f"阵盘：{summary['array']}（{summary['array_multiplier']:.1f}x）",
        f"傀儡：{summary['puppet']}（战力+{summary['puppet_power']}）",
        f"灵植：{summary['plant']}",
        f"灵石储备：{summary['spirit_stones_text']}",
        f"修炼路线：{summary['route']}",
        f"身份令牌：{summary['identity']}",
        f"天机秘境：{summary['tianji_status']}；双修次数：{summary['hehuan_remaining']}",
        f"秘境：{summary['mystic_realm']}",
        f"装备加成：{summary['equipment_power']}",
    ]
    if summary.get("is_bottleneck"):
        lines.append(f"当前瓶颈：需 {summary['breakthrough_required']} 才能突破")
    if summary.get("cultivation_lock"):
        lines.append(f"禁修状态：{summary['cultivation_lock']}")
    return "\n".join(lines)


def format_adventure_panel(record) -> str:
    summary = battle_summary(record)
    return "\n".join(
        [
            "【历练】",
            f"当前战力：{summary['power']}",
            f"当前灵器：{summary['artifact']}",
            f"当前功法：{summary['method']}",
            f"当前阵盘：{summary['array']}（{summary['array_multiplier']:.1f}x）",
            f"当前傀儡：{summary['puppet']}",
            f"当前灵植：{summary['plant']}",
            f"灵石储备：{summary['spirit_stones_text']}",
            f"修炼路线：{summary['route']}",
            f"身份令牌：{summary['identity']}（天机秘境：{summary['tianji_status']}，双修：{summary['hehuan_remaining']}）",
            "修炼路线 / 选择路线 剑修 / 选择身份 天机阁弟子 / 选择身份 合欢宗弟子",
            "每日任务 / 完成任务 1 / 商店 / 购买 1 / 出售 丹药 1",
            "炼丹 / 炼丹 筑基丹 / 天机秘境 / 双修@群友 / 随机双修",
            "我的灵器 / 我的功法 / 我的阵盘：查看可用装备",
            "我的傀儡 / 我的灵植 / 背包：查看历练资源",
            "装备灵器 1 / 参悟功法 1 / 布置阵盘 1",
            "装备傀儡 1 / 栽种灵植 1 / 使用丹药 1 / 炼化灵石 1",
            "秘境：查看60秒限时秘境入口；探索 1：推进当前秘境",
            "突破：境界圆满后使用突破道具",
            "战力 / pk @对方 / 战力榜：查看战力与切磋",
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


async def is_route_message(event: MessageEvent) -> bool:
    return is_route_command_text(normalized_plain_text(event))


async def is_task_message(event: MessageEvent) -> bool:
    return is_task_command_text(normalized_plain_text(event))


async def is_shop_message(event: MessageEvent) -> bool:
    return is_shop_command_text(normalized_plain_text(event))


async def is_alchemy_message(event: MessageEvent) -> bool:
    return is_alchemy_command_text(normalized_plain_text(event))


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


async def is_equip_array_message(event: MessageEvent) -> bool:
    return is_equip_array_command_text(normalized_plain_text(event))


async def is_duel_message(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) and is_duel_command_text(normalized_plain_text(event))


signin = on_message(rule=Rule(is_signin_message), priority=10, block=True)
status = on_message(rule=Rule(is_status_message), priority=10, block=True)
breakthrough_cmd = on_message(rule=Rule(is_breakthrough_message), priority=10, block=True)
puppet_list = on_message(rule=Rule(is_puppet_list_message), priority=10, block=True)
plant_list = on_message(rule=Rule(is_plant_list_message), priority=10, block=True)
item_list = on_message(rule=Rule(is_item_list_message), priority=10, block=True)
route_cmd = on_message(rule=Rule(is_route_message), priority=10, block=True)
task_cmd = on_message(rule=Rule(is_task_message), priority=10, block=True)
shop_cmd = on_message(rule=Rule(is_shop_message), priority=10, block=True)
alchemy_cmd = on_message(rule=Rule(is_alchemy_message), priority=10, block=True)
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
array_list = on_message(rule=Rule(is_array_list_message), priority=10, block=True)
equip_artifact_cmd = on_message(rule=Rule(is_equip_artifact_message), priority=10, block=True)
equip_method_cmd = on_message(rule=Rule(is_equip_method_message), priority=10, block=True)
equip_array_cmd = on_message(rule=Rule(is_equip_array_message), priority=10, block=True)
duel = on_message(rule=Rule(is_duel_message), priority=10, block=True)
chat_rank_counter = on_message(rule=Rule(is_group_chat_for_rank), priority=99, block=False)


@breakthrough_cmd.handle()
async def handle_breakthrough(matcher: Matcher, event: MessageEvent) -> None:
    await remember_group_member(event)
    record = await store.get_user(event.get_user_id())
    text = normalized_plain_text(event)
    if text in {"突破", "境界突破", "破境"}:
        success, message = breakthrough_realm(record)
        if success:
            await store.save_user(record)
        await finish_panel(
            matcher,
            "境界突破" if success else "突破状态",
            message,
            record,
            icon="breakthrough" if success else "warning",
        )
    await finish_panel(matcher, "突破状态", breakthrough_status(record), record, icon="breakthrough")


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
    success, message = explore_mystic_realm(record, option_index, local_today())
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
