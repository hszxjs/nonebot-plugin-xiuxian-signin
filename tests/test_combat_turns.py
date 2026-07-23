from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


DOMAIN_PATH = Path(__file__).resolve().parents[1] / "domain.py"
DOMAIN_SPEC = importlib.util.spec_from_file_location("domain", DOMAIN_PATH)
assert DOMAIN_SPEC is not None and DOMAIN_SPEC.loader is not None
domain = importlib.util.module_from_spec(DOMAIN_SPEC)
sys.modules["domain"] = domain
DOMAIN_SPEC.loader.exec_module(domain)


def combat_record(user_id: str) -> object:
    return domain.UserRecord(
        user_id=user_id,
        root=domain.Root("天阶", 4, "极品", 3, "金", 100, ["金"]),
        realm_index=2,
        realm_exp=120,
        sign_count=10,
        combat_race="人族-玄门正宗",
        physique="凡体",
        special_abilities=[],
    )


def test_combat_runtime_state_tracks_hp_mana_and_cooldowns() -> None:
    record = combat_record("42")
    state = domain.CombatRuntimeState.initial(record)

    first = domain.resolve_combat_action(record, "普通攻击", state, "turn:1")
    second = domain.resolve_combat_action(record, "普通攻击", first.state, "turn:2")

    assert first.damage > 0
    assert second.state.turn == 2
    assert second.state.hp == first.state.hp
    assert second.state.mana <= first.state.mana


def test_combat_runtime_state_copies_cooldown_snapshots() -> None:
    record = combat_record("42")
    source_cooldowns = {"金锋斩": 2}
    state = domain.CombatRuntimeState(
        hp=100,
        max_hp=100,
        mana=100,
        max_mana=100,
        cooldowns=source_cooldowns,
    )

    source_cooldowns["金锋斩"] = 99
    successor = domain.resolve_combat_action(record, "", state, "snapshot:1").state

    assert state.cooldowns == {"金锋斩": 2}
    assert successor.cooldowns is not state.cooldowns
    assert successor.cooldowns == {"金锋斩": 1}


def test_existing_action_evaluator_folds_the_single_action_resolver() -> None:
    record = combat_record("42")
    actions = [{"text": "普通攻击"}, {"text": "普通攻击"}]

    aggregate = domain.evaluate_combat_actions(record, actions, "regression")
    state = domain.CombatRuntimeState.initial(record)
    outcomes = []
    for index, action in enumerate(actions, start=1):
        outcome = domain.resolve_combat_action(record, action["text"], state, f"regression:{index}")
        outcomes.append(outcome)
        state = outcome.state

    assert aggregate["damage"] == sum(item.damage for item in outcomes)
    assert aggregate["mana"] == state.mana
    assert aggregate["cooldowns"] == state.cooldowns


def test_existing_action_evaluator_ignores_empty_action_damage() -> None:
    record = combat_record("42")

    baseline = domain.evaluate_combat_actions(record, [], "empty")
    aggregate = domain.evaluate_combat_actions(record, [{"text": ""}, {"text": ""}], "empty")

    assert aggregate == baseline


def test_empty_action_ticks_cooldowns_without_consuming_effective_turn() -> None:
    record = combat_record("42")
    state = domain.CombatRuntimeState(
        hp=100,
        max_hp=100,
        mana=100,
        max_mana=100,
        cooldowns={"金锋斩": 2},
    )

    empty = domain.resolve_combat_action(record, "", state, "empty:1")

    assert empty.damage == 0
    assert empty.defense == 0
    assert empty.state.turn == 0
    assert empty.state.cooldowns == {"金锋斩": 1}
    assert state.cooldowns == {"金锋斩": 2}


def test_leading_empty_action_preserves_first_effective_action_baseline() -> None:
    record = combat_record("42")
    state = domain.CombatRuntimeState.initial(record)

    empty = domain.resolve_combat_action(record, "", state, "leading:1")
    after_empty = domain.resolve_combat_action(record, "普通攻击", empty.state, "leading:2")
    direct = domain.resolve_combat_action(record, "普通攻击", state, "leading:2")

    assert after_empty.damage == direct.damage
    assert after_empty.defense == direct.defense
    assert after_empty.state.turn == 1


def test_existing_action_evaluator_triggers_generic_ability_once() -> None:
    record = combat_record("42")
    record.special_abilities = ["澄元剑芒"]

    single = domain.evaluate_combat_actions(record, [{"text": "澄元剑芒"}], "ability")
    repeated = domain.evaluate_combat_actions(
        record,
        [{"text": "澄元剑芒"}, {"text": "澄元剑芒"}],
        "ability",
    )

    assert repeated["triggered"].count("澄元剑芒") == 1
    assert repeated["mana"] < single["mana"]


def test_generic_ability_fallback_uses_legacy_action_index_and_trigger_count() -> None:
    record = combat_record("42")
    record.special_abilities = ["澄元剑芒"]
    record.equipped_method = {
        "name": "试炼剑诀",
        "tier": "天阶",
        "grade": "极品",
        "category": "功法",
        "kind": "战技类",
        "techniques": ["金锋斩", "庚金刺", "流光剑影"],
    }
    available = domain.available_battle_techniques(record)
    action_text = domain.sanitize_combat_text("澄元剑芒")
    side_seed = next(
        candidate
        for candidate in (f"ability-{index}" for index in range(1000))
        if domain.stable_choice(available, f"improv:{candidate}:2:{action_text}:1")
        not in {
            domain.stable_choice(available, f"improv:{candidate}:1:{action_text}:0"),
            domain.stable_choice(available, f"improv:{candidate}:1:{action_text}:1"),
            domain.stable_choice(available, f"improv:{candidate}:2:{action_text}:0"),
        }
    )
    expected = domain.stable_choice(available, f"improv:{side_seed}:2:{action_text}:1")

    result = domain.evaluate_combat_actions(
        record,
        [{"text": "澄元剑芒"}, {"text": "澄元剑芒"}],
        side_seed,
    )

    assert result["triggered"] == ["澄元剑芒", expected]
    assert result["mana"] == domain.combat_max_mana(record) - domain.technique_mana_cost(
        record,
        expected,
        improvised=True,
    )
