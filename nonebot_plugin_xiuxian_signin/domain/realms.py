"""domain 境界与突破子系统（Layer 2）。

由原 domain.py 抽取：境界阶段、突破流程、瓶颈锁定、境界品质、突破物品与奖励抽取等。
依赖 Layer 0/1 + roots，跨子系统调用通过 _domain 延迟访问。
"""
from __future__ import annotations

import random

from typing import Any, Optional
from datetime import date, datetime, timedelta

from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403
from .models import *  # noqa: F401,F403
from .rewards import *  # noqa: F401,F403
from .roots import *  # noqa: F401,F403

_domain = None

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

def breakthrough_candidate_sort_key(entry: tuple[int, dict[str, Any], int, str], name_order: dict[str, int]) -> tuple[int, int, int, int, int]:
    list_index, item, score, _quality = entry
    name = reward_name(item)
    return (
        int(score),
        breakthrough_item_quality_cap(name),
        item_quality_score(item),
        name_order.get(name, -1),
        -int(list_index),
    )

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
    special_reward = _domain.maybe_grant_special_ability_material(record, chance=0.35, source="突破余韵")
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

def realm_ratio(record: UserRecord) -> float:
    return record.realm_exp / max(1, record.progress_required)

def has_realm_progress(record: UserRecord, realm_index: int, ratio: float = 0.0) -> bool:
    return record.realm_index > realm_index or (record.realm_index == realm_index and realm_ratio(record) >= ratio)
