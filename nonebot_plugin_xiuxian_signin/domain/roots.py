"""domain 灵根子系统（Layer 2）。

由原 domain.py 抽取：灵根抽取、五行补全、丹器灵根、妖丹等。
依赖 Layer 0/1（constants/utils/models/rewards），跨子系统调用通过 _domain 延迟访问。
"""
from __future__ import annotations

from typing import Any, Optional

from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403
from .models import *  # noqa: F401,F403
from .rewards import *  # noqa: F401,F403

_domain = None

def root_default_sources(attribute: str) -> list[str]:
    attribute = normalize_root_attribute(attribute)
    if attribute == "\u5148\u5929\u9053\u4f53":
        return list(BASE_FIVE_ELEMENTS)
    if attribute in BASE_FIVE_ELEMENTS:
        return [attribute]
    if attribute in MUTATION_ROOT_SOURCES:
        return list(random.choice(MUTATION_ROOT_SOURCES[attribute]))
    if attribute in SPECIAL_ROOT_SOURCES:
        return list(SPECIAL_ROOT_SOURCES[attribute])
    return [attribute]

def root_grade_from_score(score: int) -> str:
    if score >= 92:
        return "\u6781\u54c1"
    if score >= 78:
        return "\u4e0a\u54c1"
    if score >= 62:
        return "\u4e2d\u54c1"
    return "\u4e0b\u54c1"

def ordinary_root_rating(purities: Sequence[int]) -> tuple[str, str]:
    values = [max(1, min(100, int(value))) for value in purities] or [50]
    count = len(values)
    avg_purity = sum(values) / count
    max_purity = max(values)
    score = int(avg_purity + (max_purity - avg_purity) * 0.35 - max(0, count - 1) * 8)
    if score >= 92:
        tier = "\u5929\u9636"
    elif score >= 78:
        tier = "\u5730\u9636"
    elif score >= 64:
        tier = "\u7384\u9636"
    elif score >= 48:
        tier = "\u9ec4\u9636"
    else:
        tier = "\u51e1\u54c1"
    return tier, root_grade_from_score(score)

def root_purity_for(tier: str, grade: str, count: int = 1, primary: bool = True, attribute: str = "") -> int:
    if tier == "\u53d8\u5f02\u7075\u6839" or attribute not in BASE_FIVE_ELEMENTS:
        low, high = 94, 100
    else:
        base_ranges = {
            "\u5929\u9636": (88, 100),
            "\u5730\u9636": (76, 92),
            "\u7384\u9636": (62, 82),
            "\u9ec4\u9636": (46, 68),
            "\u51e1\u54c1": (30, 56),
        }
        low, high = base_ranges.get(tier, (45, 72))
        low += GRADE_RANKS.get(grade, 1) * 2
        high += GRADE_RANKS.get(grade, 1) * 2
        penalty = max(0, count - 1) * (7 if primary else 10)
        if not primary:
            low -= 8
            high -= 6
        low -= penalty
        high -= penalty
    return max(18, min(100, random.randint(max(18, low), max(20, high))))

def make_root(
    tier: str,
    grade: str,
    attribute: str,
    purity: Optional[int] = None,
    sources: Optional[list[str]] = None,
    mutated: Optional[bool] = None,
    source_purities: Optional[dict[str, int]] = None,
) -> Root:
    attribute = normalize_root_attribute(attribute)
    source_list = list(sources) if sources is not None else root_default_sources(attribute)
    is_mutated = bool(mutated if mutated is not None else tier == "\u53d8\u5f02\u7075\u6839" or attribute not in BASE_FIVE_ELEMENTS)
    if is_mutated:
        tier = "\u53d8\u5f02\u7075\u6839"
    root_purity = purity if purity is not None else root_purity_for(tier, grade, attribute=attribute)
    if is_mutated:
        root_purity = max(92, int(root_purity))
        source_purities = {source: max(90, int((source_purities or {}).get(source, root_purity))) for source in source_list}
    return Root(
        tier=tier,
        tier_rank=TIER_RANKS[tier],
        grade=grade,
        grade_rank=GRADE_RANKS.get(grade, 1),
        attribute=attribute,
        purity=root_purity,
        sources=source_list,
        mutated=is_mutated,
        trait=ROOT_TRAITS.get(attribute, ""),
        source_purities=source_purities or {},
    )

