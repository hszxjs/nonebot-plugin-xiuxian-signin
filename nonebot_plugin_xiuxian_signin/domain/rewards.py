"""domain 物品/奖励核心（Layer 1 环打破器）。

由原 domain.py 抽取：物品元数据、归一化、背包读写、奖励签名等核心函数。
这些函数被几乎所有子系统依赖，作为 Layer 1 提取以打破循环依赖。
跨子系统调用通过模块级 _domain（由 __init__ 注入）延迟访问。
"""
from __future__ import annotations

import uuid

import re

from typing import Any, Optional

from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403
from .models import *  # noqa: F401,F403

_domain = None

# 奖励名称推断缓存（运行时由 known_reward_names_for_inference 填充）。
_REWARD_NAME_INFERENCE_CACHE: list[str] | None = None

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

def reward_category(reward: Optional[dict[str, Any]]) -> str:
    category = str((reward or {}).get("category", ""))
    if category == LEGACY_SPECIAL_ABILITY_CATEGORY:
        return SPECIAL_ABILITY_CATEGORY
    if category == LEGACY_IMMORTAL_SEED_CATEGORY:
        return IMMORTAL_SEED_CATEGORY
    return category

def reward_name(reward: Optional[dict[str, Any]]) -> str:
    return canonical_item_name(str((reward or {}).get("name", "")))

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

def same_named_growth_item(left: Optional[dict[str, Any]], right: Optional[dict[str, Any]], category: str) -> bool:
    return bool(left and right and reward_category(left) == category and reward_category(right) == category and reward_name(left) == reward_name(right))

def ensure_method_tracking(record: UserRecord, method: dict[str, Any]) -> None:
    if record.method_layers is None:
        record.method_layers = {}
    if record.method_proficiency is None:
        record.method_proficiency = {}
    key = reward_signature(method)
    record.method_layers.setdefault(key, 1)
    record.method_layers[key] = max(1, min(_domain.method_layer_cap(method), int(record.method_layers.get(key, 1) or 1)))
    record.method_proficiency.setdefault(key, 0)

def ensure_array_tracking(record: UserRecord, array: dict[str, Any]) -> None:
    if record.array_proficiency is None:
        record.array_proficiency = {}
    if record.array_layers is None:
        record.array_layers = {}
    key = reward_signature(array)
    record.array_layers.setdefault(key, 1)
    record.array_layers[key] = max(1, min(_domain.array_layer_cap(array), int(record.array_layers.get(key, 1) or 1)))
    if key not in record.array_proficiency:
        legacy = 0
        if record.equipped_method:
            legacy_key = reward_signature(record.equipped_method)
            legacy = int(record.array_proficiency.get(legacy_key, 0) or 0)
        record.array_proficiency[key] = max(0, legacy)

def advance_method_by_duplicate(record: UserRecord, method: dict[str, Any], incoming: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    ensure_method_tracking(record, method)
    old_key = reward_signature(method)
    old_display = reward_display_name(method)
    current_layer = _domain.method_layer(record, method) or 1
    new_layer = current_layer + 1
    quality_up = False
    if not _domain.growth_has_unlimited_deduction(method) and current_layer >= METHOD_LAYER_STEP:
        next_quality = _domain.next_growth_quality(str(method.get("tier", "凡品")), str(method.get("grade", "下品")), METHOD_GROWTH_TIERS)
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
    _domain.migrate_tracking_key(record.method_layers, old_key, new_key, new_layer, keep_max=False)
    _domain.migrate_tracking_key(record.method_proficiency, old_key, new_key, 0 if quality_up else None, keep_max=not quality_up)
    _domain.sync_equipped_growth_item(record, METHOD_CATEGORY, old_key, method)
    if incoming is not None:
        _domain.set_growth_reward_note(incoming, method, old_display, new_layer, quality_up, METHOD_CATEGORY)
    return method

def advance_array_by_duplicate(record: UserRecord, array: dict[str, Any], incoming: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    ensure_array_tracking(record, array)
    old_key = reward_signature(array)
    old_display = reward_display_name(array)
    current_layer = _domain.array_layer(record, array) or 1
    current_proficiency = _domain.array_proficiency_value(record, array)
    new_layer = current_layer + 1
    quality_up = False
    if not _domain.growth_has_unlimited_deduction(array) and current_layer >= ARRAY_LAYER_STEP:
        next_quality = _domain.next_growth_quality(str(array.get("tier", "凡品")), str(array.get("grade", "下品")), ARRAY_GROWTH_TIERS)
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
    _domain.migrate_tracking_key(record.array_layers, old_key, new_key, new_layer, keep_max=False)
    migrated = _domain.migrate_tracking_key(record.array_proficiency, old_key, new_key, current_proficiency, keep_max=True)
    record.array_proficiency[new_key] = min(_domain.array_proficiency_cap(array, new_layer), migrated)
    _domain.sync_equipped_growth_item(record, ARRAY_CATEGORY, old_key, array)
    if incoming is not None:
        _domain.set_growth_reward_note(incoming, array, old_display, new_layer, quality_up, ARRAY_CATEGORY)
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
        score = _domain.breakthrough_effective_quality_score(item, target_index)
        quality = _domain.breakthrough_quality_label_from_score(score, target_index)
        candidates.append((list_index, item, score, quality))
    candidates.sort(key=lambda entry: _domain._breakthrough_candidate_sort_key(entry, name_order), reverse=True)
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

def apply_demon_core_metadata(reward: dict[str, Any]) -> None:
    if not _domain.is_demon_core_item(reward):
        return
    realm_name = _domain.demon_core_realm_name(reward) or DEMON_CORE_DEFAULT_REALM_BY_TIER.get(str(reward.get("tier")), "\u6b8b\u788e")
    attribute = _domain.demon_core_attribute(reward)
    reward["beast_realm"] = realm_name
    reward["element"] = attribute
    reward["required_attribute"] = attribute
    reward["cultivation_exp"] = _domain.demon_core_cultivation_exp(reward)
    reward.setdefault("usage", "\u70bc\u4e39\u6750\u6599\uff1b\u53ef\u70bc\u5316\u63d0\u5347\u4fee\u4e3a\uff1b\u4e5f\u53ef\u70bc\u6210\u4e39\u7075\u6839\u7528\u4e8e\u4e94\u884c\u8865\u5168\u3002")
    reward["description"] = (
        f"{attribute}\u884c{realm_name}\u5996\u529b\u51dd\u6210\u7684\u5996\u4e39\uff0c"
        f"\u70bc\u5316\u7ea6\u53ef\u83b7\u5f97 {reward['cultivation_exp']} \u70b9\u4fee\u4e3a\uff0c"
        "\u4e5f\u53ef\u4f5c\u4e39\u7075\u6839\u4e0e\u70bc\u4e39\u6750\u6599\u3002"
    )

def reward_signature(reward: Optional[dict[str, Any]]) -> str:
    if not reward:
        return ""
    required = reward_required_attribute(reward) or ""
    return ":".join(
        [reward_category(reward), str(reward.get("tier", "")), str(reward.get("grade", "")), reward_name(reward), required]
    )

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

def normalize_artifact_slot(slot: Optional[str] = None, artifact: Optional[dict[str, Any]] = None) -> str:
    text = str(slot or "").strip()
    if text in ARTIFACT_SLOT_ALIASES:
        return ARTIFACT_SLOT_ALIASES[text]
    if text:
        return text
    if _domain.artifact_is_armor(artifact):
        return "护甲"
    return "主手"

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
