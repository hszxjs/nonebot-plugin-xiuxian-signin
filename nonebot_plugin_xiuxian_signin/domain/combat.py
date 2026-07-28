"""domain combat 子系统。

由原 domain.py 抽取。依赖 Layer 0+ 已提取子系统，跨子系统调用通过 _domain 延迟访问。
"""
from __future__ import annotations

import hashlib
import random
import re
import uuid
from datetime import date, datetime, timedelta
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

def has_soul_insight(record: UserRecord) -> bool:
    profile = method_profile(record.equipped_method, record)
    return bool(profile.get("soul_insight"))

def combat_root_text(record: UserRecord) -> str:
    return record.root_summary if record.root else "\u672a\u89c9\u9192\u7075\u6839"

def ensure_combat_profile(record: UserRecord) -> bool:
    changed = False
    if not record.combat_race:
        record.combat_race = weighted_choice_stable(COMBAT_RACES, f"race:{record.user_id}")
        changed = True
    if not record.physique:
        record.physique = weighted_choice_stable(COMBAT_PHYSIQUES, f"physique:{record.user_id}")
        changed = True
    abilities = normalize_special_abilities(record.special_abilities)
    if abilities != list(record.special_abilities or []):
        record.special_abilities = abilities
        changed = True
    if record.method_layers is None:
        record.method_layers = {}
        changed = True
    return changed

def physique_hp_multiplier(physique: Optional[str]) -> float:
    return {
        "\u51e1\u4f53": 1.0,
        "\u77f3\u7334\u5e9f\u8109": 0.94,
        "远荒战体": 1.28,
        "先天道胚": 1.12,
        "玄阴灵体": 1.1,
        "赤阳灵体": 1.12,
        "青华灵体": 1.15,
        "金羽神脉": 1.08,
        "身界蕴种": 1.22,
        "浑元战魔体": 1.34,
    }.get(str(physique), 1.0)

def method_physique_multiplier(record: UserRecord, profile: dict[str, Any]) -> float:
    physique = record.physique or ""
    name = str(profile.get("name", ""))
    if not physique or not name:
        return 1.0
    pairs = (
        ("远荒战体", ("\u91d1\u8eab", "\u4e0d\u706d", "\u953b\u4f53")),
        ("浑元战魔体", ("\u6df7\u6c8c", "\u4e07\u8c61", "空衡")),
        ("青华灵体", ("\u9752\u83b2", "\u957f\u751f", "\u4e07\u7075")),
        ("玄阴灵体", ("玄阴", "\u7384\u51b0", "\u5bd2")),
        ("赤阳灵体", ("赤阳", "\u771f\u706b", "\u79bb\u706b")),
    )
    for body, tokens in pairs:
        if physique == body and any(token in name for token in tokens):
            return 1.35
    return 1.0

def combat_max_hp(record: UserRecord) -> int:
    ensure_combat_profile(record)
    profile = method_profile(record.equipped_method, record)
    base = 900 + record.realm_index * 420 + max(0, record.realm_exp) * 3 + record.sign_count * 12
    base += int(battle_power(record) * 0.08)
    hp_bonus = int(profile.get("hp_bonus", 0) * method_physique_multiplier(record, profile))
    return max(500, int((base + hp_bonus) * physique_hp_multiplier(record.physique)))

def realm_quality_mana_multiplier(record: UserRecord) -> float:
    quality = realm_quality_text(record)
    if not quality:
        return 1.0
    if quality in {"\u5929\u9053\u7b51\u57fa", "\u5b8c\u7f8e\u9053\u57fa"}:
        return 1.28
    if quality == "\u4f18\u79c0\u7b51\u57fa":
        return 1.18
    if quality == "\u826f\u597d\u7b51\u57fa":
        return 1.1
    if "\u4e00\u54c1" in quality:
        return 1.30
    if "\u4e8c\u54c1" in quality:
        return 1.24
    if "\u4e09\u54c1" in quality:
        return 1.18
    if "\u56db\u54c1" in quality:
        return 1.12
    if "\u4e94\u54c1" in quality:
        return 1.06
    if any(token in quality for token in ("\u5929\u9053", "\u6df7\u5143", "\u65e0\u6781", "\u8d85\u8131", "\u6c38\u6052")):
        return 1.32
    if any(token in quality for token in ("\u9053", "\u5723", "\u4ed9", "\u771f")):
        return 1.18
    return 1.0

