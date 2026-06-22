from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Optional, TypeVar

QUALITY_TIER_POOL = [
    ("天阶", 4, 0.04),
    ("地阶", 3, 0.12),
    ("玄阶", 2, 0.24),
    ("黄阶", 1, 0.38),
    ("凡品", 0, 0.22),
]

GRADE_POOL = [
    ("极品", 3, 0.08),
    ("上品", 2, 0.22),
    ("中品", 1, 0.35),
    ("下品", 0, 0.35),
]

TIER_ORDER = ["凡品", "黄阶", "玄阶", "地阶", "天阶"]
GRADE_ORDER = ["下品", "中品", "上品", "极品"]
TIER_RANKS = {name: rank for name, rank, _ in QUALITY_TIER_POOL}
GRADE_RANKS = {name: rank for name, rank, _ in GRADE_POOL}

ATTRIBUTES = ["金", "木", "水", "火", "土", "雷", "冰"]

ATTRIBUTE_COLORS = {
    "金": "#d9a441",
    "木": "#36a269",
    "水": "#3589d8",
    "火": "#e35343",
    "土": "#a97843",
    "雷": "#7c5ce6",
    "冰": "#4db9d7",
}

ATTRIBUTE_NAMES = {
    "金": "金灵根",
    "木": "木灵根",
    "水": "水灵根",
    "火": "火灵根",
    "土": "土灵根",
    "雷": "雷灵根",
    "冰": "冰灵根",
}

REALMS = [
    '炼体期',
    '练气期',
    '筑基期',
    '金丹期',
    '元婴期',
    '化神期',
    '炼虚期',
    '合体期',
    '大乘期',
    '渡劫期',
    '真仙境',
    '金仙境',
    '太乙境',
    '大罗境',
    '混元金仙境',
    '准圣境',
    '圣人境',
    '混元大罗金仙境',
    '混元无极大罗金仙境',
    '天道境',
    '大道境',
    '道祖境',
    '半步超脱',
    '超脱境',
    '永恒境',
]


REWARD_TIERS = ["天阶", "地阶", "玄阶", "黄阶", "凡品"]
REWARD_CATEGORIES = [
    "仙缘",
    "灵器",
    "功法",
    "丹药",
    "阵盘",
    "灵材",
    "符箓",
    "傀儡",
    "灵植",
    "灵石",
    "杂物",
    "奇物",
    "灵食",
]
REWARD_MIN_COUNTS = {"仙缘": 5, "阵盘": 3, "灵器": 7, "功法": 7}
REWARD_GRADES_BY_COUNT = {
    2: ["上品", "中品"],
    3: ["极品", "上品", "中品"],
    5: ["极品", "上品", "中品", "下品", "极品"],
    7: ["极品", "上品", "中品", "下品", "上品", "中品", "下品"],
}
REWARD_TIER_WEIGHTS = {
    "天阶": 6,
    "地阶": 18,
    "玄阶": 48,
    "黄阶": 95,
    "凡品": 135,
}
REWARD_CATEGORY_WEIGHT_RATIO = {
    "仙缘": 0.45,
    "灵器": 0.75,
    "功法": 0.8,
    "阵盘": 0.9,
    "灵材": 0.9,
    "奇物": 0.95,
}
REWARD_DESCRIPTIONS = {
    "仙缘": "天地机缘凝成的{name}，可为修行添一线逆天命数。",
    "灵器": "{name}灵光内敛，装备后可计入战力。",
    "功法": "{name}玄妙难言，参悟后可增添斗法底蕴。",
    "丹药": "{name}药香沉稳，适合闭关修行时服用。",
    "阵盘": "{name}阵纹流转，可布置洞府、护身或困敌。",
    "灵材": "{name}灵性充盈，是炼器炼丹都爱收的材料。",
    "符箓": "{name}朱纹未散，关键时刻可借一缕法力。",
    "傀儡": "{name}机关精巧，可随身辅助历练。",
    "灵植": "{name}生机盎然，移入洞府可慢慢蕴养。",
    "灵石": "{name}灵气充足，是修行界最朴素也最实在的快乐。",
    "杂物": "{name}来历不明，细看又似乎藏着一点门道。",
    "奇物": "{name}气息古怪，说不上用途但绝非凡品。",
    "灵食": "{name}入口温和，可补充气血与灵力。",
}
FISHING_REWARD_NAMES = {
    "仙缘": {
        "天阶": ["鸿蒙一气", "混沌莲胎", "大道真种", "太初仙契", "造化玉露"],
        "地阶": ["洞天福脉", "星河道胎", "玄黄命砂", "青莲仙引", "云海灵契"],
        "玄阶": ["古洞机缘", "残碑悟道", "月华灵髓", "雾隐仙芽", "灵台清光"],
        "黄阶": ["山神馈赠", "灵泉一盏", "旧庙香火", "药园残运", "云游道人指点"],
        "凡品": ["半页机缘签", "梦里仙人一笑", "井底月光", "小摊旧铜钱", "破庙避雨缘"],
    },
    "灵器": {
        "天阶": ["九霄镇海印", "太虚斩星剑"],
        "地阶": ["青冥飞剑", "玄都镇魂铃"],
        "玄阶": ["寒铁护心镜", "流云缚妖索"],
        "黄阶": ["赤铜伏魔杖", "青竹听风剑"],
        "凡品": ["外门铁剑", "木柄小灵锤"],
    },
    "功法": {
        "天阶": ["太虚观想篇", "万象归元经"],
        "地阶": ["沧海听雷诀", "九转炼神录"],
        "玄阶": ["碧落御风诀", "青木长生功"],
        "黄阶": ["小周天吐纳术", "烈阳锻体篇"],
        "凡品": ["半卷残破剑谱", "外门入静诀"],
    },
    "丹药": {
        "天阶": ["九转凝神丹", "太清渡厄丹"],
        "地阶": ["玉髓化元丹", "紫府养魂丹"],
        "玄阶": ["培元丹", "洗髓小还丹"],
        "黄阶": ["聚气丸", "回春散"],
        "凡品": ["辟谷小丸", "苦口补气散"],
    },
    "阵盘": {
        "天阶": ["周天星斗阵盘", "太虚锁界盘", "九曜归墟盘"],
        "地阶": ["四象护山盘", "玄武镇宅盘", "青龙引雷盘"],
        "玄阶": ["小五行聚灵盘", "云纹迷踪盘", "水月镜花盘"],
        "黄阶": ["三才守门盘", "风火警戒盘", "土行稳基盘"],
        "凡品": ["石子迷阵盘", "草绳护院盘", "旧木罗盘"],
    },
    "灵材": {
        "天阶": ["混沌星砂", "太白仙金"],
        "地阶": ["星陨玄铁", "玄冰玉髓"],
        "玄阶": ["赤霞铜精", "青藤灵骨"],
        "黄阶": ["百炼寒铁", "紫纹灵木"],
        "凡品": ["发亮矿渣", "溪边圆石"],
    },
    "符箓": {
        "天阶": ["乾坤挪移符", "太上清宁符"],
        "地阶": ["小挪移符", "五雷辟邪符"],
        "玄阶": ["御风疾影符", "金甲护身符"],
        "黄阶": ["疾行符", "清心符"],
        "凡品": ["歪字护身符", "外门传讯符"],
    },
    "傀儡": {
        "天阶": ["天工镇魔傀", "星河巡界傀"],
        "地阶": ["银甲护法傀", "玄玉药童傀"],
        "玄阶": ["星纹寻灵傀", "青铜搬山傀"],
        "黄阶": ["木甲巡山傀", "小型采药傀"],
        "凡品": ["缺臂木傀", "会点头的草傀"],
    },
    "灵植": {
        "天阶": ["九叶仙莲", "悟道古茶枝"],
        "地阶": ["紫纹灵参", "月照灵芝"],
        "玄阶": ["碧玉灵竹", "赤霞火枣"],
        "黄阶": ["百年朱果", "凝露灵草"],
        "凡品": ["半枯灵苗", "小盆清心草"],
    },
    "灵石": {
        "天阶": ["极品仙晶匣", "星核灵晶"],
        "地阶": ["上品灵石匣", "地脉灵髓石"],
        "玄阶": ["中品灵石袋", "流光灵玉"],
        "黄阶": ["一袋下品灵石", "灵砂小匣"],
        "凡品": ["碎灵石把", "微光碎晶"],
    },
    "杂物": {
        "天阶": ["无字天书匣", "仙府门环"],
        "地阶": ["无名洞府钥匙", "旧仙舟舵盘"],
        "玄阶": ["古修士酒葫芦", "裂纹传功玉"],
        "黄阶": ["破旧丹炉盖", "无主储物袋"],
        "凡品": ["外门扫帚", "磨损练功木牌"],
    },
    "奇物": {
        "天阶": ["昆仑镜碎光", "逆命铜铃"],
        "地阶": ["会自己翻页的书", "星砂沙漏"],
        "玄阶": ["会发光的圆石", "低语玉佩"],
        "黄阶": ["不熄小灯", "自热茶盏"],
        "凡品": ["只响一次的铃铛", "没字的竹简"],
    },
    "灵食": {
        "天阶": ["九霞玉露羹", "星髓仙酿"],
        "地阶": ["玉露灵糕", "紫米蕴神饭"],
        "玄阶": ["清心莲子羹", "火枣灵酥"],
        "黄阶": ["辟谷饼", "灵麦汤"],
        "凡品": ["干硬辟谷饼", "外门粗粮糕"],
    },
}

ARTIFACT_NAMES_BY_TIER_ATTR = {
    "天阶": {"金": "太虚斩星剑", "木": "青帝长生杖", "水": "九霄镇海印", "火": "焚天离火旗", "土": "山河社稷印", "雷": "紫霄御雷槌", "冰": "玄冥封天镜"},
    "地阶": {"金": "青冥飞剑", "木": "万木回春尺", "水": "沧海分潮珠", "火": "赤阳炼魔炉", "土": "玄都镇魂铃", "雷": "五雷荡邪鼓", "冰": "寒魄凝霜环"},
    "玄阶": {"金": "寒铁护心镜", "木": "青藤缚妖索", "水": "水月流光佩", "火": "赤霞焚影刀", "土": "厚土镇岳盾", "雷": "奔雷破阵枪", "冰": "凝冰照影针"},
    "黄阶": {"金": "赤铜伏魔杖", "木": "青竹听风剑", "水": "碧波纳气瓶", "火": "烈焰短戟", "土": "黄玉护身符", "雷": "引雷桃木剑", "冰": "霜纹短刃"},
    "凡品": {"金": "外门铁剑", "木": "木柄小灵锤", "水": "清水符瓶", "火": "火折灵灯", "土": "粗陶护心坠", "雷": "响雷铜铃", "冰": "薄冰小镜"},
}

METHOD_NAMES_BY_TIER_ATTR = {
    "天阶": {"金": "太白斩星经", "木": "青帝长生经", "水": "玄冥归海经", "火": "焚天真阳录", "土": "厚土载道篇", "雷": "紫霄神雷诀", "冰": "太阴玄冰录"},
    "地阶": {"金": "庚金剑典", "木": "万木回春功", "水": "沧海听雷诀", "火": "离火炼神诀", "土": "玄黄镇岳功", "雷": "五雷正法", "冰": "寒魄凝真诀"},
    "玄阶": {"金": "金锋破云诀", "木": "青木长生功", "水": "碧海潮生诀", "火": "赤霞炼气篇", "土": "山岳稳基法", "雷": "奔雷锻脉诀", "冰": "霜华凝息术"},
    "黄阶": {"金": "锐金吐纳术", "木": "草木养气诀", "水": "小云雨诀", "火": "烈阳锻体篇", "土": "黄庭培元功", "雷": "引雷入门诀", "冰": "寒息入静篇"},
    "凡品": {"金": "半卷残破剑谱", "木": "外门植木诀", "水": "溪畔纳气术", "火": "灶火炼身法", "土": "外门入静诀", "雷": "听雷杂记", "冰": "冷泉静坐法"},
}

FISHING_REWARD_NAMES["灵器"] = {
    tier: [attr_map[attr] for attr in ATTRIBUTES]
    for tier, attr_map in ARTIFACT_NAMES_BY_TIER_ATTR.items()
}
FISHING_REWARD_NAMES["功法"] = {
    tier: [attr_map[attr] for attr in ATTRIBUTES]
    for tier, attr_map in METHOD_NAMES_BY_TIER_ATTR.items()
}
FISHING_REWARD_NAMES["丹药"] = {
    "天阶": ["筑基丹", "大还丹", "元婴丹", "九转凝神丹", "太清渡厄丹"],
    "地阶": ["筑基丹", "大还丹", "元婴丹", "玉髓化元丹", "紫府养魂丹"],
    "玄阶": ["筑基丹", "小还丹", "元婴丹", "培元丹", "洗髓小还丹"],
    "黄阶": ["筑基丹", "小还丹", "聚气丸", "回春散", "凝气散"],
    "凡品": ["筑基丹", "小还丹", "辟谷小丸", "苦口补气散", "粗炼补元丸"],
}
FISHING_REWARD_NAMES["奇物"] = {
    '天阶': ['化凡意境', '破虚灵引', '合道残章', '大乘道果', '大罗天契', '混元道果', '鸿蒙紫气', '混元真印', '无极道种', '天道权柄', '大道本源', '永恒真名'],
    '地阶': ['化凡意境', '破虚灵引', '渡劫令', '仙门符诏', '金性道果', '斩尸灵宝', '道祖法旨', '超脱契机', '命河断契'],
    '玄阶': ['化凡意境', '合道残章', '太乙玄光', '星砂沙漏', '低语玉佩'],
    '黄阶': ['化凡意境', '不熄小灯', '自热茶盏', '破境石', '醒神玉'],
    '凡品': ['化凡意境', '只响一次的铃铛', '没字的竹简', '旧木令', '无名石片'],
}
FISHING_REWARD_NAMES["灵材"] = {
    "天阶": ["混沌星砂", "太白仙金", "天髓玉露", "九转玄参", "悟道茶心"],
    "地阶": ["星陨玄铁", "玄冰玉髓", "紫府灵芝", "月华凝露", "地脉火芝"],
    "玄阶": ["赤霞铜精", "青藤灵骨", "金纹灵芝", "冰魄花蕊", "雷击灵木"],
    "黄阶": ["百炼寒铁", "紫纹灵木", "凝露草", "火枣核", "土精砂"],
    "凡品": ["发亮矿渣", "溪边圆石", "清心草叶", "灵麦芽", "苦参须"],
}


