from __future__ import annotations

import json
import random
import re
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent
CHARACTER_MANIFEST_PATH = ROOT / "assets" / "character_portraits" / "manifest.json"
FOLLOWER_LABEL = "随从"
RECRUIT_LOCATION = "任务堂"

BEAST_REALM_TIERS = ["炼气期", "筑基期", "金丹期", "元婴期", "化神期", "炼虚期"]
BEAST_REALM_MAX_PLAYERS = 4
BEAST_REALM_MAX_BOARD = 7
BEAST_REALM_SHOP_SIZE = 5
BEAST_REALM_WAIT_SECONDS = 180
BEAST_REALM_MAX_TURNS = 8
BEAST_REALM_START_HEALTH = 36
BEAST_REALM_HAND_LIMIT = 10
BEAST_REALM_DEFAULT_CARD_COPIES = 10
BEAST_REALM_CARD_POOL_COPIES = BEAST_REALM_DEFAULT_CARD_COPIES
BEAST_REALM_DISCOVER_CHOICES = 3
BEAST_REALM_LEADER_CHOICES = 3

BEAST_REALM_LEADERS: list[dict[str, Any]] = [
    {"id": "br_leader_001", "name": "青岚兽主", "health": 42, "skill": "每回合开始：随机友方随从攻击+1、防御+1。", "rules": {"round_start": [{"kind": "random_ally_stats", "attack": 1, "defense": 1}]}},
    {"id": "br_leader_002", "name": "赤霄战魁", "health": 34, "skill": "招募随从后：该随从攻击+2。", "rules": {"after_buy": [{"kind": "source_stats", "attack": 2}]}},
    {"id": "br_leader_003", "name": "玄龟镇守", "health": 52, "skill": "每回合开始：友方全体获得护盾+2；受到伤害-1。", "rules": {"round_start": [{"kind": "team_shield", "shield": 2}], "damage_taken": [{"kind": "damage_reduce", "amount": 1}]}},
    {"id": "br_leader_004", "name": "万宝堂主", "health": 38, "skill": "每回合开始：额外获得1灵石。", "rules": {"round_start": [{"kind": "leader_gold", "amount": 1}]}},
    {"id": "br_leader_005", "name": "天机观主", "health": 32, "skill": "每回合开始：下一战随机敌方随从攻击-2、防御-1。", "rules": {"round_start": [{"kind": "next_enemy_weaken", "attack": -2, "defense": -1}]}},
    {"id": "br_leader_006", "name": "灵植峰主", "health": 45, "skill": "每回合开始：随机友方防御+2；出售随从后生命+2。", "rules": {"round_start": [{"kind": "random_ally_stats", "defense": 2}], "after_sell": [{"kind": "leader_health", "amount": 2}]}},
    {"id": "br_leader_007", "name": "雷狱剑首", "health": 36, "skill": "施放法术后：随机友方攻击+2；战斗开始时最左随从获得先攻。", "rules": {"after_spell": [{"kind": "random_ally_stats", "attack": 2}], "battle_start": [{"kind": "battle_first_keyword", "keyword": "先攻"}]}},
    {"id": "br_leader_008", "name": "阵箓宗师", "health": 40, "skill": "对友方施放法术后：目标获得护盾+2，并布置玄丝反阵。", "rules": {"after_spell": [{"kind": "target_shield", "shield": 2}, {"kind": "target_trap", "trap": "玄丝反阵"}]}},
    {"id": "br_leader_009", "name": "山海御主", "health": 46, "skill": "招募妖兽随从后：该随从攻击+2、防御+2。", "rules": {"after_buy": [{"kind": "source_if_faction_stats", "faction": "妖兽", "attack": 2, "defense": 2}]}},
    {"id": "br_leader_010", "name": "散修盟主", "health": 41, "skill": "招募随从后：返还1灵石。", "rules": {"after_buy": [{"kind": "leader_gold", "amount": 1}]}},
    {"id": "br_leader_011", "name": "佛光院主", "health": 48, "skill": "每回合开始：友方全体防御+1，并获得护盾+1。", "rules": {"round_start": [{"kind": "team_stats", "defense": 1}, {"kind": "team_shield", "shield": 1}]}},
    {"id": "br_leader_012", "name": "黄泉魁首", "health": 30, "skill": "出售随从后：友方全体攻击+2。", "rules": {"after_sell": [{"kind": "team_stats", "attack": 2}]}},
    {"id": "br_leader_013", "name": "邪神祭司", "health": 28, "skill": "每回合开始：随机友方攻击+3。", "rules": {"round_start": [{"kind": "random_ally_stats", "attack": 3}]}},
    {"id": "br_leader_014", "name": "伪神执政", "health": 37, "skill": "提升任务堂后：友方全体攻击+2、防御+2。", "rules": {"after_upgrade": [{"kind": "team_stats", "attack": 2, "defense": 2}]}},
    {"id": "br_leader_015", "name": "魔神将座", "health": 35, "skill": "战斗开始时：友方全体攻击+2。", "rules": {"battle_start": [{"kind": "battle_team_stats", "attack": 2}]}},
    {"id": "br_leader_016", "name": "天魔行者", "health": 33, "skill": "每回合开始：下一战随机敌方随从攻击-3、防御-2。", "rules": {"round_start": [{"kind": "next_enemy_weaken", "attack": -3, "defense": -2}]}},
    {"id": "br_leader_017", "name": "系统宿主", "health": 36, "skill": "每回合开始：获得1灵石，并使随机友方攻击+1。", "rules": {"round_start": [{"kind": "leader_gold", "amount": 1}, {"kind": "random_ally_stats", "attack": 1}]}},
    {"id": "br_leader_018", "name": "青莲剑君", "health": 34, "skill": "战斗开始时：最左随从攻击+4，并获得先攻。", "rules": {"battle_start": [{"kind": "battle_first_stats", "attack": 4}, {"kind": "battle_first_keyword", "keyword": "先攻"}]}},
    {"id": "br_leader_019", "name": "丹鼎峰主", "health": 44, "skill": "对友方施放法术后：目标攻击+1、防御+1，且自身生命+1。", "rules": {"after_spell": [{"kind": "target_stats", "attack": 1, "defense": 1}, {"kind": "leader_health", "amount": 1}]}},
    {"id": "br_leader_020", "name": "月影潜君", "health": 39, "skill": "招募随从后：该随从护盾+2；受到伤害-2。", "rules": {"after_buy": [{"kind": "source_shield", "shield": 2}], "damage_taken": [{"kind": "damage_reduce", "amount": 2}]}},
]
BEAST_REALM_LEADER_BY_ID = {str(leader["id"]): leader for leader in BEAST_REALM_LEADERS}

BEAST_REALM_ENTRY_TEXTS = {
    "御兽秘境",
    "御兽秘境帮助",
    "御兽秘境图鉴",
    "御兽卡牌",
    "御兽卡牌图鉴",
    "随从卡牌",
    "随从卡牌图鉴",
    "御兽秘境开局",
    "御兽秘境PVE",
    "御兽秘境PVP",
    "御兽秘境状态",
    "加入御兽秘境",
    "退出御兽秘境",
    "开始御兽秘境",
    "结束御兽秘境",
    "御兽结算",
}

BEAST_REALM_PRIVATE_TEXTS = {
    "御兽峰",
    "任务堂",
    "任务堂手牌",
    "任务堂战局",
    "随从手牌",
    "御兽手牌",
    "随从战局",
    "御兽战局",
    "御兽秘境图鉴",
    "御兽卡牌",
    "御兽卡牌图鉴",
    "随从卡牌",
    "随从卡牌图鉴",
    "刷新",
    "刷新任务堂",
    "刷新御兽峰",
    "冻结",
    "冻结任务堂",
    "冻结御兽峰",
    "解冻",
    "解冻任务堂",
    "解冻御兽峰",
    "升峰",
    "升堂",
    "提升任务堂",
    "提升御兽峰",
    "完成招募",
    "结束招募",
    "准备",
    "峰主",
    "峰主选择",
    "我的峰主",
    "御兽秘境",
    "御兽秘境1V2",
    "御兽秘境 1V2",
    "御兽秘境单人",
    "单人御兽秘境",
    "开始御兽秘境",
    "结束御兽秘境",
}

BEAST_REALM_PRIVATE_PREFIXES = (
    "购买",
    "招募",
    "买入",
    "施法",
    "使用法术",
    "使用",
    "出售",
    "卖出",
    "调整",
    "移动",
    "峰主",
    "选择峰主",
    "选择",
    "发现",
    "上阵",
    "打出",
    "召唤",
)


def effect_text(trigger: str, text: str) -> str:
    return f"{trigger}：{text}"


def beast_card(
    card_id: str,
    portrait_id: str,
    name: str,
    tier: int,
    attack: int,
    defense: int,
    faction: str,
    element: str,
    effect: str,
    rules: dict[str, list[dict[str, Any]]],
    story: str,
) -> dict[str, Any]:
    return {
        "kind": "beast",
        "id": card_id,
        "portrait_id": portrait_id,
        "name": name,
        "tier": tier,
        "realm": BEAST_REALM_TIERS[tier - 1],
        "attack": attack,
        "defense": defense,
        "faction": faction,
        "element": element,
        "effect": effect,
        "rules": rules,
        "story": story,
    }


def spell_card(
    card_id: str,
    name: str,
    tier: int,
    category: str,
    effect: str,
    target: str,
    rules: list[dict[str, Any]],
    story: str,
) -> dict[str, Any]:
    return {
        "kind": "spell",
        "id": card_id,
        "name": name,
        "tier": tier,
        "realm": BEAST_REALM_TIERS[tier - 1],
        "category": category,
        "effect": effect,
        "target": target,
        "rules": rules,
        "story": story,
    }


