"""御兽秘境的规则表契约（R-19）。

御兽是「卡牌数据 + 生成规则」驱动的玩法：卡面属性来自 ``FACTION_BONUS`` 与 ``tier``，
效果文案与规则来自 ``generated_effect_and_rules`` 的四档 variant。这类表驱动代码
一旦某个阵营/档位缺分支，表现是「某张卡没有任何效果」而不是抛异常，线上极难发现。

本文件钉住四件事：

1. 九个阵营 × 四档 variant × 三档境界都必须产出非空效果与合法规则结构；
2. 生成属性随境界单调、恒为正；
3. 卡牌目录结构与图标映射自洽（图标缺失要显式暴露，不能静默出空白）；
4. 后台调参（``apply_admin_config``）能真正改到卡面并重建索引。
"""
from __future__ import annotations

import pytest

from nonebot_plugin_xiuxian_signin import beast_realm as br

FACTIONS = sorted(br.FACTION_BONUS)
# 引擎实际消费的触发时机（grep ``unit_rules(..., "<trigger>")`` 得出）。
# 卡面写了引擎不读的键，效果会静默不生效，所以这里必须与引擎一致。
RULE_TRIGGERS = {"join", "start", "leave", "ally_leave", "aura", "kill"}


def test_stable_int_is_deterministic_and_bounded() -> None:
    assert br.stable_int("青狐") == br.stable_int("青狐")
    assert br.stable_int("青狐") != br.stable_int("赤狼")
    assert 0 <= br.stable_int("任意文本" * 50) < 1_000_003


def test_character_element_prefers_text_mention() -> None:
    entry = {"name": "雷泽兽", "archetype": "", "story": ""}
    assert br.character_element(entry, seed=3) == "雷"
    # 文本里没有元素时按 seed 取，且结果稳定
    plain = {"name": "无名", "archetype": "妖兽", "story": ""}
    assert br.character_element(plain, seed=5) == br.character_element(plain, seed=5)
    assert br.character_element(plain, seed=5) in br.ELEMENT_POOL


@pytest.mark.parametrize("faction", FACTIONS)
def test_generated_stats_grow_with_tier(faction: str) -> None:
    previous = (0, 0)
    for tier in (1, 2, 3, 4, 5, 6):
        attack, defense = br.generated_card_stats(tier, faction, seed=11)
        assert attack >= 1 and defense >= 1, f"{faction} 境界 {tier} 属性必须为正"
        assert attack >= previous[0] and defense >= previous[1], f"{faction} 属性应随境界不降"
        previous = (attack, defense)


@pytest.mark.parametrize("faction", FACTIONS)
@pytest.mark.parametrize("tier", [1, 3, 6])
def test_generated_effect_covers_every_variant(faction: str, tier: int) -> None:
    """同一个阵营的四种 seed 变体都必须产出非空效果与合法规则。"""
    for seed in range(4):
        text, rules = br.generated_effect_and_rules(faction, tier, "火", seed)
        assert isinstance(text, str) and text.strip(), f"{faction} tier{tier} seed{seed} 效果文案为空"
        assert isinstance(rules, dict) and rules, f"{faction} tier{tier} seed{seed} 规则为空"
        assert set(rules) <= RULE_TRIGGERS, f"{faction} 出现未登记的触发时机：{sorted(set(rules) - RULE_TRIGGERS)}"
        for trigger, actions in rules.items():
            assert isinstance(actions, list) and actions, f"{faction} 的 {trigger} 没有任何动作"
            for action in actions:
                assert isinstance(action, dict) and action.get("kind"), (
                    f"{faction} 的 {trigger} 动作缺少 kind：{action}"
                )