ITEM_ATTRIBUTE_BY_NAME = {}
for _tier, _items in ARTIFACT_NAMES_BY_TIER_ATTR.items():
    for _attribute, _name in _items.items():
        ITEM_ATTRIBUTE_BY_NAME[_name] = _attribute
for _tier, _items in METHOD_NAMES_BY_TIER_ATTR.items():
    for _attribute, _name in _items.items():
        ITEM_ATTRIBUTE_BY_NAME[_name] = _attribute

BREAKTHROUGH_REQUIREMENTS = {
    1: {"items": ['筑基丹'], "target": '筑基期', "kind": 'foundation'},
    2: {"items": ['小还丹', '大还丹'], "target": '金丹期', "kind": 'pill'},
    3: {"items": ['元婴丹'], "target": '元婴期', "kind": 'pill'},
    4: {"items": ['化凡意境'], "target": '化神期', "kind": 'insight'},
    5: {"items": ['破虚灵引'], "target": '炼虚期', "kind": 'insight'},
    6: {"items": ['合道残章'], "target": '合体期', "kind": 'insight'},
    7: {"items": ['大乘道果'], "target": '大乘期', "kind": 'insight'},
    8: {"items": ['渡劫令'], "target": '渡劫期', "kind": 'insight'},
    9: {"items": ['仙门符诏'], "target": '真仙境', "kind": 'insight'},
    10: {"items": ['金性道果'], "target": '金仙境', "kind": 'insight'},
    11: {"items": ['太乙玄光'], "target": '太乙境', "kind": 'insight'},
    12: {"items": ['大罗天契'], "target": '大罗境', "kind": 'insight'},
    13: {"items": ['混元道果'], "target": '混元金仙境', "kind": 'insight'},
    14: {"items": ['斩尸灵宝'], "target": '准圣境', "kind": 'insight'},
    15: {"items": ['鸿蒙紫气'], "target": '圣人境', "kind": 'insight'},
    16: {"items": ['混元真印'], "target": '混元大罗金仙境', "kind": 'insight'},
    17: {"items": ['无极道种'], "target": '混元无极大罗金仙境', "kind": 'insight'},
    18: {"items": ['天道权柄'], "target": '天道境', "kind": 'insight'},
    19: {"items": ['大道本源'], "target": '大道境', "kind": 'insight'},
    20: {"items": ['道祖法旨'], "target": '道祖境', "kind": 'insight'},
    21: {"items": ['超脱契机'], "target": '半步超脱', "kind": 'insight'},
    22: {"items": ['命河断契'], "target": '超脱境', "kind": 'insight'},
    23: {"items": ['永恒真名'], "target": '永恒境', "kind": 'insight'},
}


INSTANT_EXP_BASE = {"凡品": 26, "黄阶": 52, "玄阶": 96, "地阶": 168, "天阶": 280}
CONSUMABLE_EXP_BASE = {"凡品": 18, "黄阶": 36, "玄阶": 72, "地阶": 128, "天阶": 220}
GRADE_EXP_RATIO = {"下品": 1.0, "中品": 1.18, "上品": 1.38, "极品": 1.72}
METHOD_SIGN_RATE = {"凡品": 0.08, "黄阶": 0.12, "玄阶": 0.18, "地阶": 0.26, "天阶": 0.38}
METHOD_CHAT_BASE = {"凡品": 0.35, "黄阶": 0.55, "玄阶": 0.85, "地阶": 1.25, "天阶": 1.8}
EQUIPMENT_CATEGORIES = {"灵器", "功法", "阵盘"}
ARTIFACT_CATEGORY = "灵器"
METHOD_CATEGORY = "功法"
ARRAY_CATEGORY = "阵盘"
PILL_CATEGORY = "丹药"
TALISMAN_CATEGORY = "符箓"
PUPPET_CATEGORY = "傀儡"
PLANT_CATEGORY = "灵植"
SPIRIT_STONE_CATEGORY = "灵石"
MISC_CATEGORY = "杂物"
CURIO_CATEGORY = "奇物"
FOOD_CATEGORY = "灵食"

MYSTIC_REALM_TYPES = ("上古宗门遗址", "兽潮", "上古大能洞府")
MYSTIC_REALM_MAX_STEPS = 10
BEAST_NAME_PREFIXES = ["赤焰", "玄霜", "碧鳞", "噬月", "裂山", "幽冥", "金瞳", "雷角", "青翼", "血纹"]
BEAST_NAME_SUFFIXES = ["妖虎", "蛟王", "灵猿", "玄龟", "魔狼", "狮鹫", "蛇君", "古象", "鹰王", "蜃兽"]
MYSTIC_OPTION_POOLS = {
    "上古宗门遗址": ["推开藏经阁残门", "沿断裂剑痕前行", "参拜无名祖师像", "踏入荒废丹房", "接受问心石考验", "绕过坍塌回廊", "检查残破传功玉"],
    "兽潮": ["正面冲击兽群", "绕行寻找首领气息", "设阵固守片刻", "救下受困散修", "追踪妖兽脚印", "潜入巢穴深处", "采集兽潮后的灵材"],
    "上古大能洞府": ["触碰洞府石门禁制", "点亮长明古灯", "翻看蒲团旁玉简", "踏上白玉阶", "以灵力试探阵眼", "进入静室闭目感应", "检查沉默的宝匣"],
}

SPIRIT_STONE_VALUES = {"凡品": 6, "黄阶": 14, "玄阶": 32, "地阶": 72, "天阶": 160}
PUPPET_POWER_RATE = {"凡品": 0.45, "黄阶": 0.6, "玄阶": 0.78, "地阶": 0.95, "天阶": 1.15}
PLANT_SIGN_RATE = {"凡品": 0.06, "黄阶": 0.1, "玄阶": 0.16, "地阶": 0.24, "天阶": 0.34}
CULTIVATION_ROUTES = ("剑修", "术修", "炼丹师", "阵法师")
FACTION_IDENTITIES = (
    "天机阁弟子",
    "天机阁长老",
    "天机阁太上长老",
    "合欢宗弟子",
    "合欢宗长老",
    "合欢宗太上长老",
)
TIANJI_COOLDOWN_DAYS = {"天机阁弟子": 7, "天机阁长老": 5, "天机阁太上长老": 1}
HEHUAN_DAILY_LIMITS = {"合欢宗弟子": 1, "合欢宗长老": 2, "合欢宗太上长老": 5}
ITEM_PRICE_BASE = {
    "仙缘": 160,
    "灵器": 220,
    "功法": 240,
    "丹药": 90,
    "阵盘": 180,
    "灵材": 70,
    "符箓": 72,
    "傀儡": 160,
    "灵植": 130,
    "灵石": 60,
    "杂物": 28,
    "奇物": 190,
    "灵食": 46,
}
TIER_PRICE_RATIO = {"凡品": 1, "黄阶": 3, "玄阶": 9, "地阶": 27, "天阶": 81}
GRADE_PRICE_RATIO = {"下品": 1.0, "中品": 1.22, "上品": 1.55, "极品": 2.1}
TIER_REALM_REQUIREMENT = {"凡品": 0, "黄阶": 0, "玄阶": 3, "地阶": 4, "天阶": 5}
ALCHEMY_RECIPES = {
    "筑基丹": {"tier": "黄阶", "grade": "中品", "materials": ["凝露草", "清心草叶", "百年朱果"], "cost": 80},
    "小还丹": {"tier": "玄阶", "grade": "中品", "materials": ["金纹灵芝", "火枣核", "紫纹灵木"], "cost": 180},
    "大还丹": {"tier": "地阶", "grade": "上品", "materials": ["紫府灵芝", "月华凝露", "地脉火芝"], "cost": 480},
    "元婴丹": {"tier": "地阶", "grade": "极品", "materials": ["玄冰玉髓", "紫府灵芝", "星陨玄铁"], "cost": 680},
    "九转凝神丹": {"tier": "天阶", "grade": "上品", "materials": ["九转玄参", "悟道茶心", "天髓玉露"], "cost": 1400},
    "太清渡厄丹": {"tier": "天阶", "grade": "极品", "materials": ["天髓玉露", "混沌星砂", "悟道茶心"], "cost": 2200},
}
DAILY_TASK_TEMPLATES = [
    "{realm}山门巡夜，清点护山禁制",
    "替外门弟子演示{realm}吐纳法",
    "前往坊市护送一批灵材",
    "在灵田中拔除噬灵杂草",
    "整理藏经阁残卷并标注疑难处",
    "为炼丹房守炉两个时辰",
    "追查附近失控的聚灵阵",
    "替宗门长老送一封飞剑传书",
    "在后山采集晨露与灵草",
    "陪同师兄弟演练斗法阵型",
    "镇守山门，盘查来往散修",
    "清理废弃洞府中的阴寒浊气",
    "记录灵兽园妖兽进食异动",
    "修补一处裂开的护院阵纹",
    "替同门压制丹毒反噬",
    "护送商队穿过妖雾山径",
    "调查夜半钟声的来源",
    "在问心石前完成一次静坐",
    "替宗门收取附近灵泉水脉",
    "清点库房中新入的符箓",
    "参与一次小型宗门讲法",
    "试炼新铸灵器的稳定性",
    "封存一件来历不明的奇物",
    "替阵法师绘制阵眼方位图",
    "在丹霞谷外围巡查火脉",
    "协助药童分拣不同年份灵植",
    "为新入门弟子讲解门规",
    "查验灵石账册中的缺漏",
    "追踪一只偷吃灵麦的妖兽",
    "在练功场完成百次剑式推演",
] * 10


def fishing_reward_weight(tier: str, category: str, index: int) -> int:
    base = REWARD_TIER_WEIGHTS[tier]
    ratio = REWARD_CATEGORY_WEIGHT_RATIO.get(category, 1.0)
    return max(1, int(base * ratio * (1 + index * 0.06)))


def build_fishing_rewards() -> list[tuple[str, str, str, str, str, int]]:
    rewards = []
    for category in REWARD_CATEGORIES:
        tier_map = FISHING_REWARD_NAMES.get(category, {})
        minimum = REWARD_MIN_COUNTS.get(category, 2)
        grades = REWARD_GRADES_BY_COUNT[minimum]
        for tier in REWARD_TIERS:
            names = tier_map.get(tier, [])
            if len(names) < minimum:
                raise RuntimeError(f"{category}{tier} 奖池数量不足：{len(names)}/{minimum}")
            for index, name in enumerate(names):
                grade = grades[index % len(grades)]
                description = REWARD_DESCRIPTIONS[category].format(name=name)
                weight = fishing_reward_weight(tier, category, index)
                rewards.append((tier, grade, category, name, description, weight))
    return rewards


FISHING_REWARDS = build_fishing_rewards()

ARTIFACT_POWER_BASE = {
    "天阶": 2800,
    "地阶": 1800,
    "玄阶": 1050,
    "黄阶": 520,
    "凡品": 180,
}
ARTIFACT_GRADE_RATIO = {
    "极品": 1.45,
    "上品": 1.25,
    "中品": 1.12,
    "下品": 1.0,
}
DUEL_ACTIONS = {
    "金": "剑气横生，锋芒逼人",
    "木": "青藤绕阵，生机绵长",
    "水": "水幕化潮，攻守相生",
    "火": "烈焰成环，炽意冲霄",
    "土": "厚土为垒，稳如山岳",
    "雷": "雷光乍裂，瞬息破势",
    "冰": "寒霜封路，寸步难移",
}

CONFIRM_WORDS = {
    "是",
    "好",
    "好的",
    "可以",
    "行",
    "冲",
    "抽",
    "垂钓",
    "钓",
    "来",
    "来一次",
    "十连",
    "10连",
    "十连抽",
    "y",
    "yes",
    "ok",
    "嗯",
}

CANCEL_WORDS = {"否", "不", "不了", "算了", "n", "no", "取消"}

T = TypeVar("T")


