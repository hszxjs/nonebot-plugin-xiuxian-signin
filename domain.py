from __future__ import annotations

import hashlib
import random
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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

TIER_ORDER = ["凡品", "黄阶", "玄阶", "地阶", "天阶", "仙阶", "仙帝兵"]
ROOT_TIER_ORDER = ["凡品", "黄阶", "玄阶", "地阶", "天阶", "变异灵根"]
GRADE_ORDER = ["下品", "中品", "上品", "极品"]
METHOD_GROWTH_TIERS = ["凡品", "黄阶", "玄阶", "地阶", "天阶", "仙阶"]
METHOD_LAYER_STEP = 10
METHOD_UNLIMITED_LAYER_MAX = 10**9
ARRAY_GROWTH_TIERS = METHOD_GROWTH_TIERS
ARRAY_LAYER_STEP = 10
ARRAY_UNLIMITED_LAYER_MAX = 10**9
ARRAY_MULTIPLIER_CAP_BY_TIER = {
    "凡品": 5.0,
    "凡阶": 5.0,
    "黄阶": 10.0,
    "玄阶": 20.0,
    "地阶": 50.0,
    "天阶": 100.0,
}
TIER_RANKS = {name: rank for name, rank, _ in QUALITY_TIER_POOL}
TIER_RANKS["变异灵根"] = 5
TIER_RANKS["仙阶"] = 5
TIER_RANKS["仙帝兵"] = 6
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

BASE_FIVE_ELEMENTS = ("金", "木", "水", "火", "土")
ROOT_ATTRIBUTE_ALIASES = {"道": "先天道体"}


def normalize_root_attribute(attribute: Optional[str]) -> str:
    text = str(attribute or "").strip()
    return ROOT_ATTRIBUTE_ALIASES.get(text, text)


def root_attribute_label(attribute: Optional[str]) -> str:
    normalized = normalize_root_attribute(attribute)
    return "道" if normalized == "先天道体" else normalized


def root_attribute_name(attribute: Optional[str]) -> str:
    normalized = normalize_root_attribute(attribute)
    label = root_attribute_label(normalized)
    return ATTRIBUTE_NAMES.get(normalized, f"{label}灵根")


MUTATION_ROOT_SOURCES = {
    "雷": (("金", "水"), ("火", "水")),
    "冰": (("水", "木"),),
    "风": (("木", "火"),),
    "暗": (("金", "土"),),
    "光": (("火", "土"),),
    "混沌": (BASE_FIVE_ELEMENTS,),
}
SPECIAL_ROOT_SOURCES = {
    "剑": ("金",),
    "药": ("木",),
    "玄阴": ("水",),
    "玄阳": ("火",),
    "空": (),
    "时": (),
    "先天道体": BASE_FIVE_ELEMENTS,
}
ROOT_ATTRIBUTES = list(dict.fromkeys(list(ATTRIBUTES) + list(MUTATION_ROOT_SOURCES) + list(SPECIAL_ROOT_SOURCES)))
ARTIFACT_MUTATION_ATTRIBUTES = ["雷", "冰", "风", "光", "暗", "先天道体", "混沌"]
ARTIFACT_ATTRIBUTES = list(
    dict.fromkeys(list(ATTRIBUTES) + [attr for attr in ARTIFACT_MUTATION_ATTRIBUTES if attr not in ATTRIBUTES])
)
ROOT_ATTRIBUTE_ORDER = {
    attribute: index
    for index, attribute in enumerate(
        list(dict.fromkeys(list(ROOT_ATTRIBUTES) + [attr for attr in ARTIFACT_ATTRIBUTES if attr not in ROOT_ATTRIBUTES]))
    )
}


def root_attribute_sort_key(attribute: Optional[str]) -> tuple[int, str]:
    normalized = normalize_root_attribute(attribute)
    return (ROOT_ATTRIBUTE_ORDER.get(normalized, len(ROOT_ATTRIBUTE_ORDER)), normalized)


ATTRIBUTE_COLORS.update(
    {
        "风": "#58b88f",
        "暗": "#5b4b73",
        "光": "#f2c84b",
        "混沌": "#7f6bc8",
        "剑": "#c8d3df",
        "药": "#58b46f",
        "玄阴": "#5b8ccf",
        "玄阳": "#e66a3d",
        "空": "#6d8be8",
        "时": "#b58adf",
        "先天道体": "#d8b85f",
    }
)
ATTRIBUTE_NAMES.update(
    {
        "风": "风灵根",
        "暗": "暗灵根",
        "光": "光灵根",
        "混沌": "混沌灵根",
        "剑": "剑灵根",
        "药": "药灵根",
        "玄阴": "玄阴灵根",
        "玄阳": "玄阳灵根",
        "空": "空灵根",
        "时": "时灵根",
        "先天道体": "道灵根",
    }
)
ROOT_TRAITS = {
    "金": "锋锐：灵器与剑诀威力提高",
    "木": "生息：灵植、丹道与恢复更稳",
    "水": "绵长：修炼续航与神魂韧性提高",
    "火": "炽烈：爆发术式与炼丹火候更强",
    "土": "厚载：护甲、阵盘与体魄更稳",
    "雷": "迅疾：速度与暴击率提高",
    "冰": "凝霜：效果命中、闪避与控制提高",
    "风": "御风：先手、身法与追击提高",
    "暗": "匿影：陷阱识破与偷袭伤害提高",
    "光": "明净：破邪、治疗与抗心魔提高",
    "混沌": "混沌：五行归一，灵器与功法兼容面极广",
    "剑": "极锋：剑类灵器与剑诀大幅契合",
    "药": "药心：炼丹、灵植与丹药吸收提高",
    "玄阴": "阴极：神魂、控制与冰水功法契合",
    "玄阳": "阳极：气血、火法与锻体功法契合",
    "空": "空间：秘境探索与闪避更有优势",
    "时": "时间：冷却与修炼沉淀更有优势",
    "先天道体": "道韵：全属性兼容，功法契合极高",
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
    '假仙境',
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
    '归真境',
    '太初境',
    '鸿蒙境',
    '玄黄境',
    '无量境',
    '造化境',
    '太素境',
    '太极境',
    '无始境',
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
    "神通",
]
REWARD_MIN_COUNTS = {"仙缘": 5, "阵盘": 3, "灵器": 7, "功法": 7, "神通": 5}
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
    "神通": 0.22,
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
    "神通": "{name}中藏着一段失落感悟，参悟后有机会领悟神通。",
    "仙源": "{name}凝成一缕可纳入灵台的仙源，真仙之后可纳入己身。",
}
FISHING_REWARD_NAMES = {
    "仙缘": {
        "天阶": ["元初一气", "浑元灵胎", "万道真种", "星初仙契", "造化玉露"],
        "地阶": ["洞府福脉", "星河灵胎", "玄黄命砂", "青华仙引", "云海灵契"],
        "玄阶": ["古洞机缘", "残碑悟道", "月华灵髓", "雾隐仙芽", "灵台清光"],
        "黄阶": ["山神馈赠", "灵泉一盏", "旧庙香火", "药园残运", "云游道人指点"],
        "凡品": ["半页机缘签", "梦里仙人一笑", "井底月光", "小摊旧铜钱", "破庙避雨缘"],
    },
    "灵器": {
        "天阶": ["云海镇澜印", "星阙断岳剑"],
        "地阶": ["青冥飞剑", "玄都镇魂铃"],
        "玄阶": ["寒铁护心镜", "流云缚妖索"],
        "黄阶": ["赤铜伏魔杖", "青竹听风剑"],
        "凡品": ["外门铁剑", "木柄小灵锤"],
    },
    "功法": {
        "天阶": ["星墟观想篇", "万象归元经"],
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
        "天阶": ["星罗天衡阵盘", "星墟锁界盘", "星律归墟盘"],
        "地阶": ["四仪护山盘", "玄甲镇宅盘", "青麟引雷盘"],
        "玄阶": ["小五行聚灵盘", "云纹迷踪盘", "水月镜花盘"],
        "黄阶": ["三才守门盘", "风火警戒盘", "土行稳基盘"],
        "凡品": ["石子迷阵盘", "草绳护院盘", "旧木罗盘"],
    },
    "灵材": {
        "天阶": ["浑元星砂", "白曜仙金"],
        "地阶": ["星陨玄铁", "玄冰玉髓"],
        "玄阶": ["赤霞铜精", "青藤灵骨"],
        "黄阶": ["百炼寒铁", "紫纹灵木"],
        "凡品": ["发亮矿渣", "溪边圆石"],
    },
    "符箓": {
        "天阶": ["移形换位符", "太上清宁符"],
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
        "天阶": ["镜湖碎光", "逆命铜铃"],
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
    "天阶": {"金": "星阙断岳剑", "木": "青衡万木杖", "水": "云海镇澜印", "火": "焚天离火旗", "土": "坤舆镇岳印", "雷": "玄雷破劫槌", "冰": "寒冥锁天镜"},
    "地阶": {"金": "青冥飞剑", "木": "万木回春尺", "水": "沧海分潮珠", "火": "赤阳炼魔炉", "土": "玄都镇魂铃", "雷": "五雷荡邪鼓", "冰": "寒魄凝霜环"},
    "玄阶": {"金": "寒铁护心镜", "木": "青藤缚妖索", "水": "水月流光佩", "火": "赤霞焚影刀", "土": "厚土镇岳盾", "雷": "奔雷破阵枪", "冰": "凝冰照影针"},
    "黄阶": {"金": "赤铜伏魔杖", "木": "青竹听风剑", "水": "碧波纳气瓶", "火": "烈焰短戟", "土": "黄玉护身符", "雷": "引雷桃木剑", "冰": "霜纹短刃"},
    "凡品": {"金": "外门铁剑", "木": "木柄小灵锤", "水": "清水符瓶", "火": "火折灵灯", "土": "粗陶护心坠", "雷": "响雷铜铃", "冰": "薄冰小镜"},
}

METHOD_NAMES_BY_TIER_ATTR = {
    "天阶": {"金": "白衡斩星经", "木": "青衡生息经", "水": "寒冥归海经", "火": "焚天真阳录", "土": "厚土载道篇", "雷": "玄霄神雷诀", "冰": "玄阴冰魄录"},
    "地阶": {"金": "庚金剑典", "木": "万木回春功", "水": "沧海听雷诀", "火": "离火炼神诀", "土": "玄黄镇岳功", "雷": "五雷正法", "冰": "寒魄凝真诀"},
    "玄阶": {"金": "金锋破云诀", "木": "青木长生功", "水": "碧海潮生诀", "火": "赤霞炼气篇", "土": "山岳稳基法", "雷": "奔雷锻脉诀", "冰": "霜华凝息术"},
    "黄阶": {"金": "锐金吐纳术", "木": "草木养气诀", "水": "小云雨诀", "火": "烈阳锻体篇", "土": "黄庭培元功", "雷": "引雷入门诀", "冰": "寒息入静篇"},
    "凡品": {"金": "半卷残破剑谱", "木": "外门植木诀", "水": "溪畔纳气术", "火": "灶火炼身法", "土": "外门入静诀", "雷": "听雷杂记", "冰": "冷泉静坐法"},
}


EXTRA_ARTIFACT_NAMES_BY_TIER_ATTR = {
    "天阶": {
        "金": ["斩道庚金剑", "白帝镇天戈", "星河断岳刃"],
        "木": ["青桑万灵弓", "青华开岳尺", "巨木归墟杖"],
        "水": ["归墟沧海珠", "玄水量天瓶", "天河镇魔印"],
        "火": ["赤羽焚世旗", "赤阳炼神炉", "离火吞星钟"],
        "土": ["息壤万山玺", "玄黄镇界碑", "厚土载天鼎"],
        "雷": ["玄雷万劫剑", "九天雷祖锤", "劫海镇魂鼓"],
        "冰": ["玄阴封界轮", "寒狱照神镜", "玄霜葬天枪"],
    },
    "地阶": {
        "金": ["碎星金鳞剑", "庚金裂空斧", "白虹穿云枪"],
        "木": ["青桑回春铃", "万藤缚龙索", "古木灵纹弓"],
        "水": ["碧海分光珠", "潮生覆月扇", "寒潭镇妖瓶"],
        "火": ["赤莲焚妖刀", "地肺火鸦炉", "火云破阵旗"],
        "土": ["玄岳守心盾", "黄泉镇灵印", "地脉搬山锤"],
        "雷": ["惊雷伏魔剑", "雷纹破煞钺", "五劫荡魂铃"],
        "冰": ["雪魄凝魂环", "冰螭锁灵链", "寒月照骨针"],
    },
    "玄阶": {
        "金": ["金霞破甲剑", "玄铁斩妖刀", "碎玉流光匕"],
        "木": ["青藤听雨伞", "百草蕴灵杖", "竹影追风弓"],
        "水": ["水云护身佩", "碧浪分潮叉", "寒泉聚灵盏"],
        "火": ["赤焰伏虎环", "火羽流星镖", "丹霞炼气炉"],
        "土": ["山纹镇邪印", "黄沙缚影袋", "岩心护命盾"],
        "雷": ["奔雷啸月枪", "雷枝引劫剑", "震魂小鼓"],
        "冰": ["冰纹照影剑", "寒晶护心镜", "霜花缚妖索"],
    },
    "黄阶": {
        "金": ["精钢护法剑", "铜纹降妖钵", "金线飞针"],
        "木": ["青木短杖", "灵藤小弓", "百草药锄"],
        "水": ["听雨小扇", "清泉葫芦", "水纹护符"],
        "火": ["火纹短刀", "赤砂小炉", "明灯镇邪盏"],
        "土": ["黄石护身牌", "土纹小盾", "沉砂镇纸"],
        "雷": ["雷纹桃木剑", "惊雷小铃", "电光符匕"],
        "冰": ["寒玉短剑", "霜线银针", "冰纹小镜"],
    },
    "凡品": {
        "金": ["外门制式长剑", "生锈铁尺", "粗钢短矛"],
        "木": ["桃木练功剑", "竹节拐杖", "旧药锄"],
        "水": ["粗瓷水瓶", "旧雨伞", "溪石护坠"],
        "火": ["火折短杖", "厨房铁炉", "焦木令牌"],
        "土": ["陶土护符", "磨损石盾", "山民猎叉"],
        "雷": ["响铜小铃", "劈裂桃枝", "旧雷符夹"],
        "冰": ["寒泉石片", "薄霜铜镜", "冷铁短针"],
    },
}

ARTIFACT_STANDARD_TIERS = ["凡品", "黄阶", "玄阶", "地阶", "天阶"]
ARTIFACT_IMMORTAL_TIER = "仙阶"
ARTIFACT_REALM_BOUND_TIERS = ARTIFACT_STANDARD_TIERS + [ARTIFACT_IMMORTAL_TIER]
ARTIFACT_FAKE_IMMORTAL_INDEX = REALMS.index("假仙境") if "假仙境" in REALMS else REALMS.index("真仙境")
ARTIFACT_REALM_STEMS = [
    "锻骨", "聚气", "筑基", "丹元", "元婴", "神照", "虚衡", "合真", "乘云", "渡厄",
    "半仙", "真仙", "金仙", "太乙", "大罗", "混元", "准圣", "圣人", "混罗", "无极",
    "天道", "大道", "道祖", "半脱", "超脱", "永恒",
]
ARTIFACT_TIER_STEMS = {"凡品": "素纹", "黄阶": "明纹", "玄阶": "玄纹", "地阶": "岳纹", "天阶": "天纹", "仙阶": "仙纹"}
ARTIFACT_GRADE_STEMS = {"下品": "初成", "中品": "凝华", "上品": "上清", "极品": "极曜"}
ARTIFACT_ATTRIBUTE_STEMS = {
    "金": "金衡",
    "木": "青榆",
    "水": "沧澜",
    "火": "赤曜",
    "土": "坤岳",
    "雷": "霆渊",
    "冰": "霜镜",
    "风": "扶摇",
    "光": "明昼",
    "暗": "幽冥",
    "先天道体": "道衡",
    "混沌": "混元",
}
ARTIFACT_SHAPES_BY_ATTRIBUTE = {
    "金": ["剑", "戈", "刀", "环"],
    "木": ["杖", "弓", "尺", "铃"],
    "水": ["珠", "瓶", "扇", "印"],
    "火": ["旗", "炉", "戟", "钟"],
    "土": ["盾", "玺", "鼎", "甲"],
    "雷": ["锤", "鼓", "枪", "钺"],
    "冰": ["镜", "轮", "针", "链"],
    "风": ["扇", "羽", "铃", "翼"],
    "光": ["镜", "轮", "灯", "冠"],
    "暗": ["刃", "灯", "幡", "匣"],
    "先天道体": ["印", "箓", "盘", "简"],
    "混沌": ["珠", "鼎", "钟", "胚"],
}

ARTIFACT_STORY_PLACES = {
    "金": ["陨铁谷", "西岭剑冢", "白帝旧炉", "天河沉金滩"],
    "木": ["青梧灵圃", "万藤古井", "药王山后崖", "春雷林"],
    "水": ["沧澜寒潭", "归墟潮眼", "月照泉", "天河渡口"],
    "火": ["赤霞火窟", "离焰炉心", "落日熔原", "朱雀旧坛"],
    "土": ["坤岳地宫", "玄黄石室", "息壤台", "古矿龙脉"],
    "雷": ["惊雷崖", "劫云台", "霆渊断岭", "九霄雷池"],
    "冰": ["霜镜雪原", "玄冰洞天", "寒月冰窟", "北冥裂谷"],
    "风": ["扶摇天台", "青岚古道", "风雷峡", "九霄云栈"],
    "光": ["明昼天池", "日轮旧坛", "琉璃净土", "破晓山门"],
    "暗": ["幽影古井", "无灯地宫", "月蚀荒原", "玄冥暗河"],
    "先天道体": ["问道台", "万法玄坛", "道源石室", "天机旧阁"],
    "混沌": ["混沌海眼", "太虚裂隙", "鸿蒙遗炉", "无极玄渊"],
}

ARTIFACT_STORY_OMENS = [
    "一场断续七日的灵雨",
    "夜半忽明忽灭的星痕",
    "秘境裂口传来的低鸣",
    "旧战场上未散的器魂回声",
    "无名碑文泛起的微光",
]

ARTIFACT_STORY_KEEPERS = ["守炉弟子", "游方炼器师", "失名散修", "宗门客卿", "秘境遗民"]

ARTIFACT_STORY_ENDINGS = [
    "玉册旁只留八字：先问本心，再出锋芒。",
    "传承至今，器纹仍会在夜里微亮。",
    "灵根不合者持之，只听得一声轻叹。",
    "旧主誓言未散，藏在最深一道纹里。",
]

ARTIFACT_SHAPE_DEEDS = {
    "剑": "剑脊映出一线星河，曾替旧主斩开失控炉火",
    "戈": "戈刃敲地便有战鼓回声，能镇住乱窜的庚金煞气",
    "刀": "刀光贴着炉壁游走，像一尾不肯熄灭的白焰",
    "环": "环影绕腕三匝，能把散乱灵机重新扣成一线",
    "杖": "杖端生出新芽，枯木旁的灵田因此复青",
    "弓": "弓弦无箭自鸣，曾把夜雾中的妖影逼退三里",
    "尺": "尺面浮起细密年轮，能量出草木生息的轻重",
    "铃": "铃声清而不躁，能唤回被瘴气迷住的心神",
    "珠": "珠中潮声不绝，曾在旱谷里凝出一汪救命清泉",
    "瓶": "瓶口吞吐月华，可把躁动灵息慢慢沉入丹田",
    "扇": "扇骨开合如潮，能把飞来的火星化作湿润雾气",
    "印": "印面落下时水纹四散，像替天地盖上一枚清凉法记",
    "旗": "旗角卷起赤霞，曾为一座将熄的丹炉续住真火",
    "炉": "炉腹有细小火潮，常在无人时自守三分余温",
    "戟": "戟尖挑起红芒，能把袭来的阴寒气息劈成碎烟",
    "钟": "钟声沉入骨髓，可让走火入魔者听见自己的呼吸",
    "盾": "盾面浮出山纹，曾挡住塌落矿道里的第一块巨石",
    "玺": "玺底压着玄黄印痕，能让浮躁法力重新归位",
    "鼎": "鼎足入地三寸，周围灵砂都会安静伏下",
    "甲": "甲片互扣如鳞，替旧主在乱石雨中留下一线生机",
    "锤": "锤头滚过雷光，敲一下便震散一团阴云",
    "鼓": "鼓皮藏着远雷，曾在秘境深处替众人辨出归路",
    "枪": "枪缨带电，刺出时会留下短促的青白残影",
    "钺": "钺刃沉重无声，却能劈开缠身的劫气锁链",
    "镜": "镜面映雪无尘，能照见心湖里最细的裂纹",
    "轮": "轮缘旋起寒芒，曾把毒雾冻成坠地冰沙",
    "针": "针芒细若飞霜，能在一息间封住暴走经脉",
    "链": "链节轻响如雪落，可把狂乱妖魂慢慢拖回沉寂",
    "羽": "羽纹轻颤便有长风绕臂，曾托旧主掠过塌陷云栈",
    "翼": "翼骨张开时风声成阵，可把追兵隔在三重云外",
    "刃": "刃口不映灯火，却能割开潜伏在影中的恶念",
    "灯": "灯芯一点不灭，照出迷魂夜路里真正的门径",
    "幡": "幡面无风自展，曾把满室阴影收作一缕暗纹",
    "匣": "匣盖开合无声，可封住不愿散去的旧日器魂",
    "冠": "冠纹浮起清辉，曾替旧主挡下一次心魔反噬",
    "箓": "箓文自行游走，能把散落道韵重新编成章句",
    "盘": "盘面星点轮转，曾为迷失者指出一线归真之路",
    "简": "简上字迹时隐时现，读到最后只余一声道钟",
    "胚": "胚胎般的器纹缓缓舒展，仿佛天地初分前的一次呼吸",
}


def artifact_story_pick(options: list[str], key: str, salt: str) -> str:
    if not options:
        return ""
    digest = hashlib.sha256(f"{key}:{salt}".encode("utf-8")).hexdigest()
    return options[int(digest[:8], 16) % len(options)]


def artifact_realm_story(name: str, realm_label: str, tier: str, grade: str, attribute: str, shape: str) -> str:
    key = f"{name}|{realm_label}|{tier}|{grade}|{attribute}|{shape}"
    place = artifact_story_pick(ARTIFACT_STORY_PLACES.get(attribute, ["无名器阁"]), key, "place")
    omen = artifact_story_pick(ARTIFACT_STORY_OMENS, key, "omen")
    keeper = artifact_story_pick(ARTIFACT_STORY_KEEPERS, key, "keeper")
    ending = artifact_story_pick(ARTIFACT_STORY_ENDINGS, key, "ending")
    deed = ARTIFACT_SHAPE_DEEDS.get(shape, "器纹初醒时照亮整座石室")
    attribute_label = root_attribute_label(attribute)
    return (
        f"{name}出自{place}。相传{realm_label}{keeper}在{omen}里拾得{attribute_label}系灵胚，"
        f"以{tier}{grade}火候温养九夜。器成时{deed}，只待{attribute_label}灵根者以心血唤醒。{ending}"
    )


def artifact_shape_from_name(name: str) -> str:
    text = str(name or "")
    for shape in sorted(ARTIFACT_SHAPE_DEEDS, key=len, reverse=True):
        if shape in text:
            return str(shape)
    return "器"


def crafted_artifact_story(name: str, recipe: dict[str, Any]) -> str:
    tier = str(recipe.get("tier") or "凡品")
    grade = str(recipe.get("grade") or "下品")
    materials = [str(item) for item in recipe.get("materials", []) if str(item).strip()]
    material_text = (
        (materials[0] + "等材料") if len(materials) > 1 else (materials[0] if materials else "几件失名旧料")
    )
    try:
        realm_label = REALMS[max(0, min(len(REALMS) - 1, int(recipe.get("required_realm", 0))))]
    except (TypeError, ValueError):
        realm_label = "无名境界"
    key = f"crafted:{name}|{tier}|{grade}|{material_text}|{realm_label}"
    omen = artifact_story_pick(ARTIFACT_STORY_OMENS, key, "crafted-omen")
    keeper = artifact_story_pick(ARTIFACT_STORY_KEEPERS, key, "crafted-keeper")
    ending = artifact_story_pick(ARTIFACT_STORY_ENDINGS, key, "crafted-ending")
    deed = ARTIFACT_SHAPE_DEEDS.get(artifact_shape_from_name(name), "器纹初醒时照亮整座石室")
    return (
        f"{name}由{material_text}炼成。{realm_label}{keeper}在{omen}之夜重开炉火，"
        f"以{tier}{grade}法度校正器纹。成形时{deed}，自此认心不认主。{ending}"
    )


def artifact_realm_tiers_for_index(realm_index: int) -> list[str]:
    tiers = list(ARTIFACT_STANDARD_TIERS)
    if int(realm_index) >= ARTIFACT_FAKE_IMMORTAL_INDEX:
        tiers.append(ARTIFACT_IMMORTAL_TIER)
    return tiers


def _artifact_realm_stem(realm_index: int) -> str:
    if 0 <= realm_index < len(ARTIFACT_REALM_STEMS):
        return ARTIFACT_REALM_STEMS[realm_index]
    text = REALMS[max(0, min(len(REALMS) - 1, realm_index))]
    return text[:-1] if text.endswith(("期", "境")) else text


def build_realm_artifact_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for realm_index, realm_name in enumerate(REALMS):
        realm_stem = _artifact_realm_stem(realm_index)
        realm_label = realm_name[:-1] if realm_name.endswith(("期", "境")) else realm_name
        for tier in artifact_realm_tiers_for_index(realm_index):
            for grade in GRADE_ORDER:
                grade_index = GRADE_ORDER.index(grade)
                for attribute in ARTIFACT_ATTRIBUTES:
                    shape_pool = ARTIFACT_SHAPES_BY_ATTRIBUTE.get(attribute, ["器"])
                    shape = shape_pool[(realm_index + TIER_ORDER.index(tier) + grade_index) % len(shape_pool)]
                    name = f"{realm_stem}{ARTIFACT_TIER_STEMS[tier]}{ARTIFACT_ATTRIBUTE_STEMS[attribute]}{ARTIFACT_GRADE_STEMS[grade]}{shape}"
                    story = artifact_realm_story(name, realm_label, tier, grade, attribute, shape)
                    catalog.append(
                        {
                            "name": name,
                            "realm_index": realm_index,
                            "realm": realm_name,
                            "realm_label": realm_label,
                            "tier": tier,
                            "grade": grade,
                            "attribute": attribute,
                            "category": "灵器",
                            "description": story,
                            "source": "垂钓、每日商店、秘境对应境界掉落、后台配置投放",
                            "artifact_family": "realm_bound",
                        }
                    )
    return catalog


ARTIFACT_REALM_CATALOG = build_realm_artifact_catalog()
ARTIFACT_REALM_INFOS_BY_NAME = {str(item["name"]): item for item in ARTIFACT_REALM_CATALOG}
ARTIFACT_REALM_NAMES_BY_TIER: dict[str, list[str]] = {}
for _artifact_info in ARTIFACT_REALM_CATALOG:
    ARTIFACT_REALM_NAMES_BY_TIER.setdefault(str(_artifact_info["tier"]), []).append(str(_artifact_info["name"]))


def artifact_catalog_entries(
    realm_index: int,
    tier: Optional[str] = None,
    grade: Optional[str] = None,
    attribute: Optional[str] = None,
) -> list[dict[str, Any]]:
    realm = max(0, min(len(REALMS) - 1, int(realm_index)))
    return [
        item
        for item in ARTIFACT_REALM_CATALOG
        if int(item.get("realm_index", -1)) == realm
        and (tier is None or str(item.get("tier")) == str(tier))
        and (grade is None or str(item.get("grade")) == str(grade))
        and (attribute is None or str(item.get("attribute")) == str(attribute))
    ]



def artifact_realm_catalog_summary_text() -> str:
    lines = ["【境界灵器目录】", "每个境界都有独立灵器池：凡品、黄阶、玄阶、地阶、天阶；假仙境界后额外包含下品至极品仙器。"]
    for realm_index, realm_name in enumerate(REALMS):
        tiers = artifact_tiers_for_realm(realm_index)
        pieces: list[str] = []
        for tier in tiers:
            names = [item["name"] for item in artifact_catalog_entries(realm_index, tier, "极品")[:3]]
            label = "仙器" if tier == "仙阶" else f"{tier}灵器"
            pieces.append(f"{label}例：" + "、".join(str(name) for name in names))
        lines.append(f"{realm_name}：" + "；".join(pieces))
    lines.append("后台可配置每个境界开放的阶级、普通灵器境界战力基数、阶级倍率、品质倍率和仙器出现率。")
    return "\n".join(lines)
def artifact_info_to_reward(info: dict[str, Any]) -> dict[str, Any]:
    realm_index = int(info.get("realm_index", 0))
    return {
        "tier": str(info.get("tier", "凡品")),
        "grade": str(info.get("grade", "下品")),
        "category": ARTIFACT_CATEGORY,
        "name": str(info.get("name", "无名灵器")),
        "description": str(info.get("description", "")),
        "source": str(info.get("source", "")),
        "realm_index": realm_index,
        "min_realm_index": realm_index,
        "required_attribute": str(info.get("attribute", "")),
        "artifact_family": str(info.get("artifact_family", "realm_bound")),
    }
EXTRA_METHOD_NAMES_BY_TIER_ATTR = {
    "天阶": {
        "金": ["不灭金身经", "斩道剑胎篇", "庚金开天录"],
        "木": ["青华造化经", "万灵长生篇", "巨木通天录"],
        "水": ["沧溟归墟经", "天河炼神篇", "玄水不灭诀"],
        "火": ["赤阳真火录", "赤羽焚天经", "离火炼界篇"],
        "土": ["玄黄不动经", "息壤造山诀", "后土载道书"],
        "雷": ["九劫雷身经", "玄雷御劫篇", "万雷洗神诀"],
        "冰": ["玄阴封神录", "玄冰寂灭经", "寒狱炼魂篇"],
    },
    "地阶": {
        "金": ["白锋庚金诀", "金阙炼剑章", "裂空剑元录"],
        "木": ["青木回元经", "万藤化龙诀", "灵植蕴神篇"],
        "水": ["碧海潮汐经", "水月炼心诀", "沧浪化形篇"],
        "火": ["赤阳焚脉诀", "地火炼丹篇", "火鸦吞霞功"],
        "土": ["玄岳镇身功", "地脉养元诀", "黄泉守魄篇"],
        "雷": ["五雷炼形诀", "惊雷破妄经", "劫云观想篇"],
        "冰": ["寒魄凝神经", "冰螭化息诀", "雪域炼心篇"],
    },
    "玄阶": {
        "金": ["金霞剑气诀", "玄铁炼骨篇", "碎玉锻锋法"],
        "木": ["青藤纳气诀", "百草生息功", "竹影御风篇"],
        "水": ["水云吐纳术", "寒潭静心诀", "碧浪行气篇"],
        "火": ["赤焰炼体诀", "丹霞养火功", "火羽轻身术"],
        "土": ["山纹固元法", "黄庭养土诀", "岩心守一篇"],
        "雷": ["奔雷锻骨诀", "雷竹引气术", "震魂炼息篇"],
        "冰": ["冰纹凝息诀", "霜华养魄功", "寒泉静坐篇"],
    },
    "黄阶": {
        "金": ["锐金入门篇", "铁剑吐纳法", "金线行气诀"],
        "木": ["草木回息法", "青苗养气篇", "木灵静坐诀"],
        "水": ["听雨纳息法", "溪泉养元诀", "水脉入门篇"],
        "火": ["灶火暖脉诀", "赤砂锻体篇", "明灯守神法"],
        "土": ["黄土培元诀", "山石站桩法", "土息入门篇"],
        "雷": ["听雷养气诀", "雷符入门篇", "电光淬息法"],
        "冰": ["寒泉吐纳诀", "霜息入门篇", "冷月静心法"],
    },
    "凡品": {
        "金": ["外门剑架图", "旧铁剑心得", "残缺金息诀"],
        "木": ["药童草木记", "外门栽植录", "木桩站息法"],
        "水": ["溪畔静坐札", "挑水养气法", "残页水息诀"],
        "火": ["炉边暖身法", "灶火吐纳记", "焦页火息篇"],
        "土": ["外门扎马步", "石屋静坐篇", "粗浅土息法"],
        "雷": ["雨夜听雷记", "裂竹观想图", "残页雷息诀"],
        "冰": ["冷泉守心法", "寒夜入静篇", "薄冰观想记"],
    },
}
def _equipment_names_for_tier(
    base_map: dict[str, dict[str, str]],
    extra_map: dict[str, dict[str, list[str]]],
    tier: str,
) -> list[str]:
    names: list[str] = []
    for attr in ATTRIBUTES:
        names.append(base_map[tier][attr])
        names.extend(extra_map.get(tier, {}).get(attr, []))
    return names


FISHING_REWARD_NAMES["灵器"] = {
    tier: list(ARTIFACT_REALM_NAMES_BY_TIER.get(tier, []))[:28]
    for tier in REWARD_TIERS
}
FISHING_REWARD_NAMES["功法"] = {
    tier: _equipment_names_for_tier(METHOD_NAMES_BY_TIER_ATTR, EXTRA_METHOD_NAMES_BY_TIER_ATTR, tier)
    for tier in METHOD_NAMES_BY_TIER_ATTR
}
FISHING_REWARD_NAMES["丹药"] = {
    "天阶": ["筑基丹", "大还丹", "元婴丹", "九转凝神丹", "太清渡厄丹", "造化金丹", "九窍化婴丹", "斩尘化神丹", "合道紫金丹", "渡劫护命丹", "不朽金丹", "混元圣胎"],
    "地阶": ["筑基丹", "大还丹", "元婴丹", "玉髓化元丹", "紫府养魂丹", "凝魄金丹", "护婴丹", "化神引", "破虚丹", "合体丹", "地脉筑基液", "天道筑基露"],
    "玄阶": ["筑基丹", "小还丹", "元婴丹", "培元丹", "洗髓小还丹", "金液丹", "护脉丹", "凝神丹", "破障丹", "问心丹"],
    "黄阶": ["筑基丹", "小还丹", "聚气丸", "回春散", "凝气散", "固元丹", "清心丹", "护脉散", "淬体丹", "醒神丸"],
    "凡品": ["筑基丹", "小还丹", "辟谷小丸", "苦口补气散", "粗炼补元丸", "草还丹", "土炉凝气丸", "散修护脉丸", "粗炼醒神散", "凡火淬体散"],
}
FISHING_REWARD_NAMES["奇物"] = {
    '天阶': ['化凡意境', '破虚灵引', '合道残章', '大乘道果', '大罗天契', '混元道果', '元初紫气', '混元真印', '无极道种', '天道权柄', '万道本源', '永恒真名', '太乙道胎', '大罗道种', '混元真液', '无极真符', '合道天心', '万道源流', '开天道印', '彼岸真符', '不朽唯一印'],
    '地阶': ['化凡意境', '破虚灵引', '渡劫令', '仙门符诏', '金性道果', '斩尸灵宝', '道源符诏', '超脱契机', '命河断契', '虚空灵髓', '法身合契符', '圆融道胎', '避劫雷木', '真仙接引符', '金仙法契', '清光道箓', '诸天印契', '万道归元符', '准圣道契', '天道圣契', '无量道章', '道源玄胎', '天命玉册', '万道真箓', '祖庭符诏', '彼岸舟影', '命河钥印', '因果斩线', '万劫真铭'],
    '玄阶': ['化凡意境', '合道残章', '太乙玄光', '星砂沙漏', '低语玉佩', '仙元道砂', '执念斩魂刃', '功德金莲'],
    '黄阶': ['化凡意境', '不熄小灯', '自热茶盏', '破境石', '醒神玉'],
    '凡品': ['化凡意境', '只响一次的铃铛', '没字的竹简', '旧木令', '无名石片'],
}
FISHING_REWARD_NAMES["灵材"] = {
    "天阶": ["浑元星砂", "白曜仙金", "天髓玉露", "九转玄参", "悟道茶心", "赤阳真火液", "玄阴寒髓", "坤元母气", "万道莲实", "劫雷神木"],
    "地阶": ["星陨玄铁", "玄冰玉髓", "紫府灵芝", "月华凝露", "地脉火芝", "龙血朱果", "天青灵藤", "地肺火液", "金髓玉砂", "养魂莲心"],
    "玄阶": ["赤霞铜精", "青藤灵骨", "金纹灵芝", "冰魄花蕊", "雷击灵木", "黑曜灵砂", "百年寒髓", "赤鳞妖血", "碧玉参须", "云母灵液"],
    "黄阶": ["百炼寒铁", "紫纹灵木", "凝露草", "火枣核", "土精砂", "血线草", "青灵花", "黄芽芝", "月露珠", "火鸦羽灰"],
    "凡品": ["发亮矿渣", "溪边圆石", "清心草叶", "灵麦芽", "苦参须", "山参碎须", "晨露草", "凡火炉灰", "青苔灵屑", "野兽精血"],
}



for _tier, _names in {
    "天阶": ["古妖王丹", "云殿铜锈", "道源矿髓", "魂界灵晶", "远古兽骨"],
    "地阶": ["金丹妖丹", "元婴妖丹", "蛟龙脊骨", "荒脉源石", "古铜云纹"],
    "玄阶": ["筑基妖丹", "妖兽精血", "残破兽骨", "魂界灵砂", "古矿石胆"],
    "黄阶": ["练气妖丹", "妖兽利爪", "矿脉源砂", "旧宗木简", "兽巢骨粉"],
    "凡品": ["残碎妖丹", "幼兽乳牙", "灰矿砂", "断裂兽爪", "残破碑屑"],
}.items():
    _pool = FISHING_REWARD_NAMES["灵材"].setdefault(_tier, [])
    for _name in _names:
        if _name not in _pool:
            _pool.append(_name)

FISHING_REWARD_NAMES["神通"] = {
    "天阶": ["星律残页", "归极印纹", "万象战影", "命络断线真箓", "云章九歌玉简", "叩穹一式符令", "元婴天兆星痕", "重阈战札"],
    "地阶": ["星律残页", "重阈战札", "归极印纹", "灵骨天纹", "身界蕴种道痕", "环域灵轮碎光", "血战真源血符", "梦潮回环沙"],
    "玄阶": ["初阈战札", "重阈战札", "星律残页", "沧元道章残页", "战演真法残卷", "风掣疾行风痕", "沉岳指印骨纹", "内府开阖残图"],
    "黄阶": ["初阈战札", "翠盏灵影拓片", "青华法相旧纹", "青枝护相枝影", "澄元剑芒手札", "流年意境残砂", "星律残页", "问玄旧简"],
    "凡品": ["初阈战札", "初阈战意札", "问玄旧简", "小内府残图", "澄元剑芒残页", "翠盏灵影碎片", "星律残页", "重阈战札"]
}

IMMORTAL_SEED_CATEGORY = '仙源'
LEGACY_IMMORTAL_SEED_CATEGORY = '仙种'
HIGH_RISK_MYSTIC_REALM_TYPES = (
    '远荒限界',
    '沉寂黑山',
    '星初矿渊',
    '神陨废墟',
    '仙眠幽谷',
    '轮回潮眼',
    '葬天岛',
    '穹衡古殿',
    '五行之地',
    '域外战场',
    '幽泉魔宗',
    '荒尘墟',
    '星运孤界',
    '天关古战场',
    '七宿星空古路',
    '古铜云阙深层',
    '雷池古域',
    '玄界石门',
    '星陨残原',
    '青玄门影',
)
NO_TIANJI_MYSTIC_TYPES = set(HIGH_RISK_MYSTIC_REALM_TYPES)
EMPEROR_ARTIFACT_INFOS = {
    '青华生灭印': {
        "creator": '青衡',
        "material": '青华生机残晶',
        "skill": '青华镇世',
        "story": '青衡以本体青华躯体炼成仙帝兵，帝威中仍藏生灭道意。',
    },
    '空衡明镜': {
        "creator": '空衡道主',
        "material": '空痕仙金',
        "skill": '镜照虚空',
        "story": '空衡道主一生征战险域，镜光所至空间如纸。',
    },
    '恒焰天炉': {
        "creator": '恒焰炉主',
        "material": '赤羽曜金',
        "skill": '恒焰炉火',
        "story": '赤羽曜金铸炉，炉火中藏帝者的炽烈气魄。',
    },
    '坤元源鼎': {
        "creator": '玄源天尊',
        "material": '坤源根',
        "skill": '万物归鼎',
        "story": '坤源根铸鼎，随玄源天尊征战诸天。',
    },
    '尘镜隐面': {
        "creator": '断尘仙主',
        "material": '仙金精粹',
        "skill": '尘镜无声',
        "story": '尘镜隐面承载断尘仙主孤绝执念，遮尘缘而照万古。',
    },
    '晦星封藏瓮': {
        "creator": '断尘仙主',
        "material": '晦曜古陶',
        "skill": '晦星归藏',
        "story": '晦星封藏瓮以晦曜古陶炼成，罐开则天地失色。',
    },
    '玄龙纹金鼎': {
        "creator": '玄龙铸宗历代先贤',
        "material": '玄龙纹金',
        "skill": '玄龙镇岳',
        "story": '玄龙纹金本为无上奇珍，鼎身龙纹如沉睡真龙。',
    },
    '古铜云阙': {
        "creator": '断尘仙主相关传承',
        "material": '古铜仙金与云殿残纹',
        "skill": '云阙镇狱',
        "story": '古铜云阙门后有仙机也有死局，帝者气息经年不散。',
    },
    '断尘仙剑': {
        "creator": '断尘仙主',
        "material": '仙金剑胎',
        "skill": '斩尽凡尘',
        "story": '一口仙剑随断尘仙主破尽诸敌，剑光冷而纯粹。',
    },
}
EMPEROR_ARTIFACT_NAMES = tuple(EMPEROR_ARTIFACT_INFOS.keys())
UNIQUE_REWARD_NAMES = set(EMPEROR_ARTIFACT_NAMES) | {'玄蓝冰焰', '穹衡古鼎', '人道镇印', '五行灵根', '内景星源仙源'}
UNIQUE_REWARD_INFOS = {
    '玄蓝冰焰': {
        "category": '奇物',
        "story": '穹衡古殿深处流传的寒焰，冷而不灭，可护神魂，也可作为高阶炼丹与炼器火种。',
        "source": '高危险地、穹衡古殿、上古大能洞府等秘境极低概率产出；唯一真火被取走后后续只会出现残焰或仿品。',
        "materials": '无固定制作素材，可作为炼丹/炼器高阶火种。',
    },
    '穹衡古鼎': {
        "category": '奇物',
        "story": '穹衡古殿镇殿古鼎，鼎影一现便牵动空间道韵，常被修士视作大机缘与大杀局并存之物。',
        "source": '穹衡古殿、高危险地秘境极低概率产出；本体全局唯一。',
        "materials": '不可常规制作，只能通过秘境机缘获得。',
    },
    '人道镇印': {
        "category": '奇物',
        "story": '人道气运凝成的古印，能镇压邪气与乱法，持有者更易在高危秘境中稳住心神。',
        "source": '高危险地、域外战场、人族古地秘境极低概率产出；本体全局唯一。',
        "materials": '不可常规制作，只能通过秘境机缘获得。',
    },
    '五行灵根': {
        "category": '奇物',
        "story": '五行之地孕育的后天道基奇物，可辅助化神之后参悟五行合一。',
        "source": '五行之地等高危险秘境极低概率产出；本体全局唯一。',
        "materials": '不可常规制作，可与丹灵根/器灵根体系互为补全线索。',
    },
}
CATALOG_EXTRA_ITEM_INFOS = {
    '妖丹': {
        "category": '灵材',
        "story": '妖兽内丹，是丹灵根、炼丹和部分秘境任务的重要材料。实际掉落时会带有属性与妖兽修为，例如“火系金丹妖丹”。',
        "source": '兽潮、秘境首领挑战、妖兽相关事件；首领挑战成功必定额外获得对应首领妖丹。',
        "materials": '不可常规制作，由妖兽体内凝成。',
    },
    '兽骨': {
        "category": '灵材',
        "story": '妖兽遗骨，可炼器、布阵，也可作为部分傀儡和符箓的承载材料。实际掉落时可能带首领名称。',
        "source": '兽潮、兽巢、秘境首领挑战和妖兽残骸事件。',
        "materials": '不可常规制作，可由妖兽掉落。',
    },
    '万象归元经': {
        "category": '功法',
        "story": '古铜云阙壁画中显化的古经，讲万象归一、法力返本，适合高阶修士参悟。',
        "source": '古铜云阙、上古宗门遗址、秘境功法事件；也可能通过万宝楼流通。',
        "materials": '功法不可制作，可通过秘境传承获得。',
    },
    '星墟观想篇': {
        "category": '功法',
        "story": '魂界残域石碑中拓出的观想法，偏神魂修炼，可辅助秘境感知与斗法先觉。',
        "source": '魂界残域、神魂类秘境事件；也可能通过万宝楼流通。',
        "materials": '功法不可制作，可通过秘境传承获得。',
    },
    '镜湖碎光': {
        "category": '奇物',
        "story": '断裂仙池中映出的镜光碎片，带有照见虚妄的气息，可作为高阶奇物收藏或秘境线索。',
        "source": '古铜云阙、仙池残液、镜湖类秘境事件。',
        "materials": '不可常规制作，只能通过秘境机缘获得。',
    },
}
IMMORTAL_SEED_NAME_ALIASES = {
    '身界蕴种仙种': '内景星源仙源',
    '青枝回春仙种': '翠脉回春仙源',
    '风掣疾行仙种': '迅岚流影仙源',
    '环域仙种': '守环玄域仙源',
    '梦潮回环仙种': '澄梦回澜仙源',
}
IMMORTAL_SEED_INFOS = {
    '内景星源仙源': {"limit": '真仙境', "effect": '在灵台内凝成一枚星脉源点，提升仙元转化与多系神通调息。'},
    '翠脉回春仙源': {"limit": '真仙境', "effect": '以青碧生机滋养经络，增强恢复、木系术法与秘境续航。'},
    '迅岚流影仙源': {"limit": '真仙境', "effect": '把风息压成流影脉冲，提升先手、身法与追击稳定性。'},
    '守环玄域仙源': {"limit": '真仙境', "effect": '展开护身环域，提升防御并强化连续神通的承接。'},
    '澄梦回澜仙源': {"limit": '真仙境', "effect": '以澄梦水光洗炼神魂，增强感知、破幻与危机预兆。'},
}
IMMORTAL_SEED_NAMES = tuple(IMMORTAL_SEED_INFOS.keys())
ARTIFACT_REFINING_RECIPES = {
    '翠雷云竹剑': {"tier": '玄阶', "grade": '上品', "materials": ['碧玉灵竹', '雷击灵木', '百炼寒铁'], "cost": 260, "required_realm": 2},
    '玄金雷枝剑': {"tier": '地阶', "grade": '极品', "materials": ['翠雷云竹剑', '庚金', '雷击灵木'], "cost": 900, "required_realm": 3},
    '玄金列星剑阵': {"tier": '天阶', "grade": '极品', "materials": ['玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑', '玄金雷枝剑'], "cost": 7200, "required_realm": 5, "category": '阵盘'},
    '空衡明镜仿制品': {"tier": '仙阶', "grade": '中品', "materials": ['空痕仙金', '浑元星砂', '星墟锁界盘'], "cost": 18000, "required_realm": 10},
    '坤元源鼎仿制品': {"tier": '仙阶', "grade": '上品', "materials": ['坤元母气', '坤元母气', '厚土载天鼎'], "cost": 26000, "required_realm": 11},
}
EXTRA_ARTIFACT_REFINING_RECIPES = {
    '矿渣淬火锭': {"tier": '凡品', "grade": '中品', "materials": ['发亮矿渣', '灰矿砂', '凡火炉灰'], "cost": 24, "required_realm": 0},
    '青藤骨盾': {"tier": '玄阶', "grade": '下品', "materials": ['青藤灵骨', '残破兽骨', '百炼寒铁'], "cost": 180, "required_realm": 1},
    '火砂护心镜': {"tier": '黄阶', "grade": '极品', "materials": ['土精砂', '火鸦羽灰', '百炼寒铁'], "cost": 96, "required_realm": 0},
    '赤霞铜炉': {"tier": '玄阶', "grade": '上品', "materials": ['赤霞铜精', '凡火炉灰', '地肺火液'], "cost": 360, "required_realm": 2},
    '魂界照魂镜': {"tier": '地阶', "grade": '下品', "materials": ['魂界灵砂', '魂界灵晶', '古矿石胆'], "cost": 760, "required_realm": 3},
    '兽骨战傀': {"tier": '地阶', "grade": '中品', "materials": ['远古兽骨', '妖兽利爪', '断裂兽爪'], "cost": 820, "required_realm": 3, "category": '傀儡'},
    '蛟脊破军枪': {"tier": '地阶', "grade": '极品', "materials": ['蛟龙脊骨', '金丹妖丹', '星陨玄铁'], "cost": 1180, "required_realm": 4},
    '辟邪雷竹剑': {"tier": '地阶', "grade": '极品', "materials": ['金纹雷枝', '破邪雷叶', '金纹雷枝'], "cost": 1280, "required_realm": 4},
    '翠雷云竹剑': {"tier": '玄阶', "grade": '上品', "materials": ['翠雷云竹剑剑胚', '翠雷云竹剑图谱', '金纹雷枝'], "cost": 420, "required_realm": 2},
    '小玄金剑阵盘': {"tier": '玄阶', "grade": '极品', "materials": ['剑阵残图', '星衍灵沙', '金纹雷枝'], "cost": 560, "required_realm": 3, "category": '阵盘'},
    '白曜星金剑胎': {"tier": '天阶', "grade": '极品', "materials": ['白曜仙金', '星衍灵沙', '庚金'], "cost": 3600, "required_realm": 6},
    '古铜云纹盘': {"tier": '天阶', "grade": '上品', "materials": ['古铜云纹', '云殿铜锈', '道源矿髓'], "cost": 4200, "required_realm": 6, "category": '阵盘'},
    '赤羽曜金炉仿品': {"tier": '仙阶', "grade": '下品', "materials": ['赤羽曜金', '赤阳真火液', '地肺火液'], "cost": 12800, "required_realm": 10},
    '玄龙纹金鼎仿品': {"tier": '仙阶', "grade": '中品', "materials": ['玄龙纹金', '古铜云纹', '荒脉源石'], "cost": 16800, "required_realm": 11},
    '尘镜隐面仿品': {"tier": '仙阶', "grade": '中品', "materials": ['仙金精粹', '云殿铜锈', '魂界灵晶'], "cost": 18800, "required_realm": 11},
    '坤元源鼎仿制品': {"tier": '仙阶', "grade": '上品', "materials": ['坤源根', '坤元母气', '坤元母气'], "cost": 30000, "required_realm": 12},
}
ARTIFACT_REFINING_RECIPES.update(EXTRA_ARTIFACT_REFINING_RECIPES)

EXTRA_REFINING_MATERIALS = {
    '天阶': ['庚金', '空痕仙金', '赤羽曜金', '玄龙纹金', '仙金精粹', '坤元母气', '坤源根', '青华生机残晶'],
    '地阶': ['翠雷云竹剑剑胚', '金纹雷枝', '破邪雷叶', '星衍灵沙'],
    '玄阶': ['翠雷云竹剑图谱', '金纹雷枝', '剑阵残图'],
}
for _tier, _names in EXTRA_REFINING_MATERIALS.items():
    _pool = FISHING_REWARD_NAMES['灵材'].setdefault(_tier, [])
    for _name in _names:
        if _name not in _pool:
            _pool.append(_name)

# High-rank treasures enter through dangerous mystic realms and refining; base fishing validation stays stable.
ITEM_ATTRIBUTE_BY_NAME = {}
ITEM_ATTRIBUTE_BY_NAME.update({"\u9752\u7af9\u8702\u4e91\u5251": "\u96f7", "\u5e9a\u91d1\u9752\u7af9\u8702\u4e91\u5251": "\u96f7", "\u5927\u5e9a\u5251\u9635": "\u91d1"})
for _tier, _items in ARTIFACT_NAMES_BY_TIER_ATTR.items():
    for _attribute, _name in _items.items():
        ITEM_ATTRIBUTE_BY_NAME[_name] = _attribute
for _tier, _items in METHOD_NAMES_BY_TIER_ATTR.items():
    for _attribute, _name in _items.items():
        ITEM_ATTRIBUTE_BY_NAME[_name] = _attribute
for _tier, _items in EXTRA_ARTIFACT_NAMES_BY_TIER_ATTR.items():
    for _attribute, _names in _items.items():
        for _name in _names:
            ITEM_ATTRIBUTE_BY_NAME[_name] = _attribute
for _tier, _items in EXTRA_METHOD_NAMES_BY_TIER_ATTR.items():
    for _attribute, _names in _items.items():
        for _name in _names:
            ITEM_ATTRIBUTE_BY_NAME[_name] = _attribute

BREAKTHROUGH_REQUIREMENTS = {
    1: {"items": ['筑基丹', '地脉筑基液', '天道筑基露'], "target": '筑基期', "kind": 'foundation'},
    2: {"items": ['小还丹', '大还丹', '金液丹', '凝魄金丹', '造化金丹'], "target": '金丹期', "kind": 'pill'},
    3: {"items": ['元婴丹', '护婴丹', '九窍化婴丹'], "target": '元婴期', "kind": 'pill'},
    4: {"items": ['问心丹', '化神引', '斩尘化神丹', '化凡意境'], "target": '化神期', "kind": 'insight'},
    5: {"items": ['破虚灵引', '破虚丹', '虚空灵髓'], "target": '炼虚期', "kind": 'insight'},
    6: {"items": ['合道残章', '合体丹', '法身合契符'], "target": '合体期', "kind": 'insight'},
    7: {"items": ['合道紫金丹', '圆融道胎', '大乘道果'], "target": '大乘期', "kind": 'insight'},
    8: {"items": ['渡劫令', '渡劫护命丹', '避劫雷木'], "target": '渡劫期', "kind": 'insight'},
    9: {"items": ['仙元道砂', '仙门符诏', '真仙接引符'], "target": '真仙境', "kind": 'insight'},
    10: {"items": ['金性道果', '不朽金丹', '金仙法契'], "target": '金仙境', "kind": 'insight'},
    11: {"items": ['太乙玄光', '太乙道胎', '清光道箓'], "target": '太乙境', "kind": 'insight'},
    12: {"items": ['大罗天契', '大罗道种', '诸天印契'], "target": '大罗境', "kind": 'insight'},
    13: {"items": ['混元道果', '混元真液', '万道归元符'], "target": '混元金仙境', "kind": 'insight'},
    14: {"items": ['斩尸灵宝', '执念斩魂刃', '准圣道契'], "target": '准圣境', "kind": 'insight'},
    15: {"items": ['元初紫气', '天道圣契', '功德金莲'], "target": '圣人境', "kind": 'insight'},
    16: {"items": ['混元真印', '混元圣胎', '无量道章'], "target": '混元大罗金仙境', "kind": 'insight'},
    17: {"items": ['无极道种', '无极真符', '道源玄胎'], "target": '混元无极大罗金仙境', "kind": 'insight'},
    18: {"items": ['天道权柄', '合道天心', '天命玉册'], "target": '天道境', "kind": 'insight'},
    19: {"items": ['万道本源', '万道源流', '万道真箓'], "target": '大道境', "kind": 'insight'},
    20: {"items": ['道源符诏', '开天道印', '祖庭符诏'], "target": '道祖境', "kind": 'insight'},
    21: {"items": ['超脱契机', '彼岸舟影', '命河钥印'], "target": '半步超脱', "kind": 'insight'},
    22: {"items": ['命河断契', '因果斩线', '彼岸真符'], "target": '超脱境', "kind": 'insight'},
    23: {"items": ['永恒真名', '不朽唯一印', '万劫真铭'], "target": '永恒境', "kind": 'insight'},
    24: {"items": ['归真道契', '澄源真砂', '返本灵印'], "target": '归真境', "kind": 'insight'},
    25: {"items": ['太初元符', '一炁道胚', '初源真露'], "target": '太初境', "kind": 'insight'},
    26: {"items": ['鸿蒙紫箓', '未判元胎', '混茫道种'], "target": '鸿蒙境', "kind": 'insight'},
    27: {"items": ['玄黄母气', '厚土天章', '乾坤定印'], "target": '玄黄境', "kind": 'insight'},
    28: {"items": ['无量海印', '净界法螺', '万潮道珠'], "target": '无量境', "kind": 'insight'},
    29: {"items": ['造化灵炉', '万形生箓', '天工元胎'], "target": '造化境', "kind": 'insight'},
    30: {"items": ['太素清符', '无尘道衣', '素元灵魄'], "target": '太素境', "kind": 'insight'},
    31: {"items": ['太极衡印', '两仪真图', '阴阳归元符'], "target": '太极境', "kind": 'insight'},
    32: {"items": ['无始门钥', '归墟玄碑', '长明道烛'], "target": '无始境', "kind": 'insight'},
}


BREAKTHROUGH_TALISMAN_TOKENS = (
    "\u7b26",
    "\u7b26\u8bcf",
    "\u6cd5\u65e8",
    "\u7389\u518c",
    "\u771f\u7b93",
    "\u9053\u7ae0",
    "\u6cd5\u5951",
    "\u9053\u5951",
    "\u5723\u5951",
    "\u5370\u5951",
    "\u5929\u5951",
    "\u65ad\u5951",
    "\u771f\u7b26",
    "\u4ee4",
)

INSTANT_EXP_BASE = {"凡品": 26, "黄阶": 52, "玄阶": 96, "地阶": 168, "天阶": 280, "仙阶": 520, "仙帝兵": 1200}
CONSUMABLE_EXP_BASE = {"凡品": 18, "黄阶": 36, "玄阶": 72, "地阶": 128, "天阶": 220, "仙阶": 420, "仙帝兵": 960}
GRADE_EXP_RATIO = {"下品": 1.0, "中品": 1.18, "上品": 1.38, "极品": 1.72}
METHOD_SIGN_RATE = {"凡品": 0.08, "黄阶": 0.12, "玄阶": 0.18, "地阶": 0.26, "天阶": 0.38, "仙阶": 0.56, "仙帝兵": 0.88}
METHOD_CHAT_BASE = {"凡品": 0.35, "黄阶": 0.55, "玄阶": 0.85, "地阶": 1.25, "天阶": 1.8, "仙阶": 2.8, "仙帝兵": 5.2}
METHOD_KIND_NAMES = ("修炼类", "锻体类", "神魂类", "战技类")
COMBAT_RACES = (
    ("人族-东荒", 18),
    ("人族-南域", 16),
    ("人族-西域", 12),
    ("人族-北域", 12),
    ("人族-中州", 14),
    ("妖族-金羽雷鹏", 4),
    ("妖族-青华灵裔", 4),
    ("妖族-九尾天狐", 4),
    ("妖族-远荒魔猿", 3),
    ("神族", 4),
    ("仙族", 3),
)
COMBAT_PHYSIQUES = (
    ("凡体", 30),
    ("石心废脉", 12),
    ("远荒战体", 7),
    ("先天道胚", 7),
    ("玄阴灵体", 6),
    ("赤阳灵体", 6),
    ("青华道体", 6),
    ("金羽神脉", 5),
    ("身界蕴种", 4),
    ("浑元战魔体", 3),
)
SPECIAL_ABILITY_POOL = (
    "初阈",
    "重阈",
    "归极域",
    "星律-定魂篇",
    "星律-御器篇",
    "星律-斗衡篇",
    "星律-回生篇",
    "星律-贯元篇",
    "星律-观势篇",
    "星律-布阵篇",
    "星律-先觉篇",
    "星律-流影篇",
    "翠盏灵影",
    "澄元剑芒",
    "元婴天兆",
    "沧元道章",
    "战演真法",
    "玄金血脉",
    "青华法相",
    "灵骨天纹",
    "身界蕴种",
    "万象战影",
    "环域灵轮",
    "风掣疾行",
    "青枝护相",
    "沉岳指印",
    "流年意境",
    "血战真源",
    "梦潮回环",
    "命络断线",
    "云章九歌",
    "叩穹一式",
    "内府开阖",
)

NINE_SECRET_ABILITIES = tuple(ability for ability in SPECIAL_ABILITY_POOL if ability.startswith("星律"))
FORBIDDEN_REALM_ABILITIES = ("初阈", "重阈", "归极域")
SPECIAL_ABILITY_RARITIES = {
    "初阈": ("玄阶", "极品"),
    "重阈": ("地阶", "中品"),
    "归极域": ("天阶", "下品"),
    "翠盏灵影": ("地阶", "上品"),
    "澄元剑芒": ("玄阶", "极品"),
    "元婴天兆": ("地阶", "极品"),
    "沧元道章": ("地阶", "中品"),
    "战演真法": ("天阶", "下品"),
    "玄金血脉": ("天阶", "中品"),
    "青华法相": ("天阶", "下品"),
    "灵骨天纹": ("天阶", "上品"),
    "身界蕴种": ("天阶", "极品"),
    "万象战影": ("天阶", "极品"),
    "环域灵轮": ("天阶", "中品"),
    "风掣疾行": ("天阶", "上品"),
    "青枝护相": ("天阶", "中品"),
    "沉岳指印": ("地阶", "极品"),
    "流年意境": ("地阶", "上品"),
    "血战真源": ("地阶", "极品"),
    "梦潮回环": ("天阶", "下品"),
    "命络断线": ("天阶", "中品"),
    "云章九歌": ("地阶", "极品"),
    "叩穹一式": ("天阶", "下品"),
    "内府开阖": ("玄阶", "极品"),
    **{ability: ("天阶", "极品") for ability in NINE_SECRET_ABILITIES},
}
SPECIAL_ABILITY_MATERIAL_DIFFICULTY = {
    "初阈战札": 0.75,
    "重阈战札": 0.36,
    "归极印纹": 0.16,
    "星律残页": 0.18,
}

SPECIAL_ABILITY_INFOS = {
    "初阈": {"material": "初阈战札", "source": "战境极限", "effect": "以战意踏入初阈，斗法时伤害和防御同步提升。", "aliases": ["初阈", "开启初阈"], "combat": (0.12, 0.04, 0)},
    "重阈": {"material": "重阈战札", "source": "初阈进阶", "effect": "在初阈之上再破一线，攻防与速度获得更稳定的提升。", "aliases": ["重阈", "开启重阈"], "combat": (0.15, 0.06, 4)},
    "归极域": {"material": "归极印纹", "source": "重阈升华", "effect": "重阈之后触及归极域，短时间踏入极限状态。", "aliases": ["归极", "归极域", "开启归极"], "combat": (0.18, 0.08, 8)},
    "星律-定魂篇": {"material": "星律残页", "source": "星律传承", "effect": "稳定神魂与气机，拉高攻守下限。", "aliases": ["定魂星律", "星律定魂"], "combat": (0.08, 0.08, 2)},
    "星律-御器篇": {"material": "星律残页", "source": "星律传承", "effect": "牵引灵器灵纹共鸣，提升攻伐威势。", "aliases": ["御器星律", "星律御器"], "combat": (0.10, 0.05, 0)},
    "星律-斗衡篇": {"material": "星律残页", "source": "星律传承", "effect": "演化斗战法则，以战养战。", "aliases": ["斗衡星律", "星律斗衡"], "combat": (0.13, 0.03, 0)},
    "星律-回生篇": {"material": "星律残页", "source": "星律传承", "effect": "激发生机与恢复底蕴，以守为攻。", "aliases": ["回生星律", "星律回生"], "combat": (0.00, 0.12, 0)},
    "星律-贯元篇": {"material": "星律残页", "source": "星律传承", "effect": "短暂放大自身战力，追求瞬间爆发。", "aliases": ["贯元星律", "星律贯元"], "combat": (0.16, 0.00, 0)},
    "星律-观势篇": {"material": "星律残页", "source": "星律传承", "effect": "推演战局缝隙，提升闪转和护身。", "aliases": ["观势星律", "星律观势"], "combat": (0.04, 0.05, 6)},
    "星律-布阵篇": {"material": "星律残页", "source": "星律传承", "effect": "结成战阵法纹，增强防御和控场。", "aliases": ["布阵星律", "星律布阵"], "combat": (0.03, 0.09, 3)},
    "星律-先觉篇": {"material": "星律残页", "source": "星律传承", "effect": "增强神识先觉，先一步看破攻势。", "aliases": ["先觉星律", "星律先觉"], "combat": (0.06, 0.04, 8)},
    "星律-流影篇": {"material": "星律残页", "source": "星律传承", "effect": "身法如流光，追求极速和脱身。", "aliases": ["流影星律", "星律流影"], "combat": (0.00, 0.04, 12)},
    "翠盏灵影": {"material": "翠盏灵影拓片", "source": "岁月灵液之道", "effect": "凝聚一缕绿光灵机，斗法时补足后劲。", "aliases": ["翠盏灵影", "瓶影"], "combat": (0.08, 0.07, 0)},
    "澄元剑芒": {"material": "澄元剑芒手札", "source": "剑修凝元之道", "effect": "剑芒凝而不散，提升剑类攻伐爆发。", "aliases": ["澄元剑芒", "剑芒"], "combat": (0.12, 0.02, 0)},
    "元婴天兆": {"material": "元婴天兆星痕", "source": "破婴天象感悟", "effect": "引来天兆压场，提升法力和护体。", "aliases": ["元婴天兆", "天兆"], "combat": (0.09, 0.07, 2)},
    "沧元道章": {"material": "沧元道章残页", "source": "元海观想", "effect": "气血如海，攻守节奏更稳。", "aliases": ["沧元道章", "元海"], "combat": (0.07, 0.08, 1)},
    "战演真法": {"material": "战演真法残卷", "source": "战演推法", "effect": "临阵演化攻伐，让战技更具压迫。", "aliases": ["战演", "战演真法"], "combat": (0.15, 0.02, 0)},
    "玄金血脉": {"material": "玄金血纹", "source": "金血战体之道", "effect": "气血若金海，增强近身压制与抗性。", "aliases": ["金血战体", "金血"], "combat": (0.10, 0.09, 0)},
    "青华法相": {"material": "青华法相旧纹", "source": "青华生灭之道", "effect": "青华法相开合，兼具生机与杀伐。", "aliases": ["青华法相", "莲相"], "combat": (0.09, 0.08, 0)},
    "灵骨天纹": {"material": "灵骨天纹", "source": "骨文天赋", "effect": "骨文发光，爆发强力神通。", "aliases": ["天骨", "骨符"], "combat": (0.14, 0.04, 0)},
    "身界蕴种": {"material": "身界蕴种道痕", "source": "身界蕴生之道", "effect": "以自身为天地，强化全面战力。", "aliases": ["身界蕴种", "身界"], "combat": (0.11, 0.08, 2)},
    "万象战影": {"material": "万象战影", "source": "战影分化之道", "effect": "化出一道战影，形成瞬间合击。", "aliases": ["万象战影", "分影"], "combat": (0.18, 0.03, 4)},
    "环域灵轮": {"material": "环域灵轮碎光", "source": "洞天开辟之道", "effect": "洞天光环连成一体，攻守同时拔高。", "aliases": ["环域", "灵轮", "环轮"], "combat": (0.10, 0.10, 1)},
    "风掣疾行": {"material": "风掣疾行风痕", "source": "风掣身法", "effect": "极速破空，让先手和追击更稳。", "aliases": ["风掣", "疾行"], "combat": (0.06, 0.02, 16)},
    "青枝护相": {"material": "青枝护相枝影", "source": "生灭法相", "effect": "柳枝化成护身法相，可守可攻。", "aliases": ["青枝", "护相", "法相"], "combat": (0.08, 0.11, 0)},
    "沉岳指印": {"material": "沉岳指印骨纹", "source": "沉岳肉身之道", "effect": "一指点出，以气血和法力同时压制。", "aliases": ["沉岳", "一指"], "combat": (0.13, 0.05, 0)},
    "流年意境": {"material": "流年意境残砂", "source": "时光意境", "effect": "让对手攻势似被时光拖慢，增加防御与先觉。", "aliases": ["岁月", "时光"], "combat": (0.06, 0.09, 5)},
    "血战真源": {"material": "血战真源血符", "source": "本源感悟", "effect": "攻势带上杀戮气机，伤害爆发更高。", "aliases": ["杀戮", "本源"], "combat": (0.16, 0.00, 0)},
    "梦潮回环": {"material": "梦潮回环沙", "source": "梦与轮回之道", "effect": "以梦境干扰战局，偏向控场和护身。", "aliases": ["梦道", "轮回"], "combat": (0.05, 0.10, 4)},
    "命络断线": {"material": "命络断线真箓", "source": "因果法则", "effect": "斩断一线攻势因果，以守为主并伺机反击。", "aliases": ["因果", "断线"], "combat": (0.07, 0.12, 3)},
    "云章九歌": {"material": "云章九歌玉简", "source": "神通唱诵之道", "effect": "歌声引动法则，让术式更易连成气势。", "aliases": ["牧天", "九歌"], "combat": (0.11, 0.06, 2)},
    "叩穹一式": {"material": "叩穹一式符令", "source": "问道叩天之法", "effect": "一问落下，攻势中带神魂压迫。", "aliases": ["天问", "一式"], "combat": (0.12, 0.04, 1)},
    "内府开阖": {"material": "内府开阖残图", "source": "肉身神藏", "effect": "打开身中神藏，提升灵力转化和护体。", "aliases": ["神藏", "开阖"], "combat": (0.08, 0.08, 2)},
}

SPECIAL_ABILITY_MATERIAL_TO_ABILITY = {
    "初阈战札": "初阈",
    "重阈战札": "重阈",
    "归极印纹": "归极域",
    "翠盏灵影拓片": "翠盏灵影",
    "翠盏灵影碎片": "翠盏灵影",
    "澄元剑芒手札": "澄元剑芒",
    "澄元剑芒残页": "澄元剑芒",
    "元婴天兆星痕": "元婴天兆",
    "沧元道章残页": "沧元道章",
    "战演真法残卷": "战演真法",
    "玄金血纹": "玄金血脉",
    "初阈战意札": "初阈",
    "青华法相旧纹": "青华法相",
    "灵骨天纹": "灵骨天纹",
    "身界蕴种道痕": "身界蕴种",
    "万象战影": "万象战影",
    "环域灵轮碎光": "环域灵轮",
    "风掣疾行风痕": "风掣疾行",
    "青枝护相枝影": "青枝护相",
    "沉岳指印骨纹": "沉岳指印",
    "流年意境残砂": "流年意境",
    "血战真源血符": "血战真源",
    "梦潮回环沙": "梦潮回环",
    "命络断线真箓": "命络断线",
    "云章九歌玉简": "云章九歌",
    "叩穹一式符令": "叩穹一式",
    "问玄旧简": "叩穹一式",
    "内府开阖残图": "内府开阖",
    "小内府残图": "内府开阖",
}

ATTRIBUTE_TECHNIQUE_NAMES = {
    "金": ["太白斩星", "庚金裂空", "剑气雷音", "白虹贯日", "金阙镇魔"],
    "木": ["青华化生", "万藤缚龙", "巨木撑天", "草木皆兵", "长生回春"],
    "水": ["沧海归墟", "天河倒卷", "水月镜花", "玄浪分潮", "寒潮镇魂"],
    "火": ["赤阳真火", "赤羽焚天", "离火炼界", "赤莲破妄", "炎龙吞海"],
    "土": ["玄黄不动", "息壤镇岳", "搬山覆海", "厚土载道", "山河印落"],
    "雷": ["玄雷万劫", "五雷正法", "雷海洗身", "劫光破阵", "天罚一指"],
    "冰": ["玄阴玄封", "寒狱葬天", "冰魄凝魂", "霜华照影", "寒冥锁界"],
}
GENERAL_TECHNIQUE_NAMES = ["盘龙镇邪", "大罗法咒", "问心一剑", "袖里乾坤", "灵台镇念"]
SOUL_INSIGHT_LAYER = 3
PHYSIQUE_TRAIT_NAMES = {
    "远荒战体": "远荒血脉",
    "身界蕴种": "\u8eab\u79cd\u9053\u82bd",
    "浑元战魔体": "浑元战魔相",
    "先天道胚": "\u9053\u80ce\u5171\u9e23",
    "玄阴灵体": "玄阴寒魄",
    "赤阳灵体": "赤阳灵焰",
    "青华灵体": "青华生息",
    "金羽神脉": "金羽疾行",
}
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
SPECIAL_ABILITY_CATEGORY = "神通"
LEGACY_SPECIAL_ABILITY_CATEGORY = "".join(chr(code) for code in (29305, 27530, 33021, 21147))
ACQUIRED_ROOT_DAN = "\u4e39\u7075\u6839"
ACQUIRED_ROOT_ARTIFACT = "\u5668\u7075\u6839"
ACQUIRED_ROOT_KINDS = (ACQUIRED_ROOT_DAN, ACQUIRED_ROOT_ARTIFACT)
DEMON_CORE_REALM_PURITY = {
    "\u6b8b\u788e": 34,
    "\u70bc\u4f53": 42,
    "\u7ec3\u6c14": 52,
    "\u70bc\u6c14": 52,
    "\u7b51\u57fa": 63,
    "\u91d1\u4e39": 76,
    "\u5143\u5a74": 84,
    "\u5316\u795e": 91,
    "\u70bc\u865a": 91,
    "\u5408\u4f53": 91,
    "\u5927\u4e58": 91,
    "\u6e21\u52ab": 91,
    "\u5047\u4ed9": 91,
    "\u771f\u4ed9": 91,
    "\u91d1\u4ed9": 91,
    "\u592a\u4e59": 91,
    "\u5927\u7f57": 91,
    "\u6df7\u5143\u91d1\u4ed9": 91,
    "\u51c6\u5723": 91,
    "\u5723\u4eba": 91,
}
DEMON_CORE_TIER_BASE_PURITY = {"\u51e1\u54c1": 36, "\u9ec4\u9636": 48, "\u7384\u9636": 62, "\u5730\u9636": 78, "\u5929\u9636": 88, "\u4ed9\u9636": 91, "\u4ed9\u5e1d\u5175": 91}
DEMON_CORE_EXP_BASE_BY_REALM = {
    "\u6b8b\u788e": 10,
    "\u70bc\u4f53": 14,
    "\u7ec3\u6c14": 28,
    "\u7b51\u57fa": 58,
    "\u91d1\u4e39": 118,
    "\u5143\u5a74": 240,
    "\u5316\u795e": 460,
    "\u70bc\u865a": 760,
    "\u5408\u4f53": 1180,
    "\u5927\u4e58": 1760,
    "\u6e21\u52ab": 2500,
    "\u5047\u4ed9": 3600,
    "\u771f\u4ed9": 5200,
    "\u91d1\u4ed9": 7600,
    "\u592a\u4e59": 10800,
    "\u5927\u7f57": 15200,
    "\u6df7\u5143\u91d1\u4ed9": 21000,
    "\u51c6\u5723": 28000,
    "\u5723\u4eba": 36000,
}
DEMON_CORE_TIER_EXP_RATIO = {"\u51e1\u54c1": 0.7, "\u9ec4\u9636": 1.0, "\u7384\u9636": 1.45, "\u5730\u9636": 2.05, "\u5929\u9636": 2.9, "\u4ed9\u9636": 4.2, "\u4ed9\u5e1d\u5175": 6.0}
DEMON_CORE_DEFAULT_REALM_BY_TIER = {"\u51e1\u54c1": "\u6b8b\u788e", "\u9ec4\u9636": "\u7ec3\u6c14", "\u7384\u9636": "\u7b51\u57fa", "\u5730\u9636": "\u91d1\u4e39", "\u5929\u9636": "\u5316\u795e", "\u4ed9\u9636": "\u771f\u4ed9", "\u4ed9\u5e1d\u5175": "\u5723\u4eba"}
DEMON_CORE_REALM_ALIASES = {
    "\u6b8b\u788e": "\u6b8b\u788e",
    "\u6b8b\u4e39": "\u6b8b\u788e",
    "\u70bc\u4f53": "\u70bc\u4f53",
    "\u7ec3\u4f53": "\u70bc\u4f53",
    "\u7ec3\u6c14": "\u7ec3\u6c14",
    "\u70bc\u6c14": "\u7ec3\u6c14",
    "\u7b51\u57fa": "\u7b51\u57fa",
    "\u91d1\u4e39": "\u91d1\u4e39",
    "\u5143\u5a74": "\u5143\u5a74",
    "\u5316\u795e": "\u5316\u795e",
    "\u70bc\u865a": "\u70bc\u865a",
    "\u7ec3\u865a": "\u70bc\u865a",
    "\u5408\u4f53": "\u5408\u4f53",
    "\u5927\u4e58": "\u5927\u4e58",
    "\u6e21\u52ab": "\u6e21\u52ab",
    "\u5047\u4ed9": "\u5047\u4ed9",
    "\u771f\u4ed9": "\u771f\u4ed9",
    "\u91d1\u4ed9": "\u91d1\u4ed9",
    "\u592a\u4e59": "\u592a\u4e59",
    "\u5927\u7f57": "\u5927\u7f57",
    "\u6df7\u5143\u91d1\u4ed9": "\u6df7\u5143\u91d1\u4ed9",
    "\u51c6\u5723": "\u51c6\u5723",
    "\u5723\u4eba": "\u5723\u4eba",
}
ARTIFACT_ROOT_TIER_BASE_PURITY = {"\u51e1\u54c1": 30, "\u9ec4\u9636": 42, "\u7384\u9636": 56, "\u5730\u9636": 68, "\u5929\u9636": 76, "\u4ed9\u9636": 78, "\u4ed9\u5e1d\u5175": 78}
DAN_ROOT_MAX_PURITY = 91
ARTIFACT_ROOT_MAX_PURITY = 78
ARTIFACT_ROOT_SUCCESS_RATE = 0.35
ARTIFACT_SLOTS = ("主手", "副手", "护甲")
ARTIFACT_SLOT_ALIASES = {
    "主手": "主手",
    "副手": "副手",
    "护手": "副手",
    "护甲": "护甲",
    "护盾": "护甲",
    "盾": "护甲",
    "甲": "护甲",
}
ARTIFACT_SLOT_POWER_RATE = {"主手": 1.0, "副手": 0.65, "护甲": 0.85}
ARTIFACT_ARMOR_NAME_TOKENS = ("盾", "铠", "衣", "裍", "袍", "护心", "护身", "护命", "守心")
ARTIFACT_SWORD_NAME_TOKENS = ("剑", "飞剑", "剑谱")
ARTIFACT_DUPLICATE_POWER_RATE = 0.2
ARTIFACT_NAME_POWER_RATE = {
    "星阙断岳剑": 1.0,
    "青衡万木杖": 1.13,
    "云海镇澜印": 1.16,
    "焚天离火旗": 1.14,
    "坤舆镇岳印": 1.16,
    "玄雷破劫槌": 1.15,
    "寒冥锁天镜": 1.14,
}
ARTIFACT_TIAN_TYPE_POWER_RATES = (
    (("印", "玺", "碑", "鼎"), 1.16),
    (("槌", "锤", "鼓"), 1.15),
    (("旗", "炉", "钟"), 1.14),
    (("镜", "轮", "瓶", "珠", "杖", "尺"), 1.13),
    (("戈", "刃", "枪", "弓", "刀"), 1.12),
)

def _legacy_text(*codes: int) -> str:
    return "".join(chr(code) for code in codes)


LEGACY_ITEM_NAME_ALIASES = {
    _legacy_text(23665, 27827, 31038, 31287, 21360): "坤舆镇岳印",
    _legacy_text(22826, 21476, 20861, 39592): "远古兽骨",
    _legacy_text(22826, 21476, 28304, 30707): "荒脉源石",
    _legacy_text(22826, 34394, 26025, 26143, 21073): "星阙断岳剑",
    _legacy_text(38738, 24093, 38271, 29983, 26454): "青衡万木杖",
    _legacy_text(20061, 38660, 38215, 28023, 21360): "云海镇澜印",
    _legacy_text(29572, 20901, 23553, 22825, 38236): "寒冥锁天镜",
    _legacy_text(32043, 38660, 24481, 38647, 27084): "玄雷破劫槌",
    _legacy_text(38738, 31481, 34562, 20113, 21073): "翠雷云竹剑",
    _legacy_text(24218, 37329, 38738, 31481, 34562, 20113, 21073): "玄金雷枝剑",
    _legacy_text(24218, 37329, 32441, 38647, 31481, 21073): "玄金雷枝剑",
    _legacy_text(22823, 24218, 21073, 38453): "玄金列星剑阵",
    _legacy_text(22823, 24218, 37329, 21073, 38453): "玄金列星剑阵",
    _legacy_text(38738, 33714, 20185, 20185, 24093, 20853): "青华生灭印",
    _legacy_text(38738, 33714, 20185, 24093, 20853): "青华生灭印",
    _legacy_text(38271, 29983, 38738, 33714, 27531, 36527): "青华生机残晶",
    _legacy_text(38738, 33714, 36947, 30456, 26087, 32441): "青华法相旧纹",
    _legacy_text(38738, 33714, 36947, 30456): "青华法相",
    _legacy_text(38738, 33714, 20185, 24341): "青华仙引",
    _legacy_text(38738, 33714, 24320, 22825, 23610): "青华开岳尺",
    _legacy_text(38738, 33714, 36896, 21270, 32463): "青华造化经",
    _legacy_text(34494, 31354, 20185, 37329): "空痕仙金",
    _legacy_text(20964, 34880, 36196, 37329): "赤羽曜金",
    _legacy_text(40857, 32441, 29572, 37329): "玄龙纹金",
    _legacy_text(29572, 40644, 28304, 26681): "坤源根",
    _legacy_text(29572, 40644, 27597, 27668): "坤元母气",
    _legacy_text(20185, 27583, 38738, 38108, 38152): "云殿铜锈",
    _legacy_text(38738, 38108, 20185, 32441): "古铜云纹",
    _legacy_text(38738, 38108, 20185, 32441, 30424): "古铜云纹盘",
    _legacy_text(29572, 40644, 28304, 40718): "坤元源鼎",
    _legacy_text(29572, 40644, 28304, 40718, 20223, 21046, 21697): "坤元源鼎仿制品",
    _legacy_text(40857, 32441, 29572, 37329, 40718): "玄龙纹金鼎",
    _legacy_text(40857, 32441, 29572, 37329, 40718, 20223, 21697): "玄龙纹金鼎仿品",
    _legacy_text(20964, 34880, 36196, 37329, 28809, 20223, 21697): "赤羽曜金炉仿品",
    _legacy_text(22826, 30333, 20185, 37329, 21073, 32974): "白曜星金剑胎",
    _legacy_text(20061, 31192, 27531, 39029): "星律残页",
    _legacy_text(20843, 31105, 24863, 24735): "初阈战札",
    _legacy_text(20061, 31105, 24863, 24735): "重阈战札",
    _legacy_text(31070, 31105, 28825, 21360): "归极印纹",
    _legacy_text(20843, 31105): "初阈",
    _legacy_text(20061, 31105): "重阈",
    _legacy_text(31070, 31105, 39046, 22495): "归极域",
}
LEGACY_ITEM_NAME_ALIASES.update(IMMORTAL_SEED_NAME_ALIASES)


def canonical_item_name(name: str) -> str:
    text = str(name or "").strip()
    if not text:
        return text
    replica_suffix = "仿制品"
    has_replica_suffix = text.endswith(replica_suffix)
    base = text[: -len(replica_suffix)] if has_replica_suffix else text
    if base.startswith("婴元"):
        base = f"元婴{base[2:]}"
    canonical = LEGACY_ITEM_NAME_ALIASES.get(base, base)
    return f"{canonical}{replica_suffix}" if has_replica_suffix else canonical

MYSTIC_REALM_TYPES = ("上古宗门遗址", "兽潮", "上古大能洞府", "星古矿区", "魂界残域", "古铜云阙")
MYSTIC_REALM_MAX_STEPS = 10
MYSTIC_BOSS_DAILY_BASE_ATTEMPTS = 4
MYSTIC_BOSS_WEEKLY_BONUS_THRESHOLDS = (3, 5, 7)
BEAST_NAME_PREFIXES = [
    "赤焰", "玄霜", "碧鳞", "噬月", "裂山", "幽冥", "金瞳", "雷角", "青翼", "血纹",
    "吞星", "搬山", "银翼", "黑渊", "紫电", "白骨", "青冥", "远荒", "血月", "玄甲",
    "九首", "独角", "金羽", "寒狱", "离火", "沧溟", "黄泉", "风吼", "铁脊", "玉鳞",
]
BEAST_NAME_SUFFIXES = [
    "妖虎", "蛟王", "灵猿", "玄龟", "魔狼", "狮鹫", "蛇君", "古象", "鹰王", "蜃兽",
    "魔猿", "荒犼", "雷鹏", "骨龙", "火麟", "冰蟒", "山魈", "血蝠", "天狼", "玄蛛",
    "石犀", "鬼面獒", "碧眼蟾", "吞月狐", "裂海鲸", "赤羽鸾", "铁甲蜈", "青鳞鲛", "风翼豹", "古蜥",
]

BEAST_NAMES = [
    f"{prefix}{suffix}"
    for prefix, suffix in zip(BEAST_NAME_PREFIXES, BEAST_NAME_SUFFIXES)
]


def random_beast_name() -> str:
    return random.choice(BEAST_NAMES)

BOSS_ARCHETYPE_CONFIGS = {
    "dragon": {
        "tokens": ("蛟", "龙", "鲛", "麟"),
        "race": "妖族-真龙遗脉",
        "physique": "青华道体",
        "method": "龙皇镇海经",
        "method_kind": "战技类",
        "artifact": "沧龙破海戟",
        "offhand": "逆鳞护心镜",
        "armor": "龙鳞玄甲",
        "talisman": "龙魂镇岳符",
        "array": "沧海锁龙阵",
        "abilities": ("归极域", "沉岳指印"),
        "techniques": ("沧龙裂海", "逆鳞碎岳", "真龙摆尾", "龙吟镇魂", "覆海玄光"),
        "intro": "龙血妖气如潮起伏，鳞甲间有古老龙纹明灭。",
    },
    "thunder": {
        "tokens": ("雷", "鹏", "金羽", "紫电"),
        "race": "妖族-金羽雷鹏",
        "physique": "金羽神脉",
        "method": "风掣雷遁篇",
        "method_kind": "战技类",
        "artifact": "玄雷羽刃",
        "offhand": "风雷双翼轮",
        "armor": "金鹏神羽甲",
        "talisman": "天雷破邪符",
        "array": "玄霄引雷阵",
        "abilities": ("初阈", "风掣疾行"),
        "techniques": ("风掣疾行", "玄雷万劫", "雷羽斩天", "风掣裂空", "天鹏搏龙术"),
        "intro": "鹏影压天，雷羽扫开云层，速度快到只余残光。",
    },
    "fire": {
        "tokens": ("火", "赤", "焰", "离火", "赤羽"),
        "race": "妖族-远荒火脉",
        "physique": "赤阳灵体",
        "method": "赤阳焚天诀",
        "method_kind": "战技类",
        "artifact": "离火焚天戟",
        "offhand": "赤霞火轮",
        "armor": "凰血炎甲",
        "talisman": "赤羽焚身符",
        "array": "赤阳真火阵",
        "abilities": ("重阈", "赤阳真火"),
        "techniques": ("赤阳真火", "赤羽焚天", "离火炼界", "焚山煮海", "火麟踏天"),
        "intro": "烈焰铺地，火脉首领每一次呼吸都像炉门洞开。",
    },
    "ice": {
        "tokens": ("冰", "霜", "寒", "玄霜", "寒狱"),
        "race": "妖族-玄冰血裔",
        "physique": "玄阴灵体",
        "method": "玄阴玄冰经",
        "method_kind": "神魂类",
        "artifact": "寒狱冰魄枪",
        "offhand": "玄冰照魂镜",
        "armor": "玄阴寒鳞甲",
        "talisman": "冰魄封魂符",
        "array": "寒冥锁界阵",
        "abilities": ("梦潮回环", "玄阴寒髓"),
        "techniques": ("玄阴玄封", "寒狱葬天", "冰魄凝魂", "寒冥锁界", "霜华照影"),
        "intro": "寒潮无声漫过脚踝，神魂像被冰镜照住。",
    },
    "earth": {
        "tokens": ("山", "象", "龟", "犀", "玄甲", "石"),
        "race": "妖族-搬山古兽",
        "physique": "远荒战体",
        "method": "玄黄搬山经",
        "method_kind": "锻体类",
        "artifact": "撼岳巨锤",
        "offhand": "玄龟镇海盾",
        "armor": "厚土不动甲",
        "talisman": "玄甲护身符",
        "array": "山河镇岳阵",
        "abilities": ("环域灵轮", "玄黄不动"),
        "techniques": ("玄黄不动", "搬山覆海", "厚土载道", "山河印落", "古象踏天"),
        "intro": "大地随它的脚步起伏，厚重妖力像一座山压来。",
    },
    "soul": {
        "tokens": ("蜃", "幽", "鬼", "冥", "血", "月", "魔"),
        "race": "妖族-幽冥异种",
        "physique": "浑元战魔体",
        "method": "幽冥噬魂经",
        "method_kind": "神魂类",
        "artifact": "黄泉噬魂幡",
        "offhand": "白骨摄心铃",
        "armor": "幽冥血纹袍",
        "talisman": "噬魂镇魄符",
        "array": "黄泉万魂阵",
        "abilities": ("血战真源", "梦潮回环"),
        "techniques": ("黄泉噬魂", "白骨镇魂", "血月幻杀", "幽冥入梦", "万魂噬心"),
        "intro": "阴风里有万魂低语，首领眼中倒映出你的心魔。",
    },
    "poison": {
        "tokens": ("蛇", "蛛", "蟾", "蜈"),
        "race": "妖族-万毒灵裔",
        "physique": "玄阴灵体",
        "method": "万毒噬灵经",
        "method_kind": "战技类",
        "artifact": "碧毒穿心刺",
        "offhand": "万蛊玄壶",
        "armor": "毒雾隐鳞衣",
        "talisman": "瘴毒封脉符",
        "array": "万毒迷天阵",
        "abilities": ("内府开阖", "沉岳指印"),
        "techniques": ("万毒噬灵", "碧眼封喉", "蛛网锁魂", "瘴海沉身", "毒牙裂魄"),
        "intro": "毒雾绕成古怪符纹，地面每一处阴影都在蠕动。",
    },
    "default": {
        "tokens": (),
        "race": "妖族-远荒异兽",
        "physique": "凡体",
        "method": "万兽吞灵诀",
        "method_kind": "战技类",
        "artifact": "裂山兽王爪",
        "offhand": "兽骨护魂牌",
        "armor": "兽王玄骨甲",
        "talisman": "兽血狂战符",
        "array": "万兽奔雷阵",
        "abilities": ("初阈",),
        "techniques": ("裂山爪", "万兽奔腾", "妖云压顶", "兽王怒吼", "荒骨冲撞"),
        "intro": "兽王妖气铺开，周围群兽同时俯首。",
    },
}


MYSTIC_EVENT_THEMES = {
    '上古宗门遗址': {
        'places': ['断碑林', '讲经台', '废弃丹房', '护山残阵', '问心石阶', '藏经地宫', '剑冢深处', '祖师神像', '弟子名册', '灵植药园'],
        'actions': ['探查', '推开', '绕过', '拾起', '催动灵力照向', '凝视', '破开', '沿着气息进入', '踏入', '记下'],
        'omens': ['耳边似有万人诵经', '残阵倒转星光', '地下传来祖师叹息', '断剑震颤如闻雷音', '丹香从灰烬里回甘', '石阶映出你的道心', '木牌浮出灵光', '经书自行翻页', '药园土壤仍藏生机', '山门外的风像故人低语'],
        'empty': ['石门无声合拢，只留一地尘灰。', '残经一触即碎，你只得收回神识。', '阵纹忽明忽暗，暂时没有显出生门。'],
        'reward_lines': [
            ('功法', '青木长生功', '残经与你的气机相合，化作一门可修的功法。'),
            ('丹药', '培元丹', '丹炉余热未散，灰烬里滚出一枚丹药。'),
            ('阵盘', '小五行聚灵盘', '阵眼暗格弹开，残阵核心被你取走。'),
            ('灵植', '凝露灵草', '药园残土裂开，一株灵植仍有生机。'),
            (SPECIAL_ABILITY_CATEGORY, '澄元剑芒手札', '祖师残念在你掌心留下剑芒手札。'),
            ('灵材', '旧宗木简', '弟子名册最后一页化作可入器的木简。'),
            ('仙缘', '残碑悟道', '问心石认可了你的道心，一缕悟道灵机直入丹田。'),
        ],
        'bad': '问心石骤然翻转，昔年宗门覆灭的怨念如潮压来。你强行脱身，却被残阵浊气封住经脉。',
        'intro': '残碑半埋，山门无声，深处仍有经卷气息流转。',
    },
    '兽潮': {
        'places': ['血雾山谷', '万兽骨堆', '幼兽巢穴', '妖云深处', '裂山河畔', '兽王爪痕', '雷火焦土', '古林残道', '鳄血石潭', '散修防线'],
        'actions': ['探查', '推开', '绕过', '拾起', '催动灵力照向', '凝视', '破开', '沿着气息进入', '踏入', '记下'],
        'omens': ['首领竖瞳里有丹光浮沉', '巢穴深处传来幼兽低啼', '妖风卷起灰黑骨粉', '血泥里有灵草不倒', '兽群忽然朝一点伏下', '一枚妖丹在尸骨间明灭', '裂山声中掉落异骨', '老兽把爪下灵物推出血线', '散修抛来储物符', '妖云被天雷撕开一线'],
        'empty': ['兽群忽然回涌，你稳住气息退回安全处。', '首领威压扫过山谷，你伏身不动。', '妖兽足印在乱石中断绝，只留一片焦黑血泥。'],
        'reward_lines': [
            ('灵材', '妖丹', '你剖开首领残躯，取出一枚尚在跳动的妖丹。'),
            ('灵材', '兽骨', '裂山之后，一截兽骨带着血煎灵光被你收起。'),
            ('灵材', '妖兽精血', '你以玉瓶承住兽血，血中妖力犹在汹涌。'),
            ('灵食', '火枣灵酥', '兽巢旁藏着温热灵食，似是散修逃难时遗落。'),
            ('符箓', '金甲护身符', '一名散修被你救下，他留下一道护身符作谢。'),
            ('灵石', '中品灵石袋', '兽潮冲破矿脉，你在乱石间收到一袋灵石。'),
            ('仙缘', '山神馈赠', '老兽没有扑来，反而将一缕山神馈赠送到你面前。'),
        ],
        'bad': '兽王忽然睁开竖瞳，万兽同声嘶吼，血色妖云瞬间压下。你撕开缺口逃出，却被妖煞侵入经脉。',
        'intro': '远处妖云翻涌，兽群如潮，一头首领的气息正在巢穴深处起伏。',
    },
    '上古大能洞府': {
        'places': ['青灯石室', '白玉棋盘', '三重丹库', '水镜问心台', '青铜古棺', '星河石阶', '封魔链洞', '幻音长廊', '传道壁画', '洞府阵眼'],
        'actions': ['探查', '推开', '绕过', '拾起', '催动灵力照向', '凝视', '破开', '沿着气息进入', '踏入', '记下'],
        'omens': ['宝匣内传出一声叹息', '古灯映出不属此界的影子', '棋子落下时星河倒卷', '壁画中的古修正在看你', '水镜碎成一地清辉', '丹库里有药香未散', '链洞深处传来低笑', '星阶尽头浮出古印', '阵眼吐出精纯清光', '心魔声音像极故人'],
        'empty': ['气机忽然隐去，你暂时没有所得。', '前方禁制太重，你收回神识。', '一阵风吹过，线索被灵雾遮住。'],
        'reward_lines': [
            ('奇物', '星砂沙漏', '棋盘胜负已定，一枚星砂沙漏从桌角滚落。'),
            (SPECIAL_ABILITY_CATEGORY, '沉岳指印骨纹', '壁画古修抬手，一道指意骨纹落入识海。'),
            ('灵器', '玄都镇魂铃', '青灯灭去后，灯座下露出一件灵器。'),
            ('丹药', '紫府养魂丹', '丹库禁制退开，一枚养魂丹仍有药香。'),
            ('阵盘', '水月镜花盘', '水镜破碎后，镜底一方阵盘显出真形。'),
            ('灵材', '古铜云纹', '古棺外壁剥落一片古铜云纹。'),
            ('仙缘', '古洞机缘', '洞府残念认可你未贪的一念，赐下一线机缘。'),
        ],
        'bad': '洞府传承顷刻化作杀局，古灯映出的不是大道，而是借壳归来的邪影。',
        'intro': '洞府石门半启，禁制明灭不定，像是传承，也像是请君入瓮。',
    },
    '星古矿区': {
        'places': ['黑渊矿道', '源石矿壁', '地火裂缝', '古矿祭坛', '矿奴废营', '星陨石坑', '玄铁暗河', '断龙石门', '残灯矿廊', '浑元石胎'],
        'actions': ['探查', '推开', '绕过', '拾起', '催动灵力照向', '凝视', '破开', '沿着气息进入', '踏入', '记下'],
        'omens': ['矿壁中像有古老心脏跳动', '源石裂缝里流出紫金光', '地火化作莲花形', '矿廊深处传来铁链声', '一枚石胆在掌心滚烫', '矿灯照出不属你的影子', '星陨石坑中有金铁轻鸣', '黑渊下涌起浑浊道韵', '矿锄指向一处暗壁', '石门上龙纹渐渐复苏'],
        'empty': ['气机忽然隐去，你暂时没有所得。', '前方禁制太重，你收回神识。', '一阵风吹过，线索被灵雾遮住。'],
        'reward_lines': [
            ('灵材', '荒脉源石', '你剖开源石，一块荒脉源石在掌心微微发热。'),
            ('灵材', '古矿石胆', '矿壁中的石胆被你取出，仍有地火灵机。'),
            ('灵材', '星陨玄铁', '星陨石坑裂开，露出一段可炼器的玄铁。'),
            ('灵石', '上品灵石匣', '矿奴废营里藏着一只封存完好的灵石匣。'),
            ('奇物', '无名石片', '石胎外壳剥落一片无名石片。'),
            ('杂物', '破旧丹炉盖', '矿廊尽头有旧炉残件，似能抵挡地火。'),
            ('仙缘', '玄黄命砂', '浑元石胎轻震，一缕玄黄命砂融入气海。'),
        ],
        'bad': '黑渊矿道突然整片塌落，石胎中传出不似人声的低笑。',
        'intro': '星古矿区石门半塌，地火与源气交织，深处似有石胎轻响。',
    },
    '魂界残域': {
        'places': ['魂海断桥', '虚神战台', '石碑通道', '梦道雾林', '万族试炼场', '断裂神宫', '风雷骨路', '魂砂海滩', '重瞳镜湖', '古老门户'],
        'actions': ['探查', '推开', '绕过', '拾起', '催动灵力照向', '凝视', '破开', '沿着气息进入', '踏入', '记下'],
        'omens': ['虚空中有少年独战万族的残影', '石碑上名字一个个熄灭', '梦雾里传来远古钟声', '战台残血在脚下发光', '神宫上空有环域虚影', '魂砂像星河流动', '镜湖映出你未来一次败局', '风雷残音把符文刻入虚空', '古门后的世界忽然翻面', '你听见自己的神魂在鸣唱'],
        'empty': ['气机忽然隐去，你暂时没有所得。', '前方禁制太重，你收回神识。', '一阵风吹过，线索被灵雾遮住。'],
        'reward_lines': [
            (SPECIAL_ABILITY_CATEGORY, '环域灵轮碎光', '战台虚影被你击散，环域灵轮碎光融入掌心。'),
            (SPECIAL_ABILITY_CATEGORY, '风掣疾行风痕', '风雷残音沉入脚下，留下一道风掣疾行风痕。'),
            ('灵材', '魂界灵砂', '魂砂海滩上的光点被你收拢，化作魂界灵砂。'),
            ('功法', '星墟观想篇', '石碑残名里藏着观想之法，被你拓入识海。'),
            ('符箓', '御风疾影符', '风雷骨路尽头落下一张疾影符。'),
            ('奇物', '低语玉佩', '重瞳镜湖底沉着一枚低语玉佩。'),
            ('仙缘', '灵台清光', '魂界残域与你的神魂短暂共鸣，灵台清光洗过识海。'),
        ],
        'bad': '虚神战台突然反转，万族残影同时向你杀来。',
        'intro': '魂界残域忽明忽暗，这里像一片未散的神魂战场。',
    },
    '古铜云阙': {
        'places': ['青铜长阶', '云上古殿前庭', '远荒壁画', '九重铜门', '断裂仙池', '天罚雷痕', '空悬石棺', '经文铜柱', '归墟残桥', '无声高座'],
        'actions': ['探查', '推开', '绕过', '拾起', '催动灵力照向', '凝视', '破开', '沿着气息进入', '踏入', '记下'],
        'omens': ['青铜墙面上浮出一朵青华', '高座前的空气像被大手抚平', '铜门后传来诵经声', '天罚雷痕在脚下化作细线', '石棺轻震却未开启', '仙池残液映出一条古路', '壁画中有无名强者背对众生', '铜柱经文像活了过来', '残桥下是看不到底的黑暗', '云上古殿似乎在判断你的重量'],
        'empty': ['气机忽然隐去，你暂时没有所得。', '前方禁制太重，你收回神识。', '一阵风吹过，线索被灵雾遮住。'],
        'reward_lines': [
            (SPECIAL_ABILITY_CATEGORY, '星律残页', '铜柱经文中飞出一页残篇，上有星律气息。'),
            ('灵材', '云殿铜锈', '你从壁画剥落处取下云殿铜锈。'),
            ('奇物', '镜湖碎光', '断裂仙池中浮起一点镜湖碎光。'),
            ('灵器', '星阙断岳剑', '青铜门后剑光一闪，一件灵器自行落入你手中。'),
            ('功法', '万象归元经', '远荒壁画上的经文亮起，化成一部古经。'),
            ('灵材', '天髓玉露', '仙池断口还有一滴天髓玉露，被你以玉瓶收起。'),
            ('仙缘', '青华仙引', '青华虚影在云上古殿中一闪，引来一缕仙缘清光。'),
        ],
        'bad': '古铜云阙深处忽然传来审判般的威压，九重铜门同时闭合。',
        'intro': '古铜云阙悬于虚空，铜锈与仙光交织，每一步都像走进古史。',
    },
}


def build_mystic_event_pool(realm_type: str) -> list[dict[str, Any]]:
    theme = MYSTIC_EVENT_THEMES[realm_type]
    events: list[dict[str, Any]] = []
    reward_lines = list(theme.get("reward_lines", []))
    for place in theme["places"]:
        for action in theme["actions"]:
            omen = theme["omens"][(len(events) + len(place) + len(action)) % len(theme["omens"])]
            category, reward_hint, success = reward_lines[len(events) % len(reward_lines)]
            events.append({"text": f"{action}{place}，{omen}", "category": category, "reward_hint": reward_hint, "success": success})
            if len(events) >= 100:
                return events
    return events


MYSTIC_OPTION_POOLS = {
    realm_type: build_mystic_event_pool(realm_type)
    for realm_type in MYSTIC_REALM_TYPES
}

SPIRIT_STONE_VALUES = {"凡品": 6, "黄阶": 14, "玄阶": 32, "地阶": 72, "天阶": 160, "仙阶": 420, "仙帝兵": 1800}
PUPPET_POWER_RATE = {"凡品": 0.45, "黄阶": 0.6, "玄阶": 0.78, "地阶": 0.95, "天阶": 1.15, "仙阶": 1.35, "仙帝兵": 1.65}
PLANT_SIGN_RATE = {"凡品": 0.06, "黄阶": 0.1, "玄阶": 0.16, "地阶": 0.24, "天阶": 0.34, "仙阶": 0.48, "仙帝兵": 0.72}
CULTIVATION_ROUTES = ("剑修", "术修", "炼丹师", "阵法师", "炼器师")
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
    "神通": 260,
    "仙源": 520,
}
TIER_PRICE_RATIO = {"凡品": 1, "黄阶": 3, "玄阶": 9, "地阶": 27, "天阶": 81, "仙阶": 243, "仙帝兵": 2187}
GRADE_PRICE_RATIO = {"下品": 1.0, "中品": 1.22, "上品": 1.55, "极品": 2.1}
TIER_REALM_REQUIREMENT = {"凡品": 0, "黄阶": 0, "玄阶": 3, "地阶": 4, "天阶": 5, "仙阶": 10, "仙帝兵": 13}
ARTIFACT_TIER_DEFAULT_REALM = {"凡品": 0, "黄阶": 0, "玄阶": 0, "地阶": 0, "天阶": 0, "仙阶": 10, "仙帝兵": 13}
ARTIFACT_REALM_TIER_UNLOCKS = {
    index: list(artifact_realm_tiers_for_index(index))
    for index in range(len(REALMS))
}
ARTIFACT_DROP_POOLS: dict[int, list[dict[str, Any]]] = {}
MYSTIC_ENABLED_TYPES: set[str] = set(MYSTIC_REALM_TYPES)
MYSTIC_ENABLED_HIGH_RISK_TYPES: set[str] = set(HIGH_RISK_MYSTIC_REALM_TYPES)
MYSTIC_FISHING_OPTION_RATE = 0.05
SIGNIN_EXTRA_FISHING_CHANCE_RATE = 0.10
MYSTIC_CATEGORY_WEIGHTS: dict[str, list[tuple[str, float]]] = {}
MYSTIC_DROP_OVERRIDES: dict[str, list[dict[str, Any]]] = {}
TALISMAN_DRAW_REALM_REQUIREMENT = {"\u51e1\u54c1": 0, "\u9ec4\u9636": 0, "\u7384\u9636": 3, "\u5730\u9636": 4, "\u5929\u9636": 5}
ALCHEMY_RECIPES = {
    "筑基丹": {"tier": "黄阶", "grade": "中品", "materials": ["凝露草", "清心草叶", "百年朱果"], "cost": 80, "difficulty": 4},
    "地脉筑基液": {"tier": "地阶", "grade": "下品", "materials": ["地脉火芝", "月华凝露", "黄芽芝"], "cost": 320, "difficulty": 9},
    "天道筑基露": {"tier": "天阶", "grade": "下品", "materials": ["天髓玉露", "万道莲实", "悟道茶心"], "cost": 1200, "difficulty": 15},
    "小还丹": {"tier": "玄阶", "grade": "中品", "materials": ["金纹灵芝", "火枣核", "紫纹灵木"], "cost": 180, "difficulty": 7},
    "金液丹": {"tier": "玄阶", "grade": "上品", "materials": ["金纹灵芝", "黑曜灵砂", "云母灵液"], "cost": 260, "difficulty": 8},
    "大还丹": {"tier": "地阶", "grade": "上品", "materials": ["紫府灵芝", "月华凝露", "地脉火芝"], "cost": 480, "difficulty": 11},
    "凝魄金丹": {"tier": "地阶", "grade": "极品", "materials": ["紫府灵芝", "养魂莲心", "金髓玉砂"], "cost": 760, "difficulty": 13},
    "造化金丹": {"tier": "天阶", "grade": "上品", "materials": ["九转玄参", "万道莲实", "坤元母气"], "cost": 1800, "difficulty": 17},
    "元婴丹": {"tier": "地阶", "grade": "极品", "materials": ["玄冰玉髓", "紫府灵芝", "星陨玄铁"], "cost": 680, "difficulty": 12},
    "护婴丹": {"tier": "地阶", "grade": "上品", "materials": ["养魂莲心", "月华凝露", "天青灵藤"], "cost": 620, "difficulty": 11},
    "九窍化婴丹": {"tier": "天阶", "grade": "上品", "materials": ["九转玄参", "玄阴寒髓", "悟道茶心"], "cost": 1900, "difficulty": 17},
    "九转凝神丹": {"tier": "天阶", "grade": "上品", "materials": ["九转玄参", "悟道茶心", "天髓玉露"], "cost": 1400, "difficulty": 15},
    "斩尘化神丹": {"tier": "天阶", "grade": "上品", "materials": ["悟道茶心", "玄阴寒髓", "赤阳真火液"], "cost": 2100, "difficulty": 18},
    "太清渡厄丹": {"tier": "天阶", "grade": "极品", "materials": ["天髓玉露", "浑元星砂", "悟道茶心"], "cost": 2200, "difficulty": 18},
    "渡劫护命丹": {"tier": "天阶", "grade": "极品", "materials": ["劫雷神木", "天髓玉露", "浑元星砂"], "cost": 2600, "difficulty": 19},
}
EXTRA_ALCHEMY_RECIPES = {
    "散修回气散": {"tier": "凡品", "grade": "中品", "materials": ["晨露草", "苦参须", "山参碎须"], "cost": 18, "difficulty": 2},
    "灵麦养元丸": {"tier": "凡品", "grade": "上品", "materials": ["灵麦芽", "青苔灵屑", "溪边圆石"], "cost": 22, "difficulty": 2},
    "兽血淬体膏": {"tier": "黄阶", "grade": "下品", "materials": ["野兽精血", "幼兽乳牙", "断裂兽爪"], "cost": 34, "difficulty": 3},
    "残丹续脉丸": {"tier": "黄阶", "grade": "中品", "materials": ["残碎妖丹", "残破兽骨", "残破碑屑"], "cost": 46, "difficulty": 4},
    "火鸦暖脉丹": {"tier": "黄阶", "grade": "上品", "materials": ["火鸦羽灰", "月露珠", "土精砂"], "cost": 58, "difficulty": 5},
    "练气妖丹丸": {"tier": "黄阶", "grade": "极品", "materials": ["练气妖丹", "血线草", "青灵花"], "cost": 72, "difficulty": 6},
    "兽巢壮骨丹": {"tier": "黄阶", "grade": "上品", "materials": ["兽巢骨粉", "妖兽利爪", "矿脉源砂"], "cost": 76, "difficulty": 6},
    "冰魄洗髓丹": {"tier": "玄阶", "grade": "中品", "materials": ["冰魄花蕊", "百年寒髓", "碧玉参须"], "cost": 210, "difficulty": 8},
    "赤鳞沸血丹": {"tier": "玄阶", "grade": "上品", "materials": ["赤鳞妖血", "妖兽精血", "筑基妖丹"], "cost": 260, "difficulty": 9},
    "古矿锻魂丹": {"tier": "玄阶", "grade": "极品", "materials": ["古矿石胆", "魂界灵砂", "赤霞铜精"], "cost": 330, "difficulty": 10},
    "金丹妖魄丹": {"tier": "地阶", "grade": "中品", "materials": ["金丹妖丹", "蛟龙脊骨", "龙血朱果"], "cost": 620, "difficulty": 12},
    "元婴妖魄丹": {"tier": "地阶", "grade": "极品", "materials": ["元婴妖丹", "荒脉源石", "地肺火液"], "cost": 940, "difficulty": 14},
    "青铜悟道丹": {"tier": "天阶", "grade": "下品", "materials": ["古铜云纹", "旧宗木简", "养魂莲心"], "cost": 1120, "difficulty": 15},
    "虚神凝魄丹": {"tier": "天阶", "grade": "中品", "materials": ["魂界灵晶", "道源矿髓", "远古兽骨"], "cost": 1680, "difficulty": 17},
    "古妖王血丹": {"tier": "天阶", "grade": "极品", "materials": ["古妖王丹", "青华生机残晶", "万道莲实"], "cost": 3200, "difficulty": 20},
}
ALCHEMY_RECIPES.update(EXTRA_ALCHEMY_RECIPES)

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
    "仙帝兵": 26000,
    "仙阶": 7600,
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
ARTIFACT_TIER_POWER_RATIO = {
    "凡品": 0.36,
    "黄阶": 0.50,
    "玄阶": 0.68,
    "地阶": 0.88,
    "天阶": 1.10,
    "仙阶": 1.36,
}
ARTIFACT_IMMORTAL_UPGRADE_RATE = 0.18
ARTIFACT_REALM_POWER_BASE = {
    0: 120,
    1: 180,
    2: 300,
    3: 520,
    4: 820,
    5: 1250,
    6: 1850,
    7: 2700,
    8: 3900,
    9: 5600,
    10: 7900,
    11: 11000,
    12: 15000,
    13: 20000,
    14: 26500,
    15: 34500,
    16: 44500,
    17: 56500,
    18: 71000,
    19: 88000,
    20: 108000,
    21: 131000,
    22: 158000,
    23: 189000,
    24: 225000,
    25: 266000,
}

def default_mystic_category_weights() -> dict[str, list[dict[str, Any]]]:
    return {
        "上古宗门遗址": [
            {"category": "功法", "weight": 4}, {"category": SPECIAL_ABILITY_CATEGORY, "weight": 2},
            {"category": "丹药", "weight": 2}, {"category": "阵盘", "weight": 2},
            {"category": "灵材", "weight": 3}, {"category": "灵植", "weight": 2},
            {"category": "仙缘", "weight": 1}, {"category": "杂物", "weight": 1},
        ],
        "兽潮": [
            {"category": "灵材", "weight": 6}, {"category": "灵石", "weight": 3},
            {"category": "符箓", "weight": 2}, {"category": "灵食", "weight": 2},
            {"category": "灵植", "weight": 1}, {"category": SPECIAL_ABILITY_CATEGORY, "weight": 1},
            {"category": "仙缘", "weight": 1},
        ],
        "星古矿区": [
            {"category": "灵材", "weight": 6}, {"category": "灵石", "weight": 4},
            {"category": "奇物", "weight": 2}, {"category": "杂物", "weight": 2},
            {"category": "仙缘", "weight": 1},
        ],
        "魂界残域": [
            {"category": SPECIAL_ABILITY_CATEGORY, "weight": 4}, {"category": "功法", "weight": 3},
            {"category": "灵材", "weight": 2}, {"category": "符箓", "weight": 2},
            {"category": "奇物", "weight": 2}, {"category": "仙缘", "weight": 1},
        ],
        "古铜云阙": [
            {"category": SPECIAL_ABILITY_CATEGORY, "weight": 4}, {"category": "灵材", "weight": 3},
            {"category": "奇物", "weight": 3}, {"category": "灵器", "weight": 2},
            {"category": "功法", "weight": 2}, {"category": "仙缘", "weight": 1},
        ],
        "default": [
            {"category": "奇物", "weight": 3}, {"category": SPECIAL_ABILITY_CATEGORY, "weight": 3},
            {"category": "灵器", "weight": 2}, {"category": "丹药", "weight": 2},
            {"category": "阵盘", "weight": 2}, {"category": "灵材", "weight": 2},
            {"category": "灵植", "weight": 2}, {"category": "仙缘", "weight": 1},
            {"category": "杂物", "weight": 2},
        ],
    }



def default_artifact_drop_pools() -> dict[str, list[dict[str, Any]]]:
    pools: dict[str, list[dict[str, Any]]] = {}
    for realm_index in range(len(REALMS)):
        tiers = artifact_realm_tiers_for_index(realm_index)
        pools[str(realm_index)] = [
            {
                "tier_min": tiers[0],
                "tier_max": tiers[-1],
                "grade": "",
                "attribute": "",
                "name": "",
                "weight": 1,
            }
        ]
    return pools


def _tier_range(tier_min: str = "", tier_max: str = "") -> list[str]:
    order = list(ARTIFACT_REALM_BOUND_TIERS)
    start = order.index(tier_min) if tier_min in order else 0
    end = order.index(tier_max) if tier_max in order else len(order) - 1
    if start > end:
        start, end = end, start
    return order[start : end + 1]


def _artifact_pool_candidates(entry: dict[str, Any], tier: str = "", grade: str = "") -> list[dict[str, Any]]:
    try:
        realm_index = max(0, min(len(REALMS) - 1, int(entry.get("realm_index", 0))))
    except (TypeError, ValueError):
        realm_index = 0
    tiers = [str(item) for item in entry.get("tiers", []) if str(item) in ARTIFACT_REALM_BOUND_TIERS]
    if not tiers:
        exact_tier = str(entry.get("tier") or "")
        tiers = [exact_tier] if exact_tier in ARTIFACT_REALM_BOUND_TIERS else _tier_range(str(entry.get("tier_min") or ""), str(entry.get("tier_max") or ""))
    if tier and tier in ARTIFACT_REALM_BOUND_TIERS:
        tiers = [item for item in tiers if item == tier]
    grade_filter = str(grade or entry.get("grade") or "")
    grades = [grade_filter] if grade_filter in GRADE_RANKS else list(GRADE_ORDER)
    attribute = str(entry.get("attribute") or "")
    name = str(entry.get("name") or "")
    candidates = []
    for info in ARTIFACT_REALM_CATALOG:
        if int(info.get("realm_index", -1)) != realm_index:
            continue
        if str(info.get("tier")) not in tiers:
            continue
        if str(info.get("grade")) not in grades:
            continue
        if attribute and str(info.get("attribute")) != attribute:
            continue
        if name and str(info.get("name")) != name:
            continue
        candidates.append(info)
    return candidates


def configured_artifact_drop_entries() -> list[dict[str, Any]]:
    pools = ARTIFACT_DROP_POOLS or {int(key): value for key, value in default_artifact_drop_pools().items()}
    entries: list[dict[str, Any]] = []
    for realm_index, rows in pools.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            entry = dict(row)
            entry["realm_index"] = int(realm_index)
            entries.append(entry)
    return entries


def draw_configured_artifact_reward(
    tier: str = "",
    grade: str = "",
    rng: Optional[random.Random] = None,
) -> dict[str, Any]:
    entries = configured_artifact_drop_entries()

    def weighted_entries(use_tier: str, use_grade: str) -> list[tuple[tuple[dict[str, Any], list[dict[str, Any]]], float]]:
        result: list[tuple[tuple[dict[str, Any], list[dict[str, Any]]], float]] = []
        for entry in entries:
            candidates = _artifact_pool_candidates(entry, use_tier, use_grade)
            if not candidates:
                continue
            try:
                weight = float(entry.get("weight", 1))
            except (TypeError, ValueError):
                weight = 1.0
            if weight > 0:
                result.append(((entry, candidates), weight))
        return result

    weighted = weighted_entries(str(tier or ""), str(grade or ""))
    if not weighted:
        weighted = weighted_entries("", "")
    if weighted:
        _entry, candidates = weighted_choice_rng(weighted, rng) if rng is not None else weighted_choice(weighted)
        pick = rng.choice(candidates) if rng is not None else random.choice(candidates)
        return artifact_info_to_reward(dict(pick))
    fallback_realm = rng.randrange(len(REALMS)) if rng is not None else random.randrange(len(REALMS))
    fallback_tiers = artifact_realm_tiers_for_index(fallback_realm)
    fallback_tier = str(tier or (rng.choice(fallback_tiers) if rng is not None else random.choice(fallback_tiers)))
    fallback_grade = str(grade or (rng.choice(GRADE_ORDER) if rng is not None else random.choice(GRADE_ORDER)))
    return make_realm_artifact_reward(fallback_realm, fallback_tier, fallback_grade, rng)


def _category_weight_pairs(value: Any) -> list[tuple[str, float]]:
    entries: list[tuple[str, float]] = []
    if isinstance(value, dict):
        raw_entries = value.items()
    elif isinstance(value, list):
        raw_entries = []
        for item in value:
            if isinstance(item, dict):
                raw_entries.append((item.get("category"), item.get("weight", 1)))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                raw_entries.append((item[0], item[1]))
    else:
        raw_entries = []
    for category, weight in raw_entries:
        category_text = reward_category({"category": str(category or "")})
        try:
            weight_value = float(weight)
        except (TypeError, ValueError):
            continue
        if category_text and weight_value > 0:
            entries.append((category_text, weight_value))
    return entries


def apply_admin_config(config: dict[str, Any]) -> None:
    equipment_rules = config.get("equipment_rules", {}) if isinstance(config, dict) else {}
    if isinstance(equipment_rules, dict):
        tier_default = equipment_rules.get("tier_default_realm", {})
        if isinstance(tier_default, dict):
            for tier, realm_index in tier_default.items():
                if str(tier) in TIER_RANKS:
                    try:
                        ARTIFACT_TIER_DEFAULT_REALM[str(tier)] = max(0, min(len(REALMS) - 1, int(realm_index)))
                    except (TypeError, ValueError):
                        continue
        unlocks = equipment_rules.get("realm_tier_unlocks", {})
        if isinstance(unlocks, dict):
            for realm_key, tiers in unlocks.items():
                try:
                    realm_index = max(0, min(len(REALMS) - 1, int(realm_key)))
                except (TypeError, ValueError):
                    continue
                if isinstance(tiers, list):
                    allowed = [str(tier) for tier in tiers if str(tier) in TIER_RANKS and str(tier) != "仙帝兵"]
                    if allowed:
                        ARTIFACT_REALM_TIER_UNLOCKS[realm_index] = allowed
        power_base = equipment_rules.get("artifact_power_base", {})
        if isinstance(power_base, dict):
            for tier, value in power_base.items():
                if str(tier) in ARTIFACT_POWER_BASE:
                    try:
                        ARTIFACT_POWER_BASE[str(tier)] = max(1, int(value))
                    except (TypeError, ValueError):
                        continue
        realm_power_base = equipment_rules.get("artifact_realm_power_base", {})
        if isinstance(realm_power_base, dict):
            for realm_key, value in realm_power_base.items():
                try:
                    realm_index = max(0, min(len(REALMS) - 1, int(realm_key)))
                    ARTIFACT_REALM_POWER_BASE[realm_index] = max(1, int(value))
                except (TypeError, ValueError):
                    continue
        tier_ratio = equipment_rules.get("artifact_tier_power_ratio", {})
        if isinstance(tier_ratio, dict):
            for tier, value in tier_ratio.items():
                if str(tier) in ARTIFACT_TIER_POWER_RATIO:
                    try:
                        ARTIFACT_TIER_POWER_RATIO[str(tier)] = max(0.01, float(value))
                    except (TypeError, ValueError):
                        continue
        grade_ratio = equipment_rules.get("artifact_grade_ratio", {})
        if isinstance(grade_ratio, dict):
            for grade, value in grade_ratio.items():
                if str(grade) in ARTIFACT_GRADE_RATIO:
                    try:
                        ARTIFACT_GRADE_RATIO[str(grade)] = max(0.1, float(value))
                    except (TypeError, ValueError):
                        continue
        upgrade_rate = equipment_rules.get("artifact_immortal_upgrade_rate")
        if upgrade_rate is not None:
            try:
                globals()["ARTIFACT_IMMORTAL_UPGRADE_RATE"] = max(0.0, min(1.0, float(upgrade_rate)))
            except (TypeError, ValueError):
                pass
        drop_pools = equipment_rules.get("artifact_drop_pools", {})
        ARTIFACT_DROP_POOLS.clear()
        if isinstance(drop_pools, dict):
            for realm_key, rows in drop_pools.items():
                try:
                    realm_index = max(0, min(len(REALMS) - 1, int(realm_key)))
                except (TypeError, ValueError):
                    continue
                if not isinstance(rows, list):
                    continue
                cleaned_rows: list[dict[str, Any]] = []
                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    tier_min = str(item.get("tier_min") or item.get("tier") or "")
                    tier_max = str(item.get("tier_max") or item.get("tier") or "")
                    if tier_min not in ARTIFACT_REALM_BOUND_TIERS:
                        tier_min = ""
                    if tier_max not in ARTIFACT_REALM_BOUND_TIERS:
                        tier_max = ""
                    grade = str(item.get("grade") or "")
                    if grade not in GRADE_RANKS:
                        grade = ""
                    attribute = normalize_root_attribute(str(item.get("attribute") or ""))
                    if attribute not in ARTIFACT_ATTRIBUTES:
                        attribute = ""
                    name = str(item.get("name") or "").strip()
                    if name and name not in ARTIFACT_REALM_INFOS_BY_NAME:
                        name = ""
                    tiers = [str(tier) for tier in item.get("tiers", []) if str(tier) in ARTIFACT_REALM_BOUND_TIERS] if isinstance(item.get("tiers"), list) else []
                    try:
                        weight = max(0.01, float(item.get("weight", 1)))
                    except (TypeError, ValueError):
                        weight = 1.0
                    cleaned = {
                        "tier_min": tier_min,
                        "tier_max": tier_max,
                        "grade": grade,
                        "attribute": attribute,
                        "name": name,
                        "weight": weight,
                    }
                    if tiers:
                        cleaned["tiers"] = tiers
                    cleaned_rows.append(cleaned)
                if cleaned_rows:
                    ARTIFACT_DROP_POOLS[realm_index] = cleaned_rows
    mystic_config = config.get("mystic", {}) if isinstance(config, dict) else {}
    signin_config = config.get("signin", {}) if isinstance(config, dict) else {}
    MYSTIC_CATEGORY_WEIGHTS.clear()
    MYSTIC_DROP_OVERRIDES.clear()
    MYSTIC_ENABLED_TYPES.clear()
    MYSTIC_ENABLED_HIGH_RISK_TYPES.clear()
    globals()["MYSTIC_FISHING_OPTION_RATE"] = 0.05
    globals()["SIGNIN_EXTRA_FISHING_CHANCE_RATE"] = 0.10
    if isinstance(mystic_config, dict):
        try:
            globals()["MYSTIC_FISHING_OPTION_RATE"] = max(0.0, min(1.0, float(mystic_config.get("fishing_option_rate", MYSTIC_FISHING_OPTION_RATE))))
        except (TypeError, ValueError):
            pass
        enabled_types = mystic_config.get("enabled_types", list(MYSTIC_REALM_TYPES))
        if isinstance(enabled_types, list):
            MYSTIC_ENABLED_TYPES.update(str(item) for item in enabled_types if str(item) in MYSTIC_REALM_TYPES)
        else:
            MYSTIC_ENABLED_TYPES.update(MYSTIC_REALM_TYPES)
        enabled_high_risk = mystic_config.get("enabled_high_risk_types", list(HIGH_RISK_MYSTIC_REALM_TYPES))
        if isinstance(enabled_high_risk, list):
            MYSTIC_ENABLED_HIGH_RISK_TYPES.update(str(item) for item in enabled_high_risk if str(item) in HIGH_RISK_MYSTIC_REALM_TYPES)
        else:
            MYSTIC_ENABLED_HIGH_RISK_TYPES.update(HIGH_RISK_MYSTIC_REALM_TYPES)
        category_weights = mystic_config.get("category_weights", {})
        if isinstance(category_weights, dict):
            for realm_type, value in category_weights.items():
                pairs = _category_weight_pairs(value)
                if pairs:
                    MYSTIC_CATEGORY_WEIGHTS[str(realm_type)] = pairs
        drop_overrides = mystic_config.get("drop_overrides", {})
        if isinstance(drop_overrides, dict):
            for realm_type, rewards in drop_overrides.items():
                if isinstance(rewards, list):
                    MYSTIC_DROP_OVERRIDES[str(realm_type)] = [dict(item) for item in rewards if isinstance(item, dict)]
    else:
        MYSTIC_ENABLED_TYPES.update(MYSTIC_REALM_TYPES)
        MYSTIC_ENABLED_HIGH_RISK_TYPES.update(HIGH_RISK_MYSTIC_REALM_TYPES)
    if isinstance(signin_config, dict):
        try:
            globals()["SIGNIN_EXTRA_FISHING_CHANCE_RATE"] = max(0.0, min(1.0, float(signin_config.get("extra_fishing_chance_rate", SIGNIN_EXTRA_FISHING_CHANCE_RATE))))
        except (TypeError, ValueError):
            pass
DUEL_ACTIONS = {
    "金": "剑气横生，锋芒逼人",
    "木": "青藤绕阵，生机绵长",
    "水": "水幕化潮，攻守相生",
    "火": "烈焰成环，炽意冲霄",
    "土": "厚土为垒，稳如山岳",
    "雷": "雷光乍裂，瞬息破势",
    "\u51b0": "\u5bd2\u971c\u5c01\u8def\uff0c\u5bf8\u6b65\u96be\u79fb",
    "\u98ce": "\u98ce\u5f71\u65e0\u5b9a\uff0c\u5148\u624b\u593a\u52bf",
    "\u6697": "\u5e7d\u5f71\u5165\u5c40\uff0c\u6740\u673a\u85cf\u950b",
    "\u5149": "\u660e\u5149\u7834\u90aa\uff0c\u7167\u5f7b\u5fc3\u9b54",
    "\u5251": "\u5251\u9aa8\u5929\u6210\uff0c\u4e00\u7ebf\u65a9\u5c40",
    "\u836f": "\u836f\u9999\u5316\u6d77\uff0c\u751f\u673a\u4e0d\u7edd",
    "\u7384\u9634": "\u7384\u9634\u5982\u6f6e\uff0c\u5bd2\u610f\u9501\u9b42",
    "\u7384\u9633": "\u7384\u9633\u70bc\u8840\uff0c\u70bd\u706b\u51b2\u9704",
    "\u7a7a": "\u7a7a\u95f4\u8f6c\u6298\uff0c\u8eab\u5f62\u96be\u5bfb",
    "\u65f6": "\u65f6\u5149\u4e00\u7f13\uff0c\u80dc\u8d1f\u5df2\u5206",
    "\u5148\u5929\u9053\u4f53": "\u9053\u97f5\u81ea\u751f\uff0c\u4e07\u6cd5\u76f8\u968f",
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
    purity: int = 100
    sources: Optional[list[str]] = None
    mutated: bool = False
    trait: str = ""
    source_purities: Optional[dict[str, int]] = None

    @property
    def display_name(self) -> str:
        attr_name = root_attribute_name(self.attribute)
        if self.tier == "\u53d8\u5f02\u7075\u6839":
            return f"\u53d8\u5f02\u7075\u6839{self.grade}{attr_name}"
        return f"{self.tier}{self.grade}{attr_name}"

    @property
    def color(self) -> str:
        return ATTRIBUTE_COLORS.get(self.attribute, "#8f8a83")

    @property
    def source_attributes(self) -> set[str]:
        if self.attribute == "\u5148\u5929\u9053\u4f53":
            return set(BASE_FIVE_ELEMENTS)
        sources = set(str(item) for item in (self.sources or []) if item)
        if sources:
            return sources
        if self.attribute in BASE_FIVE_ELEMENTS:
            return {self.attribute}
        if self.attribute in MUTATION_ROOT_SOURCES:
            return set(MUTATION_ROOT_SOURCES[self.attribute][0])
        if self.attribute in SPECIAL_ROOT_SOURCES:
            return set(SPECIAL_ROOT_SOURCES[self.attribute])
        return {self.attribute}

    @property
    def is_mutation(self) -> bool:
        return bool(self.mutated or self.tier == "\u53d8\u5f02\u7075\u6839" or self.attribute not in BASE_FIVE_ELEMENTS)

    @property
    def detail_name(self) -> str:
        suffix = f"\u7eaf\u5ea6{max(1, min(100, int(self.purity)))}%"
        if self.is_mutation and self.sources:
            parts = []
            purities = self.source_purities or {}
            for source in self.sources:
                source_purity = int(purities.get(source, self.purity))
                parts.append(f"{source}{source_purity}%")
            suffix += f"\uff0c\u7531{'+'.join(parts)}\u5148\u5929\u5f02\u53d8"
        return f"{self.display_name}\uff08{suffix}\uff09"

    @property
    def progress_required(self) -> int:
        tier_base = {
            "\u53d8\u5f02\u7075\u6839": 82,
            "\u5929\u9636": 100,
            "\u5730\u9636": 115,
            "\u7384\u9636": 135,
            "\u9ec4\u9636": 155,
            "\u51e1\u54c1": 180,
        }.get(self.tier, 155)
        grade_extra = {
            "\u6781\u54c1": 0,
            "\u4e0a\u54c1": 8,
            "\u4e2d\u54c1": 18,
            "\u4e0b\u54c1": 28,
        }.get(self.grade, 18)
        purity_adjust = int((80 - max(1, min(100, int(self.purity)))) * 0.55)
        return max(55, tier_base + grade_extra + purity_adjust)

    @property
    def exp_gain_range(self) -> tuple[int, int]:
        low = 6 + self.tier_rank * 3 + self.grade_rank
        high = 10 + self.tier_rank * 5 + self.grade_rank * 2
        if self.tier == "\u53d8\u5f02\u7075\u6839":
            low += 3
            high += 6
        purity_bonus = int((max(1, min(100, int(self.purity))) - 70) / 10)
        low = max(1, low + purity_bonus)
        high = max(low, high + purity_bonus * 2)
        return low, high

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "tier_rank": self.tier_rank,
            "grade": self.grade,
            "grade_rank": self.grade_rank,
            "attribute": self.attribute,
            "purity": max(1, min(100, int(self.purity))),
            "sources": list(self.sources or []),
            "mutated": bool(self.is_mutation),
            "trait": self.trait or ROOT_TRAITS.get(self.attribute, ""),
            "source_purities": {str(key): max(1, min(100, int(value))) for key, value in dict(self.source_purities or {}).items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Root:
        tier = str(data["tier"])
        if tier == "\u8def\u4eba\u7532":
            tier = "\u51e1\u54c1"
        attribute = normalize_root_attribute(str(data.get("attribute", "\u91d1")))
        is_mutated = bool(data.get("mutated", False)) or attribute not in BASE_FIVE_ELEMENTS or tier == "\u53d8\u5f02\u7075\u6839"
        if is_mutated:
            tier = "\u53d8\u5f02\u7075\u6839"
        grade = str(data.get("grade", "\u6781\u54c1" if is_mutated else "\u4e2d\u54c1"))
        sources = data.get("sources")
        if not isinstance(sources, list) or not sources:
            sources = root_default_sources(attribute)
        source_purities = data.get("source_purities")
        if not isinstance(source_purities, dict):
            source_purities = {}
        purity = max(1, min(100, int(data.get("purity", 96 if is_mutated else 72))))
        if is_mutated:
            purity = max(92, purity)
            source_purities = {str(source): max(90, int(source_purities.get(source, purity))) for source in sources}
        return cls(
            tier=tier,
            tier_rank=TIER_RANKS.get(tier, int(data.get("tier_rank", TIER_RANKS.get(tier, 0)))),
            grade=grade,
            grade_rank=int(data.get("grade_rank", GRADE_RANKS.get(grade, 1))),
            attribute=attribute,
            purity=purity,
            sources=[str(item) for item in sources if item],
            mutated=is_mutated,
            trait=str(data.get("trait") or ROOT_TRAITS.get(attribute, "")),
            source_purities={str(key): max(1, min(100, int(value))) for key, value in dict(source_purities).items()},
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
            parts.append(f"+{self.fishing_chances} 次垂钓")
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
class ExpApplyResult:
    applied: int = 0
    leveled_realms: int = 0
    overflow: int = 0
    spirit_liquid: int = 0

    def __iter__(self):
        yield self.applied
        yield self.leveled_realms


@dataclass
class UserRecord:
    user_id: str
    root: Optional[Root] = None
    acquired_roots: Optional[list[dict[str, Any]]] = None
    sign_count: int = 0
    total_exp: int = 0
    realm_index: int = 0
    realm_exp: int = 0
    last_sign_date: Optional[str] = None
    last_encounter_date: Optional[str] = None
    fishing_chances: int = 0
    pending_fishing: int = 0
    pending_exp: int = 0
    spirit_liquid: int = 0
    bottleneck_days: int = 0
    bottleneck_realm_index: Optional[int] = None
    last_bottleneck_date: Optional[str] = None
    rewards: Optional[list[dict[str, Any]]] = None
    equipped_artifact: Optional[dict[str, Any]] = None
    equipped_artifacts: Optional[dict[str, dict[str, Any]]] = None
    equipped_talisman: Optional[dict[str, Any]] = None
    equipped_method: Optional[dict[str, Any]] = None
    equipped_array: Optional[dict[str, Any]] = None
    equipped_puppet: Optional[dict[str, Any]] = None
    planted_spirit_plant: Optional[dict[str, Any]] = None
    array_proficiency: Optional[dict[str, int]] = None
    array_layers: Optional[dict[str, int]] = None
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
    combat_race: Optional[str] = None
    physique: Optional[str] = None
    special_abilities: Optional[list[str]] = None
    method_layers: Optional[dict[str, int]] = None
    method_proficiency: Optional[dict[str, int]] = None
    life_artifact: Optional[dict[str, Any]] = None
    immortal_seeds: Optional[list[dict[str, Any]]] = None
    equipped_immortal_seed: Optional[dict[str, Any]] = None
    immortal_conversion_days: int = 0
    last_immortal_conversion_date: Optional[str] = None
    last_failed_mystic_realm: Optional[dict[str, Any]] = None
    mystic_boss_successes: Optional[dict[str, list[str]]] = None
    mystic_boss_daily_date: Optional[str] = None
    mystic_boss_daily_attempts: int = 0
    mystic_boss_daily_bonus: int = 0
    mystic_boss_week_key: Optional[str] = None
    mystic_boss_week_attempts: int = 0
    mystic_boss_week_claimed: Optional[list[int]] = None

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
        return realm_progress_required(self.root, self.realm_index)

    @property
    def roots(self) -> list[Root]:
        result = []
        if self.root:
            result.append(self.root)
        result.extend(self.extra_roots or [])
        return result

    @property
    def root_attributes(self) -> set[str]:
        attrs = {root.attribute for root in self.roots}
        for root in self.roots:
            attrs.update(root.source_attributes)
        for root in normalize_acquired_roots(self):
            attr = str(root.get("attribute") or "")
            if attr:
                attrs.add(attr)
        return attrs

    @property
    def root_summary(self) -> str:
        if self.root is None:
            return "\u672a\u89c9\u9192\u7075\u6839"
        if self.root.tier == "\u53d8\u5f02\u7075\u6839":
            return f"{self.root.detail_name}\uff5c\u5148\u5929\u5f02\u7980"
        parts = [root.detail_name for root in self.roots]
        return f"{' + '.join(parts)}\uff5c\u4e94\u884c{len(self.roots)}\u7075\u6839\u91cf\u5316\u8bc4\u5b9a"

    @property
    def is_peak_aptitude(self) -> bool:
        return bool(
            self.root
            and (
                (self.root.tier == "\u5929\u9636" and self.root.grade == "\u6781\u54c1")
                or self.root.tier == "\u53d8\u5f02\u7075\u6839"
            )
        )

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
            "acquired_roots": self.acquired_roots or [],
            "sign_count": self.sign_count,
            "total_exp": self.total_exp,
            "realm_index": self.realm_index,
            "realm_exp": self.realm_exp,
            "last_sign_date": self.last_sign_date,
            "last_encounter_date": self.last_encounter_date,
            "fishing_chances": self.fishing_chances,
            "pending_fishing": self.pending_fishing,
            "pending_exp": self.pending_exp,
            "spirit_liquid": self.spirit_liquid,
            "bottleneck_days": self.bottleneck_days,
            "bottleneck_realm_index": self.bottleneck_realm_index,
            "last_bottleneck_date": self.last_bottleneck_date,
            "rewards": self.rewards or [],
            "equipped_artifact": self.equipped_artifact or None,
            "equipped_artifacts": self.equipped_artifacts or {},
            "equipped_talisman": self.equipped_talisman or None,
            "equipped_method": self.equipped_method or None,
            "equipped_array": self.equipped_array or None,
            "equipped_puppet": self.equipped_puppet or None,
            "planted_spirit_plant": self.planted_spirit_plant or None,
            "array_proficiency": self.array_proficiency or {},
            "array_layers": self.array_layers or {},
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
            "combat_race": self.combat_race,
            "physique": self.physique,
            "special_abilities": self.special_abilities or [],
            "method_layers": self.method_layers or {},
            "method_proficiency": self.method_proficiency or {},
            "life_artifact": self.life_artifact or None,
            "immortal_seeds": self.immortal_seeds or [],
            "equipped_immortal_seed": self.equipped_immortal_seed or None,
            "immortal_conversion_days": self.immortal_conversion_days,
            "last_immortal_conversion_date": self.last_immortal_conversion_date,
            "last_failed_mystic_realm": self.last_failed_mystic_realm or None,
            "mystic_boss_successes": self.mystic_boss_successes or {},
            "mystic_boss_daily_date": self.mystic_boss_daily_date,
            "mystic_boss_daily_attempts": self.mystic_boss_daily_attempts,
            "mystic_boss_daily_bonus": self.mystic_boss_daily_bonus,
            "mystic_boss_week_key": self.mystic_boss_week_key,
            "mystic_boss_week_attempts": self.mystic_boss_week_attempts,
            "mystic_boss_week_claimed": self.mystic_boss_week_claimed or [],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserRecord:
        root_data = data.get("root")
        return cls(
            user_id=str(data["user_id"]),
            root=Root.from_dict(root_data) if root_data else None,
            acquired_roots=[
                dict(root)
                for root in data.get("acquired_roots", [])
                if isinstance(root, dict)
            ],
            sign_count=int(data.get("sign_count", 0)),
            total_exp=int(data.get("total_exp", 0)),
            realm_index=int(data.get("realm_index", 0)),
            realm_exp=int(data.get("realm_exp", 0)),
            last_sign_date=data.get("last_sign_date"),
            last_encounter_date=data.get("last_encounter_date"),
            fishing_chances=int(data.get("fishing_chances", 0)),
            pending_fishing=int(data.get("pending_fishing", 0)),
            pending_exp=int(data.get("pending_exp", 0)),
            spirit_liquid=int(data.get("spirit_liquid", 0)),
            bottleneck_days=int(data.get("bottleneck_days", 0)),
            bottleneck_realm_index=(
                int(data["bottleneck_realm_index"])
                if data.get("bottleneck_realm_index") is not None
                else None
            ),
            last_bottleneck_date=(str(data["last_bottleneck_date"]) if data.get("last_bottleneck_date") else None),
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
            combat_race=(str(data["combat_race"]) if data.get("combat_race") else None),
            physique=(str(data["physique"]) if data.get("physique") else None),
            special_abilities=[str(item) for item in (data.get("special_abilities") or []) if item],
            method_layers={
                str(key): int(value)
                for key, value in dict(data.get("method_layers") or {}).items()
            },
            method_proficiency={
                str(key): int(value)
                for key, value in dict(data.get("method_proficiency") or {}).items()
            },
            equipped_artifacts={
                str(key): dict(value)
                for key, value in dict(data.get("equipped_artifacts") or {}).items()
                if isinstance(value, dict)
            },
            equipped_talisman=(
                dict(data["equipped_talisman"])
                if isinstance(data.get("equipped_talisman"), dict)
                else None
            ),
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
            array_layers={
                str(key): int(value)
                for key, value in dict(data.get("array_layers", {})).items()
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
            life_artifact=(dict(data["life_artifact"]) if isinstance(data.get("life_artifact"), dict) else None),
            immortal_seeds=[dict(item) for item in data.get("immortal_seeds", []) if isinstance(item, dict)],
            equipped_immortal_seed=(dict(data["equipped_immortal_seed"]) if isinstance(data.get("equipped_immortal_seed"), dict) else None),
            immortal_conversion_days=int(data.get("immortal_conversion_days", 0)),
            last_immortal_conversion_date=(str(data["last_immortal_conversion_date"]) if data.get("last_immortal_conversion_date") else None),
            last_failed_mystic_realm=(dict(data["last_failed_mystic_realm"]) if isinstance(data.get("last_failed_mystic_realm"), dict) else None),
            mystic_boss_successes={
                str(key): [str(item) for item in value if item]
                for key, value in dict(data.get("mystic_boss_successes") or {}).items()
                if isinstance(value, list)
            },
            mystic_boss_daily_date=(str(data["mystic_boss_daily_date"]) if data.get("mystic_boss_daily_date") else None),
            mystic_boss_daily_attempts=int(data.get("mystic_boss_daily_attempts", 0)),
            mystic_boss_daily_bonus=int(data.get("mystic_boss_daily_bonus", 0)),
            mystic_boss_week_key=(str(data["mystic_boss_week_key"]) if data.get("mystic_boss_week_key") else None),
            mystic_boss_week_attempts=int(data.get("mystic_boss_week_attempts", 0)),
            mystic_boss_week_claimed=[int(item) for item in data.get("mystic_boss_week_claimed", []) if str(item).isdigit()],
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
    overflow_exp: int = 0
    spirit_liquid_gain: int = 0
    bottleneck_days: int = 0
    leveled_realms: int = 0
    gained_fishing_chance: bool = False
    fishing_chances_gained: int = 0
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


def root_default_sources(attribute: str) -> list[str]:
    attribute = normalize_root_attribute(attribute)
    if attribute == "\u5148\u5929\u9053\u4f53":
        return list(BASE_FIVE_ELEMENTS)
    if attribute in BASE_FIVE_ELEMENTS:
        return [attribute]
    if attribute in MUTATION_ROOT_SOURCES:
        return list(random.choice(MUTATION_ROOT_SOURCES[attribute]))
    if attribute in SPECIAL_ROOT_SOURCES:
        return list(SPECIAL_ROOT_SOURCES[attribute])
    return [attribute]


def root_grade_from_score(score: int) -> str:
    if score >= 92:
        return "\u6781\u54c1"
    if score >= 78:
        return "\u4e0a\u54c1"
    if score >= 62:
        return "\u4e2d\u54c1"
    return "\u4e0b\u54c1"


def ordinary_root_rating(purities: Sequence[int]) -> tuple[str, str]:
    values = [max(1, min(100, int(value))) for value in purities] or [50]
    count = len(values)
    avg_purity = sum(values) / count
    max_purity = max(values)
    score = int(avg_purity + (max_purity - avg_purity) * 0.35 - max(0, count - 1) * 8)
    if score >= 92:
        tier = "\u5929\u9636"
    elif score >= 78:
        tier = "\u5730\u9636"
    elif score >= 64:
        tier = "\u7384\u9636"
    elif score >= 48:
        tier = "\u9ec4\u9636"
    else:
        tier = "\u51e1\u54c1"
    return tier, root_grade_from_score(score)


def root_purity_for(tier: str, grade: str, count: int = 1, primary: bool = True, attribute: str = "") -> int:
    if tier == "\u53d8\u5f02\u7075\u6839" or attribute not in BASE_FIVE_ELEMENTS:
        low, high = 94, 100
    else:
        base_ranges = {
            "\u5929\u9636": (88, 100),
            "\u5730\u9636": (76, 92),
            "\u7384\u9636": (62, 82),
            "\u9ec4\u9636": (46, 68),
            "\u51e1\u54c1": (30, 56),
        }
        low, high = base_ranges.get(tier, (45, 72))
        low += GRADE_RANKS.get(grade, 1) * 2
        high += GRADE_RANKS.get(grade, 1) * 2
        penalty = max(0, count - 1) * (7 if primary else 10)
        if not primary:
            low -= 8
            high -= 6
        low -= penalty
        high -= penalty
    return max(18, min(100, random.randint(max(18, low), max(20, high))))


def make_root(
    tier: str,
    grade: str,
    attribute: str,
    purity: Optional[int] = None,
    sources: Optional[list[str]] = None,
    mutated: Optional[bool] = None,
    source_purities: Optional[dict[str, int]] = None,
) -> Root:
    attribute = normalize_root_attribute(attribute)
    source_list = list(sources) if sources is not None else root_default_sources(attribute)
    is_mutated = bool(mutated if mutated is not None else tier == "\u53d8\u5f02\u7075\u6839" or attribute not in BASE_FIVE_ELEMENTS)
    if is_mutated:
        tier = "\u53d8\u5f02\u7075\u6839"
    root_purity = purity if purity is not None else root_purity_for(tier, grade, attribute=attribute)
    if is_mutated:
        root_purity = max(92, int(root_purity))
        source_purities = {source: max(90, int((source_purities or {}).get(source, root_purity))) for source in source_list}
    return Root(
        tier=tier,
        tier_rank=TIER_RANKS[tier],
        grade=grade,
        grade_rank=GRADE_RANKS.get(grade, 1),
        attribute=attribute,
        purity=root_purity,
        sources=source_list,
        mutated=is_mutated,
        trait=ROOT_TRAITS.get(attribute, ""),
        source_purities=source_purities or {},
    )


def draw_mutation_root() -> Root:
    attribute = weighted_choice(
        [
            ("\u96f7", 24),
            ("\u51b0", 20),
            ("\u98ce", 18),
            ("\u6697", 8),
            ("\u5149", 8),
            ("\u5251", 5),
            ("\u836f", 5),
            ("\u7384\u9634", 4),
            ("\u7384\u9633", 4),
            ("\u7a7a", 1.2),
            ("\u65f6", 1.0),
            ("\u5148\u5929\u9053\u4f53", 0.6),
            ("混沌", 0.8),
        ]
    )
    sources = root_default_sources(attribute)
    purity = random.randint(95, 100) if attribute in {"\u7a7a", "\u65f6", "\u5148\u5929\u9053\u4f53", "混沌"} else random.randint(92, 100)
    source_purities = {source: random.randint(max(90, purity - 3), 100) for source in sources}
    grade = root_grade_from_score(purity)
    return make_root("\u53d8\u5f02\u7075\u6839", grade, attribute, purity=purity, sources=sources, mutated=True, source_purities=source_purities)


def ordinary_root_count() -> int:
    return weighted_choice([(1, 11), (2, 24), (3, 32), (4, 23), (5, 10)])


def ordinary_purity_values(count: int) -> list[int]:
    ranges = {
        1: (82, 99),
        2: (68, 92),
        3: (54, 82),
        4: (40, 68),
        5: (28, 58),
    }
    low, high = ranges.get(max(1, min(5, count)), (45, 72))
    values = [random.randint(low, high) for _ in range(count)]
    values.sort(reverse=True)
    return values


def draw_ordinary_roots() -> list[Root]:
    count = ordinary_root_count()
    attributes = random.sample(list(BASE_FIVE_ELEMENTS), k=count)
    purities = ordinary_purity_values(count)
    tier, grade = ordinary_root_rating(purities)
    return [
        make_root(tier, grade, attribute, purity=purity, sources=[attribute], mutated=False, source_purities={attribute: purity})
        for attribute, purity in zip(attributes, purities)
    ]


def draw_roots() -> list[Root]:
    if random.random() < 0.075:
        return [draw_mutation_root()]
    return draw_ordinary_roots()


def draw_root() -> Root:
    return draw_roots()[0]


def normalize_root_profile(record: UserRecord) -> bool:
    if not record.root:
        return False
    changed = False
    roots = record.roots
    mutation_roots = [root for root in roots if root.attribute not in BASE_FIVE_ELEMENTS or root.tier == "\u53d8\u5f02\u7075\u6839" or root.mutated]
    if mutation_roots:
        root = mutation_roots[0]
        root.tier = "\u53d8\u5f02\u7075\u6839"
        root.tier_rank = TIER_RANKS[root.tier]
        root.grade = root.grade if root.grade in GRADE_RANKS else root_grade_from_score(max(92, int(root.purity)))
        root.grade_rank = GRADE_RANKS.get(root.grade, 3)
        root.purity = max(92, int(root.purity or 96))
        root.sources = root.sources or root_default_sources(root.attribute)
        root.source_purities = {source: max(90, int((root.source_purities or {}).get(source, root.purity))) for source in root.sources}
        root.mutated = True
        root.trait = root.trait or ROOT_TRAITS.get(root.attribute, "")
        record.root = root
        if record.extra_roots:
            record.extra_roots = []
            changed = True
        return True or changed

    seen: set[str] = set()
    clean_roots: list[Root] = []
    for root in roots:
        if root.attribute not in BASE_FIVE_ELEMENTS or root.attribute in seen:
            changed = True
            continue
        seen.add(root.attribute)
        root.sources = [root.attribute]
        root.source_purities = {root.attribute: max(1, min(100, int(root.purity or 60)))}
        root.mutated = False
        clean_roots.append(root)
    if not clean_roots:
        clean_roots = [make_root("\u51e1\u54c1", "\u4e0b\u54c1", random.choice(BASE_FIVE_ELEMENTS), purity=45)]
        changed = True
    tier, grade = ordinary_root_rating([int(root.purity) for root in clean_roots])
    for root in clean_roots:
        if root.tier != tier or root.grade != grade:
            changed = True
        root.tier = tier
        root.tier_rank = TIER_RANKS[tier]
        root.grade = grade
        root.grade_rank = GRADE_RANKS[grade]
    record.root = clean_roots[0]
    record.extra_roots = clean_roots[1:]
    return changed


def ensure_legacy_extra_roots(record: UserRecord) -> bool:
    return normalize_root_profile(record)


def max_root_purity(record: UserRecord, attribute: Optional[str] = None) -> int:
    attribute = normalize_root_attribute(attribute) if attribute is not None else None
    if not record.root:
        return 0
    acquired = normalize_acquired_roots(record)
    if attribute is None:
        innate = [int(root.purity) for root in record.roots]
        postnatal = [int(root.get("purity", 0)) for root in acquired]
        return max(innate + postnatal, default=0)
    candidates = []
    for root in record.roots:
        if root.attribute == "先天道体" or root.attribute == attribute or attribute in root.source_attributes:
            if root.source_purities and attribute in root.source_purities:
                candidates.append(int(root.source_purities[attribute]))
            else:
                candidates.append(int(root.purity))
    for root in acquired:
        if root.get("attribute") == attribute:
            candidates.append(int(root.get("purity", 0)))
    return max(candidates, default=0)

def root_purity_multiplier(record: UserRecord, attribute: Optional[str] = None) -> float:
    purity = max_root_purity(record, attribute)
    if purity <= 0:
        return 1.0
    base = 0.85 + purity / 100
    if record.root and record.root.tier == "\u53d8\u5f02\u7075\u6839":
        base += 0.18
    return base


def realm_progress_required(root: Optional[Root], realm_index: int) -> int:
    base = root.progress_required if root is not None else 100
    multiplier = 2 ** max(0, int(realm_index))
    return max(1, int(base) * multiplier)


def cumulative_realm_exp(root: Optional[Root], realm_index: int) -> int:
    return sum(realm_progress_required(root, index) for index in range(max(0, int(realm_index))))


def _realm_index(name: str, default: int) -> int:
    try:
        return REALMS.index(name)
    except ValueError:
        return default


def breakthrough_requirement_key_for_realm_index(realm_index: int) -> Optional[int]:
    index = int(realm_index)
    if index >= len(REALMS) - 1:
        return None
    fake_index = _realm_index("假仙境", len(REALMS))
    true_index = _realm_index("真仙境", len(REALMS))
    if index == fake_index:
        return None
    if fake_index < true_index and index >= true_index:
        return index - 1
    return index


def breakthrough_source_realm_index(requirement_index: int) -> int:
    key = int(requirement_index)
    fake_index = _realm_index("假仙境", len(REALMS))
    true_index = _realm_index("真仙境", len(REALMS))
    if fake_index < true_index and key >= true_index - 1:
        key += 1
    return max(0, min(len(REALMS) - 1, key))


def breakthrough_target_realm_index(requirement_index: int) -> int:
    source_index = breakthrough_source_realm_index(requirement_index)
    return max(0, min(len(REALMS) - 1, source_index + 1))


def breakthrough_target_realm(requirement_index: int, requirement: Optional[dict[str, Any]] = None) -> str:
    target_index = breakthrough_target_realm_index(requirement_index)
    if 0 <= target_index < len(REALMS):
        return REALMS[target_index]
    if requirement is not None:
        return str(requirement.get("target") or "下一境")
    return "下一境"


def current_breakthrough_requirement(record: UserRecord) -> Optional[dict[str, Any]]:
    key = breakthrough_requirement_key_for_realm_index(record.realm_index)
    if key is None:
        return None
    return BREAKTHROUGH_REQUIREMENTS.get(key)


def current_breakthrough_target_realm(record: UserRecord) -> str:
    key = breakthrough_requirement_key_for_realm_index(record.realm_index)
    if key is None:
        return "下一境"
    return breakthrough_target_realm(key, BREAKTHROUGH_REQUIREMENTS.get(key))

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


def parse_cultivation_lock_until(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value)
    try:
        if "T" in text:
            return datetime.fromisoformat(text)
        return datetime.combine(date.fromisoformat(text[:10]), datetime.min.time())
    except ValueError:
        return None


def lock_reference_datetime(until: datetime, value: Optional[str], current: Optional[Any] = None) -> datetime:
    if isinstance(current, datetime):
        now = current
    elif isinstance(current, date) and "T" not in str(value or ""):
        now = datetime.combine(current, datetime.min.time())
    else:
        now = datetime.now(until.tzinfo) if until.tzinfo else datetime.now()
    if until.tzinfo is not None and now.tzinfo is None:
        return now.replace(tzinfo=until.tzinfo)
    if until.tzinfo is None and now.tzinfo is not None:
        return now.replace(tzinfo=None)
    return now


def is_cultivation_locked(record: UserRecord, today: Optional[Any] = None) -> bool:
    until = parse_cultivation_lock_until(record.cultivation_lock_until)
    if until is None:
        return False
    if lock_reference_datetime(until, record.cultivation_lock_until, today) >= until:
        record.cultivation_lock_until = None
        return False
    return True


def cultivation_lock_text(record: UserRecord, today: Optional[Any] = None) -> str:
    if not is_cultivation_locked(record, today):
        return ""
    until = parse_cultivation_lock_until(record.cultivation_lock_until)
    if until and "T" in str(record.cultivation_lock_until):
        return f"禁修至 {until.strftime('%Y-%m-%d %H:%M')}"
    return f"禁修至 {record.cultivation_lock_until}"


def lock_cultivation(
    record: UserRecord,
    today: Optional[Any] = None,
    days: int = 1,
    hours: Optional[int] = None,
    minutes: Optional[int] = None,
) -> str:
    if minutes is not None or hours is not None:
        if isinstance(today, datetime):
            now = today
        elif isinstance(today, date):
            now = datetime.combine(today, datetime.now().time())
        else:
            now = datetime.now()
        delta = timedelta(minutes=max(1, int(minutes))) if minutes is not None else timedelta(hours=max(1, int(hours or 1)))
        until = now + delta
        record.cultivation_lock_until = until.isoformat(timespec="minutes")
        return cultivation_lock_text(record, now)
    lock_date = today.date() if isinstance(today, datetime) else (today or date.today())
    until = lock_date + timedelta(days=max(1, days))
    record.cultivation_lock_until = until.isoformat()
    return cultivation_lock_text(record, today)



def fake_immortal_realm_index() -> int:
    return REALMS.index("\u5047\u4ed9\u5883") if "\u5047\u4ed9\u5883" in REALMS else len(REALMS)


def true_immortal_realm_index() -> int:
    return REALMS.index("\u771f\u4ed9\u5883") if "\u771f\u4ed9\u5883" in REALMS else len(REALMS) - 1


def is_fake_immortal_conversion(record: UserRecord) -> bool:
    return record.root is not None and record.realm_index == fake_immortal_realm_index()


def progress_fake_immortal_conversion(record: UserRecord, today: date) -> tuple[bool, str]:
    if not is_fake_immortal_conversion(record):
        return False, ""
    today_text = today.isoformat()
    if record.last_immortal_conversion_date != today_text:
        record.last_immortal_conversion_date = today_text
        record.immortal_conversion_days = min(7, int(record.immortal_conversion_days or 0) + 1)
    if record.immortal_conversion_days >= 7:
        fake_index = fake_immortal_realm_index()
        mark = (record.realm_marks or {}).get(str(fake_index))
        record.realm_index = true_immortal_realm_index()
        if mark:
            set_realm_mark(record, record.realm_index, mark)
        record.realm_exp = 0
        record.immortal_conversion_days = 0
        record.last_immortal_conversion_date = None
        message = "七日仙元力转化已成，灵力词条改为仙元力，正式踏入真仙境。"
        if mark:
            message += f"真仙境品相继承假仙境：{mark}。"
        return True, message
    return True, f"仙元力转化中 {record.immortal_conversion_days}/7，此期间签到不增加修为。"

def update_bottleneck_tracking(record: UserRecord, today: Optional[date] = None, overflow: int = 0) -> int:
    if not is_breakthrough_bottleneck(record):
        record.bottleneck_days = 0
        record.bottleneck_realm_index = None
        record.last_bottleneck_date = None
        return 0
    if record.bottleneck_realm_index != record.realm_index:
        record.bottleneck_realm_index = record.realm_index
        record.bottleneck_days = 0
        record.last_bottleneck_date = None
    if overflow > 0 and today is not None:
        today_text = today.isoformat()
        if record.last_bottleneck_date != today_text:
            record.bottleneck_days += 1
            record.last_bottleneck_date = today_text
    return record.bottleneck_days


def reset_bottleneck_state(record: UserRecord) -> None:
    # 精纯灵液是瓶颈期沉淀资产，突破或散功只重置瓶颈计数，不清空灵液。
    record.bottleneck_days = 0
    record.bottleneck_realm_index = None
    record.last_bottleneck_date = None

def convert_overflow_to_spirit_liquid(record: UserRecord, overflow: int) -> int:
    if overflow <= 0:
        return 0
    liquid = max(1, int(overflow * 0.5))
    record.spirit_liquid += liquid
    return liquid


def apply_exp(record: UserRecord, amount: int, today: Optional[date] = None) -> ExpApplyResult:
    result = ExpApplyResult()
    if amount <= 0:
        return result
    if is_cultivation_locked(record):
        return result
    if is_fake_immortal_conversion(record):
        return result
    if is_breakthrough_bottleneck(record):
        result.overflow = amount
        result.spirit_liquid = convert_overflow_to_spirit_liquid(record, amount)
        update_bottleneck_tracking(record, today, amount)
        return result
    remaining = amount
    while remaining > 0:
        if record.realm_index >= len(REALMS) - 1:
            room = max(0, record.progress_required - record.realm_exp)
            gained = min(remaining, room)
            record.realm_exp += gained
            record.total_exp += gained
            result.applied += gained
            remaining -= gained
            if remaining > 0:
                result.overflow += remaining
                result.spirit_liquid += convert_overflow_to_spirit_liquid(record, remaining)
                update_bottleneck_tracking(record, today, remaining)
            break
        room = max(0, record.progress_required - record.realm_exp)
        if room <= 0:
            if current_breakthrough_requirement(record):
                result.overflow += remaining
                result.spirit_liquid += convert_overflow_to_spirit_liquid(record, remaining)
                update_bottleneck_tracking(record, today, remaining)
                break
            record.realm_exp = 0
            record.realm_index += 1
            result.leveled_realms += 1
            update_bottleneck_tracking(record)
            continue
        gained = min(remaining, room)
        record.realm_exp += gained
        record.total_exp += gained
        result.applied += gained
        remaining -= gained
        if record.realm_exp < record.progress_required:
            update_bottleneck_tracking(record)
            break
        if current_breakthrough_requirement(record):
            if remaining > 0:
                result.overflow += remaining
                result.spirit_liquid += convert_overflow_to_spirit_liquid(record, remaining)
            update_bottleneck_tracking(record, today, remaining)
            break
        record.realm_exp = 0
        record.realm_index += 1
        result.leveled_realms += 1
        update_bottleneck_tracking(record)
    return result


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


def recycle_price(reward: dict[str, Any]) -> int:
    return max(1, int(reward_price(reward) * 0.6))


def market_offer_price(reward: dict[str, Any]) -> int:
    return max(1, int(recycle_price(reward) * 1.5))


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



def artifact_tiers_for_realm(realm_index: int) -> list[str]:
    index = max(0, min(len(REALMS) - 1, int(realm_index)))
    return list(ARTIFACT_REALM_TIER_UNLOCKS.get(index) or ARTIFACT_REALM_TIER_UNLOCKS.get(0) or ["凡品", "黄阶", "玄阶", "地阶", "天阶"])


def artifact_realm_for_tier(tier: str, record: Optional[UserRecord] = None, preferred_realm_index: Optional[int] = None) -> int:
    tier_text = str(tier or "凡品")
    if preferred_realm_index is not None:
        try:
            preferred = max(0, min(len(REALMS) - 1, int(preferred_realm_index)))
            if tier_text in artifact_tiers_for_realm(preferred):
                return preferred
        except (TypeError, ValueError):
            pass
    if record is not None and tier_text in artifact_tiers_for_realm(record.realm_index):
        return max(0, min(len(REALMS) - 1, int(record.realm_index)))
    return max(0, min(len(REALMS) - 1, int(ARTIFACT_TIER_DEFAULT_REALM.get(tier_text, TIER_REALM_REQUIREMENT.get(tier_text, 0)))))


def apply_artifact_realm_metadata(reward: dict[str, Any], record: Optional[UserRecord] = None) -> None:
    if reward_category(reward) != ARTIFACT_CATEGORY:
        return
    if str(reward.get("tier")) == "仙帝兵" or is_unique_reward_name(reward_name(reward)):
        return
    catalog_info = ARTIFACT_REALM_INFOS_BY_NAME.get(reward_name(reward))
    if catalog_info:
        realm_index = int(catalog_info.get("realm_index", 0))
        reward["tier"] = str(catalog_info.get("tier", reward.get("tier", "凡品")))
        reward["grade"] = str(catalog_info.get("grade", reward.get("grade", "下品")))
        reward["category"] = ARTIFACT_CATEGORY
        reward["realm_index"] = realm_index
        reward["min_realm_index"] = realm_index
        reward["required_attribute"] = str(catalog_info.get("attribute", reward.get("required_attribute", "")))
        reward["artifact_family"] = str(catalog_info.get("artifact_family", "realm_bound"))
        if catalog_info.get("description"):
            reward["description"] = str(catalog_info.get("description"))
        if catalog_info.get("source"):
            reward["source"] = str(catalog_info.get("source"))
        return
    explicit = reward.get("realm_index")
    if explicit is None:
        explicit = reward.get("min_realm_index")
    if explicit is None and record is None:
        return
    realm_index = artifact_realm_for_tier(str(reward.get("tier", "凡品")), record, explicit)
    reward["realm_index"] = realm_index
    reward["min_realm_index"] = realm_index
    reward.setdefault("artifact_family", "realm_bound")


def artifact_realm_label(reward: dict[str, Any]) -> str:
    try:
        index = int(reward.get("realm_index", reward.get("min_realm_index", -1)))
    except (TypeError, ValueError):
        return ""
    if index < 0 or index >= len(REALMS):
        return ""
    return realm_short_name(REALMS[index])
def item_required_realm_index(reward: dict[str, Any]) -> int:
    explicit = reward.get("min_realm_index")
    if explicit is None and reward_category(reward) == ARTIFACT_CATEGORY:
        explicit = reward.get("realm_index")
    if explicit is not None:
        try:
            return max(0, min(len(REALMS) - 1, int(explicit)))
        except (TypeError, ValueError):
            pass
    tier = str(reward.get("tier", "凡品"))
    if reward_category(reward) == ARTIFACT_CATEGORY:
        return max(0, min(len(REALMS) - 1, int(ARTIFACT_TIER_DEFAULT_REALM.get(tier, TIER_REALM_REQUIREMENT.get(tier, 0)))))
    return TIER_REALM_REQUIREMENT.get(tier, 0)


def can_buy_reward(record: UserRecord, reward: dict[str, Any]) -> tuple[bool, str]:
    required_index = item_required_realm_index(reward)
    if reward_category(reward) != ARTIFACT_CATEGORY and required_index > record.realm_index + 2:
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


def make_realm_artifact_reward(
    realm_index: int,
    tier: str,
    grade: str,
    rng: Optional[random.Random] = None,
    preferred_attribute: Optional[str] = None,
) -> dict[str, Any]:
    realm = max(0, min(len(REALMS) - 1, int(realm_index)))
    tier_text = str(tier or "凡品")
    allowed_tiers = artifact_tiers_for_realm(realm)
    if tier_text not in allowed_tiers:
        tier_text = "仙阶" if tier_text == "仙阶" and "仙阶" in allowed_tiers else allowed_tiers[-1]
    grade_text = str(grade or "下品") if str(grade or "") in GRADE_RANKS else "下品"
    candidates = artifact_catalog_entries(realm, tier_text, grade_text, preferred_attribute)
    if not candidates:
        candidates = artifact_catalog_entries(realm, tier_text, grade_text)
    if not candidates:
        candidates = artifact_catalog_entries(realm)
    if not candidates:
        return {"tier": tier_text, "grade": grade_text, "category": ARTIFACT_CATEGORY, "name": "无名灵器", "realm_index": realm, "min_realm_index": realm}
    chooser = rng.choice if rng is not None else random.choice
    return artifact_info_to_reward(dict(chooser(candidates)))


def shop_items_for_date(date_text: str, record: Optional[UserRecord] = None) -> list[dict[str, Any]]:
    seed = f"{date_text}:{getattr(record, 'user_id', '')}:{getattr(record, 'realm_index', '')}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    pool = [(reward, float(reward[5])) for reward in FISHING_REWARDS if reward[2] != "仙缘"]
    items = []
    realm_index = int(record.realm_index) if record is not None else 0
    for _ in range(8):
        tier, grade, category, name, description, _ = weighted_choice_rng(pool, rng)
        if category == ARTIFACT_CATEGORY:
            item = draw_configured_artifact_reward(tier, grade, rng)
        else:
            item = {"tier": tier, "grade": grade, "category": category, "name": name, "description": description}
        item = normalize_reward(item, record)
        item["price"] = reward_price(item)
        items.append(item)
    return items

def buy_shop_item(record: UserRecord, item_index: int, date_text: str) -> tuple[bool, str]:
    items = shop_items_for_date(date_text, record)
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
    price = recycle_price(result)
    record.spirit_stones += price
    extra = ""
    if category == ARTIFACT_CATEGORY:
        signature = reward_signature(result)
        source_uid = reward_instance_uid(result)
        remove_equipped_artifact_by_signature(record, signature, source_uid)
        removed = prune_broken_artifact_roots(record, signature, source_uid)
        if removed:
            extra = f"\n该灵器所系 {removed} 条器灵根随器离身而失效。"
    return True, f"出售 {reward_display_name(result)}，获得 {spirit_stone_text(price)}，当前共有 {spirit_stone_text(record.spirit_stones)}。{extra}"


def reward_category(reward: Optional[dict[str, Any]]) -> str:
    category = str((reward or {}).get("category", ""))
    if category == LEGACY_SPECIAL_ABILITY_CATEGORY:
        return SPECIAL_ABILITY_CATEGORY
    if category == LEGACY_IMMORTAL_SEED_CATEGORY:
        return IMMORTAL_SEED_CATEGORY
    return category


def reward_name(reward: Optional[dict[str, Any]]) -> str:
    return canonical_item_name(str((reward or {}).get("name", "")))


_REWARD_NAME_INFERENCE_CACHE: list[str] | None = None


def known_reward_names_for_inference() -> list[str]:
    global _REWARD_NAME_INFERENCE_CACHE
    if _REWARD_NAME_INFERENCE_CACHE is not None:
        return _REWARD_NAME_INFERENCE_CACHE
    names: set[str] = set()
    for _tier, _grade, _category, name, _description, _weight in FISHING_REWARDS:
        if name:
            names.add(canonical_item_name(str(name)))
    for item in ARTIFACT_REALM_CATALOG:
        name = canonical_item_name(str(item.get("name") or ""))
        if name:
            names.add(name)
    names.update(canonical_item_name(str(name)) for name in EMPEROR_ARTIFACT_INFOS if name)
    names.update(canonical_item_name(str(name)) for name in IMMORTAL_SEED_INFOS if name)
    names.update(canonical_item_name(str(name)) for name in ARTIFACT_REFINING_RECIPES if name)
    names.update(canonical_item_name(str(name)) for name in ITEM_ATTRIBUTE_BY_NAME if name)
    _REWARD_NAME_INFERENCE_CACHE = sorted((name for name in names if name), key=len, reverse=True)
    return _REWARD_NAME_INFERENCE_CACHE


def infer_reward_name_from_description(reward: dict[str, Any]) -> str:
    description = str(reward.get("description") or "").strip()
    if not description:
        return ""
    for name in known_reward_names_for_inference():
        if description.startswith(name):
            return name
    category = reward_category(reward)
    template = REWARD_DESCRIPTIONS.get(category)
    if template and "{name}" in template:
        prefix, suffix = template.split("{name}", 1)
        if prefix and suffix and description.startswith(prefix):
            end = description.find(suffix, len(prefix))
            if end > len(prefix):
                return canonical_item_name(description[len(prefix) : end])
        if suffix:
            end = description.find(suffix)
            if end > 0:
                return canonical_item_name(description[:end])
    for marker in (
        "出自",
        "灵光内敛",
        "玄妙难言",
        "药香沉稳",
        "阵纹流转",
        "灵性充盈",
        "朱纹未散",
        "机关精巧",
        "生机盎然",
        "灵气充足",
        "来历不明",
        "气息古怪",
        "入口温和",
        "中藏着",
        "妖力凝成",
    ):
        index = description.find(marker)
        if index > 0:
            return canonical_item_name(description[:index])
    return ""


def default_reward_name_for_category(category: str) -> str:
    if category == ARTIFACT_CATEGORY:
        return "无名灵器"
    return "无名灵物"


def _needs_empty_reward_name_repair(value: dict[str, Any]) -> bool:
    if reward_name(value):
        return False
    return any(str(value.get(key) or "").strip() for key in ("category", "description", "tier", "grade"))


def _repair_empty_reward_name(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    if not _needs_empty_reward_name_repair(value):
        return value
    repaired = dict(value)
    name = infer_reward_name_from_description(repaired)
    repaired["name"] = canonical_item_name(name or default_reward_name_for_category(reward_category(repaired)))
    return repaired


def sanitize_user_record_data(data: dict[str, Any]) -> dict[str, Any]:
    UserRecord.from_dict(data)
    rewards = data.get("rewards")
    if isinstance(rewards, list):
        data["rewards"] = [
            _repair_empty_reward_name(item) if isinstance(item, dict) else item
            for item in rewards
        ]
    for key in (
        "equipped_artifact",
        "equipped_talisman",
        "equipped_method",
        "equipped_array",
        "equipped_puppet",
        "planted_spirit_plant",
        "life_artifact",
        "equipped_immortal_seed",
    ):
        if isinstance(data.get(key), dict):
            data[key] = _repair_empty_reward_name(data[key])
    equipped_artifacts = data.get("equipped_artifacts")
    if isinstance(equipped_artifacts, dict):
        data["equipped_artifacts"] = {
            str(slot): _repair_empty_reward_name(item) if isinstance(item, dict) else item
            for slot, item in equipped_artifacts.items()
        }
    immortal_seeds = data.get("immortal_seeds")
    if isinstance(immortal_seeds, list):
        data["immortal_seeds"] = [
            _repair_empty_reward_name(item) if isinstance(item, dict) else item
            for item in immortal_seeds
        ]
    return data



def is_emperor_artifact_name(name: str) -> bool:
    return str(name or "") in EMPEROR_ARTIFACT_INFOS


def is_unique_reward_name(name: str) -> bool:
    return str(name or "") in UNIQUE_REWARD_NAMES


def is_unique_reward(reward: dict[str, Any] | None) -> bool:
    return bool(reward and is_unique_reward_name(reward_name(reward)) and not reward.get("replica"))


def apply_reward_metadata(reward: dict[str, Any]) -> dict[str, Any]:
    name = reward_name(reward)
    if name in EMPEROR_ARTIFACT_INFOS:
        reward["category"] = ARTIFACT_CATEGORY
        reward["tier"] = "仙帝兵"
        reward.setdefault("grade", "\u6781\u54c1")
        reward["unique"] = not bool(reward.get("replica"))
        reward["min_realm_index"] = max(int(reward.get("min_realm_index", 0) or 0), ARTIFACT_TIER_DEFAULT_REALM.get("仙帝兵", 13))
        info = EMPEROR_ARTIFACT_INFOS[name]
        reward.setdefault(
            "description",
            f"{info.get('creator')}留下的仙帝兵，材质：{info.get('material')}。专属技：{info.get('skill')}。",
        )
    elif name in IMMORTAL_SEED_INFOS:
        reward["category"] = IMMORTAL_SEED_CATEGORY
        reward.setdefault("tier", "\u4ed9\u9636")
        reward.setdefault("grade", "\u4e0a\u54c1")
        reward["unique"] = name in UNIQUE_REWARD_NAMES and not bool(reward.get("replica"))
        reward["min_realm_index"] = max(int(reward.get("min_realm_index", 0) or 0), REALMS.index("\u771f\u4ed9\u5883"))
        reward.setdefault("description", IMMORTAL_SEED_INFOS[name].get("effect", "仙源凝着清澈灵机。"))
    elif is_unique_reward_name(name):
        reward["unique"] = not bool(reward.get("replica"))
        reward.setdefault("tier", "\u4ed9\u9636")
        reward.setdefault("grade", "\u6781\u54c1")
        reward["min_realm_index"] = max(int(reward.get("min_realm_index", 0) or 0), 8)
    if name in {"翠雷云竹剑", "玄金雷枝剑"}:
        reward["category"] = ARTIFACT_CATEGORY
        reward.setdefault("required_attribute", "\u96f7")
        reward.setdefault("min_realm_index", 2 if name == "翠雷云竹剑" else 3)
    if name == "玄金列星剑阵":
        reward["category"] = ARRAY_CATEGORY
        reward.setdefault("required_attribute", "\u91d1")
        reward.setdefault("min_realm_index", 5)
    if reward.get("replica"):
        reward["unique"] = False
        if str(reward.get("tier")) == "仙帝兵":
            reward["tier"] = "\u4ed9\u9636"
    return reward


def make_unique_replica(reward: dict[str, Any]) -> dict[str, Any]:
    replica = dict(reward)
    replica["replica"] = True
    replica["unique"] = False
    name = reward_name(replica)
    if name and not name.endswith("仿制品"):
        replica["name"] = f"{name}仿制品"
    if str(replica.get("tier")) == "仙帝兵":
        replica["tier"] = "\u4ed9\u9636"
        replica.setdefault("grade", "\u4e2d\u54c1")
    replica["description"] = f"{reward_display_name(reward)}的仿制品，得一缕真形道韵，但不具备全局唯一性。"
    return apply_reward_metadata(replica)

def reward_required_attribute(reward: dict[str, Any]) -> Optional[str]:
    required = reward.get("required_attribute")
    if required:
        normalized = normalize_root_attribute(str(required))
        reward["required_attribute"] = normalized
        return normalized
    required = ITEM_ATTRIBUTE_BY_NAME.get(reward_name(reward))
    if required:
        required = normalize_root_attribute(required)
        reward["required_attribute"] = required
    return required


def normalize_reward(reward: dict[str, Any], record: Optional[UserRecord] = None) -> dict[str, Any]:
    tier = str(reward.get("tier", "凡品"))
    if tier == "路人甲":
        tier = "凡品"
    reward["tier"] = tier
    reward.setdefault("grade", "中品")
    reward.setdefault("category", "杂物")
    reward["category"] = reward_category(reward)
    name = reward_name(reward) or infer_reward_name_from_description(reward)
    reward["name"] = canonical_item_name(name or default_reward_name_for_category(reward_category(reward)))
    reward.setdefault(
        "description",
        REWARD_DESCRIPTIONS.get(reward_category(reward), "{name}气息不明。").format(name=reward_name(reward)),
    )
    apply_reward_metadata(reward)
    apply_demon_core_metadata(reward)
    if reward_category(reward) == METHOD_CATEGORY:
        scrub_method_layer_metadata(reward)
    apply_artifact_realm_metadata(reward, record)
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

def scrub_method_layer_metadata(reward: dict[str, Any]) -> None:
    for key in ("layer", "layers", "max_layer", "initial_layer", "method_layer", "method_layers"):
        reward.pop(key, None)
    description = str(reward.get("description") or "")
    if description:
        description = re.sub(r"第\s*[一二三四五六七八九十百千万\d]+\s*层", "", description)
        description = re.sub(r"[一二三四五六七八九十百千万\d]+\s*层", "", description)
        description = re.sub(r"[；;，,。]?\s*层数[:：]?\s*[一二三四五六七八九十百千万\d]+", "", description)
        reward["description"] = re.sub(r"\s+", " ", description).strip() or REWARD_DESCRIPTIONS.get(METHOD_CATEGORY, "{name}气息不明。").format(name=reward_name(reward))


def growth_has_unlimited_deduction(item: Optional[dict[str, Any]]) -> bool:
    return bool(item and str(item.get("tier")) == "仙阶" and str(item.get("grade")) == "极品")


def next_growth_quality(tier: str, grade: str, tiers: Sequence[str]) -> Optional[tuple[str, str]]:
    tier_text = str(tier or "凡品")
    grade_text = str(grade or "下品")
    if tier_text not in tiers:
        tier_text = "凡品"
    if grade_text not in GRADE_ORDER:
        grade_text = "下品"
    if tier_text == "仙阶" and grade_text == "极品":
        return None
    grade_index = GRADE_ORDER.index(grade_text)
    if grade_index < len(GRADE_ORDER) - 1:
        return tier_text, GRADE_ORDER[grade_index + 1]
    tier_index = list(tiers).index(tier_text)
    if tier_index < len(tiers) - 1:
        return list(tiers)[tier_index + 1], GRADE_ORDER[0]
    return None


def method_layer_cap(method: Optional[dict[str, Any]]) -> int:
    if not method:
        return 0
    return METHOD_UNLIMITED_LAYER_MAX if growth_has_unlimited_deduction(method) else METHOD_LAYER_STEP


def method_layer_cap_text(method: Optional[dict[str, Any]]) -> str:
    return "无限" if growth_has_unlimited_deduction(method) else str(METHOD_LAYER_STEP)


def array_layer_cap(array: Optional[dict[str, Any]]) -> int:
    if not array:
        return 0
    return ARRAY_UNLIMITED_LAYER_MAX if growth_has_unlimited_deduction(array) else ARRAY_LAYER_STEP


def array_layer_cap_text(array: Optional[dict[str, Any]]) -> str:
    return "无限" if growth_has_unlimited_deduction(array) else str(ARRAY_LAYER_STEP)


def same_named_growth_item(left: Optional[dict[str, Any]], right: Optional[dict[str, Any]], category: str) -> bool:
    return bool(left and right and reward_category(left) == category and reward_category(right) == category and reward_name(left) == reward_name(right))


def sync_equipped_growth_item(record: UserRecord, category: str, old_key: str, item: dict[str, Any]) -> None:
    if category == METHOD_CATEGORY and record.equipped_method:
        if reward_signature(record.equipped_method) == old_key or same_named_growth_item(record.equipped_method, item, category):
            record.equipped_method = dict(item)
    if category == ARRAY_CATEGORY and record.equipped_array:
        if reward_signature(record.equipped_array) == old_key or same_named_growth_item(record.equipped_array, item, category):
            record.equipped_array = dict(item)


def ensure_method_tracking(record: UserRecord, method: dict[str, Any]) -> None:
    if record.method_layers is None:
        record.method_layers = {}
    if record.method_proficiency is None:
        record.method_proficiency = {}
    key = reward_signature(method)
    record.method_layers.setdefault(key, 1)
    record.method_layers[key] = max(1, min(method_layer_cap(method), int(record.method_layers.get(key, 1) or 1)))
    record.method_proficiency.setdefault(key, 0)


def ensure_array_tracking(record: UserRecord, array: dict[str, Any]) -> None:
    if record.array_proficiency is None:
        record.array_proficiency = {}
    if record.array_layers is None:
        record.array_layers = {}
    key = reward_signature(array)
    record.array_layers.setdefault(key, 1)
    record.array_layers[key] = max(1, min(array_layer_cap(array), int(record.array_layers.get(key, 1) or 1)))
    if key not in record.array_proficiency:
        legacy = 0
        if record.equipped_method:
            legacy_key = reward_signature(record.equipped_method)
            legacy = int(record.array_proficiency.get(legacy_key, 0) or 0)
        record.array_proficiency[key] = max(0, legacy)


def migrate_tracking_key(mapping: Optional[dict[str, int]], old_key: str, new_key: str, value: Optional[int] = None, keep_max: bool = True) -> int:
    if mapping is None:
        return int(value or 0)
    old_value = int(mapping.pop(old_key, 0) or 0)
    next_value = int(value if value is not None else old_value)
    if keep_max:
        next_value = max(int(mapping.get(new_key, 0) or 0), next_value, old_value)
    mapping[new_key] = next_value
    return next_value


def set_growth_reward_note(reward: dict[str, Any], item: dict[str, Any], old_display: str, layer: int, quality_up: bool, category: str) -> None:
    reward["tier"] = str(item.get("tier", reward.get("tier", "凡品")))
    reward["grade"] = str(item.get("grade", reward.get("grade", "下品")))
    reward["category"] = category
    reward["name"] = reward_name(item)
    reward["growth_deduction"] = True
    reward["growth_quality_up"] = bool(quality_up)
    reward["growth_layer"] = int(layer)
    reward["growth_deduction_text"] = (
        f"重复获得，已由{old_display}推演进阶为{reward_display_name(item)}第{layer}层"
        if quality_up
        else f"重复获得，已推演至第{layer}层"
    )
    if category == METHOD_CATEGORY:
        reward["method_deduction"] = True
    if category == ARRAY_CATEGORY:
        reward["array_deduction"] = True


def advance_method_by_duplicate(record: UserRecord, method: dict[str, Any], incoming: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    ensure_method_tracking(record, method)
    old_key = reward_signature(method)
    old_display = reward_display_name(method)
    current_layer = method_layer(record, method) or 1
    new_layer = current_layer + 1
    quality_up = False
    if not growth_has_unlimited_deduction(method) and current_layer >= METHOD_LAYER_STEP:
        next_quality = next_growth_quality(str(method.get("tier", "凡品")), str(method.get("grade", "下品")), METHOD_GROWTH_TIERS)
        if next_quality is not None:
            method["tier"], method["grade"] = next_quality
            method["price"] = reward_price(method)
            new_layer = 1
            quality_up = True
    new_key = reward_signature(method)
    if record.method_layers is None:
        record.method_layers = {}
    if record.method_proficiency is None:
        record.method_proficiency = {}
    migrate_tracking_key(record.method_layers, old_key, new_key, new_layer, keep_max=False)
    migrate_tracking_key(record.method_proficiency, old_key, new_key, 0 if quality_up else None, keep_max=not quality_up)
    sync_equipped_growth_item(record, METHOD_CATEGORY, old_key, method)
    if incoming is not None:
        set_growth_reward_note(incoming, method, old_display, new_layer, quality_up, METHOD_CATEGORY)
    return method


def array_layer(record: UserRecord, array: Optional[dict[str, Any]]) -> int:
    if not array:
        return 0
    key = reward_signature(array)
    current = int((record.array_layers or {}).get(key, 0) or 0)
    return max(1, min(array_layer_cap(array), current or 1))


def array_proficiency_cap(array: Optional[dict[str, Any]], layer: Optional[int] = None) -> int:
    if not array:
        return 0
    tier = str(array.get("tier", "凡品"))
    current_layer = max(1, int(layer or 1))
    if tier == "仙阶":
        cap_multiplier = max(20.0, current_layer * 20.0)
    else:
        cap_multiplier = ARRAY_MULTIPLIER_CAP_BY_TIER.get(tier, 5.0)
    return max(0, int((cap_multiplier - 1.0) * 100))


def array_proficiency_value(record: UserRecord, array: Optional[dict[str, Any]] = None) -> int:
    item = array or record.equipped_array
    if not item:
        return 0
    ensure_array_tracking(record, item)
    key = reward_signature(item)
    value = int((record.array_proficiency or {}).get(key, 0) or 0)
    return max(0, min(array_proficiency_cap(item, array_layer(record, item)), value))


def advance_array_by_duplicate(record: UserRecord, array: dict[str, Any], incoming: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    ensure_array_tracking(record, array)
    old_key = reward_signature(array)
    old_display = reward_display_name(array)
    current_layer = array_layer(record, array) or 1
    current_proficiency = array_proficiency_value(record, array)
    new_layer = current_layer + 1
    quality_up = False
    if not growth_has_unlimited_deduction(array) and current_layer >= ARRAY_LAYER_STEP:
        next_quality = next_growth_quality(str(array.get("tier", "凡品")), str(array.get("grade", "下品")), ARRAY_GROWTH_TIERS)
        if next_quality is not None:
            array["tier"], array["grade"] = next_quality
            array["price"] = reward_price(array)
            new_layer = 1
            quality_up = True
    new_key = reward_signature(array)
    if record.array_layers is None:
        record.array_layers = {}
    if record.array_proficiency is None:
        record.array_proficiency = {}
    migrate_tracking_key(record.array_layers, old_key, new_key, new_layer, keep_max=False)
    migrated = migrate_tracking_key(record.array_proficiency, old_key, new_key, current_proficiency, keep_max=True)
    record.array_proficiency[new_key] = min(array_proficiency_cap(array, new_layer), migrated)
    sync_equipped_growth_item(record, ARRAY_CATEGORY, old_key, array)
    if incoming is not None:
        set_growth_reward_note(incoming, array, old_display, new_layer, quality_up, ARRAY_CATEGORY)
    return array


def ensure_unique_growth_rewards(record: UserRecord, category: str) -> None:
    if not record.rewards:
        return
    seen: dict[str, int] = {}
    unique_rewards: list[dict[str, Any]] = []
    for reward in record.rewards:
        normalized = normalize_reward(reward, record)
        if reward_category(normalized) != category:
            unique_rewards.append(normalized)
            continue
        name = reward_name(normalized)
        if name in seen:
            if category == METHOD_CATEGORY:
                advance_method_by_duplicate(record, unique_rewards[seen[name]], normalized)
            elif category == ARRAY_CATEGORY:
                advance_array_by_duplicate(record, unique_rewards[seen[name]], normalized)
            continue
        if category == METHOD_CATEGORY:
            ensure_method_tracking(record, normalized)
        elif category == ARRAY_CATEGORY:
            ensure_array_tracking(record, normalized)
        seen[name] = len(unique_rewards)
        unique_rewards.append(normalized)
    record.rewards = unique_rewards


def append_reward(record: UserRecord, reward: dict[str, Any]) -> None:
    if record.rewards is None:
        record.rewards = []
    normalized = normalize_reward(reward, record)
    category = reward_category(normalized)
    if category in {METHOD_CATEGORY, ARRAY_CATEGORY}:
        ensure_unique_growth_rewards(record, category)
        for index, existing in enumerate(record.rewards):
            existing = normalize_reward(existing, record)
            if same_named_growth_item(existing, normalized, category):
                if category == METHOD_CATEGORY:
                    record.rewards[index] = advance_method_by_duplicate(record, existing, normalized)
                else:
                    record.rewards[index] = advance_array_by_duplicate(record, existing, normalized)
                return
        if category == METHOD_CATEGORY:
            ensure_method_tracking(record, normalized)
        else:
            ensure_array_tracking(record, normalized)
    record.rewards.append(normalized)

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


def is_breakthrough_talisman_name(name: str) -> bool:
    if not name:
        return False
    for requirement in BREAKTHROUGH_REQUIREMENTS.values():
        if name not in set(requirement["items"]):
            continue
        return any(token in name for token in BREAKTHROUGH_TALISMAN_TOKENS)
    return False


def breakthrough_talisman_requirement(name: str) -> Optional[dict[str, Any]]:
    for realm_index, requirement in BREAKTHROUGH_REQUIREMENTS.items():
        if name in set(requirement["items"]) and is_breakthrough_talisman_name(name):
            return {"realm_index": realm_index, "target": breakthrough_target_realm(realm_index, requirement)}
    return None

PILL_BREAKTHROUGH_TOKENS = ("\u4e39", "\u4e38", "\u6563", "\u9732", "\u6db2", "\u5f15")


def is_pill_like_breakthrough_item(name: str) -> bool:
    if any(reward[3] == name and reward[2] == PILL_CATEGORY for reward in FISHING_REWARDS):
        return True
    return any(token in name for token in PILL_BREAKTHROUGH_TOKENS)


def high_tier_probability(days: int) -> float:
    if days <= 0:
        return 0.0
    return min(0.9, 0.3 + max(0, days - 1) * 0.2)


def tier_preference_weight(tier: str, days: int = 0) -> float:
    if days <= 0:
        return 1.0
    tier_rank = TIER_RANKS.get(tier, 0)
    if tier == "\u5929\u9636":
        return high_tier_probability(days)
    remaining = max(0.02, 1.0 - high_tier_probability(days))
    lower_weights = {"\u5730\u9636": 0.46, "\u7384\u9636": 0.28, "\u9ec4\u9636": 0.17, "\u51e1\u54c1": 0.09}
    return remaining * lower_weights.get(tier, max(0.02, tier_rank + 1))


def high_grade_multiplier(grade: str, days: int = 0) -> float:
    grade_rank = GRADE_RANKS.get(grade, 0)
    return float((grade_rank + 1) ** max(1, min(5, days + 1)))


def high_tier_named_reward_weight(reward: tuple[str, str, str, str, str, int], days: int = 0) -> float:
    tier, grade, _category, _name, _description, _weight = reward
    if days > 0:
        return max(0.001, tier_preference_weight(tier, days) * high_grade_multiplier(grade, days))
    score = 1 + TIER_RANKS.get(tier, 0) * 4 + GRADE_RANKS.get(grade, 0)
    return float(score**3)


def breakthrough_item_fishing_weight(name: str) -> float:
    return 4.0 if is_pill_like_breakthrough_item(name) else 1.0


def breakthrough_item_category(name: str) -> str:
    matches = [reward for reward in FISHING_REWARDS if reward[3] == name]
    if matches:
        categories = [str(reward[2]) for reward in matches]
        for preferred in (PILL_CATEGORY, TALISMAN_CATEGORY, CURIO_CATEGORY):
            if preferred in categories:
                return preferred
        return categories[0]
    if is_breakthrough_talisman_name(name):
        return TALISMAN_CATEGORY
    if is_pill_like_breakthrough_item(name):
        return PILL_CATEGORY
    return CURIO_CATEGORY


DEFAULT_BREAKTHROUGH_CAPS = {
    3: [9, 14, 19],
    4: [8, 12, 15, 19],
    5: [7, 10, 12, 15, 19],
}

BREAKTHROUGH_ITEM_QUALITY_CAPS = {
    "筑基丹": 8,
    "地脉筑基液": 13,
    "天道筑基露": 19,
    "小还丹": 7,
    "大还丹": 10,
    "金液丹": 11,
    "凝魄金丹": 15,
    "造化金丹": 19,
    "元婴丹": 8,
    "护婴丹": 12,
    "九窍化婴丹": 19,
    "问心丹": 8,
    "化神引": 12,
    "斩尘化神丹": 15,
    "化凡意境": 19,
    "破虚灵引": 10,
    "破虚丹": 13,
    "虚空灵髓": 19,
    "合道残章": 10,
    "合体丹": 13,
    "法身合契符": 19,
    "合道紫金丹": 14,
    "圆融道胎": 16,
    "大乘道果": 19,
    "渡劫令": 10,
    "避劫雷木": 19,
    "渡劫护命丹": 16,
    "仙元道砂": 12,
    "仙门符诏": 14,
    "真仙接引符": 19,
}


def breakthrough_item_requirement_info(name: str) -> Optional[tuple[int, int, int]]:
    for realm_index, requirement in BREAKTHROUGH_REQUIREMENTS.items():
        items = list(requirement.get("items", []))
        if name in items:
            return realm_index, items.index(name), len(items)
    return None


def breakthrough_item_quality_cap(name: str) -> int:
    if name in BREAKTHROUGH_ITEM_QUALITY_CAPS:
        return BREAKTHROUGH_ITEM_QUALITY_CAPS[name]
    info = breakthrough_item_requirement_info(name)
    if not info:
        return 19
    _realm_index, position, count = info
    caps = DEFAULT_BREAKTHROUGH_CAPS.get(count)
    if caps is None:
        caps = [int(7 + index * (12 / max(1, count - 1))) for index in range(count)]
        caps[-1] = 19
    return max(5, min(19, int(caps[max(0, min(position, len(caps) - 1))])))


def realm_quality_title_index(realm_index: int) -> int:
    index = int(realm_index)
    fake_index = _realm_index("假仙境", len(REALMS))
    true_index = _realm_index("真仙境", len(REALMS))
    if fake_index < true_index and index >= true_index:
        return index - 1
    return index


FOUNDATION_QUALITY_TITLES = ["普通筑基", "良好筑基", "优秀筑基", "无瑕道基", "天道筑基"]

REALM_QUALITY_TITLES = {
    3: ["一品金丹", "二品金丹", "三品金丹", "四品金丹", "五品金丹", "六品金丹", "七品金丹", "八品金丹", "九品金丹"],
    4: ["天命元婴", "无瑕元婴", "紫府元婴", "灵台元婴", "凡胎元婴"],
    5: ["星衡化神", "无垢化神", "神意化形", "凡念化神"],
    6: ["洞虚道体", "玄虚法身", "清虚灵体", "凡虚之身"],
    7: ["天人合一", "道体合真", "元神合契", "法身初合"],
    8: ["无上大乘", "圆融大乘", "清净大乘", "小乘道果"],
    9: ["九重雷劫", "七重雷劫", "五重雷劫", "三重雷劫"],
    10: ["无垢真仙", "玄妙真仙", "清灵真仙", "凡蜕真仙"],
    11: ["不朽金仙", "太玄金仙", "玉清金仙", "初证金仙"],
    12: ["太乙道果", "太乙玄光", "太乙清光", "太乙初果"],
    13: ["大罗无极", "大罗圆满", "大罗玄妙", "大罗初证"],
    14: ["混元圆满", "混元无瑕", "混元玄妙", "混元初证"],
    15: ["三尸尽斩", "二尸圆融", "一尸寄道", "半步准圣"],
    16: ["天道圣位", "功德圣人", "气运圣人", "伪圣道果"],
    17: ["自在混元", "无垢混元", "玄照混元", "初入混元"],
    18: ["无极道主", "无极真圣", "无极玄光", "无极初证"],
    19: ["执掌天道", "合道无缺", "天心圆融", "借天而行"],
    20: ["大道归一", "大道无缺", "大道玄同", "大道初契"],
    21: ["万道祖庭", "一道开天", "道祖法身", "初立道统"],
    22: ["半步无上", "命河将断", "因果将尽", "彼岸初望"],
    23: ["彼岸超脱", "命河不系", "因果不染", "初证超脱"],
    24: ["永恒唯一", "万劫不磨", "无量不朽", "永恒初印"],
    25: ["归真圆满", "归真澄照", "归真玄契", "归真初悟"],
    26: ["太初一炁", "太初玄章", "太初清印", "太初微芒"],
    27: ["鸿蒙无极", "鸿蒙道胎", "鸿蒙玄息", "鸿蒙初判"],
    28: ["玄黄不朽", "玄黄厚德", "玄黄灵枢", "玄黄初成"],
    29: ["无量真源", "无量净光", "无量法海", "无量初潮"],
    30: ["造化天成", "造化元炉", "造化灵机", "造化初萌"],
    31: ["太素无尘", "太素澄明", "太素玄形", "太素初凝"],
    32: ["太极归圆", "太极两仪", "太极玄衡", "太极初分"],
    33: ["无始归墟", "无始长明", "无始玄门", "无始初证"],
}


def _build_realm_quality_power() -> dict[str, int]:
    table: dict[str, int] = {}
    for index, title in enumerate(FOUNDATION_QUALITY_TITLES):
        table[title] = 80 + index * 55
    for realm_index, titles in REALM_QUALITY_TITLES.items():
        base = 220 + realm_index * 85
        count = len(titles)
        for position, title in enumerate(titles):
            table[title] = base + (count - position) * 45
    return table


REALM_QUALITY_POWER = _build_realm_quality_power()


def item_quality_score(item: Optional[dict[str, Any]]) -> int:
    if not item:
        return 0
    tier = str(item.get("tier") or "凡品")
    grade = str(item.get("grade") or "下品")
    return 1 + TIER_RANKS.get(tier, 0) * 4 + GRADE_RANKS.get(grade, 0)


def _quality_title_index(score: int, title_count: int) -> int:
    if title_count <= 1:
        return 0
    score = max(0, min(20, int(score)))
    if title_count >= 9:
        thresholds = [19, 17, 15, 13, 11, 9, 7, 5]
    elif title_count == 5:
        thresholds = [18, 14, 10, 5]
    else:
        thresholds = [18, 14, 10]
    for index, threshold in enumerate(thresholds[: max(0, title_count - 1)]):
        if score >= threshold:
            return index
    return title_count - 1


def quality_from_titles(item: dict[str, Any], titles: Sequence[str]) -> str:
    title_list = list(titles)
    if not title_list:
        return "道基未定"
    override = item.get("quality_cap_override")
    score = int(override) if override is not None else item_quality_score(item)
    return title_list[_quality_title_index(score, len(title_list))]


def foundation_quality(item: dict[str, Any]) -> str:
    cap_value = item.get("quality_cap_override")
    cap = int(cap_value) if cap_value is not None else breakthrough_item_quality_cap(reward_name(item))
    score = min(item_quality_score(item), cap)
    if score >= 18:
        return "天道筑基"
    if score >= 14:
        return "无瑕道基"
    if score >= 10:
        return "优秀筑基"
    if score >= 5:
        return "良好筑基"
    return "普通筑基"


def breakthrough_quality_relation_text() -> str:
    lines = [
        "【品相图鉴】",
        "突破道具名决定品相上限，品阶与品质只在该上限内提高实际结果。",
    ]
    for realm_index, requirement in BREAKTHROUGH_REQUIREMENTS.items():
        source_index = breakthrough_source_realm_index(realm_index)
        target_index = breakthrough_target_realm_index(realm_index)
        current = REALMS[source_index]
        target = breakthrough_target_realm(realm_index, requirement)
        items = " / ".join(
            f"{item}（{breakthrough_item_quality_cap_text(str(item), target_index)}）"
            for item in requirement.get("items", [])
        )
        lines.append(f"{current} -> {target}：{items}")
    lines.append("假仙境为渡劫后的七日仙元力转化阶段，不单独消耗突破道具；完成后进入真仙境。")
    return "\n".join(lines)


def catalog_item_detail_text(name: str) -> str:
    query = str(name or "").strip()
    if not query:
        return ""
    matches = [reward for reward in FISHING_REWARDS if reward[3] == query]
    requirements = [
        (realm_index, requirement)
        for realm_index, requirement in BREAKTHROUGH_REQUIREMENTS.items()
        if query in set(requirement.get("items", []))
    ]
    recipe = ALCHEMY_RECIPES.get(query) or ARTIFACT_REFINING_RECIPES.get(query)
    if not matches and not requirements and recipe is None:
        return ""
    lines = [f"【{query}图鉴】"]
    if matches:
        categories = sorted({str(reward[2]) for reward in matches})
        tiers = sorted({str(reward[0]) for reward in matches}, key=lambda tier: TIER_RANKS.get(tier, 0))
        grades = sorted({str(reward[1]) for reward in matches}, key=lambda grade: GRADE_RANKS.get(grade, 0))
        lines.append(f"类型：{'、'.join(categories)}；品阶：{'、'.join(tiers)}；品质：{'、'.join(grades)}")
        descriptions = [str(reward[4]) for reward in matches if str(reward[4]).strip()]
        if descriptions:
            lines.append(f"说明：{descriptions[0]}")
    elif requirements:
        lines.append(f"类型：{breakthrough_item_category(query)}；品阶：突破机缘道具")
    if requirements:
        usages = breakthrough_item_usage_lines(query)
        if usages:
            lines.append(f"突破用途：{'；'.join(usages)}")
        cap_lines = [
            breakthrough_item_quality_cap_text(query, breakthrough_target_realm_index(realm_index))
            for realm_index, _requirement in requirements
        ]
        if cap_lines:
            lines.append(f"品相上限：{'；'.join(dict.fromkeys(cap_lines))}")
        lines.append(f"故事：{breakthrough_item_story(query, breakthrough_item_category(query))}")
    if recipe:
        materials = "、".join(str(item) for item in recipe.get("materials", [])[:8])
        if len(recipe.get("materials", [])) > 8:
            materials += "等"
        cost = int(recipe.get("cost", 0))
        lines.append(f"炼制：需{materials or '特殊材料'}；消耗灵石{cost}")
    if matches and not requirements:
        lines.append("来源：垂钓奖池、秘境、商店或后台配置投放。")
    elif requirements:
        lines.append("来源：瓶颈期签到或垂钓概率大幅提升，也可能由秘境、商店或后台投放。")
    return "\n".join(lines)

def breakthrough_item_quality_cap_text(name: str, target_index: int) -> str:
    cap = breakthrough_item_quality_cap(name)
    if target_index == 2:
        if cap >= 18:
            return "最高可成天道筑基"
        if cap >= 14:
            return "最高可成无瑕道基"
        if cap >= 10:
            return "最高可成优秀筑基"
        if cap >= 5:
            return "最高可成良好筑基"
        return "最高可成普通筑基"
    titles = REALM_QUALITY_TITLES.get(realm_quality_title_index(target_index), [])
    if not titles:
        return "影响突破品相"
    fake_item = {"tier": "凡品", "grade": "下品", "name": name, "quality_cap_override": cap}
    return f"最高可至{quality_from_titles(fake_item, titles)}"

def admin_item_catalog() -> list[dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}

    def ensure(name: str, category: str = "") -> dict[str, Any]:
        key = str(name or "").strip() or "无名灵物"
        item = catalog.get(key)
        if item is None:
            item = {
                "name": key,
                "category": str(category or ""),
                "_categories": set(),
                "_tiers": set(),
                "_grades": set(),
                "_usage": [],
                "_source": [],
                "_story": [],
                "_note": [],
                "required_realm": "",
                "required_attribute": "",
            }
            catalog[key] = item
        if category:
            item["_categories"].add(str(category))
            if not item.get("category"):
                item["category"] = str(category)
        return item

    def add_text(item: dict[str, Any], key: str, value: str) -> None:
        text = str(value or "").strip()
        if text and text not in item[key]:
            item[key].append(text)

    for tier, grade, category, name, description, _weight in FISHING_REWARDS:
        item = ensure(str(name), str(category))
        item["_tiers"].add(str(tier))
        item["_grades"].add(str(grade))
        add_text(item, "_usage", str(description))
        add_text(item, "_source", "垂钓奖池、每日商店、秘境掉落或后台配置投放")
        add_text(item, "_note", f"奖励参数：tier={tier}，grade={grade}，category={category}")
        attr = ITEM_ATTRIBUTE_BY_NAME.get(str(name))
        if attr and not item.get("required_attribute"):
            item["required_attribute"] = attr

    for info in ARTIFACT_REALM_CATALOG:
        item = ensure(str(info.get("name")), ARTIFACT_CATEGORY)
        item["_tiers"].add(str(info.get("tier", "")))
        item["_grades"].add(str(info.get("grade", "")))
        item["required_realm"] = str(info.get("realm", ""))
        item["required_attribute"] = str(info.get("attribute", ""))
        add_text(item, "_usage", "装备后提供战力；需达到灵器所属境界并满足灵根属性才可驾驭；也可祭炼为本命灵器")
        add_text(item, "_source", str(info.get("source") or "后台灵器规则池、垂钓、商店、秘境"))
        add_text(item, "_story", str(info.get("description") or ""))
        add_text(item, "_note", f"灵器池参数：realm_index={info.get('realm_index')}，tier={info.get('tier')}，grade={info.get('grade')}，attribute={info.get('attribute')}")

    for realm_index, requirement in BREAKTHROUGH_REQUIREMENTS.items():
        target_index = breakthrough_target_realm_index(realm_index)
        for name in requirement.get("items", []):
            item = ensure(str(name), breakthrough_item_category(str(name)))
            usages = breakthrough_item_usage_lines(str(name))
            if usages:
                add_text(item, "_usage", "突破用途：" + "；".join(usages))
            add_text(item, "_usage", breakthrough_item_quality_cap_text(str(name), target_index))
            add_text(item, "_source", "瓶颈期签到、垂钓机缘、秘境掉落、商店或后台配置投放")
            add_text(item, "_story", breakthrough_item_story(str(name), str(item.get("category") or "")))
            add_text(item, "_note", f"突破配置：BREAKTHROUGH_REQUIREMENTS[{realm_index}]；品相上限={breakthrough_item_quality_cap(str(name))}")

    for name, recipe in ALCHEMY_RECIPES.items():
        item = ensure(str(name), PILL_CATEGORY)
        if recipe.get("tier"):
            item["_tiers"].add(str(recipe.get("tier")))
        if recipe.get("grade"):
            item["_grades"].add(str(recipe.get("grade")))
        materials = "、".join(str(material) for material in recipe.get("materials", []))
        add_text(item, "_source", "炼丹房炼制；也可能由秘境、商店或后台投放")
        add_text(item, "_note", f"炼丹配方：材料={materials or '特殊材料'}；灵石={recipe.get('cost', 0)}；难度={recipe.get('difficulty', 0)}")

    for name, recipe in ARTIFACT_REFINING_RECIPES.items():
        category = str(recipe.get("category") or ARTIFACT_CATEGORY)
        item = ensure(str(name), category)
        if recipe.get("tier"):
            item["_tiers"].add(str(recipe.get("tier")))
        if recipe.get("grade"):
            item["_grades"].add(str(recipe.get("grade")))
        if recipe.get("required_realm") is not None:
            try:
                item["required_realm"] = REALMS[max(0, min(len(REALMS) - 1, int(recipe.get("required_realm"))))]
            except (TypeError, ValueError):
                pass
        materials = "、".join(str(material) for material in recipe.get("materials", []))
        if category == ARTIFACT_CATEGORY:
            add_text(item, "_story", crafted_artifact_story(str(name), recipe))
        add_text(item, "_source", "炼器房炼制；也可能由秘境、商店或后台投放")
        add_text(item, "_note", f"炼器配方：材料={materials or '特殊材料'}；灵石={recipe.get('cost', 0)}")

    category_order = {name: index for index, name in enumerate(REWARD_CATEGORIES + [IMMORTAL_SEED_CATEGORY])}

    def tier_sort(values: set[str]) -> list[str]:
        return sorted((value for value in values if value), key=lambda value: (TIER_ORDER.index(value) if value in TIER_ORDER else 999, value))

    def grade_sort(values: set[str]) -> list[str]:
        return sorted((value for value in values if value), key=lambda value: (GRADE_ORDER.index(value) if value in GRADE_ORDER else 999, value))

    result: list[dict[str, Any]] = []
    for item in catalog.values():
        categories = sorted(item["_categories"], key=lambda value: (category_order.get(value, 999), value))
        category = str(item.get("category") or (categories[0] if categories else ""))
        tiers = tier_sort(item["_tiers"])
        grades = grade_sort(item["_grades"])
        required_realm = str(item.get("required_realm") or "")
        if not required_realm and tiers:
            required_realm = "随品阶或具体配置变化"
        result.append(
            {
                "name": str(item["name"]),
                "category": category,
                "tiers": tiers,
                "grades": grades,
                "required_realm": required_realm,
                "required_attribute": str(item.get("required_attribute") or ""),
                "usage": "\n".join(item["_usage"]),
                "source": "\n".join(item["_source"]),
                "story": "\n".join(item["_story"]),
                "parameter_note": "\n".join(item["_note"]),
            }
        )
    result.sort(key=lambda item: (category_order.get(str(item.get("category")), 999), tier_sort(set(item.get("tiers") or []))[:1], str(item.get("name"))))
    return result


def breakthrough_effective_quality_score(item: dict[str, Any], target_index: int) -> int:
    base = item_quality_score(item)
    cap = int(item.get("quality_cap_override") or breakthrough_item_quality_cap(reward_name(item)))
    return max(0, min(base, cap))


def breakthrough_quality_label_from_score(score: int, target_index: int) -> str:
    score = max(0, min(20, int(score)))
    if int(target_index) == 2:
        if score >= 18:
            return "天道筑基"
        if score >= 14:
            return "无瑕道基"
        if score >= 10:
            return "优秀筑基"
        if score >= 5:
            return "良好筑基"
        return "普通筑基"
    titles = REALM_QUALITY_TITLES.get(realm_quality_title_index(target_index), [])
    if not titles:
        return "影响突破品相"
    return quality_from_titles({"quality_cap_override": score}, titles)


def _breakthrough_target_index_for_record(record: UserRecord) -> Optional[int]:
    key = breakthrough_requirement_key_for_realm_index(record.realm_index)
    if key is None:
        return None
    return breakthrough_target_realm_index(key)


def _breakthrough_candidate_sort_key(entry: tuple[int, dict[str, Any], int, str], name_order: dict[str, int]) -> tuple[int, int, int, int, int]:
    list_index, item, score, _quality = entry
    name = reward_name(item)
    return (
        int(score),
        breakthrough_item_quality_cap(name),
        item_quality_score(item),
        name_order.get(name, -1),
        -int(list_index),
    )


def breakthrough_reward_candidates(
    record: UserRecord,
    names: Sequence[str],
    target_index: int,
) -> list[tuple[int, dict[str, Any], int, str]]:
    wanted = {str(name) for name in names}
    name_order = {str(name): index for index, name in enumerate(names)}
    candidates: list[tuple[int, dict[str, Any], int, str]] = []
    for list_index, raw in enumerate(record.rewards or []):
        if reward_name(raw) not in wanted:
            continue
        item = normalize_reward(dict(raw), record)
        score = breakthrough_effective_quality_score(item, target_index)
        quality = breakthrough_quality_label_from_score(score, target_index)
        candidates.append((list_index, item, score, quality))
    candidates.sort(key=lambda entry: _breakthrough_candidate_sort_key(entry, name_order), reverse=True)
    return candidates


def consume_best_breakthrough_reward(
    record: UserRecord,
    names: Sequence[str],
    target_index: int,
) -> Optional[dict[str, Any]]:
    candidates = breakthrough_reward_candidates(record, names, target_index)
    if not candidates or record.rewards is None:
        return None
    list_index, _item, _score, _quality = candidates[0]
    if list_index >= len(record.rewards):
        return None
    return normalize_reward(record.rewards.pop(list_index), record)


def breakthrough_quality_order_entries(record: UserRecord, owned_only: bool = False) -> list[dict[str, Any]]:
    requirement = current_breakthrough_requirement(record)
    target_index = _breakthrough_target_index_for_record(record)
    if not requirement or target_index is None:
        return []
    names = [str(name) for name in requirement.get("items", [])]
    if owned_only:
        return [
            {"name": reward_name(item), "quality": quality, "score": score, "owned": True}
            for _list_index, item, score, quality in breakthrough_reward_candidates(record, names, target_index)
        ]
    entries = []
    for index, name in enumerate(names):
        cap = breakthrough_item_quality_cap(name)
        entries.append(
            {
                "name": name,
                "quality": breakthrough_quality_label_from_score(cap, target_index),
                "score": cap,
                "order": index,
                "owned": False,
            }
        )
    entries.sort(key=lambda entry: (int(entry.get("score", 0)), int(entry.get("order", -1))), reverse=True)
    return entries


def breakthrough_priority_text(record: UserRecord, limit: int = 4) -> str:
    owned_entries = breakthrough_quality_order_entries(record, owned_only=True)
    entries = owned_entries or breakthrough_quality_order_entries(record, owned_only=False)
    if not entries:
        return f"需 {breakthrough_required_text(record)}"
    shown = entries[:max(1, limit)]
    parts = [f"{entry['name']}->{entry['quality']}" for entry in shown]
    if len(entries) > len(shown):
        parts.append("...")
    prefix = "背包高→低" if owned_entries else "品相高→低"
    return f"{prefix}：{' > '.join(parts)}"


def breakthrough_item_name_weight(name: str, source: str = "") -> float:
    cap = breakthrough_item_quality_cap(name)
    if source == "fishing":
        return 1.0 + max(0, 20 - cap) / 4.0
    return 1.0 + max(0, 22 - cap) / 2.0


def breakthrough_tier_grade_for_cap(cap: int, record: UserRecord, source: str = "") -> tuple[str, str]:
    if cap <= 8:
        tier_pool = [("凡品", 2), ("黄阶", 5), ("玄阶", 3)]
    elif cap <= 12:
        tier_pool = [("黄阶", 3), ("玄阶", 5), ("地阶", 2)]
    elif cap <= 15:
        tier_pool = [("玄阶", 3), ("地阶", 5), ("天阶", 2)]
    else:
        tier_pool = [("地阶", 4), ("天阶", 5)]
    if record.realm_index >= 5:
        if cap <= 8:
            tier_pool = [("黄阶", 3), ("玄阶", 5), ("地阶", 2)]
        elif cap <= 12:
            tier_pool = [("玄阶", 3), ("地阶", 5), ("天阶", 2)]
        elif cap <= 15:
            tier_pool = [("地阶", 4), ("天阶", 5)]
        else:
            tier_pool = [("地阶", 2), ("天阶", 6)]
            if source in {"signin", "fishing"}:
                tier_pool.append(("仙阶", 1 if source == "signin" else 2))
    tier = weighted_choice(tier_pool)
    grade_pool = [("下品", 4), ("中品", 3), ("上品", 2), ("极品", 1)]
    if source == "fishing":
        grade_pool = [("下品", 2), ("中品", 3), ("上品", 3), ("极品", 2)]
    if cap >= 18 and source == "fishing":
        grade_pool = [("下品", 1), ("中品", 2), ("上品", 3), ("极品", 2)]
    return tier, weighted_choice(grade_pool)


def high_realm_breakthrough_matches(
    matches: list[tuple[str, str, str, str, str, int]],
    record: UserRecord,
    days: int,
) -> list[tuple[tuple[str, str, str, str, str, int], float]]:
    weighted = []
    for reward in matches:
        tier, grade, _category, _name, _description, base_weight = reward
        tier_rank = TIER_RANKS.get(tier, 0)
        grade_rank = GRADE_RANKS.get(grade, 0)
        flattened = max(1.0, float(base_weight) ** 0.45)
        tier_bonus = 1.0 + tier_rank * 0.34
        grade_bonus = 1.0 + grade_rank * 0.55
        if tier == "天阶":
            tier_bonus *= 1.0 + min(3, max(0, days)) * 0.22
        weighted.append((reward, flattened * tier_bonus * grade_bonus))
    return weighted


def draw_breakthrough_reward(record: UserRecord, name: str, source: str = "") -> dict[str, Any]:
    cap = breakthrough_item_quality_cap(name)
    tier, grade = breakthrough_tier_grade_for_cap(cap, record, source or "signin")
    category = breakthrough_item_category(name)
    target_index = record.realm_index + 1
    reward = normalize_reward(
        {
            "tier": tier,
            "grade": grade,
            "category": category,
            "name": name,
            "description": f"{tier}{grade}{name}，可用于突破瓶颈。{breakthrough_item_quality_cap_text(name, target_index)}。",
            "breakthrough_item": True,
            "quality_cap": cap,
            "quality_cap_override": cap,
        }
    )
    if tier == "仙阶":
        reward["description"] = f"仙阶{grade}{name}，由高阶瓶颈机缘凝成，但仍受该道具自身品相上限约束。"
    return reward


def weighted_named_reward_matches(matches: list[tuple[str, str, str, str, str, int]], days: int) -> list[tuple[tuple[str, str, str, str, str, int], float]]:
    if days <= 0:
        return [(reward, high_tier_named_reward_weight(reward, 0)) for reward in matches]
    tiers = {reward[0] for reward in matches}
    tier_masses: dict[str, float] = {}
    if "\u5929\u9636" in tiers:
        tier_masses["\u5929\u9636"] = high_tier_probability(days)
        remaining = max(0.02, 1.0 - tier_masses["\u5929\u9636"])
    else:
        remaining = 1.0
    lower_base = {"\u5730\u9636": 0.46, "\u7384\u9636": 0.28, "\u9ec4\u9636": 0.17, "\u51e1\u54c1": 0.09}
    available_lower = [tier for tier in ("\u5730\u9636", "\u7384\u9636", "\u9ec4\u9636", "\u51e1\u54c1") if tier in tiers]
    lower_total = sum(lower_base[tier] for tier in available_lower) or 1.0
    for tier in available_lower:
        tier_masses[tier] = remaining * lower_base[tier] / lower_total
    grade_totals: dict[str, float] = {}
    for tier, grade, *_ in matches:
        grade_totals[tier] = grade_totals.get(tier, 0.0) + high_grade_multiplier(grade, days)
    weighted = []
    for reward in matches:
        tier, grade, *_ = reward
        tier_mass = tier_masses.get(tier, 0.001)
        grade_weight = high_grade_multiplier(grade, days)
        weighted.append((reward, max(0.001, tier_mass * grade_weight / max(0.001, grade_totals.get(tier, grade_weight)))))
    return weighted


def draw_named_reward(name: str, prefer_high_tier: bool = False, bottleneck_days: int = 0) -> dict[str, Any]:
    matches = [reward for reward in FISHING_REWARDS if reward[3] == name]
    if matches:
        if prefer_high_tier:
            weighted_matches = weighted_named_reward_matches(matches, bottleneck_days)
        else:
            weighted_matches = [(reward, float(reward[5])) for reward in matches]
        tier, grade, category, item_name, description, _ = weighted_choice(weighted_matches)
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

def talisman_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    seen: set[str] = set()
    for tier, grade, category, name, _description, _weight in FISHING_REWARDS:
        if category != TALISMAN_CATEGORY:
            continue
        signature = f"{tier}:{grade}:{category}:{name}"
        if signature in seen:
            continue
        seen.add(signature)
        item = normalize_reward({"tier": tier, "grade": grade, "category": category, "name": name})
        item["draw_kind"] = "\u666e\u901a\u7b26\u7b93"
        catalog.append(item)
    for realm_index, requirement in BREAKTHROUGH_REQUIREMENTS.items():
        for name in requirement["items"]:
            if not is_breakthrough_talisman_name(name):
                continue
            reward = draw_named_reward(name)
            reward["category"] = TALISMAN_CATEGORY
            reward["draw_kind"] = "\u7a81\u7834\u7b26\u4ee4"
            reward["breakthrough_realm_index"] = realm_index
            reward["target_realm"] = breakthrough_target_realm(realm_index, requirement)
            reward["description"] = REWARD_DESCRIPTIONS[TALISMAN_CATEGORY].format(name=name)
            reward["price"] = reward_price(reward)
            catalog.append(normalize_reward(reward))
    catalog.sort(
        key=lambda item: (
            str(item.get("draw_kind")) != "\u666e\u901a\u7b26\u7b93",
            TIER_RANKS.get(str(item.get("tier")), 0),
            GRADE_RANKS.get(str(item.get("grade")), 0),
            reward_name(item),
        )
    )
    return catalog


def talisman_draw_cost(talisman: dict[str, Any]) -> int:
    cost = max(12, int(reward_price(talisman) * 0.5))
    if str(talisman.get("draw_kind", "")) == "\u7a81\u7834\u7b26\u4ee4":
        cost = max(cost, int(reward_price(talisman) * 0.85))
    return cost


def talisman_draw_cost_for_record(record: UserRecord, talisman: dict[str, Any]) -> int:
    cost = talisman_draw_cost(talisman)
    if record.cultivation_route == "\u9635\u6cd5\u5e08":
        cost = max(1, int(cost * 0.8))
    return cost


def talisman_draw_required_text(talisman: dict[str, Any]) -> str:
    requirement = breakthrough_talisman_requirement(reward_name(talisman))
    if requirement:
        realm_index = int(requirement["realm_index"])
        return f"{REALMS[realm_index]}\u5dc5\u5cf0"
    required_index = TALISMAN_DRAW_REALM_REQUIREMENT.get(str(talisman.get("tier")), 0)
    return REALMS[required_index]


def can_draw_talisman(record: UserRecord, talisman: dict[str, Any]) -> tuple[bool, str]:
    if record.root is None:
        return False, "\u5c1a\u672a\u8e0f\u5165\u4fee\u884c\u8def\uff0c\u53d1\u9001\u201c\u7b7e\u5230\u201d\u5148\u89c9\u9192\u7075\u6839\u3002"
    requirement = breakthrough_talisman_requirement(reward_name(talisman))
    if requirement:
        realm_index = int(requirement["realm_index"])
        if record.realm_index != realm_index or not is_breakthrough_bottleneck(record):
            return False, f"{reward_name(talisman)} \u9700\u8fbe\u5230{REALMS[realm_index]}\u5dc5\u5cf0\u624d\u53ef\u7ed8\u5236\u3002"
    else:
        required_index = TALISMAN_DRAW_REALM_REQUIREMENT.get(str(talisman.get("tier")), 0)
        if record.realm_index < required_index:
            return False, f"{reward_display_name(talisman)} \u9700\u8fbe\u5230{REALMS[required_index]}\u624d\u53ef\u7ed8\u5236\u3002"
    cost = talisman_draw_cost_for_record(record, talisman)
    if record.spirit_stones < cost:
        return False, f"\u7075\u77f3\u4e0d\u8db3\uff0c\u7ed8\u5236\u9700\u8981 {spirit_stone_text(cost)}\u3002"
    return True, ""


def talisman_draw_text(record: UserRecord) -> str:
    catalog = talisman_catalog()
    lines = ["\u3010\u7ed8\u5236\u7b26\u7b93\u3011", f"\u5f53\u524d\u5883\u754c\uff1a{record.realm if record.root else '\u672a\u5165\u95e8'}", f"\u7075\u77f3\uff1a{spirit_stone_text(record.spirit_stones)}"]
    lines.append("\u666e\u901a\u7b26\u7b93\u6309\u54c1\u9636\u9650\u5236\u5883\u754c\uff1b\u7a81\u7834\u7b26\u4ee4\u9700\u8fbe\u5230\u5bf9\u5e94\u7a81\u7834\u524d\u5883\u754c\u5dc5\u5cf0\u3002")
    for index, talisman in enumerate(catalog, start=1):
        kind = str(talisman.get("draw_kind", "\u666e\u901a\u7b26\u7b93"))
        cost = talisman_draw_cost_for_record(record, talisman)
        lines.append(
            f"{index}. {reward_display_name(talisman)}\uff5c{kind}\uff5c\u9700{talisman_draw_required_text(talisman)}\uff5c{spirit_stone_text(cost)}"
        )
    lines.append("\u53d1\u9001\u201c\u7ed8\u5236\u7b26\u7b93 \u7f16\u53f7\u201d\uff0c\u4f8b\u5982\uff1a\u7ed8\u5236\u7b26\u7b93 1\u3002")
    return "\n".join(lines)


def draw_talisman_by_index(record: UserRecord, talisman_index: int) -> tuple[bool, str]:
    catalog = talisman_catalog()
    if talisman_index < 1 or talisman_index > len(catalog):
        return False, f"\u8bf7\u9009\u62e9 1-{len(catalog)} \u4e4b\u95f4\u7684\u7b26\u7b93\u7f16\u53f7\u3002"
    talisman = normalize_reward(dict(catalog[talisman_index - 1]), record)
    allowed, reason = can_draw_talisman(record, talisman)
    if not allowed:
        return False, reason
    cost = talisman_draw_cost_for_record(record, talisman)
    record.spirit_stones -= cost
    talisman["crafted"] = True
    if is_breakthrough_talisman_name(reward_name(talisman)):
        talisman["breakthrough_item"] = True
    append_reward(record, talisman)
    return True, f"\u6731\u7802\u843d\u5b9a\uff0c\u7b26\u7eb9\u6210\u5f62\u3002\u7ed8\u5236 {reward_display_name(talisman)} \u6210\u529f\uff0c\u6d88\u8017 {spirit_stone_text(cost)}\u3002"


def maybe_grant_breakthrough_item(record: UserRecord, chance: float = 0.5, source: str = "") -> Optional[dict[str, Any]]:
    requirement = current_breakthrough_requirement(record)
    if not requirement or not is_breakthrough_bottleneck(record):
        return None
    if random.random() >= chance:
        return None
    item_names = list(requirement["items"])
    if source == "fishing":
        item_name = weighted_choice([(name, breakthrough_item_fishing_weight(str(name)) * breakthrough_item_name_weight(str(name), source)) for name in item_names])
    else:
        item_name = weighted_choice([(name, breakthrough_item_name_weight(str(name), source or "signin")) for name in item_names])
    reward = draw_breakthrough_reward(record, str(item_name), source or "signin")
    reward["breakthrough_bonus"] = True
    if source == "fishing":
        reward["high_tier_fishing_bonus"] = True
        reward["bottleneck_days"] = record.bottleneck_days
    append_reward(record, reward)
    return reward


def breakthrough_required_text(record: UserRecord) -> str:
    requirement = current_breakthrough_requirement(record)
    if not requirement:
        return "当前无需突破道具"
    return " / ".join(str(item) for item in requirement["items"])


def breakthrough_item_usage_lines(name: str) -> list[str]:
    lines = []
    for realm_index, requirement in BREAKTHROUGH_REQUIREMENTS.items():
        if name in set(requirement.get("items", [])):
            source_index = breakthrough_source_realm_index(realm_index)
            lines.append(f"{REALMS[source_index]}圆满 -> {breakthrough_target_realm(realm_index, requirement)}")
    return lines

def breakthrough_item_story(name: str, category: str) -> str:
    if "破虚" in name or "虚空" in name:
        return "传闻化神修士叩问天地元气时，会在识海边缘见到虚空裂隙；此物正是稳住裂隙、引神入虚的凭依。"
    if "化凡" in name or "问心" in name or "斩尘" in name:
        return "由红尘问心与斩却尘念的感悟凝成，适合在元婴之后破开神意枷锁。"
    if "丹" in name or "液" in name or "露" in name:
        return "丹香入腹后先护经脉，再冲玄关；材料品阶越高，成丹品质与突破品相越稳。"
    if "符" in name or "诏" in name or "契" in name or "法旨" in name:
        return "符令承载天地法度，燃尽时可短暂借来一线天命，使瓶颈出现可破之门。"
    if "道果" in name or "道种" in name or "本源" in name or "真名" in name:
        return "高阶修士以漫长岁月沉淀出的道痕，服之不是增长法力，而是补足通往更高层次的理解。"
    return f"{name} 是突破瓶颈时会被天地灵机呼应的关键道具，品阶越高，突破后的境界品相越容易上探。"


def breakthrough_quality(item: dict[str, Any], target_index: int) -> str:
    score = breakthrough_effective_quality_score(item, target_index)
    return breakthrough_quality_label_from_score(score, target_index)

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
    if record.realm_index == true_immortal_realm_index():
        inherited = marks.get(str(fake_immortal_realm_index()))
        if inherited:
            return inherited
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


def reward_element_hint(reward: Optional[dict[str, Any]]) -> Optional[str]:
    if not reward:
        return None
    required = reward_required_attribute(reward)
    if required in BASE_FIVE_ELEMENTS:
        return required
    name = reward_name(reward)
    for attr in BASE_FIVE_ELEMENTS:
        if f"{attr}\u7cfb" in name or f"{attr}\u884c" in name or f"{attr}\u5c5e\u6027" in name:
            return attr
    if reward_category(reward) == "\u7075\u6750" and "\u5996\u4e39" in name:
        return stable_choice(BASE_FIVE_ELEMENTS, f"core-element:{reward_signature(reward)}")
    return None

def acquired_root_tier_grade(purity: int) -> tuple[str, str]:
    purity = max(1, min(100, int(purity)))
    if purity >= 88:
        return "\u5730\u9636", "\u6781\u54c1"
    if purity >= 80:
        return "\u5730\u9636", "\u4e0a\u54c1"
    if purity >= 72:
        return "\u5730\u9636", "\u4e2d\u54c1"
    if purity >= 64:
        return "\u7384\u9636", "\u4e0a\u54c1"
    if purity >= 56:
        return "\u7384\u9636", "\u4e2d\u54c1"
    if purity >= 48:
        return "\u9ec4\u9636", "\u4e0a\u54c1"
    if purity >= 40:
        return "\u9ec4\u9636", "\u4e2d\u54c1"
    return "\u51e1\u54c1", "\u4e0b\u54c1"


def normalize_acquired_root(root: dict[str, Any]) -> Optional[dict[str, Any]]:
    kind = str(root.get("kind") or "")
    attribute = str(root.get("attribute") or "")
    if kind not in ACQUIRED_ROOT_KINDS or attribute not in BASE_FIVE_ELEMENTS:
        return None
    max_purity = DAN_ROOT_MAX_PURITY if kind == ACQUIRED_ROOT_DAN else ARTIFACT_ROOT_MAX_PURITY
    purity = max(1, min(max_purity, int(root.get("purity", 1))))
    tier, grade = acquired_root_tier_grade(purity)
    return {
        "kind": kind,
        "attribute": attribute,
        "purity": purity,
        "tier": tier,
        "grade": grade,
        "source_name": str(root.get("source_name") or "\u65e0\u540d\u7075\u7269"),
        "source_tier": str(root.get("source_tier") or "\u51e1\u54c1"),
        "source_grade": str(root.get("source_grade") or "\u4e2d\u54c1"),
        "source_signature": str(root.get("source_signature") or ""),
        "source_uid": str(root.get("source_uid") or ""),
    }


def reward_instance_uid(reward: Optional[dict[str, Any]]) -> str:
    return str((reward or {}).get("instance_uid") or (reward or {}).get("source_uid") or "")


def ensure_reward_instance_uid(reward: dict[str, Any]) -> str:
    current = reward_instance_uid(reward)
    if current:
        reward["instance_uid"] = current
        return current
    current = uuid.uuid4().hex
    reward["instance_uid"] = current
    return current


def record_has_artifact_signature(record: UserRecord, signature: str, source_uid: str = "") -> bool:
    if not signature and not source_uid:
        return False
    for reward in record.rewards or []:
        if reward_category(reward) != ARTIFACT_CATEGORY:
            continue
        if source_uid:
            if reward_instance_uid(reward) == source_uid:
                return True
        elif signature and reward_signature(reward) == signature:
            return True
    for item in artifact_slots(record).values():
        if source_uid:
            if reward_instance_uid(item) == source_uid:
                return True
        elif signature and reward_signature(item) == signature:
            return True
    return False

def prune_broken_artifact_roots(record: UserRecord, broken_signature: str = "", broken_uid: str = "") -> int:
    roots = []
    removed = 0
    for raw in record.acquired_roots or []:
        root = normalize_acquired_root(raw) if isinstance(raw, dict) else None
        if root is None:
            continue
        if root.get("kind") == ACQUIRED_ROOT_ARTIFACT:
            signature = str(root.get("source_signature") or "")
            source_uid = str(root.get("source_uid") or "")
            explicitly_broken = bool(
                (broken_uid and source_uid and broken_uid == source_uid)
                or (broken_signature and signature == broken_signature and not source_uid)
            )
            if explicitly_broken or not record_has_artifact_signature(record, signature, source_uid):
                removed += 1
                continue
        roots.append(root)
    record.acquired_roots = roots
    return removed

def normalize_acquired_roots(record: UserRecord) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for raw in record.acquired_roots or []:
        if not isinstance(raw, dict):
            continue
        root = normalize_acquired_root(raw)
        if root is None:
            continue
        if root.get("kind") == ACQUIRED_ROOT_ARTIFACT and not record_has_artifact_signature(
            record,
            str(root.get("source_signature") or ""),
            str(root.get("source_uid") or ""),
        ):
            continue
        old = best.get(str(root["attribute"]))
        if old is None or int(root["purity"]) > int(old.get("purity", 0)):
            best[str(root["attribute"])] = root
    ordered = sorted(best.values(), key=lambda item: BASE_FIVE_ELEMENTS.index(str(item["attribute"])))
    record.acquired_roots = ordered
    return ordered


def acquired_root_attribute_text(root: dict[str, Any]) -> str:
    root = normalize_acquired_root(root) or root
    attribute = str(root.get("attribute") or "")
    return root_attribute_name(attribute)


def acquired_root_display(root: dict[str, Any]) -> str:
    root = normalize_acquired_root(root) or root
    kind = str(root.get("kind") or "后天灵根")
    return (
        f"{acquired_root_attribute_text(root)}（{kind}，{root.get('tier', '')}{root.get('grade', '')}，"
        f"纯度{int(root.get('purity', 0))}%，来源{root.get('source_name', '无名灵物')}）"
    )


def acquired_root_summary(record: UserRecord, limit: int = 2) -> str:
    roots = normalize_acquired_roots(record)
    if not roots:
        return "未炼成"
    shown = [acquired_root_attribute_text(root) for root in roots[:max(1, limit)]]
    if len(roots) > limit:
        shown.append(f"+{len(roots) - limit}条")
    return " / ".join(shown)


def acquired_root_purity_summary(record: UserRecord, limit: int = 8) -> str:
    roots = normalize_acquired_roots(record)
    if not roots:
        return "后天灵根未炼成"
    lines = []
    for root in roots[:max(1, limit)]:
        kind = str(root.get("kind") or "后天灵根")
        lines.append(
            f"{acquired_root_attribute_text(root)}：{int(root.get('purity', 0))}%"
            f"（{kind}，{root.get('tier', '')}{root.get('grade', '')}，来源{root.get('source_name', '无名灵物')}）"
        )
    if len(roots) > limit:
        lines.append(f"另有 {len(roots) - limit} 条后天灵根未显示")
    return "\n".join(lines)


def acquired_root_power_total(record: UserRecord) -> int:
    total = 0
    for root in normalize_acquired_roots(record):
        purity = int(root.get("purity", 0))
        kind_bonus = 160 if root.get("kind") == ACQUIRED_ROOT_DAN else 110
        total += kind_bonus + purity * 4
    return total


def innate_five_elements(record: UserRecord) -> set[str]:
    elements = set()
    for root in record.roots:
        elements.update(attr for attr in root.source_attributes if attr in BASE_FIVE_ELEMENTS)
    return elements


def acquired_root_for_attribute(record: UserRecord, attribute: str) -> Optional[dict[str, Any]]:
    for root in normalize_acquired_roots(record):
        if root.get("attribute") == attribute:
            return root
    return None


def demon_core_realm_name(reward: dict[str, Any]) -> Optional[str]:
    explicit = str(reward.get("beast_realm") or reward.get("demon_realm") or reward.get("source_realm") or "").strip()
    if explicit:
        short = realm_short_name(explicit)
        return DEMON_CORE_REALM_ALIASES.get(short, short if short in DEMON_CORE_EXP_BASE_BY_REALM else explicit)
    name = reward_name(reward)
    for realm_name in sorted(DEMON_CORE_REALM_ALIASES, key=len, reverse=True):
        if realm_name and realm_name in name:
            return DEMON_CORE_REALM_ALIASES[realm_name]
    return DEMON_CORE_DEFAULT_REALM_BY_TIER.get(str(reward.get("tier")), "\u6b8b\u788e")


def is_demon_core_item(reward: dict[str, Any]) -> bool:
    return reward_category(reward) == "\u7075\u6750" and "\u5996\u4e39" in reward_name(reward)


def demon_core_attribute(reward: dict[str, Any]) -> str:
    explicit = str(reward.get("element") or reward.get("attribute") or reward.get("required_attribute") or "")
    if explicit in BASE_FIVE_ELEMENTS:
        return explicit
    hinted = reward_element_hint(reward)
    if hinted in BASE_FIVE_ELEMENTS:
        return hinted
    return stable_choice(BASE_FIVE_ELEMENTS, f"dan-root-attr:{reward_signature(reward)}")


def demon_core_cultivation_exp(reward: dict[str, Any]) -> int:
    explicit = reward.get("cultivation_exp") or reward.get("exp")
    if explicit is not None:
        try:
            return max(1, int(explicit))
        except (TypeError, ValueError):
            pass
    realm_name = demon_core_realm_name(reward) or "\u6b8b\u788e"
    base = DEMON_CORE_EXP_BASE_BY_REALM.get(realm_name, DEMON_CORE_EXP_BASE_BY_REALM["\u6b8b\u788e"])
    tier_ratio = DEMON_CORE_TIER_EXP_RATIO.get(str(reward.get("tier")), 1.0)
    grade_ratio_value = grade_ratio(str(reward.get("grade")))
    return max(1, int(base * tier_ratio * grade_ratio_value))


def apply_demon_core_metadata(reward: dict[str, Any]) -> None:
    if not is_demon_core_item(reward):
        return
    realm_name = demon_core_realm_name(reward) or DEMON_CORE_DEFAULT_REALM_BY_TIER.get(str(reward.get("tier")), "\u6b8b\u788e")
    attribute = demon_core_attribute(reward)
    reward["beast_realm"] = realm_name
    reward["element"] = attribute
    reward["required_attribute"] = attribute
    reward["cultivation_exp"] = demon_core_cultivation_exp(reward)
    reward.setdefault("usage", "\u70bc\u4e39\u6750\u6599\uff1b\u53ef\u70bc\u5316\u63d0\u5347\u4fee\u4e3a\uff1b\u4e5f\u53ef\u70bc\u6210\u4e39\u7075\u6839\u7528\u4e8e\u4e94\u884c\u8865\u5168\u3002")
    reward["description"] = (
        f"{attribute}\u884c{realm_name}\u5996\u529b\u51dd\u6210\u7684\u5996\u4e39\uff0c"
        f"\u70bc\u5316\u7ea6\u53ef\u83b7\u5f97 {reward['cultivation_exp']} \u70b9\u4fee\u4e3a\uff0c"
        "\u4e5f\u53ef\u4f5c\u4e39\u7075\u6839\u4e0e\u70bc\u4e39\u6750\u6599\u3002"
    )


def demon_core_purity(reward: dict[str, Any]) -> int:
    realm_name = demon_core_realm_name(reward)
    realm_base = DEMON_CORE_REALM_PURITY.get(str(realm_name or ""), 0)
    tier_base = DEMON_CORE_TIER_BASE_PURITY.get(str(reward.get("tier")), 45)
    grade_bonus = GRADE_RANKS.get(str(reward.get("grade")), 1) * 3
    purity = max(realm_base, tier_base) + grade_bonus + random.randint(0, 4)
    return max(25, min(DAN_ROOT_MAX_PURITY, purity))

def artifact_root_attribute(reward: dict[str, Any]) -> Optional[str]:
    required = reward_required_attribute(reward)
    if required in BASE_FIVE_ELEMENTS:
        return required
    hinted = reward_element_hint(reward)
    return hinted if hinted in BASE_FIVE_ELEMENTS else None


def artifact_root_purity(reward: dict[str, Any]) -> int:
    tier_base = ARTIFACT_ROOT_TIER_BASE_PURITY.get(str(reward.get("tier")), 38)
    grade_bonus = GRADE_RANKS.get(str(reward.get("grade")), 1) * 3
    purity = tier_base + grade_bonus + random.randint(0, 4)
    return max(18, min(ARTIFACT_ROOT_MAX_PURITY, purity))


def make_acquired_root(kind: str, attribute: str, purity: int, source: dict[str, Any]) -> dict[str, Any]:
    tier, grade = acquired_root_tier_grade(purity)
    return {
        "kind": kind,
        "attribute": attribute,
        "purity": purity,
        "tier": tier,
        "grade": grade,
        "source_name": reward_name(source),
        "source_tier": str(source.get("tier", "\u51e1\u54c1")),
        "source_grade": str(source.get("grade", "\u4e2d\u54c1")),
        "source_signature": reward_signature(source),
        "source_uid": reward_instance_uid(source),
    }


def add_acquired_root(record: UserRecord, root: dict[str, Any]) -> tuple[bool, str]:
    root = normalize_acquired_root(root) or root
    attribute = str(root.get("attribute") or "")
    if attribute in innate_five_elements(record):
        return False, f"\u4f60\u5df2\u5177\u5907\u5148\u5929{attribute}\u7075\u6839\uff0c\u65e0\u9700\u518d\u70bc\u6210\u540e\u5929\u7075\u6839\u3002"
    roots = normalize_acquired_roots(record)
    old = acquired_root_for_attribute(record, attribute)
    if old and int(old.get("purity", 0)) >= int(root.get("purity", 0)):
        return False, f"\u5df2\u6709\u66f4\u7a33\u7684{acquired_root_display(old)}\uff0c\u6b64\u6b21\u4e0d\u5efa\u8bae\u66ff\u6362\u3002"
    record.acquired_roots = [item for item in roots if item.get("attribute") != attribute]
    record.acquired_roots.append(root)
    normalize_acquired_roots(record)
    if old:
        return True, f"\u540e\u5929\u7075\u6839\u5df2\u66ff\u6362\uff1a{acquired_root_display(old)} -> {acquired_root_display(root)}"
    return True, f"\u540e\u5929\u7075\u6839\u5df2\u70bc\u6210\uff1a{acquired_root_display(root)}"


def refine_dan_root(record: UserRecord, material_index: int) -> tuple[bool, str]:
    if record.root is None:
        return False, "\u5c1a\u672a\u8e0f\u5165\u4fee\u884c\u8def\uff0c\u53d1\u9001\u201c\u7b7e\u5230\u201d\u5148\u89c9\u9192\u7075\u6839\u3002"
    result = reward_position_by_category_index(record, "\u7075\u6750", material_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7075\u6750\u3002"
    list_index, material = result
    if not is_demon_core_item(material):
        return False, f"{reward_display_name(material)} \u4e0d\u662f\u5996\u4e39\uff0c\u65e0\u6cd5\u70bc\u6210\u4e39\u7075\u6839\u3002"
    attribute = demon_core_attribute(material)
    purity = demon_core_purity(material)
    new_root = make_acquired_root(ACQUIRED_ROOT_DAN, attribute, purity, material)
    allowed, reason = add_acquired_root(record, new_root)
    if not allowed:
        return False, reason
    if record.rewards is None or list_index >= len(record.rewards):
        return False, "\u7075\u6750\u4f4d\u7f6e\u53d1\u751f\u53d8\u5316\uff0c\u8bf7\u91cd\u65b0\u6253\u5f00\u80cc\u5305\u786e\u8ba4\u7f16\u53f7\u3002"
    consumed = normalize_reward(record.rewards.pop(list_index), record)
    return True, f"\u70bc\u5316 {reward_display_name(consumed)} \u6210\u529f\u3002\n{reason}\n\u4e39\u7075\u6839\u4e3a\u540e\u5929\u6240\u6210\uff0c\u7cbe\u7eaf\u5ea6\u4e0a\u9650\u4e0e\u5730\u7075\u6839\u6301\u5e73\uff0c\u53ef\u7528\u4e8e\u4e94\u884c\u8865\u5168\u3001\u529f\u6cd5\u4e0e\u7075\u5668\u5951\u5408\u3002"


def remove_equipped_artifact_by_signature(record: UserRecord, signature: str, source_uid: str = "") -> None:
    if not signature and not source_uid:
        return
    slots = artifact_slots(record)
    kept = {}
    for slot, item in slots.items():
        item_uid = reward_instance_uid(item)
        if source_uid:
            if item_uid == source_uid or (not item_uid and signature and reward_signature(item) == signature):
                continue
        elif signature and reward_signature(item) == signature:
            continue
        kept[slot] = item
    record.equipped_artifacts = kept
    record.equipped_artifact = kept.get("主手") if kept else None

def refine_artifact_root(record: UserRecord, artifact_index: int) -> tuple[bool, str]:
    if record.root is None:
        return False, "尚未踏入修行路，发送“签到”先觉醒灵根。"
    result = reward_position_by_category_index(record, ARTIFACT_CATEGORY, artifact_index)
    if result is None:
        return False, "没有找到这个编号的灵器。"
    list_index, artifact = result
    attribute = artifact_root_attribute(artifact)
    if attribute is None:
        return False, f"{reward_display_name(artifact)} 没有明确五行适配属性，不能作为器灵根。"
    test_root = make_acquired_root(ACQUIRED_ROOT_ARTIFACT, attribute, artifact_root_purity(artifact), artifact)
    old = acquired_root_for_attribute(record, attribute)
    if attribute in innate_five_elements(record):
        return False, f"你已具备先天{attribute}灵根，无需再炼器为根。"
    if old and int(old.get("purity", 0)) >= int(test_root.get("purity", 0)):
        return False, f"已有更稳的{acquired_root_display(old)}，此次不建议冒险替换。"
    if record.rewards is None or list_index >= len(record.rewards):
        return False, "灵器位置发生变化，请重新打开灵器面板确认编号。"
    source = normalize_reward(record.rewards[list_index], record)
    source_uid = ensure_reward_instance_uid(source)
    record.rewards[list_index] = source
    signature = reward_signature(source)
    if random.random() >= ARTIFACT_ROOT_SUCCESS_RATE:
        destroyed = normalize_reward(record.rewards.pop(list_index), record)
        remove_equipped_artifact_by_signature(record, signature, source_uid)
        prune_broken_artifact_roots(record, signature, source_uid)
        return True, f"祭炼 {reward_display_name(destroyed)} 失败，器纹崩解，灵器已毁。\n器灵根成功率仅 {int(ARTIFACT_ROOT_SUCCESS_RATE * 100)}%，器毁则根无，建议优先使用对应妖丹炼成丹灵根。"
    new_root = make_acquired_root(ACQUIRED_ROOT_ARTIFACT, attribute, artifact_root_purity(source), source)
    allowed, reason = add_acquired_root(record, new_root)
    if not allowed:
        return True, f"祭炼 {reward_display_name(source)} 后，{reason}"
    return True, f"祭炼 {reward_display_name(source)} 成功。\n{reason}\n器灵根依托此器而成：器在则根在，器毁则根无。请勿出售或损毁该灵器。"


def acquired_root_text(record: UserRecord) -> str:
    roots = normalize_acquired_roots(record)
    lines = ["【后天灵根】"]
    if not roots:
        lines.append("当前：未炼成")
    else:
        for index, root in enumerate(roots, start=1):
            lines.append(f"{index}. {acquired_root_attribute_text(root)}")
    lines.append("")
    lines.append("【灵根精纯度】")
    lines.append(acquired_root_purity_summary(record, limit=10))
    missing = [attr for attr in BASE_FIVE_ELEMENTS if attr not in (set(record.root_attributes) & set(BASE_FIVE_ELEMENTS))]
    lines.append("")
    lines.append("【五行状态】")
    lines.append("已齐" if not missing else f"尚缺{'/'.join(missing)}")
    lines.append("")
    lines.append("【炼化方式】")
    lines.append("丹灵根：以对应属性妖丹炼成，精纯度受妖兽修为与妖丹品阶影响，上限与地灵根持平。")
    lines.append(f"器灵根：以灵器适配属性作根，成功率 {int(ARTIFACT_ROOT_SUCCESS_RATE * 100)}%，器在则根在，器毁或出售则灵根失效。")
    lines.append("用法：炼化丹灵根 编号；炼化器灵根 编号。")
    materials = available_materials(record)
    cores = [item for item in materials if is_demon_core_item(item)]
    if cores:
        lines.append("")
        lines.append("【可用妖丹】")
        for index, item in enumerate(materials, start=1):
            if is_demon_core_item(item):
                lines.append(f"{index}. {reward_display_name(item)} -> {demon_core_attribute(item)}灵根，预估精纯度≤{DAN_ROOT_MAX_PURITY}%")
    artifacts = available_artifacts(record)
    compatible_artifacts = [(index, item) for index, item in enumerate(artifacts, start=1) if artifact_root_attribute(item)]
    if compatible_artifacts:
        lines.append("")
        lines.append("【可祭炼灵器】")
        for index, item in compatible_artifacts[:8]:
            lines.append(f"{index}. {reward_display_name(item)} -> {artifact_root_attribute(item)}灵根，成功率{int(ARTIFACT_ROOT_SUCCESS_RATE * 100)}%")
    return "\n".join(lines)


def supplemental_root_elements(record: UserRecord) -> dict[str, list[int]]:
    return {attr: [] for attr in BASE_FIVE_ELEMENTS}

def effective_five_elements(record: UserRecord) -> set[str]:
    return set(record.root_attributes) & set(BASE_FIVE_ELEMENTS)

def missing_five_elements(record: UserRecord) -> list[str]:
    return [attr for attr in BASE_FIVE_ELEMENTS if attr not in effective_five_elements(record)]


def needs_five_element_completion(record: UserRecord) -> bool:
    requirement = current_breakthrough_requirement(record)
    return bool(requirement and current_breakthrough_target_realm(record) == "炼虚期")

def five_element_requirement_text(record: UserRecord) -> str:
    missing = missing_five_elements(record)
    if not missing:
        return "五行已齐，可感天地元气与空间法则。"
    return (
        f"化神破炼虚需五行合一，当前缺{'/'.join(missing)}。"
        "需先把对应属性妖丹炼成丹灵根，"
        "或借对应属性灵器炼作器灵根补全；单纯持有材料不能直接破关。"
    )


def consume_five_element_supplements(record: UserRecord) -> list[dict[str, Any]]:
    return []

def breakthrough_status(record: UserRecord) -> str:
    if record.root is None:
        return "尚未踏入修行路，发送“签到”先觉醒灵根。"
    requirement = current_breakthrough_requirement(record)
    if requirement is None:
        if is_fake_immortal_conversion(record):
            days = int(record.immortal_conversion_days or 0)
            return f"当前已至假仙境，仙元力转化中 {days}/7；每日签到会推进转化，完成后正式踏入真仙境。"
        if record.realm_index >= len(REALMS) - 1:
            return f"当前已至{record.realm}，暂时无更高境界。"
        return f"当前{record.realm}进度 {record.realm_exp}/{record.progress_required}，继续修炼即可。"
    target = current_breakthrough_target_realm(record)
    requirement_key = breakthrough_requirement_key_for_realm_index(record.realm_index)
    target_index = breakthrough_target_realm_index(requirement_key if requirement_key is not None else record.realm_index)
    needed = list(requirement["items"])
    count_text = "，".join(f"{name}x{reward_count_by_names(record, [name])}" for name in needed)
    cap_text = "；".join(
        f"{name}：{breakthrough_item_quality_cap_text(str(name), target_index)}"
        for name in needed
    )
    five_text = f"\n{five_element_requirement_text(record)}" if needs_five_element_completion(record) else ""
    priority_text = breakthrough_priority_text(record)
    if record.realm_exp < record.progress_required:
        return (
            f"当前{record.realm}进度 {record.realm_exp}/{record.progress_required}，"
            f"圆满后可凭 {breakthrough_required_text(record)} 突破至{target}。"
            f"\n品相上限：{cap_text}"
            f"\n品相排序：{priority_text}{five_text}"
        )
    return (
        f"当前已达{record.realm}，可突破至{target}。"
        f"所需道具：{breakthrough_required_text(record)}；背包：{count_text or '暂无'}。"
        f"\n品相上限：{cap_text}"
        f"\n品相排序：{priority_text}{five_text}"
    )

BREAKTHROUGH_FLAVOR_BY_REALM = {
    "筑基期": [
        "丹田灵海骤然下沉，气血如炉，骨骼间响起细密雷音。",
        "周身灵气化作一圈圈涟漪，原本散乱的根基终于凝成道台。",
        "灵根光华贯穿百脉，泥丸宫中有清钟一响，修行之路自此真正开阔。",
    ],
    "金丹期": [
        "丹田深处一点金光由虚转实，云气倒卷，仿佛有一轮小日沉入灵海。",
        "三花虚影在头顶一闪而逝，周身法力坍缩成丹，连呼吸都带着金石之音。",
        "漫天灵气被你一口吞下，丹成之刻，心魔幻景如潮退去，只余金丹悬照。",
    ],
    "元婴期": [
        "金丹裂而不碎，丹中有婴儿虚影睁眼，方圆灵气随之朝拜。",
        "天边劫云压来又散去，元婴抱一而坐，眉目间已生出几分大道气象。",
        "识海轰鸣，旧我如壳层层剥落，一尊元婴在丹田中吐纳第一缕先天灵机。",
    ],
    "化神期": [
        "元婴抬头望天，神念化作万千流光，照见尘缘、执念与未斩之心。",
        "一场无声问心在识海展开，你斩去杂念，神意终于破体而出。",
        "天地像一卷缓缓展开的古图，你在图中看见自身法相，化神之门轰然洞开。",
    ],
    "炼虚期": [
        "神意撞入虚空，身后浮现洞天裂隙，万象生灭皆在一念之间。",
        "你以神识叩问虚无，虚无回以风雷，法身自混沌边缘凝出轮廓。",
    ],
    "合体期": [
        "元神与法身相合，天地灵机如潮入体，举手之间已有山河回应。",
        "虚空法相归入己身，万千念头像星斗归位，道体终于合真。",
    ],
    "大乘期": [
        "道果雏形在身后升起，凡俗气息被一寸寸洗去，只余圆融清光。",
        "你听见大道潮声从极远处传来，肉身、元神、法力一并迈过天堑。",
    ],
    "渡劫期": [
        "劫云翻涌如海，雷光照彻神魂，你在万钧天威中守住一点本心。",
        "雷劫落下又被道心撑开，焦土之中生出新芽，渡劫气象初成。",
    ],
    "真仙境": [
        "仙门虚影在天外开启，凡蜕尽去，一缕真仙清光落入眉心。",
        "尘世因果如线寸寸松开，你踏过仙凡之隔，法力化作仙元。",
    ],
}

HIGH_REALM_BREAKTHROUGH_FLAVORS = [
    "天穹开裂，星河垂落，道音如潮洗过神魂。",
    "万象在身后轮转，旧日瓶颈如薄纸般燃尽。",
    "命河虚影从脚下流过，你以一念定住浪潮，踏向更高道途。",
    "大道符文绕身而行，诸般因果退避三尺。",
]


def breakthrough_method_text(item: dict[str, Any]) -> str:
    name = reward_name(item)
    if any(token in name for token in ("丹", "露", "液", "丸", "散")):
        return "丹破：药力入腹，先护经脉，再冲玄关，药性与法力在丹田中层层相合。"
    if any(token in name for token in ("意境", "道果", "道胎", "玄光", "本源", "源流", "真名")):
        return "悟道：你不急着破关，只在识海中守住一念，等大道痕迹自行落下。"
    if any(token in name for token in ("令", "符", "符诏", "法旨", "玉册", "真箓", "道章")):
        return "天命：符诏燃起，天地法则短暂让开一线，像有无形门户为你开启。"
    if any(token in name for token in ("灵宝", "刃", "印", "权柄", "道印", "钥印")):
        return "祭炼：器物悬于头顶，替你镇住心魔与外劫，锋芒直指瓶颈最薄弱处。"
    if any(token in name for token in ("斩", "断", "因果", "命河")):
        return "斩执：旧日因果如锁链浮现，你以一念斩下，瓶颈随执念一同裂开。"
    return "破关：灵力沿百脉奔涌，神魂、肉身与道基同时撞向瓶颈。"


def breakthrough_flavor_text(old_realm: str, target_realm: str, mark: str, item: dict[str, Any]) -> str:
    flavors = BREAKTHROUGH_FLAVOR_BY_REALM.get(target_realm, HIGH_REALM_BREAKTHROUGH_FLAVORS)
    flavor = random.choice(flavors)
    item_text = reward_display_name(item)
    process = breakthrough_method_text(item)
    return "\n".join(
        [
            f"叮！消耗{item_text}，从{old_realm}突破至{target_realm}。",
            process,
            flavor,
            f"异象渐敛，道基留痕：{mark}。",
        ]
    )

def breakthrough_realm(record: UserRecord) -> tuple[bool, str]:
    if record.root is None:
        return False, "\u5c1a\u672a\u8e0f\u5165\u4fee\u884c\u8def\uff0c\u53d1\u9001\u201c\u7b7e\u5230\u201d\u5148\u89c9\u9192\u7075\u6839\u3002"
    requirement = current_breakthrough_requirement(record)
    if requirement is None:
        return False, breakthrough_status(record)
    if record.realm_exp < record.progress_required:
        return False, breakthrough_status(record)
    if needs_five_element_completion(record) and missing_five_elements(record):
        return False, f"突破失败：{five_element_requirement_text(record)}"
    requirement_key = breakthrough_requirement_key_for_realm_index(record.realm_index)
    target_index = breakthrough_target_realm_index(requirement_key if requirement_key is not None else record.realm_index)
    item = consume_best_breakthrough_reward(record, list(requirement["items"]), target_index)
    if item is None:
        return (
            False,
            f"\u7a81\u7834\u5931\u8d25\uff1a\u9700\u8981 {breakthrough_required_text(record)}\u3002\u5883\u754c\u5706\u6ee1\u65f6\uff0c\u6bcf\u6b21\u7b7e\u5230\u6216\u5782\u9493\u90fd\u6709 50% \u6982\u7387\u989d\u5916\u83b7\u5f97\u5f53\u524d\u7a81\u7834\u9053\u5177\u3002",
        )
    consumed_supplements = consume_five_element_supplements(record) if needs_five_element_completion(record) else []
    old_realm = record.realm
    record.realm_index += 1
    record.realm_exp = 0
    reset_bottleneck_state(record)
    target_realm = record.realm
    mark = foundation_quality(item) if requirement.get("kind") == "foundation" else breakthrough_quality(item, record.realm_index)
    set_realm_mark(record, record.realm_index, mark)
    message = breakthrough_flavor_text(old_realm, target_realm, mark, item)
    cap_note = breakthrough_item_quality_cap_text(reward_name(item), record.realm_index)
    message += f"\n此物品相上限：{cap_note}；实际品相由道具名、品阶和品质共同决定。"
    if consumed_supplements:
        names = "、".join(reward_display_name(reward) for reward in consumed_supplements)
        message += f"\n五行补全：炼化{names}，丹/器灵根归入己身，助你掌握天地元气。"
    special_reward = maybe_grant_special_ability_material(record, chance=0.35, source="突破余韵")
    if special_reward:
        message += f"\n突破余韵中落下一份{reward_display_name(special_reward)}，可发送“领悟神通 编号”参悟。"
    return True, message


def regress_cultivation(record: UserRecord) -> tuple[bool, str]:
    if record.root is None:
        return False, "\u5c1a\u672a\u8e0f\u5165\u4fee\u884c\u8def\uff0c\u53d1\u9001\u201c\u7b7e\u5230\u201d\u5148\u89c9\u9192\u7075\u6839\u3002"
    if record.realm_index <= 0:
        return False, "\u5f53\u524d\u5c1a\u5728\u70bc\u4f53\u671f\uff0c\u65e0\u6cd5\u518d\u6563\u529f\u56de\u9000\u3002"
    old_realm = record.realm
    old_index = record.realm_index
    old_mark = realm_quality_text(record)
    if record.realm_marks is not None:
        record.realm_marks.pop(str(old_index), None)
    if old_index == 2:
        record.foundation_type = None
    record.realm_index = old_index - 1
    record.realm_exp = max(0, int(record.progress_required * 0.6))
    record.total_exp = max(0, cumulative_realm_exp(record.root, record.realm_index) + record.realm_exp)
    reset_bottleneck_state(record)
    new_realm = record.realm
    return (
        True,
        f"\u4e3b\u52a8\u6563\u529f\uff0c\u81ea{old_realm}\u8dcc\u56de{new_realm}\u3002\n"
        f"\u539f\u5883\u754c\u54c1\u76f8\u3010{old_mark}\u3011\u5df2\u6563\u53bb\uff0c\u7d2f\u8ba1\u4fee\u4e3a\u5df2\u540c\u6b65\u56de\u9000\u3002\n"
        f"\u91cd\u4fee\u81f3\u5706\u6ee1\u540e\u53ef\u518d\u6b21\u7a81\u7834\uff0c\u4e89\u53d6\u66f4\u9ad8\u5883\u754c\u54c1\u8d28\u3002"
    )

def reward_signature(reward: Optional[dict[str, Any]]) -> str:
    if not reward:
        return ""
    required = reward_required_attribute(reward) or ""
    return ":".join(
        [reward_category(reward), str(reward.get("tier", "")), str(reward.get("grade", "")), reward_name(reward), required]
    )



def stable_int(seed: str, length: int = 16) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:length], 16)


def stable_choice(options: Sequence[T], seed: str) -> T:
    if not options:
        raise ValueError("stable_choice requires non-empty options")
    return options[stable_int(seed) % len(options)]


def weighted_choice_stable(items: Sequence[tuple[T, int]], seed: str) -> T:
    total = sum(max(0, int(weight)) for _, weight in items)
    if total <= 0:
        return items[0][0]
    point = stable_int(seed) % total
    cursor = 0
    for item, weight in items:
        cursor += max(0, int(weight))
        if point < cursor:
            return item
    return items[-1][0]


DIVINATION_HEXAGRAMS = [
    "乾为天", "坤为地", "水雷屯", "山水蒙", "水天需", "天水讼", "地水师", "水地比",
    "风天小畜", "天泽履", "地天泰", "天地否", "天火同人", "火天大有", "地山谦", "雷地豫",
    "泽雷随", "山风蛊", "地泽临", "风地观", "火雷噬嗑", "山火贲", "山地剥", "地雷复",
    "天雷无妄", "山天大畜", "山雷颐", "泽风大过", "坎为水", "离为火", "泽山咸", "雷风恒",
    "天山遁", "雷天大壮", "火地晋", "地火明夷", "风火家人", "火泽睽", "水山蹇", "雷水解",
    "山泽损", "风雷益", "泽天夬", "天风姤", "泽地萃", "地风升", "泽水困", "水风井",
    "泽火革", "火风鼎", "震为雷", "艮为山", "风山渐", "雷泽归妹", "雷火丰", "火山旅",
    "巽为风", "兑为泽", "风水涣", "水泽节", "风泽中孚", "雷山小过", "水火既济", "火水未济",
]

DIVINATION_TRIGRAMS = [
    ("乾", "天", "健"), ("坤", "地", "顺"), ("震", "雷", "动"), ("巽", "风", "入"),
    ("坎", "水", "险"), ("离", "火", "丽"), ("艮", "山", "止"), ("兑", "泽", "悦"),
]

DIVINATION_YAO = ("初爻", "二爻", "三爻", "四爻", "五爻", "上爻")
DIVINATION_IMAGES = (
    "阳气初生，宜先正心而后行事。",
    "阴阳相薄，动中有待，待中有机。",
    "风过松间，所问之事贵在顺势而不强求。",
    "水火相济，前路有阻，亦有解法藏于其中。",
    "山泽通气，外静内动，须辨别虚实。",
    "雷动于地，先有震惊，后有生机。",
)
DIVINATION_FORTUNES = (
    ("大吉", "云开月明，所谋有成，但忌得意忘形。"),
    ("中吉", "溪水渐涨，积少成多，此事利于稳行。"),
    ("小吉", "春草初萌，尚需时日，勿急于求成。"),
    ("平", "水面无波，吉凶未定，一念一行皆是变数。"),
    ("先阻后通", "前有关隘，不可硬闯，待机而动反见生路。"),
    ("小凶", "此事有虚火与暗耗，宜收敛锋芒，先保本心。"),
)
DIVINATION_YI = ("闭关", "问道", "结善缘", "清点因果", "稳守", "先礼后兵", "择吉时", "积蓄资粮")
DIVINATION_JI = ("贪功", "急进", "轻信他言", "夜行险地", "强破瓶颈", "与人争锋", "心神散乱", "资财外露")
DIVINATION_TOPIC_ADVICES = {
    "修行": ("若问修行，当先固本培元，不宜为一时进境损了道基。", "若问破境，可先备齐灵丹符令，待气机圆融再动。", "若问秘境，此行有得有失，贪念起则陷阱近。"),
    "情缘": ("若问情缘，宜真诚相告，不宜借势试心。", "若问和合，先解旧结，后谈新缘。", "若问缘分，此象贵在相待，不贵追逼。"),
    "财事": ("若问财事，宜分散风险，小利可取，大贪则伤。", "若问买卖，先看契约，再论灵石。", "若问机缘，当以正道取之，暗财多带因果。"),
    "通用": ("所问之事不宜只看一时吉凶，先正心，再正事。", "此象有变，一变在心，二变在时，三变在人和。", "若心中犹疑，可缓一步；若机已至，当留三分余地。"),
}


def divination_topic(question: str) -> str:
    text = question.strip()
    if any(token in text for token in ("修行", "突破", "境界", "功法", "秘境", "渡劫", "签到")):
        return "修行"
    if any(token in text for token in ("情", "缘", "爱", "复合", "姻", "双修")):
        return "情缘"
    if any(token in text for token in ("财", "钱", "灵石", "买", "卖", "商店", "事业", "工作")):
        return "财事"
    return "通用"


def divination_pick_pair(options: Sequence[str], seed: str) -> str:
    if len(options) <= 1:
        return "、".join(options)
    first = stable_int(seed + ":a") % len(options)
    second = stable_int(seed + ":b") % len(options)
    if second == first:
        second = (second + 1) % len(options)
    return f"{options[first]}、{options[second]}"


def tianji_divination_text(record: UserRecord, question: str, today: Optional[date] = None) -> str:
    clean_question = " ".join(str(question or "").strip().split())[:80] or "未言之事"
    today = today or date.today()
    seed = f"divination:{record.user_id}:{today.isoformat()}:{clean_question}:{record.realm_index}:{record.sign_count}"
    hexagram = stable_choice(DIVINATION_HEXAGRAMS, seed + ":hexagram")
    upper = stable_choice(DIVINATION_TRIGRAMS, seed + ":upper")
    lower = stable_choice(DIVINATION_TRIGRAMS, seed + ":lower")
    changed_yao = stable_choice(DIVINATION_YAO, seed + ":yao")
    image = stable_choice(DIVINATION_IMAGES, seed + ":image")
    fortune, fortune_text = stable_choice(DIVINATION_FORTUNES, seed + ":fortune")
    topic = divination_topic(clean_question)
    advice = stable_choice(DIVINATION_TOPIC_ADVICES[topic], seed + ":advice")
    yi = divination_pick_pair(DIVINATION_YI, seed + ":yi")
    ji = divination_pick_pair(DIVINATION_JI, seed + ":ji")
    realm = record.realm if record.root else "未入门"
    root_text = record.root_summary if record.root else "未觉醒灵根"
    lines = [
        "【天机占卜】",
        f"所问：{clean_question}",
        f"命盘：{realm}，{root_text}",
        f"起卦：{hexagram}；变爻：{changed_yao}；签等：{fortune}",
        f"卦象：{upper[0]}{upper[1]}在上，{lower[0]}{lower[1]}在下；{image}",
        f"签语：{fortune_text}",
        f"断曰：上卦为{upper[2]}，下卦为{lower[2]}，此事须看时、势、心三处是否相合。",
        f"宜：{yi}",
        f"忌：{ji}",
        f"修士建议：{advice}",
        "注：此为趣味占卜，天机只露一线，取舍仍在宿主自心。",
    ]
    return "\n".join(lines)


def method_max_layer(method: Optional[dict[str, Any]]) -> int:
    return method_layer_cap(method)


def method_layer_required(layer: int) -> int:
    return max(80, int(80 * max(1, layer) ** 1.35))


def method_layer(record: UserRecord, method: Optional[dict[str, Any]]) -> int:
    if not method:
        return 0
    key = reward_signature(method)
    layers = record.method_layers or {}
    current = int(layers.get(key, 0) or 0)
    if current <= 0:
        return 1
    return max(1, min(method_max_layer(method), current))


def method_proficiency_value(record: UserRecord, method: Optional[dict[str, Any]]) -> int:
    if not method:
        return 0
    return max(0, int((record.method_proficiency or {}).get(reward_signature(method), 0)))


def set_method_layer(record: UserRecord, method: Optional[dict[str, Any]], layer: int) -> None:
    if not method:
        return
    if record.method_layers is None:
        record.method_layers = {}
    record.method_layers[reward_signature(method)] = max(1, min(method_max_layer(method), int(layer)))


def increase_method_proficiency(record: UserRecord, amount: int = 1, method: Optional[dict[str, Any]] = None) -> int:
    method_item = method or record.equipped_method
    if not method_item or amount <= 0:
        return 0
    ensure_method_tracking(record, method_item)
    key = reward_signature(method_item)
    layer = method_layer(record, method_item)
    max_layer = method_max_layer(method_item)
    if layer >= max_layer:
        record.method_layers[key] = max_layer
        record.method_proficiency[key] = min(method_layer_required(max_layer), int(record.method_proficiency.get(key, 0)) + amount)
        return 0
    gained_layers = 0
    proficiency = int(record.method_proficiency.get(key, 0)) + amount
    while layer < max_layer and proficiency >= method_layer_required(layer):
        proficiency -= method_layer_required(layer)
        layer += 1
        gained_layers += 1
    record.method_layers[key] = layer
    record.method_proficiency[key] = proficiency
    return gained_layers

def method_kind(method: Optional[dict[str, Any]]) -> str:
    name = reward_name(method)
    if not name:
        return "\u4fee\u70bc\u7c7b"
    if any(token in name for token in ("\u91d1\u8eab", "\u4e0d\u706d", "\u953b", "\u4f53", "\u70bc\u8eab", "\u7a33\u57fa", "\u96f7\u8eab", "\u624e\u9a6c\u6b65")):
        return "\u953b\u4f53\u7c7b"
    if any(token in name for token in ("\u89c2\u60f3", "\u70bc\u795e", "\u795e", "\u9b42", "\u95ee\u5fc3", "\u5165\u9759", "\u9759\u5750", "\u542c\u96f7", "\u609f")):
        return "\u795e\u9b42\u7c7b"
    if any(token in name for token in ("\u5251", "\u65a9", "\u7834", "\u67aa", "\u5203", "\u6cd5", "\u96f7", "\u711a", "\u70c8", "\u5fa1\u98ce")):
        return "\u6218\u6280\u7c7b"
    return stable_choice(METHOD_KIND_NAMES, f"method-kind:{reward_signature(method)}")


def method_required_race(method: Optional[dict[str, Any]], kind: str) -> Optional[str]:
    if not method or kind != "\u6218\u6280\u7c7b":
        return None
    name = reward_name(method)
    if "金羽" in name or "雷鹏" in name:
        return "妖族-金羽雷鹏"
    if "\u9752\u83b2" in name:
        return "\u5996\u65cf-\u9752\u83b2"
    if stable_int(f"race-lock:{reward_signature(method)}") % 100 < 10:
        return stable_choice([race for race, _ in COMBAT_RACES], f"race-lock-choice:{reward_signature(method)}")
    return None


def method_techniques(method: Optional[dict[str, Any]], kind: Optional[str] = None) -> list[str]:
    if not method:
        return []
    custom_techniques = [str(item) for item in method.get("techniques", []) if item]
    if custom_techniques:
        return list(dict.fromkeys(custom_techniques))[:5]
    kind = kind or method_kind(method)
    required = reward_required_attribute(method) or stable_choice(ATTRIBUTES, f"method-attr:{reward_signature(method)}")
    candidates = list(ATTRIBUTE_TECHNIQUE_NAMES.get(required, [])) + GENERAL_TECHNIQUE_NAMES
    seed = f"tech:{reward_signature(method)}"
    offset = stable_int(seed) % len(candidates)
    ordered = candidates[offset:] + candidates[:offset]
    tier_rank = TIER_RANKS.get(str(method.get("tier", "\u51e1\u54c1")), 0)
    grade_rank = GRADE_RANKS.get(str(method.get("grade", "\u4e2d\u54c1")), 1)
    if kind == "\u6218\u6280\u7c7b":
        count = max(1, min(5, 2 + tier_rank // 2 + grade_rank // 2))
    elif kind == "\u795e\u9b42\u7c7b":
        count = 1
    else:
        count = max(1, min(2, 1 + grade_rank // 3))
    return ordered[:count]


def method_origin_text(method: Optional[dict[str, Any]], kind: str) -> str:
    custom_origin = str((method or {}).get("origin") or "")
    if custom_origin:
        return custom_origin
    name = reward_name(method)
    tier = str((method or {}).get("tier", "\u51e1\u54c1"))
    origins = {
        "\u4fee\u70bc\u7c7b": [
            "\u4f20\u95fb\u6b64\u6cd5\u51fa\u81ea\u4e0a\u53e4\u6d1e\u5929\uff0c\u91cd\u5728\u62d3\u5bbd\u7ecf\u8109\u4e0e\u4e39\u7530\u3002",
            "\u6b64\u6cd5\u7531\u6563\u4fee\u8bef\u5165\u7075\u8109\u540e\u609f\u5f97\uff0c\u8bb2\u7a76\u6c34\u78e8\u5de5\u592b\u3002",
        ],
        "\u953b\u4f53\u7c7b": [
            "\u6b64\u6cd5\u6e90\u4e8e\u8fb9\u8352\u53e4\u6218\u573a\uff0c\u4ee5\u7075\u6c14\u6d17\u70bc\u7b4b\u9aa8\u8840\u9b44\u3002",
            "\u4f20\u8bf4\u4f53\u4fee\u4e00\u8109\u501f\u6b64\u6cd5\u786c\u625b\u96f7\u52ab\uff0c\u8d8a\u6218\u8d8a\u575a\u3002",
        ],
        "\u795e\u9b42\u7c7b": [
            "\u6b64\u6cd5\u89c2\u60f3\u8bc6\u6d77\u660e\u706f\uff0c\u80fd\u5728\u79d8\u5883\u6740\u673a\u524d\u6355\u6349\u4e00\u7ebf\u5f81\u5146\u3002",
            "\u65e7\u7ecf\u79f0\u5176\u53ef\u95ee\u5fc3\u3001\u5b9a\u9b42\u3001\u5bdf\u5384\uff0c\u4fee\u6210\u540e\u4e0d\u6613\u88ab\u5e7b\u5883\u8ff7\u60d1\u3002",
        ],
        "\u6218\u6280\u7c7b": [
            "\u6b64\u6cd5\u591a\u89c1\u4e8e\u5927\u5b97\u8bd5\u70bc\uff0c\u5c06\u7ecf\u4e49\u5316\u4f5c\u6740\u62db\u4e0e\u62a4\u8eab\u6cd5\u3002",
            "\u4f20\u8a00\u67d0\u4f4d\u5251\u4fee\u4ee5\u6b64\u6cd5\u5bf9\u654c\u4e09\u663c\u591c\uff0c\u4ece\u6b64\u540d\u52a8\u4e00\u57df\u3002",
        ],
    }
    prefix = "\u5929\u9636\u6b8b\u7bc7" if tier == "\u5929\u9636" else "\u4f20\u627f\u6ce8\u8bb0"
    return f"{prefix}\uff1a{name}\u3002" + stable_choice(origins.get(kind, origins["\u4fee\u70bc\u7c7b"]), f"origin:{reward_signature(method)}")


def method_content_text(method: Optional[dict[str, Any]], kind: str) -> str:
    custom_content = str((method or {}).get("content") or "")
    if custom_content:
        return custom_content
    name = reward_name(method)
    attribute = reward_required_attribute(method) or stable_choice(ATTRIBUTES, f"content-attr:{reward_signature(method)}")
    attr_name = ATTRIBUTE_NAMES.get(attribute, "\u7075\u6839")
    if kind == "\u4fee\u70bc\u7c7b":
        return f"{name}\u4ee5{attr_name}\u4e3a\u6839\uff0c\u5faa\u73af\u5468\u5929\u3001\u6e29\u517b\u7075\u53f0\uff0c\u4e3b\u589e\u7b7e\u5230\u4e0e\u804a\u5929\u4fee\u4e3a\u6536\u76ca\u3002"
    if kind == "\u953b\u4f53\u7c7b":
        return f"{name}\u5c06{attr_name}\u7075\u6c14\u5316\u5165\u6c14\u8840\uff0c\u589e\u5f3a\u8840\u91cf\u4e0e\u6297\u6253\u65ad\u80fd\u529b\uff0c\u5951\u5408\u4f53\u8d28\u65f6\u6536\u76ca\u66f4\u9ad8\u3002"
    if kind == "\u795e\u9b42\u7c7b":
        return f"{name}\u4e13\u4fee\u8bc6\u6d77\u4e0e\u5fc3\u5ff5\uff0c\u968f\u63a8\u6f14\u6df1\u5165\u53ef\u9010\u6e10\u7aa5\u89c1\u90e8\u5206\u79d8\u5883\u5371\u9669\u3002"
    return f"{name}\u5c06{attr_name}\u7075\u6c14\u538b\u7f29\u6210\u6218\u6280\uff0c\u53ef\u5728\u666e\u901a\u6597\u6cd5\u4e2d\u6839\u636e\u53d1\u8a00\u89e6\u53d1\u3002"


def method_profile(method: Optional[dict[str, Any]], record: Optional[UserRecord] = None) -> dict[str, Any]:
    if not method:
        return {
            "signature": "",
            "name": "\u672a\u53c2\u609f\u529f\u6cd5",
            "display": "\u672a\u53c2\u609f\u529f\u6cd5",
            "kind": "\u65e0",
            "layer": 0,
            "max_layer": 0,
            "proficiency": 0,
            "proficiency_required": 0,
            "origin": "",
            "content": "",
            "sign_speed": 0,
            "chat_speed": 0.0,
            "hp_bonus": 0,
            "soul_insight": False,
            "techniques": [],
            "required_race": None,
        }
    kind = method_kind(method)
    layer = method_layer(record, method) if record is not None else 1
    max_layer = method_max_layer(method)
    proficiency = method_proficiency_value(record, method) if record is not None else 0
    proficiency_required = method_layer_required(layer) if layer < max_layer else method_layer_required(max_layer)
    tier = str(method.get("tier", "\u51e1\u54c1"))
    grade = str(method.get("grade", "\u4e2d\u54c1"))
    purity_mult = root_purity_multiplier(record, reward_required_attribute(method)) if record is not None else 1.0
    sign_speed = int(10 * METHOD_SIGN_RATE.get(tier, 0.08) * grade_ratio(grade) * max(1, layer) * purity_mult)
    chat_speed = METHOD_CHAT_BASE.get(tier, 0.35) * grade_ratio(grade) * max(1.0, layer / 2) * purity_mult
    hp_bonus = 0
    if kind == "\u953b\u4f53\u7c7b":
        hp_bonus = max(60, int(method_power(method, record) * (0.18 + layer * 0.035)))
    techniques = method_techniques(method, kind)
    return {
        "signature": reward_signature(method),
        "name": reward_name(method),
        "display": reward_display_name(method),
        "kind": kind,
        "layer": layer,
        "max_layer": max_layer,
        "max_layer_text": method_layer_cap_text(method),
        "proficiency": proficiency,
        "proficiency_required": proficiency_required,
        "origin": method_origin_text(method, kind),
        "content": method_content_text(method, kind),
        "sign_speed": sign_speed,
        "chat_speed": chat_speed,
        "hp_bonus": hp_bonus,
        "soul_insight": kind == "\u795e\u9b42\u7c7b" and layer >= SOUL_INSIGHT_LAYER,
        "techniques": techniques,
        "required_race": method_required_race(method, kind),
    }


def format_method_detail(record: UserRecord, method_index: int) -> tuple[bool, str]:
    methods = available_methods(record)
    if method_index < 1 or method_index > len(methods):
        return False, f"\u8bf7\u9009\u62e9 1-{len(methods)} \u4e4b\u95f4\u7684\u529f\u6cd5\u7f16\u53f7\u3002" if methods else "\u6682\u65e0\u53ef\u5b66\u4e60\u529f\u6cd5\u3002"
    method = methods[method_index - 1]
    profile = method_profile(method, record)
    compatible = "\u5951\u5408" if item_is_compatible(record, method) else "\u7075\u6839\u4e0d\u5951\u5408"
    race_req = profile.get("required_race") or "\u65e0"
    technique_parts = [
        f"{tech}\uff08\u8017\u7075{technique_mana_cost(record, tech)} / CD{technique_cooldown(tech)}\u606f\uff09"
        for tech in profile["techniques"]
    ]
    techniques = "\u3001".join(technique_parts) or "\u6682\u65e0"
    lines = [
        f"\u3010\u529f\u6cd5\u9875\u3011{profile['display']}",
        f"\u7c7b\u578b\uff1a{profile['kind']}\uff1b\u5c42\u6570\uff1a\u7b2c {profile['layer']} / {profile['max_layer_text']} \u5c42\uff1b\u7075\u6839\uff1a{compatible}",
        f"\u79cd\u65cf\u9650\u5236\uff1a{race_req}",
        f"\u4fee\u70bc\u901f\u5ea6\uff1a\u7b7e\u5230\u7ea6 +{profile['sign_speed']} \u70b9/\u5929\uff0c\u804a\u5929\u7ea6 +{profile['chat_speed']:.1f} \u70b9/\u6761",
        f"\u953b\u4f53\u8840\u91cf\uff1a+{profile['hp_bonus']}",
        f"\u795e\u9b42\u611f\u77e5\uff1a{'\u5df2\u5f00\u542f\u79d8\u5883\u5371\u9669\u7aa5\u89c1' if profile['soul_insight'] else '\u672a\u5f00\u542f'}",
        f"\u6218\u6280\uff1a{techniques}",
        "\u3010\u6765\u5386\u3011",
        str(profile["origin"]),
        "\u3010\u5185\u5bb9\u3011",
        str(profile["content"]),
        "\u53d1\u9001\u201c\u53c2\u609f\u529f\u6cd5 \u7f16\u53f7\u201d\u53ef\u8bbe\u4e3a\u5f53\u524d\u4fee\u884c\u529f\u6cd5\u3002",
    ]
    return True, "\n".join(lines)


def has_soul_insight(record: UserRecord) -> bool:
    profile = method_profile(record.equipped_method, record)
    return bool(profile.get("soul_insight"))


def combat_root_text(record: UserRecord) -> str:
    return record.root_summary if record.root else "\u672a\u89c9\u9192\u7075\u6839"


def ensure_combat_profile(record: UserRecord) -> bool:
    changed = False
    if not record.combat_race:
        record.combat_race = weighted_choice_stable(COMBAT_RACES, f"race:{record.user_id}")
        changed = True
    if not record.physique:
        record.physique = weighted_choice_stable(COMBAT_PHYSIQUES, f"physique:{record.user_id}")
        changed = True
    abilities = normalize_special_abilities(record.special_abilities)
    if abilities != list(record.special_abilities or []):
        record.special_abilities = abilities
        changed = True
    if record.method_layers is None:
        record.method_layers = {}
        changed = True
    return changed


def physique_hp_multiplier(physique: Optional[str]) -> float:
    return {
        "\u51e1\u4f53": 1.0,
        "\u77f3\u7334\u5e9f\u8109": 0.94,
        "远荒战体": 1.28,
        "先天道胚": 1.12,
        "玄阴灵体": 1.1,
        "赤阳灵体": 1.12,
        "青华灵体": 1.15,
        "金羽神脉": 1.08,
        "身界蕴种": 1.22,
        "浑元战魔体": 1.34,
    }.get(str(physique), 1.0)


def method_physique_multiplier(record: UserRecord, profile: dict[str, Any]) -> float:
    physique = record.physique or ""
    name = str(profile.get("name", ""))
    if not physique or not name:
        return 1.0
    pairs = (
        ("远荒战体", ("\u91d1\u8eab", "\u4e0d\u706d", "\u953b\u4f53")),
        ("浑元战魔体", ("\u6df7\u6c8c", "\u4e07\u8c61", "空衡")),
        ("青华灵体", ("\u9752\u83b2", "\u957f\u751f", "\u4e07\u7075")),
        ("玄阴灵体", ("玄阴", "\u7384\u51b0", "\u5bd2")),
        ("赤阳灵体", ("赤阳", "\u771f\u706b", "\u79bb\u706b")),
    )
    for body, tokens in pairs:
        if physique == body and any(token in name for token in tokens):
            return 1.35
    return 1.0



def combat_max_hp(record: UserRecord) -> int:
    ensure_combat_profile(record)
    profile = method_profile(record.equipped_method, record)
    base = 900 + record.realm_index * 420 + max(0, record.realm_exp) * 3 + record.sign_count * 12
    base += int(battle_power(record) * 0.08)
    hp_bonus = int(profile.get("hp_bonus", 0) * method_physique_multiplier(record, profile))
    return max(500, int((base + hp_bonus) * physique_hp_multiplier(record.physique)))


def realm_quality_mana_multiplier(record: UserRecord) -> float:
    quality = realm_quality_text(record)
    if not quality:
        return 1.0
    if quality in {"\u5929\u9053\u7b51\u57fa", "\u5b8c\u7f8e\u9053\u57fa"}:
        return 1.28
    if quality == "\u4f18\u79c0\u7b51\u57fa":
        return 1.18
    if quality == "\u826f\u597d\u7b51\u57fa":
        return 1.1
    if "\u4e00\u54c1" in quality:
        return 1.30
    if "\u4e8c\u54c1" in quality:
        return 1.24
    if "\u4e09\u54c1" in quality:
        return 1.18
    if "\u56db\u54c1" in quality:
        return 1.12
    if "\u4e94\u54c1" in quality:
        return 1.06
    if any(token in quality for token in ("\u5929\u9053", "\u6df7\u5143", "\u65e0\u6781", "\u8d85\u8131", "\u6c38\u6052")):
        return 1.32
    if any(token in quality for token in ("\u9053", "\u5723", "\u4ed9", "\u771f")):
        return 1.18
    return 1.0


def combat_max_mana(record: UserRecord) -> int:
    ensure_combat_profile(record)
    root_bonus = 0
    if record.root:
        root_bonus = record.root.tier_rank * 42 + record.root.grade_rank * 28
    realm_bonus = record.realm_index * 185 + int(max(0, record.realm_exp) * 1.4)
    sign_bonus = min(420, record.sign_count * 4)
    base = 220 + realm_bonus + root_bonus + sign_bonus + int(realm_quality_power(record) * 0.12)
    profile = method_profile(record.equipped_method, record)
    if profile.get("kind") == "\u795e\u9b42\u7c7b":
        base = int(base * 1.12)
    if profile.get("kind") == "\u6218\u6280\u7c7b":
        base = int(base * 1.06)
    if record.realm_index >= true_immortal_realm_index():
        base = int(base * 1.18)
    return max(120, int(base * realm_quality_mana_multiplier(record)))


def available_battle_techniques(record: UserRecord) -> list[str]:
    profile = method_profile(record.equipped_method, record)
    techniques = list(profile.get("techniques") or [])
    if profile.get("required_race") and profile.get("required_race") != record.combat_race:
        techniques = techniques[:1]
    if not techniques and record.root:
        techniques = ATTRIBUTE_TECHNIQUE_NAMES.get(record.root.attribute, [])[:1]
    return techniques


def technique_power(record: UserRecord, technique: str, improvised: bool = False) -> int:
    profile = method_profile(record.equipped_method, record)
    layer = int(profile.get("layer", 0))
    base = max(20, int(battle_power(record) * (0.055 + layer * 0.006)))
    if profile.get("kind") == "\u6218\u6280\u7c7b":
        base = int(base * 1.22)
    if improvised:
        base = int(base * 0.72)
    return max(12, base)


def technique_mana_cost(record: UserRecord, technique: str, improvised: bool = False) -> int:
    profile = method_profile(record.equipped_method, record)
    layer = int(profile.get("layer", 1))
    tech_seed = stable_int(f"mana-cost:{technique}") % 19
    base = 34 + record.realm_index * 9 + layer * 7 + tech_seed
    if profile.get("kind") == "\u6218\u6280\u7c7b":
        base = int(base * 1.12)
    if improvised:
        base = int(base * 0.78)
    return max(18, base)


def technique_cooldown(technique: str, improvised: bool = False) -> int:
    base = 2 + stable_int(f"tech-cd:{technique}") % 4
    if improvised:
        base = max(1, base - 1)
    return base


def physical_attack_power(record: UserRecord) -> int:
    return max(10, int(battle_power(record) * (0.05 + min(0.035, record.realm_index * 0.002))))


def physique_trait_power(record: UserRecord) -> int:
    trait = PHYSIQUE_TRAIT_NAMES.get(str(record.physique or ""))
    if not trait:
        return 0
    return max(18, int(battle_power(record) * (0.075 + record.realm_index * 0.003)))


def combat_special_power(record: UserRecord, ability: str, kind: str) -> tuple[int, int, int, str]:
    power = battle_power(record)
    info = special_ability_info(ability)
    damage_rate, defense_rate, speed_bonus = info.get("combat", (0.08, 0.04, 0))
    multiplier = nine_secret_set_multiplier(record) if kind == "secret" else 1
    damage = int(power * float(damage_rate) * multiplier)
    defense = int(power * float(defense_rate) * multiplier)
    speed = int(speed_bonus) * multiplier
    rarity = special_ability_rarity_text(ability)
    if ability in FORBIDDEN_REALM_ABILITIES:
        return damage, defense, speed, f"触发{rarity}【{ability}】，限界气机展开。"
    if kind == "secret":
        return damage, defense, speed, f"触发{rarity}【{ability}】，星律共鸣共鸣{multiplier}倍，已悟星律同步增强{multiplier}倍。"
    return damage, defense, speed, f"触发{rarity}神通【{ability}】：{info.get('effect', '神通气机展开。')}"


def sanitize_combat_text(text: str) -> str:
    return re.sub(r"[\s,\u002c\u3001\uff0c\u3002.!\uff01\?\uff1f:\uff1a;\[\]\uff08\uff09()]+", "", str(text or ""))


def evaluate_combat_actions(record: UserRecord, actions: Sequence[dict[str, Any]], side_seed: str = "") -> dict[str, Any]:
    ensure_combat_profile(record)
    available = available_battle_techniques(record)
    abilities = normalize_special_abilities(record.special_abilities)
    triggered: list[str] = []
    logs: list[str] = []
    damage = int(battle_power(record) * 0.18)
    defense = int(battle_power(record) * 0.045)
    speed = 0
    action_limit = 8
    max_mana = combat_max_mana(record)
    mana = max_mana
    cooldowns: dict[str, int] = {}
    mana_spent = 0
    physical_hits = 0
    trait_triggers = 0
    equipped_talisman = record.equipped_talisman
    equipped_talisman_power = talisman_power(equipped_talisman, record)
    equipped_talisman_name_text = equipped_talisman_name(record) if equipped_talisman_power > 0 else ""
    if equipped_talisman_power > 0:
        damage += int(equipped_talisman_power * 0.72)
        defense += int(equipped_talisman_power * 0.52)
        logs.append(f"\u7b26\u7b93\u680f\u3010{equipped_talisman_name_text}\u3011\u62a4\u6301\u672c\u573a\u6597\u6cd5\uff0c\u4e0d\u6d88\u8017")
    elif equipped_talisman:
        logs.append(f"\u7b26\u7b93\u680f\u3010{equipped_talisman_name(record)}\u3011\u54c1\u9636\u8fc7\u9ad8\uff0c\u5f53\u524d\u5883\u754c\u5c1a\u65e0\u6cd5\u50ac\u52a8")

    def tick_cooldowns() -> None:
        for key in list(cooldowns):
            cooldowns[key] = max(0, int(cooldowns[key]) - 1)
            if cooldowns[key] <= 0:
                cooldowns.pop(key, None)

    def use_physical(reason: str = "") -> None:
        nonlocal damage, physical_hits
        physical_hits += 1
        damage += physical_attack_power(record)
        suffix = f"\uff0c{reason}" if reason else ""
        logs.append(f"\u6539\u4ee5\u8fd1\u8eab\u653b\u4f10{suffix}")

    def maybe_use_trait(reason: str = "") -> bool:
        nonlocal damage, defense, speed, trait_triggers
        trait = PHYSIQUE_TRAIT_NAMES.get(str(record.physique or ""))
        if not trait:
            return False
        trait_triggers += 1
        bonus = physique_trait_power(record)
        damage += bonus
        defense += int(bonus * 0.35)
        if str(record.physique or "") == "金羽神脉":
            speed += 6
        suffix = f"\uff0c{reason}" if reason else ""
        logs.append(f"\u4f53\u8d28\u7279\u6027\u3010{trait}\u3011\u81ea\u884c\u590d\u82cf{suffix}")
        return True

    def cast_technique(tech: str, improvised: bool = False) -> bool:
        nonlocal mana, mana_spent, damage
        cd_left = int(cooldowns.get(tech, 0))
        if cd_left > 0:
            logs.append(f"\u6218\u6280\u3010{tech}\u3011\u5c1a\u9700{cd_left}\u606f\u56de\u6c14")
            use_physical("\u6218\u6280\u672a\u51b7\u5374")
            return False
        cost = technique_mana_cost(record, tech, improvised)
        if mana < cost:
            logs.append(f"\u7075\u529b\u4e0d\u8db3\uff0c\u3010{tech}\u3011\u9700{cost}\u70b9\u7075\u529b")
            if not maybe_use_trait("\u7075\u529b\u89c1\u5e95"):
                use_physical("\u7075\u529b\u89c1\u5e95")
            return False
        mana -= cost
        mana_spent += cost
        cooldowns[tech] = technique_cooldown(tech, improvised)
        damage += technique_power(record, tech, improvised=improvised)
        triggered.append(tech)
        if improvised:
            logs.append(f"\u5373\u5174\u672f\u5f0f\u7275\u52a8\u3010{tech}\u3011\uff0c\u7075\u529b-{cost}\uff0cCD{cooldowns[tech]}\u606f")
        else:
            logs.append(f"\u65bd\u5c55\u6218\u6280\u3010{tech}\u3011\uff0c\u7075\u529b-{cost}\uff0cCD{cooldowns[tech]}\u606f")
        return True

    for idx, action in enumerate(list(actions)[:action_limit], start=1):
        tick_cooldowns()
        raw_text = str(action.get("text", ""))
        text = sanitize_combat_text(raw_text)
        if not text:
            continue
        matched = [tech for tech in available if sanitize_combat_text(tech) and sanitize_combat_text(tech) in text]
        if not matched:
            matched = [tech for tech in GENERAL_TECHNIQUE_NAMES if sanitize_combat_text(tech) in text]
        used_special = False
        forbidden_terms = {
            "归极域": "归极域",
            "开启归极": "归极域",
            "归极": "归极域",
            "重阈": "重阈",
            "开启重阈": "重阈",
            "初阈": "初阈",
            "开启初阈": "初阈",
        }
        requested_forbidden = None
        for term, canonical in forbidden_terms.items():
            if term in text:
                requested_forbidden = canonical
                break
        if requested_forbidden:
            used_special = True
            owned_forbidden = highest_forbidden_ability(abilities)
            if not owned_forbidden:
                logs.append("尚未领悟限界，强行开启只惊起一缕战意。")
            elif forbidden_rank(owned_forbidden) < forbidden_rank(requested_forbidden):
                logs.append(f"尝试开启【{requested_forbidden}】失败，当前只能维持【{owned_forbidden}】。")
            else:
                add_damage, add_defense, add_speed, message = combat_special_power(record, owned_forbidden, "forbidden")
                damage += add_damage
                defense += add_defense
                speed += add_speed
                triggered.append(owned_forbidden)
                logs.append(message)
        if "星律" in text or any(secret.split("-", 1)[-1] in text for secret in abilities if secret.startswith("星律")):
            secrets = [secret for secret in abilities if secret.startswith("星律")]
            used_special = True
            if secrets:
                secret = stable_choice(secrets, f"secret:{side_seed}:{idx}:{text}")
                add_damage, add_defense, add_speed, message = combat_special_power(record, secret, "secret")
                damage += add_damage
                defense += add_defense
                speed += add_speed
                triggered.append(secret)
                logs.append(message)
            else:
                logs.append("尚未悟得星律残篇，天机一闪而逝。")
        for ability in abilities:
            if ability in triggered or ability in FORBIDDEN_REALM_ABILITIES or ability.startswith("星律"):
                continue
            info = special_ability_info(ability)
            terms = [ability, *list(info.get("aliases", []) or [])]
            if not any(sanitize_combat_text(term) and sanitize_combat_text(term) in text for term in terms):
                continue
            used_special = True
            add_damage, add_defense, add_speed, message = combat_special_power(record, ability, "generic")
            damage += add_damage
            defense += add_defense
            speed += add_speed
            triggered.append(ability)
            logs.append(message)
            break
        if matched:
            for tech in matched[:2]:
                cast_technique(tech)
            continue
        if not used_special:
            if available and mana > 0:
                seed = f"improv:{side_seed}:{idx}:{text}:{len(triggered)}"
                cast_technique(stable_choice(available, seed), improvised=True)
            elif mana <= 0:
                if not maybe_use_trait("\u7075\u529b\u8017\u5c3d"):
                    use_physical("\u7075\u529b\u8017\u5c3d")
            else:
                use_physical("\u5373\u5174\u672f\u5f0f\u672a\u6210")
    return {
        "damage": max(1, damage),
        "defense": max(0, defense),
        "speed": speed,
        "triggered": list(dict.fromkeys(triggered)),
        "logs": logs[:8],
        "mana": max(0, mana),
        "max_mana": max_mana,
        "mana_spent": mana_spent,
        "cooldowns": dict(cooldowns),
        "physical_hits": physical_hits,
        "trait_triggers": trait_triggers,
        "talisman": equipped_talisman_name_text or equipped_talisman_name(record),
        "talisman_power": equipped_talisman_power,
    }

def normal_duel_fighter(record: UserRecord, nickname: str, actions: Sequence[dict[str, Any]], side_seed: str) -> dict[str, Any]:
    ensure_combat_profile(record)
    profile = method_profile(record.equipped_method, record)
    action_result = evaluate_combat_actions(record, actions, side_seed)
    return {
        "user_id": record.user_id,
        "nickname": nickname or f"QQ {record.user_id}",
        "power": battle_power(record),
        "realm": record.realm if record.root else "\u672a\u5165\u95e8",
        "root": combat_root_text(record),
        "race": record.combat_race or "\u672a\u8bb0\u5f55",
        "physique": record.physique or "\u672a\u8bb0\u5f55",
        "abilities": normalize_special_abilities(record.special_abilities),
        "method": profile.get("display", "\u672a\u53c2\u609f\u529f\u6cd5"),
        "method_kind": profile.get("kind", "\u65e0"),
        "talisman": action_result.get("talisman", equipped_talisman_name(record)),
        "talisman_power": int(action_result.get("talisman_power", talisman_power(record.equipped_talisman, record))),
        "available_techniques": available_battle_techniques(record),
        "triggered_techniques": action_result["triggered"],
        "logs": action_result["logs"],
        "damage": int(action_result["damage"]),
        "defense": int(action_result["defense"]),
        "speed": int(action_result["speed"]),
        "mana": int(action_result.get("mana", 0)),
        "max_mana": int(action_result.get("max_mana", combat_max_mana(record))),
        "mana_spent": int(action_result.get("mana_spent", 0)),
        "cooldowns": dict(action_result.get("cooldowns", {})),
        "physical_hits": int(action_result.get("physical_hits", 0)),
        "trait_triggers": int(action_result.get("trait_triggers", 0)),
        "max_hp": combat_max_hp(record),
        "hp": combat_max_hp(record),
    }


def simulate_normal_duel(
    left: UserRecord,
    right: UserRecord,
    left_name: str,
    right_name: str,
    left_actions: Sequence[dict[str, Any]],
    right_actions: Sequence[dict[str, Any]],
    duration_seconds: int = 60,
) -> dict[str, Any]:
    left_fighter = normal_duel_fighter(left, left_name, left_actions, f"{left.user_id}:{right.user_id}:left")
    right_fighter = normal_duel_fighter(right, right_name, right_actions, f"{right.user_id}:{left.user_id}:right")
    left_output = max(1, int(left_fighter["damage"] - right_fighter["defense"] * 0.55))
    right_output = max(1, int(right_fighter["damage"] - left_fighter["defense"] * 0.55))
    left_fighter["dealt_damage"] = 0
    right_fighter["dealt_damage"] = 0
    left_fighter["raw_output"] = left_output
    right_fighter["raw_output"] = right_output

    left_initiative = (
        int(left_fighter["speed"]),
        int(left_fighter["power"]),
        stable_int(f"initiative:{left.user_id}:{right.user_id}") % 100,
    )
    right_initiative = (
        int(right_fighter["speed"]),
        int(right_fighter["power"]),
        stable_int(f"initiative:{right.user_id}:{left.user_id}") % 100,
    )
    if left_initiative >= right_initiative:
        attack_order = [(left_fighter, right_fighter, left_output), (right_fighter, left_fighter, right_output)]
    else:
        attack_order = [(right_fighter, left_fighter, right_output), (left_fighter, right_fighter, left_output)]

    ended_early = False
    elapsed_seconds = duration_seconds
    finisher: Optional[dict[str, Any]] = None
    timeline: list[str] = []
    first_attacker, first_defender, _ = attack_order[0]
    timeline.append(
        f"{first_attacker['nickname']}\u51ed\u901f\u5ea6\u62a2\u5230\u5148\u624b\uff0c{first_defender['nickname']}\u88ab\u8feb\u8f6c\u5165\u5b88\u52bf\u3002"
    )
    for turn_index, (attacker, defender, output) in enumerate(attack_order, start=1):
        before_hp = max(0, int(defender["hp"]))
        dealt = min(before_hp, max(1, int(output)))
        defender["hp"] = max(0, before_hp - dealt)
        attacker["dealt_damage"] = int(attacker.get("dealt_damage", 0)) + dealt
        timeline.append(
            f"{attacker['nickname']}\u7b2c{turn_index}\u624b\u9020\u6210{dealt}\u70b9\u4f24\u5bb3\uff0c"
            f"{defender['nickname']}\u8840\u91cf\u964d\u81f3{defender['hp']}/{defender['max_hp']}\u3002"
        )
        if defender["hp"] <= 0:
            ended_early = True
            finisher = attacker
            elapsed_seconds = max(5, min(duration_seconds, int(duration_seconds * (0.38 if turn_index == 1 else 0.68))))
            timeline.append(
                f"{attacker['nickname']}\u6293\u4f4f\u7834\u7efd\u5b9a\u4e0b\u80dc\u8d1f\uff0c{defender['nickname']}\u5df2\u65e0\u529b\u53cd\u51fb\u3002"
            )
            break

    if finisher is left_fighter:
        winner = left_fighter
        loser = right_fighter
    elif finisher is right_fighter:
        winner = right_fighter
        loser = left_fighter
    elif left_fighter["hp"] > right_fighter["hp"]:
        winner = left_fighter
        loser = right_fighter
    elif right_fighter["hp"] > left_fighter["hp"]:
        winner = right_fighter
        loser = left_fighter
    else:
        left_score = left_fighter["power"] + left_fighter["speed"] * 40 + stable_int(f"tie:{left.user_id}:{right.user_id}") % 100
        right_score = right_fighter["power"] + right_fighter["speed"] * 40 + stable_int(f"tie:{right.user_id}:{left.user_id}") % 100
        winner, loser = (left_fighter, right_fighter) if left_score >= right_score else (right_fighter, left_fighter)
    for log in left_fighter["logs"][:4]:
        timeline.append(f"{left_fighter['nickname']}\uff1a{log}")
    for log in right_fighter["logs"][:4]:
        timeline.append(f"{right_fighter['nickname']}\uff1a{log}")
    if not timeline:
        timeline.append("\u53cc\u65b9\u8bd5\u63a2\u6c14\u673a\uff0c\u7075\u538b\u5728\u6f14\u6b66\u573a\u4e2d\u6765\u56de\u78b0\u649e\u3002")
    return {
        "left": left_fighter,
        "right": right_fighter,
        "winner": winner,
        "loser": loser,
        "winner_id": winner["user_id"],
        "winner_name": winner["nickname"],
        "ended_early": ended_early,
        "elapsed_seconds": elapsed_seconds,
        "remaining_seconds": max(0, duration_seconds - elapsed_seconds),
        "duration_seconds": duration_seconds,
        "timeline": timeline[:8],
        "summary": f"{winner['nickname']}\u80dc\u51fa\uff0c\u5269\u4f59\u8840\u91cf {winner['hp']}/{winner['max_hp']}\u3002",
    }

def item_is_compatible(record: UserRecord, item: dict[str, Any]) -> bool:
    required_attribute = reward_required_attribute(item)
    if not required_attribute:
        return True
    return required_attribute in record.root_attributes


def array_multiplier_cap(array: Optional[dict[str, Any]], layer: Optional[int] = None) -> float:
    if not array:
        return 1.0
    tier = str(array.get("tier", "凡品"))
    current_layer = max(1, int(layer or 1))
    if tier == "仙阶":
        return max(20.0, current_layer * 20.0)
    return ARRAY_MULTIPLIER_CAP_BY_TIER.get(tier, 5.0)


def array_multiplier(record: UserRecord, method: Optional[dict[str, Any]] = None) -> float:
    if not record.equipped_array:
        return 1.0
    array = record.equipped_array
    layer = array_layer(record, array)
    proficiency = array_proficiency_value(record, array)
    cap = array_multiplier_cap(array, layer)
    multiplier = min(cap, 1.0 + proficiency / 100)
    if record.cultivation_route == "阵法师":
        multiplier = min(cap, multiplier * 1.5)
    return multiplier


def increase_array_proficiency(record: UserRecord, amount: int = 1) -> None:
    if not record.equipped_array or amount <= 0:
        return
    array = record.equipped_array
    ensure_array_tracking(record, array)
    key = reward_signature(array)
    gain = amount * (2 if record.cultivation_route == "阵法师" else 1)
    cap = array_proficiency_cap(array, array_layer(record, array))
    record.array_proficiency[key] = min(cap, int(record.array_proficiency.get(key, 0) or 0) + gain)

def method_sign_bonus(record: UserRecord, base_exp: int) -> int:
    method = record.equipped_method
    if not method or not item_is_compatible(record, method):
        return 0
    layer = method_layer(record, method)
    rate = METHOD_SIGN_RATE.get(str(method.get("tier")), 0.0)
    bonus = int(
        base_exp
        * rate
        * grade_ratio(str(method.get("grade")))
        * max(1, layer)
        * array_multiplier(record, method)
        * root_purity_multiplier(record, reward_required_attribute(method))
    )
    return max(1, bonus) if rate > 0 else 0


def method_chat_exp(record: UserRecord, count: int = 1) -> int:
    method = record.equipped_method
    if count <= 0 or not method or not item_is_compatible(record, method):
        return 0
    layer = method_layer(record, method)
    raw = (
        METHOD_CHAT_BASE.get(str(method.get("tier")), 0.0)
        * grade_ratio(str(method.get("grade")))
        * max(1.0, layer / 2)
        * array_multiplier(record, method)
        * root_purity_multiplier(record, reward_required_attribute(method))
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
        increase_method_proficiency(record, max(1, count))
    return applied_exp, leveled


def route_status_text(record: UserRecord) -> str:
    lines = [
        "\u3010\u4fee\u70bc\u8def\u7ebf\u3011",
        f"\u5f53\u524d\u4e3b\u8def\u7ebf\uff1a{record.cultivation_route or '\u672a\u9009\u62e9'}",
        f"\u90aa\u4fee\u540c\u4fee\uff1a{'\u5df2\u5f00\u542f' if record.evil_cultivator else '\u672a\u5f00\u542f'}",
        f"\u5b97\u95e8\u8eab\u4efd\uff1a{record.identity_summary}",
        f"\u5929\u673a\u79d8\u5883\uff1a{tianji_status_text(record)}",
        f"\u53cc\u4fee\u6b21\u6570\uff1a{hehuan_remaining_text(record)}",
        "",
        "\u3010\u4e3b\u4fee\u8def\u7ebf\u3011",
        "\u5251\u4fee\uff1a\u88c5\u5907\u5251\u7c7b\u7075\u5668\u65f6\u6218\u529b\u63d0\u534730%\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8def\u7ebf \u5251\u4fee\u3002",
        "\u672f\u4fee\uff1a\u88c5\u5907\u975e\u5251\u7c7b\u7075\u5668\u65f6\u6cd5\u672f\u4f24\u5bb3\u63d0\u534730%\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8def\u7ebf \u672f\u4fee\u3002",
        "\u70bc\u4e39\u5e08\uff1a\u53ef\u4f7f\u7528\u7075\u6750\u3001\u7075\u690d\u548c\u7075\u77f3\u70bc\u5236\u4e39\u836f\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8def\u7ebf \u70bc\u4e39\u5e08\u3002",
        "\u9635\u6cd5\u5e08\uff1a\u9635\u6cd5\u719f\u7ec3\u5ea6\u63d0\u5347\u66f4\u5feb\uff0c\u9635\u6cd5\u6548\u679c\u63d0\u534750%\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8def\u7ebf \u9635\u6cd5\u5e08\u3002",
        "\u70bc\u5668\u5e08\uff1a\u53ef\u4f7f\u7528\u7075\u6750\u548c\u7075\u77f3\u70bc\u5236\u7075\u5668\u3001\u9635\u76d8\u4e0e\u4eff\u5236\u4ed9\u5e1d\u5175\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8def\u7ebf \u70bc\u5668\u5e08\u3002",
        "",
        "\u3010\u90aa\u4fee\u540c\u4fee\u3011",
        "\u6307\u4ee4\uff1a\u9009\u62e9\u90aa\u4fee / \u9000\u51fa\u90aa\u4fee\u3002\u90aa\u4fee\u53ef\u4e0e\u4e3b\u8def\u7ebf\u5e76\u5b58\uff0c\u4f46\u574f\u7ed3\u5c40\u60e9\u7f5a\u66f4\u91cd\u3002",
        "",
        "\u3010\u5b97\u95e8\u8eab\u4efd\u600e\u4e48\u9009\u3011",
        "\u5929\u673a\u9601\u5f1f\u5b50\uff1a\u9700\u7b51\u57fa\uff0c\u6bcf7\u5929\u4e00\u6b21\u7279\u6b8a\u79d8\u5883\u793a\u8b66\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8eab\u4efd \u5929\u673a\u9601\u5f1f\u5b50\u3002",
        "\u5929\u673a\u9601\u957f\u8001\uff1a\u9700\u5143\u5a74\uff0c\u4e14\u5f1f\u5b50\u8eab\u4efd\u7b7e\u523010\u5929\uff0c\u6bcf5\u5929\u4e00\u6b21\u793a\u8b66\u79d8\u5883\u3002",
        "\u5929\u673a\u9601\u592a\u4e0a\u957f\u8001\uff1a\u9700\u70bc\u865a\uff0c\u4e14\u957f\u8001\u8eab\u4efd\u7b7e\u523030\u5929\uff0c\u6bcf\u5929\u4e00\u6b21\u793a\u8b66\u79d8\u5883\u3002",
        "\u5408\u6b22\u5b97\u5f1f\u5b50\uff1a\u9700\u7ec3\u6c14\u4e2d\u671f\uff0c\u6bcf\u59291\u6b21\u53cc\u4fee\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8eab\u4efd \u5408\u6b22\u5b97\u5f1f\u5b50\u3002",
        "\u5408\u6b22\u5b97\u957f\u8001\uff1a\u9700\u91d1\u4e39\uff0c\u4e14\u5f1f\u5b50\u8eab\u4efd\u7b7e\u523010\u5929\uff0c\u6bcf\u59292\u6b21\u53cc\u4fee\u3002",
        "\u5408\u6b22\u5b97\u592a\u4e0a\u957f\u8001\uff1a\u9700\u5316\u795e\uff0c\u4e14\u957f\u8001\u8eab\u4efd\u7b7e\u523020\u5929\uff0c\u6bcf\u59295\u6b21\u53cc\u4fee\u3002",
    ]
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
        return True, "已同修邪修路线。秘境中不会因邪修陷阱直接落入坏结局，若真正反噬则进入5分钟禁修期。"
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
    actor_exp, _ = apply_exp(actor, exp, today)
    target_exp, _ = apply_exp(target, exp, today)
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
    entries = [entry for entry in draw_mystic_entrances(record) if str(entry.get("type")) not in NO_TIANJI_MYSTIC_TYPES]
    attempts = 0
    while len(entries) < 3 and attempts < 8:
        attempts += 1
        drawn = [entry for entry in draw_mystic_entrances(record) if str(entry.get("type")) not in NO_TIANJI_MYSTIC_TYPES]
        if not drawn:
            break
        for entry in drawn:
            entries.append(entry)
            if len(entries) >= 3:
                break
    if not entries:
        return False, "当前后台未开启可供天机推演的普通秘境。", []
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
    applied_result = apply_exp(record, exp, today)
    applied, leveled = applied_result
    record.spirit_stones += stones
    record.fishing_chances += fishing
    record.daily_tasks = {"date": today.isoformat(), "tasks": tasks}
    extra = f"，连破{leveled}境" if leveled else ""
    fish_text = f"，垂钓+{fishing}" if fishing else ""
    return True, f"完成任务：{task.get('title')}。修为+{applied}{extra}，灵石+{spirit_stone_text(stones)}{fish_text}。"


def recipe_base_quality_text(recipe: dict[str, Any]) -> str:
    return f"{recipe.get('tier', '凡品')}{recipe.get('grade', '中品')}"


def alchemy_text(record: UserRecord) -> str:
    lines = ["【炼丹】", f"当前路线：{record.cultivation_route or '未选择'}", f"灵石：{spirit_stone_text(record.spirit_stones)}"]
    for index, (name, recipe) in enumerate(ALCHEMY_RECIPES.items(), start=1):
        materials = "、".join(recipe["materials"])
        lines.append(
            f"{index}. {name}：基准{recipe_base_quality_text(recipe)}；{materials}；"
            f"炉资{spirit_stone_text(int(recipe['cost']))}；难度{int(recipe.get('difficulty', 8))}"
        )
    lines.append("材料品阶与品质会影响成功率、升阶率和成丹品质。发送“炼丹 丹药名”，例如：炼丹 筑基丹。")
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


def rewards_and_positions_by_names(record: UserRecord, names: Sequence[str]) -> list[tuple[int, dict[str, Any]]]:
    results: list[tuple[int, dict[str, Any]]] = []
    used = set()
    for name in names:
        for list_index, reward in enumerate(record.rewards or []):
            if list_index in used:
                continue
            if reward_name(reward) == name:
                results.append((list_index, normalize_reward(reward, record)))
                used.add(list_index)
                break
    return results


def quality_score_from_tier_grade(tier: str, grade: str) -> int:
    return TIER_RANKS.get(str(tier), 0) * 4 + GRADE_RANKS.get(str(grade), 0)


def tier_grade_from_quality_score(score: int) -> tuple[str, str]:
    max_score = len(TIER_ORDER) * len(GRADE_ORDER) - 1
    score = max(0, min(max_score, int(score)))
    tier_rank, grade_rank = divmod(score, 4)
    tier = TIER_ORDER[max(0, min(len(TIER_ORDER) - 1, tier_rank))]
    grade = GRADE_ORDER[max(0, min(len(GRADE_ORDER) - 1, grade_rank))]
    return tier, grade


def alchemy_material_score(materials: Sequence[dict[str, Any]]) -> float:
    if not materials:
        return 0.0
    return sum(item_quality_score(material) for material in materials) / len(materials)


def alchemy_roll_quality(recipe: dict[str, Any], materials: Sequence[dict[str, Any]]) -> tuple[bool, str, str, int, int, int]:
    base_score = quality_score_from_tier_grade(str(recipe.get("tier", "凡品")), str(recipe.get("grade", "中品")))
    material_score = alchemy_material_score(materials)
    difficulty = int(recipe.get("difficulty", 8))
    surplus = material_score - difficulty
    success_rate = max(0.18, min(0.96, 0.58 + surplus * 0.045))
    high_rate = max(0.04, min(0.62, 0.12 + surplus * 0.035))
    if random.random() > success_rate:
        return False, "凡品", "下品", int(success_rate * 100), int(high_rate * 100), base_score
    delta = 0
    if random.random() < high_rate:
        delta += 1
    if random.random() < max(0.02, high_rate * 0.45):
        delta += 1
    if surplus >= 5 and random.random() < 0.16:
        delta += 1
    if surplus < -3 and random.random() < 0.28:
        delta -= 1
    final_score = max(0, min(19, base_score + delta))
    tier, grade = tier_grade_from_quality_score(final_score)
    return True, tier, grade, int(success_rate * 100), int(high_rate * 100), final_score


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
    found = rewards_and_positions_by_names(record, materials)
    if len(found) < len(materials):
        owned = [reward_name(reward) for reward in record.rewards or []]
        missing = [name for name in materials if name not in owned]
        return False, f"材料不足，缺少：{'、'.join(missing)}。"
    if record.rewards is None:
        return False, "材料不足。"
    material_items = [reward for _, reward in found]
    success, tier, grade, success_rate, high_rate, final_score = alchemy_roll_quality(recipe, material_items)
    for list_index, _ in sorted(found, reverse=True):
        record.rewards.pop(list_index)
    record.spirit_stones -= cost
    material_text = "、".join(reward_display_name(item) for item in material_items)
    if not success:
        ash_tier, ash_grade = tier_grade_from_quality_score(max(0, int(alchemy_material_score(material_items)) - 4))
        ash = make_reward(ash_tier, ash_grade, MISC_CATEGORY, "焦黑丹渣")
        append_reward(record, ash)
        return (
            False,
            f"丹炉轰鸣，火候失守。消耗材料：{material_text}\n"
            f"本炉成功率约{success_rate}%，升品率约{high_rate}%。炼丹失败，仅得 {reward_display_name(ash)}。"
        )
    pill = make_reward(tier, grade, PILL_CATEGORY, pill_name.strip())
    append_reward(record, pill)
    return (
        True,
        f"丹炉火候已成，消耗材料：{material_text}\n"
        f"本炉成功率约{success_rate}%，升品率约{high_rate}%，成丹评分{final_score}/19。\n"
        f"炼出 {reward_display_name(pill)}，炉资 {spirit_stone_text(cost)}。"
    )


def available_immortal_seeds(record: UserRecord) -> list[dict[str, Any]]:
    items = rewards_by_category(record, IMMORTAL_SEED_CATEGORY)
    for seed in record.immortal_seeds or []:
        if isinstance(seed, dict):
            items.append(normalize_reward(seed, record))
    return items


def immortal_seed_power(seed: Optional[dict[str, Any]], record: Optional[UserRecord] = None) -> int:
    if not seed:
        return 0
    base = int(ARTIFACT_POWER_BASE.get(str(seed.get("tier")), 320) * 0.62)
    ratio = ARTIFACT_GRADE_RATIO.get(str(seed.get("grade")), 1.0)
    realm_rate = 1.0 + ((record.realm_index if record else 0) * 0.05)
    return int(base * ratio * realm_rate)


def equipped_immortal_seed_name(record: UserRecord) -> str:
    return reward_display_name(record.equipped_immortal_seed) if record.equipped_immortal_seed else "未纳入仙源"


def equip_immortal_seed(record: UserRecord, seed_index: int) -> tuple[bool, str]:
    seeds = available_immortal_seeds(record)
    if seed_index < 1 or seed_index > len(seeds):
        return False, f"请选择 1-{len(seeds)} 之间的仙源编号。"
    required = REALMS.index("\u771f\u4ed9\u5883")
    if record.realm_index < required:
        return False, "真仙境后才可纳入仙源。"
    seed = normalize_reward(dict(seeds[seed_index - 1]), record)
    record.equipped_immortal_seed = seed
    return True, f"已纳入 {reward_display_name(seed)}，战力+{immortal_seed_power(seed, record)}。"


def immortal_seed_text(record: UserRecord) -> str:
    seeds = available_immortal_seeds(record)
    lines = ["【仙源】", f"当前仙源：{equipped_immortal_seed_name(record)}"]
    if not seeds:
        lines.append("暂无仙源。高危险秘境、天机事件和唯一道具掉落可获得。")
    for index, seed in enumerate(seeds, start=1):
        info = IMMORTAL_SEED_INFOS.get(reward_name(seed), {})
        lines.append(f"{index}. {reward_display_name(seed)}\uff5c{info.get('effect', seed.get('description', ''))}\uff5c\u6218\u529b+{immortal_seed_power(seed, record)}")
    lines.append("发送“装备仙源 编号”可在真仙后纳入己身；旧指令“装备仙种”仍兼容。")
    return "\n".join(lines)


def refining_text(record: UserRecord) -> str:
    lines = ["\u3010\u70bc\u5668\u3011", f"\u5f53\u524d\u8def\u7ebf\uff1a{record.cultivation_route or '\u672a\u9009\u62e9'}", f"\u7075\u77f3\uff1a{spirit_stone_text(record.spirit_stones)}"]
    lines.append("\u70bc\u5668\u5e08\u53ef\u4ee5\u4f7f\u7528\u7075\u6750\u3001\u7075\u5668\u548c\u9635\u76d8\u70bc\u6210\u9ad8\u9636\u88c5\u5907\u3002\u6750\u6599\u54c1\u8d28\u8d8a\u9ad8\uff0c\u6210\u54c1\u54c1\u76f8\u8d8a\u7a33\u3002")
    for index, (name, recipe) in enumerate(ARTIFACT_REFINING_RECIPES.items(), start=1):
        mats = "\u3001".join(recipe["materials"][:6])
        if len(recipe["materials"]) > 6:
            mats += f"\u7b49{len(recipe['materials'])}\u4ef6"
        category = recipe.get("category", ARTIFACT_CATEGORY)
        lines.append(f"{index}. {name}\uff1a{recipe['tier']}{recipe['grade']}{category}\uff5c\u9700{REALMS[int(recipe.get('required_realm', 0))]}\uff5c{mats}\uff5c{spirit_stone_text(int(recipe['cost']))}")
    lines.append("\u53d1\u9001\u201c\u70bc\u5668 \u540d\u79f0\u201d\u5f00\u7089\uff0c\u4f8b\u5982\uff1a\u70bc\u5668 \u9752\u7af9\u8702\u4e91\u5251\u3002")
    return "\n".join(lines)


def refining_material_items(record: UserRecord, materials: Sequence[str]) -> Optional[list[tuple[int, dict[str, Any]]]]:
    found: list[tuple[int, dict[str, Any]]] = []
    used: set[int] = set()
    for name in materials:
        match = None
        for list_index, reward in enumerate(record.rewards or []):
            if list_index in used:
                continue
            if reward_name(reward) == name:
                match = (list_index, normalize_reward(reward, record))
                break
        if match is None:
            return None
        used.add(match[0])
        found.append(match)
    return found


def refine_artifact_by_recipe(record: UserRecord, item_name: str) -> tuple[bool, str]:
    if record.cultivation_route != "\u70bc\u5668\u5e08":
        return False, "\u53ea\u6709\u9009\u62e9\u70bc\u5668\u5e08\u8def\u7ebf\u540e\uff0c\u624d\u80fd\u4f7f\u7528\u70bc\u5668\u529f\u80fd\u3002"
    recipe = ARTIFACT_REFINING_RECIPES.get(item_name.strip())
    if not recipe:
        return False, f"\u672a\u627e\u5230\u70bc\u5668\u56fe\u8c31\uff1a{item_name}\u3002"
    required_realm = int(recipe.get("required_realm", 0))
    if record.realm_index < required_realm:
        return False, f"\u70bc\u5236{item_name}\u9700\u81f3\u5c11\u8fbe\u5230{REALMS[required_realm]}\u3002"
    cost = int(recipe.get("cost", 0))
    if record.spirit_stones < cost:
        return False, f"\u7075\u77f3\u4e0d\u8db3\uff0c\u5f00\u7089\u9700\u8981 {spirit_stone_text(cost)}\u3002"
    found = refining_material_items(record, recipe["materials"])
    if found is None:
        owned_names = [reward_name(reward) for reward in record.rewards or []]
        missing = []
        temp = list(owned_names)
        for name in recipe["materials"]:
            if name in temp:
                temp.remove(name)
            else:
                missing.append(name)
        return False, f"\u6750\u6599\u4e0d\u8db3\uff0c\u7f3a\u5c11\uff1a{'\u3001'.join(missing[:8])}{'\u7b49' if len(missing) > 8 else ''}\u3002"
    material_items = [item for _, item in found]
    avg_score = sum(item_quality_score(item) for item in material_items) / max(1, len(material_items))
    base_score = quality_score_from_tier_grade(str(recipe.get("tier")), str(recipe.get("grade")))
    bonus = 1 if avg_score >= base_score + 2 else 0
    if random.random() < 0.18:
        bonus += 1
    tier, grade = tier_grade_from_quality_score(base_score + bonus)
    category = str(recipe.get("category", ARTIFACT_CATEGORY))
    for list_index, _ in sorted(found, reverse=True):
        if record.rewards is not None:
            record.rewards.pop(list_index)
    record.spirit_stones -= cost
    item = make_reward(tier, grade, category, item_name.strip())
    item["crafted"] = True
    item["min_realm_index"] = int(recipe.get("required_realm", item_required_realm_index(item)))
    append_reward(record, item)
    material_text = "\u3001".join(reward_display_name(item) for item in material_items[:8])
    if len(material_items) > 8:
        material_text += f"\u7b49{len(material_items)}\u4ef6"
    return True, f"\u7089\u706b\u6536\u675f\uff0c\u6d88\u8017{material_text}\uff0c\u70bc\u6210 {reward_display_name(item)}\u3002\n\u6210\u54c1\u6700\u4f4e\u4f7f\u7528\u4fee\u4e3a\uff1a{REALMS[item_required_realm_index(item)]}\uff1b\u7075\u77f3\u5269\u4f59\uff1a{spirit_stone_text(record.spirit_stones)}\u3002"


def set_life_artifact(record: UserRecord, artifact_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, ARTIFACT_CATEGORY, artifact_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7075\u5668\u3002"
    list_index, artifact = result
    artifact = normalize_reward(dict(artifact), record)
    required_index = item_required_realm_index(artifact)
    if required_index > record.realm_index:
        return False, f"{reward_display_name(artifact)}\u81f3\u5c11\u9700{REALMS[required_index]}\u624d\u80fd\u796d\u4e3a\u672c\u547d\u7075\u5668\u3002"
    if not artifact_is_compatible(record, artifact):
        required_attribute = reward_required_attribute(artifact)
        return False, f"{reward_display_name(artifact)} \u9700\u6c42{root_attribute_name(required_attribute)}\uff0c\u6682\u65f6\u65e0\u6cd5\u796d\u4e3a\u672c\u547d\u7075\u5668\u3002"
    ensure_reward_instance_uid(artifact)
    if record.rewards is not None and 0 <= list_index < len(record.rewards):
        record.rewards[list_index] = artifact
    record.life_artifact = dict(artifact)
    power_gain = int(artifact_power(artifact, record) * 0.38)
    required_attribute = reward_required_attribute(artifact)
    attribute_text = root_attribute_name(required_attribute) if required_attribute else "无属性限制"
    return True, f"\u5df2\u5c06 {reward_display_name(artifact)} \u796d\u4e3a\u672c\u547d\u7075\u5668\u3002\u5951\u5408\uff1a{attribute_text}\uff1b\u672c\u547d\u6218\u529b\u989d\u5916\u751f\u6548 {power_gain}\u3002"


def next_tier_grade(tier: str, grade: str) -> tuple[str, str]:
    result = next_growth_quality(tier, grade, TIER_ORDER)
    return result if result is not None else ("仙阶", "极品")


def array_deduction_text(record: UserRecord) -> str:
    arrays = available_arrays(record)
    lines = ["【阵法推演】", "重复获得阵盘会自动对同名阵盘推演：每次加一层，10层后升品或升阶；仙阶极品后可无限推演。"]
    if not arrays:
        lines.append("暂无阵盘。")
    for index, array in enumerate(arrays, start=1):
        layer = array_layer(record, array)
        proficiency = array_proficiency_value(record, array)
        cap = array_proficiency_cap(array, layer)
        cap_text = array_layer_cap_text(array)
        same = sum(1 for item in record.rewards or [] if reward_category(item) == ARRAY_CATEGORY and reward_name(item) == reward_name(array))
        lines.append(
            f"{index}. {reward_display_name(array)}｜第{layer}/{cap_text}层｜熟练度 {proficiency}/{cap}｜旧档同名数量 {same}"
        )
    lines.append("发送“阵法推演 编号”可查看该阵盘状态；后续重复获得同名阵盘会自动并入推演。")
    return "\n".join(lines)


def deduce_array(record: UserRecord, array_index: int) -> tuple[bool, str]:
    arrays = available_arrays(record)
    if array_index < 1 or array_index > len(arrays):
        return False, f"请选择 1-{len(arrays)} 之间的阵盘编号。"
    target = arrays[array_index - 1]
    target_name = reward_name(target)
    target_key = reward_signature(target)
    material_index = None
    for list_index, reward in enumerate(record.rewards or []):
        if reward_category(reward) != ARRAY_CATEGORY or reward_name(reward) != target_name:
            continue
        if reward_signature(reward) == target_key and material_index is None:
            continue
        material_index = list_index
        break
    if material_index is None:
        layer = array_layer(record, target)
        proficiency = array_proficiency_value(record, target)
        cap = array_proficiency_cap(target, layer)
        return True, f"{reward_display_name(target)} 当前第{layer}/{array_layer_cap_text(target)}层，熟练度 {proficiency}/{cap}；后续重复获得同名阵盘会自动推演。"
    material = normalize_reward(record.rewards.pop(material_index), record) if record.rewards is not None else None
    if material is None:
        return False, "阵盘材料读取失败，请稍后再试。"
    for list_index, reward in enumerate(record.rewards or []):
        if reward_category(reward) == ARRAY_CATEGORY and reward_name(reward) == target_name:
            before = reward_display_name(reward)
            record.rewards[list_index] = advance_array_by_duplicate(record, normalize_reward(reward, record), material)
            after = reward_display_name(record.rewards[list_index])
            return True, f"阵纹重组，消耗 {reward_display_name(material)} 推演 {before}，当前为 {after} 第{array_layer(record, record.rewards[list_index])}层。"
    append_reward(record, material)
    return False, "没有找到可推演的目标阵盘。"

def batch_sell_rewards(record: UserRecord, category: str, limit: int = 999) -> tuple[bool, str]:
    category = str(category).strip()
    if category not in REWARD_CATEGORIES and category != IMMORTAL_SEED_CATEGORY:
        return False, "\u7c7b\u522b\u53ef\u9009\uff1a" + "\u3001".join(REWARD_CATEGORIES + [IMMORTAL_SEED_CATEGORY])
    sold = []
    kept = []
    total = 0
    for reward in record.rewards or []:
        if reward_category(reward) == category and len(sold) < max(1, int(limit)):
            if is_unique_reward(reward):
                kept.append(reward)
                continue
            sold.append(normalize_reward(reward, record))
            total += recycle_price(reward)
        else:
            kept.append(reward)
    if not sold:
        return False, f"\u6ca1\u6709\u53ef\u6279\u91cf\u51fa\u552e\u7684{category}\u3002\u552f\u4e00\u9053\u5177\u4e0d\u4f1a\u88ab\u6279\u91cf\u51fa\u552e\u3002"
    record.rewards = kept
    record.spirit_stones += total
    return True, f"\u6279\u91cf\u51fa\u552e{category} {len(sold)} \u4ef6\uff0c\u83b7\u5f97 {spirit_stone_text(total)}\uff0c\u5f53\u524d\u5171 {spirit_stone_text(record.spirit_stones)}\u3002"


def batch_sell_low_realm_artifacts(record: UserRecord, limit: int = 999) -> tuple[bool, str]:
    sold = []
    kept = []
    total = 0
    try:
        max_count = max(1, int(limit))
    except (TypeError, ValueError):
        max_count = 999
    current_realm = max(0, int(record.realm_index))
    equipped_items = list(artifact_slots(record).values())
    equipped_uids = {reward_instance_uid(item) for item in equipped_items if reward_instance_uid(item)}
    equipped_signatures: dict[str, int] = {}
    for item in equipped_items:
        if reward_instance_uid(item):
            continue
        signature = reward_signature(item)
        if signature:
            equipped_signatures[signature] = equipped_signatures.get(signature, 0) + 1
    for reward in record.rewards or []:
        if reward_category(reward) == ARTIFACT_CATEGORY and len(sold) < max_count:
            normalized = normalize_reward(dict(reward), record)
            uid = reward_instance_uid(normalized)
            signature = reward_signature(normalized)
            if uid and uid in equipped_uids:
                kept.append(reward)
                continue
            if signature and equipped_signatures.get(signature, 0) > 0:
                equipped_signatures[signature] -= 1
                kept.append(reward)
                continue
            if is_unique_reward(normalized):
                kept.append(reward)
                continue
            if item_required_realm_index(normalized) < current_realm:
                sold.append(normalized)
                total += recycle_price(normalized)
                continue
        kept.append(reward)
    if not sold:
        return False, "没有可批量出售的低阶灵器。只会出售背包内低于自身境界、且非唯一的灵器；已装备灵器会保留。"
    record.rewards = kept
    record.spirit_stones += total
    return True, f"批量出售低阶灵器 {len(sold)} 件，获得 {spirit_stone_text(total)}，当前共有 {spirit_stone_text(record.spirit_stones)}。已装备灵器未受影响。"


def emperor_artifact_catalog_text(owner_lookup: Optional[dict[str, str]] = None) -> str:
    owner_lookup = owner_lookup or {}
    lines = ["\u3010\u552f\u4e00\u88c5\u5907\u56fe\u9274\u3011", "\u552f\u4e00\u88c5\u5907\u5177\u6709\u5168\u5c40\u552f\u4e00\u6027\uff1b\u4ed9\u5e1d\u5175\u672c\u4f53\u5df2\u6709\u4e3b\u65f6\uff0c\u540e\u7eed\u53ea\u80fd\u83b7\u5f97\u4eff\u5236\u54c1\u3002"]
    for index, (name, info) in enumerate(EMPEROR_ARTIFACT_INFOS.items(), start=1):
        owner = owner_lookup.get(name) or "\u6682\u65e0\u62e5\u6709\u8005"
        lines.append(f"{index}. {name}\uff5c\u70bc\u5236\u8005\uff1a{info.get('creator')}\uff5c\u6750\u6599\uff1a{info.get('material')}\uff5c\u62e5\u6709\u8005\uff1a{owner}")
        lines.append(f"   \u4e8b\u8ff9\uff1a{info.get('story')}\uff5c\u4e13\u5c5e\u6280\uff1a{info.get('skill')}")
    return "\n".join(lines)


def divine_ability_catalog_text(record: Optional[UserRecord] = None) -> str:
    text = special_ability_catalog_text(record)
    return text.replace("\u795e\u901a", "\u795e\u901a")


def improve_root_once(root: Root) -> Root:
    if root.tier == "\u53d8\u5f02\u7075\u6839":
        root.purity = min(100, int(root.purity) + random.randint(1, 3))
        if root.source_purities:
            root.source_purities = {key: min(100, int(value) + random.randint(1, 2)) for key, value in root.source_purities.items()}
        root.grade = root_grade_from_score(root.purity)
        root.grade_rank = GRADE_RANKS.get(root.grade, root.grade_rank)
        return root
    new_purity = min(100, int(root.purity) + random.randint(4, 9))
    return make_root(root.tier, root.grade, root.attribute, purity=new_purity, sources=[root.attribute], mutated=False)


def maybe_apply_encounter(record: UserRecord, today: date) -> EncounterResult:
    today_text = today.isoformat()
    if record.root is None or record.last_encounter_date == today_text:
        return EncounterResult()

    normalize_root_profile(record)
    record.last_encounter_date = today_text
    if record.root and record.root.tier == "\u53d8\u5f02\u7075\u6839":
        if random.randint(1, 999) > 1 + max(0, record.sign_count // 30):
            return EncounterResult()
        old_root = Root.from_dict(record.root.to_dict())
        new_root = improve_root_once(record.root)
        record.root = new_root
        record.extra_roots = []
        return EncounterResult(
            happened=True,
            success=True,
            message=f"\u4eca\u65e5\u5148\u5929\u5f02\u8c61\u56de\u54cd\uff0c{new_root.display_name}\u7cbe\u7eaf\u5ea6\u63d0\u5347\u81f3{new_root.purity}%\u3002",
            old_root=old_root,
            new_root=new_root,
        )

    if not record.is_peak_aptitude:
        if random.randint(1, 365) != 1:
            return EncounterResult()
        old_root = Root.from_dict(record.root.to_dict()) if record.root else None
        if random.random() >= 0.5:
            return EncounterResult(
                happened=True,
                success=False,
                message="\u4eca\u65e5\u5ffd\u9022\u5c71\u4e2d\u53e4\u6d1e\uff0c\u53ef\u60dc\u673a\u7f18\u4e00\u95ea\u800c\u901d\uff0c\u8d44\u8d28\u672a\u6709\u53d8\u5316\u3002",
                old_root=old_root,
            )
        if record.root:
            record.root = improve_root_once(record.root)
            normalize_root_profile(record)
        return EncounterResult(
            happened=True,
            success=True,
            message=f"\u4eca\u65e5\u5947\u9047\u5165\u68a6\uff0c\u7075\u6839\u7cbe\u7eaf\u5ea6\u63d0\u5347\uff0c\u8d44\u8d28\u8bc4\u5b9a\u4e3a{record.root.tier}{record.root.grade}\uff01",
            old_root=old_root,
            new_root=record.root,
        )

    return EncounterResult()



def apply_signin(record: UserRecord, today: date) -> SigninResult:
    today_text = today.isoformat()
    if record.last_sign_date == today_text:
        return SigninResult(record=record, is_first=False, already_signed=True)

    is_first = record.root is None
    if record.root is None:
        roots = draw_roots()
        record.root = roots[0]
        record.extra_roots = [] if roots[0].tier == "\u53d8\u5f02\u7075\u6839" else roots[1:]
        normalize_root_profile(record)
    else:
        ensure_legacy_extra_roots(record)

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
    conversion_happened, conversion_message = progress_fake_immortal_conversion(record, today)
    if conversion_happened and is_fake_immortal_conversion(record):
        exp_result = ExpApplyResult()
    else:
        exp_result = apply_exp(record, base_exp + method_bonus + plant_bonus + pending_exp, today)
    applied_exp, leveled_realms = exp_result
    if applied_exp:
        increase_array_proficiency(record, 1)
        increase_method_proficiency(record, 2)
    encounter = maybe_apply_encounter(record, today)
    breakthrough_reward = maybe_grant_breakthrough_item(record)
    record_identity_sign_day(record, today)
    tasks = ensure_daily_tasks(record, today)

    gained_fishing_chance = True
    fishing_gain = 1
    if random.random() < SIGNIN_EXTRA_FISHING_CHANCE_RATE:
        fishing_gain += 1
    record.fishing_chances += fishing_gain
    record.pending_fishing = record.fishing_chances

    return SigninResult(
        record=record,
        is_first=is_first,
        already_signed=False,
        gained_exp=applied_exp,
        pending_exp_applied=min(pending_exp, applied_exp) if pending_exp else 0,
        method_bonus_exp=min(method_bonus, applied_exp) if method_bonus else 0,
        item_bonus_exp=min(plant_bonus, applied_exp) if plant_bonus else 0,
        overflow_exp=exp_result.overflow,
        spirit_liquid_gain=exp_result.spirit_liquid,
        bottleneck_days=record.bottleneck_days,
        leveled_realms=leveled_realms,
        gained_fishing_chance=gained_fishing_chance,
        fishing_chances_gained=fishing_gain,
        encounter=encounter,
        breakthrough_reward=breakthrough_reward,
        lock_message=conversion_message or (cultivation_lock_text(record, today) if locked else ""),
        daily_tasks=tasks,
    )

def draw_fishing_rewards(count: int, record: Optional[UserRecord] = None) -> list[dict[str, Any]]:
    rewards = []
    pool = [(reward, float(reward[5])) for reward in FISHING_REWARDS]
    realm_index = int(record.realm_index) if record is not None else 0
    for _ in range(count):
        tier, grade, category, name, description, _ = weighted_choice(pool)
        if category == ARTIFACT_CATEGORY:
            raw = draw_configured_artifact_reward(tier, grade)
        else:
            raw = {
                "tier": tier,
                "grade": grade,
                "category": category,
                "name": name,
                "description": description,
            }
        rewards.append(normalize_reward(raw, record))
    return rewards

def apply_fishing(record: UserRecord, requested_count: int) -> list[dict[str, Any]]:
    count = max(1, min(requested_count, record.fishing_chances, 10))
    rewards = draw_fishing_rewards(count, record)
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
        bonus_reward = maybe_grant_breakthrough_item(record, source="fishing")
        if bonus_reward:
            bonus_reward["source"] = "\u74f6\u9888\u673a\u7f18"
            shown_rewards.append(bonus_reward)
        special_reward = maybe_grant_special_ability_material(record, chance=0.16, source="垂钓灵光")
        if special_reward:
            shown_rewards.append(special_reward)
    return shown_rewards


def fishing_count_from_text(text: str, chances: int) -> int:
    normalized = text.strip().lower()
    if "\u5341" in normalized or "10" in normalized:
        return min(10, chances)
    return 1


def reward_display_name(reward: Optional[dict[str, Any]]) -> str:
    if not reward:
        return "[无]"
    tier = str(reward.get("tier", "未知"))
    grade = str(reward.get("grade", ""))
    category = reward_category(reward)
    name = reward_name(reward) or "无名灵物"
    if category == ARTIFACT_CATEGORY and tier == "仙阶":
        prefix = f"{grade}仙器"
    elif category == ARTIFACT_CATEGORY and tier != "仙帝兵":
        realm_label = artifact_realm_label(reward)
        prefix = f"{realm_label}{tier}{grade}{category}" if realm_label else f"{tier}{grade}{category}"
    else:
        prefix = f"{tier}{grade}{category}"
    return f"[{prefix} {name}]"

def available_artifacts(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, ARTIFACT_CATEGORY)


def available_methods(record: UserRecord) -> list[dict[str, Any]]:
    ensure_unique_growth_rewards(record, METHOD_CATEGORY)
    return rewards_by_category(record, METHOD_CATEGORY)


def available_arrays(record: UserRecord) -> list[dict[str, Any]]:
    ensure_unique_growth_rewards(record, ARRAY_CATEGORY)
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


def available_special_ability_items(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, SPECIAL_ABILITY_CATEGORY)


def normalize_special_abilities(abilities: Sequence[str] | None) -> list[str]:
    result = list(dict.fromkeys(canonical_item_name(str(item)) for item in (abilities or []) if item))
    owned = set(result)
    if "归极域" in owned:
        result = [item for item in result if item not in {"初阈", "重阈"}]
    elif "重阈" in owned:
        result = [item for item in result if item != "初阈"]
    return result


def forbidden_rank(ability: Optional[str]) -> int:
    if ability == "初阈":
        return 1
    if ability == "重阈":
        return 2
    if ability == "归极域":
        return 3
    return 0


def highest_forbidden_ability(abilities: Sequence[str] | None) -> Optional[str]:
    owned = set(abilities or [])
    for ability in reversed(FORBIDDEN_REALM_ABILITIES):
        if ability in owned:
            return ability
    return None


def nine_secret_count(record: UserRecord) -> int:
    return len([ability for ability in normalize_special_abilities(record.special_abilities) if ability.startswith("星律")])


def nine_secret_set_multiplier(record: UserRecord) -> int:
    return max(1, nine_secret_count(record))


def special_ability_rarity(ability: str) -> tuple[str, str]:
    return SPECIAL_ABILITY_RARITIES.get(str(ability), ("\u7384\u9636", "\u4e0a\u54c1"))


def special_ability_rarity_text(ability: str) -> str:
    tier, grade = special_ability_rarity(ability)
    return f"{tier}{grade}"


def special_ability_power_value(ability: str) -> int:
    tier, grade = special_ability_rarity(ability)
    tier_rank = TIER_ORDER.index(tier) if tier in TIER_ORDER else 2
    grade_rank = GRADE_ORDER.index(grade) if grade in GRADE_ORDER else 2
    return 120 + tier_rank * 170 + grade_rank * 55


def special_ability_power_total(record: UserRecord) -> int:
    abilities = normalize_special_abilities(record.special_abilities)
    secret_count = len([ability for ability in abilities if ability.startswith("星律")])
    total = sum(special_ability_power_value(ability) for ability in abilities)
    if secret_count:
        total += secret_count * max(0, secret_count - 1) * 90
    return total


def special_ability_info(ability: str) -> dict[str, Any]:
    info = dict(SPECIAL_ABILITY_INFOS.get(ability, {
        "material": ability,
        "source": "\u5931\u843d\u4f20\u627f",
        "effect": "\u4e00\u6bb5\u5c1a\u672a\u5b8c\u5168\u660e\u609f\u7684\u795e\u901a\u3002",
        "aliases": [ability],
        "combat": (0.08, 0.04, 0),
    }))
    info["rarity"] = special_ability_rarity_text(ability)
    return info


def special_ability_material_requirement_text(record: UserRecord, material_name: str) -> str:
    material_name = str(material_name or "").strip()
    abilities = set(normalize_special_abilities(record.special_abilities))
    highest = highest_forbidden_ability(abilities)
    if material_name in {"初阈战札", "初阈战意札"} and highest:
        return f"\u5df2\u638c\u63e1\u3010{highest}\u3011\uff0c\u7981\u57df\u8def\u7ebf\u53ea\u4fdd\u7559\u6700\u9ad8\u7ea7\u80fd\u529b\u3002"
    if material_name == "重阈战札":
        if "归极域" in abilities or "重阈" in abilities:
            return "你已掌握重阈或更高限界。"
        if "初阈" not in abilities:
            return "需先领悟初阈，才能借重阈战札进阶。"
    if material_name == "归极印纹":
        if "归极域" in abilities:
            return "你已掌握归极域。"
        if "重阈" not in abilities:
            return "需先将初阈推至重阈，才能承载归极印纹。"
    return "\u5df2\u65e0\u53ef\u9886\u609f\u76ee\u6807"


def special_ability_material_target(record: UserRecord, material_name: str, seed: str = "") -> Optional[str]:
    material_name = str(material_name or "").strip()
    owned = set(normalize_special_abilities(record.special_abilities))
    highest = highest_forbidden_ability(owned)
    if material_name == "星律残页":
        candidates = [ability for ability in NINE_SECRET_ABILITIES if ability not in owned]
        if not candidates:
            return None
        return stable_choice(candidates, seed or f"nine-secret:{record.user_id}:{len(owned)}")
    if material_name in {"初阈战札", "初阈战意札"}:
        return None if highest else "初阈"
    if material_name == "重阈战札":
        if "初阈" in owned and "重阈" not in owned and "归极域" not in owned:
            return "重阈"
        return None
    if material_name == "归极印纹":
        if "重阈" in owned and "归极域" not in owned:
            return "归极域"
        return None
    if material_name in SPECIAL_ABILITY_POOL:
        return None if material_name in owned else material_name
    target = SPECIAL_ABILITY_MATERIAL_TO_ABILITY.get(material_name)
    if target:
        return None if target in owned else target
    for ability, info in SPECIAL_ABILITY_INFOS.items():
        if material_name == str(info.get("material", "")):
            return None if ability in owned else ability
    return None


def draw_special_ability_material(record: Optional[UserRecord] = None) -> dict[str, Any]:
    pool = [reward for reward in FISHING_REWARDS if reward[2] == SPECIAL_ABILITY_CATEGORY]
    if record is not None:
        preferred = [
            reward
            for reward in pool
            if special_ability_material_target(record, reward[3], f"draw:{record.user_id}:{reward[3]}") is not None
        ]
        if preferred:
            pool = preferred
    if not pool:
        return make_reward("\u7384\u9636", "\u4e0a\u54c1", SPECIAL_ABILITY_CATEGORY, "星律残页")
    weighted_pool = [
        (reward, float(reward[5]) * SPECIAL_ABILITY_MATERIAL_DIFFICULTY.get(str(reward[3]), 1.0))
        for reward in pool
    ]
    tier, grade, category, name, description, _ = weighted_choice(weighted_pool)
    return normalize_reward({"tier": tier, "grade": grade, "category": category, "name": name, "description": description})


def maybe_grant_special_ability_material(
    record: UserRecord,
    chance: float = 0.18,
    source: str = "",
) -> Optional[dict[str, Any]]:
    effective_chance = max(0.0, min(1.0, chance * 0.55))
    if not SPECIAL_ABILITY_POOL or random.random() >= effective_chance:
        return None
    reward = draw_special_ability_material(record)
    reward["special_ability_bonus"] = True
    if source:
        reward["source"] = source
    append_reward(record, reward)
    return reward


def learn_special_ability(record: UserRecord, item_index: int) -> tuple[bool, str]:
    record.special_abilities = normalize_special_abilities(record.special_abilities)
    result = reward_position_by_category_index(record, SPECIAL_ABILITY_CATEGORY, item_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u795e\u901a\u4f20\u627f\u6750\u6599\u3002"
    list_index, item = result
    material = reward_name(item)
    seed = f"learn-special:{record.user_id}:{reward_signature(item)}:{item_index}:{len(record.special_abilities or [])}"
    target = special_ability_material_target(record, material, seed)
    if not target:
        return False, f"{reward_display_name(item)} \u6682\u65f6\u65e0\u6cd5\u9886\u609f\uff1a{special_ability_material_requirement_text(record, material)}"
    abilities = normalize_special_abilities(record.special_abilities)
    if target in abilities:
        return False, f"\u4f60\u5df2\u638c\u63e1\u3010{target}\u3011\uff0c\u8fd9\u4efd{material}\u53ef\u6682\u65f6\u7559\u5b58\u6216\u51fa\u552e\u7ed9\u5176\u4ed6\u4fee\u58eb\u3002"
    if record.rewards is None or list_index >= len(record.rewards):
        return False, "\u4f20\u627f\u6750\u6599\u4f4d\u7f6e\u53d1\u751f\u53d8\u5316\uff0c\u8bf7\u91cd\u65b0\u6253\u5f00\u80cc\u5305\u786e\u8ba4\u7f16\u53f7\u3002"
    record.rewards.pop(list_index)
    if target == "重阈":
        abilities = [ability for ability in abilities if ability != "初阈"]
    elif target == "归极域":
        abilities = [ability for ability in abilities if ability not in {"初阈", "重阈"}]
    abilities.append(target)
    record.special_abilities = normalize_special_abilities(abilities)
    info = special_ability_info(target)
    extra = ""
    if target.startswith("星律"):
        count = nine_secret_count(record)
        extra = f"\n星律联动\uff1a\u5df2\u83b7{count}/9\u4ef6\uff0c\u5df2\u83b7星律\u6548\u679c\u5728\u6597\u6cd5\u4e2d\u63d0\u5347{max(1, count)}\u500d\u3002"
    elif target in FORBIDDEN_REALM_ABILITIES:
        extra = "\n\u7981\u57df\u8def\u7ebf\uff1a初阈 -> 重阈 -> 归极\uff0c\u5347\u7ea7\u540e\u53ea\u4fdd\u7559\u6700\u9ad8\u7ea7\u80fd\u529b\u3002"
    return (
        True,
        "\n".join(
            [
                f"\u53ee\uff01\u53c2\u609f {reward_display_name(item)} \u6210\u529f\u3002",
                f"\u9886\u609f{special_ability_rarity_text(target)}\u795e\u901a\u3010{target}\u3011\u3002",
                f"\u6765\u6e90\uff1a{info.get('source', '\u5931\u843d\u4f20\u627f')}",
                f"\u6548\u679c\uff1a{info.get('effect', '\u4e00\u6bb5\u5c1a\u672a\u5b8c\u5168\u660e\u609f\u7684\u795e\u901a\u3002')}{extra}",
                "\u6597\u6cd5\u4e2d\u76f4\u63a5\u53d1\u9001\u80fd\u529b\u540d\u6216\u522b\u540d\u5373\u53ef\u5c1d\u8bd5\u89e6\u53d1\u3002",
            ]
        ),
    )


def special_ability_list_text(record: UserRecord) -> str:
    record.special_abilities = normalize_special_abilities(record.special_abilities)
    abilities = list(record.special_abilities or [])
    materials = available_special_ability_items(record)
    secret_count = nine_secret_count(record)
    lines = ["\u3010\u6211\u7684\u795e\u901a\u3011"]
    if secret_count:
        lines.append(f"星律联动\uff1a{secret_count}/9\uff0c\u5df2\u83b7星律\u6548\u679c\u6597\u6cd5\u65f6 {secret_count}x \u589e\u5f3a\u3002")
    highest = highest_forbidden_ability(abilities)
    if highest:
        lines.append(f"\u7981\u57df\u8def\u7ebf\uff1a\u5f53\u524d\u4fdd\u7559\u6700\u9ad8\u7ea7\u3010{highest}\u3011\u3002")
    if abilities:
        lines.append(f"\u5df2\u9886\u609f\uff08{len(abilities)}\uff09\uff1a")
        for index, ability in enumerate(abilities, start=1):
            info = special_ability_info(ability)
            damage, defense, speed = info.get("combat", (0.08, 0.04, 0))
            multiplier = nine_secret_set_multiplier(record) if ability.startswith("星律") else 1
            lines.append(
                f"{index}. {special_ability_rarity_text(ability)}\u3010{ability}\u3011\uff5c\u4f24\u5bb3+{int(float(damage) * 100)}%\uff5c\u9632\u5fa1+{int(float(defense) * 100)}%\uff5c\u901f\u5ea6+{int(speed)}\uff5c{multiplier}x\uff5c{info.get('effect', '')}"
            )
    else:
        lines.append("\u6682\u672a\u9886\u609f\u795e\u901a\u3002")
    lines.append("")
    lines.append("\u3010\u53ef\u9886\u609f\u4f20\u627f\u6750\u6599\u3011")
    if not materials:
        lines.append("\u6682\u65e0\u3002\u5782\u9493\u3001\u79d8\u5883\u548c\u7a81\u7834\u4f59\u97f5\u90fd\u6709\u673a\u4f1a\u83b7\u5f97星律残页\u3001初阈战札\u3001重阈战札\u3001归极印纹\u7b49\u4f20\u627f\u6750\u6599\u3002")
    else:
        for index, item in enumerate(materials, start=1):
            material = reward_name(item)
            target = special_ability_material_target(record, material, f"preview:{record.user_id}:{index}:{reward_signature(item)}")
            target_text = target or special_ability_material_requirement_text(record, material)
            lines.append(f"{index}. {reward_display_name(item)} -> {target_text}")
    lines.append("\u53d1\u9001\u201c\u9886\u609f\u795e\u901a \u7f16\u53f7\u201d\u53c2\u609f\u4f20\u627f\uff1b\u53d1\u9001\u201c\u795e\u901a\u56fe\u9274\u201d\u67e5\u770b\u5b8c\u6574\u8ffd\u6c42\u8def\u5f84\u3002")
    return "\n".join(lines)


def special_ability_catalog_text(record: Optional[UserRecord] = None) -> str:
    owned = set(normalize_special_abilities(record.special_abilities if record is not None else []))
    secret_count = len([ability for ability in owned if ability.startswith("星律")])
    lines = [
        "\u3010\u795e\u901a\u56fe\u9274\u3011",
        "\u83b7\u53d6\u8def\u5f84\uff1a\u5782\u9493\u3001\u79d8\u5883\u63a2\u7d22\u3001\u5883\u754c\u7a81\u7834\u4f59\u97f5\u4f1a\u4f4e\u6982\u7387\u6389\u843d\u4f20\u627f\u6750\u6599\uff0c\u73b0\u5df2\u63d0\u9ad8\u83b7\u53d6\u96be\u5ea6\u3002",
        "\u56fa\u5b9a\u54c1\u9636\uff1a\u6240\u6709\u795e\u901a\u5747\u5df2\u56fa\u5b9a\u54c1\u9636\u4e0e\u54c1\u8d28\uff0c\u8be6\u89c1\u6bcf\u9879\u6807\u9898\uff1b星律\u7edf\u4e00\u4e3a\u5929\u9636\u6781\u54c1\u3002",
        "\u8fdb\u9636\u8def\u7ebf\uff1a初阈 -> 重阈 -> 归极\uff0c\u5347\u7ea7\u540e\u53ea\u4fdd\u7559\u6700\u9ad8\u7ea7\u80fd\u529b\u3002",
        f"星律\u8054\u52a8\uff1a\u83b7\u53d6 n \u4ef6\u540e\uff0c\u5df2\u83b7星律\u7684\u6597\u6cd5\u6548\u679c\u6309 n \u500d\u8ba1\u7b97\u3002\u5f53\u524d\uff1a{secret_count}/9\u3002",
        "",
    ]
    for index, ability in enumerate(SPECIAL_ABILITY_POOL, start=1):
        info = special_ability_info(ability)
        damage, defense, speed = info.get("combat", (0.08, 0.04, 0))
        mark = "\u5df2\u609f" if ability in owned else "\u672a\u609f"
        aliases = "\u3001".join(str(item) for item in info.get("aliases", [])[:3])
        lines.append(
            f"{index}. \u3010{mark}\u3011{special_ability_rarity_text(ability)}\u3010{ability}\u3011\uff5c\u6750\u6599\uff1a{info.get('material', ability)}\uff5c\u6765\u6e90\uff1a{info.get('source', '\u5931\u843d\u4f20\u627f')}"
        )
        lines.append(
            f"   \u6548\u679c\uff1a{info.get('effect', '')}\uff5c\u6597\u6cd5\uff1a\u4f24\u5bb3+{int(float(damage) * 100)}% \u9632\u5fa1+{int(float(defense) * 100)}% \u901f\u5ea6+{int(speed)}\uff5c\u522b\u540d\uff1a{aliases or ability}"
        )
    return "\n".join(lines)


def normalize_artifact_slot(slot: Optional[str] = None, artifact: Optional[dict[str, Any]] = None) -> str:
    text = str(slot or "").strip()
    if text in ARTIFACT_SLOT_ALIASES:
        return ARTIFACT_SLOT_ALIASES[text]
    if text:
        return text
    if artifact_is_armor(artifact):
        return "护甲"
    return "主手"


def artifact_is_armor(artifact: Optional[dict[str, Any]]) -> bool:
    name = reward_name(artifact)
    return name.endswith("甲") or any(token in name for token in ARTIFACT_ARMOR_NAME_TOKENS)


def artifact_slot_allowed(slot: str, artifact: Optional[dict[str, Any]]) -> bool:
    normalized = normalize_artifact_slot(slot)
    if artifact_is_armor(artifact):
        return normalized == "护甲"
    return normalized in {"主手", "副手"}


def artifact_power_rate(artifact: dict[str, Any]) -> float:
    name = reward_name(artifact)
    explicit_rate = ARTIFACT_NAME_POWER_RATE.get(name)
    if explicit_rate is not None:
        return explicit_rate
    if str(artifact.get("tier")) != "天阶":
        return 1.0
    if any(token in name for token in ARTIFACT_SWORD_NAME_TOKENS):
        return 1.0
    for tokens, rate in ARTIFACT_TIAN_TYPE_POWER_RATES:
        if any(token in name for token in tokens):
            return rate
    return 1.1


def artifact_slots(record: UserRecord) -> dict[str, dict[str, Any]]:
    slots: dict[str, dict[str, Any]] = {}
    raw = record.equipped_artifacts or {}
    for slot, item in raw.items():
        if isinstance(item, dict):
            normalized = normalize_artifact_slot(slot, item)
            slots[normalized] = dict(item)
    if record.equipped_artifact and "主手" not in slots:
        slots["主手"] = dict(record.equipped_artifact)
    record.equipped_artifacts = slots
    record.equipped_artifact = slots.get("主手")
    return slots


def equipped_artifact_in_slot(record: UserRecord, slot: str) -> Optional[dict[str, Any]]:
    return artifact_slots(record).get(normalize_artifact_slot(slot))


def equipped_artifact_lines(record: UserRecord) -> list[str]:
    slots = artifact_slots(record)
    lines = []
    seen_names: set[str] = set()
    for slot in ARTIFACT_SLOTS:
        item = slots.get(slot)
        if item:
            display = reward_display_name(item)
            name = reward_name(item)
            if not artifact_slot_allowed(slot, item) or artifact_power(item, record) <= 0:
                display += "（未生效）"
            elif name in seen_names:
                display += "（同名削弱）"
            else:
                seen_names.add(name)
        else:
            display = "\u672a\u88c5\u5907"
        lines.append(f"{slot}：{display}")
    return lines

def equipped_artifact_summary(record: UserRecord) -> str:
    return "；".join(equipped_artifact_lines(record))


def artifact_is_compatible(record: UserRecord, artifact: dict[str, Any]) -> bool:
    return item_is_compatible(record, artifact)

def artifact_power(artifact: Optional[dict[str, Any]], record: Optional[UserRecord] = None) -> int:
    if not artifact:
        return 0
    required_index = item_required_realm_index(artifact)
    if record is not None and record.realm_index < required_index:
        return 0
    tier = str(artifact.get("tier", "凡品"))
    grade = str(artifact.get("grade", "下品"))
    if tier == "仙帝兵" or is_unique_reward(artifact):
        base = ARTIFACT_POWER_BASE.get(tier, ARTIFACT_POWER_BASE.get("仙阶", 7600))
        power = int(base * ARTIFACT_GRADE_RATIO.get(grade, 1.0))
        if required_index:
            power = int(power * (1.0 + required_index * 0.045))
        power = int(power * artifact_power_rate(artifact))
        if record is not None and is_unique_reward(artifact):
            power = int(power * (1.0 + min(1.8, record.realm_index * 0.075)))
            power += special_ability_power_total(record) // 4
    else:
        realm_base = ARTIFACT_REALM_POWER_BASE.get(required_index)
        if realm_base is None:
            realm_base = ARTIFACT_REALM_POWER_BASE[max(ARTIFACT_REALM_POWER_BASE)]
        power = int(
            realm_base
            * ARTIFACT_TIER_POWER_RATIO.get(tier, 0.36)
            * ARTIFACT_GRADE_RATIO.get(grade, 1.0)
        )
        power = int(power * artifact_power_rate(artifact))
    if record is not None and artifact_is_compatible(record, artifact):
        power = int(power * 1.15 * root_purity_multiplier(record, reward_required_attribute(artifact)))
    if record is not None and record.life_artifact and reward_signature(record.life_artifact) == reward_signature(artifact):
        power = int(power * 1.22)
    return power

def method_power(method: Optional[dict[str, Any]], record: Optional[UserRecord] = None) -> int:
    if not method:
        return 0
    base = int(ARTIFACT_POWER_BASE.get(str(method.get("tier")), 120) * 0.72)
    ratio = ARTIFACT_GRADE_RATIO.get(str(method.get("grade")), 1.0)
    power = int(base * ratio)
    if record is not None and item_is_compatible(record, method):
        layer = method_layer(record, method)
        layer_rate = 1.0 + max(0, layer - 1) * 0.08
        power = int(power * 1.12 * layer_rate * root_purity_multiplier(record, reward_required_attribute(method)))
    return power


def array_power(array: Optional[dict[str, Any]], record: Optional[UserRecord] = None) -> int:
    if not array:
        return 0
    base = int(ARTIFACT_POWER_BASE.get(str(array.get("tier")), 120) * 0.55)
    ratio = ARTIFACT_GRADE_RATIO.get(str(array.get("grade")), 1.0)
    multiplier = array_multiplier(record) if record is not None else 1.0
    return int(base * ratio * min(2.6, multiplier))


def equipped_artifact_name(record: UserRecord) -> str:
    slots = artifact_slots(record)
    if not slots:
        return "\u672a\u88c5\u5907\u7075\u5668"
    return "；".join(
        f"{slot}{reward_display_name(item)}"
        for slot, item in slots.items()
        if item
    )


def equipped_talisman_name(record: UserRecord) -> str:
    if not record.equipped_talisman:
        return "未装备符箓"
    return reward_display_name(record.equipped_talisman)


def talisman_power(talisman: Optional[dict[str, Any]], record: Optional[UserRecord] = None) -> int:
    if not talisman:
        return 0
    required_index = talisman_required_realm_index(str(talisman.get("tier")))
    if record is not None and record.realm_index < required_index:
        return 0
    base = tier_exp(CONSUMABLE_EXP_BASE, str(talisman.get("tier")), str(talisman.get("grade")))
    return max(20, int(base * 1.8))


def equipped_artifact_power(record: UserRecord) -> int:
    total = 0
    seen_names: set[str] = set()
    for slot, artifact in artifact_slots(record).items():
        if not artifact_slot_allowed(slot, artifact):
            continue
        power = artifact_power(artifact, record)
        if power <= 0:
            continue
        name = reward_name(artifact)
        if name in seen_names:
            power = int(power * ARTIFACT_DUPLICATE_POWER_RATE)
        else:
            seen_names.add(name)
        total += int(power * ARTIFACT_SLOT_POWER_RATE.get(slot, 1.0))
    return total


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


def equip_artifact(record: UserRecord, artifact_index: int, slot: Optional[str] = None) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, ARTIFACT_CATEGORY, artifact_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7075\u5668\u3002"
    _, artifact = result
    required_index = item_required_realm_index(artifact)
    if record.realm_index < required_index:
        return False, f"{reward_display_name(artifact)} \u9700\u81f3\u5c11\u8fbe\u5230{REALMS[required_index]}\u624d\u80fd\u9a7e\u9a6d\u3002"
    if not artifact_is_compatible(record, artifact):
        required_attribute = reward_required_attribute(artifact)
        return False, f"{reward_display_name(artifact)} \u9700\u6c42{root_attribute_name(required_attribute)}\uff0c\u6682\u65f6\u65e0\u6cd5\u88c5\u5907\u3002"
    target_slot = normalize_artifact_slot(slot, artifact)
    if target_slot not in ARTIFACT_SLOTS:
        return False, "槽位只能填写主手、副手或护甲。"
    if not artifact_slot_allowed(target_slot, artifact):
        if target_slot == "护甲":
            return False, f"{reward_display_name(artifact)} 不是护甲/护盾类灵器，不能装备到护甲槽。"
        return False, f"{reward_display_name(artifact)} 属于护甲/护盾类灵器，只能装备到护甲槽。"
    slots = artifact_slots(record)
    artifact_name = reward_name(artifact)
    for existing_slot, equipped in slots.items():
        if existing_slot != target_slot and reward_name(equipped) == artifact_name:
            return False, f"同名灵器不可同时装备：{reward_display_name(artifact)} 已在{existing_slot}，请先卸下或改用其他灵器搭配。"
    slots[target_slot] = dict(artifact)
    record.equipped_artifacts = slots
    record.equipped_artifact = slots.get("主手")
    power_gain = int(artifact_power(artifact, record) * ARTIFACT_SLOT_POWER_RATE.get(target_slot, 1.0))
    return True, f"\u5df2\u88c5\u5907{target_slot} {reward_display_name(artifact)}\uff0c\u8be5\u69fd\u4f4d\u6218\u529b\u63d0\u5347 {power_gain}\u3002"


def equip_method(record: UserRecord, method_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, METHOD_CATEGORY, method_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u529f\u6cd5\u3002"
    _, method = result
    if not item_is_compatible(record, method):
        required_attribute = reward_required_attribute(method)
        return False, f"{reward_display_name(method)} \u9700\u6c42{root_attribute_name(required_attribute)}\uff0c\u6682\u65f6\u65e0\u6cd5\u4fee\u884c\u3002"
    record.equipped_method = dict(method)
    ensure_method_tracking(record, method)
    profile = method_profile(method, record)
    return True, f"\u5df2\u53c2\u609f {reward_display_name(method)}\uff0c\u5f53\u524d\u4e3a{profile['kind']}\uff0c\u7b2c{profile['layer']}\u5c42\uff0c\u7b7e\u5230\u4e0e\u804a\u5929\u4fee\u4e3a\u5c06\u83b7\u5f97\u52a0\u6210\u3002"


def equip_array(record: UserRecord, array_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, ARRAY_CATEGORY, array_index)
    if result is None:
        return False, "没有找到这个编号的阵盘。"
    _, array = result
    record.equipped_array = dict(array)
    ensure_array_tracking(record, record.equipped_array)
    layer = array_layer(record, record.equipped_array)
    proficiency = array_proficiency_value(record, record.equipped_array)
    cap = array_proficiency_cap(record.equipped_array, layer)
    multiplier = array_multiplier(record)
    return True, f"已布置 {reward_display_name(array)}，第{layer}层，熟练度 {proficiency}/{cap}，当前阵法效果 {multiplier:.1f}x。"

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


def unequip_artifact(record: UserRecord, slot: Optional[str] = None) -> str:
    slots = artifact_slots(record)
    if not slots:
        return "\u5f53\u524d\u6ca1\u6709\u88c5\u5907\u7075\u5668\u3002"
    if slot:
        target_slot = normalize_artifact_slot(slot)
        old = slots.pop(target_slot, None)
        record.equipped_artifacts = slots
        record.equipped_artifact = slots.get("主手")
        if not old:
            return f"{target_slot}\u6ca1\u6709\u88c5\u5907\u7075\u5668\u3002"
        return f"\u5df2\u5378\u4e0b{target_slot} {reward_display_name(old)}\u3002"
    old_names = "；".join(equipped_artifact_lines(record))
    record.equipped_artifacts = {}
    record.equipped_artifact = None
    return f"\u5df2\u5378\u4e0b\u5168\u90e8\u7075\u5668\uff1a{old_names}\u3002"


def blocked_cultivation_message(record: UserRecord) -> str:
    lock_text = cultivation_lock_text(record)
    return f"当前处于秘境反噬惩罚期，{lock_text}，暂时无法提升修为。" if lock_text else "当前无法提升修为。"


def exp_gain_text(prefix: str, applied: int, leveled: int, result: ExpApplyResult) -> str:
    extra = f"\uff0c\u8fde\u7834 {leveled} \u5883" if leveled else ""
    if applied > 0:
        text = f"{prefix}\uff0c\u4fee\u4e3a +{applied}{extra}"
        if result.spirit_liquid:
            text += f"\uff0c\u6ea2\u51fa\u4fee\u4e3a {result.overflow} \u51dd\u6210\u7cbe\u7eaf\u7075\u6db2 +{result.spirit_liquid}"
        return text + "\u3002"
    if result.spirit_liquid:
        return f"{prefix}\uff0c\u5f53\u524d\u5df2\u81f3\u74f6\u9888\u5dc5\u5cf0\uff0c\u6ea2\u51fa\u4fee\u4e3a {result.overflow} \u51dd\u6210\u7cbe\u7eaf\u7075\u6db2 +{result.spirit_liquid}\u3002"
    return f"{prefix}\uff0c\u5f53\u524d\u65e0\u6cd5\u589e\u957f\u4fee\u4e3a\u3002"

def refine_demon_core(record: UserRecord, material_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, "\u7075\u6750", material_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7075\u6750\u3002"
    list_index, material = result
    if not is_demon_core_item(material):
        return False, f"{reward_display_name(material)} \u4e0d\u662f\u5996\u4e39\uff0c\u65e0\u6cd5\u70bc\u5316\u4e3a\u4fee\u4e3a\u3002"
    if record.root is None:
        return False, "\u5c1a\u672a\u8e0f\u5165\u4fee\u884c\u8def\uff0c\u53d1\u9001\u201c\u7b7e\u5230\u201d\u5148\u89c9\u9192\u7075\u6839\u3002"
    if is_cultivation_locked(record):
        return False, blocked_cultivation_message(record)
    if record.rewards is None or list_index >= len(record.rewards):
        return False, "\u7075\u6750\u4f4d\u7f6e\u53d1\u751f\u53d8\u5316\uff0c\u8bf7\u91cd\u65b0\u6253\u5f00\u80cc\u5305\u786e\u8ba4\u7f16\u53f7\u3002"
    consumed = normalize_reward(record.rewards.pop(list_index), record)
    exp = demon_core_cultivation_exp(consumed)
    exp_result = apply_exp(record, exp)
    applied_exp, leveled = exp_result
    if applied_exp <= 0 and exp_result.spirit_liquid <= 0:
        append_reward(record, consumed)
        return False, "\u5f53\u524d\u5df2\u81f3\u74f6\u9888\u5dc5\u5cf0\uff0c\u5996\u4e39\u5996\u529b\u6682\u65f6\u65e0\u6cd5\u878d\u5165\u4e39\u7530\uff0c\u8bf7\u5148\u7a81\u7834\u3002"
    realm_name = demon_core_realm_name(consumed) or "\u672a\u77e5"
    attribute = demon_core_attribute(consumed)
    prefix = f"\u70bc\u5316 {reward_display_name(consumed)}\uff0c{attribute}\u884c{realm_name}\u5996\u529b\u5165\u4f53"
    return True, exp_gain_text(prefix, applied_exp, leveled, exp_result)

def refine_spirit_liquid(record: UserRecord, amount: Optional[int] = None, today: Optional[date] = None) -> tuple[bool, str]:
    if record.root is None:
        return False, "\u5c1a\u672a\u8e0f\u5165\u4fee\u884c\u8def\uff0c\u53d1\u9001\u201c\u7b7e\u5230\u201d\u5148\u89c9\u9192\u7075\u6839\u3002"
    if record.spirit_liquid <= 0:
        return False, "\u5f53\u524d\u6ca1\u6709\u53ef\u70bc\u5316\u7684\u7cbe\u7eaf\u7075\u6db2\u3002"
    if is_cultivation_locked(record, today):
        return False, blocked_cultivation_message(record)
    if is_breakthrough_bottleneck(record):
        return False, "\u5f53\u524d\u5df2\u81f3\u74f6\u9888\u5dc5\u5cf0\uff0c\u8bf7\u5148\u5b8c\u6210\u7a81\u7834\uff0c\u518d\u70bc\u5316\u7cbe\u7eaf\u7075\u6db2\u3002"
    if record.realm_index >= len(REALMS) - 1 and record.realm_exp >= record.progress_required:
        return False, "\u5f53\u524d\u5df2\u81f3\u5927\u9053\u5c3d\u5934\uff0c\u7cbe\u7eaf\u7075\u6db2\u6682\u65f6\u65e0\u6cd5\u7ee7\u7eed\u63a8\u52a8\u4fee\u4e3a\u3002"
    consume = record.spirit_liquid if amount is None else max(0, min(int(amount), record.spirit_liquid))
    if consume <= 0:
        return False, "\u8bf7\u8f93\u5165\u8981\u70bc\u5316\u7684\u7cbe\u7eaf\u7075\u6db2\u6570\u91cf\u3002"
    record.spirit_liquid -= consume
    exp_result = apply_exp(record, consume, today)
    applied_exp, leveled = exp_result
    if applied_exp <= 0 and exp_result.spirit_liquid <= 0:
        record.spirit_liquid += consume
        return False, "\u5f53\u524d\u7075\u6db2\u65e0\u6cd5\u878d\u5165\u4e39\u7530\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5\u3002"
    if applied_exp <= 0:
        return True, exp_gain_text(f"\u70bc\u5316\u7cbe\u7eaf\u7075\u6db2 {consume}", applied_exp, leveled, exp_result)
    return True, exp_gain_text(f"\u70bc\u5316\u7cbe\u7eaf\u7075\u6db2 {consume}", applied_exp, leveled, exp_result)


def use_pill(record: UserRecord, pill_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, PILL_CATEGORY, pill_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u4e39\u836f\u3002"
    name = reward_name(result)
    requirement = current_breakthrough_requirement(record)
    if requirement and name in set(requirement["items"]):
        append_reward(record, result)
        return False, f"{reward_display_name(result)} \u662f\u5f53\u524d\u7a81\u7834\u9053\u5177\uff0c\u8bf7\u53d1\u9001\u201c\u7a81\u7834\u201d\u4f7f\u7528\u3002"
    if is_cultivation_locked(record):
        append_reward(record, result)
        return False, blocked_cultivation_message(record)
    exp = tier_exp(CONSUMABLE_EXP_BASE, str(result.get("tier")), str(result.get("grade")))
    exp_result = apply_exp(record, exp)
    applied_exp, leveled = exp_result
    if applied_exp <= 0:
        if exp_result.spirit_liquid:
            return True, exp_gain_text(f"\u670d\u7528 {reward_display_name(result)}", applied_exp, leveled, exp_result)
        append_reward(record, result)
        return False, "\u5f53\u524d\u5df2\u81f3\u74f6\u9888\u5dc5\u5cf0\uff0c\u670d\u7528\u4e39\u836f\u4e5f\u65e0\u6cd5\u589e\u957f\u4fee\u4e3a\uff0c\u8bf7\u5148\u7a81\u7834\u3002"
    return True, exp_gain_text(f"\u670d\u7528 {reward_display_name(result)}", applied_exp, leveled, exp_result)

def refine_spirit_stone(record: UserRecord, stone_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, SPIRIT_STONE_CATEGORY, stone_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7075\u77f3\u3002"
    if is_cultivation_locked(record):
        append_reward(record, result)
        return False, blocked_cultivation_message(record)
    reserve = int(SPIRIT_STONE_VALUES.get(str(result.get("tier")), 8) * grade_ratio(str(result.get("grade"))))
    record.spirit_stones += reserve
    exp = max(1, reserve // 2)
    exp_result = apply_exp(record, exp)
    applied_exp, leveled = exp_result
    prefix = f"\u70bc\u5316 {reward_display_name(result)}\uff0c\u7075\u77f3\u50a8\u5907 +{reserve}"
    if applied_exp <= 0:
        if exp_result.spirit_liquid:
            return True, exp_gain_text(prefix, applied_exp, leveled, exp_result)
        append_reward(record, result)
        record.spirit_stones = max(0, record.spirit_stones - reserve)
        return False, "\u5f53\u524d\u5df2\u81f3\u74f6\u9888\u5dc5\u5cf0\uff0c\u7075\u77f3\u7075\u6c14\u65e0\u6cd5\u7ee7\u7eed\u70bc\u5165\u4e39\u7530\uff0c\u8bf7\u5148\u7a81\u7834\u3002"
    return True, exp_gain_text(prefix, applied_exp, leveled, exp_result)

def use_food(record: UserRecord, food_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, FOOD_CATEGORY, food_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7075\u98df\u3002"
    if is_cultivation_locked(record):
        append_reward(record, result)
        return False, blocked_cultivation_message(record)
    exp = max(1, tier_exp(CONSUMABLE_EXP_BASE, str(result.get("tier")), str(result.get("grade"))) // 2)
    exp_result = apply_exp(record, exp)
    applied_exp, leveled = exp_result
    prefix = f"\u4eab\u7528 {reward_display_name(result)}\uff0c\u6c14\u8840\u56de\u6696"
    if applied_exp <= 0:
        if exp_result.spirit_liquid:
            return True, exp_gain_text(prefix, applied_exp, leveled, exp_result)
        append_reward(record, result)
        return False, "\u5f53\u524d\u5df2\u81f3\u74f6\u9888\u5dc5\u5cf0\uff0c\u7075\u98df\u53ea\u80fd\u6696\u80c3\uff0c\u65e0\u6cd5\u518d\u6da8\u4fee\u4e3a\u3002"
    return True, exp_gain_text(prefix, applied_exp, leveled, exp_result)

def _batch_limit(limit: Optional[int]) -> int:
    if limit is None:
        return 999
    try:
        return max(1, min(999, int(limit)))
    except (TypeError, ValueError):
        return 999


def _compact_item_names(items: Sequence[str], max_items: int = 6) -> str:
    names = [str(item) for item in items if item]
    if not names:
        return "无"
    text = "、".join(names[:max_items])
    if len(names) > max_items:
        text += f"等{len(names)}件"
    return text


def _batch_apply_exp_items(
    record: UserRecord,
    category: str,
    limit: Optional[int],
    verb: str,
    exp_ratio: float = 1.0,
    reserve_stones: bool = False,
    skip_names: Optional[set[str]] = None,
) -> tuple[bool, str]:
    if record.root is None:
        return False, "尚未踏入修行路，发送“签到”先觉醒灵根。"
    if is_cultivation_locked(record):
        return False, blocked_cultivation_message(record)
    wanted = _batch_limit(limit)
    skip_names = skip_names or set()
    candidates: list[tuple[int, dict[str, Any], int, int]] = []
    for list_index, reward in enumerate(record.rewards or []):
        if reward_category(reward) != category:
            continue
        normalized = normalize_reward(reward, record)
        name = reward_name(normalized)
        if name in skip_names:
            continue
        if category == SPIRIT_STONE_CATEGORY:
            reserve = int(SPIRIT_STONE_VALUES.get(str(normalized.get("tier")), 8) * grade_ratio(str(normalized.get("grade"))))
            exp = max(1, reserve // 2)
        elif category == "\u7075\u6750" and is_demon_core_item(normalized):
            reserve = 0
            exp = demon_core_cultivation_exp(normalized)
        elif category == "\u7075\u6750":
            continue
        else:
            reserve = 0
            exp = tier_exp(CONSUMABLE_EXP_BASE, str(normalized.get("tier")), str(normalized.get("grade")))
            if category == FOOD_CATEGORY:
                exp = max(1, exp // 2)
        exp = max(1, int(exp * exp_ratio))
        candidates.append((list_index, normalized, exp, reserve))
        if len(candidates) >= wanted:
            break
    if not candidates:
        if category == PILL_CATEGORY and skip_names:
            return False, "没有可批量服用的丹药；当前突破道具已自动跳过，请发送“突破”使用。"
        return False, f"没有可批量使用的{category}。"
    before_stones = int(record.spirit_stones)
    before_liquid = int(record.spirit_liquid)
    before_exp = int(record.realm_exp)
    before_total = int(record.total_exp)
    before_realm = int(record.realm_index)
    names = [reward_display_name(item) for _, item, _, _ in candidates]
    total_exp = sum(exp for _, _, exp, _ in candidates)
    total_reserve = sum(reserve for _, _, _, reserve in candidates)
    if record.rewards is None:
        return False, f"没有可批量使用的{category}。"
    for list_index, _, _, _ in sorted(candidates, reverse=True):
        record.rewards.pop(list_index)
    if reserve_stones and total_reserve:
        record.spirit_stones += total_reserve
    exp_result = apply_exp(record, total_exp)
    applied_exp, leveled = exp_result
    if applied_exp <= 0 and exp_result.spirit_liquid <= 0:
        for _, reward, _, _ in candidates:
            append_reward(record, reward)
        record.spirit_stones = before_stones
        record.spirit_liquid = before_liquid
        record.realm_exp = before_exp
        record.total_exp = before_total
        record.realm_index = before_realm
        return False, f"当前修为无法吸纳这些{category}，本次未消耗道具。"
    prefix = f"{verb}{len(candidates)}件{category}"
    if reserve_stones and total_reserve:
        prefix += f"，灵石储备 +{total_reserve}"
    message = exp_gain_text(prefix, applied_exp, leveled, exp_result)
    message += f"\n消耗：{_compact_item_names(names)}。"
    if category == PILL_CATEGORY and skip_names:
        skipped = sum(1 for reward in record.rewards or [] if reward_category(reward) == PILL_CATEGORY and reward_name(reward) in skip_names)
        if skipped:
            message += f"\n已跳过当前突破丹药 {skipped} 件。"
    if reserve_stones:
        message += f"\n当前灵石：{spirit_stone_text(record.spirit_stones)}。"
    if record.spirit_liquid != before_liquid:
        message += f"\n当前精纯灵液：{record.spirit_liquid}。"
    return True, message


def use_pills_batch(record: UserRecord, limit: Optional[int] = None) -> tuple[bool, str]:
    protected = {
        str(item)
        for requirement in BREAKTHROUGH_REQUIREMENTS.values()
        for item in requirement.get("items", [])
    }
    return _batch_apply_exp_items(record, PILL_CATEGORY, limit, "服用", skip_names=protected)


def refine_spirit_stones_batch(record: UserRecord, limit: Optional[int] = None) -> tuple[bool, str]:
    return _batch_apply_exp_items(record, SPIRIT_STONE_CATEGORY, limit, "炼化", reserve_stones=True)


def refine_demon_cores_batch(record: UserRecord, limit: Optional[int] = None) -> tuple[bool, str]:
    return _batch_apply_exp_items(record, "\u7075\u6750", limit, "炼化")

def use_foods_batch(record: UserRecord, limit: Optional[int] = None) -> tuple[bool, str]:
    return _batch_apply_exp_items(record, FOOD_CATEGORY, limit, "享用")


def use_curio(record: UserRecord, curio_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, CURIO_CATEGORY, curio_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u5947\u7269\u3002"
    name = reward_name(result)
    requirement = current_breakthrough_requirement(record)
    if requirement and name in set(requirement["items"]):
        append_reward(record, result)
        return False, f"{reward_display_name(result)} \u662f\u5f53\u524d\u7a81\u7834\u9053\u5177\uff0c\u8bf7\u53d1\u9001\u201c\u7a81\u7834\u201d\u4f7f\u7528\u3002"
    roll = random.random()
    if roll < 0.38:
        record.fishing_chances += 1
        return True, f"\u50ac\u52a8 {reward_display_name(result)}\uff0c\u8bf8\u5929\u6c34\u6ce2\u8f7b\u54cd\uff0c\u5782\u9493\u6b21\u6570 +1\u3002"
    if roll < 0.78:
        if is_cultivation_locked(record):
            append_reward(record, result)
            return False, blocked_cultivation_message(record)
        exp = tier_exp(INSTANT_EXP_BASE, str(result.get("tier")), str(result.get("grade")))
        exp_result = apply_exp(record, exp)
        applied_exp, leveled = exp_result
        prefix = f"\u53c2\u609f {reward_display_name(result)}\uff0c\u5fc3\u795e\u901a\u660e"
        if applied_exp <= 0:
            if exp_result.spirit_liquid:
                return True, exp_gain_text(prefix, applied_exp, leveled, exp_result)
            append_reward(record, result)
            return False, "\u5f53\u524d\u5df2\u81f3\u74f6\u9888\u5dc5\u5cf0\uff0c\u5947\u7269\u7075\u673a\u65e0\u6cd5\u70bc\u5316\uff0c\u8bf7\u5148\u7a81\u7834\u3002"
        return True, exp_gain_text(prefix, applied_exp, leveled, exp_result)
    reward = draw_fishing_rewards(1, record)[0]
    append_reward(record, reward)
    return True, f"{reward_display_name(result)} \u5185\u85cf\u5939\u5c42\uff0c\u53d6\u51fa {reward_display_name(reward)}\u3002"

def identify_misc_item(record: UserRecord, misc_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, MISC_CATEGORY, misc_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u6742\u7269\u3002"
    roll = random.random()
    if roll < 0.45:
        pool = [reward for reward in FISHING_REWARDS if reward[2] not in {"\u4ed9\u7f18", "\u6742\u7269"}]
        tier, grade, category, name, description, _ = weighted_choice([(reward, float(reward[5])) for reward in pool])
        reward = normalize_reward({"tier": tier, "grade": grade, "category": category, "name": name, "description": description}, record)
        append_reward(record, reward)
        return True, f"\u9274\u5b9a {reward_display_name(result)}\uff0c\u7adf\u8fa8\u51fa {reward_display_name(reward)}\u3002"
    if roll < 0.72:
        if is_cultivation_locked(record):
            return True, f"\u9274\u5b9a {reward_display_name(result)}\uff0c\u53ea\u6563\u51fa\u4e00\u7f15\u7075\u6c14\uff1b\u56e0\u7981\u4fee\u671f\u672a\u80fd\u5438\u7eb3\u3002"
        exp = max(1, tier_exp(CONSUMABLE_EXP_BASE, str(result.get("tier")), str(result.get("grade"))) // 3)
        exp_result = apply_exp(record, exp)
        applied_exp, leveled = exp_result
        return True, exp_gain_text(f"\u9274\u5b9a {reward_display_name(result)}\uff0c\u6b8b\u4f59\u7075\u6c14\u5165\u4f53", applied_exp, leveled, exp_result)
    return True, f"\u9274\u5b9a {reward_display_name(result)}\uff0c\u53ea\u662f\u65e7\u7269\u4e00\u4ef6\uff0c\u968f\u624b\u5316\u4f5c\u5c18\u7070\u3002"

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


def equip_talisman(record: UserRecord, talisman_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, TALISMAN_CATEGORY, talisman_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7b26\u7b93\u3002"
    _, talisman = result
    required_index = talisman_required_realm_index(str(talisman.get("tier")))
    if record.realm_index < required_index:
        return False, f"{reward_display_name(talisman)} \u9700\u8981{REALMS[required_index]}\u624d\u80fd\u88c5\u5907\u751f\u6548\u3002"
    record.equipped_talisman = dict(talisman)
    return True, f"\u5df2\u88c5\u5907\u7b26\u7b93\u69fd {reward_display_name(talisman)}\uff0c\u8fdb\u5165\u6597\u6cd5\u65f6\u751f\u6548\uff0c\u4e0d\u4f1a\u6d88\u8017\u3002"


def unequip_talisman(record: UserRecord) -> str:
    if not record.equipped_talisman:
        return "\u5f53\u524d\u6ca1\u6709\u88c5\u5907\u7b26\u7b93\u3002"
    old_name = reward_display_name(record.equipped_talisman)
    record.equipped_talisman = None
    return f"\u5df2\u5378\u4e0b\u7b26\u7b93 {old_name}\u3002"


def use_talisman(record: UserRecord, talisman_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, TALISMAN_CATEGORY, talisman_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7b26\u7b93\u3002"
    list_index, talisman = result
    if is_breakthrough_talisman_name(reward_name(talisman)):
        return False, f"{reward_display_name(talisman)} \u662f\u7a81\u7834\u7b26\u4ee4\uff0c\u8bf7\u5728\u5bf9\u5e94\u5883\u754c\u5dc5\u5cf0\u53d1\u9001\u201c\u7a81\u7834\u201d\u4f7f\u7528\u3002"
    required_index = talisman_required_realm_index(str(talisman.get("tier")))
    if record.realm_index < required_index:
        return False, f"{reward_display_name(talisman)} \u9700\u8981{REALMS[required_index]}\u624d\u80fd\u4f7f\u7528\u3002"
    if record.rewards is not None:
        record.rewards.pop(list_index)
    strength = tier_exp(CONSUMABLE_EXP_BASE, str(talisman.get("tier")), str(talisman.get("grade"))) * 6
    return True, f"\u6fc0\u53d1 {reward_display_name(talisman)}\uff0c\u7b26\u5149\u5316\u4f5c {strength} \u70b9\u5386\u7ec3\u5a01\u52bf\u3002"



MYSTIC_SUCCESS_TEXTS = {
    "上古宗门遗址": [
        "你屏住气息，将残阵一线线拆开，尘封多年的灵机终于从砖缝中浮出。",
        "一阵旧日讲法声在耳畔回响，你照着经义运转周天，眼前禁制悄然退开。",
        "祖师残像只看了你一眼，袖中便落下一点清光，像是认可，又像是考校。",
        "断剑轻鸣，满地铁锈化作细碎星芒，你在剑意余韵中寻到一件遗物。",
        "问心石没有碎裂，只映出你一路修行的狼狈与坚持，随后让开半步。",
        "丹房地火复燃一瞬，灰烬中滚出尚未完全失性的灵物。",
        "护山阵纹与你的灵力短暂同调，藏在阵眼下的暗格自行弹开。",
        "旧钟低鸣三声，群山间云气倒卷，像有一位失名长老隔世赐缘。",
    ],
    "兽潮": [
        "你抓住兽群换气的刹那突入，避开首领锋芒，从血尘里夺得战利。",
        "妖兽嘶吼震山，你以阵盘压住退路，等兽潮一乱便抽身取宝。",
        "首领气血如炉，却被你引向乱石阵中，轰鸣过后只余一地灵材。",
        "你救下的散修抛来一枚储物符，转身便消失在妖雾深处。",
        "兽巢深处有幼兽啼鸣，你没有恋战，只取走一件被妖气温养的灵物。",
        "雷光劈落，兽群短暂伏地，你趁天威压顶穿过妖云。",
        "一头老兽望了你许久，没有扑上来，只将爪下灵物推到血线之外。",
        "你以傀儡诱开兽潮主力，回身从巢穴暗处摸出一份机缘。",
    ],
    "上古大能洞府": [
        "洞府禁制层层亮起，你以神识压住心魔杂念，终于从杀局中看见生门。",
        "古灯照出万千岔路，你只守住本心一步踏出，脚下白玉阶化作星河。",
        "宝匣内没有金光，只有一声叹息；叹息散尽后，匣底浮出真正的遗赠。",
        "壁画中的古修抬手讲道，你听不全，却从残缺处悟到一线破局之法。",
        "青铜棺震动三次便归于沉寂，棺旁石槽吐出被岁月磨亮的灵物。",
        "水镜映出你最贪婪的一念，你没有伸手，镜面反而碎成一地清辉。",
        "阵眼吞下你的灵力，又吐出更精纯的一缕，洞府深处随之开出暗门。",
        "棋盘自行落子，你弃掉三路胜势，只求一线生机，反倒赢得洞府认可。",
    ],
}

MYSTIC_EMPTY_TEXTS = {
    "上古宗门遗址": [
        "石壁无声合拢，你绕行半晌才寻回原路。",
        "残经一触即碎，只余满手尘灰。",
        "旧阵忽明忽暗，你谨慎退开，没有惊动更深处的禁制。",
        "风声像讲法，又像叹息，最终什么也没有留下。",
    ],
    "兽潮": [
        "兽群忽然回涌，你稳住气息，避开了暗处扑杀。",
        "前方腥风太重，你没有硬闯，绕路退回安全处。",
        "首领威压扫过山谷，你伏身不动，等尘埃落下才继续前行。",
        "妖兽足印在乱石中断绝，只留下一片焦黑血泥。",
    ],
    "上古大能洞府": [
        "禁制轻轻一颤，你察觉不妙，及时收回神识。",
        "古镜里的人影笑了一下，你没有回应，镜面随即黯淡。",
        "宝匣只是幻象，指尖穿过时只碰到冰冷尘埃。",
        "洞府深处传来锁链声，你后退一步，避开了未知杀机。",
    ],
}

BAD_ENDING_TEXTS = {
    "上古宗门遗址": "问心石骤然翻转，昔年宗门覆灭的怨念如潮压来。你强行脱身，却被残阵浊气封住经脉。",
    "兽潮": "兽王忽然睁开竖瞳，万兽同声嘶吼，血色妖云瞬间压下。你撕开缺口逃出，却被妖煞侵入经脉。",
    "上古大能洞府": "洞府传承顷刻化作杀局，古灯映出的不是大道，而是一尊借壳归来的邪影。你斩断神识退走，却被浊气封住经脉。",
}


def mystic_success_text(realm_type: str) -> str:
    theme = MYSTIC_EVENT_THEMES.get(realm_type)
    if theme:
        lines = [str(item[2]) for item in theme.get("reward_lines", []) if len(item) >= 3]
        if lines:
            return random.choice(lines)
    return random.choice(MYSTIC_SUCCESS_TEXTS.get(realm_type, MYSTIC_SUCCESS_TEXTS["上古宗门遗址"]))


def mystic_empty_text(realm_type: str) -> str:
    theme = MYSTIC_EVENT_THEMES.get(realm_type)
    if theme and theme.get("empty"):
        return random.choice(list(theme["empty"]))
    return random.choice(MYSTIC_EMPTY_TEXTS.get(realm_type, MYSTIC_EMPTY_TEXTS["上古宗门遗址"]))


def mystic_bad_ending_text(realm_type: str) -> str:
    theme = MYSTIC_EVENT_THEMES.get(realm_type)
    if theme and theme.get("bad"):
        return str(theme["bad"])
    return BAD_ENDING_TEXTS.get(realm_type, BAD_ENDING_TEXTS["上古大能洞府"])


def mystic_realm_title(realm: dict[str, Any]) -> str:
    if realm.get("title"):
        return str(realm["title"])
    realm_type = str(realm.get("type", "未知秘境"))
    if realm_type == "兽潮":
        return f"{realm.get('boss_realm', '未知')}兽巢"
    return realm_type


def mystic_option_display(option: Any) -> str:
    if isinstance(option, dict):
        text = str(option.get("text") or "未知去处")
        hint = str(option.get("reward_hint") or "").strip()
        category = str(option.get("category") or "").strip()
        if hint:
            return f"{text}（线索：{hint}）"
        if category:
            return f"{text}（线索：{category}）"
        return text
    return str(option)


def mystic_realm_options_text(record: UserRecord) -> str:
    realm = record.mystic_realm or {}
    options = list(realm.get("options", []))
    if not realm:
        return "当前没有正在探索的秘境。"
    lines = [f"【秘境探索】{mystic_realm_title(realm)}", f"剩余探索次数：{int(realm.get('steps_left', 0))}/{MYSTIC_REALM_MAX_STEPS}"]
    if realm.get("type") == "兽潮":
        lines.append(f"兽潮首领：{realm.get('boss_realm', '未知')}·{realm.get('boss_name', '无名妖兽')}")
    if any(isinstance(item, dict) and item.get("boss") for item in options):
        lines.append(mystic_boss_attempt_status_text(record))
    if realm.get("insight") and realm.get("bad_option_index"):
        lines.append(f"天机示警：第 {int(realm.get('bad_option_index'))} 项通往坏结局。")
    for index, option in enumerate(options, start=1):
        lines.append(f"{index}. {mystic_option_display(option)}")
    lines.append("发送“探索 编号”继续。")
    return "\n".join(lines)



def is_high_risk_mystic_type(realm_type: str) -> bool:
    return str(realm_type) in HIGH_RISK_MYSTIC_REALM_TYPES


def build_high_risk_mystic_event_pool(realm_type: str) -> list[dict[str, Any]]:
    rewards = [
        ("\u7075\u6750", "\u5e9a\u91d1", "\u88c2\u7f1d\u4e2d\u6eda\u51fa\u4e00\u7f15\u5e9a\u91d1\u950b\u8292\uff0c\u53ef\u5165\u5251\u5668\u3002"),
        ("\u7075\u6750", "\u4e07\u7269\u6bcd\u6c14", "\u6c89\u91cd\u6bcd\u6c14\u81ea\u5730\u8109\u5347\u8d77\uff0c\u50cf\u4e00\u53e3\u672a\u6210\u7684\u9f0e\u3002"),
        ("\u7075\u6750", "\u865a\u7a7a\u4ed9\u91d1", "\u865a\u7a7a\u6ce2\u7eb9\u88c2\u5f00\uff0c\u4ed9\u91d1\u5982\u955c\u7247\u843d\u5165\u638c\u5fc3\u3002"),
        ("\u7075\u6750", "\u4e0d\u6b7b\u836f\u9752\u83b2\u6b8b\u8eaf", "\u9752\u83b2\u6b8b\u8eaf\u6709\u4e00\u7ebf\u751f\u673a\uff0c\u9999\u6c14\u538b\u4f4f\u8840\u8165\u3002"),
        ("\u5947\u7269", "\u4e7e\u84dd\u51b0\u7130", "\u5bd2\u7130\u4e0d\u71c3\u7269\uff0c\u53ea\u7167\u795e\u9b42\uff0c\u4e00\u7f15\u4e7e\u84dd\u51b0\u7130\u88ab\u4f60\u5c01\u5165\u7389\u74f6\u3002"),
        ("\u5947\u7269", "\u865a\u5929\u9f0e", "\u53e4\u6bbf\u6df1\u5904\u6709\u9f0e\u5f71\u4e00\u95ea\uff0c\u865a\u5929\u9f0e\u7684\u9053\u97f5\u843d\u5165\u4f60\u624b\u4e2d\u3002"),
        ("\u5947\u7269", "\u4eba\u7687\u5370", "\u4eba\u9053\u6c14\u8fd0\u51dd\u6210\u5370\u73ba\uff0c\u4e00\u77ac\u95f4\u538b\u4f4f\u56db\u5468\u9b54\u6c14\u3002"),
        (IMMORTAL_SEED_CATEGORY, "内景星源仙源", "灵台忽开一线星井，内景星源化作温润仙光纳入掌心。"),
        (IMMORTAL_SEED_CATEGORY, "迅岚流影仙源", "一缕青白风息绕过雷痕，迅岚流影仙源在指间凝成。"),
        (SPECIAL_ABILITY_CATEGORY, "\u4ed6\u5316\u81ea\u5728\u5f71", "\u4e00\u9053\u4ed6\u5316\u6218\u5f71\u5728\u8eab\u540e\u51dd\u51fa\uff0c\u968f\u5373\u5316\u6210\u4f20\u627f\u6750\u6599\u3002"),
    ]
    rewards.extend((ARTIFACT_CATEGORY, name, f"\u5e1d\u5a01\u4e00\u95ea\uff0c{name}\u7684\u771f\u5f62\u4ece\u9669\u5730\u6df1\u5904\u6d6e\u73b0\u3002") for name in EMPEROR_ARTIFACT_NAMES)
    places = ["\u6b8b\u7834\u796d\u575b", "\u8840\u8272\u77f3\u95e8", "\u5e1d\u7eb9\u65ad\u58c1", "\u865a\u7a7a\u88c2\u7f1d", "\u9ed1\u6697\u53e4\u4e95", "\u65e0\u58f0\u6218\u573a", "\u9ec4\u6cc9\u6cb3\u7554", "\u661f\u7a7a\u6b8b\u6865", "\u4ed9\u706b\u51b0\u6d77", "\u7981\u533a\u6df1\u5904"]
    omens = ["\u4e00\u7f15\u5e1d\u5a01\u626b\u8fc7\u80cc\u810a", "\u8fdc\u5904\u6709\u53e4\u4ee3\u9053\u97f3\u4e0e\u54ed\u58f0\u540c\u54cd", "\u5730\u9762\u6bcf\u4e00\u9053\u7eb9\u8def\u90fd\u50cf\u6d3b\u7269", "\u6cd5\u5219\u98ce\u66b4\u5ffd\u7136\u538b\u4f4e", "\u4f60\u770b\u89c1\u81ea\u5df1\u6b7b\u53bb\u53c8\u91cd\u6765\u7684\u5012\u5f71"]
    events = []
    for idx in range(100):
        category, hint, success = rewards[idx % len(rewards)]
        danger = idx % 5 not in {1, 3}
        option_text = f"\u8e0f\u5165{places[idx % len(places)]}\uff0c{omens[idx % len(omens)]}"
        events.append({"text": option_text, "category": category, "reward_hint": hint, "success": success, "forced_bad": danger, "high_risk": True})
    return events


def maybe_add_mystic_fishing_option(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if random.random() < MYSTIC_FISHING_OPTION_RATE:
        options.append(
            {
                "text": "循着灵河回响抛下一缕神识钓线",
                "category": "奇物",
                "reward_hint": "垂钓次数+1",
                "fishing_chance": 1,
                "success": "秘境水脉忽然回应，钓线牵回一枚灵河印记。",
            }
        )
        random.shuffle(options)
    return options


def roll_mystic_options(realm_type: str) -> list[dict[str, Any]]:
    if is_high_risk_mystic_type(realm_type):
        pool = build_high_risk_mystic_event_pool(realm_type)
        safe = [item for item in pool if not item.get("forced_bad")]
        bad = [item for item in pool if item.get("forced_bad")]
        options = random.sample(safe, k=min(2, len(safe))) + random.sample(bad, k=min(3, len(bad)))
        random.shuffle(options)
        return maybe_add_mystic_fishing_option([dict(item) for item in options])
    pool = MYSTIC_OPTION_POOLS.get(realm_type, MYSTIC_OPTION_POOLS["\u4e0a\u53e4\u5b97\u95e8\u9057\u5740"])
    return maybe_add_mystic_fishing_option([dict(item) for item in random.sample(pool, k=min(5, len(pool)))])


def mystic_realm_intro(realm: dict[str, Any]) -> str:
    realm_type = str(realm.get("type"))
    if realm_type == "兽潮":
        return f"远处妖云翻涌，探得{realm.get('boss_realm', '未知')}兽巢，首领似为{realm.get('boss_name', '无名妖兽')}。"
    return str(MYSTIC_EVENT_THEMES.get(realm_type, {}).get("intro", "秘境灵雾翻涌，等你踏入。"))


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

    def clamp_index(value: int) -> int:
        return max(1, min(len(REALMS) - 1, value))

    beast_index = clamp_index(random.choice([base_index, base_index - 1]) if random.random() < 0.5 else base_index + random.choice([1, 2, 2, 3]))
    beast_stage = random.choice(["初期", "中期", "后期", "圆满"])
    candidate_entries = [
        {
            "type": "上古宗门遗址",
            "title": "上古宗门遗址",
            "recommended_index": clamp_index(base_index + random.choice([0, 1, 1, 2])),
            "danger": random.randint(12, 30),
        },
        {
            "type": "兽潮",
            "title": f"{recommended_realm_text(beast_index)}妖兽兽巢",
            "recommended_index": beast_index,
            "recommended": recommended_realm_text(beast_index, beast_stage),
            "boss_realm_index": beast_index,
            "boss_realm": REALMS[beast_index],
            "boss_name": random_beast_name(),
            "danger": random.randint(18, 38),
        },
        {
            "type": "上古大能洞府",
            "title": "上古大能洞府",
            "recommended_index": clamp_index(base_index + random.choice([2, 3, 3, 4])),
            "danger": random.randint(22, 46),
            "false_lure": random.random() < 0.35,
        },
        {
            "type": "星古矿区",
            "title": "星古矿区",
            "recommended_index": clamp_index(base_index + random.choice([1, 2, 2, 3])),
            "danger": random.randint(20, 44),
            "false_lure": random.random() < 0.18,
        },
        {
            "type": "魂界残域",
            "title": "魂界残域",
            "recommended_index": clamp_index(base_index + random.choice([0, 1, 2, 2])),
            "danger": random.randint(16, 40),
        },
        {
            "type": "古铜云阙",
            "title": "古铜云阙",
            "recommended_index": clamp_index(base_index + random.choice([3, 4, 4, 5])),
            "danger": random.randint(28, 56),
            "false_lure": random.random() < 0.28,
        },
    ]
    candidate_entries = [entry for entry in candidate_entries if str(entry.get("type")) in MYSTIC_ENABLED_TYPES]
    for entry in candidate_entries:
        entry.setdefault("recommended", recommended_realm_text(int(entry.get("recommended_index", base_index))))
    beast_entries = [entry for entry in candidate_entries if entry["type"] == "兽潮"]
    others = [entry for entry in candidate_entries if entry["type"] != "兽潮"]
    entries: list[dict[str, Any]] = []
    if beast_entries:
        entries.append(beast_entries[0])
    if others:
        entries.extend(random.sample(others, k=min(2, len(others))))
    if len(entries) < min(3, len(candidate_entries)):
        remaining = [entry for entry in candidate_entries if entry not in entries]
        if remaining:
            entries.extend(random.sample(remaining, k=min(min(3, len(candidate_entries)) - len(entries), len(remaining))))
    high_risk_pool = [item for item in HIGH_RISK_MYSTIC_REALM_TYPES if item in MYSTIC_ENABLED_HIGH_RISK_TYPES]
    if high_risk_pool and (random.random() < 0.28 or not entries):
        high_type = random.choice(high_risk_pool)
        high_index = clamp_index(base_index + random.choice([2, 3, 4, 5]))
        entries.append(
            {
                "type": high_type,
                "title": high_type,
                "recommended_index": high_index,
                "recommended": recommended_realm_text(high_index),
                "danger": random.randint(45, 78),
                "false_lure": True,
                "high_risk": True,
            }
        )
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
    if realm_type not in MYSTIC_REALM_TYPES and not is_high_risk_mystic_type(realm_type):
        return False, "秘境类型可选：上古宗门遗址、兽潮、上古大能洞府、星古矿区、魂界残域、古铜云阙，以及高危险地。"
    if record.mystic_realm:
        return False, mystic_realm_options_text(record)
    if is_cultivation_locked(record, today):
        return False, blocked_cultivation_message(record)
    recommended_index = int(entrance.get("recommended_index", max(1, min(len(REALMS) - 1, record.realm_index + 2))))
    boss_realm = str(entrance.get("boss_realm") or REALMS[min(len(REALMS) - 1, recommended_index)])
    boss_name = str(entrance.get("boss_name") or random_beast_name())
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
        "boss_element": str(entrance.get("boss_element") or random.choice(BASE_FIVE_ELEMENTS)),
        "options": roll_mystic_options(realm_type),
        "insight": bool(entrance.get("insight")) or has_soul_insight(record),
        "tianji": bool(entrance.get("tianji")),
    }
    if not is_high_risk_mystic_type(realm_type):
        realm["options"].append({"text": f"挑战秘境首领：{realm.get('boss_realm')}·{realm.get('boss_name')}", "boss": True, "category": "灵材", "reward_hint": "首领妖丹"})
    assign_mystic_bad_option(realm)
    if realm.get("tianji") and today is not None:
        record.last_tianji_mystic_date = today.isoformat()
    record.mystic_realm = realm
    return True, f"{mystic_realm_intro(realm)}\n{mystic_realm_options_text(record)}"

def mystic_reward_category(realm_type: str) -> str:
    configured = MYSTIC_CATEGORY_WEIGHTS.get(realm_type) or MYSTIC_CATEGORY_WEIGHTS.get("default")
    if configured:
        return weighted_choice(configured)
    defaults = default_mystic_category_weights()
    return weighted_choice(_category_weight_pairs(defaults.get(realm_type) or defaults["default"]))


def draw_reward_by_category(category: str, record: Optional[UserRecord] = None, preferred_realm_index: Optional[int] = None) -> dict[str, Any]:
    pool = [reward for reward in FISHING_REWARDS if reward[2] == category]
    if not pool:
        return draw_fishing_rewards(1, record)[0]
    tier, grade, item_category, name, description, _ = weighted_choice([(reward, float(reward[5])) for reward in pool])
    if item_category == ARTIFACT_CATEGORY:
        realm_index = preferred_realm_index if preferred_realm_index is not None else (int(record.realm_index) if record is not None else 0)
        reward = draw_configured_artifact_reward(tier, grade)
    else:
        reward = {"tier": tier, "grade": grade, "category": item_category, "name": name, "description": description}
    return normalize_reward(reward, record)

def mystic_reward_tier(record: UserRecord, realm: dict[str, Any]) -> str:
    recommended = int(realm.get("recommended_index", record.realm_index or 1))
    gap = recommended - int(record.realm_index or 0)
    if gap >= 4:
        return weighted_choice([("天阶", 5), ("地阶", 4), ("玄阶", 1)])
    if gap >= 2:
        return weighted_choice([("地阶", 5), ("玄阶", 3), ("天阶", 1)])
    if gap >= 0:
        return weighted_choice([("玄阶", 5), ("地阶", 2), ("黄阶", 2)])
    return weighted_choice([("黄阶", 5), ("玄阶", 2), ("凡品", 2)])


def matching_fishing_reward(category: str, hint: str) -> Optional[tuple[str, str, str, str, str, int]]:
    pool = [reward for reward in FISHING_REWARDS if reward[2] == category]
    exact = [reward for reward in pool if str(reward[3]) == hint]
    fuzzy = [reward for reward in pool if hint and (hint in str(reward[3]) or str(reward[3]) in hint)]
    source_pool = exact or fuzzy
    if not source_pool:
        return None
    return weighted_choice([(reward, float(reward[5])) for reward in source_pool])



def draw_mystic_override_reward(record: UserRecord, realm: dict[str, Any]) -> Optional[dict[str, Any]]:
    rewards = MYSTIC_DROP_OVERRIDES.get(str(realm.get("type"))) or MYSTIC_DROP_OVERRIDES.get(str(realm.get("title"))) or []
    if not rewards:
        return None
    weighted: list[tuple[dict[str, Any], float]] = []
    for item in rewards:
        try:
            weight = float(item.get("weight", 1))
        except (TypeError, ValueError):
            weight = 1.0
        if weight > 0:
            weighted.append((item, weight))
    if not weighted:
        return None
    raw = dict(weighted_choice(weighted))
    raw.pop("weight", None)
    if reward_category(raw) == ARTIFACT_CATEGORY and not str(raw.get("name") or "").strip():
        return normalize_reward(draw_configured_artifact_reward(str(raw.get("tier") or ""), str(raw.get("grade") or "")), record)
    return normalize_reward(raw, record)


def draw_mystic_event_reward(record: UserRecord, realm: dict[str, Any], event: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    override_reward = draw_mystic_override_reward(record, realm)
    if override_reward is not None:
        return reward_category(override_reward), override_reward
    category = str(event.get("category") or mystic_reward_category(str(realm.get("type"))))
    hint = str(event.get("reward_hint") or "").strip()
    tier = mystic_reward_tier(record, realm)
    grade = weighted_choice([("极品", 1), ("上品", 2), ("中品", 4), ("下品", 3)])
    if category == ARTIFACT_CATEGORY:
        return category, normalize_reward(draw_configured_artifact_reward(tier, grade), record)
    if category == SPECIAL_ABILITY_CATEGORY:
        matched = matching_fishing_reward(category, hint) if hint else None
        if matched is not None:
            tier, grade, item_category, name, description, _ = matched
            return category, normalize_reward({"tier": tier, "grade": grade, "category": item_category, "name": name, "description": description}, record)
        reward = draw_special_ability_material(record)
        if hint and hint not in {"古修神通烙印", "旧宗传承残卷"}:
            reward["name"] = hint
        return category, normalize_reward(reward, record)
    if hint:
        if hint == "妖丹":
            boss_realm = realm_short_name(str(realm.get("boss_realm", REALMS[min(len(REALMS) - 1, record.realm_index)])))
            hint = f"{boss_element(realm)}系{boss_realm}妖丹"
        elif hint == "兽骨":
            hint = f"{str(realm.get('boss_name', '妖兽'))}兽骨"
        matched = matching_fishing_reward(category, hint)
        if matched is not None:
            tier, grade, item_category, name, description, _ = matched
            return category, normalize_reward({"tier": tier, "grade": grade, "category": item_category, "name": name, "description": description}, record)
        return category, normalize_reward({"tier": tier, "grade": grade, "category": category, "name": hint}, record)
    return category, draw_reward_by_category(category, record, int(realm.get("recommended_index", record.realm_index)))


def boss_archetype_config(realm: dict[str, Any]) -> dict[str, Any]:
    boss_name = str(realm.get("boss_name") or "")
    for key, config in BOSS_ARCHETYPE_CONFIGS.items():
        if key == "default":
            continue
        if any(token and token in boss_name for token in config.get("tokens", ())):
            return dict(config)
    return dict(BOSS_ARCHETYPE_CONFIGS["default"])


def realm_index_from_name(realm_name: str, fallback: int = 0) -> int:
    text = str(realm_name or "")
    for index, name in enumerate(REALMS):
        if text == name or text.startswith(name) or realm_short_name(name) in text:
            return index
    return max(0, min(len(REALMS) - 1, int(fallback)))


def boss_tier_for_realm(realm_index: int) -> str:
    if realm_index >= 13:
        return "仙帝兵"
    if realm_index >= 10:
        return "仙阶"
    if realm_index >= 5:
        return "天阶"
    if realm_index >= 3:
        return "地阶"
    if realm_index >= 2:
        return "玄阶"
    if realm_index >= 1:
        return "黄阶"
    return "凡品"


def boss_grade_for_realm(realm_index: int) -> str:
    if realm_index >= 8:
        return "极品"
    if realm_index >= 5:
        return "上品"
    if realm_index >= 2:
        return "中品"
    return "下品"


def boss_method_layers_for(method: dict[str, Any], realm_index: int) -> dict[str, int]:
    return {reward_signature(method): 1}

def boss_record_for_realm(realm: dict[str, Any], player: UserRecord) -> UserRecord:
    config = boss_archetype_config(realm)
    realm_index = realm_index_from_name(str(realm.get("boss_realm") or ""), int(realm.get("recommended_index", player.realm_index or 1)))
    attr = boss_element(realm)
    tier = boss_tier_for_realm(realm_index)
    grade = boss_grade_for_realm(realm_index)
    boss_name = str(realm.get("boss_name") or "秘境首领")
    boss = UserRecord(user_id=f"boss:{mystic_boss_limit_key(realm)}:{boss_name}")
    root_tier = tier if tier in TIER_RANKS and tier != "仙帝兵" else "天阶"
    purity = min(100, 72 + realm_index * 3)
    boss.root = make_root(root_tier, grade, attr, purity=purity, sources=[attr], source_purities={attr: purity})
    boss.realm_index = max(0, min(len(REALMS) - 1, realm_index))
    boss.realm_exp = int(realm_progress_required(boss.root, boss.realm_index) * min(0.88, 0.18 + realm_index * 0.035))
    boss.total_exp = cumulative_realm_exp(boss.root, boss.realm_index) + boss.realm_exp
    boss.sign_count = 30 + realm_index * 16
    boss.combat_race = str(config.get("race") or "妖族-远荒异兽")
    boss.physique = str(config.get("physique") or "凡体")
    boss.special_abilities = [str(item) for item in config.get("abilities", ())]
    method = make_reward(tier, grade, METHOD_CATEGORY, str(config.get("method") or "万兽吞灵诀"))
    method["kind"] = str(config.get("method_kind") or "战技类")
    method["techniques"] = list(config.get("techniques", ()))
    method["origin"] = str(config.get("intro") or "秘境首领天生妖术所化。")
    method["content"] = "首领本命传承，战斗时会自行催发。"
    boss.equipped_method = method
    boss.method_layers = boss_method_layers_for(method, realm_index)
    boss.method_proficiency = {reward_signature(method): 0}
    artifact = make_reward(tier, grade, ARTIFACT_CATEGORY, str(config.get("artifact") or "兽王爪"))
    offhand = make_reward(tier, grade, ARTIFACT_CATEGORY, str(config.get("offhand") or "兽骨牌"))
    armor = make_reward(tier, grade, ARTIFACT_CATEGORY, str(config.get("armor") or "兽王甲"))
    for item in (artifact, offhand, armor):
        item["required_attribute"] = attr
        item["min_realm_index"] = max(0, min(len(REALMS) - 1, realm_index))
    boss.equipped_artifact = artifact
    boss.equipped_artifacts = {"主手": artifact, "副手": offhand, "护甲": armor}
    talisman = make_reward(tier, grade, TALISMAN_CATEGORY, str(config.get("talisman") or "兽血狂战符"))
    talisman["min_realm_index"] = max(0, min(len(REALMS) - 1, realm_index))
    boss.equipped_talisman = talisman
    array = make_reward(tier, grade, ARRAY_CATEGORY, str(config.get("array") or "万兽奔雷阵"))
    boss.equipped_array = array
    boss.array_layers = {reward_signature(array): 1}
    boss.array_proficiency = {reward_signature(array): max(100, realm_index * 45)}
    return boss


def boss_combat_actions(realm: dict[str, Any], boss: UserRecord) -> list[dict[str, Any]]:
    config = boss_archetype_config(realm)
    techniques = list(config.get("techniques", ())) or available_battle_techniques(boss)
    abilities = list(config.get("abilities", ()))
    actions = [{"text": str(technique)} for technique in techniques[:5]]
    actions.extend({"text": str(ability)} for ability in abilities[:3])
    if not actions:
        actions.append({"text": "妖云压顶"})
    return actions


def player_boss_auto_actions(record: UserRecord) -> list[dict[str, Any]]:
    actions = [{"text": str(technique)} for technique in available_battle_techniques(record)[:5]]
    actions.extend({"text": str(ability)} for ability in normalize_special_abilities(record.special_abilities)[:3])
    if not actions:
        actions.append({"text": "即兴术式"})
    return actions



def split_boss_duel_damage(total: int, rounds: int, seed: str) -> list[int]:
    total = max(0, int(total))
    rounds = max(1, int(rounds))
    if total <= 0:
        return [0 for _ in range(rounds)]
    weights = [70 + stable_int(f"{seed}:{index}") % 61 for index in range(rounds)]
    weight_total = max(1, sum(weights))
    parts = [int(total * weight / weight_total) for weight in weights]
    diff = total - sum(parts)
    for index in range(abs(diff)):
        pos = index % rounds
        parts[pos] += 1 if diff > 0 else -1
    return [max(0, value) for value in parts]


def boss_duel_skill_cycle(fighter: dict[str, Any], fallback: Sequence[str], seed: str) -> list[str]:
    skills = [str(item) for item in fighter.get("triggered_techniques", []) if item]
    skills.extend(str(item) for item in fallback if item)
    skills.extend(str(item) for item in fighter.get("abilities", []) if item)
    skills = list(dict.fromkeys(skills))
    if not skills:
        return ["近身搏杀", "灵压冲撞", "护体灵光"]
    offset = stable_int(seed) % len(skills)
    return skills[offset:] + skills[:offset]


def build_mystic_boss_duel_timeline(result: dict[str, Any], realm: dict[str, Any], boss: UserRecord) -> list[str]:
    left = dict(result.get("left") or {})
    right = dict(result.get("right") or {})
    elapsed = max(5, int(result.get("elapsed_seconds", 60)))
    rounds = max(5, min(12, elapsed // 6 + (1 if elapsed % 6 else 0)))
    player_damage_total = max(0, int(right.get("max_hp", 0)) - int(right.get("hp", 0)))
    boss_damage_total = max(0, int(left.get("max_hp", 0)) - int(left.get("hp", 0)))
    player_damage_parts = split_boss_duel_damage(player_damage_total, rounds, f"boss-duel-player:{record_signature_for_boss(left)}:{right.get('user_id')}")
    boss_damage_parts = split_boss_duel_damage(boss_damage_total, rounds, f"boss-duel-boss:{right.get('user_id')}:{record_signature_for_boss(left)}")
    player_skills = boss_duel_skill_cycle(left, left.get("available_techniques", []), f"player-skills:{left.get('user_id')}")
    boss_skills = boss_duel_skill_cycle(right, available_battle_techniques(boss), f"boss-skills:{right.get('user_id')}")
    player_hp = max(0, int(left.get("max_hp", 1)))
    boss_hp = max(0, int(right.get("max_hp", 1)))
    player_name = str(left.get("nickname") or "宿主")
    boss_name = str(right.get("nickname") or realm.get("boss_name") or "秘境首领")
    intro = str(result.get("boss_intro") or "妖气压下，生死斗法已起。")
    boss_gears = "、".join(reward_display_name(item) for item in (boss.equipped_artifacts or {}).values()) or "妖骨本命兵"
    timeline = [
        f"入场：{intro}",
        f"对峙：{player_name}祭起功法与符箓，{boss_name}展开{boss.equipped_array and reward_display_name(boss.equipped_array) or '本命妖阵'}，灵器为{boss_gears}。",
    ]
    for index in range(rounds):
        seconds = min(elapsed, (index + 1) * 6)
        p_skill = player_skills[index % len(player_skills)]
        b_skill = boss_skills[index % len(boss_skills)]
        p_damage = player_damage_parts[index]
        b_damage = boss_damage_parts[index]
        boss_hp = max(0, boss_hp - p_damage)
        player_hp = max(0, player_hp - b_damage)
        if p_damage >= b_damage * 1.25:
            phrase = "抢到先机"
        elif b_damage >= p_damage * 1.25:
            phrase = "被首领压回半步"
        else:
            phrase = "与首领硬撼一记"
        timeline.append(
            f"第{seconds}息：{player_name}催动【{p_skill}】，{boss_name}以【{b_skill}】反扑，{phrase}；首领受创{p_damage}，宿主受创{b_damage}，血量 {player_hp}/{left.get('max_hp', 1)} vs {boss_hp}/{right.get('max_hp', 1)}。"
        )
        if player_hp <= 0 or boss_hp <= 0:
            break
    winner_name = str(result.get("winner_name") or "胜者")
    if result.get("ended_early"):
        timeline.append(f"终局：{winner_name}提前分出生死，剩余{int(result.get('remaining_seconds', 0))}息。")
    else:
        timeline.append(f"终局：一炷香斗到最后，{winner_name}凭剩余血量压过对手。")
    for log in list(left.get("logs") or [])[:2]:
        timeline.append(f"余波：{player_name}曾{log}")
    for log in list(right.get("logs") or [])[:2]:
        timeline.append(f"妖术：{boss_name}曾{log}")
    return timeline


def record_signature_for_boss(fighter: dict[str, Any]) -> str:
    return f"{fighter.get('user_id')}:{fighter.get('nickname')}:{fighter.get('power')}"


def simulate_mystic_boss_duel(record: UserRecord, realm: dict[str, Any]) -> tuple[dict[str, Any], UserRecord]:
    boss = boss_record_for_realm(realm, record)
    player_name = str(getattr(record, "combat_nickname", "") or "宿主")
    boss_name = f"{realm.get('boss_realm', '未知')}·{realm.get('boss_name', '秘境首领')}"
    result = simulate_normal_duel(
        record,
        boss,
        player_name,
        boss_name,
        player_boss_auto_actions(record),
        boss_combat_actions(realm, boss),
        duration_seconds=60,
    )
    result["title"] = "秘境首领生死斗战报"
    result["summary"] = "秘境首领生死斗：" + str(result.get("summary") or "胜负已分。")
    result["boss_intro"] = str(boss_archetype_config(realm).get("intro") or "首领妖气翻涌。")
    result["mystic_boss"] = True
    result["life_and_death"] = True
    result["footer"] = "秘境首领为生死斗法：胜利折算10次探索奖励；失败会反噬禁修，并随机折损100-500点修为，修为跌破本境会跌落境界。"
    result["timeline"] = build_mystic_boss_duel_timeline(result, realm, boss)
    return result, boss

def boss_element(realm: dict[str, Any]) -> str:
    value = str(realm.get("boss_element") or "").strip()
    if value in BASE_FIVE_ELEMENTS:
        return value
    value = random.choice(BASE_FIVE_ELEMENTS)
    realm["boss_element"] = value
    return value


def boss_demon_core_reward(record: UserRecord, realm: dict[str, Any]) -> dict[str, Any]:
    attr = boss_element(realm)
    boss_realm = realm_short_name(str(realm.get("boss_realm", REALMS[min(len(REALMS) - 1, record.realm_index)])))
    boss_name = str(realm.get("boss_name") or "妖兽")
    tier = mystic_reward_tier(record, realm)
    grade = weighted_choice([("极品", 1), ("上品", 2), ("中品", 4), ("下品", 3)])
    return normalize_reward(
        {
            "tier": tier,
            "grade": grade,
            "category": "灵材",
            "name": f"{attr}系{boss_realm}{boss_name}妖丹",
            "description": f"{attr}行妖力凝成的首领妖丹，可作丹灵根补全五行，也可炼化为修为。",
            "required_attribute": attr,
            "element": attr,
            "beast_realm": boss_realm,
            "source": f"秘境首领：{boss_realm}·{boss_name}",
        },
        record,
    )


def draw_mystic_boss_rewards(record: UserRecord, realm: dict[str, Any]) -> list[dict[str, Any]]:
    rewards: list[dict[str, Any]] = []
    options = list(realm.get("options", [])) or roll_mystic_options(str(realm.get("type")))
    normal_options = [item for item in options if not (isinstance(item, dict) and item.get("boss"))]
    for index in range(MYSTIC_REALM_MAX_STEPS):
        event = dict(random.choice(normal_options)) if normal_options else {}
        category, reward = draw_mystic_event_reward(record, realm, event)
        if category == "仙缘":
            exp = tier_exp(INSTANT_EXP_BASE, str(reward.get("tier")), str(reward.get("grade")))
            applied_result = apply_exp(record, exp) if not is_cultivation_locked(record) else ExpApplyResult()
            applied, leveled = applied_result
            reward["used"] = True
            reward["exp_gain"] = applied
            reward["leveled_realms"] = leveled
            if applied < exp:
                reward["blocked"] = True
        else:
            append_reward(record, reward)
        rewards.append(reward)
    core = boss_demon_core_reward(record, realm)
    append_reward(record, core)
    rewards.append(core)
    return rewards


def today_key(today: Optional[Any] = None) -> str:
    if today is None:
        return date.today().isoformat()
    if isinstance(today, datetime):
        return today.date().isoformat()
    if isinstance(today, date):
        return today.isoformat()
    parsed = parse_lock_until(str(today))
    if parsed is not None:
        return parsed.date().isoformat()
    return str(today)[:10]



def mystic_boss_week_key(today: Optional[Any] = None) -> str:
    if isinstance(today, datetime):
        day = today.date()
    elif isinstance(today, date):
        day = today
    else:
        parsed = parse_lock_until(str(today)) if today is not None else None
        day = parsed or date.today()
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def normalize_mystic_boss_attempts(record: UserRecord, today: Optional[Any] = None) -> None:
    day = today_key(today)
    if record.mystic_boss_daily_date != day:
        record.mystic_boss_daily_date = day
        record.mystic_boss_daily_attempts = 0
        record.mystic_boss_daily_bonus = 0
    week = mystic_boss_week_key(today)
    if record.mystic_boss_week_key != week:
        record.mystic_boss_week_key = week
        record.mystic_boss_week_attempts = 0
        record.mystic_boss_week_claimed = []
    record.mystic_boss_week_claimed = sorted(
        {int(item) for item in (record.mystic_boss_week_claimed or []) if int(item) in MYSTIC_BOSS_WEEKLY_BONUS_THRESHOLDS}
    )
    record.mystic_boss_daily_attempts = max(0, int(record.mystic_boss_daily_attempts or 0))
    record.mystic_boss_daily_bonus = max(0, int(record.mystic_boss_daily_bonus or 0))
    record.mystic_boss_week_attempts = max(0, int(record.mystic_boss_week_attempts or 0))


def mystic_boss_daily_limit(record: UserRecord, today: Optional[Any] = None) -> int:
    normalize_mystic_boss_attempts(record, today)
    return MYSTIC_BOSS_DAILY_BASE_ATTEMPTS + int(record.mystic_boss_daily_bonus or 0)


def mystic_boss_remaining_attempts(record: UserRecord, today: Optional[Any] = None) -> int:
    limit = mystic_boss_daily_limit(record, today)
    return max(0, limit - int(record.mystic_boss_daily_attempts or 0))


def mystic_boss_attempt_status_text(record: UserRecord, today: Optional[Any] = None) -> str:
    limit = mystic_boss_daily_limit(record, today)
    remaining = max(0, limit - int(record.mystic_boss_daily_attempts or 0))
    claimed = "、".join(str(item) for item in record.mystic_boss_week_claimed or []) or "暂无"
    return (
        f"首领斗法次数：今日剩余 {remaining}/{limit}；"
        f"本周已进行 {int(record.mystic_boss_week_attempts or 0)}/7 次；"
        f"周补给节点 {claimed}。"
    )


def consume_mystic_boss_attempt(record: UserRecord, today: Optional[Any] = None) -> tuple[bool, str, list[int]]:
    limit = mystic_boss_daily_limit(record, today)
    if int(record.mystic_boss_daily_attempts or 0) >= limit:
        return (
            False,
            f"今日Boss挑战次数已用尽（{limit}/{limit}）。所有秘境首领共享次数；本周进行3/5/7次首领斗法时，会分别给当天补充1次挑战机会。",
            [],
        )
    record.mystic_boss_daily_attempts = int(record.mystic_boss_daily_attempts or 0) + 1
    record.mystic_boss_week_attempts = int(record.mystic_boss_week_attempts or 0) + 1
    claimed = set(record.mystic_boss_week_claimed or [])
    grants: list[int] = []
    for threshold in MYSTIC_BOSS_WEEKLY_BONUS_THRESHOLDS:
        if record.mystic_boss_week_attempts >= threshold and threshold not in claimed:
            claimed.add(threshold)
            grants.append(threshold)
            record.mystic_boss_daily_bonus = int(record.mystic_boss_daily_bonus or 0) + 1
    record.mystic_boss_week_claimed = sorted(claimed)
    new_limit = mystic_boss_daily_limit(record, today)
    remaining = max(0, new_limit - int(record.mystic_boss_daily_attempts or 0))
    text = f"今日Boss斗法次数已消耗 {record.mystic_boss_daily_attempts}/{new_limit}，剩余 {remaining} 次；本周已进行 {record.mystic_boss_week_attempts}/7 次。"
    if grants:
        text += "\n周任务达成：" + "、".join(f"第{item}次" for item in grants) + "，已为今日补充对应Boss挑战次数。"
    return True, text, grants


def apply_mystic_boss_defeat_penalty(record: UserRecord) -> tuple[int, int, str]:
    if record.root is None:
        return 0, 0, "尚未凝成修为，反噬只在经脉中留下刺痛。"
    loss = random.randint(100, 500)
    old_realm = record.realm
    old_index = record.realm_index
    remaining = loss
    if remaining <= record.realm_exp:
        record.realm_exp = max(0, int(record.realm_exp) - remaining)
    else:
        remaining -= max(0, int(record.realm_exp))
        while remaining > 0 and record.realm_index > 0:
            record.realm_index -= 1
            required = realm_progress_required(record.root, record.realm_index)
            if remaining >= required:
                remaining -= required
                record.realm_exp = 0
            else:
                record.realm_exp = max(0, required - remaining)
                remaining = 0
        if record.realm_index <= 0 and remaining > 0:
            record.realm_index = 0
            record.realm_exp = 0
    record.total_exp = max(0, cumulative_realm_exp(record.root, record.realm_index) + record.realm_exp)
    if record.realm_marks:
        record.realm_marks = {key: value for key, value in record.realm_marks.items() if int(key) <= record.realm_index}
    if record.realm_index < 2:
        record.foundation_type = None
    reset_bottleneck_state(record)
    dropped = max(0, old_index - record.realm_index)
    if dropped:
        return loss, dropped, f"生死斗反噬折损修为{loss}点，境界从{old_realm}跌落至{record.realm}。"
    return loss, 0, f"生死斗反噬折损修为{loss}点，当前进度降至 {record.realm_exp}/{record.progress_required}。"


def mystic_boss_limit_key(realm: dict[str, Any]) -> str:
    realm_type = str(realm.get("type") or "未知秘境")
    title = str(realm.get("title") or mystic_realm_title(realm) or realm_type)
    return f"{realm_type}:{title}"


def mystic_boss_success_map(record: UserRecord) -> dict[str, list[str]]:
    cleaned: dict[str, list[str]] = {}
    raw = record.mystic_boss_successes or {}
    for day, keys in raw.items():
        if isinstance(keys, list):
            cleaned[str(day)] = [str(key) for key in keys if key]
    record.mystic_boss_successes = cleaned
    return cleaned


def has_mystic_boss_success_today(record: UserRecord, realm: dict[str, Any], today: Optional[Any] = None) -> bool:
    day = today_key(today)
    return mystic_boss_limit_key(realm) in set(mystic_boss_success_map(record).get(day, []))


def mark_mystic_boss_success(record: UserRecord, realm: dict[str, Any], today: Optional[Any] = None) -> None:
    day = today_key(today)
    successes = mystic_boss_success_map(record)
    # Keep only today and yesterday; older locks are useless noise.
    keep_days = {day}
    parsed = parse_lock_until(day)
    if isinstance(parsed, datetime):
        keep_days.add((parsed.date() - timedelta(days=1)).isoformat())
    elif isinstance(parsed, date):
        keep_days.add((parsed - timedelta(days=1)).isoformat())
    for old_day in list(successes):
        if old_day not in keep_days:
            successes.pop(old_day, None)
    key = mystic_boss_limit_key(realm)
    day_keys = successes.setdefault(day, [])
    if key not in day_keys:
        day_keys.append(key)
    record.mystic_boss_successes = successes


def mystic_boss_success_chance(record: UserRecord, realm: dict[str, Any]) -> float:
    base = mystic_success_chance(record, realm) - 0.18
    recommended = int(realm.get("recommended_index", record.realm_index or 1))
    if record.realm_index >= recommended:
        base += 0.1
    return max(0.12, min(0.72, base))


def handle_mystic_boss_challenge(record: UserRecord, realm: dict[str, Any], today: Optional[date] = None) -> tuple[bool, str]:
    realm_type = str(realm.get("type"))
    boss_name = str(realm.get("boss_name") or "无名妖兽")
    boss_realm = str(realm.get("boss_realm") or "未知")
    realm_title = mystic_realm_title(realm)
    if has_mystic_boss_success_today(record, realm, today):
        return False, f"今日已成功挑战过【{realm_title}】首领，不能再次通过同一秘境首领折算10次探索奖励。可继续普通探索，或明日再来。\n{mystic_boss_attempt_status_text(record, today)}"
    consumed, attempt_text, grants = consume_mystic_boss_attempt(record, today)
    if not consumed:
        return False, attempt_text
    duel_result, boss = simulate_mystic_boss_duel(record, realm)
    record.last_mystic_boss_duel = duel_result
    player_win = str(duel_result.get("winner_id")) == str(record.user_id)
    left = duel_result.get("left", {})
    right = duel_result.get("right", {})
    lines = [
        f"你选择：挑战{boss_realm}·{boss_name}",
        str(duel_result.get("boss_intro") or "首领妖气压下，斗法已起。"),
        attempt_text,
        "生死斗法战报已尝试私聊发送，内含玩家与Boss的完整斗法过程。",
        f"宿主血量：{int(left.get('hp', 0))}/{int(left.get('max_hp', 1))}；首领血量：{int(right.get('hp', 0))}/{int(right.get('max_hp', 1))}。",
        "首领装备：" + "、".join(reward_display_name(item) for item in (boss.equipped_artifacts or {}).values()),
        "首领阵盘：" + reward_display_name(boss.equipped_array),
        "首领符箓：" + reward_display_name(boss.equipped_talisman),
        "首领战技：" + "、".join(available_battle_techniques(boss)[:5]),
        "首领神通：" + "、".join(normalize_special_abilities(boss.special_abilities)[:5]),
    ]
    if grants:
        lines.append("本周Boss斗法进度触发补给，当天可继续追击更多首领。")
    if not player_win:
        loss, dropped, penalty_text = apply_mystic_boss_defeat_penalty(record)
        duel_result["penalty_text"] = penalty_text
        duel_result["summary"] = f"秘境首领生死斗：{duel_result.get('winner_name', '首领')}胜出，宿主反噬折损修为{loss}点。"
        duel_result.setdefault("timeline", []).append("反噬：" + penalty_text)
        lock_text = lock_cultivation(record, today, minutes=5)
        record.last_failed_mystic_realm = dict(realm)
        record.mystic_realm = None
        lines.append(mystic_bad_ending_text(realm_type))
        lines.append(f"斗法失败：进入5分钟反噬期，{lock_text}。{penalty_text}")
        if dropped:
            lines.append("修为跌破本境根基，境界已发生跌落；可重新修炼并尝试改善突破品相。")
        lines.append(mystic_boss_attempt_status_text(record, today))
        return True, "\n".join(lines)
    rewards = draw_mystic_boss_rewards(record, realm)
    mark_mystic_boss_success(record, realm, today)
    layer_up = increase_method_proficiency(record, 28)
    increase_array_proficiency(record, 18)
    record.mystic_realm = None
    reward_text = "、".join(reward_display_name(reward) for reward in rewards[:11])
    lines.append("你以斗法斩开首领妖云，硬生生打穿此处秘境。")
    lines.append(f"获得10次探索折算奖励与首领妖丹：{reward_text}")
    lines.append(f"功法熟练度+28{f'，功法连升 {layer_up} 层' if layer_up else ''}；阵法熟练度+18。")
    lines.append(f"今日【{realm_title}】首领挑战成功次数已用尽，重复进入同一秘境不会再触发首领折算奖励。")
    lines.append(mystic_boss_attempt_status_text(record, today))
    return True, "\n".join(lines)

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
    event = dict(choice) if isinstance(choice, dict) else {"text": str(choice)}
    choice_text = mystic_option_display(event)
    realm_type = str(realm.get("type"))
    if event.get("boss"):
        return handle_mystic_boss_challenge(record, realm, today)
    realm["step"] = int(realm.get("step", 0)) + 1
    realm["steps_left"] = max(0, int(realm.get("steps_left", MYSTIC_REALM_MAX_STEPS)) - 1)
    if int(event.get("fishing_chance", 0) or 0) > 0:
        gained = max(1, int(event.get("fishing_chance", 1) or 1))
        record.fishing_chances += gained
        record.pending_fishing = record.fishing_chances
        lines = [f"你选择：{choice_text}", f"{event.get('success') or '灵河印记落入掌心。'}垂钓次数 +{gained}，当前共有 {record.fishing_chances} 次。"]
        if int(realm.get("steps_left", 0)) <= 0:
            record.mystic_realm = None
            lines.append("十次探索已尽，秘境门户在身后缓缓闭合。")
            return True, "\n".join(lines)
        realm["options"] = roll_mystic_options(realm_type)
        if not is_high_risk_mystic_type(realm_type):
            realm["options"].append({"text": f"挑战秘境首领：{realm.get('boss_realm')}·{realm.get('boss_name')}", "boss": True, "category": "灵材", "reward_hint": "首领妖丹"})
        assign_mystic_bad_option(realm)
        record.mystic_realm = realm
        lines.append("")
        lines.append(mystic_realm_options_text(record))
        return True, "\n".join(lines)
    success_chance = mystic_success_chance(record, realm)
    bad_rate = 0.08 + int(realm.get("danger", 20)) / 500
    if realm.get("false_lure") and not record.evil_cultivator:
        bad_rate += 0.12
    if event.get("forced_bad"):
        bad_rate = max(bad_rate, 0.92)
    elif int(realm.get("bad_option_index", 0)) == option_index:
        bad_rate = max(bad_rate, 0.88)
    elif realm.get("insight"):
        bad_rate = max(0.02, bad_rate * 0.35)
    if record.equipped_puppet:
        bad_rate = max(0.03, bad_rate - 0.04)
    roll = random.random()
    lines = [f"你选择：{choice_text}"]
    if realm.get("false_lure") and record.evil_cultivator:
        lines.append("邪修气息识破了洞府中的同源陷阱，你没有因此直接坠入杀局。")
    if roll < bad_rate:
        lock_text = lock_cultivation(record, today, minutes=5)
        record.last_failed_mystic_realm = dict(realm)
        record.mystic_realm = None
        lines.append(mystic_bad_ending_text(realm_type))
        lines.append(f"坏结局：进入5分钟反噬惩罚期，{lock_text}，期间无法通过任何手段提升修为。")
        return True, "\n".join(lines)
    if roll < bad_rate + success_chance:
        category, reward = draw_mystic_event_reward(record, realm, event)
        success_text = str(event.get("success") or mystic_success_text(realm_type))
        if category == "仙缘":
            exp = tier_exp(INSTANT_EXP_BASE, str(reward.get("tier")), str(reward.get("grade")))
            applied_result = apply_exp(record, exp, today) if not is_cultivation_locked(record, today) else ExpApplyResult()
            applied, leveled = applied_result
            reward["used"] = True
            reward["exp_gain"] = applied
            if applied < exp:
                reward["blocked"] = True
            extra = f"，连破 {leveled} 境" if leveled else ""
            if applied:
                lines.append(f"{success_text}触发 {reward_display_name(reward)}，修为 +{applied}{extra}。")
            else:
                lines.append(f"{success_text}触发 {reward_display_name(reward)}，但当前瓶颈或禁修阻住了灵机。")
        else:
            append_reward(record, reward)
            reward_note = str(reward.get("growth_deduction_text") or f"获得 {reward_display_name(reward)}")
            lines.append(f"{success_text}{reward_note}。")
        if category not in {"仙缘", "功法", "灵器", "阵盘", "傀儡", "灵植", SPECIAL_ABILITY_CATEGORY} and not is_cultivation_locked(record, today):
            exp = max(1, tier_exp(CONSUMABLE_EXP_BASE, str(reward.get("tier")), str(reward.get("grade"))) // 4)
            applied, _ = apply_exp(record, exp)
            if applied:
                lines.append(f"顺势炼化一缕灵机，修为 +{applied}。")
    else:
        lines.append(mystic_empty_text(realm_type))
    if int(realm.get("steps_left", 0)) <= 0:
        record.mystic_realm = None
        lines.append("十次探索已尽，秘境门户在身后缓缓闭合。")
        return True, "\n".join(lines)
    realm["options"] = roll_mystic_options(realm_type)
    if not is_high_risk_mystic_type(realm_type):
        realm["options"].append({"text": f"挑战秘境首领：{realm.get('boss_realm')}·{realm.get('boss_name')}", "boss": True, "category": "灵材", "reward_hint": "首领妖丹"})
    assign_mystic_bad_option(realm)
    record.mystic_realm = realm
    lines.append("")
    lines.append(mystic_realm_options_text(record))
    return True, "\n".join(lines)


def artifact_is_sword(artifact: Optional[dict[str, Any]]) -> bool:
    name = reward_name(artifact)
    return any(token in name for token in ARTIFACT_SWORD_NAME_TOKENS)


def route_power_multiplier(record: UserRecord) -> float:
    effective_artifacts = []
    seen_names: set[str] = set()
    for slot, artifact in artifact_slots(record).items():
        if not artifact_slot_allowed(slot, artifact):
            continue
        if artifact_power(artifact, record) <= 0:
            continue
        name = reward_name(artifact)
        if name in seen_names:
            continue
        seen_names.add(name)
        effective_artifacts.append(artifact)
    has_artifact = bool(effective_artifacts)
    has_sword = any(artifact_is_sword(item) for item in effective_artifacts)
    if record.cultivation_route == "剑修" and has_sword:
        return 1.3
    if record.cultivation_route == "术修" and has_artifact and not has_sword:
        return 1.3
    return 1.0


def battle_power(record: UserRecord) -> int:
    realm_power = (record.realm_index + 1) * 900 + record.realm_exp * 3
    exp_power = record.total_exp * 2 + record.pending_exp
    sign_power = record.sign_count * 20
    root_power = 120
    if record.root:
        root_power += 320 + record.root.tier_rank * 280 + record.root.grade_rank * 120
        if record.root.tier == "变异灵根":
            root_power += 520
    root_power += len(record.extra_roots or []) * 160
    root_power += max_root_purity(record) * 6
    root_power += acquired_root_power_total(record)
    foundation_bonus = realm_quality_power(record)
    equipment_power = (
        equipped_artifact_power(record)
        + method_power(record.equipped_method, record)
        + array_power(record.equipped_array, record)
        + puppet_power(record.equipped_puppet, record)
        + talisman_power(record.equipped_talisman, record)
        + int(artifact_power(record.life_artifact, record) * 0.38)
        + immortal_seed_power(record.equipped_immortal_seed, record)
    )
    special_ability_power = special_ability_power_total(record)
    power = realm_power + exp_power + sign_power + root_power + foundation_bonus + equipment_power + special_ability_power
    power = int(power * route_power_multiplier(record))
    if is_breakthrough_bottleneck(record):
        power = int(power * 1.1)
    return max(1, power)

def battle_summary(record: UserRecord) -> dict[str, Any]:
    equipment_power = (
        equipped_artifact_power(record)
        + method_power(record.equipped_method, record)
        + array_power(record.equipped_array, record)
        + puppet_power(record.equipped_puppet, record)
        + talisman_power(record.equipped_talisman, record)
        + int(artifact_power(record.life_artifact, record) * 0.38)
        + immortal_seed_power(record.equipped_immortal_seed, record)
    )
    return {
        "power": battle_power(record),
        "realm": record.realm if record.root else "\u672a\u5165\u95e8",
        "total_exp": record.total_exp,
        "pending_exp": record.pending_exp,
        "artifact": equipped_artifact_name(record),
        "artifact_slots": equipped_artifact_summary(record),
        "talisman": equipped_talisman_name(record),
        "method": equipped_method_name(record),
        "array": equipped_array_name(record),
        "puppet": equipped_puppet_name(record),
        "plant": planted_spirit_plant_name(record),
        "spirit_stones": record.spirit_stones,
        "spirit_liquid": record.spirit_liquid,
        "bottleneck_days": record.bottleneck_days,
        "array_multiplier": array_multiplier(record),
        "artifact_power": equipped_artifact_power(record),
        "talisman_power": talisman_power(record.equipped_talisman, record),
        "puppet_power": puppet_power(record.equipped_puppet, record),
        "equipment_power": equipment_power,
        "cultivation_lock": cultivation_lock_text(record),
        "mystic_realm": mystic_realm_title(record.mystic_realm) if record.mystic_realm else "无",
        "foundation_type": record.foundation_type or "",
        "realm_quality": realm_quality_text(record),
        "mana": combat_max_mana(record),
        "is_bottleneck": is_breakthrough_bottleneck(record),
        "breakthrough_required": breakthrough_required_text(record),
        "route": record.route_summary,
        "identity": record.identity_summary,
        "hehuan_remaining": hehuan_remaining_text(record),
        "tianji_status": tianji_status_text(record),
        "spirit_stones_text": spirit_stone_text(record.spirit_stones),
        "special_abilities": normalize_special_abilities(record.special_abilities),
        "special_ability_materials": len(available_special_ability_items(record)),
        "special_ability_power": special_ability_power_total(record),
        "life_artifact": reward_display_name(record.life_artifact) if record.life_artifact else "未祭炼本命灵器",
        "immortal_seed": equipped_immortal_seed_name(record),
        "immortal_seed_power": immortal_seed_power(record.equipped_immortal_seed, record),
        "mana_label": "仙元力" if record.realm_index >= true_immortal_realm_index() else "灵力",
        "immortal_conversion": record.immortal_conversion_days,
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
        exp = 36
    elif rank == 2:
        exp = 28
    elif rank == 3:
        exp = 22
    elif 4 <= rank <= 5:
        exp = 16
    elif 6 <= rank <= 10:
        exp = 10
    else:
        exp = 0
    fishing_rewards = {1: 10, 2: 8, 3: 6, 4: 4, 5: 2}
    return exp, fishing_rewards.get(rank, 0)


def apply_rank_reward(record: UserRecord, rank: int) -> RankReward:
    exp, fishing_chances = rank_reward_for(rank)
    reward = RankReward(rank=rank, exp=exp, fishing_chances=fishing_chances)
    if exp <= 0 and fishing_chances <= 0:
        return reward

    if record.root is None or is_cultivation_locked(record):
        record.pending_exp += exp
        reward.pending = True
    else:
        rank_result = apply_exp(record, exp)
        applied_exp, reward.leveled_realms = rank_result
        reward.exp = applied_exp
    record.fishing_chances += fishing_chances
    return reward
