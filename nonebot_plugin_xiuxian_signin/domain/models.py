"""domain 数据类。

由原 domain.py 抽取：9 个 dataclass（Root/UserRecord/SigninResult/CombatRuntimeState 等）。
UserRecord/Root/CombatRuntimeState 的部分 property 反向调用子系统函数，
通过模块级 _domain（由 domain/__init__.py 加载后注入）延迟访问，避免循环导入。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .constants import *  # noqa: F401,F403  # REALMS/ATTRIBUTE_COLORS/TIER_RANKS 等数据
from .utils import *  # noqa: F401,F403  # root_attribute_name 等工具
from .utils import normalize_mystic_settlement_ids

# 由 domain/__init__.py 在导入本模块后注入为 domain 主模块，用于 property 内延迟访问子系统函数。
_domain = None

@dataclass
class Root:
    tier: str
    tier_rank: int
    grade: str
    grade_rank: int
    attribute: str
    purity: int = 100
    sources: Optional[list[str]] = None
    mutated: bool = False
    trait: str = ""
    source_purities: Optional[dict[str, int]] = None

    @property
    def display_name(self) -> str:
        attr_name = root_attribute_name(self.attribute)
        if self.tier == "\u53d8\u5f02\u7075\u6839":
            return f"\u53d8\u5f02\u7075\u6839{self.grade}{attr_name}"
        return f"{self.tier}{self.grade}{attr_name}"

    @property
    def color(self) -> str:
        return ATTRIBUTE_COLORS.get(self.attribute, "#8f8a83")

    @property
    def source_attributes(self) -> set[str]:
        if self.attribute == "\u5148\u5929\u9053\u4f53":
            return set(BASE_FIVE_ELEMENTS)
        sources = set(str(item) for item in (self.sources or []) if item)
        if sources:
            return sources
        if self.attribute in BASE_FIVE_ELEMENTS:
            return {self.attribute}
        if self.attribute in MUTATION_ROOT_SOURCES:
            return set(MUTATION_ROOT_SOURCES[self.attribute][0])
        if self.attribute in SPECIAL_ROOT_SOURCES:
            return set(SPECIAL_ROOT_SOURCES[self.attribute])
        return {self.attribute}

    @property
    def is_mutation(self) -> bool:
        return bool(self.mutated or self.tier == "\u53d8\u5f02\u7075\u6839" or self.attribute not in BASE_FIVE_ELEMENTS)

    @property
    def detail_name(self) -> str:
        suffix = f"\u7eaf\u5ea6{max(1, min(100, int(self.purity)))}%"
        if self.is_mutation and self.sources:
            parts = []
            purities = self.source_purities or {}
            for source in self.sources:
                source_purity = int(purities.get(source, self.purity))
                parts.append(f"{source}{source_purity}%")
            suffix += f"\uff0c\u7531{'+'.join(parts)}\u5148\u5929\u5f02\u53d8"
        return f"{self.display_name}\uff08{suffix}\uff09"

    @property
    def progress_required(self) -> int:
        tier_base = {
            "\u53d8\u5f02\u7075\u6839": 82,
            "\u5929\u9636": 100,
            "\u5730\u9636": 115,
            "\u7384\u9636": 135,
            "\u9ec4\u9636": 155,
            "\u51e1\u54c1": 180,
        }.get(self.tier, 155)
        grade_extra = {
            "\u6781\u54c1": 0,
            "\u4e0a\u54c1": 8,
            "\u4e2d\u54c1": 18,
            "\u4e0b\u54c1": 28,
        }.get(self.grade, 18)
        purity_adjust = int((80 - max(1, min(100, int(self.purity)))) * 0.55)
        return max(55, tier_base + grade_extra + purity_adjust)

    @property
    def exp_gain_range(self) -> tuple[int, int]:
        low = 6 + self.tier_rank * 3 + self.grade_rank
        high = 10 + self.tier_rank * 5 + self.grade_rank * 2
        if self.tier == "\u53d8\u5f02\u7075\u6839":
            low += 3
            high += 6
        purity_bonus = int((max(1, min(100, int(self.purity))) - 70) / 10)
        low = max(1, low + purity_bonus)
        high = max(low, high + purity_bonus * 2)
        return low, high

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "tier_rank": self.tier_rank,
            "grade": self.grade,
            "grade_rank": self.grade_rank,
            "attribute": self.attribute,
            "purity": max(1, min(100, int(self.purity))),
            "sources": list(self.sources or []),
            "mutated": bool(self.is_mutation),
            "trait": self.trait or ROOT_TRAITS.get(self.attribute, ""),
            "source_purities": {str(key): max(1, min(100, int(value))) for key, value in dict(self.source_purities or {}).items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Root:
        tier = str(data["tier"])
        if tier == "\u8def\u4eba\u7532":
            tier = "\u51e1\u54c1"
        attribute = normalize_root_attribute(str(data.get("attribute", "\u91d1")))
        is_mutated = bool(data.get("mutated", False)) or attribute not in BASE_FIVE_ELEMENTS or tier == "\u53d8\u5f02\u7075\u6839"
        if is_mutated:
            tier = "\u53d8\u5f02\u7075\u6839"
        grade = str(data.get("grade", "\u6781\u54c1" if is_mutated else "\u4e2d\u54c1"))
        sources = data.get("sources")
        if not isinstance(sources, list) or not sources:
            sources = _domain.root_default_sources(attribute)
        source_purities = data.get("source_purities")
        if not isinstance(source_purities, dict):
            source_purities = {}
        purity = max(1, min(100, int(data.get("purity", 96 if is_mutated else 72))))
        if is_mutated:
            purity = max(92, purity)
            source_purities = {str(source): max(90, int(source_purities.get(source, purity))) for source in sources}
        return cls(
            tier=tier,
            tier_rank=TIER_RANKS.get(tier, int(data.get("tier_rank", TIER_RANKS.get(tier, 0)))),
            grade=grade,
            grade_rank=int(data.get("grade_rank", GRADE_RANKS.get(grade, 1))),
            attribute=attribute,
            purity=purity,
            sources=[str(item) for item in sources if item],
            mutated=is_mutated,
            trait=str(data.get("trait") or ROOT_TRAITS.get(attribute, "")),
            source_purities={str(key): max(1, min(100, int(value))) for key, value in dict(source_purities).items()},
        )
@dataclass
class EncounterResult:
    happened: bool = False
    success: bool = False
    message: str = ""
    old_root: Optional[Root] = None
    new_root: Optional[Root] = None
    added_root: Optional[Root] = None
@dataclass
class RankReward:
    rank: int
    exp: int
    fishing_chances: int = 0
    pending: bool = False
    leveled_realms: int = 0

    @property
    def label(self) -> str:
        parts = [f"+{self.exp} 修为"]
        if self.fishing_chances:
            parts.append(f"+{self.fishing_chances} 次垂钓")
        if self.pending:
            parts.append("暂存")
        return "，".join(parts)
@dataclass
class DuelResult:
    attacker_power: int
    defender_power: int
    attacker_win: bool
    chance: float
    detail: str

    @property
    def winner_side(self) -> str:
        return "attacker" if self.attacker_win else "defender"
@dataclass
class ExpApplyResult:
    applied: int = 0
    leveled_realms: int = 0
    overflow: int = 0
    spirit_liquid: int = 0

    def __iter__(self):
        yield self.applied
        yield self.leveled_realms
@dataclass
class UserRecord:
    user_id: str
    root: Optional[Root] = None
    acquired_roots: Optional[list[dict[str, Any]]] = None
    sign_count: int = 0
    total_exp: int = 0
    realm_index: int = 0
    realm_exp: int = 0
    last_sign_date: Optional[str] = None
    last_encounter_date: Optional[str] = None
    fishing_chances: int = 0
    pending_fishing: int = 0
    pending_exp: int = 0
    spirit_liquid: int = 0
    bottleneck_days: int = 0
    bottleneck_realm_index: Optional[int] = None
    last_bottleneck_date: Optional[str] = None
    rewards: Optional[list[dict[str, Any]]] = None
    equipped_artifact: Optional[dict[str, Any]] = None
    equipped_artifacts: Optional[dict[str, dict[str, Any]]] = None
    equipped_talisman: Optional[dict[str, Any]] = None
    equipped_method: Optional[dict[str, Any]] = None
    equipped_array: Optional[dict[str, Any]] = None
    equipped_puppet: Optional[dict[str, Any]] = None
    planted_spirit_plant: Optional[dict[str, Any]] = None
    array_proficiency: Optional[dict[str, int]] = None
    array_layers: Optional[dict[str, int]] = None
    spirit_stones: int = 0
    foundation_type: Optional[str] = None
    realm_marks: Optional[dict[str, str]] = None
    extra_roots: Optional[list[Root]] = None
    active_mystic_run_id: Optional[str] = None
    mystic_settlement_ids: Optional[list[str]] = None
    cultivation_lock_until: Optional[str] = None
    cultivation_route: Optional[str] = None
    evil_cultivator: bool = False
    faction_identity: Optional[str] = None
    identity_sign_days: Optional[dict[str, int]] = None
    daily_tasks: Optional[dict[str, Any]] = None
    dual_cultivation_date: Optional[str] = None
    dual_cultivation_used: int = 0
    last_tianji_mystic_date: Optional[str] = None
    combat_race: Optional[str] = None
    physique: Optional[str] = None
    special_abilities: Optional[list[str]] = None
    method_layers: Optional[dict[str, int]] = None
    method_proficiency: Optional[dict[str, int]] = None
    life_artifact: Optional[dict[str, Any]] = None
    immortal_seeds: Optional[list[dict[str, Any]]] = None
    equipped_immortal_seed: Optional[dict[str, Any]] = None
    immortal_conversion_days: int = 0
    last_immortal_conversion_date: Optional[str] = None

    def __post_init__(self) -> None:
        self.active_mystic_run_id = str(self.active_mystic_run_id) if self.active_mystic_run_id else None
        self.mystic_settlement_ids = normalize_mystic_settlement_ids(self.mystic_settlement_ids)

    @property
    def realm_name(self) -> str:
        return REALMS[min(self.realm_index, len(REALMS) - 1)]

    @property
    def realm_stage(self) -> str:
        return _domain.realm_stage(self)

    @property
    def realm(self) -> str:
        return f"{self.realm_name}{self.realm_stage}"

    @property
    def progress_required(self) -> int:
        return _domain.realm_progress_required(self.root, self.realm_index)

    @property
    def roots(self) -> list[Root]:
        result = []
        if self.root:
            result.append(self.root)
        result.extend(self.extra_roots or [])
        return result

    @property
    def root_attributes(self) -> set[str]:
        attrs = {root.attribute for root in self.roots}
        for root in self.roots:
            attrs.update(root.source_attributes)
        for root in _domain.normalize_acquired_roots(self):
            attr = str(root.get("attribute") or "")
            if attr:
                attrs.add(attr)
        return attrs

    @property
    def root_summary(self) -> str:
        if self.root is None:
            return "\u672a\u89c9\u9192\u7075\u6839"
        if self.root.tier == "\u53d8\u5f02\u7075\u6839":
            return f"{self.root.detail_name}\uff5c\u5148\u5929\u5f02\u7980"
        parts = [root.detail_name for root in self.roots]
        return f"{' + '.join(parts)}\uff5c\u4e94\u884c{len(self.roots)}\u7075\u6839\u91cf\u5316\u8bc4\u5b9a"

    @property
    def is_peak_aptitude(self) -> bool:
        return bool(
            self.root
            and (
                (self.root.tier == "\u5929\u9636" and self.root.grade == "\u6781\u54c1")
                or self.root.tier == "\u53d8\u5f02\u7075\u6839"
            )
        )

    @property
    def is_bottleneck(self) -> bool:
        return _domain.is_breakthrough_bottleneck(self)

    @property
    def realm_quality(self) -> str:
        return _domain.realm_quality_text(self)

    @property
    def cultivation_locked(self) -> bool:
        return _domain.is_cultivation_locked(self)

    @property
    def route_summary(self) -> str:
        base = self.cultivation_route or "未选择路线"
        return f"{base}+邪修" if self.evil_cultivator else base

    @property
    def identity_summary(self) -> str:
        return self.faction_identity or "暂无身份"

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "root": self.root.to_dict() if self.root else None,
            "acquired_roots": self.acquired_roots or [],
            "sign_count": self.sign_count,
            "total_exp": self.total_exp,
            "realm_index": self.realm_index,
            "realm_exp": self.realm_exp,
            "last_sign_date": self.last_sign_date,
            "last_encounter_date": self.last_encounter_date,
            "fishing_chances": self.fishing_chances,
            "pending_fishing": self.pending_fishing,
            "pending_exp": self.pending_exp,
            "spirit_liquid": self.spirit_liquid,
            "bottleneck_days": self.bottleneck_days,
            "bottleneck_realm_index": self.bottleneck_realm_index,
            "last_bottleneck_date": self.last_bottleneck_date,
            "rewards": self.rewards or [],
            "equipped_artifact": self.equipped_artifact or None,
            "equipped_artifacts": self.equipped_artifacts or {},
            "equipped_talisman": self.equipped_talisman or None,
            "equipped_method": self.equipped_method or None,
            "equipped_array": self.equipped_array or None,
            "equipped_puppet": self.equipped_puppet or None,
            "planted_spirit_plant": self.planted_spirit_plant or None,
            "array_proficiency": self.array_proficiency or {},
            "array_layers": self.array_layers or {},
            "spirit_stones": self.spirit_stones,
            "foundation_type": self.foundation_type,
            "realm_marks": self.realm_marks or {},
            "extra_roots": [root.to_dict() for root in self.extra_roots or []],
            "active_mystic_run_id": self.active_mystic_run_id,
            "mystic_settlement_ids": normalize_mystic_settlement_ids(self.mystic_settlement_ids),
            "cultivation_lock_until": self.cultivation_lock_until,
            "cultivation_route": self.cultivation_route,
            "evil_cultivator": self.evil_cultivator,
            "faction_identity": self.faction_identity,
            "identity_sign_days": self.identity_sign_days or {},
            "daily_tasks": self.daily_tasks or None,
            "dual_cultivation_date": self.dual_cultivation_date,
            "dual_cultivation_used": self.dual_cultivation_used,
            "last_tianji_mystic_date": self.last_tianji_mystic_date,
            "combat_race": self.combat_race,
            "physique": self.physique,
            "special_abilities": self.special_abilities or [],
            "method_layers": self.method_layers or {},
            "method_proficiency": self.method_proficiency or {},
            "life_artifact": self.life_artifact or None,
            "immortal_seeds": self.immortal_seeds or [],
            "equipped_immortal_seed": self.equipped_immortal_seed or None,
            "immortal_conversion_days": self.immortal_conversion_days,
            "last_immortal_conversion_date": self.last_immortal_conversion_date,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserRecord:
        root_data = data.get("root")
        return cls(
            user_id=str(data["user_id"]),
            root=Root.from_dict(root_data) if root_data else None,
            acquired_roots=[
                dict(root)
                for root in data.get("acquired_roots", [])
                if isinstance(root, dict)
            ],
            sign_count=int(data.get("sign_count", 0)),
            total_exp=int(data.get("total_exp", 0)),
            realm_index=int(data.get("realm_index", 0)),
            realm_exp=int(data.get("realm_exp", 0)),
            last_sign_date=data.get("last_sign_date"),
            last_encounter_date=data.get("last_encounter_date"),
            fishing_chances=int(data.get("fishing_chances", 0)),
            pending_fishing=int(data.get("pending_fishing", 0)),
            pending_exp=int(data.get("pending_exp", 0)),
            spirit_liquid=int(data.get("spirit_liquid", 0)),
            bottleneck_days=int(data.get("bottleneck_days", 0)),
            bottleneck_realm_index=(
                int(data["bottleneck_realm_index"])
                if data.get("bottleneck_realm_index") is not None
                else None
            ),
            last_bottleneck_date=(str(data["last_bottleneck_date"]) if data.get("last_bottleneck_date") else None),
            rewards=list(data.get("rewards", [])),
            spirit_stones=int(data.get("spirit_stones", 0)),
            active_mystic_run_id=(
                str(data["active_mystic_run_id"])
                if data.get("active_mystic_run_id")
                else None
            ),
            mystic_settlement_ids=normalize_mystic_settlement_ids(
                data.get("mystic_settlement_ids")
            ),
            cultivation_lock_until=(str(data["cultivation_lock_until"]) if data.get("cultivation_lock_until") else None),
            cultivation_route=(str(data["cultivation_route"]) if data.get("cultivation_route") else None),
            evil_cultivator=bool(data.get("evil_cultivator", False)),
            faction_identity=(str(data["faction_identity"]) if data.get("faction_identity") else None),
            identity_sign_days={
                str(key): int(value)
                for key, value in dict(data.get("identity_sign_days", {})).items()
            },
            daily_tasks=(dict(data["daily_tasks"]) if isinstance(data.get("daily_tasks"), dict) else None),
            dual_cultivation_date=(str(data["dual_cultivation_date"]) if data.get("dual_cultivation_date") else None),
            dual_cultivation_used=int(data.get("dual_cultivation_used", 0)),
            last_tianji_mystic_date=(str(data["last_tianji_mystic_date"]) if data.get("last_tianji_mystic_date") else None),
            combat_race=(str(data["combat_race"]) if data.get("combat_race") else None),
            physique=(str(data["physique"]) if data.get("physique") else None),
            special_abilities=[str(item) for item in (data.get("special_abilities") or []) if item],
            method_layers={
                str(key): int(value)
                for key, value in dict(data.get("method_layers") or {}).items()
            },
            method_proficiency={
                str(key): int(value)
                for key, value in dict(data.get("method_proficiency") or {}).items()
            },
            equipped_artifacts={
                str(key): dict(value)
                for key, value in dict(data.get("equipped_artifacts") or {}).items()
                if isinstance(value, dict)
            },
            equipped_talisman=(
                dict(data["equipped_talisman"])
                if isinstance(data.get("equipped_talisman"), dict)
                else None
            ),
            equipped_artifact=(
                dict(data["equipped_artifact"])
                if isinstance(data.get("equipped_artifact"), dict)
                else None
            ),
            equipped_method=(
                dict(data["equipped_method"])
                if isinstance(data.get("equipped_method"), dict)
                else None
            ),
            equipped_array=(
                dict(data["equipped_array"])
                if isinstance(data.get("equipped_array"), dict)
                else None
            ),
            equipped_puppet=(
                dict(data["equipped_puppet"])
                if isinstance(data.get("equipped_puppet"), dict)
                else None
            ),
            planted_spirit_plant=(
                dict(data["planted_spirit_plant"])
                if isinstance(data.get("planted_spirit_plant"), dict)
                else None
            ),
            array_proficiency={
                str(key): int(value)
                for key, value in dict(data.get("array_proficiency", {})).items()
            },
            array_layers={
                str(key): int(value)
                for key, value in dict(data.get("array_layers", {})).items()
            },
            foundation_type=(
                str(data["foundation_type"])
                if data.get("foundation_type")
                else None
            ),
            realm_marks={
                str(key): str(value)
                for key, value in dict(data.get("realm_marks", {})).items()
            },
            extra_roots=[
                Root.from_dict(root)
                for root in data.get("extra_roots", [])
                if isinstance(root, dict)
            ],
            life_artifact=(dict(data["life_artifact"]) if isinstance(data.get("life_artifact"), dict) else None),
            immortal_seeds=[dict(item) for item in data.get("immortal_seeds", []) if isinstance(item, dict)],
            equipped_immortal_seed=(dict(data["equipped_immortal_seed"]) if isinstance(data.get("equipped_immortal_seed"), dict) else None),
            immortal_conversion_days=int(data.get("immortal_conversion_days", 0)),
            last_immortal_conversion_date=(str(data["last_immortal_conversion_date"]) if data.get("last_immortal_conversion_date") else None),
        )
@dataclass
class SigninResult:
    record: UserRecord
    is_first: bool
    already_signed: bool
    gained_exp: int = 0
    pending_exp_applied: int = 0
    method_bonus_exp: int = 0
    item_bonus_exp: int = 0
    overflow_exp: int = 0
    spirit_liquid_gain: int = 0
    bottleneck_days: int = 0
    leveled_realms: int = 0
    gained_fishing_chance: bool = False
    fishing_chances_gained: int = 0
    encounter: Optional[EncounterResult] = None
    breakthrough_reward: Optional[dict[str, Any]] = None
    lock_message: str = ""
    daily_tasks: Optional[list[dict[str, Any]]] = None
@dataclass(frozen=True)
class CombatRuntimeState:
    hp: int
    max_hp: int
    mana: int
    max_mana: int
    cooldowns: dict[str, int]
    turn: int = 0
    triggered_abilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cooldowns",
            {str(key): int(value) for key, value in self.cooldowns.items()},
        )

    @classmethod
    def initial(cls, record: UserRecord) -> "CombatRuntimeState":
        max_hp = _domain.combat_max_hp(record)
        max_mana = _domain.combat_max_mana(record)
        return cls(
            hp=max_hp,
            max_hp=max_hp,
            mana=max_mana,
            max_mana=max_mana,
            cooldowns={},
        )
@dataclass(frozen=True)
class CombatActionOutcome:
    state: CombatRuntimeState
    damage: int
    defense: int
    speed: int
    triggered: tuple[str, ...]
    logs: tuple[str, ...]