def draw_mutation_root() -> Root:
    attribute = weighted_choice(
        [
            ("\u96f7", 24),
            ("\u51b0", 20),
            ("\u98ce", 18),
            ("\u6697", 8),
            ("\u5149", 8),
            ("\u5251", 5),
            ("\u836f", 5),
            ("\u7384\u9634", 4),
            ("\u7384\u9633", 4),
            ("\u7a7a", 1.2),
            ("\u65f6", 1.0),
            ("\u5148\u5929\u9053\u4f53", 0.6),
            ("混沌", 0.8),
        ]
    )
    sources = root_default_sources(attribute)
    purity = random.randint(95, 100) if attribute in {"\u7a7a", "\u65f6", "\u5148\u5929\u9053\u4f53", "混沌"} else random.randint(92, 100)
    source_purities = {source: random.randint(max(90, purity - 3), 100) for source in sources}
    grade = root_grade_from_score(purity)
    return make_root("\u53d8\u5f02\u7075\u6839", grade, attribute, purity=purity, sources=sources, mutated=True, source_purities=source_purities)

def ordinary_root_count() -> int:
    return weighted_choice([(1, 11), (2, 24), (3, 32), (4, 23), (5, 10)])

def ordinary_purity_values(count: int) -> list[int]:
    ranges = {
        1: (82, 99),
        2: (68, 92),
        3: (54, 82),
        4: (40, 68),
        5: (28, 58),
    }
    low, high = ranges.get(max(1, min(5, count)), (45, 72))
    values = [random.randint(low, high) for _ in range(count)]
    values.sort(reverse=True)
    return values

def draw_ordinary_roots() -> list[Root]:
    count = ordinary_root_count()
    attributes = random.sample(list(BASE_FIVE_ELEMENTS), k=count)
    purities = ordinary_purity_values(count)
    tier, grade = ordinary_root_rating(purities)
    return [
        make_root(tier, grade, attribute, purity=purity, sources=[attribute], mutated=False, source_purities={attribute: purity})
        for attribute, purity in zip(attributes, purities)
    ]

def draw_roots() -> list[Root]:
    if random.random() < 0.075:
        return [draw_mutation_root()]
    return draw_ordinary_roots()

def draw_root() -> Root:
    return draw_roots()[0]

def normalize_root_profile(record: UserRecord) -> bool:
    if not record.root:
        return False
    changed = False
    roots = record.roots
    mutation_roots = [root for root in roots if root.attribute not in BASE_FIVE_ELEMENTS or root.tier == "\u53d8\u5f02\u7075\u6839" or root.mutated]
    if mutation_roots:
        root = mutation_roots[0]
        root.tier = "\u53d8\u5f02\u7075\u6839"
        root.tier_rank = TIER_RANKS[root.tier]
        root.grade = root.grade if root.grade in GRADE_RANKS else root_grade_from_score(max(92, int(root.purity)))
        root.grade_rank = GRADE_RANKS.get(root.grade, 3)
        root.purity = max(92, int(root.purity or 96))
        root.sources = root.sources or root_default_sources(root.attribute)
        root.source_purities = {source: max(90, int((root.source_purities or {}).get(source, root.purity))) for source in root.sources}
        root.mutated = True
        root.trait = root.trait or ROOT_TRAITS.get(root.attribute, "")
        record.root = root
        if record.extra_roots:
            record.extra_roots = []
            changed = True
        return True or changed

    seen: set[str] = set()
    clean_roots: list[Root] = []
    for root in roots:
        if root.attribute not in BASE_FIVE_ELEMENTS or root.attribute in seen:
            changed = True
            continue
        seen.add(root.attribute)
        root.sources = [root.attribute]
        root.source_purities = {root.attribute: max(1, min(100, int(root.purity or 60)))}
        root.mutated = False
        clean_roots.append(root)
    if not clean_roots:
        clean_roots = [make_root("\u51e1\u54c1", "\u4e0b\u54c1", random.choice(BASE_FIVE_ELEMENTS), purity=45)]
        changed = True
    tier, grade = ordinary_root_rating([int(root.purity) for root in clean_roots])
    for root in clean_roots:
        if root.tier != tier or root.grade != grade:
            changed = True
        root.tier = tier
        root.tier_rank = TIER_RANKS[tier]
        root.grade = grade
        root.grade_rank = GRADE_RANKS[grade]
    record.root = clean_roots[0]
    record.extra_roots = clean_roots[1:]
    return changed