@dataclass
class Root:
    tier: str
    tier_rank: int
    grade: str
    grade_rank: int
    attribute: str

    @property
    def display_name(self) -> str:
        return f"{self.tier}{self.grade}{ATTRIBUTE_NAMES[self.attribute]}"

    @property
    def color(self) -> str:
        return ATTRIBUTE_COLORS[self.attribute]

    @property
    def progress_required(self) -> int:
        tier_base = {
            "天阶": 100,
            "地阶": 115,
            "玄阶": 135,
            "黄阶": 155,
            "凡品": 180,
        }.get(self.tier, 155)
        grade_extra = {
            "极品": 0,
            "上品": 10,
            "中品": 20,
            "下品": 30,
        }.get(self.grade, 20)
        return tier_base + grade_extra

    @property
    def exp_gain_range(self) -> tuple[int, int]:
        low = 6 + self.tier_rank * 3 + self.grade_rank
        high = 10 + self.tier_rank * 5 + self.grade_rank * 2
        return low, high

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "tier_rank": self.tier_rank,
            "grade": self.grade,
            "grade_rank": self.grade_rank,
            "attribute": self.attribute,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Root:
        tier = str(data["tier"])
        if tier == "路人甲":
            tier = "凡品"
        return cls(
            tier=tier,
            tier_rank=TIER_RANKS.get(tier, int(data["tier_rank"])),
            grade=str(data["grade"]),
            grade_rank=int(data["grade_rank"]),
            attribute=str(data["attribute"]),
        )


@dataclass
class EncounterResult:
    happened: bool = False
    success: bool = False
    message: str = ""
    old_root: Optional[Root] = None
    new_root: Optional[Root] = None
    added_root: Optional[Root] = None


@dataclass
class RankReward:
    rank: int
    exp: int
    fishing_chances: int = 0
    pending: bool = False
    leveled_realms: int = 0

    @property
    def label(self) -> str:
        parts = [f"+{self.exp} 修为"]
        if self.fishing_chances:
            parts.append(f"+{self.fishing_chances} 垂钓")
        if self.pending:
            parts.append("暂存")
        return "，".join(parts)


@dataclass
class DuelResult:
    attacker_power: int
    defender_power: int
    attacker_win: bool
    chance: float
    detail: str

    @property
    def winner_side(self) -> str:
        return "attacker" if self.attacker_win else "defender"


@dataclass
class UserRecord:
    user_id: str
    root: Optional[Root] = None
    sign_count: int = 0
    total_exp: int = 0
    realm_index: int = 0
    realm_exp: int = 0
    last_sign_date: Optional[str] = None
    last_encounter_date: Optional[str] = None
    fishing_chances: int = 0
    pending_fishing: int = 0
    pending_exp: int = 0
    rewards: Optional[list[dict[str, Any]]] = None
    equipped_artifact: Optional[dict[str, Any]] = None
    equipped_method: Optional[dict[str, Any]] = None
    equipped_array: Optional[dict[str, Any]] = None
    equipped_puppet: Optional[dict[str, Any]] = None
    planted_spirit_plant: Optional[dict[str, Any]] = None
    array_proficiency: Optional[dict[str, int]] = None
    spirit_stones: int = 0
    foundation_type: Optional[str] = None
    realm_marks: Optional[dict[str, str]] = None
    extra_roots: Optional[list[Root]] = None
    mystic_realm: Optional[dict[str, Any]] = None
    cultivation_lock_until: Optional[str] = None
    cultivation_route: Optional[str] = None
    evil_cultivator: bool = False
    faction_identity: Optional[str] = None
    identity_sign_days: Optional[dict[str, int]] = None
    daily_tasks: Optional[dict[str, Any]] = None
    dual_cultivation_date: Optional[str] = None
    dual_cultivation_used: int = 0
    last_tianji_mystic_date: Optional[str] = None

    @property
    def realm_name(self) -> str:
        return REALMS[min(self.realm_index, len(REALMS) - 1)]

    @property
    def realm_stage(self) -> str:
        return realm_stage(self)

    @property
    def realm(self) -> str:
        return f"{self.realm_name}{self.realm_stage}"

    @property
    def progress_required(self) -> int:
        if self.root is None:
            return 100
        return self.root.progress_required

    @property
    def roots(self) -> list[Root]:
        result = []
        if self.root:
            result.append(self.root)
        result.extend(self.extra_roots or [])
        return result

    @property
    def root_attributes(self) -> set[str]:
        return {root.attribute for root in self.roots}

    @property
    def root_summary(self) -> str:
        if self.root is None:
            return "\u672a\u89c9\u9192\u7075\u6839"
        extras = [ATTRIBUTE_NAMES[root.attribute] for root in self.extra_roots or []]
        if not extras:
            return self.root.display_name
        return f"{self.root.display_name} + {'/'.join(extras)}"

    @property
    def is_peak_aptitude(self) -> bool:
        return bool(self.root and self.root.tier == "\u5929\u9636" and self.root.grade == "\u6781\u54c1")

    @property
    def is_bottleneck(self) -> bool:
        return is_breakthrough_bottleneck(self)

    @property
    def realm_quality(self) -> str:
        return realm_quality_text(self)

    @property
    def cultivation_locked(self) -> bool:
        return is_cultivation_locked(self)

    @property
    def route_summary(self) -> str:
        base = self.cultivation_route or "未选择路线"
        return f"{base}+邪修" if self.evil_cultivator else base

    @property
    def identity_summary(self) -> str:
        return self.faction_identity or "暂无身份"

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "root": self.root.to_dict() if self.root else None,
            "sign_count": self.sign_count,
            "total_exp": self.total_exp,
            "realm_index": self.realm_index,
            "realm_exp": self.realm_exp,
            "last_sign_date": self.last_sign_date,
            "last_encounter_date": self.last_encounter_date,
            "fishing_chances": self.fishing_chances,
            "pending_fishing": self.pending_fishing,
            "pending_exp": self.pending_exp,
            "rewards": self.rewards or [],
            "equipped_artifact": self.equipped_artifact or None,
            "equipped_method": self.equipped_method or None,
            "equipped_array": self.equipped_array or None,
            "equipped_puppet": self.equipped_puppet or None,
            "planted_spirit_plant": self.planted_spirit_plant or None,
            "array_proficiency": self.array_proficiency or {},
            "spirit_stones": self.spirit_stones,
            "foundation_type": self.foundation_type,
            "realm_marks": self.realm_marks or {},
            "extra_roots": [root.to_dict() for root in self.extra_roots or []],
            "mystic_realm": self.mystic_realm or None,
            "cultivation_lock_until": self.cultivation_lock_until,
            "cultivation_route": self.cultivation_route,
            "evil_cultivator": self.evil_cultivator,
            "faction_identity": self.faction_identity,
            "identity_sign_days": self.identity_sign_days or {},
            "daily_tasks": self.daily_tasks or None,
            "dual_cultivation_date": self.dual_cultivation_date,
            "dual_cultivation_used": self.dual_cultivation_used,
            "last_tianji_mystic_date": self.last_tianji_mystic_date,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserRecord:
        root_data = data.get("root")
        return cls(
            user_id=str(data["user_id"]),
            root=Root.from_dict(root_data) if root_data else None,
            sign_count=int(data.get("sign_count", 0)),
            total_exp=int(data.get("total_exp", 0)),
            realm_index=int(data.get("realm_index", 0)),
            realm_exp=int(data.get("realm_exp", 0)),
            last_sign_date=data.get("last_sign_date"),
            last_encounter_date=data.get("last_encounter_date"),
            fishing_chances=int(data.get("fishing_chances", 0)),
            pending_fishing=int(data.get("pending_fishing", 0)),
            pending_exp=int(data.get("pending_exp", 0)),
            rewards=list(data.get("rewards", [])),
            spirit_stones=int(data.get("spirit_stones", 0)),
            mystic_realm=(dict(data["mystic_realm"]) if isinstance(data.get("mystic_realm"), dict) else None),
            cultivation_lock_until=(str(data["cultivation_lock_until"]) if data.get("cultivation_lock_until") else None),
            cultivation_route=(str(data["cultivation_route"]) if data.get("cultivation_route") else None),
            evil_cultivator=bool(data.get("evil_cultivator", False)),
            faction_identity=(str(data["faction_identity"]) if data.get("faction_identity") else None),
            identity_sign_days={
                str(key): int(value)
                for key, value in dict(data.get("identity_sign_days", {})).items()
            },
            daily_tasks=(dict(data["daily_tasks"]) if isinstance(data.get("daily_tasks"), dict) else None),
            dual_cultivation_date=(str(data["dual_cultivation_date"]) if data.get("dual_cultivation_date") else None),
            dual_cultivation_used=int(data.get("dual_cultivation_used", 0)),
            last_tianji_mystic_date=(str(data["last_tianji_mystic_date"]) if data.get("last_tianji_mystic_date") else None),
            equipped_artifact=(
                dict(data["equipped_artifact"])
                if isinstance(data.get("equipped_artifact"), dict)
                else None
            ),
            equipped_method=(
                dict(data["equipped_method"])
                if isinstance(data.get("equipped_method"), dict)
                else None
            ),
            equipped_array=(
                dict(data["equipped_array"])
                if isinstance(data.get("equipped_array"), dict)
                else None
            ),
            equipped_puppet=(
                dict(data["equipped_puppet"])
                if isinstance(data.get("equipped_puppet"), dict)
                else None
            ),
            planted_spirit_plant=(
                dict(data["planted_spirit_plant"])
                if isinstance(data.get("planted_spirit_plant"), dict)
                else None
            ),
            array_proficiency={
                str(key): int(value)
                for key, value in dict(data.get("array_proficiency", {})).items()
            },
            foundation_type=(
                str(data["foundation_type"])
                if data.get("foundation_type")
                else None
            ),
            realm_marks={
                str(key): str(value)
                for key, value in dict(data.get("realm_marks", {})).items()
            },
            extra_roots=[
                Root.from_dict(root)
                for root in data.get("extra_roots", [])
                if isinstance(root, dict)
            ],
        )

@dataclass
class SigninResult:
    record: UserRecord
    is_first: bool
    already_signed: bool
    gained_exp: int = 0
    pending_exp_applied: int = 0
    method_bonus_exp: int = 0
    item_bonus_exp: int = 0
    leveled_realms: int = 0
    gained_fishing_chance: bool = False
    encounter: Optional[EncounterResult] = None
    breakthrough_reward: Optional[dict[str, Any]] = None
    lock_message: str = ""
    daily_tasks: Optional[list[dict[str, Any]]] = None

def weighted_choice(items: Sequence[tuple[T, float]]) -> T:
    total = sum(weight for _, weight in items)
    point = random.uniform(0, total)
    cursor = 0.0
    for item, weight in items:
        cursor += weight
        if cursor >= point:
            return item
    return items[-1][0]


def make_root(tier: str, grade: str, attribute: str) -> Root:
    return Root(
        tier=tier,
        tier_rank=TIER_RANKS[tier],
        grade=grade,
        grade_rank=GRADE_RANKS[grade],
        attribute=attribute,
    )


def draw_root() -> Root:
    tier, _, _ = weighted_choice([(item, item[2]) for item in QUALITY_TIER_POOL])
    grade, _, _ = weighted_choice([(item, item[2]) for item in GRADE_POOL])
    return make_root(tier, grade, random.choice(ATTRIBUTES))


def current_breakthrough_requirement(record: UserRecord) -> Optional[dict[str, Any]]:
    if record.realm_index >= len(REALMS) - 1:
        return None
    return BREAKTHROUGH_REQUIREMENTS.get(record.realm_index)


def is_breakthrough_bottleneck(record: UserRecord) -> bool:
    return (
        record.root is not None
        and current_breakthrough_requirement(record) is not None
        and record.realm_exp >= record.progress_required
    )


def realm_stage(record: UserRecord) -> str:
    if record.root is None:
        return ""
    if is_breakthrough_bottleneck(record):
        return "巅峰"
    ratio = record.realm_exp / max(1, record.progress_required)
    if ratio >= 1:
        return "圆满"
    if ratio >= 0.6:
        return "后期"
    if ratio >= 0.3:
        return "中期"
    return "初期"