def combat_max_mana(record: UserRecord) -> int:
    ensure_combat_profile(record)
    root_bonus = 0
    if record.root:
        root_bonus = record.root.tier_rank * 42 + record.root.grade_rank * 28
    realm_bonus = record.realm_index * 185 + int(max(0, record.realm_exp) * 1.4)
    sign_bonus = min(420, record.sign_count * 4)
    base = 220 + realm_bonus + root_bonus + sign_bonus + int(realm_quality_power(record) * 0.12)
    profile = method_profile(record.equipped_method, record)
    if profile.get("kind") == "\u795e\u9b42\u7c7b":
        base = int(base * 1.12)
    if profile.get("kind") == "\u6218\u6280\u7c7b":
        base = int(base * 1.06)
    if record.realm_index >= true_immortal_realm_index():
        base = int(base * 1.18)
    return max(120, int(base * realm_quality_mana_multiplier(record)))

def available_battle_techniques(record: UserRecord) -> list[str]:
    profile = method_profile(record.equipped_method, record)
    techniques = list(profile.get("techniques") or [])
    if profile.get("required_race") and profile.get("required_race") != record.combat_race:
        techniques = techniques[:1]
    if not techniques and record.root:
        techniques = ATTRIBUTE_TECHNIQUE_NAMES.get(record.root.attribute, [])[:1]
    return techniques

def technique_power(record: UserRecord, technique: str, improvised: bool = False) -> int:
    profile = method_profile(record.equipped_method, record)
    layer = int(profile.get("layer", 0))
    base = max(20, int(battle_power(record) * (0.055 + layer * 0.006)))
    if profile.get("kind") == "\u6218\u6280\u7c7b":
        base = int(base * 1.22)
    if improvised:
        base = int(base * 0.72)
    return max(12, base)

def technique_mana_cost(record: UserRecord, technique: str, improvised: bool = False) -> int:
    profile = method_profile(record.equipped_method, record)
    layer = int(profile.get("layer", 1))
    tech_seed = stable_int(f"mana-cost:{technique}") % 19
    base = 34 + record.realm_index * 9 + layer * 7 + tech_seed
    if profile.get("kind") == "\u6218\u6280\u7c7b":
        base = int(base * 1.12)
    if improvised:
        base = int(base * 0.78)
    return max(18, base)

def technique_cooldown(technique: str, improvised: bool = False) -> int:
    base = 2 + stable_int(f"tech-cd:{technique}") % 4
    if improvised:
        base = max(1, base - 1)
    return base

def physical_attack_power(record: UserRecord) -> int:
    return max(10, int(battle_power(record) * (0.05 + min(0.035, record.realm_index * 0.002))))

def physique_trait_power(record: UserRecord) -> int:
    trait = PHYSIQUE_TRAIT_NAMES.get(str(record.physique or ""))
    if not trait:
        return 0
    return max(18, int(battle_power(record) * (0.075 + record.realm_index * 0.003)))

def combat_special_power(record: UserRecord, ability: str, kind: str) -> tuple[int, int, int, str]:
    power = battle_power(record)
    info = special_ability_info(ability)
    damage_rate, defense_rate, speed_bonus = info.get("combat", (0.08, 0.04, 0))
    multiplier = nine_secret_set_multiplier(record) if kind == "secret" else 1
    damage = int(power * float(damage_rate) * multiplier)
    defense = int(power * float(defense_rate) * multiplier)
    speed = int(speed_bonus) * multiplier
    rarity = special_ability_rarity_text(ability)
    if ability in FORBIDDEN_REALM_ABILITIES:
        return damage, defense, speed, f"触发{rarity}【{ability}】，限界气机展开。"
    if kind == "secret":
        return damage, defense, speed, f"触发{rarity}【{ability}】，星律共鸣共鸣{multiplier}倍，已悟星律同步增强{multiplier}倍。"
    return damage, defense, speed, f"触发{rarity}神通【{ability}】：{info.get('effect', '神通气机展开。')}"

def sanitize_combat_text(text: str) -> str:
    return re.sub(r"[\s,\u002c\u3001\uff0c\u3002.!\uff01\?\uff1f:\uff1a;\[\]\uff08\uff09()]+", "", str(text or ""))