def ensure_legacy_extra_roots(record: UserRecord) -> bool:
    return normalize_root_profile(record)

def max_root_purity(record: UserRecord, attribute: Optional[str] = None) -> int:
    attribute = normalize_root_attribute(attribute) if attribute is not None else None
    if not record.root:
        return 0
    acquired = normalize_acquired_roots(record)
    if attribute is None:
        innate = [int(root.purity) for root in record.roots]
        postnatal = [int(root.get("purity", 0)) for root in acquired]
        return max(innate + postnatal, default=0)
    candidates = []
    for root in record.roots:
        if root.attribute == "先天道体" or root.attribute == attribute or attribute in root.source_attributes:
            if root.source_purities and attribute in root.source_purities:
                candidates.append(int(root.source_purities[attribute]))
            else:
                candidates.append(int(root.purity))
    for root in acquired:
        if root.get("attribute") == attribute:
            candidates.append(int(root.get("purity", 0)))
    return max(candidates, default=0)

def root_purity_multiplier(record: UserRecord, attribute: Optional[str] = None) -> float:
    purity = max_root_purity(record, attribute)
    if purity <= 0:
        return 1.0
    base = 0.85 + purity / 100
    if record.root and record.root.tier == "\u53d8\u5f02\u7075\u6839":
        base += 0.18
    return base

def realm_progress_required(root: Optional[Root], realm_index: int) -> int:
    base = root.progress_required if root is not None else 100
    multiplier = 2 ** max(0, int(realm_index))
    return max(1, int(base) * multiplier)

def cumulative_realm_exp(root: Optional[Root], realm_index: int) -> int:
    return sum(realm_progress_required(root, index) for index in range(max(0, int(realm_index))))

def acquired_root_tier_grade(purity: int) -> tuple[str, str]:
    purity = max(1, min(100, int(purity)))
    if purity >= 88:
        return "\u5730\u9636", "\u6781\u54c1"
    if purity >= 80:
        return "\u5730\u9636", "\u4e0a\u54c1"
    if purity >= 72:
        return "\u5730\u9636", "\u4e2d\u54c1"
    if purity >= 64:
        return "\u7384\u9636", "\u4e0a\u54c1"
    if purity >= 56:
        return "\u7384\u9636", "\u4e2d\u54c1"
    if purity >= 48:
        return "\u9ec4\u9636", "\u4e0a\u54c1"
    if purity >= 40:
        return "\u9ec4\u9636", "\u4e2d\u54c1"
    return "\u51e1\u54c1", "\u4e0b\u54c1"

