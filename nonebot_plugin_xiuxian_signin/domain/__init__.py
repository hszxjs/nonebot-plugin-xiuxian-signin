from __future__ import annotations

import hashlib
import random
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Optional, TypeVar
from .constants import *  # noqa: F401,F403  # 数据表与派生初始化
from .utils import *  # noqa: F401,F403  # 通用工具函数
from .models import *  # noqa: F401,F403  # 数据类
from .rewards import *  # noqa: F401,F403  # 物品/奖励核心（Layer 1 环打破器）

# 子模块延迟访问器注入：models/rewards 的部分函数/property 反向调用仍在 __init__ 的子系统函数，
# 通过模块级 _domain 延迟访问。所有子模块 import 完成后统一注入 domain 主模块。
import sys as _sys
_domain_self = _sys.modules[__name__]
from . import models as _models_module  # noqa: E402
from . import rewards as _rewards_module  # noqa: E402
_models_module._domain = _domain_self  # noqa: E402
_rewards_module._domain = _domain_self  # noqa: E402
from .roots import *  # noqa: F401,F403  # 灵根子系统
from . import roots as _roots_module  # noqa: E402
_roots_module._domain = _domain_self  # noqa: E402
from .realms import *  # noqa: F401,F403  # 境界与突破子系统
from . import realms as _realms_module  # noqa: E402
_realms_module._domain = _domain_self  # noqa: E402
from .methods_arrays import *  # noqa: F401,F403  # 功法与阵盘子系统
from . import methods_arrays as _methods_arrays_module  # noqa: E402
_methods_arrays_module._domain = _domain_self  # noqa: E402
from .equipment import *  # noqa: F401,F403  # 装备子系统
from . import equipment as _equipment_module  # noqa: E402
_equipment_module._domain = _domain_self  # noqa: E402
from .mystic_drops import *  # noqa: F401,F403
from . import mystic_drops as _mystic_drops_module  # noqa: E402
_mystic_drops_module._domain = _domain_self  # noqa: E402






























































# High-rank treasures enter through dangerous mystic realms and refining; base fishing validation stays stable.














































































































































































def shop_items_for_date(date_text: str, record: Optional[UserRecord] = None) -> list[dict[str, Any]]:
    seed = f"{date_text}:{getattr(record, 'user_id', '')}:{getattr(record, 'realm_index', '')}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    pool = [(reward, float(reward[5])) for reward in FISHING_REWARDS if reward[2] != "仙缘"]
    items = []
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

    for name, definition in MYSTIC_TOKEN_DEFINITIONS.items():
        item = ensure(name, str(definition["category"]))
        item["_tiers"].add(str(definition["tier"]))
        item["_grades"].add(str(definition["grade"]))
        add_text(item, "_usage", str(definition["description"]))
        add_text(item, "_source", "签到、每日任务或后台配置投放")
        add_text(item, "_note", "秘境副本入场凭证；不进入垂钓奖池")

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


def _combat_action_baseline(record: UserRecord) -> dict[str, Any]:
    equipped_talisman = record.equipped_talisman
    equipped_talisman_power = talisman_power(equipped_talisman, record)
    equipped_talisman_name_text = equipped_talisman_name(record) if equipped_talisman_power > 0 else ""
    damage = int(battle_power(record) * 0.18)
    defense = int(battle_power(record) * 0.045)
    logs: list[str] = []
    if equipped_talisman_power > 0:
        damage += int(equipped_talisman_power * 0.72)
        defense += int(equipped_talisman_power * 0.52)
        logs.append(f"\u7b26\u7b93\u680f\u3010{equipped_talisman_name_text}\u3011\u62a4\u6301\u672c\u573a\u6597\u6cd5\uff0c\u4e0d\u6d88\u8017")
    elif equipped_talisman:
        logs.append(f"\u7b26\u7b93\u680f\u3010{equipped_talisman_name(record)}\u3011\u54c1\u9636\u8fc7\u9ad8\uff0c\u5f53\u524d\u5883\u754c\u5c1a\u65e0\u6cd5\u50ac\u52a8")
    return {
        "damage": damage,
        "defense": defense,
        "logs": logs,
        "talisman": equipped_talisman_name_text or equipped_talisman_name(record),
        "talisman_power": equipped_talisman_power,
    }






