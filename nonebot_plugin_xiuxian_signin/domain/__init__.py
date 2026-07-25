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
from .economy import *  # noqa: F401,F403
from . import economy as _economy_module  # noqa: E402
_economy_module._domain = _domain_self  # noqa: E402
from .combat import *  # noqa: F401,F403
from . import combat as _combat_module  # noqa: E402
_combat_module._domain = _domain_self  # noqa: E402
from .codex import *  # noqa: F401,F403
from . import codex as _codex_module  # noqa: E402
_codex_module._domain = _domain_self  # noqa: E402
from .signin import *  # noqa: F401,F403
from . import signin as _signin_module  # noqa: E402
_signin_module._domain = _domain_self  # noqa: E402






























































# High-rank treasures enter through dangerous mystic realms and refining; base fishing validation stays stable.















































































































































































































































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





















