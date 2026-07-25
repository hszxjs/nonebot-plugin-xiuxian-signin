"""domain codex 子系统。

由原 domain.py 抽取。依赖 Layer 0+ 已提取子系统，跨子系统调用通过 _domain 延迟访问。
"""
from __future__ import annotations

import hashlib
import random
import re
import uuid
from typing import Any, Optional

from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403
from .models import *  # noqa: F401,F403
from .rewards import *  # noqa: F401,F403
from .roots import *  # noqa: F401,F403
from .realms import *  # noqa: F401,F403
from .methods_arrays import *  # noqa: F401,F403
from .equipment import *  # noqa: F401,F403
from .abilities import *  # noqa: F401,F403
from .crafting import *  # noqa: F401,F403
from .mystic_drops import *  # noqa: F401,F403
from .economy import *  # noqa: F401,F403

_domain = None

# 直接引用 mystic_drops 模块对象，读取其可调标量（apply_admin_config 运行时重绑）。
try:
    from . import mystic_drops as _mystic_drops_module  # noqa: E402,F401
except ImportError:
    pass

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