def normalize_acquired_root(root: dict[str, Any]) -> Optional[dict[str, Any]]:
    kind = str(root.get("kind") or "")
    attribute = str(root.get("attribute") or "")
    if kind not in ACQUIRED_ROOT_KINDS or attribute not in BASE_FIVE_ELEMENTS:
        return None
    max_purity = DAN_ROOT_MAX_PURITY if kind == ACQUIRED_ROOT_DAN else ARTIFACT_ROOT_MAX_PURITY
    purity = max(1, min(max_purity, int(root.get("purity", 1))))
    tier, grade = acquired_root_tier_grade(purity)
    return {
        "kind": kind,
        "attribute": attribute,
        "purity": purity,
        "tier": tier,
        "grade": grade,
        "source_name": str(root.get("source_name") or "\u65e0\u540d\u7075\u7269"),
        "source_tier": str(root.get("source_tier") or "\u51e1\u54c1"),
        "source_grade": str(root.get("source_grade") or "\u4e2d\u54c1"),
        "source_signature": str(root.get("source_signature") or ""),
        "source_uid": str(root.get("source_uid") or ""),
    }

def prune_broken_artifact_roots(record: UserRecord, broken_signature: str = "", broken_uid: str = "") -> int:
    roots = []
    removed = 0
    for raw in record.acquired_roots or []:
        root = normalize_acquired_root(raw) if isinstance(raw, dict) else None
        if root is None:
            continue
        if root.get("kind") == ACQUIRED_ROOT_ARTIFACT:
            signature = str(root.get("source_signature") or "")
            source_uid = str(root.get("source_uid") or "")
            explicitly_broken = bool(
                (broken_uid and source_uid and broken_uid == source_uid)
                or (broken_signature and signature == broken_signature and not source_uid)
            )
            if explicitly_broken or not record_has_artifact_signature(record, signature, source_uid):
                removed += 1
                continue
        roots.append(root)
    record.acquired_roots = roots
    return removed

def normalize_acquired_roots(record: UserRecord) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for raw in record.acquired_roots or []:
        if not isinstance(raw, dict):
            continue
        root = normalize_acquired_root(raw)
        if root is None:
            continue
        if root.get("kind") == ACQUIRED_ROOT_ARTIFACT and not record_has_artifact_signature(
            record,
            str(root.get("source_signature") or ""),
            str(root.get("source_uid") or ""),
        ):
            continue
        old = best.get(str(root["attribute"]))
        if old is None or int(root["purity"]) > int(old.get("purity", 0)):
            best[str(root["attribute"])] = root
    ordered = sorted(best.values(), key=lambda item: BASE_FIVE_ELEMENTS.index(str(item["attribute"])))
    record.acquired_roots = ordered
    return ordered

def acquired_root_attribute_text(root: dict[str, Any]) -> str:
    root = normalize_acquired_root(root) or root
    attribute = str(root.get("attribute") or "")
    return root_attribute_name(attribute)

def acquired_root_display(root: dict[str, Any]) -> str:
    root = normalize_acquired_root(root) or root
    kind = str(root.get("kind") or "后天灵根")
    return (
        f"{acquired_root_attribute_text(root)}（{kind}，{root.get('tier', '')}{root.get('grade', '')}，"
        f"纯度{int(root.get('purity', 0))}%，来源{root.get('source_name', '无名灵物')}）"
    )

def acquired_root_summary(record: UserRecord, limit: int = 2) -> str:
    roots = normalize_acquired_roots(record)
    if not roots:
        return "未炼成"
    shown = [acquired_root_attribute_text(root) for root in roots[:max(1, limit)]]
    if len(roots) > limit:
        shown.append(f"+{len(roots) - limit}条")
    return " / ".join(shown)

def acquired_root_purity_summary(record: UserRecord, limit: int = 8) -> str:
    roots = normalize_acquired_roots(record)
    if not roots:
        return "后天灵根未炼成"
    lines = []
    for root in roots[:max(1, limit)]:
        kind = str(root.get("kind") or "后天灵根")
        lines.append(
            f"{acquired_root_attribute_text(root)}：{int(root.get('purity', 0))}%"
            f"（{kind}，{root.get('tier', '')}{root.get('grade', '')}，来源{root.get('source_name', '无名灵物')}）"
        )
    if len(roots) > limit:
        lines.append(f"另有 {len(roots) - limit} 条后天灵根未显示")
    return "\n".join(lines)