BEAST_REALM_CARDS: list[dict[str, Any]] = [
    beast_card(
        "br_qi_001",
        "beast_001",
        "赤焰妖虎",
        1,
        3,
        2,
        "远荒",
        "火",
        effect_text("加入战局", "自身攻击+1；若场上已有火系御兽，再获得防御+1"),
        {"join": [{"kind": "self_stats", "attack": 1}, {"kind": "self_if_element", "element": "火", "defense": 1}]},
        "幼虎额间生赤纹，最爱在兽潮前沿试爪，火脉越盛越不肯退。",
    ),
    beast_card(
        "br_qi_002",
        "beast_002",
        "玄霜蛟王",
        1,
        2,
        4,
        "真龙遗脉",
        "水",
        effect_text("阵营效果", "同为真龙遗脉的御兽防御+1"),
        {"aura": [{"kind": "aura_faction", "faction": "真龙遗脉", "defense": 1}]},
        "尚未成蛟时已懂盘水为阵，寒息覆鳞，护住同脉幼兽。",
    ),
    beast_card(
        "br_qi_003",
        "beast_003",
        "碧鳞灵猿",
        1,
        2,
        3,
        "山海灵族",
        "木",
        effect_text("每回合开始", "随机友方随从攻击+1"),
        {"start": [{"kind": "random_ally_stats", "attack": 1}]},
        "灵猿会把捡来的青果分给同伴，果核落地便生一缕战意。",
    ),
    beast_card(
        "br_qi_004",
        "beast_004",
        "噬月玄龟",
        1,
        1,
        6,
        "搬山",
        "土",
        effect_text("持续效果", "自身拥有护卫；被攻击时优先承受伤害"),
        {"join": [{"kind": "keyword", "keyword": "护卫"}]},
        "玄龟背纹似缺月，慢吞吞挡在阵前时，反而最让人安心。",
    ),
    beast_card(
        "br_qi_005",
        "beast_005",
        "裂山魔狼",
        1,
        4,
        2,
        "远荒",
        "金",
        effect_text("离开时", "使随机友方随从攻击+1"),
        {"leave": [{"kind": "random_ally_stats", "attack": 1}]},
        "魔狼断齿仍会长啸，余音催得同伴扑向猎物喉间。",
    ),
    beast_card(
        "br_zhuji_001",
        "beast_006",
        "幽冥狮鹫",
        2,
        5,
        4,
        "幽冥",
        "暗",
        effect_text("离开时", "对敌方前排造成3点伤害"),
        {"leave": [{"kind": "enemy_front_damage", "damage": 3}]},
        "狮鹫死羽会化为阴火，坠入敌阵后才真正开始燃烧。",
    ),
    beast_card(
        "br_zhuji_002",
        "beast_007",
        "金瞳蛇君",
        2,
        4,
        5,
        "毒泽",
        "金",
        effect_text("加入战局", "使左侧御兽攻击+2；右侧御兽防御+2"),
        {"join": [{"kind": "adjacent_stats", "left_attack": 2, "right_defense": 2}]},
        "金瞳一开，左右兽影皆按它的节奏吐息、潜伏、暴起。",
    ),
    beast_card(
        "br_zhuji_003",
        "beast_008",
        "雷角古象",
        2,
        3,
        8,
        "搬山",
        "雷",
        effect_text("阵营效果", "搬山御兽攻击+1、防御+1"),
        {"aura": [{"kind": "aura_faction", "faction": "搬山", "attack": 1, "defense": 1}]},
        "古象一步一雷，队伍只要跟着它走，阵脚便不会散。",
    ),
    beast_card(
        "br_zhuji_004",
        "beast_009",
        "青翼鹰王",
        2,
        6,
        3,
        "天羽",
        "风",
        effect_text("持续效果", "自身拥有先攻；每回合开始自身攻击+1"),
        {"join": [{"kind": "keyword", "keyword": "先攻"}], "start": [{"kind": "self_stats", "attack": 1}]},
        "青翼划开云岚，最先落下的不是影子，而是爪风。",
    ),
    beast_card(
        "br_zhuji_005",
        "beast_010",
        "血纹蜃兽",
        2,
        4,
        6,
        "幻潮",
        "水",
        effect_text("加入战局", "随机友方获得护盾+4"),
        {"join": [{"kind": "random_ally_shield", "shield": 4}]},
        "蜃气像一层旧梦，挡住了第一口咬来的凶光。",
    ),
    beast_card(
        "br_jindan_001",
        "beast_011",
        "吞星魔猿",
        3,
        8,
        7,
        "山海灵族",
        "暗",
        effect_text("离开时", "友方全体攻击+1"),
        {"leave": [{"kind": "team_stats", "attack": 1}]},
        "魔猿倒下时仍会捶碎星砂，碎光落在同伴拳锋上。",
    ),
    beast_card(
        "br_jindan_002",
        "beast_012",
        "搬山荒犼",
        3,
        6,
        10,
        "搬山",
        "土",
        effect_text("加入战局", "自身获得护盾+8"),
        {"join": [{"kind": "self_shield", "shield": 8}]},
        "荒犼披山为甲，低吼时连任务堂的石阶都跟着下沉。",
    ),
    beast_card(
        "br_jindan_003",
        "beast_013",
        "银翼雷鹏",
        3,
        9,
        5,
        "天羽",
        "雷",
        effect_text("每回合开始", "天羽御兽攻击+1"),
        {"start": [{"kind": "faction_stats", "faction": "天羽", "attack": 1}]},
        "雷鹏绕峰一周，羽声如鼓，唤得所有飞兽振翅。",
    ),
    beast_card(
        "br_jindan_004",
        "beast_014",
        "黑渊骨龙",
        3,
        7,
        8,
        "真龙遗脉",
        "暗",
        effect_text("阵营效果", "真龙遗脉攻击+2"),
        {"aura": [{"kind": "aura_faction", "faction": "真龙遗脉", "attack": 2}]},
        "骨龙未必记得生前来处，却记得如何让龙血沸腾。",
    ),
    beast_card(
        "br_jindan_005",
        "beast_015",
        "紫电火麟",
        3,
        10,
        6,
        "远荒",
        "火",
        effect_text("加入战局", "友方火系御兽攻击+2"),
        {"join": [{"kind": "element_stats", "element": "火", "attack": 2}]},
        "火麟踏过的紫电会留在鳞片间，成群时像一片雷火林。",
    ),
    beast_card(
        "br_yuanying_001",
        "beast_016",
        "白骨冰蟒",
        4,
        10,
        12,
        "幽冥",
        "冰",
        effect_text("被动", "自身拥有护卫；离开时敌方前排攻击-3"),
        {"join": [{"kind": "keyword", "keyword": "护卫"}], "leave": [{"kind": "enemy_front_stats", "attack": -3}]},
        "冰蟒盘骨成墙，崩碎时寒意仍会咬住敌人的筋骨。",
    ),
    beast_card(
        "br_yuanying_002",
        "beast_017",
        "青冥山魈",
        4,
        12,
        9,
        "山海灵族",
        "木",
        effect_text("每回合开始", "友方全体防御+1"),
        {"start": [{"kind": "team_stats", "defense": 1}]},
        "山魈在晨雾里敲木鼓，鼓声会让伤口结出青藤。",
    ),
    beast_card(
        "br_yuanying_003",
        "beast_018",
        "远荒血蝠",
        4,
        13,
        8,
        "远荒",
        "暗",
        effect_text("持续效果", "每当友方离开战局，自身攻击+2、防御+1"),
        {"ally_leave": [{"kind": "self_stats", "attack": 2, "defense": 1}]},
        "血蝠听见同伴濒死的心跳，便会循声化作一道红影。",
    ),
    beast_card(
        "br_yuanying_004",
        "beast_019",
        "血月天狼",
        4,
        14,
        10,
        "远荒",
        "火",
        effect_text("阵营效果", "远荒御兽攻击+2；若带护盾再防御+1"),
        {"aura": [{"kind": "aura_faction", "faction": "远荒", "attack": 2, "shielded_defense": 1}]},
        "月色越红，狼群越沉默；沉默过后便是齐扑。",
    ),
    beast_card(
        "br_yuanying_005",
        "beast_020",
        "玄甲玄蛛",
        4,
        9,
        15,
        "毒泽",
        "土",
        effect_text("加入战局", "给自身布置一次玄丝反阵"),
        {"join": [{"kind": "self_trap", "trap": "玄丝反阵"}]},
        "玄蛛吐丝不为捕食，只为等敌人自己撞上阵眼。",
    ),
    beast_card(
        "br_huashen_001",
        "beast_021",
        "九首石犀",
        5,
        16,
        18,
        "搬山",
        "土",
        effect_text("阵营效果", "友方全体防御+3"),
        {"aura": [{"kind": "aura_team", "defense": 3}]},
        "九首同望一处时，整支兽群都像披上了山岳。",
    ),
    beast_card(
        "br_huashen_002",
        "beast_022",
        "独角鬼面獒",
        5,
        18,
        14,
        "幽冥",
        "暗",
        effect_text("离开时", "对敌方前排造成8点伤害"),
        {"leave": [{"kind": "enemy_front_damage", "damage": 8}]},
        "鬼面獒一生只认一次主，倒下时也会替主人咬完最后一口。",
    ),
    beast_card(
        "br_huashen_003",
        "beast_023",
        "金羽碧眼蟾",
        5,
        15,
        16,
        "毒泽",
        "金",
        effect_text("每回合开始", "随机敌方在下一战攻击-4"),
        {"start": [{"kind": "next_enemy_weaken", "attack": -4}]},
        "碧眼蟾的金粉藏在袖风里，尚未开战便已落入敌阵。",
    ),
    beast_card(
        "br_huashen_004",
        "beast_024",
        "寒狱吞月狐",
        5,
        17,
        15,
        "幻潮",
        "冰",
        effect_text("加入战局", "友方全体获得护盾+4"),
        {"join": [{"kind": "team_shield", "shield": 4}]},
        "吞月狐把月霜含在齿间，吐息一散，整座阵列都冷了下来。",
    ),
    beast_card(
        "br_huashen_005",
        "beast_025",
        "离火裂海鲸",
        5,
        20,
        13,
        "幻潮",
        "火",
        effect_text("加入战局", "火系与水系友方攻击+2、防御+2"),
        {"join": [{"kind": "multi_element_stats", "elements": ["火", "水"], "attack": 2, "defense": 2}]},
        "裂海鲸一啸，水火分潮，竟能把两种灵力推向同一处锋刃。",
    ),
    beast_card(
        "br_lianxu_001",
        "beast_026",
        "沧溟赤羽鸾",
        6,
        24,
        22,
        "天羽",
        "火",
        effect_text("每回合开始", "友方全体攻击+2、防御+2"),
        {"start": [{"kind": "team_stats", "attack": 2, "defense": 2}]},
        "赤羽鸾衔来沧溟日火，落在峰顶便是一轮小太阳。",
    ),
    beast_card(
        "br_lianxu_002",
        "beast_027",
        "黄泉铁甲蜈",
        6,
        21,
        26,
        "毒泽",
        "土",
        effect_text("被攻击时", "自带一次黄泉反阵；离开时敌方全体攻击-2"),
        {"join": [{"kind": "self_trap", "trap": "黄泉反阵"}], "leave": [{"kind": "enemy_team_stats", "attack": -2}]},
        "铁甲蜈行过之地，土壤会记住黄泉的腥气。",
    ),
    beast_card(
        "br_lianxu_003",
        "beast_028",
        "风吼青鳞鲛",
        6,
        23,
        23,
        "真龙遗脉",
        "风",
        effect_text("阵营效果", "真龙遗脉与天羽御兽攻击+3"),
        {"aura": [{"kind": "aura_factions", "factions": ["真龙遗脉", "天羽"], "attack": 3}]},
        "青鳞鲛歌声一起，龙影与羽影都被风托上高处。",
    ),
    beast_card(
        "br_lianxu_004",
        "beast_029",
        "铁脊风翼豹",
        6,
        27,
        18,
        "天羽",
        "风",
        effect_text("持续效果", "自身拥有先攻；击破敌人后攻击+4"),
        {"join": [{"kind": "keyword", "keyword": "先攻"}], "kill": [{"kind": "self_stats", "attack": 4}]},
        "风翼豹从不回头确认猎物是否倒下，因为下一次扑击已经开始。",
    ),
    beast_card(
        "br_lianxu_005",
        "beast_030",
        "玉鳞古蜥",
        6,
        22,
        28,
        "山海灵族",
        "木",
        effect_text("加入战局", "友方全体获得护盾+6；山海灵族额外防御+3"),
        {"join": [{"kind": "team_shield", "shield": 6}, {"kind": "faction_stats", "faction": "山海灵族", "defense": 3}]},
        "古蜥静卧如玉山，身上脱落的一枚鳞都可镇住一角阵脚。",
    ),
]

BEAST_REALM_SPELLS: list[dict[str, Any]] = [
    spell_card("br_spell_001", "青木培元丹", 1, "丹药", "目标随从攻击+1、防御+3。", "ally", [{"kind": "target_stats", "attack": 1, "defense": 3}], "温养筋骨的小丹，适合刚入峰的幼兽。"),
    spell_card("br_spell_002", "赤髓暴血丹", 1, "丹药", "目标随从攻击+4。", "ally", [{"kind": "target_stats", "attack": 4}], "药力刚烈，短时间内会让爪牙赤红如炭。"),
    spell_card("br_spell_003", "金光护身符", 1, "符箓", "目标随从获得护盾+5。", "ally", [{"kind": "target_shield", "shield": 5}], "金纹一亮，先挡一劫。"),
    spell_card("br_spell_004", "小五行醒脉丹", 2, "丹药", "随机3个友方随从攻击+1、防御+1。", "team", [{"kind": "random_many_stats", "count": 3, "attack": 1, "defense": 1}], "五色药气会自己寻找尚未舒展的兽脉。"),
    spell_card("br_spell_005", "玄甲镇魂符", 2, "符箓", "友方全体护盾+2。", "team", [{"kind": "team_shield", "shield": 2}], "符胆沉稳，最适合开战前压住阵脚。"),
    spell_card("br_spell_006", "风雷疾行术", 2, "神通", "目标随从获得先攻，并攻击+2。", "ally", [{"kind": "target_keyword", "keyword": "先攻"}, {"kind": "target_stats", "attack": 2}], "风托其身，雷催其爪。"),
    spell_card("br_spell_007", "炎狱反阵", 2, "阵法", "布置在目标随从上：被攻击时对攻击者造成6点反击伤害。", "ally", [{"kind": "target_trap", "trap": "炎狱反阵"}], "阵纹藏在鳞下，敌爪落下时才见火狱。"),
    spell_card("br_spell_008", "玄水回阵", 3, "阵法", "布置在目标随从上：被攻击时自身回复8点防御。", "ally", [{"kind": "target_trap", "trap": "玄水回阵"}], "水纹绕身一周，伤口会像潮汐般回拢。"),
    spell_card("br_spell_009", "龙虎金元丹", 3, "丹药", "友方全体攻击+2。", "team", [{"kind": "team_stats", "attack": 2}], "丹中有龙虎争鸣，吞下便知何为锐气。"),
    spell_card("br_spell_010", "千叶生机散", 3, "丹药", "友方全体防御+2。", "team", [{"kind": "team_stats", "defense": 2}], "青叶散开，连旧伤都长出新肉。"),
    spell_card("br_spell_011", "裂魂破甲符", 3, "符箓", "下一战随机敌方御兽攻击-3、防御-3。", "enemy", [{"kind": "next_enemy_weaken", "attack": -3, "defense": -3}], "不直接杀敌，只把敌人的护身灵光撕开一线。"),
    spell_card("br_spell_012", "星火燎原诀", 4, "神通", "火系友方攻击+4；非火系友方攻击+1。", "team", [{"kind": "element_stats", "element": "火", "attack": 4}, {"kind": "non_element_stats", "element": "火", "attack": 1}], "一枚星火落地，整座兽阵都知道该向哪里燃烧。"),
    spell_card("br_spell_013", "五行锁灵阵", 4, "阵法", "布置在目标随从上：被攻击时使攻击者攻击-5。", "ally", [{"kind": "target_trap", "trap": "五行锁灵阵"}], "阵眼不伤皮肉，只锁敌人一口灵机。"),
    spell_card("br_spell_014", "天罡护命符", 4, "符箓", "目标随从防御+8，并获得护卫。", "ally", [{"kind": "target_stats", "defense": 8}, {"kind": "target_keyword", "keyword": "护卫"}], "天罡符落在额心，便要替同伴守一次命。"),
    spell_card("br_spell_015", "九转化形丹", 4, "丹药", "目标随从攻击+5、防御+5；若境界低于任务堂等级，额外+2/+2。", "ally", [{"kind": "target_stats", "attack": 5, "defense": 5}, {"kind": "target_if_below_peak", "attack": 2, "defense": 2}], "九转之后，兽骨会短暂显出更高境界的影子。"),
    spell_card("br_spell_016", "雷火裂阵", 5, "阵法", "布置在目标随从上：被攻击时对攻击者造成10点反击伤害。", "ally", [{"kind": "target_trap", "trap": "雷火裂阵"}], "雷先裂甲，火再入骨。"),
    spell_card("br_spell_017", "万兽同心印", 5, "神通", "友方全体攻击+3、防御+3。", "team", [{"kind": "team_stats", "attack": 3, "defense": 3}], "印成一瞬，兽群的心跳像同一面战鼓。"),
    spell_card("br_spell_018", "幽泉续命符", 5, "符箓", "选择目标随从，防御+10；若它已有护盾，再攻击+3。", "ally", [{"kind": "target_stats", "defense": 10}, {"kind": "target_if_shielded", "attack": 3}], "幽泉不问生死，只给还能站着的躯壳再添一口气。"),
    spell_card("br_spell_019", "太虚御灵诀", 6, "神通", "本回合友方全体获得先攻；天羽和真龙遗脉额外攻击+4。", "team", [{"kind": "team_keyword", "keyword": "先攻"}, {"kind": "factions_stats", "factions": ["天羽", "真龙遗脉"], "attack": 4}], "太虚一开，兽群像被无形之手推过战场。"),
    spell_card("br_spell_020", "周天归墟阵", 6, "阵法", "布置在目标随从上：被攻击时造成12点反击伤害并自身回复12点防御。", "ally", [{"kind": "target_trap", "trap": "周天归墟阵"}], "阵成周天，敌力越重，归墟回响越沉。"),
]


_ORIGINAL_BEAST_REALM_CARDS = BEAST_REALM_CARDS

ELEMENT_POOL = ["金", "木", "水", "火", "土", "雷", "冰", "风", "暗", "光"]
FACTION_BONUS = {
    "妖兽": (2, 2),
    "散修": (1, 1),
    "佛修": (0, 3),
    "邪修": (3, 0),
    "邪神": (4, 1),
    "伪神": (1, 4),
    "魔神": (5, 0),
    "域外天魔": (3, 2),
    "系统持有者": (2, 3),
}


def stable_int(text: str) -> int:
    value = 0
    for char in str(text):
        value = (value * 131 + ord(char)) % 1_000_003
    return value