def _evaluate_one_combat_action(
    record: UserRecord,
    action_text: str,
    mana: int,
    cooldowns: dict[str, int],
    seed: str,
    *,
    include_baseline: bool,
    already_triggered: tuple[str, ...] = (),
) -> dict[str, Any]:
    ensure_combat_profile(record)
    available = available_battle_techniques(record)
    abilities = normalize_special_abilities(record.special_abilities)
    text = sanitize_combat_text(action_text)
    baseline = _combat_action_baseline(record)
    triggered: list[str] = []
    logs = list(baseline["logs"]) if text and include_baseline else []
    damage = int(baseline["damage"]) if text and include_baseline else 0
    defense = int(baseline["defense"]) if text and include_baseline else 0
    speed = 0
    mana_spent = 0
    physical_hits = 0
    trait_triggers = 0

    next_cooldowns = dict(cooldowns)

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
        cd_left = int(next_cooldowns.get(tech, 0))
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
        next_cooldowns[tech] = technique_cooldown(tech, improvised)
        damage += technique_power(record, tech, improvised=improvised)
        triggered.append(tech)
        if improvised:
            logs.append(
                f"\u5373\u5174\u672f\u5f0f\u7275\u52a8\u3010{tech}\u3011\uff0c\u7075\u529b-{cost}\uff0cCD{next_cooldowns[tech]}\u606f"
            )
        else:
            logs.append(
                f"\u65bd\u5c55\u6218\u6280\u3010{tech}\u3011\uff0c\u7075\u529b-{cost}\uff0cCD{next_cooldowns[tech]}\u606f"
            )
        return True

    if text:
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
                secret = stable_choice(secrets, f"secret:{seed}:{text}")
                add_damage, add_defense, add_speed, message = combat_special_power(record, secret, "secret")
                damage += add_damage
                defense += add_defense
                speed += add_speed
                triggered.append(secret)
                logs.append(message)
            else:
                logs.append("尚未悟得星律残篇，天机一闪而逝。")
        for ability in abilities:
            if (
                ability in already_triggered
                or ability in triggered
                or ability in FORBIDDEN_REALM_ABILITIES
                or ability.startswith("星律")
            ):
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
        elif not used_special:
            if available and mana > 0:
                choice_seed = f"improv:{seed}:{text}:{len(already_triggered) + len(triggered)}"
                cast_technique(stable_choice(available, choice_seed), improvised=True)
            elif mana <= 0:
                if not maybe_use_trait("\u7075\u529b\u8017\u5c3d"):
                    use_physical("\u7075\u529b\u8017\u5c3d")
            else:
                use_physical("\u5373\u5174\u672f\u5f0f\u672a\u6210")
    return {
        "damage": damage,
        "defense": defense,
        "speed": speed,
        "triggered": list(dict.fromkeys(triggered)),
        "logs": logs,
        "mana": max(0, mana),
        "mana_spent": mana_spent,
        "cooldowns": next_cooldowns,
        "physical_hits": physical_hits,
        "trait_triggers": trait_triggers,
        "talisman": str(baseline["talisman"]),
        "talisman_power": int(baseline["talisman_power"]),
    }


