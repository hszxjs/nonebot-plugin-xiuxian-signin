"""domain 通用工具函数。

由原 domain.py 抽取：纯叶子工具函数（随机加权、数值换算、属性归一化等），
仅依赖标准库与 .constants，作为 Layer 0 工具层。
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

from .constants import *  # noqa: F401,F403  # REALMS/ATTRIBUTE_NAMES/normalize_root_attribute 等数据

__all__ = [
    "root_attribute_name",
    "root_attribute_sort_key",
    "normalize_mystic_settlement_ids",
    "weighted_choice",
    "grade_ratio",
    "tier_exp",
    "spirit_stone_text",
    "weighted_choice_rng",
    "stable_int",
    "stable_choice",
    "weighted_choice_stable",
    "realm_short_name",
    "quality_score_from_tier_grade",
    "tier_grade_from_quality_score",
    "_realm_index",
]

def root_attribute_name(attribute: Optional[str]) -> str:
    normalized = normalize_root_attribute(attribute)
    label = root_attribute_label(normalized)
    return ATTRIBUTE_NAMES.get(normalized, f"{label}灵根")
def root_attribute_sort_key(attribute: Optional[str]) -> tuple[int, str]:
    normalized = normalize_root_attribute(attribute)
    return (ROOT_ATTRIBUTE_ORDER.get(normalized, len(ROOT_ATTRIBUTE_ORDER)), normalized)
def normalize_mystic_settlement_ids(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        settlement_id = str(item or "").strip()
        if not settlement_id or settlement_id in seen:
            continue
        seen.add(settlement_id)
        normalized.append(settlement_id)
    return normalized[-100:]
def weighted_choice(items: Sequence[tuple[T, float]]) -> T:
    total = sum(weight for _, weight in items)
    point = random.uniform(0, total)
    cursor = 0.0
    for item, weight in items:
        cursor += weight
        if cursor >= point:
            return item
    return items[-1][0]
def _realm_index(name: str, default: int) -> int:
    try:
        return REALMS.index(name)
    except ValueError:
        return default
def grade_ratio(grade: str) -> float:
    return GRADE_EXP_RATIO.get(str(grade), 1.0)
def tier_exp(base_map: dict[str, int], tier: str, grade: str) -> int:
    base = base_map.get(str(tier), min(base_map.values()))
    return max(1, int(base * grade_ratio(grade)))
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
def weighted_choice_rng(items: Sequence[tuple[T, float]], rng: random.Random) -> T:
    total = sum(weight for _, weight in items)
    point = rng.uniform(0, total)
    cursor = 0.0
    for item, weight in items:
        cursor += weight
        if cursor >= point:
            return item
    return items[-1][0]
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
def realm_short_name(realm_name: str) -> str:
    return str(realm_name).split("·", 1)[0] or "炼体期"
def quality_score_from_tier_grade(tier: str, grade: str) -> int:
    return TIER_RANKS.get(str(tier), 0) * 4 + GRADE_RANKS.get(str(grade), 0)
def tier_grade_from_quality_score(score: int) -> tuple[str, str]:
    max_score = len(TIER_ORDER) * len(GRADE_ORDER) - 1
    score = max(0, min(max_score, int(score)))
    tier_rank, grade_rank = divmod(score, 4)
    tier = TIER_ORDER[max(0, min(len(TIER_ORDER) - 1, tier_rank))]
    grade = GRADE_ORDER[max(0, min(len(GRADE_ORDER) - 1, grade_rank))]
    return tier, grade
