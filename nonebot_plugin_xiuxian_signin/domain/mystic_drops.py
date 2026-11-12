"""domain mystic_drops 子系统。

由原 domain.py 抽取。跨子系统反向依赖一律在函数内 import，模块级不持有全局访问器。
"""
from __future__ import annotations

import random

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional

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


@dataclass(frozen=True)
class MysticTuning:
    """秘境/签到可调参数的**不可变快照**。

    所有字段只读（映射用 ``MappingProxyType`` 包裹、集合用 ``frozenset``、行列表用 ``tuple``），
    调参时整对象替换，读取方永远看到某个完整版本，不会读到「清空到一半」的中间态。
    """

    artifact_drop_pools: Mapping[int, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    enabled_types: frozenset[str] = frozenset()
    enabled_high_risk_types: frozenset[str] = frozenset()
    category_weights: Mapping[str, tuple[tuple[str, float], ...]] = field(default_factory=dict)
    drop_overrides: Mapping[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    fishing_option_rate: float = 0.05
    signin_extra_fishing_chance_rate: float = 0.10

    def __post_init__(self) -> None:
        """把映射字段统一包成只读视图，保证任何构造路径产出的快照都改不动。"""
        for name in ("artifact_drop_pools", "category_weights", "drop_overrides"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        for name in ("enabled_types", "enabled_high_risk_types"):
            object.__setattr__(self, name, frozenset(getattr(self, name)))


class _TuningHolder:
    """当前生效快照的唯一持有者。只有 ``apply_admin_config`` 会写它，写入是单次属性赋值。"""

    __slots__ = ("snapshot",)

    def __init__(self, snapshot: MysticTuning) -> None:
        self.snapshot = snapshot


def default_mystic_tuning() -> MysticTuning:
    return MysticTuning(
        enabled_types=frozenset(MYSTIC_REALM_TYPES),
        enabled_high_risk_types=frozenset(HIGH_RISK_MYSTIC_REALM_TYPES),
    )


_TUNING = _TuningHolder(default_mystic_tuning())


def current_mystic_tuning() -> MysticTuning:
    """返回当前生效的不可变快照（读取方统一走这里，不再读模块级可变全局）。"""
    return _TUNING.snapshot


def _install_mystic_tuning(snapshot: MysticTuning) -> None:
    _TUNING.snapshot = snapshot

def random_beast_name() -> str:
    return random.choice(BEAST_NAMES)

def mystic_token_reward(name: str) -> dict[str, Any]:
    try:
        definition = MYSTIC_TOKEN_DEFINITIONS[name]
    except KeyError as exc:
        raise ValueError(f"unknown mystic token {name!r}") from exc
    return {"name": name, **definition}

def default_mystic_category_weights() -> dict[str, list[dict[str, Any]]]:
    return {
        "上古宗门遗址": [
            {"category": "功法", "weight": 4}, {"category": SPECIAL_ABILITY_CATEGORY, "weight": 2},
            {"category": "丹药", "weight": 2}, {"category": "阵盘", "weight": 2},
            {"category": "灵材", "weight": 3}, {"category": "灵植", "weight": 2},
            {"category": "仙缘", "weight": 1}, {"category": "杂物", "weight": 1},
        ],
        "兽潮": [
            {"category": "灵材", "weight": 6}, {"category": "灵石", "weight": 3},
            {"category": "符箓", "weight": 2}, {"category": "灵食", "weight": 2},
            {"category": "灵植", "weight": 1}, {"category": SPECIAL_ABILITY_CATEGORY, "weight": 1},
            {"category": "仙缘", "weight": 1},
        ],
        "星古矿区": [
            {"category": "灵材", "weight": 6}, {"category": "灵石", "weight": 4},
            {"category": "奇物", "weight": 2}, {"category": "杂物", "weight": 2},
            {"category": "仙缘", "weight": 1},
        ],
        "魂界残域": [
            {"category": SPECIAL_ABILITY_CATEGORY, "weight": 4}, {"category": "功法", "weight": 3},
            {"category": "灵材", "weight": 2}, {"category": "符箓", "weight": 2},
            {"category": "奇物", "weight": 2}, {"category": "仙缘", "weight": 1},
        ],
        "古铜云阙": [
            {"category": SPECIAL_ABILITY_CATEGORY, "weight": 4}, {"category": "灵材", "weight": 3},
            {"category": "奇物", "weight": 3}, {"category": "灵器", "weight": 2},
            {"category": "功法", "weight": 2}, {"category": "仙缘", "weight": 1},
        ],
        "default": [
            {"category": "奇物", "weight": 3}, {"category": SPECIAL_ABILITY_CATEGORY, "weight": 3},
            {"category": "灵器", "weight": 2}, {"category": "丹药", "weight": 2},
            {"category": "阵盘", "weight": 2}, {"category": "灵材", "weight": 2},
            {"category": "灵植", "weight": 2}, {"category": "仙缘", "weight": 1},
            {"category": "杂物", "weight": 2},
        ],
    }

def default_artifact_drop_pools() -> dict[str, list[dict[str, Any]]]:
    pools: dict[str, list[dict[str, Any]]] = {}
    for realm_index in range(len(REALMS)):
        tiers = artifact_realm_tiers_for_index(realm_index)
        pools[str(realm_index)] = [
            {
                "tier_min": tiers[0],
                "tier_max": tiers[-1],
                "grade": "",
                "attribute": "",
                "name": "",
                "weight": 1,
            }
        ]
    return pools

def _tier_range(tier_min: str = "", tier_max: str = "") -> list[str]:
    order = list(ARTIFACT_REALM_BOUND_TIERS)
    start = order.index(tier_min) if tier_min in order else 0
    end = order.index(tier_max) if tier_max in order else len(order) - 1
    if start > end:
        start, end = end, start
    return order[start : end + 1]

def _artifact_pool_candidates(entry: dict[str, Any], tier: str = "", grade: str = "") -> list[dict[str, Any]]:
    try:
        realm_index = max(0, min(len(REALMS) - 1, int(entry.get("realm_index", 0))))
    except (TypeError, ValueError):
        realm_index = 0
    tiers = [str(item) for item in entry.get("tiers", []) if str(item) in ARTIFACT_REALM_BOUND_TIERS]
    if not tiers:
        exact_tier = str(entry.get("tier") or "")
        tiers = [exact_tier] if exact_tier in ARTIFACT_REALM_BOUND_TIERS else _tier_range(str(entry.get("tier_min") or ""), str(entry.get("tier_max") or ""))
    if tier and tier in ARTIFACT_REALM_BOUND_TIERS:
        tiers = [item for item in tiers if item == tier]
    grade_filter = str(grade or entry.get("grade") or "")
    grades = [grade_filter] if grade_filter in GRADE_RANKS else list(GRADE_ORDER)
    attribute = str(entry.get("attribute") or "")
    name = str(entry.get("name") or "")
    candidates = []
    for info in ARTIFACT_REALM_CATALOG:
        if int(info.get("realm_index", -1)) != realm_index:
            continue
        if str(info.get("tier")) not in tiers:
            continue
        if str(info.get("grade")) not in grades:
            continue
        if attribute and str(info.get("attribute")) != attribute:
            continue
        if name and str(info.get("name")) != name:
            continue
        candidates.append(info)
    return candidates

def configured_artifact_drop_entries() -> list[dict[str, Any]]:
    pools = current_mystic_tuning().artifact_drop_pools or {
        int(key): tuple(value) for key, value in default_artifact_drop_pools().items()
    }
    entries: list[dict[str, Any]] = []
    for realm_index, rows in pools.items():
        if not isinstance(rows, (list, tuple)):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            entry = dict(row)
            entry["realm_index"] = int(realm_index)
            entries.append(entry)
    return entries

def draw_configured_artifact_reward(
    tier: str = "",
    grade: str = "",
    rng: Optional[random.Random] = None,
) -> dict[str, Any]:
    entries = configured_artifact_drop_entries()

    def weighted_entries(use_tier: str, use_grade: str) -> list[tuple[tuple[dict[str, Any], list[dict[str, Any]]], float]]:
        result: list[tuple[tuple[dict[str, Any], list[dict[str, Any]]], float]] = []
        for entry in entries:
            candidates = _artifact_pool_candidates(entry, use_tier, use_grade)
            if not candidates:
                continue
            try:
                weight = float(entry.get("weight", 1))
            except (TypeError, ValueError):
                weight = 1.0
            if weight > 0:
                result.append(((entry, candidates), weight))
        return result

    weighted = weighted_entries(str(tier or ""), str(grade or ""))
    if not weighted:
        weighted = weighted_entries("", "")
    if weighted:
        _entry, candidates = weighted_choice_rng(weighted, rng) if rng is not None else weighted_choice(weighted)
        pick = rng.choice(candidates) if rng is not None else random.choice(candidates)
        return artifact_info_to_reward(dict(pick))
    fallback_realm = rng.randrange(len(REALMS)) if rng is not None else random.randrange(len(REALMS))
    fallback_tiers = artifact_realm_tiers_for_index(fallback_realm)
    fallback_tier = str(tier or (rng.choice(fallback_tiers) if rng is not None else random.choice(fallback_tiers)))
    fallback_grade = str(grade or (rng.choice(GRADE_ORDER) if rng is not None else random.choice(GRADE_ORDER)))
    return make_realm_artifact_reward(fallback_realm, fallback_tier, fallback_grade, rng)

def _category_weight_pairs(value: Any) -> list[tuple[str, float]]:
    entries: list[tuple[str, float]] = []
    if isinstance(value, dict):
        raw_entries = value.items()
    elif isinstance(value, list):
        raw_entries = []
        for item in value:
            if isinstance(item, dict):
                raw_entries.append((item.get("category"), item.get("weight", 1)))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                raw_entries.append((item[0], item[1]))
    else:
        raw_entries = []
    for category, weight in raw_entries:
        category_text = reward_category({"category": str(category or "")})
        try:
            weight_value = float(weight)
        except (TypeError, ValueError):
            continue
        if category_text and weight_value > 0:
            entries.append((category_text, weight_value))
    return entries

def apply_admin_config(config: dict[str, Any]) -> None:
    equipment_rules = config.get("equipment_rules", {}) if isinstance(config, dict) else {}
    if isinstance(equipment_rules, dict):
        tier_default = equipment_rules.get("tier_default_realm", {})
        if isinstance(tier_default, dict):
            for tier, realm_index in tier_default.items():
                if str(tier) in TIER_RANKS:
                    try:
                        ARTIFACT_TIER_DEFAULT_REALM[str(tier)] = max(0, min(len(REALMS) - 1, int(realm_index)))
                    except (TypeError, ValueError):
                        continue
        unlocks = equipment_rules.get("realm_tier_unlocks", {})
        if isinstance(unlocks, dict):
            for realm_key, tiers in unlocks.items():
                try:
                    realm_index = max(0, min(len(REALMS) - 1, int(realm_key)))
                except (TypeError, ValueError):
                    continue
                if isinstance(tiers, list):
                    allowed = [str(tier) for tier in tiers if str(tier) in TIER_RANKS and str(tier) != "仙帝兵"]
                    if allowed:
                        ARTIFACT_REALM_TIER_UNLOCKS[realm_index] = allowed
        power_base = equipment_rules.get("artifact_power_base", {})
        if isinstance(power_base, dict):
            for tier, value in power_base.items():
                if str(tier) in ARTIFACT_POWER_BASE:
                    try:
                        ARTIFACT_POWER_BASE[str(tier)] = max(1, int(value))
                    except (TypeError, ValueError):
                        continue
        realm_power_base = equipment_rules.get("artifact_realm_power_base", {})
        if isinstance(realm_power_base, dict):
            for realm_key, value in realm_power_base.items():
                try:
                    realm_index = max(0, min(len(REALMS) - 1, int(realm_key)))
                    ARTIFACT_REALM_POWER_BASE[realm_index] = max(1, int(value))
                except (TypeError, ValueError):
                    continue
        tier_ratio = equipment_rules.get("artifact_tier_power_ratio", {})
        if isinstance(tier_ratio, dict):
            for tier, value in tier_ratio.items():
                if str(tier) in ARTIFACT_TIER_POWER_RATIO:
                    try:
                        ARTIFACT_TIER_POWER_RATIO[str(tier)] = max(0.01, float(value))
                    except (TypeError, ValueError):
                        continue
        grade_ratio = equipment_rules.get("artifact_grade_ratio", {})
        if isinstance(grade_ratio, dict):
            for grade, value in grade_ratio.items():
                if str(grade) in ARTIFACT_GRADE_RATIO:
                    try:
                        ARTIFACT_GRADE_RATIO[str(grade)] = max(0.1, float(value))
                    except (TypeError, ValueError):
                        continue
        # `artifact_immortal_upgrade_rate` 只被后台表单当作配置键读写，游戏内无消费者，
        # 因此不再写模块级全局（原 globals() 重绑既无读者，又污染本模块命名空间）。
        drop_pools = equipment_rules.get("artifact_drop_pools", {})
        drop_pool_rows: dict[int, tuple[dict[str, Any], ...]] = {}
        if isinstance(drop_pools, dict):
            for realm_key, rows in drop_pools.items():
                try:
                    realm_index = max(0, min(len(REALMS) - 1, int(realm_key)))
                except (TypeError, ValueError):
                    continue
                if not isinstance(rows, list):
                    continue
                cleaned_rows: list[dict[str, Any]] = []
                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    tier_min = str(item.get("tier_min") or item.get("tier") or "")
                    tier_max = str(item.get("tier_max") or item.get("tier") or "")
                    if tier_min not in ARTIFACT_REALM_BOUND_TIERS:
                        tier_min = ""
                    if tier_max not in ARTIFACT_REALM_BOUND_TIERS:
                        tier_max = ""
                    grade = str(item.get("grade") or "")
                    if grade not in GRADE_RANKS:
                        grade = ""
                    attribute = normalize_root_attribute(str(item.get("attribute") or ""))
                    if attribute not in ARTIFACT_ATTRIBUTES:
                        attribute = ""
                    name = str(item.get("name") or "").strip()
                    if name and name not in ARTIFACT_REALM_INFOS_BY_NAME:
                        name = ""
                    tiers = [str(tier) for tier in item.get("tiers", []) if str(tier) in ARTIFACT_REALM_BOUND_TIERS] if isinstance(item.get("tiers"), list) else []
                    try:
                        weight = max(0.01, float(item.get("weight", 1)))
                    except (TypeError, ValueError):
                        weight = 1.0
                    cleaned = {
                        "tier_min": tier_min,
                        "tier_max": tier_max,
                        "grade": grade,
                        "attribute": attribute,
                        "name": name,
                        "weight": weight,
                    }
                    if tiers:
                        cleaned["tiers"] = tiers
                    cleaned_rows.append(cleaned)
                if cleaned_rows:
                    drop_pool_rows[realm_index] = tuple(cleaned_rows)
    mystic_config = config.get("mystic", {}) if isinstance(config, dict) else {}
    signin_config = config.get("signin", {}) if isinstance(config, dict) else {}
    enabled_types = frozenset(MYSTIC_REALM_TYPES)
    enabled_high_risk_types = frozenset(HIGH_RISK_MYSTIC_REALM_TYPES)
    category_weights: dict[str, tuple[tuple[str, float], ...]] = {}
    drop_overrides: dict[str, tuple[dict[str, Any], ...]] = {}
    fishing_option_rate = 0.05
    if isinstance(mystic_config, dict):
        try:
            fishing_option_rate = max(0.0, min(1.0, float(mystic_config.get("fishing_option_rate", 0.05))))
        except (TypeError, ValueError):
            pass
        raw_enabled_types = mystic_config.get("enabled_types")
        if isinstance(raw_enabled_types, list):
            enabled_types = frozenset(
                str(item) for item in raw_enabled_types if str(item) in MYSTIC_REALM_TYPES
            )
        raw_high_risk = mystic_config.get("enabled_high_risk_types")
        if isinstance(raw_high_risk, list):
            enabled_high_risk_types = frozenset(
                str(item) for item in raw_high_risk if str(item) in HIGH_RISK_MYSTIC_REALM_TYPES
            )
        raw_category_weights = mystic_config.get("category_weights")
        if isinstance(raw_category_weights, dict):
            for realm_type, value in raw_category_weights.items():
                pairs = _category_weight_pairs(value)
                if pairs:
                    category_weights[str(realm_type)] = tuple(pairs)
        raw_overrides = mystic_config.get("drop_overrides")
        if isinstance(raw_overrides, dict):
            for realm_type, rewards in raw_overrides.items():
                if isinstance(rewards, list):
                    drop_overrides[str(realm_type)] = tuple(
                        dict(item) for item in rewards if isinstance(item, dict)
                    )
    signin_extra_fishing_rate = 0.10
    if isinstance(signin_config, dict):
        try:
            signin_extra_fishing_rate = max(
                0.0,
                min(1.0, float(signin_config.get("extra_fishing_chance_rate", 0.10))),
            )
        except (TypeError, ValueError):
            pass
    # 一次性替换整个快照：读取方要么看到旧版本、要么看到新版本，永不读到中间态。
    _install_mystic_tuning(
        MysticTuning(
            artifact_drop_pools=drop_pool_rows,
            enabled_types=enabled_types,
            enabled_high_risk_types=enabled_high_risk_types,
            category_weights=category_weights,
            drop_overrides=drop_overrides,
            fishing_option_rate=fishing_option_rate,
            signin_extra_fishing_chance_rate=signin_extra_fishing_rate,
        )
    )

MYSTIC_TOKEN_MAX_COUNT = 3


def grant_mystic_tokens(
    record: UserRecord,
    normal_count: int,
    high_risk_count: int,
) -> dict[str, int]:
    """发放秘境令牌,考虑当前持有量,使每种令牌总数不超过 MYSTIC_TOKEN_MAX_COUNT。"""
    current_normal = _count_token(record, "普通秘境令牌")
    current_high = _count_token(record, "高风险秘境令牌")
    cap = MYSTIC_TOKEN_MAX_COUNT
    granted = {
        "普通秘境令牌": max(0, min(cap - current_normal, int(normal_count))),
        "高风险秘境令牌": max(0, min(cap - current_high, int(high_risk_count))),
    }
    for name, count in granted.items():
        for _ in range(count):
            append_reward(record, mystic_token_reward(name))
    return granted


def _count_token(record: UserRecord, name: str) -> int:
    """统计玩家当前持有的某种令牌数量(不消耗)。"""
    return sum(
        1
        for reward in (record.rewards or [])
        if reward_name(reward) == name
    )