def acquired_root_power_total(record: UserRecord) -> int:
    total = 0
    for root in normalize_acquired_roots(record):
        purity = int(root.get("purity", 0))
        kind_bonus = 160 if root.get("kind") == ACQUIRED_ROOT_DAN else 110
        total += kind_bonus + purity * 4
    return total

def innate_five_elements(record: UserRecord) -> set[str]:
    elements = set()
    for root in record.roots:
        elements.update(attr for attr in root.source_attributes if attr in BASE_FIVE_ELEMENTS)
    return elements

def acquired_root_for_attribute(record: UserRecord, attribute: str) -> Optional[dict[str, Any]]:
    for root in normalize_acquired_roots(record):
        if root.get("attribute") == attribute:
            return root
    return None

def demon_core_realm_name(reward: dict[str, Any]) -> Optional[str]:
    explicit = str(reward.get("beast_realm") or reward.get("demon_realm") or reward.get("source_realm") or "").strip()
    if explicit:
        short = realm_short_name(explicit)
        return DEMON_CORE_REALM_ALIASES.get(short, short if short in DEMON_CORE_EXP_BASE_BY_REALM else explicit)
    name = reward_name(reward)
    for realm_name in sorted(DEMON_CORE_REALM_ALIASES, key=len, reverse=True):
        if realm_name and realm_name in name:
            return DEMON_CORE_REALM_ALIASES[realm_name]
    return DEMON_CORE_DEFAULT_REALM_BY_TIER.get(str(reward.get("tier")), "\u6b8b\u788e")

def is_demon_core_item(reward: dict[str, Any]) -> bool:
    return reward_category(reward) == "\u7075\u6750" and "\u5996\u4e39" in reward_name(reward)

def demon_core_attribute(reward: dict[str, Any]) -> str:
    explicit = str(reward.get("element") or reward.get("attribute") or reward.get("required_attribute") or "")
    if explicit in BASE_FIVE_ELEMENTS:
        return explicit
    hinted = reward_element_hint(reward)
    if hinted in BASE_FIVE_ELEMENTS:
        return hinted
    return stable_choice(BASE_FIVE_ELEMENTS, f"dan-root-attr:{reward_signature(reward)}")

def demon_core_cultivation_exp(reward: dict[str, Any]) -> int:
    explicit = reward.get("cultivation_exp") or reward.get("exp")
    if explicit is not None:
        try:
            return max(1, int(explicit))
        except (TypeError, ValueError):
            pass
    realm_name = demon_core_realm_name(reward) or "\u6b8b\u788e"
    base = DEMON_CORE_EXP_BASE_BY_REALM.get(realm_name, DEMON_CORE_EXP_BASE_BY_REALM["\u6b8b\u788e"])
    tier_ratio = DEMON_CORE_TIER_EXP_RATIO.get(str(reward.get("tier")), 1.0)
    grade_ratio_value = grade_ratio(str(reward.get("grade")))
    return max(1, int(base * tier_ratio * grade_ratio_value))

def demon_core_purity(reward: dict[str, Any]) -> int:
    realm_name = demon_core_realm_name(reward)
    realm_base = DEMON_CORE_REALM_PURITY.get(str(realm_name or ""), 0)
    tier_base = DEMON_CORE_TIER_BASE_PURITY.get(str(reward.get("tier")), 45)
    grade_bonus = GRADE_RANKS.get(str(reward.get("grade")), 1) * 3
    purity = max(realm_base, tier_base) + grade_bonus + random.randint(0, 4)
    return max(25, min(DAN_ROOT_MAX_PURITY, purity))

def artifact_root_attribute(reward: dict[str, Any]) -> Optional[str]:
    required = reward_required_attribute(reward)
    if required in BASE_FIVE_ELEMENTS:
        return required
    hinted = reward_element_hint(reward)
    return hinted if hinted in BASE_FIVE_ELEMENTS else None