def resolve_combat_action(
    record: UserRecord,
    action_text: str,
    state: CombatRuntimeState,
    seed: str,
) -> CombatActionOutcome:
    action_is_effective = bool(sanitize_combat_text(action_text))
    next_cooldowns = {
        name: max(0, int(value) - 1)
        for name, value in state.cooldowns.items()
        if int(value) > 1
    }
    result = _evaluate_one_combat_action(
        record=record,
        action_text=action_text,
        mana=state.mana,
        cooldowns=next_cooldowns,
        seed=seed,
        include_baseline=state.turn == 0,
        already_triggered=state.triggered_abilities,
    )
    next_state = CombatRuntimeState(
        hp=state.hp,
        max_hp=state.max_hp,
        mana=max(0, int(result["mana"])),
        max_mana=state.max_mana,
        cooldowns={str(key): int(value) for key, value in dict(result["cooldowns"]).items()},
        turn=state.turn + int(action_is_effective),
        triggered_abilities=(
            *state.triggered_abilities,
            *(str(item) for item in result["triggered"]),
        ),
    )
    return CombatActionOutcome(
        state=next_state,
        damage=int(result["damage"]),
        defense=int(result["defense"]),
        speed=int(result["speed"]),
        triggered=tuple(str(item) for item in result["triggered"]),
        logs=tuple(str(item) for item in result["logs"]),
    )


def evaluate_combat_actions(record: UserRecord, actions: Sequence[dict[str, Any]], side_seed: str = "") -> dict[str, Any]:
    state = CombatRuntimeState.initial(record)
    outcomes: list[CombatActionOutcome] = []
    for index, action in enumerate(list(actions)[:8], start=1):
        action_text = str(action.get("text", ""))
        outcome = resolve_combat_action(record, action_text, state, f"{side_seed}:{index}")
        if sanitize_combat_text(action_text):
            outcomes.append(outcome)
        state = outcome.state

    if outcomes:
        damage = sum(outcome.damage for outcome in outcomes)
        defense = sum(outcome.defense for outcome in outcomes)
        speed = sum(outcome.speed for outcome in outcomes)
        triggered = [item for outcome in outcomes for item in outcome.triggered]
        logs = [item for outcome in outcomes for item in outcome.logs]
    else:
        baseline = _combat_action_baseline(record)
        damage = max(1, int(baseline["damage"]))
        defense = max(0, int(baseline["defense"]))
        speed = 0
        triggered = []
        logs = [str(item) for item in baseline["logs"]]

    equipped_talisman_power = talisman_power(record.equipped_talisman, record)
    equipped_talisman_name_text = equipped_talisman_name(record) if equipped_talisman_power > 0 else ""
    return {
        "damage": max(1, damage),
        "defense": max(0, defense),
        "speed": speed,
        "triggered": list(dict.fromkeys(triggered)),
        "logs": logs[:8],
        "mana": state.mana,
        "max_mana": state.max_mana,
        "mana_spent": max(0, state.max_mana - state.mana),
        "cooldowns": dict(state.cooldowns),
        "physical_hits": sum(log.startswith("\u6539\u4ee5\u8fd1\u8eab\u653b\u4f10") for log in logs),
        "trait_triggers": sum(log.startswith("\u4f53\u8d28\u7279\u6027\u3010") for log in logs),
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
    token_grants = grant_mystic_tokens(
        record,
        _mystic_drops_module.DAILY_TASK_NORMAL_MYSTIC_TOKEN_COUNT,
        _mystic_drops_module.DAILY_TASK_HIGH_RISK_MYSTIC_TOKEN_COUNT,
    )
    record.daily_tasks = {"date": today.isoformat(), "tasks": tasks}
    extra = f"，连破{leveled}境" if leveled else ""
    fish_text = f"，垂钓+{fishing}" if fishing else ""
    token_text = "".join(
        f"，{name}+{count}"
        for name, count in token_grants.items()
        if count
    )
    return True, f"完成任务：{task.get('title')}。修为+{applied}{extra}，灵石+{spirit_stone_text(stones)}{fish_text}{token_text}。"


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
    if random.random() < _mystic_drops_module.SIGNIN_EXTRA_FISHING_CHANCE_RATE:
        fishing_gain += 1
    record.fishing_chances += fishing_gain
    record.pending_fishing = record.fishing_chances
    grant_mystic_tokens(
        record,
        _mystic_drops_module.SIGNIN_NORMAL_MYSTIC_TOKEN_COUNT,
        _mystic_drops_module.SIGNIN_HIGH_RISK_MYSTIC_TOKEN_COUNT,
    )

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
        "mystic_realm": "进行中" if record.active_mystic_run_id else "无",
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
