from __future__ import annotations

import hashlib
import random
import re
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
    "特殊能力",
]
REWARD_MIN_COUNTS = {"仙缘": 5, "阵盘": 3, "灵器": 7, "功法": 7, "特殊能力": 5}
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
    "特殊能力": 0.42,
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
    "特殊能力": "{name}中藏着一段失落感悟，参悟后有机会领悟特殊能力。",
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


EXTRA_ARTIFACT_NAMES_BY_TIER_ATTR = {
    "天阶": {
        "金": ["斩道庚金剑", "白帝镇天戈", "星河断岳刃"],
        "木": ["扶桑万灵弓", "青莲开天尺", "建木归墟杖"],
        "水": ["归墟沧海珠", "玄水量天瓶", "天河镇魔印"],
        "火": ["朱雀焚世旗", "太阳炼神炉", "离火吞星钟"],
        "土": ["息壤万山玺", "玄黄镇界碑", "厚土载天鼎"],
        "雷": ["紫霄万劫剑", "九天雷祖锤", "劫海镇魂鼓"],
        "冰": ["太阴封界轮", "寒狱照神镜", "玄霜葬天枪"],
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
        "雷": ["奔雷啸月枪", "雷竹引劫剑", "震魂小鼓"],
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

EXTRA_METHOD_NAMES_BY_TIER_ATTR = {
    "天阶": {
        "金": ["不灭金身经", "斩道剑胎篇", "庚金开天录"],
        "木": ["青莲造化经", "万灵长生篇", "建木通天录"],
        "水": ["沧溟归墟经", "天河炼神篇", "玄水不灭诀"],
        "火": ["太阳真火录", "朱雀焚天经", "离火炼界篇"],
        "土": ["玄黄不动经", "息壤造山诀", "后土载道书"],
        "雷": ["九劫雷身经", "紫霄御劫篇", "万雷洗神诀"],
        "冰": ["太阴封神录", "玄冰寂灭经", "寒狱炼魂篇"],
    },
    "地阶": {
        "金": ["白虎庚金诀", "金阙炼剑章", "裂空剑元录"],
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
    tier: _equipment_names_for_tier(ARTIFACT_NAMES_BY_TIER_ATTR, EXTRA_ARTIFACT_NAMES_BY_TIER_ATTR, tier)
    for tier in ARTIFACT_NAMES_BY_TIER_ATTR
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
    '天阶': ['化凡意境', '破虚灵引', '合道残章', '大乘道果', '大罗天契', '混元道果', '鸿蒙紫气', '混元真印', '无极道种', '天道权柄', '大道本源', '永恒真名', '太乙道胎', '大罗道种', '混元真液', '无极真符', '合道天心', '万道源流', '开天道印', '彼岸真符', '不朽唯一印'],
    '地阶': ['化凡意境', '破虚灵引', '渡劫令', '仙门符诏', '金性道果', '斩尸灵宝', '道祖法旨', '超脱契机', '命河断契', '虚空灵髓', '法身合契符', '圆融道胎', '避劫雷木', '真仙接引符', '金仙法契', '清光道箓', '诸天印契', '万道归元符', '准圣道契', '天道圣契', '无量道章', '道源玄胎', '天命玉册', '大道真箓', '祖庭符诏', '彼岸舟影', '命河钥印', '因果斩线', '万劫真铭'],
    '玄阶': ['化凡意境', '合道残章', '太乙玄光', '星砂沙漏', '低语玉佩', '仙元道砂', '执念斩魂刃', '功德金莲'],
    '黄阶': ['化凡意境', '不熄小灯', '自热茶盏', '破境石', '醒神玉'],
    '凡品': ['化凡意境', '只响一次的铃铛', '没字的竹简', '旧木令', '无名石片'],
}
FISHING_REWARD_NAMES["灵材"] = {
    "天阶": ["混沌星砂", "太白仙金", "天髓玉露", "九转玄参", "悟道茶心", "太阳真火液", "太阴寒髓", "玄黄母气", "大道莲子", "劫雷神木"],
    "地阶": ["星陨玄铁", "玄冰玉髓", "紫府灵芝", "月华凝露", "地脉火芝", "龙血朱果", "天青灵藤", "地肺火液", "金髓玉砂", "养魂莲心"],
    "玄阶": ["赤霞铜精", "青藤灵骨", "金纹灵芝", "冰魄花蕊", "雷击灵木", "黑曜灵砂", "百年寒髓", "赤鳞妖血", "碧玉参须", "云母灵液"],
    "黄阶": ["百炼寒铁", "紫纹灵木", "凝露草", "火枣核", "土精砂", "血线草", "青灵花", "黄芽芝", "月露珠", "火鸦羽灰"],
    "凡品": ["发亮矿渣", "溪边圆石", "清心草叶", "灵麦芽", "苦参须", "山参碎须", "晨露草", "凡火炉灰", "青苔灵屑", "野兽精血"],
}



FISHING_REWARD_NAMES["特殊能力"] = {
    "天阶": ["九秘残页", "八禁感悟", "神禁烙印", "他化自在影", "因果断线真箓", "牧天九歌玉简", "天问一式法旨", "元婴天兆星痕"],
    "地阶": ["九秘残页", "八禁感悟", "神禁烙印", "至尊骨符文", "以身为种道痕", "十洞天神环碎光", "杀戮本源血符", "梦道轮回沙"],
    "玄阶": ["九秘残页", "八禁感悟", "神禁烙印", "道经轮海残章", "斗战圣法残卷", "鲲鹏极速羽痕", "古神一指骨纹", "神藏开阖残图"],
    "黄阶": ["九秘残页", "八禁感悟", "神禁烙印", "掌天瓶影拓片", "青帝莲相旧纹", "柳神法相枝影", "青元剑芒手札", "岁月意境残砂"],
    "凡品": ["九秘残页", "八禁感悟", "神禁烙印", "凡骨战意札", "问道旧简", "小神藏残图", "青元剑芒残页", "掌天瓶影碎片"],
}
ITEM_ATTRIBUTE_BY_NAME = {}
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
    4: {"items": ['化凡意境', '化神引', '斩尘化神丹', '问心丹'], "target": '化神期', "kind": 'insight'},
    5: {"items": ['破虚灵引', '破虚丹', '虚空灵髓'], "target": '炼虚期', "kind": 'insight'},
    6: {"items": ['合道残章', '合体丹', '法身合契符'], "target": '合体期', "kind": 'insight'},
    7: {"items": ['大乘道果', '合道紫金丹', '圆融道胎'], "target": '大乘期', "kind": 'insight'},
    8: {"items": ['渡劫令', '渡劫护命丹', '避劫雷木'], "target": '渡劫期', "kind": 'insight'},
    9: {"items": ['仙门符诏', '真仙接引符', '仙元道砂'], "target": '真仙境', "kind": 'insight'},
    10: {"items": ['金性道果', '不朽金丹', '金仙法契'], "target": '金仙境', "kind": 'insight'},
    11: {"items": ['太乙玄光', '太乙道胎', '清光道箓'], "target": '太乙境', "kind": 'insight'},
    12: {"items": ['大罗天契', '大罗道种', '诸天印契'], "target": '大罗境', "kind": 'insight'},
    13: {"items": ['混元道果', '混元真液', '万道归元符'], "target": '混元金仙境', "kind": 'insight'},
    14: {"items": ['斩尸灵宝', '执念斩魂刃', '准圣道契'], "target": '准圣境', "kind": 'insight'},
    15: {"items": ['鸿蒙紫气', '天道圣契', '功德金莲'], "target": '圣人境', "kind": 'insight'},
    16: {"items": ['混元真印', '混元圣胎', '无量道章'], "target": '混元大罗金仙境', "kind": 'insight'},
    17: {"items": ['无极道种', '无极真符', '道源玄胎'], "target": '混元无极大罗金仙境', "kind": 'insight'},
    18: {"items": ['天道权柄', '合道天心', '天命玉册'], "target": '天道境', "kind": 'insight'},
    19: {"items": ['大道本源', '万道源流', '大道真箓'], "target": '大道境', "kind": 'insight'},
    20: {"items": ['道祖法旨', '开天道印', '祖庭符诏'], "target": '道祖境', "kind": 'insight'},
    21: {"items": ['超脱契机', '彼岸舟影', '命河钥印'], "target": '半步超脱', "kind": 'insight'},
    22: {"items": ['命河断契', '因果斩线', '彼岸真符'], "target": '超脱境', "kind": 'insight'},
    23: {"items": ['永恒真名', '不朽唯一印', '万劫真铭'], "target": '永恒境', "kind": 'insight'},
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

INSTANT_EXP_BASE = {"凡品": 26, "黄阶": 52, "玄阶": 96, "地阶": 168, "天阶": 280}
CONSUMABLE_EXP_BASE = {"凡品": 18, "黄阶": 36, "玄阶": 72, "地阶": 128, "天阶": 220}
GRADE_EXP_RATIO = {"下品": 1.0, "中品": 1.18, "上品": 1.38, "极品": 1.72}
METHOD_SIGN_RATE = {"凡品": 0.08, "黄阶": 0.12, "玄阶": 0.18, "地阶": 0.26, "天阶": 0.38}
METHOD_CHAT_BASE = {"凡品": 0.35, "黄阶": 0.55, "玄阶": 0.85, "地阶": 1.25, "天阶": 1.8}
METHOD_KIND_NAMES = ("修炼类", "锻体类", "神魂类", "战技类")
COMBAT_RACES = (
    ("人族-东荒", 18),
    ("人族-南域", 16),
    ("人族-西域", 12),
    ("人族-北域", 12),
    ("人族-中州", 14),
    ("妖族-金翅大鹏", 4),
    ("妖族-青莲", 4),
    ("妖族-九尾天狐", 4),
    ("妖族-太古魔猿", 3),
    ("神族", 4),
    ("仙族", 3),
)
COMBAT_PHYSIQUES = (
    ("凡体", 30),
    ("石猴废脉", 12),
    ("荒古圣体", 7),
    ("先天道胎", 7),
    ("太阴之体", 6),
    ("太阳神体", 6),
    ("青莲道体", 6),
    ("金翅神脉", 5),
    ("以身为种", 4),
    ("混沌神魔体", 3),
)
SPECIAL_ABILITY_POOL = (
    "八禁",
    "神禁领域",
    "九秘-临字秘",
    "九秘-兵字秘",
    "九秘-斗字秘",
    "九秘-者字秘",
    "九秘-皆字秘",
    "九秘-数字秘",
    "九秘-组字秘",
    "九秘-前字秘",
    "九秘-行字秘",
    "掌天瓶影",
    "青元剑芒",
    "元婴天兆",
    "道经轮海",
    "斗战圣法",
    "荒古圣血",
    "青帝莲相",
    "至尊骨符文",
    "以身为种",
    "他化自在影",
    "十洞天神环",
    "鲲鹏极速",
    "柳神法相",
    "古神一指",
    "岁月意境",
    "杀戮本源",
    "梦道轮回",
    "因果断线",
    "牧天九歌",
    "天问一式",
    "神藏开阖",
)

NINE_SECRET_ABILITIES = tuple(ability for ability in SPECIAL_ABILITY_POOL if ability.startswith("九秘"))

SPECIAL_ABILITY_INFOS = {
    "八禁": {"material": "八禁感悟", "source": "战境极限", "effect": "斗法时战意暴涨，伤害和防御同步提升。", "aliases": ["八禁", "开启八禁"], "combat": (0.12, 0.04, 0)},
    "神禁领域": {"material": "神禁烙印", "source": "禁域升华", "effect": "短时间踏入极限状态，伤害、防御和速度一并提升。", "aliases": ["神禁", "神禁领域"], "combat": (0.18, 0.08, 8)},
    "九秘-临字秘": {"material": "九秘残页", "source": "九秘传承", "effect": "稳定神魂与气机，拉高攻守下限。", "aliases": ["临字秘", "九秘"], "combat": (0.08, 0.08, 2)},
    "九秘-兵字秘": {"material": "九秘残页", "source": "九秘传承", "effect": "牵引灵器与法宝共鸣，提升攻伐威势。", "aliases": ["兵字秘", "九秘"], "combat": (0.10, 0.05, 0)},
    "九秘-斗字秘": {"material": "九秘残页", "source": "九秘传承", "effect": "演化斗战法则，以战养战。", "aliases": ["斗字秘", "九秘"], "combat": (0.13, 0.03, 0)},
    "九秘-者字秘": {"material": "九秘残页", "source": "九秘传承", "effect": "激发生机与恢复底蕴，以守为攻。", "aliases": ["者字秘", "九秘"], "combat": (0.00, 0.12, 0)},
    "九秘-皆字秘": {"material": "九秘残页", "source": "九秘传承", "effect": "短暂放大自身战力，追求瞬间爆发。", "aliases": ["皆字秘", "九秘"], "combat": (0.16, 0.00, 0)},
    "九秘-数字秘": {"material": "九秘残页", "source": "九秘传承", "effect": "推演战局缝隙，提升闪转和护身。", "aliases": ["数字秘", "九秘"], "combat": (0.04, 0.05, 6)},
    "九秘-组字秘": {"material": "九秘残页", "source": "九秘传承", "effect": "结成战阵法纹，增强防御和控场。", "aliases": ["组字秘", "九秘"], "combat": (0.03, 0.09, 3)},
    "九秘-前字秘": {"material": "九秘残页", "source": "九秘传承", "effect": "增强神识先觉，先一步看破攻势。", "aliases": ["前字秘", "九秘"], "combat": (0.06, 0.04, 8)},
    "九秘-行字秘": {"material": "九秘残页", "source": "九秘传承", "effect": "身法如流光，追求极速和脱身。", "aliases": ["行字秘", "九秘"], "combat": (0.00, 0.04, 12)},
    "掌天瓶影": {"material": "掌天瓶影拓片", "source": "岁月灵液之道", "effect": "凝聚一缕绿光灵机，斗法时补足后劲。", "aliases": ["掌天", "小瓶", "瓶影"], "combat": (0.08, 0.07, 0)},
    "青元剑芒": {"material": "青元剑芒手札", "source": "剑修凝元之道", "effect": "剑芒凝而不散，提升剑类攻伐爆发。", "aliases": ["青元", "剑芒"], "combat": (0.12, 0.02, 0)},
    "元婴天兆": {"material": "元婴天兆星痕", "source": "破婴天象感悟", "effect": "引来天兆压场，提升法力和护体。", "aliases": ["元婴天兆", "天兆"], "combat": (0.09, 0.07, 2)},
    "道经轮海": {"material": "道经轮海残章", "source": "轮海秘境观想", "effect": "气血如海，攻守节奏更稳。", "aliases": ["道经", "轮海"], "combat": (0.07, 0.08, 1)},
    "斗战圣法": {"material": "斗战圣法残卷", "source": "斗战演法", "effect": "临阵演化攻伐，让战技更具压迫。", "aliases": ["斗战", "斗战圣法"], "combat": (0.15, 0.02, 0)},
    "荒古圣血": {"material": "荒古圣血金纹", "source": "圣体肉身之道", "effect": "气血若金海，增强近身压制与抗性。", "aliases": ["圣血", "圣体", "金血"], "combat": (0.10, 0.09, 0)},
    "青帝莲相": {"material": "青帝莲相旧纹", "source": "青莲生灭之道", "effect": "青莲法相开合，兼具生机与杀伐。", "aliases": ["青帝", "青莲", "莲相"], "combat": (0.09, 0.08, 0)},
    "至尊骨符文": {"material": "至尊骨符文", "source": "骨文天赋", "effect": "骨文发光，爆发强力神通。", "aliases": ["至尊骨", "骨符"], "combat": (0.14, 0.04, 0)},
    "以身为种": {"material": "以身为种道痕", "source": "身种大道", "effect": "以自身为天地，强化全面战力。", "aliases": ["以身为种", "身种"], "combat": (0.11, 0.08, 2)},
    "他化自在影": {"material": "他化自在影", "source": "自在化身之道", "effect": "化出一道战影，形成瞬间合击。", "aliases": ["他化自在", "自在影"], "combat": (0.18, 0.03, 4)},
    "十洞天神环": {"material": "十洞天神环碎光", "source": "洞天开辟之道", "effect": "洞天光环连成一体，攻守同时拔高。", "aliases": ["十洞天", "洞天", "神环"], "combat": (0.10, 0.10, 1)},
    "鲲鹏极速": {"material": "鲲鹏极速羽痕", "source": "鲲鹏身法", "effect": "极速破空，让先手和追击更稳。", "aliases": ["鲲鹏", "极速"], "combat": (0.06, 0.02, 16)},
    "柳神法相": {"material": "柳神法相枝影", "source": "生灭法相", "effect": "柳枝化成护身法相，可守可攻。", "aliases": ["柳神", "柳枝", "法相"], "combat": (0.08, 0.11, 0)},
    "古神一指": {"material": "古神一指骨纹", "source": "古神肉身之道", "effect": "一指点出，以气血和法力同时压制。", "aliases": ["古神", "一指"], "combat": (0.13, 0.05, 0)},
    "岁月意境": {"material": "岁月意境残砂", "source": "时光意境", "effect": "让对手攻势似被时光拖慢，增加防御与先觉。", "aliases": ["岁月", "时光"], "combat": (0.06, 0.09, 5)},
    "杀戮本源": {"material": "杀戮本源血符", "source": "本源感悟", "effect": "攻势带上杀戮气机，伤害爆发更高。", "aliases": ["杀戮", "本源"], "combat": (0.16, 0.00, 0)},
    "梦道轮回": {"material": "梦道轮回沙", "source": "梦与轮回之道", "effect": "以梦境干扰战局，偏向控场和护身。", "aliases": ["梦道", "轮回"], "combat": (0.05, 0.10, 4)},
    "因果断线": {"material": "因果断线真箓", "source": "因果法则", "effect": "斩断一线攻势因果，以守为主并伺机反击。", "aliases": ["因果", "断线"], "combat": (0.07, 0.12, 3)},
    "牧天九歌": {"material": "牧天九歌玉简", "source": "神通唱诵之道", "effect": "歌声引动法则，让术式更易连成气势。", "aliases": ["牧天", "九歌"], "combat": (0.11, 0.06, 2)},
    "天问一式": {"material": "天问一式法旨", "source": "问道叩天之法", "effect": "一问落下，攻势中带神魂压迫。", "aliases": ["天问", "一式"], "combat": (0.12, 0.04, 1)},
    "神藏开阖": {"material": "神藏开阖残图", "source": "肉身神藏", "effect": "打开身中神藏，提升灵力转化和护体。", "aliases": ["神藏", "开阖"], "combat": (0.08, 0.08, 2)},
}

SPECIAL_ABILITY_MATERIAL_TO_ABILITY = {
    "八禁感悟": "八禁",
    "神禁烙印": "神禁领域",
    "掌天瓶影拓片": "掌天瓶影",
    "掌天瓶影碎片": "掌天瓶影",
    "青元剑芒手札": "青元剑芒",
    "青元剑芒残页": "青元剑芒",
    "元婴天兆星痕": "元婴天兆",
    "道经轮海残章": "道经轮海",
    "斗战圣法残卷": "斗战圣法",
    "荒古圣血金纹": "荒古圣血",
    "凡骨战意札": "八禁",
    "青帝莲相旧纹": "青帝莲相",
    "至尊骨符文": "至尊骨符文",
    "以身为种道痕": "以身为种",
    "他化自在影": "他化自在影",
    "十洞天神环碎光": "十洞天神环",
    "鲲鹏极速羽痕": "鲲鹏极速",
    "柳神法相枝影": "柳神法相",
    "古神一指骨纹": "古神一指",
    "岁月意境残砂": "岁月意境",
    "杀戮本源血符": "杀戮本源",
    "梦道轮回沙": "梦道轮回",
    "因果断线真箓": "因果断线",
    "牧天九歌玉简": "牧天九歌",
    "天问一式法旨": "天问一式",
    "问道旧简": "天问一式",
    "神藏开阖残图": "神藏开阖",
    "小神藏残图": "神藏开阖",
}

ATTRIBUTE_TECHNIQUE_NAMES = {
    "金": ["太白斩星", "庚金裂空", "剑气雷音", "白虹贯日", "金阙镇魔"],
    "木": ["青莲化生", "万藤缚龙", "建木撑天", "草木皆兵", "长生回春"],
    "水": ["沧海归墟", "天河倒卷", "水月镜花", "玄浪分潮", "寒潮镇魂"],
    "火": ["太阳真火", "朱雀焚天", "离火炼界", "赤莲破妄", "炎龙吞海"],
    "土": ["玄黄不动", "息壤镇岳", "搬山覆海", "厚土载道", "山河印落"],
    "雷": ["紫霄万劫", "五雷正法", "雷海洗身", "劫光破阵", "天罚一指"],
    "冰": ["太阴玄封", "寒狱葬天", "冰魄凝魂", "霜华照影", "玄冥锁界"],
}
GENERAL_TECHNIQUE_NAMES = ["大威天龙", "大罗法咒", "问心一剑", "袖里乾坤", "灵台镇念"]
SOUL_INSIGHT_LAYER = 3
PHYSIQUE_TRAIT_NAMES = {
    "\u8352\u53e4\u5723\u4f53": "\u5723\u4f53\u91d1\u8840",
    "\u4ee5\u8eab\u4e3a\u79cd": "\u8eab\u79cd\u9053\u82bd",
    "\u6df7\u6c8c\u795e\u9b54\u4f53": "\u6df7\u6c8c\u795e\u9b54\u76f8",
    "\u5148\u5929\u9053\u80ce": "\u9053\u80ce\u5171\u9e23",
    "\u592a\u9634\u4e4b\u4f53": "\u592a\u9634\u5bd2\u9b44",
    "\u592a\u9633\u795e\u4f53": "\u592a\u9633\u795e\u7130",
    "\u9752\u83b2\u9053\u4f53": "\u9752\u83b2\u9053\u97f5",
    "\u91d1\u7fc5\u795e\u8109": "\u91d1\u7fc5\u6781\u901f",
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
SPECIAL_ABILITY_CATEGORY = "特殊能力"

MYSTIC_REALM_TYPES = ("上古宗门遗址", "兽潮", "上古大能洞府")
MYSTIC_REALM_MAX_STEPS = 10
BEAST_NAME_PREFIXES = [
    "赤焰", "玄霜", "碧鳞", "噬月", "裂山", "幽冥", "金瞳", "雷角", "青翼", "血纹",
    "吞星", "搬山", "银翼", "黑渊", "紫电", "白骨", "青冥", "古荒", "血月", "玄甲",
    "九首", "独角", "金翅", "寒狱", "离火", "沧溟", "黄泉", "风吼", "铁脊", "玉鳞",
]
BEAST_NAME_SUFFIXES = [
    "妖虎", "蛟王", "灵猿", "玄龟", "魔狼", "狮鹫", "蛇君", "古象", "鹰王", "蜃兽",
    "魔猿", "荒犼", "雷鹏", "骨龙", "火麟", "冰蟒", "山魈", "血蝠", "天狼", "玄蛛",
    "石犀", "鬼面獒", "碧眼蟾", "吞月狐", "裂海鲸", "赤羽鸾", "铁甲蜈", "青鳞鲛", "风翼豹", "古蜥",
]

MYSTIC_EVENT_THEMES = {
    "上古宗门遗址": {
        "places": [
            "藏经阁残楼", "断剑石阶", "荒废丹房", "祖师殿前", "问心石林", "传功玉璧", "灵兽园废墟", "山门铜钟",
            "剑冢深处", "试炼石塔", "外门讲法台", "护山阵眼", "掌门闭关室", "灵田枯井", "符堂灰烬", "炼器地火口",
            "云桥断处", "执法堂旧案台", "功德碑背面", "禁地石门",
        ],
        "actions": [
            "推开", "叩问", "绕行", "踏入", "静坐感应", "以灵力试探", "沿裂痕追索", "拂去尘灰查看", "布下简阵护身后靠近", "屏息倾听",
        ],
        "omens": [
            "残页自行翻动", "剑痕泛起冷光", "丹香忽然复燃", "石像眼中有泪", "心魔低声问道", "玉璧浮出古字", "兽骨叩击地面", "铜钟无风自鸣", "阵纹明灭如星", "灰烬中生出青芽",
        ],
    },
    "兽潮": {
        "places": [
            "黑雾谷口", "碎骨河滩", "兽巢外环", "坍塌山脊", "血月林间", "雷暴沼泽", "寒潭边缘", "赤砂荒丘",
            "妖云深处", "古战场裂隙", "灵矿塌洞", "枯木巢穴", "风吼峡道", "石林伏击点", "毒瘴洼地", "断崖兽道",
            "兽王祭坛", "潮湿洞窟", "残破营地", "月影坡前",
        ],
        "actions": [
            "正面压上", "绕后探查", "设阵固守", "救下散修", "追踪足印", "潜入巢穴", "采集残留灵材", "以傀儡引开兽群", "屏息观察首领", "趁乱夺取妖核",
        ],
        "omens": [
            "兽吼震得山石滚落", "妖云压低三尺", "首领气血如炉", "地底传来爪刨声", "幼兽忽然噤声", "腥风里夹着雷光", "白骨堆中有灵火", "远处散修阵旗折断", "兽群退开一条血路", "巢穴深处响起心跳",
        ],
    },
    "上古大能洞府": {
        "places": [
            "洞府石门", "长明古灯旁", "白玉阶尽头", "静室蒲团前", "沉默宝匣", "残缺阵眼", "水镜回廊", "青铜仙棺侧",
            "星砂沙漏前", "无字碑下", "血色莲池", "倒悬丹炉", "虚空裂缝边", "古镜照影处", "问道棋盘", "封魔铁索旁",
            "枯坐骸骨前", "天井月光中", "壁画深处", "石胎呼吸处",
        ],
        "actions": [
            "触碰", "点亮", "翻看", "踏上", "以神识试探", "闭目感应", "检查", "逆转阵纹", "祭出护身符箓", "默念清心口诀靠近",
        ],
        "omens": [
            "禁制明灭不定", "古灯照出前世影", "阶上浮现血脚印", "蒲团传出讲道声", "宝匣内有心跳", "阵眼吞吐星辉", "镜中人先你一步抬头", "棺盖轻轻震动", "沙漏倒流一息", "碑面映出你的名字",
        ],
    },
}


def build_mystic_event_pool(realm_type: str) -> list[str]:
    theme = MYSTIC_EVENT_THEMES[realm_type]
    events: list[str] = []
    for place in theme["places"]:
        for action in theme["actions"]:
            omen = theme["omens"][(len(events) + len(place) + len(action)) % len(theme["omens"])]
            events.append(f"{action}{place}，{omen}")
            if len(events) >= 100:
                return events
    return events


MYSTIC_OPTION_POOLS = {
    realm_type: build_mystic_event_pool(realm_type)
    for realm_type in MYSTIC_REALM_TYPES
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
    "特殊能力": 260,
}
TIER_PRICE_RATIO = {"凡品": 1, "黄阶": 3, "玄阶": 9, "地阶": 27, "天阶": 81}
GRADE_PRICE_RATIO = {"下品": 1.0, "中品": 1.22, "上品": 1.55, "极品": 2.1}
TIER_REALM_REQUIREMENT = {"凡品": 0, "黄阶": 0, "玄阶": 3, "地阶": 4, "天阶": 5}
TALISMAN_DRAW_REALM_REQUIREMENT = {"\u51e1\u54c1": 0, "\u9ec4\u9636": 0, "\u7384\u9636": 3, "\u5730\u9636": 4, "\u5929\u9636": 5}
ALCHEMY_RECIPES = {
    "筑基丹": {"tier": "黄阶", "grade": "中品", "materials": ["凝露草", "清心草叶", "百年朱果"], "cost": 80, "difficulty": 4},
    "地脉筑基液": {"tier": "地阶", "grade": "下品", "materials": ["地脉火芝", "月华凝露", "黄芽芝"], "cost": 320, "difficulty": 9},
    "天道筑基露": {"tier": "天阶", "grade": "下品", "materials": ["天髓玉露", "大道莲子", "悟道茶心"], "cost": 1200, "difficulty": 15},
    "小还丹": {"tier": "玄阶", "grade": "中品", "materials": ["金纹灵芝", "火枣核", "紫纹灵木"], "cost": 180, "difficulty": 7},
    "金液丹": {"tier": "玄阶", "grade": "上品", "materials": ["金纹灵芝", "黑曜灵砂", "云母灵液"], "cost": 260, "difficulty": 8},
    "大还丹": {"tier": "地阶", "grade": "上品", "materials": ["紫府灵芝", "月华凝露", "地脉火芝"], "cost": 480, "difficulty": 11},
    "凝魄金丹": {"tier": "地阶", "grade": "极品", "materials": ["紫府灵芝", "养魂莲心", "金髓玉砂"], "cost": 760, "difficulty": 13},
    "造化金丹": {"tier": "天阶", "grade": "上品", "materials": ["九转玄参", "大道莲子", "玄黄母气"], "cost": 1800, "difficulty": 17},
    "元婴丹": {"tier": "地阶", "grade": "极品", "materials": ["玄冰玉髓", "紫府灵芝", "星陨玄铁"], "cost": 680, "difficulty": 12},
    "护婴丹": {"tier": "地阶", "grade": "上品", "materials": ["养魂莲心", "月华凝露", "天青灵藤"], "cost": 620, "difficulty": 11},
    "九窍化婴丹": {"tier": "天阶", "grade": "上品", "materials": ["九转玄参", "太阴寒髓", "悟道茶心"], "cost": 1900, "difficulty": 17},
    "九转凝神丹": {"tier": "天阶", "grade": "上品", "materials": ["九转玄参", "悟道茶心", "天髓玉露"], "cost": 1400, "difficulty": 15},
    "斩尘化神丹": {"tier": "天阶", "grade": "上品", "materials": ["悟道茶心", "太阴寒髓", "太阳真火液"], "cost": 2100, "difficulty": 18},
    "太清渡厄丹": {"tier": "天阶", "grade": "极品", "materials": ["天髓玉露", "混沌星砂", "悟道茶心"], "cost": 2200, "difficulty": 18},
    "渡劫护命丹": {"tier": "天阶", "grade": "极品", "materials": ["劫雷神木", "天髓玉露", "混沌星砂"], "cost": 2600, "difficulty": 19},
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
    combat_race: Optional[str] = None
    physique: Optional[str] = None
    special_abilities: Optional[list[str]] = None
    method_layers: Optional[dict[str, int]] = None

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
            "spirit_liquid": self.spirit_liquid,
            "bottleneck_days": self.bottleneck_days,
            "bottleneck_realm_index": self.bottleneck_realm_index,
            "last_bottleneck_date": self.last_bottleneck_date,
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
            "combat_race": self.combat_race,
            "physique": self.physique,
            "special_abilities": self.special_abilities or [],
            "method_layers": self.method_layers or {},
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
    overflow_exp: int = 0
    spirit_liquid_gain: int = 0
    bottleneck_days: int = 0
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


def lock_cultivation(record: UserRecord, today: Optional[Any] = None, days: int = 1, hours: Optional[int] = None) -> str:
    if hours is not None:
        if isinstance(today, datetime):
            now = today
        elif isinstance(today, date):
            now = datetime.combine(today, datetime.now().time())
        else:
            now = datetime.now()
        until = now + timedelta(hours=max(1, hours))
        record.cultivation_lock_until = until.isoformat(timespec="minutes")
        return cultivation_lock_text(record, now)
    lock_date = today.date() if isinstance(today, datetime) else (today or date.today())
    until = lock_date + timedelta(days=max(1, days))
    record.cultivation_lock_until = until.isoformat()
    return cultivation_lock_text(record, today)


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
    record.spirit_liquid = 0
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
            return {"realm_index": realm_index, "target": requirement["target"]}
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
            reward["target_realm"] = requirement["target"]
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
        item_name = weighted_choice([(name, breakthrough_item_fishing_weight(str(name))) for name in item_names])
    else:
        item_name = random.choice(item_names)
    prefer_high_tier = source == "fishing" and is_pill_like_breakthrough_item(str(item_name))
    days = record.bottleneck_days if source == "fishing" else 0
    reward = draw_named_reward(str(item_name), prefer_high_tier=prefer_high_tier, bottleneck_days=days)
    reward["breakthrough_bonus"] = True
    if prefer_high_tier:
        reward["high_tier_fishing_bonus"] = True
        reward["bottleneck_days"] = days
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
    item = consume_reward_by_names(record, list(requirement["items"]))
    if item is None:
        return (
            False,
            f"\u7a81\u7834\u5931\u8d25\uff1a\u9700\u8981 {breakthrough_required_text(record)}\u3002\u5883\u754c\u5706\u6ee1\u65f6\uff0c\u6bcf\u6b21\u7b7e\u5230\u6216\u5782\u9493\u90fd\u6709 50% \u6982\u7387\u989d\u5916\u83b7\u5f97\u5f53\u524d\u7a81\u7834\u9053\u5177\u3002",
        )
    old_realm = record.realm
    record.realm_index += 1
    record.realm_exp = 0
    reset_bottleneck_state(record)
    target_realm = record.realm
    mark = foundation_quality(item) if requirement.get("kind") == "foundation" else breakthrough_quality(item, record.realm_index)
    set_realm_mark(record, record.realm_index, mark)
    message = breakthrough_flavor_text(old_realm, target_realm, mark, item)
    special_reward = maybe_grant_special_ability_material(record, chance=0.35, source="突破余韵")
    if special_reward:
        message += f"\n突破余韵中落下一份{reward_display_name(special_reward)}，可发送“领悟特殊能力 编号”参悟。"
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
    record.total_exp = max(0, record.realm_index * record.progress_required + record.realm_exp)
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


def method_layer(record: UserRecord, method: Optional[dict[str, Any]]) -> int:
    if not method:
        return 0
    key = reward_signature(method)
    layers = record.method_layers or {}
    current = int(layers.get(key, 0))
    if current > 0:
        return max(1, min(9, current))
    tier_rank = TIER_RANKS.get(str(method.get("tier", "\u51e1\u54c1")), 0)
    grade_rank = GRADE_RANKS.get(str(method.get("grade", "\u4e2d\u54c1")), 1)
    return max(1, min(9, 1 + tier_rank // 2 + grade_rank // 2))


def set_method_layer(record: UserRecord, method: Optional[dict[str, Any]], layer: int) -> None:
    if not method:
        return
    if record.method_layers is None:
        record.method_layers = {}
    record.method_layers[reward_signature(method)] = max(1, min(9, int(layer)))


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
    if "\u91d1\u7fc5" in name or "\u5927\u9e4f" in name:
        return "\u5996\u65cf-\u91d1\u7fc5\u5927\u9e4f"
    if "\u9752\u83b2" in name:
        return "\u5996\u65cf-\u9752\u83b2"
    if stable_int(f"race-lock:{reward_signature(method)}") % 100 < 10:
        return stable_choice([race for race, _ in COMBAT_RACES], f"race-lock-choice:{reward_signature(method)}")
    return None


def method_techniques(method: Optional[dict[str, Any]], kind: Optional[str] = None) -> list[str]:
    if not method:
        return []
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
    name = reward_name(method)
    attribute = reward_required_attribute(method) or stable_choice(ATTRIBUTES, f"content-attr:{reward_signature(method)}")
    attr_name = ATTRIBUTE_NAMES.get(attribute, "\u7075\u6839")
    if kind == "\u4fee\u70bc\u7c7b":
        return f"{name}\u4ee5{attr_name}\u4e3a\u6839\uff0c\u5faa\u73af\u5468\u5929\u3001\u6e29\u517b\u7075\u53f0\uff0c\u4e3b\u589e\u7b7e\u5230\u4e0e\u804a\u5929\u4fee\u4e3a\u6536\u76ca\u3002"
    if kind == "\u953b\u4f53\u7c7b":
        return f"{name}\u5c06{attr_name}\u7075\u6c14\u5316\u5165\u6c14\u8840\uff0c\u589e\u5f3a\u8840\u91cf\u4e0e\u6297\u6253\u65ad\u80fd\u529b\uff0c\u5951\u5408\u4f53\u8d28\u65f6\u6536\u76ca\u66f4\u9ad8\u3002"
    if kind == "\u795e\u9b42\u7c7b":
        return f"{name}\u4e13\u4fee\u8bc6\u6d77\u4e0e\u5fc3\u5ff5\uff0c\u5c42\u6570\u8fbe\u5230{SOUL_INSIGHT_LAYER}\u5c42\u540e\u53ef\u63d0\u524d\u7aa5\u89c1\u90e8\u5206\u79d8\u5883\u5371\u9669\u3002"
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
    tier = str(method.get("tier", "\u51e1\u54c1"))
    grade = str(method.get("grade", "\u4e2d\u54c1"))
    sign_speed = int(10 * METHOD_SIGN_RATE.get(tier, 0.08) * grade_ratio(grade) * max(1, layer))
    chat_speed = METHOD_CHAT_BASE.get(tier, 0.35) * grade_ratio(grade) * max(1.0, layer / 2)
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
        "max_layer": 9,
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
        f"\u7c7b\u578b\uff1a{profile['kind']}\uff1b\u5c42\u6570\uff1a\u7b2c {profile['layer']} / {profile['max_layer']} \u5c42\uff1b\u7075\u6839\uff1a{compatible}",
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
    abilities = list(dict.fromkeys(record.special_abilities or []))
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
        "\u8352\u53e4\u5723\u4f53": 1.28,
        "\u5148\u5929\u9053\u80ce": 1.12,
        "\u592a\u9634\u4e4b\u4f53": 1.1,
        "\u592a\u9633\u795e\u4f53": 1.12,
        "\u9752\u83b2\u9053\u4f53": 1.15,
        "\u91d1\u7fc5\u795e\u8109": 1.08,
        "\u4ee5\u8eab\u4e3a\u79cd": 1.22,
        "\u6df7\u6c8c\u795e\u9b54\u4f53": 1.34,
    }.get(str(physique), 1.0)


def method_physique_multiplier(record: UserRecord, profile: dict[str, Any]) -> float:
    physique = record.physique or ""
    name = str(profile.get("name", ""))
    if not physique or not name:
        return 1.0
    pairs = (
        ("\u8352\u53e4\u5723\u4f53", ("\u91d1\u8eab", "\u4e0d\u706d", "\u953b\u4f53")),
        ("\u6df7\u6c8c\u795e\u9b54\u4f53", ("\u6df7\u6c8c", "\u4e07\u8c61", "\u592a\u865a")),
        ("\u9752\u83b2\u9053\u4f53", ("\u9752\u83b2", "\u957f\u751f", "\u4e07\u7075")),
        ("\u592a\u9634\u4e4b\u4f53", ("\u592a\u9634", "\u7384\u51b0", "\u5bd2")),
        ("\u592a\u9633\u795e\u4f53", ("\u592a\u9633", "\u771f\u706b", "\u79bb\u706b")),
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
    damage = int(power * float(damage_rate))
    defense = int(power * float(defense_rate))
    speed = int(speed_bonus)
    if kind == "eight":
        return damage, defense, speed, "\u6210\u529f\u5f00\u542f\u516b\u7981\uff0c\u6218\u610f\u66b4\u6da8"
    if kind == "god":
        return damage, defense, speed, "\u8e0f\u5165\u795e\u7981\u9886\u57df\uff0c\u77ed\u6682\u538b\u4f4f\u6218\u5c40"
    if kind == "secret":
        return damage, defense, speed, f"\u5f15\u52a8{ability}\uff0c\u4e5d\u79d8\u6cd5\u5219\u95ea\u73b0"
    return damage, defense, speed, f"\u5f15\u52a8{ability}\uff0c{info.get('effect', '\u6c14\u673a\u9aa4\u7136\u62d4\u5347')}"


def sanitize_combat_text(text: str) -> str:
    return re.sub(r"[\s,\u002c\u3001\uff0c\u3002.!\uff01\?\uff1f:\uff1a;\[\]\uff08\uff09()]+", "", str(text or ""))


def evaluate_combat_actions(record: UserRecord, actions: Sequence[dict[str, Any]], side_seed: str = "") -> dict[str, Any]:
    ensure_combat_profile(record)
    available = available_battle_techniques(record)
    abilities = list(record.special_abilities or [])
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
        if str(record.physique or "") == "\u91d1\u7fc5\u795e\u8109":
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
        if "\u516b\u7981" in text:
            used_special = True
            if "\u516b\u7981" in abilities:
                add_damage, add_defense, add_speed, message = combat_special_power(record, "\u516b\u7981", "eight")
                damage += add_damage
                defense += add_defense
                speed += add_speed
                triggered.append("\u516b\u7981")
                logs.append(message)
            else:
                logs.append("\u5c1d\u8bd5\u5f00\u542f\u516b\u7981\uff0c\u4f46\u672a\u638c\u63e1\u6b64\u80fd\u529b")
        if "\u795e\u7981" in text:
            used_special = True
            if "\u795e\u7981\u9886\u57df" in abilities:
                add_damage, add_defense, add_speed, message = combat_special_power(record, "\u795e\u7981\u9886\u57df", "god")
                damage += add_damage
                defense += add_defense
                speed += add_speed
                triggered.append("\u795e\u7981\u9886\u57df")
                logs.append(message)
            else:
                logs.append("\u51b2\u51fb\u795e\u7981\u5931\u8d25\uff0c\u6c14\u673a\u53ea\u662f\u4e00\u9707")
        if "\u4e5d\u79d8" in text or any(secret.split("-", 1)[-1] in text for secret in abilities if secret.startswith("\u4e5d\u79d8")):
            secrets = [secret for secret in abilities if secret.startswith("\u4e5d\u79d8")]
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
                logs.append("\u5c1d\u8bd5\u5f15\u52a8\u4e5d\u79d8\uff0c\u4f46\u8bc6\u6d77\u4e2d\u6ca1\u6709\u56de\u5e94")
        for ability in abilities:
            if ability in triggered or ability in {"\u516b\u7981", "\u795e\u7981\u9886\u57df"} or ability.startswith("\u4e5d\u79d8"):
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
        "abilities": list(record.special_abilities or []),
        "method": profile.get("display", "\u672a\u53c2\u609f\u529f\u6cd5"),
        "method_kind": profile.get("kind", "\u65e0"),
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
    right_fighter["hp"] = max(0, int(right_fighter["max_hp"] - left_output))
    left_fighter["hp"] = max(0, int(left_fighter["max_hp"] - right_output))
    left_fighter["dealt_damage"] = left_output
    right_fighter["dealt_damage"] = right_output
    ended_early = left_fighter["hp"] <= 0 or right_fighter["hp"] <= 0
    elapsed_seconds = duration_seconds
    if ended_early:
        left_ko = duration_seconds * (left_fighter["max_hp"] / max(1, right_output)) if left_fighter["hp"] <= 0 else duration_seconds
        right_ko = duration_seconds * (right_fighter["max_hp"] / max(1, left_output)) if right_fighter["hp"] <= 0 else duration_seconds
        elapsed_seconds = max(5, int(min(left_ko, right_ko, duration_seconds)))
    if left_fighter["hp"] > right_fighter["hp"]:
        winner = left_fighter
        loser = right_fighter
    elif right_fighter["hp"] > left_fighter["hp"]:
        winner = right_fighter
        loser = left_fighter
    else:
        left_score = left_fighter["power"] + left_fighter["speed"] * 40 + stable_int(f"tie:{left.user_id}:{right.user_id}") % 100
        right_score = right_fighter["power"] + right_fighter["speed"] * 40 + stable_int(f"tie:{right.user_id}:{left.user_id}") % 100
        winner, loser = (left_fighter, right_fighter) if left_score >= right_score else (right_fighter, left_fighter)
    timeline = []
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
        return True, "已同修邪修路线。秘境中不会因邪修陷阱直接落入坏结局，但所有坏结局禁修期变为12小时。"
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
    score = max(0, min(19, int(score)))
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
    exp_result = apply_exp(record, base_exp + method_bonus + plant_bonus + pending_exp, today)
    applied_exp, leveled_realms = exp_result
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
        overflow_exp=exp_result.overflow,
        spirit_liquid_gain=exp_result.spirit_liquid,
        bottleneck_days=record.bottleneck_days,
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


def available_special_ability_items(record: UserRecord) -> list[dict[str, Any]]:
    return rewards_by_category(record, SPECIAL_ABILITY_CATEGORY)


def special_ability_info(ability: str) -> dict[str, Any]:
    return dict(SPECIAL_ABILITY_INFOS.get(ability, {
        "material": ability,
        "source": "失落传承",
        "effect": "一段尚未完全明悟的特殊能力。",
        "aliases": [ability],
        "combat": (0.08, 0.04, 0),
    }))


def special_ability_material_target(record: UserRecord, material_name: str, seed: str = "") -> Optional[str]:
    material_name = str(material_name or "").strip()
    owned = set(record.special_abilities or [])
    if material_name == "九秘残页":
        candidates = [ability for ability in NINE_SECRET_ABILITIES if ability not in owned]
        if not candidates:
            return None
        return stable_choice(candidates, seed or f"nine-secret:{record.user_id}:{len(owned)}")
    if material_name in SPECIAL_ABILITY_POOL:
        return material_name
    target = SPECIAL_ABILITY_MATERIAL_TO_ABILITY.get(material_name)
    if target:
        return target
    for ability, info in SPECIAL_ABILITY_INFOS.items():
        if material_name == str(info.get("material", "")):
            return ability
    return None


def draw_special_ability_material(record: Optional[UserRecord] = None) -> dict[str, Any]:
    pool = [reward for reward in FISHING_REWARDS if reward[2] == SPECIAL_ABILITY_CATEGORY]
    if record is not None:
        unowned = set(SPECIAL_ABILITY_POOL) - set(record.special_abilities or [])
        preferred = [
            reward
            for reward in pool
            if special_ability_material_target(record, reward[3], f"draw:{record.user_id}:{reward[3]}") in unowned
        ]
        if preferred:
            pool = preferred
    if not pool:
        return make_reward("玄阶", "上品", SPECIAL_ABILITY_CATEGORY, "九秘残页")
    tier, grade, category, name, description, _ = weighted_choice([(reward, float(reward[5])) for reward in pool])
    return normalize_reward({"tier": tier, "grade": grade, "category": category, "name": name, "description": description})


def maybe_grant_special_ability_material(
    record: UserRecord,
    chance: float = 0.18,
    source: str = "",
) -> Optional[dict[str, Any]]:
    if not SPECIAL_ABILITY_POOL or random.random() >= chance:
        return None
    reward = draw_special_ability_material(record)
    reward["special_ability_bonus"] = True
    if source:
        reward["source"] = source
    append_reward(record, reward)
    return reward


def learn_special_ability(record: UserRecord, item_index: int) -> tuple[bool, str]:
    result = reward_position_by_category_index(record, SPECIAL_ABILITY_CATEGORY, item_index)
    if result is None:
        return False, "没有找到这个编号的特殊能力传承材料。"
    list_index, item = result
    seed = f"learn-special:{record.user_id}:{reward_signature(item)}:{item_index}:{len(record.special_abilities or [])}"
    target = special_ability_material_target(record, reward_name(item), seed)
    if not target:
        return False, f"{reward_display_name(item)} 暂时无法继续领悟：可解锁的九秘或特殊能力已全部掌握。"
    abilities = list(dict.fromkeys(record.special_abilities or []))
    if target in abilities:
        return False, f"你已掌握【{target}】，这份{reward_name(item)}可暂时留存或出售给其他修士。"
    if record.rewards is None or list_index >= len(record.rewards):
        return False, "传承材料位置发生变化，请重新打开背包确认编号。"
    record.rewards.pop(list_index)
    abilities.append(target)
    record.special_abilities = abilities
    info = special_ability_info(target)
    return (
        True,
        "\n".join(
            [
                f"叮！参悟 {reward_display_name(item)} 成功。",
                f"领悟特殊能力【{target}】。",
                f"来源：{info.get('source', '失落传承')}",
                f"效果：{info.get('effect', '一段尚未完全明悟的特殊能力。')}",
                "斗法中直接发送能力名或别名即可尝试触发；未命中战技时仍会按即兴术式处理。",
            ]
        ),
    )


def special_ability_list_text(record: UserRecord) -> str:
    abilities = list(dict.fromkeys(record.special_abilities or []))
    materials = available_special_ability_items(record)
    lines = ["【我的特殊能力】"]
    if abilities:
        lines.append(f"已领悟（{len(abilities)}）：")
        for index, ability in enumerate(abilities, start=1):
            info = special_ability_info(ability)
            damage, defense, speed = info.get("combat", (0.08, 0.04, 0))
            lines.append(
                f"{index}. {ability}｜伤害+{int(float(damage) * 100)}%｜防御+{int(float(defense) * 100)}%｜速度+{int(speed)}｜{info.get('effect', '')}"
            )
    else:
        lines.append("暂未领悟特殊能力。")
    lines.append("")
    lines.append("【可领悟传承材料】")
    if not materials:
        lines.append("暂无。垂钓、秘境和突破余韵都有机会获得九秘残页、八禁感悟、神禁烙印等传承材料。")
    else:
        for index, item in enumerate(materials, start=1):
            target = special_ability_material_target(record, reward_name(item), f"preview:{record.user_id}:{index}:{reward_signature(item)}")
            target_text = target or "已无可领悟目标"
            lines.append(f"{index}. {reward_display_name(item)} -> {target_text}")
    lines.append("发送“领悟特殊能力 编号”参悟传承；发送“特殊能力图鉴”查看完整追求路径。")
    return "\n".join(lines)


def special_ability_catalog_text(record: Optional[UserRecord] = None) -> str:
    owned = set(record.special_abilities or []) if record is not None else set()
    lines = [
        "【特殊能力图鉴】",
        "获取路径：垂钓、秘境探索、境界突破余韵会掉落“九秘残页”“八禁感悟”“神禁烙印”及其他传承材料。",
        "使用方式：背包查看材料，发送“领悟特殊能力 编号”进行参悟；斗法中发送能力名或别名可触发。",
        "",
    ]
    for index, ability in enumerate(SPECIAL_ABILITY_POOL, start=1):
        info = special_ability_info(ability)
        damage, defense, speed = info.get("combat", (0.08, 0.04, 0))
        mark = "已悟" if ability in owned else "未悟"
        aliases = "、".join(str(item) for item in info.get("aliases", [])[:3])
        lines.append(
            f"{index}. 【{mark}】{ability}｜材料：{info.get('material', ability)}｜来源：{info.get('source', '失落传承')}"
        )
        lines.append(
            f"   效果：{info.get('effect', '')}｜斗法：伤害+{int(float(damage) * 100)}% 防御+{int(float(defense) * 100)}% 速度+{int(speed)}｜别名：{aliases or ability}"
        )
    return "\n".join(lines)


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
    if record.method_layers is None:
        record.method_layers = {}
    key = reward_signature(method)
    record.method_layers.setdefault(key, method_layer(record, method))
    profile = method_profile(method, record)
    return True, f"\u5df2\u53c2\u609f {reward_display_name(method)}\uff0c\u5f53\u524d\u4e3a{profile['kind']}\uff0c\u7b2c{profile['layer']}\u5c42\uff0c\u7b7e\u5230\u4e0e\u804a\u5929\u4fee\u4e3a\u5c06\u83b7\u5f97\u52a0\u6210\u3002"


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
    reward = draw_fishing_rewards(1)[0]
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
    return random.choice(MYSTIC_SUCCESS_TEXTS.get(realm_type, MYSTIC_SUCCESS_TEXTS["上古宗门遗址"]))


def mystic_empty_text(realm_type: str) -> str:
    return random.choice(MYSTIC_EMPTY_TEXTS.get(realm_type, MYSTIC_EMPTY_TEXTS["上古宗门遗址"]))


def mystic_bad_ending_text(realm_type: str) -> str:
    return BAD_ENDING_TEXTS.get(realm_type, BAD_ENDING_TEXTS["上古大能洞府"])

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
        "insight": bool(entrance.get("insight")) or has_soul_insight(record),
        "tianji": bool(entrance.get("tianji")),
    }
    assign_mystic_bad_option(realm)
    if realm.get("tianji") and today is not None:
        record.last_tianji_mystic_date = today.isoformat()
    record.mystic_realm = realm
    return True, f"{mystic_realm_intro(realm)}\n{mystic_realm_options_text(record)}"

def mystic_reward_category(realm_type: str) -> str:
    if realm_type == "上古宗门遗址":
        return weighted_choice([("功法", 4), (SPECIAL_ABILITY_CATEGORY, 2), ("丹药", 2), ("阵盘", 2), ("灵材", 3), ("灵植", 2), ("仙缘", 1), ("杂物", 1)])
    if realm_type == "兽潮":
        return weighted_choice([("灵材", 5), ("灵石", 3), ("傀儡", 1), ("符箓", 2), ("灵食", 2), ("灵植", 2), (SPECIAL_ABILITY_CATEGORY, 1), ("仙缘", 1)])
    return weighted_choice([("奇物", 3), (SPECIAL_ABILITY_CATEGORY, 3), ("灵器", 2), ("丹药", 2), ("阵盘", 2), ("灵材", 2), ("灵植", 2), ("仙缘", 1), ("杂物", 2)])


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
        lock_hours = 12 if record.evil_cultivator else 3
        lock_text = lock_cultivation(record, today, hours=lock_hours)
        record.mystic_realm = None
        lines.append(mystic_bad_ending_text(realm_type))
        penalty = "12小时" if record.evil_cultivator else "3小时"
        lines.append(f"坏结局：进入{penalty}惩罚期，{lock_text}，期间无法通过任何手段提升修为。")
        return True, "\n".join(lines)
    if roll < bad_rate + success_chance:
        category = mystic_reward_category(realm_type)
        reward = draw_reward_by_category(category)
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
                lines.append(f"{mystic_success_text(realm_type)}触发 {reward_display_name(reward)}，修为 +{applied}{extra}。")
            else:
                lines.append(f"{mystic_success_text(realm_type)}触发 {reward_display_name(reward)}，但当前瓶颈或禁修阻住了灵机。")
        else:
            append_reward(record, reward)
            lines.append(f"{mystic_success_text(realm_type)}获得 {reward_display_name(reward)}。")
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
    special_ability_power = len(record.special_abilities or []) * 180
    power = realm_power + exp_power + sign_power + root_power + foundation_bonus + equipment_power + special_ability_power
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
        "spirit_liquid": record.spirit_liquid,
        "bottleneck_days": record.bottleneck_days,
        "array_multiplier": array_multiplier(record),
        "artifact_power": artifact_power(record.equipped_artifact, record),
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
        "special_abilities": list(record.special_abilities or []),
        "special_ability_materials": len(available_special_ability_items(record)),
        "special_ability_power": len(record.special_abilities or []) * 180,
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
        rank_result = apply_exp(record, exp)
        applied_exp, reward.leveled_realms = rank_result
        reward.exp = applied_exp
    record.fishing_chances += fishing_chances
    return reward