def artifact_root_purity(reward: dict[str, Any]) -> int:
    tier_base = ARTIFACT_ROOT_TIER_BASE_PURITY.get(str(reward.get("tier")), 38)
    grade_bonus = GRADE_RANKS.get(str(reward.get("grade")), 1) * 3
    purity = tier_base + grade_bonus + random.randint(0, 4)
    return max(18, min(ARTIFACT_ROOT_MAX_PURITY, purity))

def make_acquired_root(kind: str, attribute: str, purity: int, source: dict[str, Any]) -> dict[str, Any]:
    tier, grade = acquired_root_tier_grade(purity)
    return {
        "kind": kind,
        "attribute": attribute,
        "purity": purity,
        "tier": tier,
        "grade": grade,
        "source_name": reward_name(source),
        "source_tier": str(source.get("tier", "\u51e1\u54c1")),
        "source_grade": str(source.get("grade", "\u4e2d\u54c1")),
        "source_signature": reward_signature(source),
        "source_uid": reward_instance_uid(source),
    }

def add_acquired_root(record: UserRecord, root: dict[str, Any]) -> tuple[bool, str]:
    root = normalize_acquired_root(root) or root
    attribute = str(root.get("attribute") or "")
    if attribute in innate_five_elements(record):
        return False, f"\u4f60\u5df2\u5177\u5907\u5148\u5929{attribute}\u7075\u6839\uff0c\u65e0\u9700\u518d\u70bc\u6210\u540e\u5929\u7075\u6839\u3002"
    roots = normalize_acquired_roots(record)
    old = acquired_root_for_attribute(record, attribute)
    if old and int(old.get("purity", 0)) >= int(root.get("purity", 0)):
        return False, f"\u5df2\u6709\u66f4\u7a33\u7684{acquired_root_display(old)}\uff0c\u6b64\u6b21\u4e0d\u5efa\u8bae\u66ff\u6362\u3002"
    record.acquired_roots = [item for item in roots if item.get("attribute") != attribute]
    record.acquired_roots.append(root)
    normalize_acquired_roots(record)
    if old:
        return True, f"\u540e\u5929\u7075\u6839\u5df2\u66ff\u6362\uff1a{acquired_root_display(old)} -> {acquired_root_display(root)}"
    return True, f"\u540e\u5929\u7075\u6839\u5df2\u70bc\u6210\uff1a{acquired_root_display(root)}"

def refine_dan_root(record: UserRecord, material_index: int) -> tuple[bool, str]:
    if record.root is None:
        return False, "\u5c1a\u672a\u8e0f\u5165\u4fee\u884c\u8def\uff0c\u53d1\u9001\u201c\u7b7e\u5230\u201d\u5148\u89c9\u9192\u7075\u6839\u3002"
    result = reward_position_by_category_index(record, "\u7075\u6750", material_index)
    if result is None:
        return False, "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7f16\u53f7\u7684\u7075\u6750\u3002"
    list_index, material = result
    if not is_demon_core_item(material):
        return False, f"{reward_display_name(material)} \u4e0d\u662f\u5996\u4e39\uff0c\u65e0\u6cd5\u70bc\u6210\u4e39\u7075\u6839\u3002"
    attribute = demon_core_attribute(material)
    purity = demon_core_purity(material)
    new_root = make_acquired_root(ACQUIRED_ROOT_DAN, attribute, purity, material)
    allowed, reason = add_acquired_root(record, new_root)
    if not allowed:
        return False, reason
    if record.rewards is None or list_index >= len(record.rewards):
        return False, "\u7075\u6750\u4f4d\u7f6e\u53d1\u751f\u53d8\u5316\uff0c\u8bf7\u91cd\u65b0\u6253\u5f00\u80cc\u5305\u786e\u8ba4\u7f16\u53f7\u3002"
    consumed = normalize_reward(record.rewards.pop(list_index), record)
    return True, f"\u70bc\u5316 {reward_display_name(consumed)} \u6210\u529f\u3002\n{reason}\n\u4e39\u7075\u6839\u4e3a\u540e\u5929\u6240\u6210\uff0c\u7cbe\u7eaf\u5ea6\u4e0a\u9650\u4e0e\u5730\u7075\u6839\u6301\u5e73\uff0c\u53ef\u7528\u4e8e\u4e94\u884c\u8865\u5168\u3001\u529f\u6cd5\u4e0e\u7075\u5668\u5951\u5408\u3002"