def _combat_action_baseline(record: UserRecord) -> dict[str, Any]:
    equipped_talisman = record.equipped_talisman
    equipped_talisman_power = talisman_power(equipped_talisman, record)
    equipped_talisman_name_text = equipped_talisman_name(record) if equipped_talisman_power > 0 else ""
    damage = int(battle_power(record) * 0.18)
    defense = int(battle_power(record) * 0.045)
    logs: list[str] = []
    if equipped_talisman_power > 0:
        damage += int(equipped_talisman_power * 0.72)
        defense += int(equipped_talisman_power * 0.52)
        logs.append(f"\u7b26\u7b93\u680f\u3010{equipped_talisman_name_text}\u3011\u62a4\u6301\u672c\u573a\u6597\u6cd5\uff0c\u4e0d\u6d88\u8017")
    elif equipped_talisman:
        logs.append(f"\u7b26\u7b93\u680f\u3010{equipped_talisman_name(record)}\u3011\u54c1\u9636\u8fc7\u9ad8\uff0c\u5f53\u524d\u5883\u754c\u5c1a\u65e0\u6cd5\u50ac\u52a8")
    return {
        "damage": damage,
        "defense": defense,
        "logs": logs,
        "talisman": equipped_talisman_name_text or equipped_talisman_name(record),
        "talisman_power": equipped_talisman_power,
    }

def _merge_triggered_abilities(
    existing: Sequence[str], newly_triggered: Any
) -> tuple[str, ...]:
    """合并本回合新触发的技能，保持首次触发顺序并去重。

    triggered_abilities 的语义是“本次战斗已触发过的技能集合”，多处仅以
    ``ability in triggered_abilities`` 判断是否曾触发，不依赖重复计数。
    但战斗状态序列化（mystic_battle._string_list）要求元素唯一，故在此从
    写入端保证不出现重复，避免同一技能跨回合重复触发后恢复存档时报错。
    """
    merged: list[str] = list(existing)
    seen = set(existing)
    for item in newly_triggered or []:
        name = str(item)
        if not name or name in seen:
            continue
        seen.add(name)
        merged.append(name)
    return tuple(merged)


