"""domain 功法与阵盘子系统（Layer 2）。

由原 domain.py 抽取：功法/阵盘层数、熟练度、成长追踪、阵法推演、聊天修炼等。
依赖 Layer 0/1 + roots + realms，跨子系统调用通过 _domain 延迟访问。
"""
from __future__ import annotations

from typing import Any, Optional

from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403
from .models import *  # noqa: F401,F403
from .rewards import *  # noqa: F401,F403
from .roots import *  # noqa: F401,F403
from .realms import *  # noqa: F401,F403

_domain = None

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

def sync_equipped_growth_item(record: UserRecord, category: str, old_key: str, item: dict[str, Any]) -> None:
    if category == METHOD_CATEGORY and record.equipped_method:
        if reward_signature(record.equipped_method) == old_key or same_named_growth_item(record.equipped_method, item, category):
            record.equipped_method = dict(item)
    if category == ARRAY_CATEGORY and record.equipped_array:
        if reward_signature(record.equipped_array) == old_key or same_named_growth_item(record.equipped_array, item, category):
            record.equipped_array = dict(item)

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
        hp_bonus = max(60, int(_domain.method_power(method, record) * (0.18 + layer * 0.035)))
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
    methods = _domain.available_methods(record)
    if method_index < 1 or method_index > len(methods):
        return False, f"\u8bf7\u9009\u62e9 1-{len(methods)} \u4e4b\u95f4\u7684\u529f\u6cd5\u7f16\u53f7\u3002" if methods else "\u6682\u65e0\u53ef\u5b66\u4e60\u529f\u6cd5\u3002"
    method = methods[method_index - 1]
    profile = method_profile(method, record)
    compatible = "\u5951\u5408" if _domain.item_is_compatible(record, method) else "\u7075\u6839\u4e0d\u5951\u5408"
    race_req = profile.get("required_race") or "\u65e0"
    technique_parts = [
        f"{tech}\uff08\u8017\u7075{_domain.technique_mana_cost(record, tech)} / CD{_domain.technique_cooldown(tech)}\u606f\uff09"
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
    layer = _domain.array_layer(record, array)
    proficiency = _domain.array_proficiency_value(record, array)
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
    cap = _domain.array_proficiency_cap(array, _domain.array_layer(record, array))
    record.array_proficiency[key] = min(cap, int(record.array_proficiency.get(key, 0) or 0) + gain)

def method_sign_bonus(record: UserRecord, base_exp: int) -> int:
    method = record.equipped_method
    if not method or not _domain.item_is_compatible(record, method):
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
    if count <= 0 or not method or not _domain.item_is_compatible(record, method):
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

def next_tier_grade(tier: str, grade: str) -> tuple[str, str]:
    result = next_growth_quality(tier, grade, TIER_ORDER)
    return result if result is not None else ("仙阶", "极品")

def array_deduction_text(record: UserRecord) -> str:
    arrays = _domain.available_arrays(record)
    lines = ["【阵法推演】", "重复获得阵盘会自动对同名阵盘推演：每次加一层，10层后升品或升阶；仙阶极品后可无限推演。"]
    if not arrays:
        lines.append("暂无阵盘。")
    for index, array in enumerate(arrays, start=1):
        layer = _domain.array_layer(record, array)
        proficiency = _domain.array_proficiency_value(record, array)
        cap = _domain.array_proficiency_cap(array, layer)
        cap_text = array_layer_cap_text(array)
        same = sum(1 for item in record.rewards or [] if reward_category(item) == ARRAY_CATEGORY and reward_name(item) == reward_name(array))
        lines.append(
            f"{index}. {reward_display_name(array)}｜第{layer}/{cap_text}层｜熟练度 {proficiency}/{cap}｜旧档同名数量 {same}"
        )
    lines.append("发送“阵法推演 编号”可查看该阵盘状态；后续重复获得同名阵盘会自动并入推演。")
    return "\n".join(lines)

def deduce_array(record: UserRecord, array_index: int) -> tuple[bool, str]:
    arrays = _domain.available_arrays(record)
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
        layer = _domain.array_layer(record, target)
        proficiency = _domain.array_proficiency_value(record, target)
        cap = _domain.array_proficiency_cap(target, layer)
        return True, f"{reward_display_name(target)} 当前第{layer}/{array_layer_cap_text(target)}层，熟练度 {proficiency}/{cap}；后续重复获得同名阵盘会自动推演。"
    material = normalize_reward(record.rewards.pop(material_index), record) if record.rewards is not None else None
    if material is None:
        return False, "阵盘材料读取失败，请稍后再试。"
    for list_index, reward in enumerate(record.rewards or []):
        if reward_category(reward) == ARRAY_CATEGORY and reward_name(reward) == target_name:
            before = reward_display_name(reward)
            record.rewards[list_index] = advance_array_by_duplicate(record, normalize_reward(reward, record), material)
            after = reward_display_name(record.rewards[list_index])
            return True, f"阵纹重组，消耗 {reward_display_name(material)} 推演 {before}，当前为 {after} 第{_domain.array_layer(record, record.rewards[list_index])}层。"
    append_reward(record, material)
    return False, "没有找到可推演的目标阵盘。"