def parse_lock_until(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def is_cultivation_locked(record: UserRecord, today: Optional[date] = None) -> bool:
    until = parse_lock_until(record.cultivation_lock_until)
    if until is None:
        return False
    today = today or date.today()
    if today >= until:
        record.cultivation_lock_until = None
        return False
    return True


def cultivation_lock_text(record: UserRecord, today: Optional[date] = None) -> str:
    if not is_cultivation_locked(record, today):
        return ""
    return f"禁修至 {record.cultivation_lock_until}"


def lock_cultivation(record: UserRecord, today: Optional[date] = None, days: int = 1) -> str:
    today = today or date.today()
    until = today + timedelta(days=max(1, days))
    record.cultivation_lock_until = until.isoformat()
    return cultivation_lock_text(record, today)


def apply_exp(record: UserRecord, amount: int) -> tuple[int, int]:
    if amount <= 0:
        return 0, 0
    if is_cultivation_locked(record):
        return 0, 0
    if is_breakthrough_bottleneck(record):
        return 0, 0
    remaining = amount
    applied = 0
    leveled_realms = 0
    while remaining > 0:
        if record.realm_index >= len(REALMS) - 1:
            room = max(0, record.progress_required - record.realm_exp)
            gained = min(remaining, room)
            record.realm_exp += gained
            record.total_exp += gained
            applied += gained
            break
        room = max(0, record.progress_required - record.realm_exp)
        if room <= 0:
            if current_breakthrough_requirement(record):
                break
            record.realm_exp = 0
            record.realm_index += 1
            leveled_realms += 1
            continue
        gained = min(remaining, room)
        record.realm_exp += gained
        record.total_exp += gained
        applied += gained
        remaining -= gained
        if record.realm_exp < record.progress_required:
            break
        if current_breakthrough_requirement(record):
            break
        record.realm_exp = 0
        record.realm_index += 1
        leveled_realms += 1
    return applied, leveled_realms


def add_exp(record: UserRecord, amount: int) -> int:
    _, leveled_realms = apply_exp(record, amount)
    return leveled_realms


def grade_ratio(grade: str) -> float:
    return GRADE_EXP_RATIO.get(str(grade), 1.0)


def tier_exp(base_map: dict[str, int], tier: str, grade: str) -> int:
    base = base_map.get(str(tier), min(base_map.values()))
    return max(1, int(base * grade_ratio(grade)))


def reward_price(reward: dict[str, Any]) -> int:
    category = reward_category(reward)
    base = ITEM_PRICE_BASE.get(category, 40)
    tier = str(reward.get("tier", "凡品"))
    grade = str(reward.get("grade", "中品"))
    return max(1, int(base * TIER_PRICE_RATIO.get(tier, 1) * GRADE_PRICE_RATIO.get(grade, 1.0)))


def spirit_stone_text(amount: int) -> str:
    amount = max(0, int(amount))
    if amount <= 0:
        return "0下品灵石"
    units = [(1_000_000, "极品"), (10_000, "上品"), (100, "中品"), (1, "下品")]
    parts = []
    remaining = amount
    for value, name in units:
        count, remaining = divmod(remaining, value)
        if count:
            parts.append(f"{count}{name}灵石")
    return " ".join(parts)


def item_required_realm_index(reward: dict[str, Any]) -> int:
    return TIER_REALM_REQUIREMENT.get(str(reward.get("tier", "凡品")), 0)


def can_buy_reward(record: UserRecord, reward: dict[str, Any]) -> tuple[bool, str]:
    required_index = item_required_realm_index(reward)
    if required_index > record.realm_index + 2:
        return False, f"{reward_display_name(reward)} 至少约需{REALMS[required_index]}附近才能驾驭，已超过当前修为两大境界。"
    price = int(reward.get("price") or reward_price(reward))
    if record.spirit_stones < price:
        return False, f"灵石不足，需要 {spirit_stone_text(price)}，当前 {spirit_stone_text(record.spirit_stones)}。"
    return True, ""


def weighted_choice_rng(items: Sequence[tuple[T, float]], rng: random.Random) -> T:
    total = sum(weight for _, weight in items)
    point = rng.uniform(0, total)
    cursor = 0.0
    for item, weight in items:
        cursor += weight
        if cursor >= point:
            return item
    return items[-1][0]


def shop_items_for_date(date_text: str) -> list[dict[str, Any]]:
    digest = hashlib.sha256(date_text.encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    pool = [(reward, float(reward[5])) for reward in FISHING_REWARDS if reward[2] != "仙缘"]
    items = []
    for _ in range(8):
        tier, grade, category, name, description, _ = weighted_choice_rng(pool, rng)
        item = normalize_reward({"tier": tier, "grade": grade, "category": category, "name": name, "description": description})
        item["price"] = reward_price(item)
        items.append(item)
    return items


def buy_shop_item(record: UserRecord, item_index: int, date_text: str) -> tuple[bool, str]:
    items = shop_items_for_date(date_text)
    if item_index < 1 or item_index > len(items):
        return False, f"请选择 1-{len(items)} 之间的商品编号。"
    item = normalize_reward(dict(items[item_index - 1]), record)
    allowed, reason = can_buy_reward(record, item)
    if not allowed:
        return False, reason
    price = int(item.get("price") or reward_price(item))
    record.spirit_stones -= price
    append_reward(record, item)
    return True, f"购买 {reward_display_name(item)} 成功，花费 {spirit_stone_text(price)}，剩余 {spirit_stone_text(record.spirit_stones)}。"


def sell_reward(record: UserRecord, category: str, item_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, category, item_index)
    if result is None:
        return False, f"没有找到这个编号的{category}。"
    price = max(1, int(reward_price(result) * 0.6))
    record.spirit_stones += price
    return True, f"出售 {reward_display_name(result)}，获得 {spirit_stone_text(price)}，当前共有 {spirit_stone_text(record.spirit_stones)}。"


def reward_category(reward: Optional[dict[str, Any]]) -> str:
    return str((reward or {}).get("category", ""))


def reward_name(reward: Optional[dict[str, Any]]) -> str:
    return str((reward or {}).get("name", ""))


def reward_required_attribute(reward: dict[str, Any]) -> Optional[str]:
    required = reward.get("required_attribute")
    if required:
        return str(required)
    required = ITEM_ATTRIBUTE_BY_NAME.get(reward_name(reward))
    if required:
        reward["required_attribute"] = required
    return required


def normalize_reward(reward: dict[str, Any], record: Optional[UserRecord] = None) -> dict[str, Any]:
    tier = str(reward.get("tier", "凡品"))
    if tier == "路人甲":
        tier = "凡品"
    reward["tier"] = tier
    reward.setdefault("grade", "中品")
    reward.setdefault("category", "杂物")
    reward.setdefault("name", "无名灵物")
    reward.setdefault(
        "description",
        REWARD_DESCRIPTIONS.get(reward_category(reward), "{name}气息不明。").format(name=reward_name(reward)),
    )
    reward["price"] = int(reward.get("price") or reward_price(reward))
    if reward_category(reward) in EQUIPMENT_CATEGORIES:
        required = reward_required_attribute(reward)
        if required and record is not None:
            reward["compatible"] = required in record.root_attributes
    return reward

def make_reward(tier: str, grade: str, category: str, name: str) -> dict[str, Any]:
    return normalize_reward(
        {
            "tier": tier,
            "grade": grade,
            "category": category,
            "name": name,
            "description": REWARD_DESCRIPTIONS.get(category, "{name}气息不明。").format(name=name),
        }
    )

def append_reward(record: UserRecord, reward: dict[str, Any]) -> None:
    if record.rewards is None:
        record.rewards = []
    record.rewards.append(normalize_reward(reward, record))


def rewards_by_category(record: UserRecord, category: str) -> list[dict[str, Any]]:
    return [
        normalize_reward(reward, record)
        for reward in record.rewards or []
        if reward_category(reward) == category
    ]


def reward_position_by_category_index(record: UserRecord, category: str, item_index: int) -> Optional[tuple[int, dict[str, Any]]]:
    if item_index < 1:
        return None
    cursor = 0
    for list_index, reward in enumerate(record.rewards or []):
        if reward_category(reward) != category:
            continue
        cursor += 1
        if cursor == item_index:
            return list_index, normalize_reward(reward, record)
    return None


def pop_reward_by_category_index(record: UserRecord, category: str, item_index: int) -> Optional[dict[str, Any]]:
    result = reward_position_by_category_index(record, category, item_index)
    if result is None or record.rewards is None:
        return None
    list_index, reward = result
    record.rewards.pop(list_index)
    return reward


def consume_reward_by_names(record: UserRecord, names: Sequence[str]) -> Optional[dict[str, Any]]:
    wanted = set(names)
    for list_index, reward in enumerate(record.rewards or []):
        if reward_name(reward) not in wanted:
            continue
        if record.rewards is None:
            return None
        return normalize_reward(record.rewards.pop(list_index), record)
    return None


def reward_count_by_names(record: UserRecord, names: Sequence[str]) -> int:
    wanted = set(names)
    return sum(1 for reward in record.rewards or [] if reward_name(reward) in wanted)


def draw_named_reward(name: str) -> dict[str, Any]:
    matches = [reward for reward in FISHING_REWARDS if reward[3] == name]
    if matches:
        tier, grade, category, item_name, description, _ = weighted_choice(
            [(reward, float(reward[5])) for reward in matches]
        )
        return normalize_reward(
            {
                "tier": tier,
                "grade": grade,
                "category": category,
                "name": item_name,
                "description": description,
            }
        )
    return make_reward("\u7384\u9636", "\u4e0a\u54c1", "\u5947\u7269", name)


def maybe_grant_breakthrough_item(record: UserRecord, chance: float = 0.5) -> Optional[dict[str, Any]]:
    requirement = current_breakthrough_requirement(record)
    if not requirement or not is_breakthrough_bottleneck(record):
        return None
    if random.random() >= chance:
        return None
    item_name = random.choice(list(requirement["items"]))
    reward = draw_named_reward(item_name)
    reward["breakthrough_bonus"] = True
    append_reward(record, reward)
    return reward


def breakthrough_required_text(record: UserRecord) -> str:
    requirement = current_breakthrough_requirement(record)
    if not requirement:
        return "\u65e0\u9700\u7279\u6b8a\u7a81\u7834\u9053\u5177"
    return " / ".join(str(item) for item in requirement["items"])


def foundation_quality(item: dict[str, Any]) -> str:
    score = TIER_RANKS.get(str(item.get("tier")), 0) * 4 + GRADE_RANKS.get(str(item.get("grade")), 0)
    if score >= 18:
        return "天道筑基"
    if score >= 14:
        return "完美道基"
    if score >= 10:
        return "优秀筑基"
    if score >= 5:
        return "良好筑基"
    return "普通筑基"


REALM_QUALITY_TITLES = {
    3: ['一品金丹', '二品金丹', '三品金丹', '四品金丹', '五品金丹', '六品金丹', '七品金丹', '八品金丹', '九品金丹'],
    4: ['天命元婴', '无瑕元婴', '紫府元婴', '灵台元婴', '凡胎元婴'],
    5: ['太虚化神', '无垢化神', '神意化形', '凡念化神'],
    6: ['洞虚道体', '玄虚法身', '清虚灵体', '凡虚之身'],
    7: ['天人合一', '道体合真', '元神合契', '法身初合'],
    8: ['无上大乘', '圆融大乘', '清净大乘', '小乘道果'],
    9: ['九重雷劫', '七重雷劫', '五重雷劫', '三重雷劫'],
    10: ['无垢真仙', '玄妙真仙', '清灵真仙', '凡蜕真仙'],
    11: ['不朽金仙', '太玄金仙', '玉清金仙', '初证金仙'],
    12: ['太乙道果', '太乙玄光', '太乙清光', '太乙初果'],
    13: ['大罗无极', '大罗圆满', '大罗玄妙', '大罗初证'],
    14: ['混元圆满', '混元无瑕', '混元玄妙', '混元初证'],
    15: ['三尸尽斩', '二尸圆融', '一尸寄道', '半步准圣'],
    16: ['天道圣位', '功德圣人', '气运圣人', '伪圣道果'],
    17: ['自在混元', '无垢混元', '玄照混元', '初入混元'],
    18: ['无极道主', '无极真圣', '无极玄光', '无极初证'],
    19: ['执掌天道', '合道无缺', '天心圆融', '借天而行'],
    20: ['大道归一', '大道无缺', '大道玄同', '大道初契'],
    21: ['万道祖庭', '一道开天', '道祖法身', '初立道统'],
    22: ['半步无上', '命河将断', '因果将尽', '彼岸初望'],
    23: ['彼岸超脱', '命河不系', '因果不染', '初证超脱'],
    24: ['永恒唯一', '万劫不磨', '无量不朽', '永恒初印'],
}


REALM_QUALITY_POWER = {
    "\u666e\u901a\u7b51\u57fa": 120,
    "\u826f\u597d\u7b51\u57fa": 220,
    "\u4f18\u79c0\u7b51\u57fa": 360,
    "\u5b8c\u7f8e\u9053\u57fa": 560,
    "\u5929\u9053\u7b51\u57fa": 820,
    "\u4e00\u54c1\u91d1\u4e39": 900,
    "\u4e8c\u54c1\u91d1\u4e39": 780,
    "\u4e09\u54c1\u91d1\u4e39": 660,
    "\u56db\u54c1\u91d1\u4e39": 540,
    "\u4e94\u54c1\u91d1\u4e39": 430,
    "\u516d\u54c1\u91d1\u4e39": 330,
    "\u4e03\u54c1\u91d1\u4e39": 240,
    "\u516b\u54c1\u91d1\u4e39": 170,
    "\u4e5d\u54c1\u91d1\u4e39": 110,
}


for _realm_quality_index, _realm_quality_titles in REALM_QUALITY_TITLES.items():
    _base_power = 900 + _realm_quality_index * 180
    for _realm_quality_pos, _realm_quality_title in enumerate(_realm_quality_titles):
        REALM_QUALITY_POWER.setdefault(
            _realm_quality_title,
            max(120, _base_power - _realm_quality_pos * 120),
        )


def item_quality_score(item: dict[str, Any]) -> int:
    return TIER_RANKS.get(str(item.get("tier")), 0) * 4 + GRADE_RANKS.get(str(item.get("grade")), 0)


def quality_from_titles(item: dict[str, Any], titles: list[str]) -> str:
    if not titles:
        return "\u9053\u57fa\u672a\u5b9a"
    score = max(0, min(19, item_quality_score(item)))
    index = int((19 - score) / max(1, 20 / len(titles)))
    return titles[max(0, min(len(titles) - 1, index))]


def breakthrough_quality(item: dict[str, Any], target_index: int) -> str:
    return quality_from_titles(item, REALM_QUALITY_TITLES.get(target_index, []))


def set_realm_mark(record: UserRecord, realm_index: int, mark: str) -> None:
    if record.realm_marks is None:
        record.realm_marks = {}
    record.realm_marks[str(realm_index)] = mark
    if realm_index == 2:
        record.foundation_type = mark


def realm_quality_text(record: UserRecord) -> str:
    marks = record.realm_marks or {}
    current = marks.get(str(record.realm_index))
    if current:
        return current
    if record.foundation_type and record.realm_index >= 2:
        return record.foundation_type
    return "\u672a\u5b9a\u9053\u57fa"


def realm_quality_power(record: UserRecord) -> int:
    total = 0
    seen = set()
    if record.foundation_type:
        seen.add(record.foundation_type)
        total += REALM_QUALITY_POWER.get(record.foundation_type, 0)
    for mark in (record.realm_marks or {}).values():
        if mark in seen:
            continue
        seen.add(mark)
        total += REALM_QUALITY_POWER.get(mark, 260)
    return total


def breakthrough_status(record: UserRecord) -> str:
    if record.root is None:
        return "尚未踏入修行路，发送“签到”先觉醒灵根。"
    requirement = current_breakthrough_requirement(record)
    if requirement is None:
        if record.realm_index >= len(REALMS) - 1:
            return f"当前已至{record.realm}，暂时无更高境界。"
        return f"当前{record.realm}进度 {record.realm_exp}/{record.progress_required}，继续修炼即可。"
    target = str(requirement["target"])
    needed = list(requirement["items"])
    count_text = "，".join(f"{name}x{reward_count_by_names(record, [name])}" for name in needed)
    if record.realm_exp < record.progress_required:
        return (
            f"当前{record.realm}进度 {record.realm_exp}/{record.progress_required}，"
            f"圆满后可凭 {breakthrough_required_text(record)} 突破至{target}。"
        )
    return (
        f"当前已达{record.realm}，可突破至{target}。"
        f"所需道具：{breakthrough_required_text(record)}；背包：{count_text or '暂无'}。"
    )

def breakthrough_realm(record: UserRecord) -> tuple[bool, str]:
    if record.root is None:
        return False, "\u5c1a\u672a\u8e0f\u5165\u4fee\u884c\u8def\uff0c\u53d1\u9001\u201c\u7b7e\u5230\u201d\u5148\u89c9\u9192\u7075\u6839\u3002"
    requirement = current_breakthrough_requirement(record)
    if requirement is None:
        return False, breakthrough_status(record)
    if record.realm_exp < record.progress_required:
        return False, breakthrough_status(record)
    item = consume_reward_by_names(record, list(requirement["items"]))
    if item is None:
        return (
            False,
            f"\u7a81\u7834\u5931\u8d25\uff1a\u9700\u8981 {breakthrough_required_text(record)}\u3002\u5883\u754c\u5706\u6ee1\u65f6\uff0c\u6bcf\u6b21\u7b7e\u5230\u6216\u5782\u9493\u90fd\u6709 50% \u6982\u7387\u989d\u5916\u83b7\u5f97\u5f53\u524d\u7a81\u7834\u9053\u5177\u3002",
        )
    old_realm = record.realm
    record.realm_index += 1
    record.realm_exp = 0
    target_realm = record.realm
    mark = foundation_quality(item) if requirement.get("kind") == "foundation" else breakthrough_quality(item, record.realm_index)
    set_realm_mark(record, record.realm_index, mark)
    return True, f"\u53ee\uff01\u6d88\u8017{reward_display_name(item)}\uff0c\u4ece{old_realm}\u7a81\u7834\u81f3{target_realm}\uff0c\u51dd\u6210{mark}\u3002"

def reward_signature(reward: Optional[dict[str, Any]]) -> str:
    if not reward:
        return ""
    required = reward_required_attribute(reward) or ""
    return ":".join(
        [reward_category(reward), str(reward.get("tier", "")), str(reward.get("grade", "")), reward_name(reward), required]
    )


def item_is_compatible(record: UserRecord, item: dict[str, Any]) -> bool:
    required_attribute = reward_required_attribute(item)
    return not required_attribute or required_attribute in record.root_attributes


def array_multiplier(record: UserRecord, method: Optional[dict[str, Any]] = None) -> float:
    method_item = method or record.equipped_method
    if not record.equipped_array or not method_item:
        return 1.0
    key = reward_signature(method_item)
    proficiency = int((record.array_proficiency or {}).get(key, 0))
    multiplier = min(10.0, 1.0 + proficiency / 100)
    if record.cultivation_route == "阵法师":
        multiplier = min(10.0, multiplier * 1.5)
    return multiplier


def increase_array_proficiency(record: UserRecord, amount: int = 1) -> None:
    if not record.equipped_array or not record.equipped_method or amount <= 0:
        return
    key = reward_signature(record.equipped_method)
    if record.array_proficiency is None:
        record.array_proficiency = {}
    gain = amount * (2 if record.cultivation_route == "阵法师" else 1)
    record.array_proficiency[key] = min(900, int(record.array_proficiency.get(key, 0)) + gain)


def method_sign_bonus(record: UserRecord, base_exp: int) -> int:
    method = record.equipped_method
    if not method or not item_is_compatible(record, method):
        return 0
    rate = METHOD_SIGN_RATE.get(str(method.get("tier")), 0.0)
    bonus = int(base_exp * rate * grade_ratio(str(method.get("grade"))) * array_multiplier(record, method))
    return max(1, bonus) if rate > 0 else 0


def method_chat_exp(record: UserRecord, count: int = 1) -> int:
    method = record.equipped_method
    if count <= 0 or not method or not item_is_compatible(record, method):
        return 0
    raw = (
        METHOD_CHAT_BASE.get(str(method.get("tier")), 0.0)
        * grade_ratio(str(method.get("grade")))
        * array_multiplier(record, method)
        * count
    )
    gained = int(raw)
    if random.random() < raw - gained:
        gained += 1
    return gained


def apply_chat_cultivation(record: UserRecord, count: int = 1) -> tuple[int, int]:
    gained_exp = method_chat_exp(record, count)
    if gained_exp <= 0:
        return 0, 0
    applied_exp, leveled = apply_exp(record, gained_exp)
    if applied_exp:
        increase_array_proficiency(record, count)
    return applied_exp, leveled


def route_status_text(record: UserRecord) -> str:
    lines = ["【修炼路线】", f"主路线：{record.cultivation_route or '未选择'}", f"邪修：{'已同修' if record.evil_cultivator else '未同修'}"]
    lines.append(f"身份令牌：{record.identity_summary}")
    lines.append(f"天机秘境：{tianji_status_text(record)}")
    lines.append(f"双修次数：{hehuan_remaining_text(record)}")
    lines.append("可选路线：剑修、术修、炼丹师、阵法师；发送“选择路线 路线名”。")
    lines.append("邪修可发送“选择邪修”同修，发送“退出邪修”暂离。")
    lines.append("宗门身份可选：天机阁弟子、天机阁长老、天机阁太上长老；合欢宗弟子、合欢宗长老、合欢宗太上长老。")
    lines.append("选择格式：选择身份 天机阁弟子 / 选择身份 合欢宗弟子。")
    lines.append("天机阁门槛：弟子需筑基；长老需元婴且弟子身份签到10天；太上长老需炼虚且长老身份签到30天。")
    lines.append("合欢宗门槛：弟子需练气中期；长老需金丹且弟子身份签到10天；太上长老需化神且长老身份签到20天。")
    return "\n".join(lines)


def choose_cultivation_route(record: UserRecord, route: str) -> tuple[bool, str]:
    route = route.strip()
    if route not in CULTIVATION_ROUTES:
        return False, f"路线可选：{'、'.join(CULTIVATION_ROUTES)}。"
    old = record.cultivation_route or "未选择"
    record.cultivation_route = route
    return True, f"修炼路线已从{old}调整为{route}。"


def choose_evil_cultivation(record: UserRecord, enabled: bool = True) -> tuple[bool, str]:
    record.evil_cultivator = enabled
    if enabled:
        return True, "已同修邪修路线。秘境中不会因邪修陷阱直接落入坏结局，但所有坏结局禁修期变为2天。"
    return True, "已暂离邪修路线。"


def realm_ratio(record: UserRecord) -> float:
    return record.realm_exp / max(1, record.progress_required)


def has_realm_progress(record: UserRecord, realm_index: int, ratio: float = 0.0) -> bool:
    return record.realm_index > realm_index or (record.realm_index == realm_index and realm_ratio(record) >= ratio)


def identity_days(record: UserRecord, identity: str) -> int:
    return int((record.identity_sign_days or {}).get(identity, 0))


def choose_faction_identity(record: UserRecord, identity: str) -> tuple[bool, str]:
    identity = identity.strip()
    if identity not in FACTION_IDENTITIES:
        return False, f"身份可选：{'、'.join(FACTION_IDENTITIES)}。"
    requirements = {
        "天机阁弟子": (2, 0.0, None, 0, "筑基修为"),
        "天机阁长老": (4, 0.0, "天机阁弟子", 10, "元婴修为，且天机阁弟子签到10天"),
        "天机阁太上长老": (6, 0.0, "天机阁长老", 30, "炼虚修为，且天机阁长老签到30天"),
        "合欢宗弟子": (1, 0.3, None, 0, "练气中期"),
        "合欢宗长老": (3, 0.0, "合欢宗弟子", 10, "金丹修为，且合欢宗弟子签到10天"),
        "合欢宗太上长老": (5, 0.0, "合欢宗长老", 20, "化神修为，且合欢宗长老签到20天"),
    }
    realm_index, ratio, previous, days, text = requirements[identity]
    if not has_realm_progress(record, realm_index, ratio):
        return False, f"选择{identity}需要{text}。"
    if previous and identity_days(record, previous) < days:
        return False, f"选择{identity}需要{previous}身份签到{days}天，当前{identity_days(record, previous)}天。"
    old = record.faction_identity or "暂无身份"
    record.faction_identity = identity
    return True, f"身份令牌已由{old}更换为{identity}。"


def record_identity_sign_day(record: UserRecord, today: date) -> None:
    identity = record.faction_identity
    if not identity:
        return
    if record.identity_sign_days is None:
        record.identity_sign_days = {}
    record.identity_sign_days[identity] = int(record.identity_sign_days.get(identity, 0)) + 1


def hehuan_daily_limit(record: UserRecord) -> int:
    return HEHUAN_DAILY_LIMITS.get(record.faction_identity or "", 0)


def hehuan_remaining(record: UserRecord, today: Optional[date] = None) -> int:
    today_text = (today or date.today()).isoformat()
    if record.dual_cultivation_date != today_text:
        return hehuan_daily_limit(record)
    return max(0, hehuan_daily_limit(record) - int(record.dual_cultivation_used))


def hehuan_remaining_text(record: UserRecord, today: Optional[date] = None) -> str:
    limit = hehuan_daily_limit(record)
    if limit <= 0:
        return "无"
    return f"{hehuan_remaining(record, today)}/{limit}"


def special_cultivation_exp(record: UserRecord) -> int:
    method = record.equipped_method
    if not method:
        low, high = record.root.exp_gain_range if record.root else (4, 8)
        return max(4, (low + high) // 2)
    base = METHOD_CHAT_BASE.get(str(method.get("tier")), 0.8) * 10
    return max(8, int(base * grade_ratio(str(method.get("grade"))) * array_multiplier(record, method) * 2))


def apply_dual_cultivation(actor: UserRecord, target: UserRecord, today: date) -> tuple[bool, str]:
    if hehuan_daily_limit(actor) <= 0:
        return False, "当前身份没有双修次数，请先选择合欢宗身份。"
    if hehuan_remaining(actor, today) <= 0:
        return False, "今日双修次数已用完。"
    if is_cultivation_locked(actor, today) or is_cultivation_locked(target, today):
        return False, "双方有人处于禁修期，无法通过任何手段提升修为。"
    exp = special_cultivation_exp(actor)
    actor_exp, _ = apply_exp(actor, exp)
    target_exp, _ = apply_exp(target, exp)
    today_text = today.isoformat()
    if actor.dual_cultivation_date != today_text:
        actor.dual_cultivation_date = today_text
        actor.dual_cultivation_used = 0
    actor.dual_cultivation_used += 1
    return True, f"双修完成，双方各得修为：发起者 +{actor_exp}，对象 +{target_exp}。今日剩余 {hehuan_remaining(actor, today)} 次。"


def tianji_status_text(record: UserRecord, today: Optional[date] = None) -> str:
    cooldown = TIANJI_COOLDOWN_DAYS.get(record.faction_identity or "")
    if not cooldown:
        return "无"
    today = today or date.today()
    last = parse_lock_until(record.last_tianji_mystic_date)
    if last is None:
        return "可用"
    remain = cooldown - (today - last).days
    return "可用" if remain <= 0 else f"冷却{remain}天"


def tianji_mystic_available(record: UserRecord, today: date) -> tuple[bool, str]:
    cooldown = TIANJI_COOLDOWN_DAYS.get(record.faction_identity or "")
    if not cooldown:
        return False, "当前没有天机阁身份，无法开启天机秘境。"
    last = parse_lock_until(record.last_tianji_mystic_date)
    if last is not None and (today - last).days < cooldown:
        return False, f"天机秘境仍在冷却，{tianji_status_text(record, today)}。"
    return True, ""


def draw_tianji_mystic_entrances(record: UserRecord, today: date) -> tuple[bool, str, list[dict[str, Any]]]:
    allowed, reason = tianji_mystic_available(record, today)
    if not allowed:
        return False, reason, []
    entries = draw_mystic_entrances(record)
    for entry in entries:
        entry["insight"] = True
        entry["tianji"] = True
    return True, "天机示警已开启，本次秘境会提示坏结局选项。", entries


def generate_daily_tasks(record: UserRecord, today: date) -> list[dict[str, Any]]:
    seed = int(hashlib.sha256(f"{record.user_id}:{today.isoformat()}".encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    tasks = []
    templates = rng.sample(DAILY_TASK_TEMPLATES, k=5)
    for template in templates:
        realm_label = realm_short_name(record.realm_name if record.root else "炼体期")
        exp = 10 + max(1, record.realm_index + 1) * rng.randint(3, 7)
        stones = 15 + max(1, record.realm_index + 1) * rng.randint(5, 12)
        fishing = 1 if rng.random() < 0.16 else 0
        tasks.append({"title": template.format(realm=realm_label), "exp": exp, "stones": stones, "fishing": fishing, "done": False})
    record.daily_tasks = {"date": today.isoformat(), "tasks": tasks}
    return tasks


def ensure_daily_tasks(record: UserRecord, today: date) -> list[dict[str, Any]]:
    if not isinstance(record.daily_tasks, dict) or record.daily_tasks.get("date") != today.isoformat():
        return generate_daily_tasks(record, today)
    tasks = record.daily_tasks.get("tasks", [])
    return list(tasks) if isinstance(tasks, list) else generate_daily_tasks(record, today)


def daily_tasks_text(record: UserRecord, today: Optional[date] = None) -> str:
    tasks = ensure_daily_tasks(record, today or date.today())
    lines = ["【每日任务】", f"灵石：{spirit_stone_text(record.spirit_stones)}"]
    for index, task in enumerate(tasks, start=1):
        status = "已完成" if task.get("done") else "未完成"
        reward = f"修为+{int(task.get('exp', 0))}，灵石+{spirit_stone_text(int(task.get('stones', 0)))}"
        if int(task.get("fishing", 0)):
            reward += f"，垂钓+{int(task.get('fishing', 0))}"
        lines.append(f"{index}. {task.get('title')} | {status} | {reward}")
    lines.append("发送“完成任务 编号”领取对应奖励。")
    return "\n".join(lines)


def complete_daily_task(record: UserRecord, task_index: int, today: date) -> tuple[bool, str]:
    tasks = ensure_daily_tasks(record, today)
    if task_index < 1 or task_index > len(tasks):
        return False, f"请选择 1-{len(tasks)} 之间的任务编号。"
    task = tasks[task_index - 1]
    if task.get("done"):
        return False, "这个任务今日已经完成。"
    if is_cultivation_locked(record, today):
        return False, blocked_cultivation_message(record)
    task["done"] = True
    exp = int(task.get("exp", 0))
    stones = int(task.get("stones", 0))
    fishing = int(task.get("fishing", 0))
    applied, leveled = apply_exp(record, exp)
    record.spirit_stones += stones
    record.fishing_chances += fishing
    record.daily_tasks = {"date": today.isoformat(), "tasks": tasks}
    extra = f"，连破{leveled}境" if leveled else ""
    fish_text = f"，垂钓+{fishing}" if fishing else ""
    return True, f"完成任务：{task.get('title')}。修为+{applied}{extra}，灵石+{spirit_stone_text(stones)}{fish_text}。"


def alchemy_text(record: UserRecord) -> str:
    lines = ["【炼丹】", f"当前路线：{record.cultivation_route or '未选择'}", f"灵石：{spirit_stone_text(record.spirit_stones)}"]
    for index, (name, recipe) in enumerate(ALCHEMY_RECIPES.items(), start=1):
        materials = "、".join(recipe["materials"])
        lines.append(f"{index}. {name}：{materials}；炉资{spirit_stone_text(int(recipe['cost']))}")
    lines.append("发送“炼丹 丹药名”，例如：炼丹 筑基丹。")
    return "\n".join(lines)


def reward_positions_by_names(record: UserRecord, names: Sequence[str]) -> list[int]:
    positions = []
    used = set()
    for name in names:
        for list_index, reward in enumerate(record.rewards or []):
            if list_index in used:
                continue
            if reward_name(reward) == name:
                positions.append(list_index)
                used.add(list_index)
                break
    return positions


def refine_pill_by_recipe(record: UserRecord, pill_name: str) -> tuple[bool, str]:
    if record.cultivation_route != "炼丹师":
        return False, "只有选择炼丹师路线后，才能使用丹方炼制丹药。"
    recipe = ALCHEMY_RECIPES.get(pill_name.strip())
    if not recipe:
        return False, f"未找到丹方：{pill_name}。"
    cost = int(recipe["cost"])
    if record.spirit_stones < cost:
        return False, f"灵石不足，开炉需要 {spirit_stone_text(cost)}。"
    materials = list(recipe["materials"])
    positions = reward_positions_by_names(record, materials)
    if len(positions) < len(materials):
        owned = [reward_name(reward) for reward in record.rewards or []]
        missing = [name for name in materials if name not in owned]
        return False, f"材料不足，缺少：{'、'.join(missing)}。"
    if record.rewards is None:
        return False, "材料不足。"
    for list_index in sorted(positions, reverse=True):
        record.rewards.pop(list_index)
    record.spirit_stones -= cost
    pill = make_reward(str(recipe["tier"]), str(recipe["grade"]), PILL_CATEGORY, pill_name.strip())
    append_reward(record, pill)
    return True, f"丹炉火候已成，消耗材料炼出 {reward_display_name(pill)}，炉资 {spirit_stone_text(cost)}。"

def improve_root_once(root: Root) -> Root:
    grade_index = GRADE_ORDER.index(root.grade)
    if grade_index < len(GRADE_ORDER) - 1:
        return make_root(root.tier, GRADE_ORDER[grade_index + 1], root.attribute)

    tier_index = TIER_ORDER.index(root.tier)
    if tier_index < len(TIER_ORDER) - 1:
        return make_root(TIER_ORDER[tier_index + 1], "下品", root.attribute)

    return root


def maybe_apply_encounter(record: UserRecord, today: date) -> EncounterResult:
    today_text = today.isoformat()
    if record.root is None or record.last_encounter_date == today_text:
        return EncounterResult()

    record.last_encounter_date = today_text
    if not record.is_peak_aptitude:
        if random.randint(1, 365) != 1:
            return EncounterResult()
        old_root = record.root
        if random.random() >= 0.5:
            return EncounterResult(
                happened=True,
                success=False,
                message="今日忽逢山中古洞，可惜机缘一闪而逝，资质未有变化。",
                old_root=old_root,
            )
        new_root = improve_root_once(old_root)
        record.root = new_root
        return EncounterResult(
            happened=True,
            success=True,
            message=f"今日奇遇入梦，资质由{old_root.display_name}提升为{new_root.display_name}！",
            old_root=old_root,
            new_root=new_root,
        )

    extra_count = len(record.extra_roots or [])
    if random.randint(1, 999) > 1 + extra_count:
        return EncounterResult()

    owned = record.root_attributes
    candidates = [attribute for attribute in ATTRIBUTES if attribute not in owned]
    if not candidates:
        return EncounterResult(
            happened=True,
            success=False,
            message="今日灵台七窍同明，可惜七系灵根已全，机缘化作一缕清气。",
        )
    extra_root = make_root("天阶", "极品", random.choice(candidates))
    if record.extra_roots is None:
        record.extra_roots = []
    record.extra_roots.append(extra_root)
    return EncounterResult(
        happened=True,
        success=True,
        message=f"今日天门洞开，额外觉醒{extra_root.display_name}！",
        added_root=extra_root,
    )



def apply_signin(record: UserRecord, today: date) -> SigninResult:
    today_text = today.isoformat()
    if record.last_sign_date == today_text:
        return SigninResult(record=record, is_first=False, already_signed=True)

    is_first = record.root is None
    if record.root is None:
        record.root = draw_root()

    low, high = record.root.exp_gain_range
    base_exp = random.randint(low, high)
    method_bonus = method_sign_bonus(record, base_exp)
    plant_bonus = plant_sign_bonus(record, base_exp)
    locked = is_cultivation_locked(record, today)
    pending_exp = 0 if locked else record.pending_exp
    if not locked:
        record.pending_exp = 0
    record.last_sign_date = today_text
    record.sign_count += 1
    applied_exp, leveled_realms = apply_exp(record, base_exp + method_bonus + plant_bonus + pending_exp)
    if applied_exp:
        increase_array_proficiency(record, 1)
    encounter = maybe_apply_encounter(record, today)
    breakthrough_reward = maybe_grant_breakthrough_item(record)
    record_identity_sign_day(record, today)
    tasks = ensure_daily_tasks(record, today)

    gained_fishing_chance = True
    record.fishing_chances += 1
    record.pending_fishing = record.fishing_chances

    return SigninResult(
        record=record,
        is_first=is_first,
        already_signed=False,
        gained_exp=applied_exp,
        pending_exp_applied=min(pending_exp, applied_exp) if pending_exp else 0,
        method_bonus_exp=min(method_bonus, applied_exp) if method_bonus else 0,
        item_bonus_exp=min(plant_bonus, applied_exp) if plant_bonus else 0,
        leveled_realms=leveled_realms,
        gained_fishing_chance=gained_fishing_chance,
        encounter=encounter,
        breakthrough_reward=breakthrough_reward,
        lock_message=cultivation_lock_text(record, today) if locked else "",
        daily_tasks=tasks,
    )

def draw_fishing_rewards(count: int) -> list[dict[str, Any]]:
    rewards = []
    pool = [(reward, float(reward[5])) for reward in FISHING_REWARDS]
    for _ in range(count):
        tier, grade, category, name, description, _ = weighted_choice(pool)
        rewards.append(
            normalize_reward(
                {
                    "tier": tier,
                    "grade": grade,
                    "category": category,
                    "name": name,
                    "description": description,
                }
            )
        )
    return rewards


def apply_fishing(record: UserRecord, requested_count: int) -> list[dict[str, Any]]:
    count = max(1, min(requested_count, record.fishing_chances, 10))
    rewards = draw_fishing_rewards(count)
    shown_rewards = []
    record.fishing_chances -= count
    record.pending_fishing = record.fishing_chances
    for reward in rewards:
        reward = normalize_reward(reward, record)
        category = reward_category(reward)
        if category == "\u4ed9\u7f18":
            exp = tier_exp(INSTANT_EXP_BASE, str(reward.get("tier")), str(reward.get("grade")))
            applied_exp, leveled = apply_exp(record, exp)
            reward["used"] = True
            reward["exp_gain"] = applied_exp
            reward["leveled_realms"] = leveled
            if applied_exp < exp:
                reward["blocked"] = True
        else:
            append_reward(record, reward)
        shown_rewards.append(reward)
        bonus_reward = maybe_grant_breakthrough_item(record)
        if bonus_reward:
            bonus_reward["source"] = "\u74f6\u9888\u673a\u7f18"
            shown_rewards.append(bonus_reward)
    return shown_rewards


def fishing_count_from_text(text: str, chances: int) -> int:
    normalized = text.strip().lower()
    if "\u5341" in normalized or "10" in normalized:
        return min(10, chances)
    return 1


def reward_display_name(reward: Optional[dict[str, Any]]) -> str:
    if not reward:
        return "[\u65e0]"
    return f"[{reward.get('tier', '\u672a\u77e5')}{reward.get('grade', '')}{reward.get('category', '')} {reward.get('name', '\u65e0\u540d\u7075\u7269')}]"


def available_artifacts(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, ARTIFACT_CATEGORY)


def available_methods(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, METHOD_CATEGORY)


def available_arrays(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, ARRAY_CATEGORY)


def available_pills(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, PILL_CATEGORY)


def available_talismans(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, TALISMAN_CATEGORY)


def available_puppets(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, PUPPET_CATEGORY)


def available_plants(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, PLANT_CATEGORY)


def available_spirit_stones(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, SPIRIT_STONE_CATEGORY)


def available_misc_items(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, MISC_CATEGORY)


def available_curios(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, CURIO_CATEGORY)


def available_foods(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, FOOD_CATEGORY)


def available_materials(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, "灵材")


def artifact_is_compatible(record: UserRecord, artifact: dict[str, Any]) -> bool:
    return item_is_compatible(record, artifact)


def artifact_power(artifact: Optional[dict[str, Any]], record: Optional[UserRecord] = None) -> int:
    if not artifact:
        return 0
    base = ARTIFACT_POWER_BASE.get(str(artifact.get("tier")), 120)
    ratio = ARTIFACT_GRADE_RATIO.get(str(artifact.get("grade")), 1.0)
    power = int(base * ratio)
    if record is not None and artifact_is_compatible(record, artifact):
        power = int(power * 1.15)
    return power


def method_power(method: Optional[dict[str, Any]], record: Optional[UserRecord] = None) -> int:
    if not method:
        return 0
    base = int(ARTIFACT_POWER_BASE.get(str(method.get("tier")), 120) * 0.72)
    ratio = ARTIFACT_GRADE_RATIO.get(str(method.get("grade")), 1.0)
    power = int(base * ratio)
    if record is not None and item_is_compatible(record, method):
        power = int(power * 1.12)
    return power


def array_power(array: Optional[dict[str, Any]], record: Optional[UserRecord] = None) -> int:
    if not array:
        return 0
    base = int(ARTIFACT_POWER_BASE.get(str(array.get("tier")), 120) * 0.55)
    ratio = ARTIFACT_GRADE_RATIO.get(str(array.get("grade")), 1.0)
    multiplier = array_multiplier(record) if record is not None else 1.0
    return int(base * ratio * min(2.6, multiplier))


def equipped_artifact_name(record: UserRecord) -> str:
    if not record.equipped_artifact:
        return "\u672a\u88c5\u5907\u7075\u5668"
    return reward_display_name(record.equipped_artifact)


def equipped_method_name(record: UserRecord) -> str:
    if not record.equipped_method:
        return "\u672a\u88c5\u5907\u529f\u6cd5"
    return reward_display_name(record.equipped_method)


def equipped_array_name(record: UserRecord) -> str:
    if not record.equipped_array:
        return "\u672a\u5e03\u7f6e\u9635\u76d8"
    return reward_display_name(record.equipped_array)


def equipped_puppet_name(record: UserRecord) -> str:
    if not record.equipped_puppet:
        return "未装备傀儡"
    return reward_display_name(record.equipped_puppet)


def planted_spirit_plant_name(record: UserRecord) -> str:
    if not record.planted_spirit_plant:
        return "未栽种灵植"
    return reward_display_name(record.planted_spirit_plant)


def puppet_power(puppet: Optional[dict[str, Any]], record: Optional[UserRecord] = None) -> int:
    if not puppet:
        return 0
    base = ARTIFACT_POWER_BASE.get(str(puppet.get("tier")), 120)
    ratio = ARTIFACT_GRADE_RATIO.get(str(puppet.get("grade")), 1.0)
    rate = PUPPET_POWER_RATE.get(str(puppet.get("tier")), 0.55)
    return int(base * ratio * rate)


def plant_sign_bonus(record: UserRecord, base_exp: int) -> int:
    plant = record.planted_spirit_plant
    if not plant or base_exp <= 0:
        return 0
    rate = PLANT_SIGN_RATE.get(str(plant.get("tier")), 0.08)
    bonus = int(base_exp * rate * grade_ratio(str(plant.get("grade"))))
    return max(1, bonus)


def equip_artifact(record: UserRecord, artifact_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, ARTIFACT_CATEGORY, artifact_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7075\u5668\u3002"
    _, artifact = result
    if not artifact_is_compatible(record, artifact):
        required_attribute = reward_required_attribute(artifact)
        return False, f"{reward_display_name(artifact)} \u9700\u6c42{required_attribute}\u7075\u6839\uff0c\u6682\u65f6\u65e0\u6cd5\u88c5\u5907\u3002"
    record.equipped_artifact = dict(artifact)
    return True, f"\u5df2\u88c5\u5907 {reward_display_name(artifact)}\uff0c\u6218\u529b\u63d0\u5347 {artifact_power(artifact, record)}\u3002"


def equip_method(record: UserRecord, method_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, METHOD_CATEGORY, method_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u529f\u6cd5\u3002"
    _, method = result
    if not item_is_compatible(record, method):
        required_attribute = reward_required_attribute(method)
        return False, f"{reward_display_name(method)} \u9700\u6c42{required_attribute}\u7075\u6839\uff0c\u6682\u65f6\u65e0\u6cd5\u4fee\u884c\u3002"
    record.equipped_method = dict(method)
    return True, f"\u5df2\u53c2\u609f {reward_display_name(method)}\uff0c\u7b7e\u5230\u4e0e\u804a\u5929\u4fee\u4e3a\u5c06\u83b7\u5f97\u52a0\u6210\u3002"


def equip_array(record: UserRecord, array_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, ARRAY_CATEGORY, array_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u9635\u76d8\u3002"
    _, array = result
    record.equipped_array = dict(array)
    multiplier = array_multiplier(record)
    return True, f"\u5df2\u5e03\u7f6e {reward_display_name(array)}\uff0c\u5f53\u524d\u9635\u6cd5\u6548\u679c {multiplier:.1f}x\u3002"


def equip_puppet(record: UserRecord, puppet_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, PUPPET_CATEGORY, puppet_index)
    if result is None:
        return False, "没有找到这个编号的傀儡。"
    _, puppet = result
    record.equipped_puppet = dict(puppet)
    return True, f"已唤醒 {reward_display_name(puppet)}，战力提升 {puppet_power(puppet, record)}。"


def plant_spirit_plant(record: UserRecord, plant_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, PLANT_CATEGORY, plant_index)
    if result is None:
        return False, "没有找到这个编号的灵植。"
    _, plant = result
    record.planted_spirit_plant = dict(plant)
    rate = PLANT_SIGN_RATE.get(str(plant.get("tier")), 0.08) * grade_ratio(str(plant.get("grade")))
    return True, f"已栽种 {reward_display_name(plant)}，每日签到修为约增加 {rate:.0%}。"


def unequip_artifact(record: UserRecord) -> str:
    if not record.equipped_artifact:
        return "\u5f53\u524d\u6ca1\u6709\u88c5\u5907\u7075\u5668\u3002"
    old_name = reward_display_name(record.equipped_artifact)
    record.equipped_artifact = None
    return f"\u5df2\u5378\u4e0b {old_name}\u3002"


def blocked_cultivation_message(record: UserRecord) -> str:
    lock_text = cultivation_lock_text(record)
    return f"当前处于秘境反噬惩罚期，{lock_text}，暂时无法提升修为。" if lock_text else "当前无法提升修为。"


def use_pill(record: UserRecord, pill_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, PILL_CATEGORY, pill_index)
    if result is None:
        return False, "没有找到这个编号的丹药。"
    name = reward_name(result)
    requirement = current_breakthrough_requirement(record)
    if requirement and name in set(requirement["items"]):
        append_reward(record, result)
        return False, f"{reward_display_name(result)} 是当前突破道具，请发送“突破”使用。"
    if is_cultivation_locked(record):
        append_reward(record, result)
        return False, blocked_cultivation_message(record)
    exp = tier_exp(CONSUMABLE_EXP_BASE, str(result.get("tier")), str(result.get("grade")))
    applied_exp, leveled = apply_exp(record, exp)
    if applied_exp <= 0:
        append_reward(record, result)
        return False, "当前已至瓶颈巅峰，服用丹药也无法增长修为，请先突破。"
    extra = f"，连破 {leveled} 境" if leveled else ""
    return True, f"服用 {reward_display_name(result)}，修为 +{applied_exp}{extra}。"


def refine_spirit_stone(record: UserRecord, stone_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, SPIRIT_STONE_CATEGORY, stone_index)
    if result is None:
        return False, "没有找到这个编号的灵石。"
    if is_cultivation_locked(record):
        append_reward(record, result)
        return False, blocked_cultivation_message(record)
    reserve = int(SPIRIT_STONE_VALUES.get(str(result.get("tier")), 8) * grade_ratio(str(result.get("grade"))))
    record.spirit_stones += reserve
    exp = max(1, reserve // 2)
    applied_exp, leveled = apply_exp(record, exp)
    if applied_exp <= 0:
        append_reward(record, result)
        record.spirit_stones = max(0, record.spirit_stones - reserve)
        return False, "当前已至瓶颈巅峰，灵石灵气无法继续炼入丹田，请先突破。"
    extra = f"，连破 {leveled} 境" if leveled else ""
    return True, f"炼化 {reward_display_name(result)}，灵石储备 +{reserve}，修为 +{applied_exp}{extra}。"


def use_food(record: UserRecord, food_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, FOOD_CATEGORY, food_index)
    if result is None:
        return False, "没有找到这个编号的灵食。"
    if is_cultivation_locked(record):
        append_reward(record, result)
        return False, blocked_cultivation_message(record)
    exp = max(1, tier_exp(CONSUMABLE_EXP_BASE, str(result.get("tier")), str(result.get("grade"))) // 2)
    applied_exp, leveled = apply_exp(record, exp)
    if applied_exp <= 0:
        append_reward(record, result)
        return False, "当前已至瓶颈巅峰，灵食只能暖胃，无法再涨修为。"
    extra = f"，连破 {leveled} 境" if leveled else ""
    return True, f"享用 {reward_display_name(result)}，气血回暖，修为 +{applied_exp}{extra}。"


def use_curio(record: UserRecord, curio_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, CURIO_CATEGORY, curio_index)
    if result is None:
        return False, "没有找到这个编号的奇物。"
    name = reward_name(result)
    requirement = current_breakthrough_requirement(record)
    if requirement and name in set(requirement["items"]):
        append_reward(record, result)
        return False, f"{reward_display_name(result)} 是当前突破道具，请发送“突破”使用。"
    roll = random.random()
    if roll < 0.38:
        record.fishing_chances += 1
        return True, f"催动 {reward_display_name(result)}，诸天水波轻响，垂钓次数 +1。"
    if roll < 0.78:
        if is_cultivation_locked(record):
            append_reward(record, result)
            return False, blocked_cultivation_message(record)
        exp = tier_exp(INSTANT_EXP_BASE, str(result.get("tier")), str(result.get("grade")))
        applied_exp, leveled = apply_exp(record, exp)
        if applied_exp <= 0:
            append_reward(record, result)
            return False, "当前已至瓶颈巅峰，奇物灵机无法炼化，请先突破。"
        extra = f"，连破 {leveled} 境" if leveled else ""
        return True, f"参悟 {reward_display_name(result)}，心神通明，修为 +{applied_exp}{extra}。"
    reward = draw_fishing_rewards(1)[0]
    append_reward(record, reward)
    return True, f"{reward_display_name(result)} 内藏夹层，取出 {reward_display_name(reward)}。"


def identify_misc_item(record: UserRecord, misc_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, MISC_CATEGORY, misc_index)
    if result is None:
        return False, "没有找到这个编号的杂物。"
    roll = random.random()
    if roll < 0.45:
        pool = [reward for reward in FISHING_REWARDS if reward[2] not in {"仙缘", "杂物"}]
        tier, grade, category, name, description, _ = weighted_choice([(reward, float(reward[5])) for reward in pool])
        reward = normalize_reward({"tier": tier, "grade": grade, "category": category, "name": name, "description": description}, record)
        append_reward(record, reward)
        return True, f"鉴定 {reward_display_name(result)}，竟辨出 {reward_display_name(reward)}。"
    if roll < 0.72:
        if is_cultivation_locked(record):
            return True, f"鉴定 {reward_display_name(result)}，只散出一缕灵气；因禁修期未能吸纳。"
        exp = max(1, tier_exp(CONSUMABLE_EXP_BASE, str(result.get("tier")), str(result.get("grade"))) // 3)
        applied_exp, _ = apply_exp(record, exp)
        return True, f"鉴定 {reward_display_name(result)}，残余灵气入体，修为 +{applied_exp}。"
    return True, f"鉴定 {reward_display_name(result)}，只是旧物一件，随手化作尘灰。"


def talisman_required_realm_index(tier: str) -> int:
    if tier in {"\u51e1\u54c1", "\u9ec4\u9636"}:
        return 0
    if tier == "\u7384\u9636":
        return 3
    if tier == "\u5730\u9636":
        return 4
    if tier == "\u5929\u9636":
        return 5
    return 0


def use_talisman(record: UserRecord, talisman_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, TALISMAN_CATEGORY, talisman_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7b26\u7b93\u3002"
    list_index, talisman = result
    required_index = talisman_required_realm_index(str(talisman.get("tier")))
    if record.realm_index < required_index:
        return False, f"{reward_display_name(talisman)} \u9700\u8981{REALMS[required_index]}\u624d\u80fd\u4f7f\u7528\u3002"
    if record.rewards is not None:
        record.rewards.pop(list_index)
    strength = tier_exp(CONSUMABLE_EXP_BASE, str(talisman.get("tier")), str(talisman.get("grade"))) * 6
    return True, f"\u6fc0\u53d1 {reward_display_name(talisman)}\uff0c\u7b26\u5149\u5316\u4f5c {strength} \u70b9\u5386\u7ec3\u5a01\u52bf\u3002"


def mystic_realm_title(realm: dict[str, Any]) -> str:
    if realm.get("title"):
        return str(realm["title"])
    realm_type = str(realm.get("type", "未知秘境"))
    if realm_type == "兽潮":
        return f"{realm.get('boss_realm', '未知')}兽巢"
    return realm_type


def mystic_realm_options_text(record: UserRecord) -> str:
    realm = record.mystic_realm or {}
    options = list(realm.get("options", []))
    if not realm:
        return "当前没有正在探索的秘境。"
    lines = [f"【秘境探索】{mystic_realm_title(realm)}", f"剩余探索次数：{int(realm.get('steps_left', 0))}/{MYSTIC_REALM_MAX_STEPS}"]
    if realm.get("type") == "兽潮":
        lines.append(f"兽潮首领：{realm.get('boss_realm', '未知')}·{realm.get('boss_name', '无名妖兽')}")
    if realm.get("insight") and realm.get("bad_option_index"):
        lines.append(f"天机示警：第 {int(realm.get('bad_option_index'))} 项通往坏结局。")
    for index, option in enumerate(options, start=1):
        lines.append(f"{index}. {option}")
    lines.append("发送“探索 编号”继续。")
    return "\n".join(lines)


def roll_mystic_options(realm_type: str) -> list[str]:
    pool = MYSTIC_OPTION_POOLS.get(realm_type, MYSTIC_OPTION_POOLS["上古宗门遗址"])
    return random.sample(pool, k=min(5, len(pool)))


def mystic_realm_intro(realm: dict[str, Any]) -> str:
    realm_type = str(realm.get("type"))
    if realm_type == "上古宗门遗址":
        return "残碑半埋，山门无声，深处仍有经卷气息流转。"
    if realm_type == "兽潮":
        return f"远处妖云翻涌，探得{realm.get('boss_realm', '未知')}兽巢，首领似为{realm.get('boss_name', '无名妖兽')}。"
    return "洞府石门半启，禁制明灭不定，像是传承，也像是请君入瓮。"


def realm_short_name(realm_name: str) -> str:
    for suffix in ("期", "境"):
        if realm_name.endswith(suffix):
            return realm_name[:-1]
    return realm_name


def recommended_realm_text(index: int, stage: str = "") -> str:
    base = realm_short_name(REALMS[max(0, min(index, len(REALMS) - 1))])
    return f"{base}{stage}" if stage else base


def mystic_realm_title_from_entry(entry: dict[str, Any]) -> str:
    entry_type = str(entry.get("type", "未知秘境"))
    if entry.get("title"):
        return str(entry["title"])
    if entry_type == "兽潮":
        return f"{recommended_realm_text(int(entry.get('boss_realm_index', 1)))}妖兽兽巢"
    return entry_type


def draw_mystic_entrances(record: UserRecord) -> list[dict[str, Any]]:
    base_index = max(1, record.realm_index or 1)
    sect_index = max(2, min(len(REALMS) - 1, base_index + random.choice([0, 1, 1, 2])))
    if random.random() < 0.5:
        beast_index = max(1, min(len(REALMS) - 1, random.choice([base_index, base_index - 1])))
    else:
        beast_index = max(2, min(len(REALMS) - 1, base_index + random.choice([1, 2, 2, 3])))
    cave_index = max(3, min(len(REALMS) - 1, base_index + random.choice([2, 3, 3, 4])))
    beast_stage = random.choice(["初期", "中期", "后期", "圆满"])
    entries = [
        {
            "type": "上古宗门遗址",
            "title": "上古宗门遗址",
            "recommended_index": sect_index,
            "recommended": recommended_realm_text(sect_index),
            "danger": random.randint(12, 30),
        },
        {
            "type": "兽潮",
            "title": f"{recommended_realm_text(beast_index)}妖兽兽巢",
            "recommended_index": beast_index,
            "recommended": recommended_realm_text(beast_index, beast_stage),
            "boss_realm_index": beast_index,
            "boss_realm": REALMS[beast_index],
            "boss_name": random.choice(BEAST_NAME_PREFIXES) + random.choice(BEAST_NAME_SUFFIXES),
            "danger": random.randint(18, 38),
        },
        {
            "type": "上古大能洞府",
            "title": "上古大能洞府",
            "recommended_index": cave_index,
            "recommended": recommended_realm_text(cave_index),
            "danger": random.randint(22, 46),
            "false_lure": random.random() < 0.35,
        },
    ]
    return entries


def assign_mystic_bad_option(realm: dict[str, Any]) -> None:
    options = list(realm.get("options", []))
    if realm.get("insight") and options:
        realm["bad_option_index"] = random.randint(1, len(options))
    else:
        realm.pop("bad_option_index", None)


def start_mystic_realm(
    record: UserRecord,
    realm_type: str,
    today: Optional[date] = None,
    entrance: Optional[dict[str, Any]] = None,
) -> tuple[bool, str]:
    entrance = entrance or {}
    realm_type = str(entrance.get("type") or realm_type).strip()
    if realm_type not in MYSTIC_REALM_TYPES:
        return False, "秘境类型可选：上古宗门遗址、兽潮、上古大能洞府。"
    if record.mystic_realm:
        return False, mystic_realm_options_text(record)
    if is_cultivation_locked(record, today):
        return False, blocked_cultivation_message(record)
    recommended_index = int(entrance.get("recommended_index", max(1, min(len(REALMS) - 1, record.realm_index + 2))))
    boss_realm = str(entrance.get("boss_realm") or REALMS[min(len(REALMS) - 1, recommended_index)])
    boss_name = str(entrance.get("boss_name") or (random.choice(BEAST_NAME_PREFIXES) + random.choice(BEAST_NAME_SUFFIXES)))
    realm = {
        "type": realm_type,
        "title": mystic_realm_title_from_entry(entrance) if entrance else realm_type,
        "recommended": entrance.get("recommended") or recommended_realm_text(recommended_index),
        "steps_left": MYSTIC_REALM_MAX_STEPS,
        "step": 0,
        "danger": int(entrance.get("danger", random.randint(12, 30) if realm_type != "上古大能洞府" else random.randint(20, 42))),
        "false_lure": bool(entrance.get("false_lure", realm_type == "上古大能洞府" and random.random() < 0.35)),
        "boss_realm": boss_realm,
        "boss_name": boss_name,
        "options": roll_mystic_options(realm_type),
        "insight": bool(entrance.get("insight")),
        "tianji": bool(entrance.get("tianji")),
    }
    assign_mystic_bad_option(realm)
    if realm.get("tianji") and today is not None:
        record.last_tianji_mystic_date = today.isoformat()
    record.mystic_realm = realm
    return True, f"{mystic_realm_intro(realm)}\n{mystic_realm_options_text(record)}"

def mystic_reward_category(realm_type: str) -> str:
    if realm_type == "上古宗门遗址":
        return weighted_choice([("功法", 4), ("丹药", 2), ("阵盘", 2), ("灵材", 3), ("杂物", 1)])
    if realm_type == "兽潮":
        return weighted_choice([("灵材", 5), ("灵石", 3), ("傀儡", 1), ("符箓", 2), ("灵食", 2)])
    return weighted_choice([("奇物", 3), ("灵器", 2), ("丹药", 2), ("阵盘", 2), ("灵材", 2), ("杂物", 2)])


def draw_reward_by_category(category: str) -> dict[str, Any]:
    pool = [reward for reward in FISHING_REWARDS if reward[2] == category]
    if not pool:
        return draw_fishing_rewards(1)[0]
    tier, grade, item_category, name, description, _ = weighted_choice([(reward, float(reward[5])) for reward in pool])
    return normalize_reward({"tier": tier, "grade": grade, "category": item_category, "name": name, "description": description})


def mystic_success_chance(record: UserRecord, realm: dict[str, Any]) -> float:
    power = battle_power(record)
    danger = int(realm.get("danger", 20))
    threshold = max(900, (record.realm_index + 1) * 850 + danger * 45)
    chance = 0.42 + min(0.32, power / max(1, threshold) * 0.18)
    if record.equipped_puppet:
        chance += 0.08
    if record.equipped_array:
        chance += 0.04
    return max(0.18, min(0.82, chance))


def explore_mystic_realm(record: UserRecord, option_index: int, today: Optional[date] = None) -> tuple[bool, str]:
    realm = record.mystic_realm
    if not realm:
        return False, "当前没有正在探索的秘境，发送“秘境”查看入口。"
    options = list(realm.get("options", []))
    if option_index < 1 or option_index > len(options):
        return False, f"请选择 1-{len(options)} 之间的探索选项。"
    choice = options[option_index - 1]
    realm_type = str(realm.get("type"))
    realm["step"] = int(realm.get("step", 0)) + 1
    realm["steps_left"] = max(0, int(realm.get("steps_left", MYSTIC_REALM_MAX_STEPS)) - 1)
    success_chance = mystic_success_chance(record, realm)
    bad_rate = 0.08 + int(realm.get("danger", 20)) / 500
    if realm.get("false_lure") and not record.evil_cultivator:
        bad_rate += 0.12
    if int(realm.get("bad_option_index", 0)) == option_index:
        bad_rate = max(bad_rate, 0.88)
    elif realm.get("insight"):
        bad_rate = max(0.02, bad_rate * 0.35)
    if record.equipped_puppet:
        bad_rate = max(0.03, bad_rate - 0.04)
    roll = random.random()
    lines = [f"你选择：{choice}"]
    if realm.get("false_lure") and record.evil_cultivator:
        lines.append("邪修气息识破了洞府中的同源陷阱，你没有因此直接坠入杀局。")
    if roll < bad_rate:
        lock_days = 2 if record.evil_cultivator else 1
        lock_text = lock_cultivation(record, today, lock_days)
        record.mystic_realm = None
        lines.append("禁制骤然反卷，眼前所见化作杀局。你强行脱身，却被浊气封住经脉。")
        penalty = "两天" if record.evil_cultivator else "一天"
        lines.append(f"坏结局：进入{penalty}惩罚期，{lock_text}，期间无法通过任何手段提升修为。")
        return True, "\n".join(lines)
    if roll < bad_rate + success_chance:
        category = mystic_reward_category(realm_type)
        reward = draw_reward_by_category(category)
        append_reward(record, reward)
        lines.append(f"此行有惊无险，获得 {reward_display_name(reward)}。")
        if category not in {"功法", "灵器", "阵盘", "傀儡", "灵植"} and not is_cultivation_locked(record, today):
            exp = max(1, tier_exp(CONSUMABLE_EXP_BASE, str(reward.get("tier")), str(reward.get("grade"))) // 4)
            applied, _ = apply_exp(record, exp)
            if applied:
                lines.append(f"顺势炼化一缕灵机，修为 +{applied}。")
    else:
        lines.append(random.choice(["石壁无声合拢，你绕行半晌才寻回原路。", "风声像人在耳边低语，最终却什么也没有留下。", "一阵灵压扫过，你稳住气息，避开了暗处杀机。", "前方气机紊乱，你谨慎退开，未再深入。"]))
    if int(realm.get("steps_left", 0)) <= 0:
        record.mystic_realm = None
        lines.append("十次探索已尽，秘境门户在身后缓缓闭合。")
        return True, "\n".join(lines)
    realm["options"] = roll_mystic_options(realm_type)
    assign_mystic_bad_option(realm)
    record.mystic_realm = realm
    lines.append("")
    lines.append(mystic_realm_options_text(record))
    return True, "\n".join(lines)


def artifact_is_sword(artifact: Optional[dict[str, Any]]) -> bool:
    name = reward_name(artifact)
    return any(token in name for token in ("剑", "飞剑", "剑谱"))


def route_power_multiplier(record: UserRecord) -> float:
    if record.cultivation_route == "剑修" and artifact_is_sword(record.equipped_artifact):
        return 1.3
    if record.cultivation_route == "术修" and record.equipped_artifact and not artifact_is_sword(record.equipped_artifact):
        return 1.3
    return 1.0


def battle_power(record: UserRecord) -> int:
    realm_power = (record.realm_index + 1) * 900 + record.realm_exp * 3
    exp_power = record.total_exp * 2 + record.pending_exp
    sign_power = record.sign_count * 20
    root_power = 120
    if record.root:
        root_power += 320 + record.root.tier_rank * 280 + record.root.grade_rank * 120
    root_power += len(record.extra_roots or []) * 220
    foundation_bonus = realm_quality_power(record)
    equipment_power = (
        artifact_power(record.equipped_artifact, record)
        + method_power(record.equipped_method, record)
        + array_power(record.equipped_array, record)
        + puppet_power(record.equipped_puppet, record)
    )
    power = realm_power + exp_power + sign_power + root_power + foundation_bonus + equipment_power
    power = int(power * route_power_multiplier(record))
    if is_breakthrough_bottleneck(record):
        power = int(power * 1.1)
    return max(1, power)


def battle_summary(record: UserRecord) -> dict[str, Any]:
    equipment_power = (
        artifact_power(record.equipped_artifact, record)
        + method_power(record.equipped_method, record)
        + array_power(record.equipped_array, record)
        + puppet_power(record.equipped_puppet, record)
    )
    return {
        "power": battle_power(record),
        "realm": record.realm if record.root else "\u672a\u5165\u95e8",
        "total_exp": record.total_exp,
        "pending_exp": record.pending_exp,
        "artifact": equipped_artifact_name(record),
        "method": equipped_method_name(record),
        "array": equipped_array_name(record),
        "puppet": equipped_puppet_name(record),
        "plant": planted_spirit_plant_name(record),
        "spirit_stones": record.spirit_stones,
        "array_multiplier": array_multiplier(record),
        "artifact_power": artifact_power(record.equipped_artifact, record),
        "puppet_power": puppet_power(record.equipped_puppet, record),
        "equipment_power": equipment_power,
        "cultivation_lock": cultivation_lock_text(record),
        "mystic_realm": mystic_realm_title(record.mystic_realm) if record.mystic_realm else "无",
        "foundation_type": record.foundation_type or "",
        "realm_quality": realm_quality_text(record),
        "is_bottleneck": is_breakthrough_bottleneck(record),
        "breakthrough_required": breakthrough_required_text(record),
        "route": record.route_summary,
        "identity": record.identity_summary,
        "hehuan_remaining": hehuan_remaining_text(record),
        "tianji_status": tianji_status_text(record),
        "spirit_stones_text": spirit_stone_text(record.spirit_stones),
    }


def duel_records(attacker: UserRecord, defender: UserRecord) -> DuelResult:
    attacker_power = battle_power(attacker)
    defender_power = battle_power(defender)
    total = max(1, attacker_power + defender_power)
    chance = max(0.1, min(0.9, attacker_power / total))
    attacker_win = random.random() < chance
    root = attacker.root if attacker_win else defender.root
    detail = DUEL_ACTIONS.get(root.attribute, "\u7075\u6c14\u7ffb\u6d8c\uff0c\u80dc\u8d1f\u4e00\u7ebf") if root else "\u62f3\u811a\u4ea4\u9519\uff0c\u5c18\u70df\u56db\u8d77"
    return DuelResult(
        attacker_power=attacker_power,
        defender_power=defender_power,
        attacker_win=attacker_win,
        chance=chance,
        detail=detail,
    )


def rank_reward_for(rank: int) -> tuple[int, int]:
    if rank == 1:
        return 36, 2
    if rank == 2:
        return 28, 1
    if rank == 3:
        return 22, 1
    if 4 <= rank <= 5:
        return 16, 0
    if 6 <= rank <= 10:
        return 10, 0
    return 0, 0


def apply_rank_reward(record: UserRecord, rank: int) -> RankReward:
    exp, fishing_chances = rank_reward_for(rank)
    reward = RankReward(rank=rank, exp=exp, fishing_chances=fishing_chances)
    if exp <= 0 and fishing_chances <= 0:
        return reward

    if record.root is None or is_cultivation_locked(record):
        record.pending_exp += exp
        reward.pending = True
    else:
        applied_exp, reward.leveled_realms = apply_exp(record, exp)
        reward.exp = applied_exp
    record.fishing_chances += fishing_chances
    return reward