def _evaluate_one_combat_action(
    record: UserRecord,
    action_text: str,
    mana: int,
    cooldowns: dict[str, int],
    seed: str,
    *,
    include_baseline: bool,
    already_triggered: tuple[str, ...] = (),
) -> dict[str, Any]:
    ensure_combat_profile(record)
    available = available_battle_techniques(record)
    abilities = normalize_special_abilities(record.special_abilities)
    text = sanitize_combat_text(action_text)
    baseline = _combat_action_baseline(record)
    triggered: list[str] = []
    logs = list(baseline["logs"]) if text and include_baseline else []
    damage = int(baseline["damage"]) if text and include_baseline else 0
    defense = int(baseline["defense"]) if text and include_baseline else 0
    speed = 0
    mana_spent = 0
    physical_hits = 0
    trait_triggers = 0

    next_cooldowns = dict(cooldowns)

    def use_physical(reason: str = "") -> None:
        nonlocal damage, physical_hits
        physical_hits += 1
        damage += physical_attack_power(record)
        suffix = f"\uff0c{reason}" if reason else ""
        logs.append(f"\u6539\u4ee5\u8fd1\u8eab\u653b\u4f10{suffix}")

    def maybe_use_trait(reason: str = "") -> bool:
        nonlocal damage, defense, speed, trait_triggers
        trait = PHYSIQUE_TRAIT_NAMES.get(str(record.physique or ""))
        if not trait:
            return False
        trait_triggers += 1
        bonus = physique_trait_power(record)
        damage += bonus
        defense += int(bonus * 0.35)
        if str(record.physique or "") == "金羽神脉":
            speed += 6
        suffix = f"\uff0c{reason}" if reason else ""
        logs.append(f"\u4f53\u8d28\u7279\u6027\u3010{trait}\u3011\u81ea\u884c\u590d\u82cf{suffix}")
        return True

    def cast_technique(tech: str, improvised: bool = False) -> bool:
        nonlocal mana, mana_spent, damage
        cd_left = int(next_cooldowns.get(tech, 0))
        if cd_left > 0:
            logs.append(f"\u6218\u6280\u3010{tech}\u3011\u5c1a\u9700{cd_left}\u606f\u56de\u6c14")
            use_physical("\u6218\u6280\u672a\u51b7\u5374")
            return False
        cost = technique_mana_cost(record, tech, improvised)
        if mana < cost:
            logs.append(f"\u7075\u529b\u4e0d\u8db3\uff0c\u3010{tech}\u3011\u9700{cost}\u70b9\u7075\u529b")
            if not maybe_use_trait("\u7075\u529b\u89c1\u5e95"):
                use_physical("\u7075\u529b\u89c1\u5e95")
            return False
        mana -= cost
        mana_spent += cost
        next_cooldowns[tech] = technique_cooldown(tech, improvised)
        damage += technique_power(record, tech, improvised=improvised)
        triggered.append(tech)
        if improvised:
            logs.append(
                f"\u5373\u5174\u672f\u5f0f\u7275\u52a8\u3010{tech}\u3011\uff0c\u7075\u529b-{cost}\uff0cCD{next_cooldowns[tech]}\u606f"
            )
        else:
            logs.append(
                f"\u65bd\u5c55\u6218\u6280\u3010{tech}\u3011\uff0c\u7075\u529b-{cost}\uff0cCD{next_cooldowns[tech]}\u606f"
            )
        return True

    if text:
        matched = [tech for tech in available if sanitize_combat_text(tech) and sanitize_combat_text(tech) in text]
        if not matched:
            matched = [tech for tech in GENERAL_TECHNIQUE_NAMES if sanitize_combat_text(tech) in text]
        used_special = False
        forbidden_terms = {
            "归极域": "归极域",
            "开启归极": "归极域",
            "归极": "归极域",
            "重阈": "重阈",
            "开启重阈": "重阈",
            "初阈": "初阈",
            "开启初阈": "初阈",
        }
        requested_forbidden = None
        for term, canonical in forbidden_terms.items():
            if term in text:
                requested_forbidden = canonical
                break
        if requested_forbidden:
            used_special = True
            owned_forbidden = highest_forbidden_ability(abilities)
            if not owned_forbidden:
                logs.append("尚未领悟限界，强行开启只惊起一缕战意。")
            elif forbidden_rank(owned_forbidden) < forbidden_rank(requested_forbidden):
                logs.append(f"尝试开启【{requested_forbidden}】失败，当前只能维持【{owned_forbidden}】。")
            else:
                add_damage, add_defense, add_speed, message = combat_special_power(record, owned_forbidden, "forbidden")
                damage += add_damage
                defense += add_defense
                speed += add_speed
                triggered.append(owned_forbidden)
                logs.append(message)
        if "星律" in text or any(secret.split("-", 1)[-1] in text for secret in abilities if secret.startswith("星律")):
            secrets = [secret for secret in abilities if secret.startswith("星律")]
            used_special = True
            if secrets:
                secret = stable_choice(secrets, f"secret:{seed}:{text}")
                add_damage, add_defense, add_speed, message = combat_special_power(record, secret, "secret")
                damage += add_damage
                defense += add_defense
                speed += add_speed
                triggered.append(secret)
                logs.append(message)
            else:
                logs.append("尚未悟得星律残篇，天机一闪而逝。")
        for ability in abilities:
            if (
                ability in already_triggered
                or ability in triggered
                or ability in FORBIDDEN_REALM_ABILITIES
                or ability.startswith("星律")
            ):
                continue
            info = special_ability_info(ability)
            terms = [ability, *list(info.get("aliases", []) or [])]
            if not any(sanitize_combat_text(term) and sanitize_combat_text(term) in text for term in terms):
                continue
            used_special = True
            add_damage, add_defense, add_speed, message = combat_special_power(record, ability, "generic")
            damage += add_damage
            defense += add_defense
            speed += add_speed
            triggered.append(ability)
            logs.append(message)
            break
        if matched:
            for tech in matched[:2]:
                cast_technique(tech)
        elif not used_special:
            if available and mana > 0:
                choice_seed = f"improv:{seed}:{text}:{len(already_triggered) + len(triggered)}"
                cast_technique(stable_choice(available, choice_seed), improvised=True)
            elif mana <= 0:
                if not maybe_use_trait("\u7075\u529b\u8017\u5c3d"):
                    use_physical("\u7075\u529b\u8017\u5c3d")
            else:
                use_physical("\u5373\u5174\u672f\u5f0f\u672a\u6210")
    return {
        "damage": damage,
        "defense": defense,
        "speed": speed,
        "triggered": list(dict.fromkeys(triggered)),
        "logs": logs,
        "mana": max(0, mana),
        "mana_spent": mana_spent,
        "cooldowns": next_cooldowns,
        "physical_hits": physical_hits,
        "trait_triggers": trait_triggers,
        "talisman": str(baseline["talisman"]),
        "talisman_power": int(baseline["talisman_power"]),
    }