def remove_equipped_artifact_by_signature(record: UserRecord, signature: str, source_uid: str = "") -> None:
    if not signature and not source_uid:
        return
    slots = artifact_slots(record)
    kept = {}
    for slot, item in slots.items():
        item_uid = reward_instance_uid(item)
        if source_uid:
            if item_uid == source_uid or (not item_uid and signature and reward_signature(item) == signature):
                continue
        elif signature and reward_signature(item) == signature:
            continue
        kept[slot] = item
    record.equipped_artifacts = kept
    record.equipped_artifact = kept.get("主手") if kept else None

def refine_artifact_root(record: UserRecord, artifact_index: int) -> tuple[bool, str]:
    if record.root is None:
        return False, "尚未踏入修行路，发送“签到”先觉醒灵根。"
    result = reward_position_by_category_index(record, ARTIFACT_CATEGORY, artifact_index)
    if result is None:
        return False, "没有找到这个编号的灵器。"
    list_index, artifact = result
    attribute = artifact_root_attribute(artifact)
    if attribute is None:
        return False, f"{reward_display_name(artifact)} 没有明确五行适配属性，不能作为器灵根。"
    test_root = make_acquired_root(ACQUIRED_ROOT_ARTIFACT, attribute, artifact_root_purity(artifact), artifact)
    old = acquired_root_for_attribute(record, attribute)
    if attribute in innate_five_elements(record):
        return False, f"你已具备先天{attribute}灵根，无需再炼器为根。"
    if old and int(old.get("purity", 0)) >= int(test_root.get("purity", 0)):
        return False, f"已有更稳的{acquired_root_display(old)}，此次不建议冒险替换。"
    if record.rewards is None or list_index >= len(record.rewards):
        return False, "灵器位置发生变化，请重新打开灵器面板确认编号。"
    source = normalize_reward(record.rewards[list_index], record)
    source_uid = ensure_reward_instance_uid(source)
    record.rewards[list_index] = source
    signature = reward_signature(source)
    if random.random() >= ARTIFACT_ROOT_SUCCESS_RATE:
        destroyed = normalize_reward(record.rewards.pop(list_index), record)
        remove_equipped_artifact_by_signature(record, signature, source_uid)
        prune_broken_artifact_roots(record, signature, source_uid)
        return True, f"祭炼 {reward_display_name(destroyed)} 失败，器纹崩解，灵器已毁。\n器灵根成功率仅 {int(ARTIFACT_ROOT_SUCCESS_RATE * 100)}%，器毁则根无，建议优先使用对应妖丹炼成丹灵根。"
    new_root = make_acquired_root(ACQUIRED_ROOT_ARTIFACT, attribute, artifact_root_purity(source), source)
    allowed, reason = add_acquired_root(record, new_root)
    if not allowed:
        return True, f"祭炼 {reward_display_name(source)} 后，{reason}"
    return True, f"祭炼 {reward_display_name(source)} 成功。\n{reason}\n器灵根依托此器而成：器在则根在，器毁则根无。请勿出售或损毁该灵器。"