def load_character_records() -> list[dict[str, Any]]:
    try:
        data = json.loads(CHARACTER_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    records = data.get("characters", [])
    return [entry for entry in records if isinstance(entry, dict)]


def character_element(entry: dict[str, Any], seed: int) -> str:
    text = f"{entry.get('name', '')}{entry.get('archetype', '')}{entry.get('story', '')}"
    for element in ELEMENT_POOL:
        if element in text:
            return element
    return ELEMENT_POOL[seed % len(ELEMENT_POOL)]


def generated_card_stats(tier: int, faction: str, seed: int) -> tuple[int, int]:
    atk_bonus, def_bonus = FACTION_BONUS.get(faction, (1, 1))
    base_attack = tier * 3 + 1 + atk_bonus + seed % 3
    base_defense = tier * 4 + 2 + def_bonus + (seed // 7) % 4
    if faction in {"佛修", "伪神"}:
        base_attack = max(1, base_attack - 1)
    if faction in {"邪修", "魔神"}:
        base_defense = max(2, base_defense - 1)
    return base_attack, base_defense


def generated_effect_and_rules(faction: str, tier: int, element: str, seed: int) -> tuple[str, dict[str, list[dict[str, Any]]]]:
    amount = max(1, tier)
    variant = seed % 4
    if faction == "妖兽":
        if variant == 0:
            return effect_text("加入战局", f"自身攻击+{amount}；同阵营随从防御+1"), {"join": [{"kind": "self_stats", "attack": amount}, {"kind": "faction_stats", "faction": faction, "defense": 1}]}
        if variant == 1:
            return effect_text("每回合开始", f"随机友方随从攻击+{amount}"), {"start": [{"kind": "random_ally_stats", "attack": amount}]}
        if variant == 2:
            return effect_text("阵营效果", f"{faction}随从攻击+{max(1, tier // 2)}、防御+1"), {"aura": [{"kind": "aura_faction", "faction": faction, "attack": max(1, tier // 2), "defense": 1}]}
        return effect_text("离开时", f"对敌方前排造成{tier + 2}点伤害"), {"leave": [{"kind": "enemy_front_damage", "damage": tier + 2}]}
    if faction == "散修":
        if variant == 0:
            return effect_text("加入战局", f"相邻随从各获得+{amount}/+{amount}"), {"join": [{"kind": "adjacent_stats", "left_attack": amount, "left_defense": amount, "right_attack": amount, "right_defense": amount}]}
        if variant == 1:
            return effect_text("每回合开始", "随机友方随从攻击+2、防御+1"), {"start": [{"kind": "random_ally_stats", "attack": 2, "defense": 1}]}
        if variant == 2:
            return effect_text("离开时", "友方全体攻击+1"), {"leave": [{"kind": "team_stats", "attack": 1}]}
        return effect_text("持续效果", "自身拥有先攻"), {"join": [{"kind": "keyword", "keyword": "先攻"}]}
    if faction == "佛修":
        if variant == 0:
            return effect_text("加入战局", f"友方全体获得护盾+{tier + 2}"), {"join": [{"kind": "team_shield", "shield": tier + 2}]}
        if variant == 1:
            return effect_text("阵营效果", f"{faction}随从防御+{max(1, tier // 2 + 1)}"), {"aura": [{"kind": "aura_faction", "faction": faction, "defense": max(1, tier // 2 + 1)}]}
        if variant == 2:
            return effect_text("每回合开始", "友方全体防御+1"), {"start": [{"kind": "team_stats", "defense": 1}]}
        return effect_text("持续效果", "自身拥有护卫"), {"join": [{"kind": "keyword", "keyword": "护卫"}]}
    if faction == "邪修":
        if variant == 0:
            return effect_text("离开时", f"对敌方前排造成{tier + 4}点伤害"), {"leave": [{"kind": "enemy_front_damage", "damage": tier + 4}]}
        if variant == 1:
            return effect_text("加入战局", f"自身攻击+{tier + 1}"), {"join": [{"kind": "self_stats", "attack": tier + 1}]}
        if variant == 2:
            return effect_text("每回合开始", "下一战随机敌方随从攻击-2"), {"start": [{"kind": "next_enemy_weaken", "attack": -2}]}
        return effect_text("离开时", "敌方前排攻击-3"), {"leave": [{"kind": "enemy_front_stats", "attack": -3}]}
    if faction == "邪神":
        if variant == 0:
            return effect_text("阵营效果", "友方全体攻击+2"), {"aura": [{"kind": "aura_team", "attack": 2}]}
        if variant == 1:
            return effect_text("每回合开始", "随机敌方随从攻击-3、防御-1"), {"start": [{"kind": "next_enemy_weaken", "attack": -3, "defense": -1}]}
        if variant == 2:
            return effect_text("加入战局", f"友方全体攻击+{max(1, tier // 2)}"), {"join": [{"kind": "team_stats", "attack": max(1, tier // 2)}]}
        return effect_text("离开时", "敌方全体攻击-2"), {"leave": [{"kind": "enemy_team_stats", "attack": -2}]}
    if faction == "伪神":
        if variant == 0:
            return effect_text("加入战局", f"自身获得护盾+{tier * 3}"), {"join": [{"kind": "self_shield", "shield": tier * 3}]}
        if variant == 1:
            return effect_text("阵营效果", f"{faction}随从攻击+1、防御+2"), {"aura": [{"kind": "aura_faction", "faction": faction, "attack": 1, "defense": 2}]}
        if variant == 2:
            return effect_text("加入战局", f"给自身布置一次{element}相反阵"), {"join": [{"kind": "self_trap", "trap": "五行锁灵阵"}]}
        return effect_text("每回合开始", "友方全体护盾+2"), {"start": [{"kind": "team_shield", "shield": 2}]}
    if faction == "魔神":
        if variant == 0:
            return effect_text("击破时", f"自身攻击+{tier + 1}"), {"kill": [{"kind": "self_stats", "attack": tier + 1}]}
        if variant == 1:
            return effect_text("加入战局", f"自身攻击+{tier * 2}"), {"join": [{"kind": "self_stats", "attack": tier * 2}]}
        if variant == 2:
            return effect_text("离开时", f"对敌方前排造成{tier + 6}点伤害"), {"leave": [{"kind": "enemy_front_damage", "damage": tier + 6}]}
        return effect_text("持续效果", "自身拥有先攻"), {"join": [{"kind": "keyword", "keyword": "先攻"}]}
    if faction == "域外天魔":
        if variant == 0:
            return effect_text("每回合开始", "下一战随机敌方随从攻击-3、防御-3"), {"start": [{"kind": "next_enemy_weaken", "attack": -3, "defense": -3}]}
        if variant == 1:
            return effect_text("阵营效果", f"{faction}随从攻击+2"), {"aura": [{"kind": "aura_faction", "faction": faction, "attack": 2}]}
        if variant == 2:
            return effect_text("加入战局", f"{element}系随从攻击+{max(1, tier // 2 + 1)}"), {"join": [{"kind": "element_stats", "element": element, "attack": max(1, tier // 2 + 1)}]}
        return effect_text("离开时", "敌方前排攻击-4"), {"leave": [{"kind": "enemy_front_stats", "attack": -4}]}
    if faction == "系统持有者":
        if variant == 0:
            return effect_text("加入战局", "友方全体攻击+1、防御+1"), {"join": [{"kind": "team_stats", "attack": 1, "defense": 1}]}
        if variant == 1:
            return effect_text("每回合开始", f"随机友方随从+{max(1, tier // 2)}/+{max(1, tier // 2)}"), {"start": [{"kind": "random_ally_stats", "attack": max(1, tier // 2), "defense": max(1, tier // 2)}]}
        if variant == 2:
            return effect_text("加入战局", "左右随从攻击+2、防御+2"), {"join": [{"kind": "adjacent_stats", "left_attack": 2, "left_defense": 2, "right_attack": 2, "right_defense": 2}]}
        return effect_text("阵营效果", f"{faction}随从防御+2"), {"aura": [{"kind": "aura_faction", "faction": faction, "defense": 2}]}
    return effect_text("加入战局", f"自身+{amount}/+{amount}"), {"join": [{"kind": "self_stats", "attack": amount, "defense": amount}]}


def character_to_card(entry: dict[str, Any], faction_index: int) -> dict[str, Any]:
    role_id = str(entry.get("id") or f"character_{faction_index:03d}")
    name = str(entry.get("name") or role_id)
    faction = str(entry.get("faction") or "散修")
    tier = max(1, min(6, faction_index // 5 + 1))
    seed = stable_int(role_id + name + faction)
    element = character_element(entry, seed)
    attack, defense = generated_card_stats(tier, faction, seed)
    effect, rules = generated_effect_and_rules(faction, tier, element, seed)
    return {
        "kind": "beast",
        "id": f"follower_{role_id}",
        "portrait_id": role_id,
        "name": name,
        "tier": tier,
        "realm": BEAST_REALM_TIERS[tier - 1],
        "faction": faction,
        "element": element,
        "attack": attack,
        "defense": defense,
        "effect": effect,
        "rules": rules,
        "story": str(entry.get("story") or "来自任务堂档案的随从。"),
        "source_realm": str(entry.get("realm") or ""),
        "archetype": str(entry.get("archetype") or ""),
    }


def load_character_follower_cards() -> list[dict[str, Any]]:
    records = load_character_records()
    if not records:
        return []
    faction_counts: dict[str, int] = {}
    cards: list[dict[str, Any]] = []
    for entry in records:
        faction = str(entry.get("faction") or "散修")
        index = faction_counts.get(faction, 0)
        faction_counts[faction] = index + 1
        cards.append(character_to_card(entry, index))
    return cards


_loaded_character_cards = load_character_follower_cards()
if _loaded_character_cards:
    BEAST_REALM_CARDS = _loaded_character_cards
BEAST_REALM_CARD_BY_ID = {card["id"]: card for card in BEAST_REALM_CARDS}
BEAST_REALM_SPELL_BY_ID = {card["id"]: card for card in BEAST_REALM_SPELLS}
BEAST_REALM_ALL_CARDS_BY_ID = {**BEAST_REALM_CARD_BY_ID, **BEAST_REALM_SPELL_BY_ID}
_BASE_BEAST_REALM_CARDS = deepcopy(BEAST_REALM_CARDS)
_BASE_BEAST_REALM_SPELLS = deepcopy(BEAST_REALM_SPELLS)
_CARD_TEXT_FIELDS = {"portrait_id", "name", "realm", "faction", "element", "effect", "story", "source_realm", "archetype", "category", "target"}
_CARD_INT_FIELDS = {"tier", "attack", "defense", "pool_copies", "cost"}
_CARD_STRUCT_FIELDS = {"rules"}


def _int_setting(value: Any, default: int, minimum: int = 0, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _default_card_cost(card: dict[str, Any]) -> int:
    if card.get("kind") == "spell":
        return max(2, int(card.get("tier", 1)) + 1)
    return 3


def _normalize_card(card: dict[str, Any]) -> dict[str, Any]:
    next_card = dict(card)
    tier = _int_setting(next_card.get("tier"), 1, 1, len(BEAST_REALM_TIERS))
    next_card["tier"] = tier
    if not next_card.get("realm"):
        next_card["realm"] = BEAST_REALM_TIERS[tier - 1]
    next_card["cost"] = _int_setting(next_card.get("cost"), _default_card_cost(next_card), 0)
    if next_card.get("kind") == "beast":
        next_card["attack"] = _int_setting(next_card.get("attack"), 1, 0)
        next_card["defense"] = _int_setting(next_card.get("defense"), 1, 1)
        next_card["pool_copies"] = _int_setting(next_card.get("pool_copies"), BEAST_REALM_CARD_POOL_COPIES, 0)
    return next_card


def _apply_card_override(card: dict[str, Any], override: Any) -> dict[str, Any]:
    next_card = deepcopy(card)
    if not isinstance(override, dict):
        return _normalize_card(next_card)
    for field in _CARD_TEXT_FIELDS:
        if field in override:
            next_card[field] = str(override.get(field) or "")
    for field in _CARD_INT_FIELDS:
        if field in override:
            default = _default_card_cost(next_card) if field == "cost" else int(next_card.get(field, 0) or 0)
            next_card[field] = _int_setting(override.get(field), default, 0)
    for field in _CARD_STRUCT_FIELDS:
        if field in override and isinstance(override.get(field), (dict, list)):
            next_card[field] = deepcopy(override[field])
    if "tier" in override and "realm" not in override:
        tier = _int_setting(next_card.get("tier"), 1, 1, len(BEAST_REALM_TIERS))
        next_card["realm"] = BEAST_REALM_TIERS[tier - 1]
    return _normalize_card(next_card)


def rebuild_card_indexes() -> None:
    global BEAST_REALM_CARD_BY_ID, BEAST_REALM_SPELL_BY_ID, BEAST_REALM_ALL_CARDS_BY_ID
    BEAST_REALM_CARD_BY_ID = {card["id"]: card for card in BEAST_REALM_CARDS}
    BEAST_REALM_SPELL_BY_ID = {card["id"]: card for card in BEAST_REALM_SPELLS}
    BEAST_REALM_ALL_CARDS_BY_ID = {**BEAST_REALM_CARD_BY_ID, **BEAST_REALM_SPELL_BY_ID}


def apply_admin_config(config: dict[str, Any]) -> None:
    global BEAST_REALM_CARDS, BEAST_REALM_SPELLS, BEAST_REALM_CARD_POOL_COPIES
    realm_config = config.get("beast_realm", {}) if isinstance(config, dict) else {}
    if not isinstance(realm_config, dict):
        realm_config = {}
    BEAST_REALM_CARD_POOL_COPIES = _int_setting(realm_config.get("card_pool_copies"), BEAST_REALM_DEFAULT_CARD_COPIES, 0)
    overrides = realm_config.get("card_overrides", {})
    if not isinstance(overrides, dict):
        overrides = {}
    BEAST_REALM_CARDS = [_apply_card_override(card, overrides.get(str(card.get("id")))) for card in _BASE_BEAST_REALM_CARDS]
    BEAST_REALM_SPELLS = [_apply_card_override(card, overrides.get(str(card.get("id")))) for card in _BASE_BEAST_REALM_SPELLS]
    rebuild_card_indexes()


def admin_card_payload() -> dict[str, Any]:
    cards: list[dict[str, Any]] = []
    for card in BEAST_REALM_CARDS + BEAST_REALM_SPELLS:
        item = _normalize_card(deepcopy(card))
        if item.get("kind") == "beast":
            item["pool_copies"] = _int_setting(item.get("pool_copies"), BEAST_REALM_CARD_POOL_COPIES, 0)
        cards.append(item)
    factions = sorted({str(card.get("faction")) for card in BEAST_REALM_CARDS if card.get("faction")})
    elements = sorted({str(card.get("element")) for card in BEAST_REALM_CARDS if card.get("element")})
    categories = sorted({str(card.get("category")) for card in BEAST_REALM_SPELLS if card.get("category")})
    return {
        "ok": True,
        "cards": cards,
        "meta": {
            "realms": list(BEAST_REALM_TIERS),
            "factions": factions,
            "elements": elements,
            "categories": categories,
            "targets": ["ally", "team", "enemy"],
            "default_pool_copies": BEAST_REALM_CARD_POOL_COPIES,
        },
    }

TRAP_RULES: dict[str, list[dict[str, Any]]] = {
    "玄丝反阵": [{"kind": "trap_damage", "damage": 4}, {"kind": "trap_self_shield", "shield": 2}],
    "黄泉反阵": [{"kind": "trap_damage", "damage": 8}, {"kind": "trap_attacker_stats", "attack": -2}],
    "炎狱反阵": [{"kind": "trap_damage", "damage": 6}],
    "玄水回阵": [{"kind": "trap_self_heal", "heal": 8}],
    "五行锁灵阵": [{"kind": "trap_attacker_stats", "attack": -5}],
    "雷火裂阵": [{"kind": "trap_damage", "damage": 10}],
    "周天归墟阵": [{"kind": "trap_damage", "damage": 12}, {"kind": "trap_self_heal", "heal": 12}],
}


def is_beast_realm_group_command(text: str) -> bool:
    normalized = text.strip()
    if normalized in BEAST_REALM_ENTRY_TEXTS:
        return True
    if "御兽秘境" in normalized and parse_mode(normalized) == "solo_pve":
        return True
    return normalized.startswith("御兽秘境开局") or normalized.startswith("开启御兽秘境")


def is_beast_realm_private_command(text: str) -> bool:
    normalized = text.strip()
    if normalized in BEAST_REALM_PRIVATE_TEXTS:
        return True
    return any(normalized == prefix or normalized.startswith(f"{prefix} ") for prefix in BEAST_REALM_PRIVATE_PREFIXES)


def parse_mode(text: str) -> str:
    upper = text.upper().replace(" ", "")
    if "1V2" in upper or "单人" in text or "SOLO" in upper:
        return "solo_pve"
    if "PVP" in upper or "2V2" in upper or "排位" in text:
        return "pvp"
    return "pve"


def group_key(group_id: str | int) -> str:
    return f"group:{group_id}"


def private_key(user_id: str | int) -> str:
    return f"private:{user_id}"


def is_beast_realm_private_entry_command(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return False
    return parse_mode(normalized) == "solo_pve" and ("御兽秘境" in normalized or "单人" in normalized)


def mode_label(mode: str) -> str:
    if mode == "pvp":
        return "4人排位 PVP"
    if mode == "solo_pve":
        return "1V2 单人PVE"
    return "4V4 PVE"


def help_text() -> str:
    return "\n".join(
        [
            "【御兽秘境】",
            "灵感来自酒馆战棋：群聊开局，私聊在任务堂招募随从，群聊自动播报每回合战报。",
            "",
            "【群聊流程】",
            "御兽秘境开局 PVE：开启4V4秘境演武，需要4名修士，每人匹配1名bot代理。",
            "御兽秘境开局 PVP：开启4人排位战，需要4名修士，每回合两两匹配进行1V1。",
            "加入御兽秘境 / 退出御兽秘境 / 开始御兽秘境 / 御兽秘境状态 / 结束御兽秘境。",
            "私聊发送 御兽秘境1V2：开启单人PVE，全流程在私聊中完成。",
            "开房或加入后系统会私聊随机3位峰主，发送 选择峰主 1/2/3 决定初始生命和专属技能。",
            "",
            "【私聊招募】",
            "任务堂：查看商店、战局和灵石。",
            "购买 1 或 招募 1：购买随从并加入战局；施法 1 2：使用第1张法术到第2个随从。",
            "刷新：花1灵石刷新商店；冻结：保留当前商店；升堂：提升任务堂，解锁更高境界卡牌。",
            "出售 1：移除第1个随从并返还1灵石；调整 1 3：交换站位；完成招募：准备进入战斗。",
            "",
            "【战斗规则】",
            "PVP每回合随机两场1V1；胜者按剩余随从境界层数总和 + 任务堂层数，对败者造成生命伤害。",
            "4V4 PVE为4名修士分别匹配4名bot代理；1V2 PVE为单人私聊对抗2名bot代理。血量归零即淘汰。",
            "随从保留成长属性；战斗中复制为临时单位。护卫会优先被攻击，先攻单位会更早出手。",
            "入场、离开、每回合开始、阵营光环和阵法反击都会结算。PVE撑过并击败第8回合秘境兽潮即胜利。",
        ]
    )


def catalog_text() -> str:
    lines = [
        "【御兽秘境卡牌图鉴】",
        "随从牌共有270张，来自通用角色库并按妖兽、散修、佛修等阵营区分；法术牌20张，分为丹药、符箓、神通、阵法。",
    ]
    for tier, realm in enumerate(BEAST_REALM_TIERS, start=1):
        lines.append("")
        lines.append(f"【{realm}随从】")
        for card in [item for item in BEAST_REALM_CARDS if int(item["tier"]) == tier]:
            lines.append(
                f"{card['name']}｜{card['attack']}/{card['defense']}｜{card['faction']}·{card['element']}｜{card['effect']}"
            )
    lines.append("")
    lines.append("【法术牌】")
    for card in BEAST_REALM_SPELLS:
        lines.append(f"{card['name']}｜{card['realm']}｜{card['category']}｜{card['effect']}")
    return "\n".join(lines)


def leader_by_id(leader_id: str) -> Optional[dict[str, Any]]:
    leader = BEAST_REALM_LEADER_BY_ID.get(str(leader_id))
    return deepcopy(leader) if leader else None


def leader_choices_for(player: dict[str, Any]) -> list[dict[str, Any]]:
    choice_ids = [str(item) for item in player.get("leader_choices", []) if str(item) in BEAST_REALM_LEADER_BY_ID]
    if len(choice_ids) < BEAST_REALM_LEADER_CHOICES:
        pool = [leader for leader in BEAST_REALM_LEADERS if str(leader.get("id")) not in set(choice_ids)]
        random.shuffle(pool)
        choice_ids.extend(str(leader["id"]) for leader in pool[: BEAST_REALM_LEADER_CHOICES - len(choice_ids)])
        player["leader_choices"] = choice_ids[:BEAST_REALM_LEADER_CHOICES]
    return [deepcopy(BEAST_REALM_LEADER_BY_ID[leader_id]) for leader_id in choice_ids[:BEAST_REALM_LEADER_CHOICES]]


def selected_leader(player: dict[str, Any]) -> Optional[dict[str, Any]]:
    return leader_by_id(str(player.get("leader_id") or ""))


def leader_status(player: dict[str, Any]) -> str:
    leader = selected_leader(player)
    if not leader:
        return "待选峰主"
    return f"{leader.get('name')}｜{leader.get('health')}生命"


def leader_choice_text(player: dict[str, Any]) -> str:
    leader = selected_leader(player)
    lines = ["【峰主选择】"]
    if leader:
        lines.append(f"当前峰主：{leader.get('name')}｜初始生命{leader.get('health')}")
        lines.append(f"技能：{leader.get('skill')}")
        lines.append("")
        lines.append("本局开始前仍可发送 选择峰主 1/2/3 更换。")
    else:
        lines.append("开局前请选择一位峰主；未选择峰主时无法开始御兽秘境。")
    lines.append("发送：选择峰主 1 / 选择峰主 2 / 选择峰主 3")
    lines.append("")
    for index, option in enumerate(leader_choices_for(player), start=1):
        mark = "（当前）" if leader and str(leader.get("id")) == str(option.get("id")) else ""
        lines.append(f"{index}. {option.get('name')}{mark}｜生命{option.get('health')}")
        lines.append(f"   技能：{option.get('skill')}")
    return "\n".join(lines)


def choose_leader(player: dict[str, Any], choice_index: int) -> tuple[bool, str]:
    choices = leader_choices_for(player)
    if choice_index < 1 or choice_index > len(choices):
        return False, f"请选择1-{len(choices)}之间的峰主。"
    leader = choices[choice_index - 1]
    player["leader_id"] = str(leader.get("id"))
    player["leader_name"] = str(leader.get("name"))
    player["leader_skill"] = str(leader.get("skill"))
    player["max_health"] = int(leader.get("health", BEAST_REALM_START_HEALTH))
    player["health"] = int(leader.get("health", BEAST_REALM_START_HEALTH))
    return True, f"已选择峰主【{leader.get('name')}】，初始生命{leader.get('health')}。\n技能：{leader.get('skill')}"


def pending_leader_players(table: dict[str, Any]) -> list[dict[str, Any]]:
    return [player for player in active_human_players(table) if not selected_leader(player)]

def create_human_player(user_id: str, name: str) -> dict[str, Any]:
    player = {
        "id": str(user_id),
        "name": name or f"QQ {user_id}",
        "bot": False,
        "team": 1,
        "eliminated": False,
        "health": BEAST_REALM_START_HEALTH,
        "max_health": BEAST_REALM_START_HEALTH,
        "leader_choices": [],
        "leader_id": "",
        "leader_name": "",
        "leader_skill": "",
        "peak_level": 1,
        "gold": 6,
        "max_gold": 6,
        "board": [],
        "shop": [],
        "frozen": False,
        "ready": False,
        "next_enemy_weaken": [],
    }
    leader_choices_for(player)
    return player


def create_bot_player(index: int, team: int = 1, level: int = 1, enemy: bool = False) -> dict[str, Any]:
    name_prefix = "秘境兽潮" if enemy else "任务堂执事"
    player = create_human_player(f"bot:{'enemy' if enemy else 'ally'}:{index}", f"{name_prefix}{index}")
    player["bot"] = True
    player["leader_choices"] = []
    player["leader_id"] = ""
    player["leader_name"] = ""
    player["leader_skill"] = ""
    player["team"] = team
    player["peak_level"] = max(1, min(6, level))
    player["max_gold"] = 8 + min(4, level)
    player["gold"] = player["max_gold"]
    return player


def create_table(group_id: str, host_id: str, host_name: str, mode: str = "pve") -> dict[str, Any]:
    host = create_human_player(host_id, host_name)
    return {
        "group_id": str(group_id),
        "mode": mode,
        "phase": "lobby",
        "host_id": str(host_id),
        "host_name": host_name or f"QQ {host_id}",
        "players": [host],
        "turn": 0,
        "created_at": time.monotonic(),
        "expires_at": time.monotonic() + BEAST_REALM_WAIT_SECONDS,
        "last_report": "",
    }


def active_human_players(table: dict[str, Any]) -> list[dict[str, Any]]:
    return [player for player in table.get("players", []) if not player.get("bot")]


def is_player_alive(player: dict[str, Any]) -> bool:
    return not bool(player.get("eliminated")) and int(player.get("health", BEAST_REALM_START_HEALTH)) > 0


def live_human_players(table: dict[str, Any]) -> list[dict[str, Any]]:
    return [player for player in active_human_players(table) if is_player_alive(player)]


def mark_eliminated(player: dict[str, Any]) -> bool:
    if int(player.get("health", 0)) <= 0 and not player.get("eliminated"):
        player["health"] = 0
        player["eliminated"] = True
        player["ready"] = True
        return True
    return False

def table_player(table: dict[str, Any], user_id: str) -> Optional[dict[str, Any]]:
    for player in table.get("players", []):
        if str(player.get("id")) == str(user_id):
            return player
    return None


def lobby_text(table: dict[str, Any]) -> str:
    players = active_human_players(table)
    mode = str(table.get("mode", "pve"))
    target_players = 1 if mode == "solo_pve" else BEAST_REALM_MAX_PLAYERS
    lines = [
        f"【御兽秘境等待房】{mode_label(mode)}",
        f"峰主：{table.get('host_name')}",
        f"人数：{len(players)}/{target_players}",
    ]
    for index, player in enumerate(players, start=1):
        lines.append(f"{index}. {player.get('name')}｜{leader_status(player)}")
    if mode == "pvp":
        lines.append("PVP需要4名修士；每回合随机两两匹配，同时进行两场1V1排位战。")
    elif mode == "solo_pve":
        lines.append("1V2单人PVE仅需1名修士；每回合在私聊中对抗2名bot代理。")
    else:
        lines.append("PVE需要4名修士；每回合分别匹配4名bot代理进行1V1战斗。")
    if mode == "solo_pve":
        lines.append("选择峰主后发送 开始御兽秘境。")
    else:
        lines.append("群聊发送 加入御兽秘境；峰主发送 开始御兽秘境。")
    return "\n".join(lines)


def add_player(table: dict[str, Any], user_id: str, name: str) -> tuple[bool, str]:
    if table.get("phase") != "lobby":
        return False, "御兽秘境已经开始，不能中途加入。"
    if str(table.get("mode", "pve")) == "solo_pve":
        return False, "1V2单人PVE为私聊单人玩法，不能加入他人的试炼。"
    if table_player(table, user_id):
        return False, "你已经在御兽秘境队伍中。"
    humans = active_human_players(table)
    if len(humans) >= BEAST_REALM_MAX_PLAYERS:
        return False, "御兽秘境队伍已满。"
    table.setdefault("players", []).append(create_human_player(user_id, name))
    return True, lobby_text(table)


def remove_player(table: dict[str, Any], user_id: str) -> tuple[bool, str]:
    if table.get("phase") != "lobby":
        return False, "御兽秘境已经开始，不能中途退出。"
    player = table_player(table, user_id)
    if not player:
        return False, "你不在当前御兽秘境队伍中。"
    table["players"] = [item for item in table["players"] if str(item.get("id")) != str(user_id)]
    if not active_human_players(table):
        return True, "御兽秘境队伍已解散。"
    if str(table.get("host_id")) == str(user_id):
        host = active_human_players(table)[0]
        table["host_id"] = str(host.get("id"))
        table["host_name"] = str(host.get("name"))
    return True, lobby_text(table)


def start_table(table: dict[str, Any]) -> tuple[bool, str]:
    if table.get("phase") != "lobby":
        return False, "御兽秘境已经开始。"
    humans = active_human_players(table)
    mode = str(table.get("mode", "pve"))
    required = 1 if mode == "solo_pve" else 4
    if len(humans) != required:
        if mode == "pvp":
            return False, "4人排位PVP需要4名修士才能开始。"
        if mode == "solo_pve":
            return False, "1V2单人PVE只能由1名修士在私聊开始。"
        return False, "4V4 PVE需要4名修士才能开始。"
    missing_leaders = pending_leader_players(table)
    if missing_leaders:
        names = "、".join(str(player.get("name")) for player in missing_leaders)
        return False, f"还有修士未选择峰主：{names}。请先在私聊发送 峰主 或 选择峰主 1。"
    for player in table["players"]:
        player["team"] = 1
        player["eliminated"] = False
    table["phase"] = "recruit"
    prepare_round(table)
    return True, start_round_text(table)


def start_round_text(table: dict[str, Any]) -> str:
    mode = str(table.get("mode", "pve"))
    lines = [f"【御兽秘境·第{table.get('turn', 1)}回合】", f"模式：{mode_label(mode)}"]
    alive = "、".join(str(player.get("name")) for player in live_human_players(table)) or "无"
    if mode == "pvp":
        lines.append(f"存活修士：{alive}")
        lines.append("本回合会随机两两匹配，胜者按剩余随从境界层数+任务堂层数攻击败者。")
    elif mode == "solo_pve":
        lines.append(f"独行修士：{alive}；本回合将遭遇2名bot代理。")
    else:
        lines.append(f"探索修士：{alive}；本回合分别匹配4名bot代理。")
    if mode == "solo_pve":
        lines.append("招募流程在本私聊完成。发送 完成招募 后立即触发1V2战报。")
    else:
        lines.append("招募流程已发送到私聊。完成后私聊发送 完成招募；全部准备后触发群聊战报。")
    return "\n".join(lines)


def tier_cards(max_tier: int, kind: str = "beast", table: Optional[dict[str, Any]] = None, exact_tier: bool = False) -> list[dict[str, Any]]:
    pool = BEAST_REALM_CARDS if kind == "beast" else BEAST_REALM_SPELLS
    cards = [card for card in pool if int(card.get("tier", 1)) == max_tier] if exact_tier else [card for card in pool if int(card.get("tier", 1)) <= max_tier]
    if kind != "beast" or table is None:
        return cards
    card_pool = table_card_pool(table)
    return [card for card in cards if int(card_pool.get(str(card.get("id")), 0)) > 0]


def card_pool_copies(card: dict[str, Any]) -> int:
    return _int_setting(card.get("pool_copies"), BEAST_REALM_CARD_POOL_COPIES, 0)


def create_card_pool() -> dict[str, int]:
    return {str(card.get("id")): card_pool_copies(card) for card in BEAST_REALM_CARDS}


def table_card_pool(table: dict[str, Any]) -> dict[str, int]:
    pool = table.get("card_pool")
    if not isinstance(pool, dict):
        pool = create_card_pool()
        table["card_pool"] = pool
    else:
        for card in BEAST_REALM_CARDS:
            card_id = str(card.get("id"))
            pool.setdefault(card_id, card_pool_copies(card))
    return pool


def take_card_from_pool(table: Optional[dict[str, Any]], card_id: str, count: int = 1) -> bool:
    if table is None:
        return True
    pool = table_card_pool(table)
    current = int(pool.get(str(card_id), 0))
    if current < count:
        return False
    pool[str(card_id)] = current - count
    return True


def return_card_to_pool(table: Optional[dict[str, Any]], card_id: str, count: int = 1) -> None:
    if table is None or not card_id:
        return
    pool = table_card_pool(table)
    card = BEAST_REALM_CARD_BY_ID.get(str(card_id))
    cap = card_pool_copies(card) if card else BEAST_REALM_CARD_POOL_COPIES
    pool[str(card_id)] = min(cap, int(pool.get(str(card_id), 0)) + max(0, int(count)))


def return_shop_to_pool(player: dict[str, Any], table: Optional[dict[str, Any]]) -> None:
    if table is None:
        return
    for card in list(player.get("shop", [])):
        if isinstance(card, dict) and card.get("kind") == "beast":
            return_card_to_pool(table, str(card.get("id")), 1)


def weighted_card(max_tier: int, kind: str, table: Optional[dict[str, Any]] = None, exact_tier: bool = False) -> Optional[dict[str, Any]]:
    pool = tier_cards(max_tier, kind, table=table, exact_tier=exact_tier)
    if not pool and table is None:
        pool = tier_cards(max_tier, kind, table=None, exact_tier=exact_tier)
    if not pool:
        return None
    weights = [1 + int(card.get("tier", 1)) for card in pool]
    card = deepcopy(random.choices(pool, weights=weights, k=1)[0])
    if kind == "beast" and table is not None:
        if not take_card_from_pool(table, str(card.get("id")), 1):
            return None
    return card


def roll_shop(player: dict[str, Any], table: Optional[dict[str, Any]] = None, free: bool = False) -> tuple[bool, str]:
    if not free and int(player.get("gold", 0)) < 1:
        return False, "灵石不足，刷新任务堂需要1灵石。"
    if not free:
        player["gold"] = int(player.get("gold", 0)) - 1
    return_shop_to_pool(player, table)
    max_tier = int(player.get("peak_level", 1))
    shop = []
    for index in range(BEAST_REALM_SHOP_SIZE):
        kind = "spell" if index == BEAST_REALM_SHOP_SIZE - 1 or random.random() < 0.22 else "beast"
        card = weighted_card(max_tier, kind, table=table)
        if card is None and kind == "beast":
            card = weighted_card(max_tier, "spell")
        if card is not None:
            shop.append(card)
    player["shop"] = shop
    player["frozen"] = False
    if len(shop) < BEAST_REALM_SHOP_SIZE:
        return True, "任务堂卡池略显空荡，只刷新出部分卡牌。"
    return True, "任务堂灵光翻涌，新的卡牌已经出现。"


def unit_from_card(card: dict[str, Any], golden: bool = False) -> dict[str, Any]:
    tier = int(card.get("tier", 1))
    attack = int(card.get("attack", 1))
    defense = int(card.get("defense", 1))
    if golden:
        attack = attack * 2 + tier
        defense = defense * 2 + tier * 2
    return {
        "uid": f"{card.get('id')}:{random.randint(1000, 9999)}:{time.monotonic_ns()}",
        "card_id": card.get("id"),
        "portrait_id": card.get("portrait_id", ""),
        "name": f"金色·{card.get('name')}" if golden else card.get("name"),
        "base_name": card.get("name"),
        "tier": tier,
        "realm": card.get("realm"),
        "faction": card.get("faction"),
        "element": card.get("element"),
        "attack": attack,
        "defense": defense,
        "shield": 0,
        "keywords": [],
        "traps": [],
        "golden": bool(golden),
        "triple_copies": 3 if golden else 1,
    }

def card_cost(card: dict[str, Any]) -> int:
    return _int_setting(card.get("cost"), _default_card_cost(card), 0)


def upgrade_cost(player: dict[str, Any]) -> int:
    level = int(player.get("peak_level", 1))
    return max(0, 4 + level * 2)


def prepare_round(table: dict[str, Any]) -> None:
    table["turn"] = int(table.get("turn", 0)) + 1
    table["phase"] = "recruit"
    mode = str(table.get("mode", "pve"))
    for player in table.get("players", []):
        if player.get("bot") or not is_player_alive(player):
            player["ready"] = True
            continue
        player["ready"] = False
        player["max_gold"] = min(12, 5 + int(table.get("turn", 1)))
        player["gold"] = int(player.get("max_gold", 6))
        apply_start_rules(player)
        apply_leader_trigger(player, "round_start", table=table)
        if not player.get("frozen") or not player.get("shop"):
            roll_shop(player, table, free=True)
    if mode in {"pve", "solo_pve"}:
        enemy_count = 2 if mode == "solo_pve" else max(1, len(live_human_players(table)))
        table["enemies"] = create_pve_enemies(int(table.get("turn", 1)), enemy_count, table)
    else:
        table["enemies"] = []

def card_rules(card_id: str, section: str) -> list[dict[str, Any]]:
    card = BEAST_REALM_ALL_CARDS_BY_ID.get(str(card_id), {})
    return list((card.get("rules") or {}).get(section, []))


def apply_start_rules(player: dict[str, Any]) -> None:
    for unit in list(player.get("board", [])):
        for rule in unit_rules(unit, "start"):
            apply_rule(rule, player, unit)


def board_targets(player: dict[str, Any], rule: dict[str, Any], source: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    board = list(player.get("board", []))
    kind = str(rule.get("kind", ""))
    if kind in {"self_stats", "self_shield", "self_trap", "keyword", "self_if_element"}:
        return [source] if source is not None else []
    if "faction" in rule:
        board = [unit for unit in board if str(unit.get("faction")) == str(rule.get("faction"))]
    if "element" in rule and kind not in {"non_element_stats", "self_if_element"}:
        board = [unit for unit in board if str(unit.get("element")) == str(rule.get("element"))]
    if kind == "non_element_stats":
        board = [unit for unit in board if str(unit.get("element")) != str(rule.get("element"))]
    if "factions" in rule:
        factions = {str(item) for item in rule.get("factions", [])}
        board = [unit for unit in board if str(unit.get("faction")) in factions]
    if "elements" in rule:
        elements = {str(item) for item in rule.get("elements", [])}
        board = [unit for unit in board if str(unit.get("element")) in elements]
    return board


def add_stats(unit: dict[str, Any], attack: int = 0, defense: int = 0) -> None:
    unit["attack"] = max(0, int(unit.get("attack", 0)) + int(attack))
    unit["defense"] = max(1, int(unit.get("defense", 1)) + int(defense))


def add_shield(unit: dict[str, Any], shield: int) -> None:
    unit["shield"] = max(0, int(unit.get("shield", 0)) + int(shield))


def add_keyword(unit: dict[str, Any], keyword: str) -> None:
    keywords = list(unit.get("keywords", []))
    if keyword and keyword not in keywords:
        keywords.append(keyword)
    unit["keywords"] = keywords


def add_trap(unit: dict[str, Any], trap: str) -> None:
    if trap:
        traps = list(unit.get("traps", []))
        traps.append(trap)
        unit["traps"] = traps


def apply_rule(rule: dict[str, Any], player: dict[str, Any], source: Optional[dict[str, Any]] = None) -> None:
    kind = str(rule.get("kind", ""))
    attack = int(rule.get("attack", 0))
    defense = int(rule.get("defense", 0))
    if kind == "self_if_element":
        if source is not None and any(unit is not source and str(unit.get("element")) == str(rule.get("element")) for unit in player.get("board", [])):
            add_stats(source, attack, defense)
        return
    if kind in {"self_stats", "team_stats", "faction_stats", "element_stats", "multi_element_stats", "non_element_stats", "factions_stats"}:
        for unit in board_targets(player, rule, source):
            add_stats(unit, attack, defense)
        return
    if kind == "random_ally_stats":
        candidates = list(player.get("board", []))
        if candidates:
            add_stats(random.choice(candidates), attack, defense)
        return
    if kind == "random_many_stats":
        candidates = list(player.get("board", []))
        random.shuffle(candidates)
        for unit in candidates[: max(0, int(rule.get("count", 1)))]:
            add_stats(unit, attack, defense)
        return
    if kind == "adjacent_stats" and source is not None:
        board = list(player.get("board", []))
        try:
            index = board.index(source)
        except ValueError:
            return
        if index > 0:
            add_stats(board[index - 1], int(rule.get("left_attack", 0)), int(rule.get("left_defense", 0)))
        if index + 1 < len(board):
            add_stats(board[index + 1], int(rule.get("right_attack", 0)), int(rule.get("right_defense", 0)))
        return
    if kind in {"self_shield", "team_shield", "random_ally_shield"}:
        if kind == "self_shield" and source is not None:
            add_shield(source, int(rule.get("shield", 0)))
        elif kind == "team_shield":
            for unit in player.get("board", []):
                add_shield(unit, int(rule.get("shield", 0)))
        elif player.get("board"):
            add_shield(random.choice(player["board"]), int(rule.get("shield", 0)))
        return
    if kind == "keyword" and source is not None:
        add_keyword(source, str(rule.get("keyword", "")))
        return
    if kind == "self_trap" and source is not None:
        add_trap(source, str(rule.get("trap", "")))
        return
    if kind == "next_enemy_weaken":
        player.setdefault("next_enemy_weaken", []).append({"attack": attack, "defense": defense})


LEADER_BOARD_RULE_KINDS = {
    "self_if_element", "self_stats", "team_stats", "faction_stats", "element_stats",
    "multi_element_stats", "non_element_stats", "factions_stats", "random_ally_stats",
    "random_many_stats", "adjacent_stats", "self_shield", "team_shield",
    "random_ally_shield", "keyword", "self_trap", "next_enemy_weaken",
}


def leader_rules(player: dict[str, Any], trigger: str) -> list[dict[str, Any]]:
    leader = selected_leader(player)
    if not leader:
        return []
    rules = leader.get("rules", {})
    if not isinstance(rules, dict):
        return []
    return [deepcopy(rule) for rule in rules.get(trigger, []) if isinstance(rule, dict)]


def apply_leader_rule(
    player: dict[str, Any],
    rule: dict[str, Any],
    table: Optional[dict[str, Any]] = None,
    source: Optional[dict[str, Any]] = None,
    target: Optional[dict[str, Any]] = None,
    card: Optional[dict[str, Any]] = None,
) -> bool:
    kind = str(rule.get("kind", ""))
    if kind in LEADER_BOARD_RULE_KINDS:
        apply_rule(rule, player, source)
        return True
    if kind == "source_stats" and source is not None:
        add_stats(source, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
        return True
    if kind == "source_shield" and source is not None:
        add_shield(source, int(rule.get("shield", 0)))
        return True
    if kind == "source_if_faction_stats" and source is not None:
        faction = str(rule.get("faction", ""))
        card_faction = str((card or source).get("faction", ""))
        if card_faction == faction:
            add_stats(source, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
            return True
        return False
    if kind == "target_stats" and target is not None:
        add_stats(target, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
        return True
    if kind == "target_shield" and target is not None:
        add_shield(target, int(rule.get("shield", 0)))
        return True
    if kind == "target_trap" and target is not None:
        add_trap(target, str(rule.get("trap", "")))
        return True
    if kind == "leader_gold":
        player["gold"] = max(0, int(player.get("gold", 0)) + int(rule.get("amount", 0)))
        return True
    if kind == "leader_max_gold":
        amount = int(rule.get("amount", 0))
        player["max_gold"] = max(0, int(player.get("max_gold", 0)) + amount)
        player["gold"] = max(0, int(player.get("gold", 0)) + amount)
        return True
    if kind == "leader_health":
        player["health"] = max(0, int(player.get("health", BEAST_REALM_START_HEALTH)) + int(rule.get("amount", 0)))
        return True
    return False


def apply_leader_trigger(
    player: dict[str, Any],
    trigger: str,
    table: Optional[dict[str, Any]] = None,
    source: Optional[dict[str, Any]] = None,
    target: Optional[dict[str, Any]] = None,
    card: Optional[dict[str, Any]] = None,
) -> str:
    leader = selected_leader(player)
    if not leader:
        return ""
    triggered = False
    for rule in leader_rules(player, trigger):
        if apply_leader_rule(player, rule, table=table, source=source, target=target, card=card):
            triggered = True
    if not triggered:
        return ""
    return f"峰主【{leader.get('name')}】触发：{leader.get('skill')}"


def leader_damage_taken(player: dict[str, Any], damage: int) -> int:
    final_damage = max(0, int(damage))
    for rule in leader_rules(player, "damage_taken"):
        if str(rule.get("kind")) == "damage_reduce":
            final_damage = max(0, final_damage - int(rule.get("amount", 0)))
    return final_damage


def battle_rule_targets(player: dict[str, Any], units: list[dict[str, Any]], rule: dict[str, Any]) -> list[dict[str, Any]]:
    targets = [unit for unit in units if str(unit.get("owner_id")) == str(player.get("id"))]
    if "faction" in rule:
        targets = [unit for unit in targets if str(unit.get("faction")) == str(rule.get("faction"))]
    if "element" in rule:
        targets = [unit for unit in targets if str(unit.get("element")) == str(rule.get("element"))]
    if str(rule.get("kind", "")).startswith("battle_first"):
        return targets[:1]
    return targets


def apply_leader_battle_rules(players: list[dict[str, Any]], units: list[dict[str, Any]]) -> None:
    for player in players:
        for rule in leader_rules(player, "battle_start"):
            kind = str(rule.get("kind", ""))
            targets = battle_rule_targets(player, units, rule)
            if not targets:
                continue
            if kind in {"battle_team_stats", "battle_first_stats"}:
                attack = int(rule.get("attack", 0))
                defense = int(rule.get("defense", 0))
                for target in targets:
                    add_stats(target, attack, defense)
                    if defense:
                        target["hp"] = max(1, int(target.get("hp", 1)) + defense)
                        target["max_hp"] = max(int(target.get("max_hp", 1)), int(target.get("hp", 1)))
            elif kind in {"battle_team_keyword", "battle_first_keyword"}:
                for target in targets:
                    add_keyword(target, str(rule.get("keyword", "")))

_RULE_SCALE_FIELDS = {
    "attack", "defense", "damage", "shield", "heal", "left_attack", "left_defense",
    "right_attack", "right_defense", "shielded_defense", "count",
}


def scale_rule(rule: dict[str, Any], multiplier: int) -> dict[str, Any]:
    if multiplier <= 1:
        return deepcopy(rule)
    next_rule = deepcopy(rule)
    for field in _RULE_SCALE_FIELDS:
        if field in next_rule:
            try:
                next_rule[field] = int(next_rule[field]) * multiplier
            except (TypeError, ValueError):
                pass
    return next_rule


def unit_rules(unit: dict[str, Any], section: str) -> list[dict[str, Any]]:
    multiplier = 2 if unit.get("golden") else 1
    return [scale_rule(rule, multiplier) for rule in card_rules(str(unit.get("card_id")), section)]


def golden_unit_from_units(card: dict[str, Any], units: list[dict[str, Any]]) -> dict[str, Any]:
    golden = unit_from_card(card, golden=True)
    base_attack = int(card.get("attack", 1))
    base_defense = int(card.get("defense", 1))
    bonus_attack = sum(max(0, int(unit.get("attack", 0)) - base_attack) for unit in units)
    bonus_defense = sum(max(0, int(unit.get("defense", 0)) - base_defense) for unit in units)
    golden["attack"] = int(golden.get("attack", 0)) + bonus_attack
    golden["defense"] = int(golden.get("defense", 0)) + bonus_defense
    golden["shield"] = sum(int(unit.get("shield", 0)) for unit in units)
    keywords: list[str] = []
    traps: list[str] = []
    for unit in units:
        for keyword in unit.get("keywords", []):
            if keyword not in keywords:
                keywords.append(keyword)
        traps.extend(str(trap) for trap in unit.get("traps", []) if trap)
    golden["keywords"] = keywords
    golden["traps"] = traps
    return golden


def create_triple_reward_choices(table: Optional[dict[str, Any]], player: dict[str, Any]) -> list[dict[str, Any]]:
    target_tier = min(len(BEAST_REALM_TIERS), int(player.get("peak_level", 1)) + 1)
    choices: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _ in range(BEAST_REALM_DISCOVER_CHOICES * 3):
        if len(choices) >= BEAST_REALM_DISCOVER_CHOICES:
            break
        card = weighted_card(target_tier, "beast", table=table, exact_tier=True)
        if card is None:
            break
        card_id = str(card.get("id"))
        if card_id in seen:
            return_card_to_pool(table, card_id, 1)
            continue
        seen.add(card_id)
        choices.append(card)
    return choices


def check_triple(player: dict[str, Any], unit: dict[str, Any], table: Optional[dict[str, Any]]) -> str:
    if unit.get("golden"):
        return ""
    card_id = str(unit.get("card_id"))
    board = list(player.get("board", []))
    matches = [item for item in board if str(item.get("card_id")) == card_id and not item.get("golden")]
    if len(matches) < 3:
        return ""
    selected = matches[:3]
    first_index = min(board.index(item) for item in selected)
    remaining = [item for item in board if item not in selected]
    card = BEAST_REALM_CARD_BY_ID.get(card_id)
    if not card:
        return ""
    golden = golden_unit_from_units(card, selected)
    remaining.insert(min(first_index, len(remaining)), golden)
    player["board"] = remaining
    choices = create_triple_reward_choices(table, player)
    if choices:
        player["discover"] = {"source_card": card_id, "tier": min(len(BEAST_REALM_TIERS), int(player.get("peak_level", 1)) + 1), "choices": choices}
        return f"三张【{card.get('name')}】合成为金色随从！请选择三连奖励：发送 选择1/2/3，获得一张高一境界随从加入手牌。"
    player["discover"] = None
    return f"三张【{card.get('name')}】合成为金色随从！但更高境界卡池暂无可发现随从。"


def choose_discover_reward(player: dict[str, Any], choice_index: int, table: Optional[dict[str, Any]]) -> tuple[bool, str]:
    discover = player.get("discover")
    if not isinstance(discover, dict):
        return False, "当前没有待选择的三连奖励。"
    choices = [card for card in discover.get("choices", []) if isinstance(card, dict)]
    if choice_index < 1 or choice_index > len(choices):
        return False, f"请选择1-{len(choices)}之间的三连奖励。"
    hand = list(player.get("hand", []))
    if len(hand) >= BEAST_REALM_HAND_LIMIT:
        return False, f"手牌最多保留{BEAST_REALM_HAND_LIMIT}张，请先上阵随从。"
    chosen = choices[choice_index - 1]
    for index, card in enumerate(choices):
        if index != choice_index - 1:
            return_card_to_pool(table, str(card.get("id")), 1)
    hand.append(chosen)
    player["hand"] = hand
    player["discover"] = None
    return True, f"已选择【{chosen.get('realm')}·{chosen.get('name')}】加入手牌，可发送 上阵 {len(hand)}。"


def play_hand_card(player: dict[str, Any], hand_index: int, table: Optional[dict[str, Any]]) -> tuple[bool, str]:
    hand = list(player.get("hand", []))
    if hand_index < 1 or hand_index > len(hand):
        return False, f"请选择1-{len(hand)}之间的手牌。"
    if len(player.get("board", [])) >= BEAST_REALM_MAX_BOARD:
        return False, f"战局最多容纳{BEAST_REALM_MAX_BOARD}个随从，请先出售或调整。"
    card = hand.pop(hand_index - 1)
    player["hand"] = hand
    unit = unit_from_card(card)
    player.setdefault("board", []).append(unit)
    apply_join_rules(player, unit)
    triple_message = check_triple(player, unit, table)
    message = f"已上阵【{unit['realm']}·{unit['name']}】。"
    if triple_message:
        message += "\n" + triple_message
    return True, message

def apply_join_rules(player: dict[str, Any], unit: dict[str, Any]) -> None:
    for rule in unit_rules(unit, "join"):
        apply_rule(rule, player, unit)


def apply_sell_leave_rules(player: dict[str, Any], unit: dict[str, Any]) -> None:
    for rule in unit_rules(unit, "leave"):
        if str(rule.get("kind")) in {"random_ally_stats", "team_stats", "faction_stats", "element_stats"}:
            apply_rule(rule, player, unit)
    for ally in player.get("board", []):
        for rule in unit_rules(ally, "ally_leave"):
            apply_rule(rule, player, ally)


def buy_card(player: dict[str, Any], shop_index: int, table: Optional[dict[str, Any]] = None) -> tuple[bool, str]:
    shop = list(player.get("shop", []))
    if shop_index < 1 or shop_index > len(shop):
        return False, f"请选择1-{len(shop)}之间的任务堂卡牌。"
    card = shop[shop_index - 1]
    if card.get("kind") == "spell":
        return False, "这是法术牌，请发送“施法 编号 目标位”，例如：施法 5 2。"
    if len(player.get("board", [])) >= BEAST_REALM_MAX_BOARD:
        return False, f"战局最多容纳{BEAST_REALM_MAX_BOARD}个随从，请先出售或调整。"
    cost = card_cost(card)
    if int(player.get("gold", 0)) < cost:
        return False, f"灵石不足，招募{card.get('name')}需要{cost}灵石。"
    player["gold"] = int(player.get("gold", 0)) - cost
    unit = unit_from_card(card)
    player.setdefault("board", []).append(unit)
    apply_join_rules(player, unit)
    leader_message = apply_leader_trigger(player, "after_buy", table=table, source=unit, card=card)
    triple_message = check_triple(player, unit, table)
    del shop[shop_index - 1]
    player["shop"] = shop
    message = f"已招募【{unit['realm']}·{unit['name']}】加入战局。"
    if leader_message:
        message += "\n" + leader_message
    if triple_message:
        message += "\n" + triple_message
    return True, message

def target_unit(player: dict[str, Any], index: int) -> Optional[dict[str, Any]]:
    board = list(player.get("board", []))
    if 1 <= index <= len(board):
        return board[index - 1]
    return None


def apply_spell_rule(player: dict[str, Any], spell: dict[str, Any], target: Optional[dict[str, Any]], rule: dict[str, Any]) -> None:
    kind = str(rule.get("kind", ""))
    if kind == "target_stats" and target is not None:
        add_stats(target, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
    elif kind == "target_shield" and target is not None:
        add_shield(target, int(rule.get("shield", 0)))
    elif kind == "target_keyword" and target is not None:
        add_keyword(target, str(rule.get("keyword", "")))
    elif kind == "target_trap" and target is not None:
        add_trap(target, str(rule.get("trap", "")))
    elif kind == "target_if_below_peak" and target is not None:
        if int(target.get("tier", 1)) < int(player.get("peak_level", 1)):
            add_stats(target, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
    elif kind == "target_if_shielded" and target is not None:
        if int(target.get("shield", 0)) > 0:
            add_stats(target, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
    elif kind == "team_keyword":
        for unit in player.get("board", []):
            add_keyword(unit, str(rule.get("keyword", "")))
    else:
        apply_rule(rule, player, target)


def cast_spell(player: dict[str, Any], shop_index: int, target_index: Optional[int]) -> tuple[bool, str]:
    shop = list(player.get("shop", []))
    if shop_index < 1 or shop_index > len(shop):
        return False, f"请选择1-{len(shop)}之间的法术牌。"
    spell = shop[shop_index - 1]
    if spell.get("kind") != "spell":
        return False, "这是随从牌，请发送“购买 编号”或“招募 编号”。"
    cost = card_cost(spell)
    if int(player.get("gold", 0)) < cost:
        return False, f"灵石不足，施放{spell.get('name')}需要{cost}灵石。"
    target = None
    if str(spell.get("target")) == "ally":
        if target_index is None:
            return False, "这张法术需要目标，请发送“施法 卡牌编号 随从编号”。"
        target = target_unit(player, target_index)
        if target is None:
            return False, "没有找到目标随从。"
    if str(spell.get("target")) in {"team", "enemy"} and not player.get("board"):
        return False, "战局中暂无随从，暂时无法施放这张法术。"
    player["gold"] = int(player.get("gold", 0)) - cost
    for rule in spell.get("rules", []):
        apply_spell_rule(player, spell, target, rule)
    leader_message = apply_leader_trigger(player, "after_spell", target=target, card=spell)
    del shop[shop_index - 1]
    player["shop"] = shop
    suffix = f"于【{target.get('name')}】" if target else ""
    message = f"已施放【{spell.get('name')}】{suffix}。"
    if leader_message:
        message += "\n" + leader_message
    return True, message


def sell_unit(player: dict[str, Any], board_index: int, table: Optional[dict[str, Any]] = None) -> tuple[bool, str]:
    board = list(player.get("board", []))
    if board_index < 1 or board_index > len(board):
        return False, f"请选择1-{len(board)}之间的随从。"
    unit = board.pop(board_index - 1)
    player["board"] = board
    player["gold"] = min(int(player.get("max_gold", 6)), int(player.get("gold", 0)) + 1)
    return_card_to_pool(table, str(unit.get("card_id")), int(unit.get("triple_copies", 3 if unit.get("golden") else 1)))
    apply_sell_leave_rules(player, unit)
    leader_message = apply_leader_trigger(player, "after_sell", table=table, source=unit)
    label = "金色随从" if unit.get("golden") else "随从"
    message = f"已送离【{unit.get('name')}】{label}，返还1灵石，并结算离开效果。"
    if leader_message:
        message += "\n" + leader_message
    return True, message

def move_unit(player: dict[str, Any], left: int, right: int) -> tuple[bool, str]:
    board = list(player.get("board", []))
    if left < 1 or right < 1 or left > len(board) or right > len(board):
        return False, "调整站位需要两个有效随从编号，例如：调整 1 3。"
    board[left - 1], board[right - 1] = board[right - 1], board[left - 1]
    player["board"] = board
    return True, f"已交换第{left}与第{right}位随从。"


def upgrade_peak(player: dict[str, Any], table: Optional[dict[str, Any]] = None) -> tuple[bool, str]:
    level = int(player.get("peak_level", 1))
    if level >= 6:
        return False, "任务堂已达炼虚期，无法继续提升。"
    cost = upgrade_cost(player)
    if int(player.get("gold", 0)) < cost:
        return False, f"灵石不足，提升任务堂需要{cost}灵石。"
    player["gold"] = int(player.get("gold", 0)) - cost
    player["peak_level"] = level + 1
    roll_shop(player, table, free=True)
    leader_message = apply_leader_trigger(player, "after_upgrade", table=table)
    message = f"任务堂已提升至【{BEAST_REALM_TIERS[level]}】，高阶卡牌开始显化。"
    if leader_message:
        message += "\n" + leader_message
    return True, message


def parse_numbers(text: str) -> list[int]:
    return [int(item) for item in re.findall(r"\d+", text)]


def private_action(table: dict[str, Any], player: dict[str, Any], text: str) -> tuple[str, str]:
    normalized = text.strip()
    numbers = parse_numbers(normalized)
    if str(table.get("phase")) == "lobby":
        if normalized in {"峰主", "峰主选择", "我的峰主", "任务堂", "御兽峰"}:
            return "峰主选择", leader_choice_text(player)
        if normalized.startswith(("选择峰主", "峰主", "选择")):
            if not numbers:
                return "操作提示", "请发送“选择峰主 1”选择候选峰主。\n\n" + leader_choice_text(player)
            ok, message = choose_leader(player, numbers[0])
            return ("峰主选择" if ok else "操作失败"), message + "\n\n" + leader_choice_text(player)
        return "峰主选择", leader_choice_text(player)
    if normalized in {"御兽秘境图鉴", "御兽卡牌", "御兽卡牌图鉴", "随从卡牌", "随从卡牌图鉴"}:
        return "御兽秘境图鉴", catalog_text()
    if not is_player_alive(player):
        return "御兽秘境", "你已在本局御兽秘境中被淘汰，可等待结算或重新开局。"
    if normalized in {"峰主", "峰主选择", "我的峰主"}:
        return "峰主", leader_choice_text(player)
    if normalized.startswith("选择峰主"):
        return "操作失败", "本局御兽秘境已经开始，峰主不可更换。\n\n" + leader_choice_text(player)
    if normalized in {"任务堂", "任务堂手牌", "任务堂战局", "御兽峰", "御兽手牌", "御兽战局", "随从手牌", "随从战局"}:
        return "任务堂", player_text(player, table)
    if normalized in {"刷新", "刷新任务堂", "刷新御兽峰"}:
        ok, message = roll_shop(player, table)
        return ("任务堂刷新" if ok else "操作失败"), message + "\n\n" + player_text(player, table)
    if normalized in {"冻结", "冻结任务堂", "冻结御兽峰"}:
        player["frozen"] = True
        return "任务堂冻结", "当前任务堂已冻结，下回合不会自动刷新。\n\n" + player_text(player, table)
    if normalized in {"解冻", "解冻任务堂", "解冻御兽峰"}:
        player["frozen"] = False
        return "任务堂解冻", "任务堂已解冻。\n\n" + player_text(player, table)
    if normalized in {"升堂", "提升任务堂", "升峰", "提升御兽峰"}:
        ok, message = upgrade_peak(player, table)
        return ("任务堂提升" if ok else "操作失败"), message + "\n\n" + player_text(player, table)
    if normalized in {"完成招募", "结束招募", "准备"}:
        player["ready"] = True
        return "招募完成", "你已完成本回合招募。若想重新查看，可发送 任务堂。"
    numbers = parse_numbers(normalized)
    if normalized.startswith(("选择", "发现")):
        if not numbers:
            return "操作提示", "请发送“选择 1”领取三连奖励。"
        ok, message = choose_discover_reward(player, numbers[0], table)
        return ("三连奖励" if ok else "操作失败"), message + "\n\n" + player_text(player, table)
    if normalized.startswith(("上阵", "打出", "召唤")):
        if not numbers:
            return "操作提示", "请发送“上阵 1”将手牌随从加入战局。"
        ok, message = play_hand_card(player, numbers[0], table)
        return ("手牌上阵" if ok else "操作失败"), message + "\n\n" + player_text(player, table)
    if normalized.startswith(("购买", "招募", "买入")):
        if not numbers:
            return "操作提示", "请发送“购买 1”或“招募 1”。"
        ok, message = buy_card(player, numbers[0], table)
        return ("随从招募" if ok else "操作失败"), message + "\n\n" + player_text(player, table)
    if normalized.startswith(("施法", "使用法术")) or (normalized.startswith("使用") and numbers):
        if not numbers:
            return "操作提示", "请发送“施法 卡牌编号 随从编号”，例如：施法 5 2。"
        target = numbers[1] if len(numbers) > 1 else None
        ok, message = cast_spell(player, numbers[0], target)
        return ("法术施放" if ok else "操作失败"), message + "\n\n" + player_text(player, table)
    if normalized.startswith(("出售", "卖出")):
        if not numbers:
            return "操作提示", "请发送“出售 1”。"
        ok, message = sell_unit(player, numbers[0], table)
        return ("随从离阵" if ok else "操作失败"), message + "\n\n" + player_text(player, table)
    if normalized.startswith(("调整", "移动")):
        if len(numbers) < 2:
            return "操作提示", "请发送“调整 1 3”。"
        ok, message = move_unit(player, numbers[0], numbers[1])
        return ("站位调整" if ok else "操作失败"), message + "\n\n" + player_text(player, table)
    return "任务堂", player_text(player, table)


def all_humans_ready(table: dict[str, Any]) -> bool:
    humans = live_human_players(table)
    return bool(humans) and all(bool(player.get("ready")) for player in humans)


def unit_line(unit: dict[str, Any], index: int) -> str:
    keyword = f"｜{','.join(unit.get('keywords', []))}" if unit.get("keywords") else ""
    shield = f"｜盾{unit.get('shield')}" if int(unit.get("shield", 0)) else ""
    traps = f"｜阵{len(unit.get('traps', []))}" if unit.get("traps") else ""
    golden = "｜金色" if unit.get("golden") else ""
    return (
        f"{index}. {unit.get('realm')}·{unit.get('name')} "
        f"{unit.get('attack')}/{unit.get('defense')}｜{unit.get('faction')}·{unit.get('element')}{golden}{shield}{traps}{keyword}"
    )


def card_summary_line(card: dict[str, Any], index: int, prefix: str = "随从") -> str:
    if card.get("kind") == "spell":
        return f"{index}. 【法术】{card.get('name')}｜{card.get('realm')}｜{card.get('category')}｜{card.get('effect')}"
    return (
        f"{index}. 【{prefix}】{card.get('name')}｜{card.get('realm')}｜"
        f"{card.get('attack')}/{card.get('defense')}｜{card.get('faction')}·{card.get('element')}｜{card.get('effect')}"
    )

def shop_line(card: dict[str, Any], index: int) -> str:
    cost = card_cost(card)
    if card.get("kind") == "spell":
        return f"{index}. 【法术】{card.get('name')}｜{card.get('realm')}｜{card.get('category')}｜{cost}灵石｜{card.get('effect')}"
    return (
        f"{index}. 【随从】{card.get('name')}｜{card.get('realm')}｜"
        f"{card.get('attack')}/{card.get('defense')}｜{card.get('faction')}·{card.get('element')}｜{cost}灵石｜{card.get('effect')}"
    )


def player_text(player: dict[str, Any], table: dict[str, Any]) -> str:
    leader = selected_leader(player)
    leader_name = str(leader.get("name")) if leader else "未选择"
    leader_skill = str(leader.get("skill")) if leader else "发送 峰主 查看候选"
    max_health = int(player.get("max_health", player.get("health", BEAST_REALM_START_HEALTH)))
    card_pool = table_card_pool(table)
    available = sum(int(value) for value in card_pool.values())
    lines = [
        f"【{player.get('name')}的任务堂】第{table.get('turn', 1)}回合",
        f"灵石：{player.get('gold', 0)}/{player.get('max_gold', 0)}｜任务堂：{BEAST_REALM_TIERS[int(player.get('peak_level', 1)) - 1]}｜生命：{player.get('health', 0)}/{max_health}",
        f"峰主：{leader_name}｜{leader_skill}",
        f"状态：{'已准备' if player.get('ready') else '招募中'}｜商店：{'冻结' if player.get('frozen') else '流转'}｜卡池剩余：{available}",
    ]
    discover = player.get("discover")
    if isinstance(discover, dict) and discover.get("choices"):
        lines.extend(["", f"【三连奖励】发现{BEAST_REALM_TIERS[int(discover.get('tier', 1)) - 1]}随从，发送 选择1/2/3："])
        for index, card in enumerate(discover.get("choices", []), start=1):
            lines.append(card_summary_line(card, index, "奖励"))
    hand = list(player.get("hand", []))
    if hand:
        lines.extend(["", "【手牌】发送 上阵 编号 可加入战局"])
        for index, card in enumerate(hand, start=1):
            lines.append(card_summary_line(card, index, "手牌"))
    lines.extend(["", "【任务堂卡牌】"])
    shop = list(player.get("shop", []))
    if shop:
        for index, card in enumerate(shop, start=1):
            lines.append(shop_line(card, index))
    else:
        lines.append("任务堂暂无卡牌，可发送 刷新。")
    lines.append("")
    lines.append("【当前战局】")
    board = list(player.get("board", []))
    if board:
        for index, unit in enumerate(board, start=1):
            lines.append(unit_line(unit, index))
    else:
        lines.append("暂无随从。")
    lines.append("")
    lines.append("指令：购买1 / 选择1 / 上阵1 / 施法1 2 / 刷新 / 冻结 / 升堂 / 出售1 / 调整1 3 / 完成招募")
    return "\n".join(lines)


def bot_recruit(player: dict[str, Any], table: dict[str, Any]) -> None:
    if int(table.get("turn", 1)) in {3, 5, 7} and int(player.get("peak_level", 1)) < 6:
        player["peak_level"] = min(6, int(player.get("peak_level", 1)) + 1)
    if not player.get("shop"):
        roll_shop(player, table, free=True)
    attempts = 0
    while int(player.get("gold", 0)) >= 3 and len(player.get("board", [])) < BEAST_REALM_MAX_BOARD and attempts < 8:
        attempts += 1
        beasts = [(idx + 1, card) for idx, card in enumerate(player.get("shop", [])) if card.get("kind") == "beast"]
        if not beasts:
            roll_shop(player, table)
            continue
        best_index, _best = max(beasts, key=lambda item: int(item[1].get("tier", 1)) * 10 + int(item[1].get("attack", 0)) + int(item[1].get("defense", 0)))
        ok, _message = buy_card(player, best_index, table)
        if not ok:
            break
    player["ready"] = True


def create_pve_enemies(turn: int, count: int = 4, table: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    level = max(1, min(6, 1 + turn // 2))
    enemies = [create_bot_player(index, team=2, level=level, enemy=True) for index in range(1, max(1, count) + 1)]
    for enemy in enemies:
        enemy["max_gold"] = min(12, 6 + turn)
        enemy["gold"] = int(enemy["max_gold"])
        enemy["peak_level"] = level
        enemy["shop"] = []
        bot_recruit(enemy, table or {})
        target_count = min(BEAST_REALM_MAX_BOARD, 2 + turn // 2)
        attempts = 0
        while len(enemy.get("board", [])) < target_count and attempts < target_count * 4:
            attempts += 1
            card = weighted_card(level, "beast", table=table)
            if not card:
                break
            unit = unit_from_card(card)
            scale = max(0, turn - int(card.get("tier", 1)))
            add_stats(unit, scale, scale * 2)
            enemy.setdefault("board", []).append(unit)
            apply_join_rules(enemy, unit)
        enemy["ready"] = True
    return enemies

def clone_battle_unit(unit: dict[str, Any], owner: dict[str, Any]) -> dict[str, Any]:
    clone = deepcopy(unit)
    clone["owner_id"] = owner.get("id")
    clone["owner_name"] = owner.get("name")
    clone["team"] = int(owner.get("team", 1))
    clone["hp"] = int(clone.get("defense", 1)) + int(clone.get("shield", 0))
    clone["max_hp"] = clone["hp"]
    clone["alive"] = True
    return clone


def battle_units(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for player in players:
        for unit in player.get("board", []):
            units.append(clone_battle_unit(unit, player))
    apply_battle_auras(units)
    apply_leader_battle_rules(players, units)
    for player in players:
        weakens = list(player.get("next_enemy_weaken", []))
        if not weakens:
            continue
        for weaken in weakens:
            candidates = [unit for unit in units if int(unit.get("team", 1)) != int(player.get("team", 1))]
            if candidates:
                target = random.choice(candidates)
                add_stats(target, int(weaken.get("attack", 0)), int(weaken.get("defense", 0)))
        player["next_enemy_weaken"] = []
    return units


def apply_battle_auras(units: list[dict[str, Any]]) -> None:
    for source in list(units):
        for rule in unit_rules(source, "aura"):
            kind = str(rule.get("kind", ""))
            targets = [unit for unit in units if int(unit.get("team", 1)) == int(source.get("team", 1))]
            if kind == "aura_faction":
                targets = [unit for unit in targets if str(unit.get("faction")) == str(rule.get("faction"))]
            elif kind == "aura_factions":
                factions = {str(item) for item in rule.get("factions", [])}
                targets = [unit for unit in targets if str(unit.get("faction")) in factions]
            elif kind == "aura_team":
                targets = list(targets)
            else:
                continue
            for target in targets:
                add_stats(target, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
                if int(rule.get("shielded_defense", 0)) and int(target.get("shield", 0)) > 0:
                    add_stats(target, 0, int(rule.get("shielded_defense", 0)))
                target["hp"] = int(target.get("hp", target.get("defense", 1))) + int(rule.get("defense", 0))
                target["max_hp"] = max(int(target.get("max_hp", 1)), int(target.get("hp", 1)))


def living(units: list[dict[str, Any]], team: int) -> list[dict[str, Any]]:
    return [unit for unit in units if int(unit.get("team", 0)) == team and bool(unit.get("alive")) and int(unit.get("hp", 0)) > 0]


def choose_defender(units: list[dict[str, Any]], team: int) -> Optional[dict[str, Any]]:
    candidates = living(units, team)
    if not candidates:
        return None
    guards = [unit for unit in candidates if "护卫" in set(unit.get("keywords", []))]
    return guards[0] if guards else candidates[0]


def trigger_traps(defender: dict[str, Any], attacker: dict[str, Any], logs: list[str]) -> None:
    traps = list(defender.get("traps", []))
    if not traps:
        return
    trap = traps.pop(0)
    defender["traps"] = traps
    logs.append(f"{defender.get('name')}触发【{trap}】。")
    for rule in TRAP_RULES.get(trap, []):
        kind = str(rule.get("kind", ""))
        if kind == "trap_damage":
            attacker["hp"] = int(attacker.get("hp", 0)) - int(rule.get("damage", 0))
            logs.append(f"{trap}反噬{attacker.get('name')} {rule.get('damage', 0)}点。")
        elif kind == "trap_self_heal":
            defender["hp"] = int(defender.get("hp", 0)) + int(rule.get("heal", 0))
            logs.append(f"{defender.get('name')}借阵势回复{rule.get('heal', 0)}点。")
        elif kind == "trap_self_shield":
            defender["hp"] = int(defender.get("hp", 0)) + int(rule.get("shield", 0))
            defender["max_hp"] = max(int(defender.get("max_hp", 1)), int(defender.get("hp", 1)))
        elif kind == "trap_attacker_stats":
            add_stats(attacker, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
    if int(attacker.get("hp", 0)) <= 0:
        attacker["alive"] = False


def apply_battle_leave(dead: dict[str, Any], units: list[dict[str, Any]], logs: list[str]) -> None:
    team = int(dead.get("team", 1))
    enemy_team = 2 if team == 1 else 1
    for rule in unit_rules(dead, "leave"):
        kind = str(rule.get("kind", ""))
        if kind == "enemy_front_damage":
            target = choose_defender(units, enemy_team)
            if target:
                target["hp"] = int(target.get("hp", 0)) - int(rule.get("damage", 0))
                logs.append(f"{dead.get('name')}离场反扑，重创{target.get('name')} {rule.get('damage', 0)}点。")
                if int(target.get("hp", 0)) <= 0:
                    target["alive"] = False
        elif kind == "enemy_front_stats":
            target = choose_defender(units, enemy_team)
            if target:
                add_stats(target, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
                logs.append(f"{dead.get('name')}寒意未散，压制{target.get('name')}。")
        elif kind == "enemy_team_stats":
            for target in living(units, enemy_team):
                add_stats(target, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
            logs.append(f"{dead.get('name')}离场余威扫过敌阵。")
        elif kind in {"team_stats", "random_ally_stats"}:
            allies = living(units, team)
            if not allies:
                continue
            targets = allies if kind == "team_stats" else [random.choice(allies)]
            for target in targets:
                add_stats(target, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
            logs.append(f"{dead.get('name')}离场激励友方。")
    for ally in living(units, team):
        for rule in unit_rules(ally, "ally_leave"):
            if str(rule.get("kind")) == "self_stats":
                add_stats(ally, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
                ally["hp"] = int(ally.get("hp", 0)) + int(rule.get("defense", 0))


def resolve_battle(left_players: list[dict[str, Any]], right_players: list[dict[str, Any]]) -> dict[str, Any]:
    units = battle_units(left_players + right_players)
    logs: list[str] = []
    if not living(units, 1):
        return {"winner": 2, "logs": ["青岚阵中暂无随从，赤霄方不战而胜。"], "survivors": living(units, 2)}
    if not living(units, 2):
        return {"winner": 1, "logs": ["赤霄阵中暂无随从，青岚方不战而胜。"], "survivors": living(units, 1)}
    attack_queue = sorted(
        [unit for unit in units if bool(unit.get("alive"))],
        key=lambda unit: (0 if "先攻" in set(unit.get("keywords", [])) else 1, -int(unit.get("attack", 0))),
    )
    cursor = 0
    rounds = 0
    while living(units, 1) and living(units, 2) and rounds < 120:
        rounds += 1
        if cursor >= len(attack_queue):
            attack_queue = [unit for unit in units if bool(unit.get("alive")) and int(unit.get("hp", 0)) > 0]
            cursor = 0
            if not attack_queue:
                break
        attacker = attack_queue[cursor]
        cursor += 1
        if not attacker.get("alive") or int(attacker.get("hp", 0)) <= 0:
            continue
        defender = choose_defender(units, 2 if int(attacker.get("team", 1)) == 1 else 1)
        if not defender:
            break
        trigger_traps(defender, attacker, logs)
        if not attacker.get("alive"):
            logs.append(f"{attacker.get('name')}被阵法反噬击溃。")
            apply_battle_leave(attacker, units, logs)
            continue
        damage = max(1, int(attacker.get("attack", 1)))
        defender["hp"] = int(defender.get("hp", 0)) - damage
        logs.append(f"{attacker.get('owner_name')}的{attacker.get('name')}攻击{defender.get('name')}，造成{damage}点。")
        killed = int(defender.get("hp", 0)) <= 0
        if killed:
            defender["alive"] = False
            logs.append(f"{defender.get('name')}离开战局。")
            for rule in unit_rules(attacker, "kill"):
                if str(rule.get("kind")) == "self_stats":
                    add_stats(attacker, int(rule.get("attack", 0)), int(rule.get("defense", 0)))
                    logs.append(f"{attacker.get('name')}越战越凶。")
            apply_battle_leave(defender, units, logs)
            continue
        counter = max(1, int(defender.get("attack", 1)))
        attacker["hp"] = int(attacker.get("hp", 0)) - counter
        logs.append(f"{defender.get('name')}反击，造成{counter}点。")
        if int(attacker.get("hp", 0)) <= 0:
            attacker["alive"] = False
            logs.append(f"{attacker.get('name')}离开战局。")
            apply_battle_leave(attacker, units, logs)
    left_alive = living(units, 1)
    right_alive = living(units, 2)
    if left_alive and not right_alive:
        winner = 1
        survivors = left_alive
    elif right_alive and not left_alive:
        winner = 2
        survivors = right_alive
    else:
        winner = 0
        survivors = left_alive + right_alive
    return {"winner": winner, "logs": logs[-18:], "survivors": survivors}


def team_players(table: dict[str, Any], team: int) -> list[dict[str, Any]]:
    return [player for player in table.get("players", []) if int(player.get("team", 1)) == team]


def survivor_damage(table: dict[str, Any], winners: list[dict[str, Any]], survivors: list[dict[str, Any]]) -> int:
    winner_ids = {str(player.get("id")) for player in winners}
    survivor_score = sum(int(unit.get("tier", 1)) for unit in survivors if str(unit.get("owner_id")) in winner_ids)
    peak = max([int(player.get("peak_level", 1)) for player in winners] or [1])
    return max(1, survivor_score + peak)


def apply_player_damage(player: dict[str, Any], damage: int) -> int:
    final_damage = leader_damage_taken(player, damage)
    player["health"] = max(0, int(player.get("health", BEAST_REALM_START_HEALTH)) - final_damage)
    mark_eliminated(player)
    return final_damage


def assign_match_teams(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[tuple[dict[str, Any], Any]]:
    saved: list[tuple[dict[str, Any], Any]] = []
    for player in left:
        saved.append((player, player.get("team")))
        player["team"] = 1
    for player in right:
        saved.append((player, player.get("team")))
        player["team"] = 2
    return saved


def restore_match_teams(saved: list[tuple[dict[str, Any], Any]]) -> None:
    for player, team in saved:
        if team is None:
            player.pop("team", None)
        else:
            player["team"] = team


def match_name(players: list[dict[str, Any]]) -> str:
    return "、".join(str(player.get("name")) for player in players) or "空阵"


def resolve_match(table: dict[str, Any], left: list[dict[str, Any]], right: list[dict[str, Any]], title: str) -> list[str]:
    saved = assign_match_teams(left, right)
    try:
        result = resolve_battle(left, right)
    finally:
        restore_match_teams(saved)
    winner = int(result.get("winner", 0))
    survivors = list(result.get("survivors", []))
    lines = [f"【{title}】{match_name(left)}  vs  {match_name(right)}"]
    lines.extend(str(line) for line in result.get("logs", [])[-6:])
    if winner == 1:
        damage = survivor_damage(table, left, survivors)
        damage_logs = []
        for loser in right:
            if loser.get("bot"):
                continue
            final_damage = apply_player_damage(loser, damage)
            damage_logs.append(f"{loser.get('name')} 生命-{final_damage}（剩余{loser.get('health')}）")
        lines.append(f"胜者：{match_name(left)}｜攻击威压 {damage}" + ("｜" + "；".join(damage_logs) if damage_logs else ""))
    elif winner == 2:
        damage = survivor_damage(table, right, survivors)
        damage_logs = []
        for loser in left:
            if loser.get("bot"):
                continue
            final_damage = apply_player_damage(loser, damage)
            damage_logs.append(f"{loser.get('name')} 生命-{final_damage}（剩余{loser.get('health')}）")
        lines.append(f"胜者：{match_name(right)}｜攻击威压 {damage}" + ("｜" + "；".join(damage_logs) if damage_logs else ""))
    else:
        lines.append("双方战平，本场无人受创。")
    eliminated = [player for player in left + right if not player.get("bot") and player.get("eliminated")]
    for player in eliminated:
        lines.append(f"{player.get('name')} 血量归零，已被淘汰。")
    return lines


def ranked_pairings(players: list[dict[str, Any]]) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], Optional[dict[str, Any]]]:
    pool = list(players)
    random.shuffle(pool)
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    while len(pool) >= 2:
        pairs.append((pool.pop(0), pool.pop(0)))
    bye = pool[0] if pool else None
    return pairs, bye


def ranking_lines(table: dict[str, Any]) -> list[str]:
    players = active_human_players(table)
    ranked = sorted(players, key=lambda item: (0 if is_player_alive(item) else 1, -int(item.get("health", 0)), -int(item.get("peak_level", 1))))
    lines = ["【当前排名】"]
    for index, player in enumerate(ranked, start=1):
        state = "存活" if is_player_alive(player) else "淘汰"
        lines.append(f"{index}. {player.get('name')}｜{state}｜生命{player.get('health', 0)}｜任务堂{BEAST_REALM_TIERS[int(player.get('peak_level', 1)) - 1]}")
    return lines


def resolve_round(table: dict[str, Any]) -> str:
    table["phase"] = "battle"
    mode = str(table.get("mode", "pve"))
    turn = int(table.get("turn", 1))
    lines = [f"【御兽秘境战报·第{turn}回合】", f"模式：{mode_label(mode)}"]

    if mode == "pvp":
        alive = live_human_players(table)
        if len(alive) <= 1:
            table["phase"] = "ended"
            lines.append("排位战已无足够对手。")
            lines.extend(ranking_lines(table))
        else:
            pairs, bye = ranked_pairings(alive)
            for index, (left, right) in enumerate(pairs, start=1):
                lines.extend(resolve_match(table, [left], [right], f"排位战 {index}"))
            if bye:
                lines.append(f"{bye.get('name')} 本回合轮空。")
            alive_after = live_human_players(table)
            lines.extend(ranking_lines(table))
            if len(alive_after) <= 1 or turn >= BEAST_REALM_MAX_TURNS:
                table["phase"] = "ended"
                winner = alive_after[0] if len(alive_after) == 1 else max(active_human_players(table), key=lambda item: int(item.get("health", 0)))
                lines.append(f"排位战结束，胜者：{winner.get('name')}。")
            else:
                prepare_round(table)
                lines.append("")
                lines.append(start_round_text(table))
    elif mode == "solo_pve":
        humans = live_human_players(table)
        if not humans:
            table["phase"] = "ended"
            lines.append("独行修士已被淘汰，1V2试炼失败。")
        else:
            enemies = list(table.get("enemies", [])) or create_pve_enemies(turn, 2, table)
            lines.extend(resolve_match(table, [humans[0]], enemies[:2], "1V2试炼"))
            if not live_human_players(table):
                table["phase"] = "ended"
                lines.append("独行修士血量归零，1V2试炼失败。")
            elif turn >= BEAST_REALM_MAX_TURNS:
                table["phase"] = "ended"
                lines.append("第八轮试炼已过，1V2单人PVE通关！")
            else:
                prepare_round(table)
                lines.append("")
                lines.append(start_round_text(table))
    else:
        humans = live_human_players(table)
        enemies = list(table.get("enemies", [])) or create_pve_enemies(turn, max(1, len(humans)), table)
        if not humans:
            table["phase"] = "ended"
            lines.append("所有修士均已淘汰，PVE演武失败。")
        else:
            for index, player in enumerate(humans):
                enemy = enemies[index % len(enemies)]
                lines.extend(resolve_match(table, [player], [enemy], f"PVE对阵 {index + 1}"))
            health_text = "；".join(f"{player.get('name')} {player.get('health')}" for player in active_human_players(table))
            lines.append(f"修士生命：{health_text}")
            if not live_human_players(table):
                table["phase"] = "ended"
                lines.append("所有修士均已淘汰，PVE演武失败。")
            elif turn >= BEAST_REALM_MAX_TURNS:
                table["phase"] = "ended"
                lines.append("第八轮兽潮已破，御兽秘境通关！")
            else:
                prepare_round(table)
                lines.append("")
                lines.append(start_round_text(table))
    table["last_report"] = "\n".join(lines)
    return table["last_report"]

def status_text(table: dict[str, Any]) -> str:
    if table.get("phase") == "lobby":
        return lobby_text(table)
    lines = [f"【御兽秘境状态】第{table.get('turn', 1)}回合｜{mode_label(str(table.get('mode', 'pve')))}"]
    for player in active_human_players(table):
        state = "存活" if is_player_alive(player) else "淘汰"
        lines.append(
            f"{player.get('name')}｜{state}｜{leader_status(player)}｜生命{player.get('health')}/{player.get('max_health', player.get('health'))}｜"
            f"{BEAST_REALM_TIERS[int(player.get('peak_level', 1)) - 1]}｜随从{len(player.get('board', []))}｜"
            f"{'已准备' if player.get('ready') else '招募中'}"
        )
    if str(table.get("mode")) == "pvp" and table.get("phase") != "ended":
        lines.extend(ranking_lines(table))
    return "\n".join(lines)