def resolve_combat_action(
    record: UserRecord,
    action_text: str,
    state: CombatRuntimeState,
    seed: str,
) -> CombatActionOutcome:
    action_is_effective = bool(sanitize_combat_text(action_text))
    next_cooldowns = {
        name: max(0, int(value) - 1)
        for name, value in state.cooldowns.items()
        if int(value) > 1
    }
    result = _evaluate_one_combat_action(
        record=record,
        action_text=action_text,
        mana=state.mana,
        cooldowns=next_cooldowns,
        seed=seed,
        include_baseline=state.turn == 0,
        already_triggered=state.triggered_abilities,
    )
    next_state = CombatRuntimeState(
        hp=state.hp,
        max_hp=state.max_hp,
        mana=max(0, int(result["mana"])),
        max_mana=state.max_mana,
        cooldowns={str(key): int(value) for key, value in dict(result["cooldowns"]).items()},
        turn=state.turn + int(action_is_effective),
        triggered_abilities=_merge_triggered_abilities(
            state.triggered_abilities, result["triggered"]
        ),
    )
    return CombatActionOutcome(
        state=next_state,
        damage=int(result["damage"]),
        defense=int(result["defense"]),
        speed=int(result["speed"]),
        triggered=tuple(str(item) for item in result["triggered"]),
        logs=tuple(str(item) for item in result["logs"]),
    )

def evaluate_combat_actions(record: UserRecord, actions: Sequence[dict[str, Any]], side_seed: str = "") -> dict[str, Any]:
    state = CombatRuntimeState.initial(record)
    outcomes: list[CombatActionOutcome] = []
    for index, action in enumerate(list(actions)[:8], start=1):
        action_text = str(action.get("text", ""))
        outcome = resolve_combat_action(record, action_text, state, f"{side_seed}:{index}")
        if sanitize_combat_text(action_text):
            outcomes.append(outcome)
        state = outcome.state

    if outcomes:
        damage = sum(outcome.damage for outcome in outcomes)
        defense = sum(outcome.defense for outcome in outcomes)
        speed = sum(outcome.speed for outcome in outcomes)
        triggered = [item for outcome in outcomes for item in outcome.triggered]
        logs = [item for outcome in outcomes for item in outcome.logs]
    else:
        baseline = _combat_action_baseline(record)
        damage = max(1, int(baseline["damage"]))
        defense = max(0, int(baseline["defense"]))
        speed = 0
        triggered = []
        logs = [str(item) for item in baseline["logs"]]

    equipped_talisman_power = talisman_power(record.equipped_talisman, record)
    equipped_talisman_name_text = equipped_talisman_name(record) if equipped_talisman_power > 0 else ""
    return {
        "damage": max(1, damage),
        "defense": max(0, defense),
        "speed": speed,
        "triggered": list(dict.fromkeys(triggered)),
        "logs": logs[:8],
        "mana": state.mana,
        "max_mana": state.max_mana,
        "mana_spent": max(0, state.max_mana - state.mana),
        "cooldowns": dict(state.cooldowns),
        "physical_hits": sum(log.startswith("\u6539\u4ee5\u8fd1\u8eab\u653b\u4f10") for log in logs),
        "trait_triggers": sum(log.startswith("\u4f53\u8d28\u7279\u6027\u3010") for log in logs),
        "talisman": equipped_talisman_name_text or equipped_talisman_name(record),
        "talisman_power": equipped_talisman_power,
    }