def acquired_root_text(record: UserRecord) -> str:
    roots = normalize_acquired_roots(record)
    lines = ["【后天灵根】"]
    if not roots:
        lines.append("当前：未炼成")
    else:
        for index, root in enumerate(roots, start=1):
            lines.append(f"{index}. {acquired_root_attribute_text(root)}")
    lines.append("")
    lines.append("【灵根精纯度】")
    lines.append(acquired_root_purity_summary(record, limit=10))
    missing = [attr for attr in BASE_FIVE_ELEMENTS if attr not in (set(record.root_attributes) & set(BASE_FIVE_ELEMENTS))]
    lines.append("")
    lines.append("【五行状态】")
    lines.append("已齐" if not missing else f"尚缺{'/'.join(missing)}")
    lines.append("")
    lines.append("【炼化方式】")
    lines.append("丹灵根：以对应属性妖丹炼成，精纯度受妖兽修为与妖丹品阶影响，上限与地灵根持平。")
    lines.append(f"器灵根：以灵器适配属性作根，成功率 {int(ARTIFACT_ROOT_SUCCESS_RATE * 100)}%，器在则根在，器毁或出售则灵根失效。")
    lines.append("用法：炼化丹灵根 编号；炼化器灵根 编号。")
    materials = _domain.available_materials(record)
    cores = [item for item in materials if is_demon_core_item(item)]
    if cores:
        lines.append("")
        lines.append("【可用妖丹】")
        for index, item in enumerate(materials, start=1):
            if is_demon_core_item(item):
                lines.append(f"{index}. {reward_display_name(item)} -> {demon_core_attribute(item)}灵根，预估精纯度≤{DAN_ROOT_MAX_PURITY}%")
    artifacts = _domain.available_artifacts(record)
    compatible_artifacts = [(index, item) for index, item in enumerate(artifacts, start=1) if artifact_root_attribute(item)]
    if compatible_artifacts:
        lines.append("")
        lines.append("【可祭炼灵器】")
        for index, item in compatible_artifacts[:8]:
            lines.append(f"{index}. {reward_display_name(item)} -> {artifact_root_attribute(item)}灵根，成功率{int(ARTIFACT_ROOT_SUCCESS_RATE * 100)}%")
    return "\n".join(lines)

def supplemental_root_elements(record: UserRecord) -> dict[str, list[int]]:
    return {attr: [] for attr in BASE_FIVE_ELEMENTS}

def effective_five_elements(record: UserRecord) -> set[str]:
    return set(record.root_attributes) & set(BASE_FIVE_ELEMENTS)

def missing_five_elements(record: UserRecord) -> list[str]:
    return [attr for attr in BASE_FIVE_ELEMENTS if attr not in effective_five_elements(record)]

def needs_five_element_completion(record: UserRecord) -> bool:
    requirement = _domain.current_breakthrough_requirement(record)
    return bool(requirement and _domain.current_breakthrough_target_realm(record) == "炼虚期")

def five_element_requirement_text(record: UserRecord) -> str:
    missing = missing_five_elements(record)
    if not missing:
        return "五行已齐，可感天地元气与空间法则。"
    return (
        f"化神破炼虚需五行合一，当前缺{'/'.join(missing)}。"
        "需先把对应属性妖丹炼成丹灵根，"
        "或借对应属性灵器炼作器灵根补全；单纯持有材料不能直接破关。"
    )

def consume_five_element_supplements(record: UserRecord) -> list[dict[str, Any]]:
    return []

def improve_root_once(root: Root) -> Root:
    if root.tier == "\u53d8\u5f02\u7075\u6839":
        root.purity = min(100, int(root.purity) + random.randint(1, 3))
        if root.source_purities:
            root.source_purities = {key: min(100, int(value) + random.randint(1, 2)) for key, value in root.source_purities.items()}
        root.grade = root_grade_from_score(root.purity)
        root.grade_rank = GRADE_RANKS.get(root.grade, root.grade_rank)
        return root
    new_purity = min(100, int(root.purity) + random.randint(4, 9))
    return make_root(root.tier, root.grade, root.attribute, purity=new_purity, sources=[root.attribute], mutated=False)
