"""各面板的纯文本装配（R-18）。

format_* 只根据传入数据拼字符串/分段列表，不发消息、不读写存档；
发送统一走 commands/panels.py。"""
from __future__ import annotations

from typing import Any

from ..domain import (
    ARTIFACT_REFINING_RECIPES,
    BREAKTHROUGH_REQUIREMENTS,
    FISHING_REWARDS,
    IMMORTAL_SEED_INFOS,
    REALMS,
    RankReward,
    acquired_root_summary,
    array_layer,
    array_layer_cap_text,
    array_multiplier,
    array_proficiency_cap,
    array_proficiency_value,
    artifact_power,
    artifact_realm_catalog_summary_text,
    available_arrays,
    available_artifacts,
    available_curios,
    available_foods,
    available_materials,
    available_methods,
    available_misc_items,
    available_pills,
    available_plants,
    available_puppets,
    available_special_ability_items,
    available_spirit_stones,
    available_talismans,
    battle_summary,
    breakthrough_item_quality_cap_text,
    breakthrough_quality_relation_text,
    breakthrough_requirement_key_for_realm_index,
    breakthrough_source_realm_index,
    breakthrough_target_realm,
    breakthrough_target_realm_index,
    catalog_item_detail_text,
    emperor_artifact_catalog_text,
    ensure_combat_profile,
    item_required_realm_index,
    method_power,
    method_profile,
    puppet_power,
    reward_display_name,
    shop_items_for_date,
    special_ability_catalog_text,
    spirit_stone_text,
)
from ..mystic_menu import MYSTIC_HELP_SUMMARY
from .parsing import parse_artifact_slot, parse_catalog_query
from .ranking import format_cultivation_rank, format_power_rank
from .texts import EMPEROR_CATALOG_TEXTS, SPECIAL_ABILITY_CATALOG_TEXTS


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
            "【秘境副本】",
            MYSTIC_HELP_SUMMARY,
            "常用：创建单人秘境 普通 / 创建单人秘境 高风险 / 秘境状态 / 秘境地图 / 投骰。",
            "组队：创建秘境队伍 普通 / 加入秘境队伍 / 秘境准备 / 开始秘境。",
            "战斗：群聊应战，私聊确认配装与出招；失败后可用 救援列表 / 秘境救援 1000。",
            "",
            "【任务与路线】",
            "任务：每日任务 / 接取任务 / 完成任务 1。路线：修炼路线 / 选择路线 剑修 / 选择身份 天机阁弟子。",
            "御兽秘境：群聊发送 御兽秘境开局 PVE 或 御兽秘境开局 PVP；开始后私聊任务堂购买随从、施放法术、升堂并完成招募。",
            "",
            "【交易、休闲、后台】",
            "商店：商店 / 购买 1 / 出售 丹药 1 / 批量出售 杂物 20 / 批量出售低阶灵器。",
            "万宝楼：万宝楼 / 万宝楼挂售 灵器 1 / 万宝楼购买 1 / 万宝楼下架 1。",
            "休闲：斗地主 / 斗地主帮助 / 御兽秘境 / 排行 / 战力榜。",
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
        f"\u53cc\u4fee\u6b21\u6570\uff1a{summary['hehuan_remaining']}",
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
            f"\u8eab\u4efd\u4ee4\u724c\uff1a{summary['identity']}\uff08\u53cc\u4fee\uff1a{summary['hehuan_remaining']}\uff09",
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


def _is_likely_sent_despite_error(exc: Exception) -> bool:
    """判断 ActionFailed 是否属于"消息实际已送达但 ACK 超时"的场景。

    NapCat/QQ NT 内核发图时，sendMsg 的 ACK 可能慢于超时阈值，
    导致 retcode=1200 ActionFailed，但消息实际已发出。
    """
    msg = str(getattr(exc, "wording", "") or getattr(exc, "message", "") or str(exc))
    return "1200" in msg or "Timeout" in msg or "sendMsg" in msg