def normal_duel_fighter(record: UserRecord, nickname: str, actions: Sequence[dict[str, Any]], side_seed: str) -> dict[str, Any]:
    ensure_combat_profile(record)
    profile = method_profile(record.equipped_method, record)
    action_result = evaluate_combat_actions(record, actions, side_seed)
    return {
        "user_id": record.user_id,
        "nickname": nickname or f"QQ {record.user_id}",
        "power": battle_power(record),
        "realm": record.realm if record.root else "\u672a\u5165\u95e8",
        "root": combat_root_text(record),
        "race": record.combat_race or "\u672a\u8bb0\u5f55",
        "physique": record.physique or "\u672a\u8bb0\u5f55",
        "abilities": normalize_special_abilities(record.special_abilities),
        "method": profile.get("display", "\u672a\u53c2\u609f\u529f\u6cd5"),
        "method_kind": profile.get("kind", "\u65e0"),
        "talisman": action_result.get("talisman", equipped_talisman_name(record)),
        "talisman_power": int(action_result.get("talisman_power", talisman_power(record.equipped_talisman, record))),
        "available_techniques": available_battle_techniques(record),
        "triggered_techniques": action_result["triggered"],
        "logs": action_result["logs"],
        "damage": int(action_result["damage"]),
        "defense": int(action_result["defense"]),
        "speed": int(action_result["speed"]),
        "mana": int(action_result.get("mana", 0)),
        "max_mana": int(action_result.get("max_mana", combat_max_mana(record))),
        "mana_spent": int(action_result.get("mana_spent", 0)),
        "cooldowns": dict(action_result.get("cooldowns", {})),
        "physical_hits": int(action_result.get("physical_hits", 0)),
        "trait_triggers": int(action_result.get("trait_triggers", 0)),
        "max_hp": combat_max_hp(record),
        "hp": combat_max_hp(record),
    }

