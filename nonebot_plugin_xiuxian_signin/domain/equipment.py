"""domain 装备子系统（Layer 3）。

由原 domain.py 抽取：灵器/符箓/傀儡/灵植/仙源装备、各 power 计算、本命灵器、图鉴等。
依赖 Layer 0-2，跨子系统调用通过 _domain 延迟访问。
"""
from __future__ import annotations

from typing import Any, Optional

from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403
from .models import *  # noqa: F401,F403
from .rewards import *  # noqa: F401,F403
from .roots import *  # noqa: F401,F403
from .realms import *  # noqa: F401,F403
from .methods_arrays import *  # noqa: F401,F403

_domain = None

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

def can_buy_reward(record: UserRecord, reward: dict[str, Any]) -> tuple[bool, str]:
    required_index = item_required_realm_index(reward)
    if reward_category(reward) != ARTIFACT_CATEGORY and required_index > record.realm_index + 2:
        return False, f"{reward_display_name(reward)} 至少约需{REALMS[required_index]}附近才能驾驭，已超过当前修为两大境界。"
    price = int(reward.get("price") or reward_price(reward))
    if record.spirit_stones < price:
        return False, f"灵石不足，需要 {spirit_stone_text(price)}，当前 {spirit_stone_text(record.spirit_stones)}。"
    return True, ""

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

def item_is_compatible(record: UserRecord, item: dict[str, Any]) -> bool:
    required_attribute = reward_required_attribute(item)
    if not required_attribute:
        return True
    return required_attribute in record.root_attributes

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

def emperor_artifact_catalog_text(owner_lookup: Optional[dict[str, str]] = None) -> str:
    owner_lookup = owner_lookup or {}
    lines = ["\u3010\u552f\u4e00\u88c5\u5907\u56fe\u9274\u3011", "\u552f\u4e00\u88c5\u5907\u5177\u6709\u5168\u5c40\u552f\u4e00\u6027\uff1b\u4ed9\u5e1d\u5175\u672c\u4f53\u5df2\u6709\u4e3b\u65f6\uff0c\u540e\u7eed\u53ea\u80fd\u83b7\u5f97\u4eff\u5236\u54c1\u3002"]
    for index, (name, info) in enumerate(EMPEROR_ARTIFACT_INFOS.items(), start=1):
        owner = owner_lookup.get(name) or "\u6682\u65e0\u62e5\u6709\u8005"
        lines.append(f"{index}. {name}\uff5c\u70bc\u5236\u8005\uff1a{info.get('creator')}\uff5c\u6750\u6599\uff1a{info.get('material')}\uff5c\u62e5\u6709\u8005\uff1a{owner}")
        lines.append(f"   \u4e8b\u8ff9\uff1a{info.get('story')}\uff5c\u4e13\u5c5e\u6280\uff1a{info.get('skill')}")
    return "\n".join(lines)

def divine_ability_catalog_text(record: Optional[UserRecord] = None) -> str:
    text = _domain.special_ability_catalog_text(record)
    return text.replace("\u795e\u901a", "\u795e\u901a")

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
            power += _domain.special_ability_power_total(record) // 4
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
        layer = _domain.method_layer(record, method)
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
    layer = _domain.array_layer(record, record.equipped_array)
    proficiency = _domain.array_proficiency_value(record, record.equipped_array)
    cap = _domain.array_proficiency_cap(record.equipped_array, layer)
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