def test_card_catalog_is_well_formed() -> None:
    cards = br.BEAST_REALM_CARDS
    spells = br.BEAST_REALM_SPELLS
    assert cards, "随从卡表不应为空"
    assert spells, "法术卡表不应为空"

    for card in cards:
        for key in ("kind", "id", "name", "tier", "realm", "attack", "defense", "faction", "element"):
            assert key in card, f"随从卡 {card.get('id')} 缺少字段 {key}"
        assert card["kind"] == "beast"
        assert 1 <= int(card["tier"]) <= len(br.BEAST_REALM_TIERS)
        assert card["realm"] == br.BEAST_REALM_TIERS[int(card["tier"]) - 1]
        assert int(card["attack"]) >= 1 and int(card["defense"]) >= 1
        assert card["faction"] in br.FACTION_BONUS, f"未知阵营 {card['faction']}"
        assert card["element"] in br.ELEMENT_POOL, f"未知元素 {card['element']}"

    for spell in spells:
        assert spell["kind"] == "spell"
        for key in ("id", "name", "tier", "realm", "category", "target", "effect", "rules"):
            assert key in spell, f"法术卡 {spell.get('id')} 缺少字段 {key}"
        assert spell["realm"] == br.BEAST_REALM_TIERS[int(spell["tier"]) - 1]
        assert spell["target"] in {"ally", "team", "enemy"}
        # 法术卡的 rules 是「动作列表」，与随从卡的「触发时机 → 动作列表」不同。
        assert isinstance(spell["rules"], list) and spell["rules"]
        for action in spell["rules"]:
            assert isinstance(action, dict) and action.get("kind")

    ids = [card["id"] for card in cards] + [spell["id"] for spell in spells]
    assert len(ids) == len(set(ids)), "卡牌 id 必须唯一，否则索引会互相覆盖"


def test_card_indexes_cover_catalog() -> None:
    assert set(br.BEAST_REALM_CARD_BY_ID) == {card["id"] for card in br.BEAST_REALM_CARDS}
    assert set(br.BEAST_REALM_SPELL_BY_ID) == {spell["id"] for spell in br.BEAST_REALM_SPELLS}
    assert len(br.BEAST_REALM_ALL_CARDS_BY_ID) == len(br.BEAST_REALM_CARD_BY_ID) + len(
        br.BEAST_REALM_SPELL_BY_ID
    )


def test_spell_icon_mapping_never_points_to_missing_file() -> None:
    """图标映射只允许「返回存在的文件」或「返回空串」，不许返回不存在的路径。"""
    for spell in br.BEAST_REALM_SPELLS:
        filename = br.spell_icon_filename_for(spell)
        if filename:
            assert (br.SPELL_ICON_DIR / filename).is_file()
        else:
            assert not (br.SPELL_ICON_DIR / f"{spell['id']}.png").exists() or not spell.get("icon_id")


def test_trap_rules_are_reachable_from_cards() -> None:
    """卡面引用到的反阵名必须在 TRAP_RULES 里有实现。"""
    referenced: set[str] = set()
    for spell in br.BEAST_REALM_SPELLS:
        for action in spell.get("rules", []):
            if isinstance(action, dict) and action.get("trap"):
                referenced.add(str(action["trap"]))
    missing = referenced - set(br.TRAP_RULES)
    assert not missing, f"这些反阵在卡面被引用但没有实现：{sorted(missing)}"


def test_create_table_invariants() -> None:
    table = br.create_table("10000", "42", "青衫客")
    assert table["group_id"] == "10000"
    assert table["host_id"] == "42"
    assert table["mode"] == "pve"
    assert table["phase"] == "lobby"
    assert len(table["players"]) == 1
    host = table["players"][0]
    assert host["id"] == "42" and not host.get("bot")
    assert br.active_human_players(table) == [host]
    assert br.is_player_alive(host)
    assert table["expires_at"] > table["created_at"]


def test_keys_and_mode_labels() -> None:
    assert br.group_key(123) == br.group_key("123")
    assert br.private_key(456) == br.private_key("456")
    assert br.group_key(1) != br.private_key(1)
    for mode in ("pve", "pvp"):
        assert br.parse_mode(br.mode_label(mode)) == mode


def test_apply_admin_config_rebuilds_indexes_with_overrides() -> None:
    """后台改卡面必须真的生效，并且索引同步重建。"""
    first_card = br.BEAST_REALM_CARDS[0]
    card_id = str(first_card["id"])
    try:
        br.apply_admin_config({"beast_realm": {"card_overrides": {card_id: {"cost": 9, "attack": 99}}}})
        updated = br.BEAST_REALM_ALL_CARDS_BY_ID[card_id]
        assert int(updated.get("cost", 0)) == 9
        assert int(updated["attack"]) == 99
        assert br.BEAST_REALM_CARD_BY_ID[card_id] is updated
    finally:
        br.apply_admin_config({})
    restored = br.BEAST_REALM_ALL_CARDS_BY_ID[card_id]
    assert int(restored["attack"]) == int(first_card["attack"])