def simulate_normal_duel(
    left: UserRecord,
    right: UserRecord,
    left_name: str,
    right_name: str,
    left_actions: Sequence[dict[str, Any]],
    right_actions: Sequence[dict[str, Any]],
    duration_seconds: int = 60,
) -> dict[str, Any]:
    left_fighter = normal_duel_fighter(left, left_name, left_actions, f"{left.user_id}:{right.user_id}:left")
    right_fighter = normal_duel_fighter(right, right_name, right_actions, f"{right.user_id}:{left.user_id}:right")
    left_output = max(1, int(left_fighter["damage"] - right_fighter["defense"] * 0.55))
    right_output = max(1, int(right_fighter["damage"] - left_fighter["defense"] * 0.55))
    left_fighter["dealt_damage"] = 0
    right_fighter["dealt_damage"] = 0
    left_fighter["raw_output"] = left_output
    right_fighter["raw_output"] = right_output

    left_initiative = (
        int(left_fighter["speed"]),
        int(left_fighter["power"]),
        stable_int(f"initiative:{left.user_id}:{right.user_id}") % 100,
    )
    right_initiative = (
        int(right_fighter["speed"]),
        int(right_fighter["power"]),
        stable_int(f"initiative:{right.user_id}:{left.user_id}") % 100,
    )
    if left_initiative >= right_initiative:
        attack_order = [(left_fighter, right_fighter, left_output), (right_fighter, left_fighter, right_output)]
    else:
        attack_order = [(right_fighter, left_fighter, right_output), (left_fighter, right_fighter, left_output)]

    ended_early = False
    elapsed_seconds = duration_seconds
    finisher: Optional[dict[str, Any]] = None
    timeline: list[str] = []
    first_attacker, first_defender, _ = attack_order[0]
    timeline.append(
        f"{first_attacker['nickname']}\u51ed\u901f\u5ea6\u62a2\u5230\u5148\u624b\uff0c{first_defender['nickname']}\u88ab\u8feb\u8f6c\u5165\u5b88\u52bf\u3002"
    )
    for turn_index, (attacker, defender, output) in enumerate(attack_order, start=1):
        before_hp = max(0, int(defender["hp"]))
        dealt = min(before_hp, max(1, int(output)))
        defender["hp"] = max(0, before_hp - dealt)
        attacker["dealt_damage"] = int(attacker.get("dealt_damage", 0)) + dealt
        timeline.append(
            f"{attacker['nickname']}\u7b2c{turn_index}\u624b\u9020\u6210{dealt}\u70b9\u4f24\u5bb3\uff0c"
            f"{defender['nickname']}\u8840\u91cf\u964d\u81f3{defender['hp']}/{defender['max_hp']}\u3002"
        )
        if defender["hp"] <= 0:
            ended_early = True
            finisher = attacker
            elapsed_seconds = max(5, min(duration_seconds, int(duration_seconds * (0.38 if turn_index == 1 else 0.68))))
            timeline.append(
                f"{attacker['nickname']}\u6293\u4f4f\u7834\u7efd\u5b9a\u4e0b\u80dc\u8d1f\uff0c{defender['nickname']}\u5df2\u65e0\u529b\u53cd\u51fb\u3002"
            )
            break

    if finisher is left_fighter:
        winner = left_fighter
        loser = right_fighter
    elif finisher is right_fighter:
        winner = right_fighter
        loser = left_fighter
    elif left_fighter["hp"] > right_fighter["hp"]:
        winner = left_fighter
        loser = right_fighter
    elif right_fighter["hp"] > left_fighter["hp"]:
        winner = right_fighter
        loser = left_fighter
    else:
        left_score = left_fighter["power"] + left_fighter["speed"] * 40 + stable_int(f"tie:{left.user_id}:{right.user_id}") % 100
        right_score = right_fighter["power"] + right_fighter["speed"] * 40 + stable_int(f"tie:{right.user_id}:{left.user_id}") % 100
        winner, loser = (left_fighter, right_fighter) if left_score >= right_score else (right_fighter, left_fighter)
    for log in left_fighter["logs"][:4]:
        timeline.append(f"{left_fighter['nickname']}\uff1a{log}")
    for log in right_fighter["logs"][:4]:
        timeline.append(f"{right_fighter['nickname']}\uff1a{log}")
    if not timeline:
        timeline.append("\u53cc\u65b9\u8bd5\u63a2\u6c14\u673a\uff0c\u7075\u538b\u5728\u6f14\u6b66\u573a\u4e2d\u6765\u56de\u78b0\u649e\u3002")
    return {
        "left": left_fighter,
        "right": right_fighter,
        "winner": winner,
        "loser": loser,
        "winner_id": winner["user_id"],
        "winner_name": winner["nickname"],
        "ended_early": ended_early,
        "elapsed_seconds": elapsed_seconds,
        "remaining_seconds": max(0, duration_seconds - elapsed_seconds),
        "duration_seconds": duration_seconds,
        "timeline": timeline[:8],
        "summary": f"{winner['nickname']}\u80dc\u51fa\uff0c\u5269\u4f59\u8840\u91cf {winner['hp']}/{winner['max_hp']}\u3002",
    }

def battle_power(record: UserRecord) -> int:
    realm_power = (record.realm_index + 1) * 900 + record.realm_exp * 3
    exp_power = record.total_exp * 2 + record.pending_exp
    sign_power = record.sign_count * 20
    root_power = 120
    if record.root:
        root_power += 320 + record.root.tier_rank * 280 + record.root.grade_rank * 120
        if record.root.tier == "变异灵根":
            root_power += 520
    root_power += len(record.extra_roots or []) * 160
    root_power += max_root_purity(record) * 6
    root_power += acquired_root_power_total(record)
    foundation_bonus = realm_quality_power(record)
    equipment_power = (
        equipped_artifact_power(record)
        + method_power(record.equipped_method, record)
        + array_power(record.equipped_array, record)
        + puppet_power(record.equipped_puppet, record)
        + talisman_power(record.equipped_talisman, record)
        + int(artifact_power(record.life_artifact, record) * 0.38)
        + immortal_seed_power(record.equipped_immortal_seed, record)
    )
    special_ability_power = special_ability_power_total(record)
    power = realm_power + exp_power + sign_power + root_power + foundation_bonus + equipment_power + special_ability_power
    power = int(power * route_power_multiplier(record))
    if is_breakthrough_bottleneck(record):
        power = int(power * 1.1)
    return max(1, power)

def battle_summary(record: UserRecord) -> dict[str, Any]:
    equipment_power = (
        equipped_artifact_power(record)
        + method_power(record.equipped_method, record)
        + array_power(record.equipped_array, record)
        + puppet_power(record.equipped_puppet, record)
        + talisman_power(record.equipped_talisman, record)
        + int(artifact_power(record.life_artifact, record) * 0.38)
        + immortal_seed_power(record.equipped_immortal_seed, record)
    )
    return {
        "power": battle_power(record),
        "realm": record.realm if record.root else "\u672a\u5165\u95e8",
        "total_exp": record.total_exp,
        "pending_exp": record.pending_exp,
        "artifact": equipped_artifact_name(record),
        "artifact_slots": equipped_artifact_summary(record),
        "talisman": equipped_talisman_name(record),
        "method": equipped_method_name(record),
        "array": equipped_array_name(record),
        "puppet": equipped_puppet_name(record),
        "plant": planted_spirit_plant_name(record),
        "spirit_stones": record.spirit_stones,
        "spirit_liquid": record.spirit_liquid,
        "bottleneck_days": record.bottleneck_days,
        "array_multiplier": array_multiplier(record),
        "artifact_power": equipped_artifact_power(record),
        "talisman_power": talisman_power(record.equipped_talisman, record),
        "puppet_power": puppet_power(record.equipped_puppet, record),
        "equipment_power": equipment_power,
        "cultivation_lock": cultivation_lock_text(record),
        "mystic_realm": "进行中" if record.active_mystic_run_id else "无",
        "foundation_type": record.foundation_type or "",
        "realm_quality": realm_quality_text(record),
        "mana": combat_max_mana(record),
        "is_bottleneck": is_breakthrough_bottleneck(record),
        "breakthrough_required": breakthrough_required_text(record),
        "route": record.route_summary,
        "identity": record.identity_summary,
        "hehuan_remaining": hehuan_remaining_text(record),
        "tianji_status": tianji_status_text(record),
        "spirit_stones_text": spirit_stone_text(record.spirit_stones),
        "special_abilities": normalize_special_abilities(record.special_abilities),
        "special_ability_materials": len(_domain.available_special_ability_items(record)),
        "special_ability_power": special_ability_power_total(record),
        "life_artifact": reward_display_name(record.life_artifact) if record.life_artifact else "未祭炼本命灵器",
        "immortal_seed": equipped_immortal_seed_name(record),
        "immortal_seed_power": immortal_seed_power(record.equipped_immortal_seed, record),
        "mana_label": "仙元力" if record.realm_index >= true_immortal_realm_index() else "灵力",
        "immortal_conversion": record.immortal_conversion_days,
    }

def duel_records(attacker: UserRecord, defender: UserRecord) -> DuelResult:
    attacker_power = battle_power(attacker)
    defender_power = battle_power(defender)
    total = max(1, attacker_power + defender_power)
    chance = max(0.1, min(0.9, attacker_power / total))
    attacker_win = random.random() < chance
    root = attacker.root if attacker_win else defender.root
    detail = DUEL_ACTIONS.get(root.attribute, "\u7075\u6c14\u7ffb\u6d8c\uff0c\u80dc\u8d1f\u4e00\u7ebf") if root else "\u62f3\u811a\u4ea4\u9519\uff0c\u5c18\u70df\u56db\u8d77"
    return DuelResult(
        attacker_power=attacker_power,
        defender_power=defender_power,
        attacker_win=attacker_win,
        chance=chance,
        detail=detail,
    )

def rank_reward_for(rank: int) -> tuple[int, int]:
    if rank == 1:
        exp = 36
    elif rank == 2:
        exp = 28
    elif rank == 3:
        exp = 22
    elif 4 <= rank <= 5:
        exp = 16
    elif 6 <= rank <= 10:
        exp = 10
    else:
        exp = 0
    fishing_rewards = {1: 10, 2: 8, 3: 6, 4: 4, 5: 2}
    return exp, fishing_rewards.get(rank, 0)

def apply_rank_reward(record: UserRecord, rank: int) -> RankReward:
    exp, fishing_chances = rank_reward_for(rank)
    reward = RankReward(rank=rank, exp=exp, fishing_chances=fishing_chances)
    if exp <= 0 and fishing_chances <= 0:
        return reward

    if record.root is None or is_cultivation_locked(record):
        record.pending_exp += exp
        reward.pending = True
    else:
        rank_result = apply_exp(record, exp)
        applied_exp, reward.leveled_realms = rank_result
        reward.exp = applied_exp
    record.fishing_chances += fishing_chances
    return reward
