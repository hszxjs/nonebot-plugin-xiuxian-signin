from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "mystic_dungeon.py"
MODULE_SPEC = importlib.util.spec_from_file_location("mystic_dungeon", MODULE_PATH)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
mystic_dungeon = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules["mystic_dungeon"] = mystic_dungeon
MODULE_SPEC.loader.exec_module(mystic_dungeon)

DEFAULT_MAP_SIZE_RULES = mystic_dungeon.DEFAULT_MAP_SIZE_RULES
SUPPORTED_MAP_SIZES = mystic_dungeon.SUPPORTED_MAP_SIZES
DungeonRisk = mystic_dungeon.DungeonRisk
MysticTemplateCatalog = mystic_dungeon.MysticTemplateCatalog
map_size_for_boss = mystic_dungeon.map_size_for_boss
DungeonMode = mystic_dungeon.DungeonMode
DungeonPhase = mystic_dungeon.DungeonPhase
DungeonRewardLedger = mystic_dungeon.DungeonRewardLedger
DungeonVote = mystic_dungeon.DungeonVote
MysticContentFactory = mystic_dungeon.MysticContentFactory
MysticGameplayConfig = mystic_dungeon.MysticGameplayConfig
MysticDungeonRun = mystic_dungeon.MysticDungeonRun
MysticDungeonService = mystic_dungeon.MysticDungeonService
NodeKind = mystic_dungeon.NodeKind
VoteKind = mystic_dungeon.VoteKind
default_mystic_gameplay_config = mystic_dungeon.default_mystic_gameplay_config


ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets" / "mystic_maps"
EXPECTED_NORMAL_THEMES = {
    "ancient_sect_ruins": "上古宗门遗址",
    "beast_tide": "兽潮",
    "ancient_cultivator_cave": "上古大能洞府",
    "star_mine": "星古矿区",
    "soul_remnant": "魂界残域",
    "bronze_cloud_palace": "古铜云阙",
}
EXPECTED_HIGH_RISK_THEMES = {
    "far_wilderness_boundary": "远荒限界",
    "silent_black_mountain": "沉寂黑山",
    "prime_star_mine": "星初矿渊",
    "fallen_god_ruins": "神陨废墟",
    "immortal_sleep_valley": "仙眠幽谷",
    "reincarnation_tide_eye": "轮回潮眼",
    "burial_sky_island": "葬天岛",
    "qiongheng_ancient_hall": "穹衡古殿",
    "five_elements_land": "五行之地",
    "outer_battlefield": "域外战场",
    "nether_spring_demon_sect": "幽泉魔宗",
    "dust_ruins": "荒尘墟",
    "star_fate_lonely_realm": "星运孤界",
    "heaven_gate_battlefield": "天关古战场",
    "seven_constellations_road": "七宿星空古路",
    "bronze_cloud_deep": "古铜云阙深层",
    "thunder_pool": "雷池古域",
    "mystic_stone_gate": "玄界石门",
    "starfall_remnant": "星陨残原",
    "green_mystic_shadow": "青玄门影",
}
NOW = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def catalog() -> MysticTemplateCatalog:
    return MysticTemplateCatalog.from_files()


@pytest.fixture
def service(catalog: MysticTemplateCatalog) -> MysticDungeonService:
    return MysticDungeonService(catalog, now=lambda: NOW)


def _start_team(
    service: MysticDungeonService,
    member_count: int = 2,
    *,
    risk: DungeonRisk = DungeonRisk.NORMAL,
) -> MysticDungeonRun:
    run = service.create_lobby("run-team", "100", "leader", risk)
    for index in range(2, member_count + 1):
        service.join_lobby(run, f"member-{index}", f"Member {index}")
    for user_id in run.member_ids:
        service.set_ready(run, user_id, True)
    service.start_run(run, boss_realm_index=4, map_seed=7, content_seed=11)
    return run


def _graph_for_run(catalog: MysticTemplateCatalog, run: MysticDungeonRun):
    return catalog.templates[run.template_id].active_graph(run.map_size)


def test_map_size_uses_supported_realm_tiers() -> None:
    expected = {0: 24, 5: 28, 10: 32, 15: 36, 20: 40, 25: 44, 30: 48}
    for realm_index, node_count in expected.items():
        assert map_size_for_boss(realm_index, DEFAULT_MAP_SIZE_RULES) == node_count


def test_map_size_rejects_unsupported_configured_size() -> None:
    with pytest.raises(ValueError, match="unsupported map size: 26"):
        map_size_for_boss(0, ((0, 26),))


def test_apply_admin_config_updates_runtime_config_and_theme_selection() -> None:
    configured = default_mystic_gameplay_config().to_mapping()
    configured["ordinary_monster_hp_multiplier"] = 1.75
    configured["enabled_types"] = ["ancient_sect_ruins"]
    configured["enabled_high_risk_types"] = ["thunder_pool"]
    try:
        mystic_dungeon.apply_admin_config({"mystic": configured})

        assert (
            mystic_dungeon.active_mystic_gameplay_config()
            .ordinary_monster_hp_multiplier
            == 1.75
        )
        assert mystic_dungeon.active_mystic_theme_ids(DungeonRisk.NORMAL) == (
            "ancient_sect_ruins",
        )
        assert mystic_dungeon.active_mystic_theme_ids(DungeonRisk.HIGH) == (
            "thunder_pool",
        )
    finally:
        mystic_dungeon.apply_admin_config(
            {"mystic": default_mystic_gameplay_config().to_mapping()}
        )


def test_started_run_reads_latest_config_and_enabled_theme_provider(
    catalog: MysticTemplateCatalog,
) -> None:
    state = {"config": default_mystic_gameplay_config()}
    enabled_theme_id = sorted(
        theme.theme_id
        for theme in catalog.themes.values()
        if theme.risk is DungeonRisk.NORMAL
    )[1]
    service = MysticDungeonService(
        catalog,
        now=lambda: NOW,
        config_provider=lambda: state["config"],
        enabled_theme_ids_provider=lambda risk: (
            (enabled_theme_id,) if risk is DungeonRisk.NORMAL else None
        ),
    )
    configured = state["config"].to_mapping()
    configured["map_size_rules"] = [
        {"minimum_boss_realm_index": 0, "node_count": 48}
    ]
    configured["max_map_size"] = 36
    configured["normal_node_weights"] = {NodeKind.RESOURCE.value: 1.0}
    state["config"] = MysticGameplayConfig.from_mapping(configured)

    run, _ = service.create_solo_run(
        "dynamic-config",
        "100",
        "leader",
        DungeonRisk.NORMAL,
        boss_realm_index=30,
        map_seed=0,
        content_seed=19,
    )

    assert run.map_size == 36
    assert run.theme_id == enabled_theme_id
    graph = catalog.templates[run.template_id].active_graph(run.map_size)
    weighted_nodes = [
        node
        for node in graph.nodes
        if not node.is_safe
        and node.node_id not in {graph.start_node_id, graph.boss_node_id}
        and NodeKind.RESOURCE in node.allowed_kinds
    ]
    assert weighted_nodes
    assert all(
        run.node_contents[node.node_id].kind is NodeKind.RESOURCE
        for node in weighted_nodes
    )


def test_reward_multiplier_scales_numeric_dungeon_rewards(
    catalog: MysticTemplateCatalog,
) -> None:
    base = default_mystic_gameplay_config()
    configured = base.to_mapping()
    configured["reward_multiplier"] = 2.5
    boosted = MysticGameplayConfig.from_mapping(configured)
    base_service = MysticDungeonService(
        catalog,
        now=lambda: NOW,
        config_provider=lambda: base,
    )
    boosted_service = MysticDungeonService(
        catalog,
        now=lambda: NOW,
        config_provider=lambda: boosted,
    )
    base_run, _ = base_service.create_solo_run(
        "base-reward",
        "100",
        "leader",
        DungeonRisk.NORMAL,
        boss_realm_index=0,
        map_seed=7,
        content_seed=11,
    )
    boosted_run, _ = boosted_service.create_solo_run(
        "boosted-reward",
        "100",
        "leader",
        DungeonRisk.NORMAL,
        boss_realm_index=0,
        map_seed=7,
        content_seed=11,
    )

    for index in range(20):
        reward_key = f"reward-{index}"
        base_reward = base_service.grant_encounter_rewards(
            base_run,
            reward_key,
            ("leader",),
        ).rewards_by_user["leader"][0]
        boosted_reward = boosted_service.grant_encounter_rewards(
            boosted_run,
            reward_key,
            ("leader",),
        ).rewards_by_user["leader"][0]
        if "amount" in base_reward:
            assert boosted_reward["amount"] == max(
                1,
                int(base_reward["amount"] * boosted.reward_multiplier),
            )
            break
    else:
        pytest.fail("expected at least one deterministic numeric reward")


def test_manifest_contains_every_approved_theme(catalog: MysticTemplateCatalog) -> None:
    expected = EXPECTED_NORMAL_THEMES | EXPECTED_HIGH_RISK_THEMES

    assert len(catalog.themes) == 26
    assert {theme_id: theme.display_name for theme_id, theme in catalog.themes.items()} == expected
    assert {
        theme_id for theme_id, theme in catalog.themes.items() if theme.risk is DungeonRisk.NORMAL
    } == set(EXPECTED_NORMAL_THEMES)
    assert {
        theme_id for theme_id, theme in catalog.themes.items() if theme.risk is DungeonRisk.HIGH
    } == set(EXPECTED_HIGH_RISK_THEMES)
    for theme_id, theme in catalog.themes.items():
        assert theme.template_id == theme_id
        assert theme.background_path.as_posix().endswith(f"assets/mystic_maps/backgrounds/{theme_id}.png")


def test_catalog_rejects_background_sha256_mismatch(tmp_path: Path) -> None:
    manifest = json.loads((ASSET_ROOT / "manifest.json").read_text(encoding="utf-8"))
    theme_id = next(iter(manifest["themes"]))
    background = tmp_path / manifest["themes"][theme_id]["background"]
    background.parent.mkdir(parents=True)
    background.write_bytes(b"tampered-background")
    manifest["themes"][theme_id]["sha256"] = "0" * 64
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="sha256.*does not match"):
        MysticTemplateCatalog.from_files(
            manifest_path=manifest_path,
            templates_path=ASSET_ROOT / "templates.json",
        )


def test_every_template_is_connected_for_every_active_size(catalog: MysticTemplateCatalog) -> None:
    assert set(catalog.templates) == set(catalog.themes)
    for template in catalog.templates.values():
        for size in SUPPORTED_MAP_SIZES:
            active = template.active_graph(size)
            assert len(active.nodes) == size
            assert active.has_path(active.start_node_id, active.boss_node_id)
            assert any(node.is_safe and node.node_id != active.start_node_id for node in active.nodes)


def test_template_coordinates_and_activation_counts_are_valid(catalog: MysticTemplateCatalog) -> None:
    for template in catalog.templates.values():
        assert len(template.nodes) == 48
        assert len({node.node_id for node in template.nodes}) == 48
        assert all(0.0 <= node.x <= 1.0 and 0.0 <= node.y <= 1.0 for node in template.nodes)
        assert tuple(sum(node.activation_size <= size for node in template.nodes) for size in SUPPORTED_MAP_SIZES) == (
            24,
            28,
            32,
            36,
            40,
            44,
            48,
        )


def test_normal_and_high_risk_branch_density(catalog: MysticTemplateCatalog) -> None:
    for template in catalog.normal_templates():
        assert template.active_graph(24).branch_count == 3
        assert template.active_graph(48).branch_count == 5
        assert not template.active_graph(48).loop_edges

    for template in catalog.high_risk_templates():
        assert template.active_graph(24).branch_count >= 5
        assert template.active_graph(48).branch_count >= 8
        assert 1 <= len(template.active_graph(24).loop_edges) <= 2
        assert 1 <= len(template.active_graph(48).loop_edges) <= 4


def test_high_risk_loops_never_form_the_only_boss_route(catalog: MysticTemplateCatalog) -> None:
    for template in catalog.high_risk_templates():
        template.validate_loop_safety()
        for size in SUPPORTED_MAP_SIZES:
            active = template.active_graph(size)
            assert active.has_path(active.start_node_id, active.boss_node_id, include_loop_edges=False)


def test_catalog_rejects_coordinates_outside_normalized_range(tmp_path: Path) -> None:
    manifest = json.loads((ASSET_ROOT / "manifest.json").read_text(encoding="utf-8"))
    templates = json.loads((ASSET_ROOT / "templates.json").read_text(encoding="utf-8"))
    first_template = next(iter(templates["templates"].values()))
    first_template["nodes"][0]["x"] = 1.01
    manifest_path = tmp_path / "manifest.json"
    templates_path = tmp_path / "templates.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    templates_path.write_text(json.dumps(templates, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="coordinate"):
        MysticTemplateCatalog.from_files(manifest_path, templates_path)


def test_catalog_rejects_edges_that_reference_unknown_nodes(tmp_path: Path) -> None:
    manifest = json.loads((ASSET_ROOT / "manifest.json").read_text(encoding="utf-8"))
    templates = json.loads((ASSET_ROOT / "templates.json").read_text(encoding="utf-8"))
    first_template = next(iter(templates["templates"].values()))
    first_template["edges"][0]["target_node_id"] = "missing-node"
    manifest_path = tmp_path / "manifest.json"
    templates_path = tmp_path / "templates.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    templates_path.write_text(json.dumps(templates, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown node"):
        MysticTemplateCatalog.from_files(manifest_path, templates_path)


def test_catalog_rejects_nodes_unreachable_from_start(tmp_path: Path) -> None:
    manifest = json.loads((ASSET_ROOT / "manifest.json").read_text(encoding="utf-8"))
    templates = json.loads((ASSET_ROOT / "templates.json").read_text(encoding="utf-8"))
    first_template = next(iter(templates["templates"].values()))
    incoming_edge = next(edge for edge in first_template["edges"] if edge["edge_id"] == "main-09-10")
    incoming_edge["target_node_id"] = "n11"
    manifest_path = tmp_path / "manifest.json"
    templates_path = tmp_path / "templates.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    templates_path.write_text(json.dumps(templates, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="unreachable from start"):
        MysticTemplateCatalog.from_files(manifest_path, templates_path)


def test_catalog_rejects_nodes_that_cannot_reach_boss(tmp_path: Path) -> None:
    manifest = json.loads((ASSET_ROOT / "manifest.json").read_text(encoding="utf-8"))
    templates = json.loads((ASSET_ROOT / "templates.json").read_text(encoding="utf-8"))
    first_template = next(iter(templates["templates"].values()))
    first_template["edges"] = [
        edge for edge in first_template["edges"] if edge["edge_id"] != "main-10-11"
    ]
    manifest_path = tmp_path / "manifest.json"
    templates_path = tmp_path / "templates.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    templates_path.write_text(json.dumps(templates, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="cannot reach boss"):
        MysticTemplateCatalog.from_files(manifest_path, templates_path)


def test_catalog_rejects_backward_edges_mislabeled_as_non_loop(tmp_path: Path) -> None:
    manifest = json.loads((ASSET_ROOT / "manifest.json").read_text(encoding="utf-8"))
    templates = json.loads((ASSET_ROOT / "templates.json").read_text(encoding="utf-8"))
    first_template = next(iter(templates["templates"].values()))
    branch_edge = next(edge for edge in first_template["edges"] if edge["edge_id"] == "branch-normal-00")
    branch_edge["source_node_id"] = "n05"
    branch_edge["target_node_id"] = "n02"
    branch_edge["is_loop"] = False
    manifest_path = tmp_path / "manifest.json"
    templates_path = tmp_path / "templates.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    templates_path.write_text(json.dumps(templates, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="non-loop edge.*depth"):
        MysticTemplateCatalog.from_files(manifest_path, templates_path)


def test_catalog_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    manifest_text = (ASSET_ROOT / "manifest.json").read_text(encoding="utf-8")
    manifest_text = manifest_text.replace(
        '"schema_version": 1,',
        '"schema_version": 1,\n  "schema_version": 1,',
        1,
    )
    manifest_path = tmp_path / "manifest.json"
    templates_path = tmp_path / "templates.json"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    templates_path.write_text(
        (ASSET_ROOT / "templates.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate JSON key"):
        MysticTemplateCatalog.from_files(manifest_path, templates_path)


@pytest.mark.parametrize("member_count", [2, 3])
def test_team_start_locks_two_or_three_members_and_charges_only_leader(
    service: MysticDungeonService,
    member_count: int,
) -> None:
    run = service.create_lobby("run-start", "100", "leader", DungeonRisk.NORMAL)
    for index in range(2, member_count + 1):
        service.join_lobby(run, f"member-{index}")
    for user_id in run.member_ids:
        service.set_ready(run, user_id, True)

    charge = service.start_run(run, boss_realm_index=4, map_seed=7, content_seed=11)

    expected_members = tuple(["leader", *[f"member-{index}" for index in range(2, member_count + 1)]])
    assert run.phase is DungeonPhase.READY_TO_ROLL
    assert run.member_ids == expected_members
    assert charge.payer_id == "leader"
    assert charge.token_name == "普通秘境令牌"
    assert charge.amount == 1
    assert run.revision == member_count * 2


def test_team_lobby_allows_one_to_three_members_but_requires_ready_pair_to_start(
    service: MysticDungeonService,
) -> None:
    run = service.create_lobby("run-lobby", "100", "leader", DungeonRisk.NORMAL)
    with pytest.raises(ValueError, match="two or three"):
        service.start_run(run, boss_realm_index=4, map_seed=7, content_seed=11)

    service.join_lobby(run, "member-2")
    service.set_ready(run, "leader", True)
    with pytest.raises(ValueError, match="ready"):
        service.start_run(run, boss_realm_index=4, map_seed=7, content_seed=11)

    service.join_lobby(run, "member-3")
    with pytest.raises(ValueError, match="full"):
        service.join_lobby(run, "member-4")


def test_solo_start_creates_one_member_run_and_charges_that_player(
    service: MysticDungeonService,
) -> None:
    run, charge = service.create_solo_run(
        run_id="run-solo",
        group_id="100",
        user_id="solo",
        risk=DungeonRisk.NORMAL,
        boss_realm_index=4,
        map_seed=7,
        content_seed=11,
    )

    assert run.mode is DungeonMode.SOLO
    assert run.member_ids == ("solo",)
    assert run.phase is DungeonPhase.READY_TO_ROLL
    assert charge.payer_id == "solo"
    assert charge.token_name == "普通秘境令牌"


def test_team_start_returns_high_risk_leader_charge(service: MysticDungeonService) -> None:
    run = service.create_lobby("run-high", "100", "leader", DungeonRisk.HIGH)
    service.join_lobby(run, "member-2")
    service.set_ready(run, "leader", True)
    service.set_ready(run, "member-2", True)

    charge = service.start_run(run, boss_realm_index=10, map_seed=7, content_seed=11)

    assert charge.payer_id == "leader"
    assert charge.token_name == "高风险秘境令牌"
    assert run.map_size == 32


def test_start_selects_theme_deterministically_from_sorted_risk_catalog(
    catalog: MysticTemplateCatalog,
) -> None:
    first_service = MysticDungeonService(catalog, now=lambda: NOW)
    second_service = MysticDungeonService(catalog, now=lambda: NOW)

    first, _ = first_service.create_solo_run(
        "run-a", "100", "solo-a", DungeonRisk.NORMAL, 4, 13, 21
    )
    second, _ = second_service.create_solo_run(
        "run-b", "100", "solo-b", DungeonRisk.NORMAL, 4, 13, 22
    )

    expected_theme_ids = sorted(
        theme.theme_id for theme in catalog.themes.values() if theme.risk is DungeonRisk.NORMAL
    )
    expected_theme_id = expected_theme_ids[13 % len(expected_theme_ids)]
    assert first.theme_id == second.theme_id == expected_theme_id
    assert first.template_id == second.template_id == expected_theme_id


def test_member_roster_cannot_change_after_start(service: MysticDungeonService) -> None:
    run = _start_team(service)

    with pytest.raises(ValueError, match="lobby"):
        service.join_lobby(run, "replacement")
    with pytest.raises(ValueError, match="lobby"):
        service.remove_lobby_member(run, "member-2")

    assert run.member_ids == ("leader", "member-2")


def test_roll_pauses_at_branch_and_choose_resumes_remaining_steps(
    service: MysticDungeonService,
    catalog: MysticTemplateCatalog,
) -> None:
    run = _start_team(service)
    graph = _graph_for_run(catalog, run)
    outgoing = {
        node.node_id: tuple(edge for edge in graph.edges if edge.source_node_id == node.node_id)
        for node in graph.nodes
    }
    branch_node_id, branch_edges = next(
        (node_id, edges) for node_id, edges in outgoing.items() if len(edges) > 1
    )
    run.current_node_id = branch_node_id
    run.visited_node_ids = [branch_node_id]
    run.cleared_node_ids = [branch_node_id]

    movement = service.roll(run, actor_id=run.leader_id, dice_value=1)

    assert movement.landed_node_id is None
    assert movement.pending_branch_choices == tuple(sorted(edge.target_node_id for edge in branch_edges))
    assert run.phase is DungeonPhase.AWAITING_BRANCH
    assert run.remaining_steps == 1

    resumed = service.choose_branch(
        run,
        actor_id=run.leader_id,
        target_node_id=movement.pending_branch_choices[0],
    )

    assert resumed.landed_node_id == movement.pending_branch_choices[0]
    assert run.remaining_steps == 0
    assert not run.pending_branch_choices


def test_choose_branch_rejects_unknown_target(
    service: MysticDungeonService,
    catalog: MysticTemplateCatalog,
) -> None:
    run = _start_team(service)
    graph = _graph_for_run(catalog, run)
    outgoing = {
        node.node_id: tuple(edge for edge in graph.edges if edge.source_node_id == node.node_id)
        for node in graph.nodes
    }
    branch_node_id = next(node_id for node_id, edges in outgoing.items() if len(edges) > 1)
    run.current_node_id = branch_node_id
    run.visited_node_ids = [branch_node_id]
    run.cleared_node_ids = [branch_node_id]
    service.roll(run, run.leader_id, 1)

    with pytest.raises(ValueError, match="pending branch"):
        service.choose_branch(run, run.leader_id, "not-a-choice")


def test_boss_overshoot_stops_on_boss(
    service: MysticDungeonService,
    catalog: MysticTemplateCatalog,
) -> None:
    run = _start_team(service)
    graph = _graph_for_run(catalog, run)
    outgoing_counts = {
        node.node_id: sum(edge.source_node_id == node.node_id for edge in graph.edges)
        for node in graph.nodes
    }
    boss_edge = next(
        edge
        for edge in graph.edges
        if edge.target_node_id == graph.boss_node_id and outgoing_counts[edge.source_node_id] == 1
    )
    run.current_node_id = boss_edge.source_node_id
    run.visited_node_ids = [boss_edge.source_node_id]
    run.cleared_node_ids = [boss_edge.source_node_id]

    movement = service.roll(run, actor_id=run.leader_id, dice_value=6)

    assert run.current_node_id == run.boss_node_id
    assert run.remaining_steps == 0
    assert movement.landed_node_id == run.boss_node_id
    assert movement.traversed_edge_ids == (boss_edge.edge_id,)


def test_revisit_does_not_require_duplicate_resolution(
    service: MysticDungeonService,
    catalog: MysticTemplateCatalog,
) -> None:
    run = _start_team(service)
    graph = _graph_for_run(catalog, run)
    outgoing_counts = {
        node.node_id: sum(edge.source_node_id == node.node_id for edge in graph.edges)
        for node in graph.nodes
    }
    edge = next(
        edge
        for edge in graph.edges
        if outgoing_counts[edge.source_node_id] == 1 and edge.target_node_id != graph.boss_node_id
    )
    run.current_node_id = edge.source_node_id
    run.visited_node_ids = [edge.source_node_id, edge.target_node_id]
    run.cleared_node_ids = [edge.source_node_id, edge.target_node_id]
    run.visited_edge_ids = [edge.edge_id]

    movement = service.roll(run, actor_id=run.leader_id, dice_value=1)

    assert movement.landed_node_id == edge.target_node_id
    assert not movement.node_resolution_required
    assert run.phase is DungeonPhase.READY_TO_ROLL
    assert run.visited_node_ids.count(edge.target_node_id) == 1
    assert run.visited_edge_ids.count(edge.edge_id) == 1


def test_roll_rejects_wrong_actor_and_invalid_dice(service: MysticDungeonService) -> None:
    run = _start_team(service)

    with pytest.raises(PermissionError, match="leader"):
        service.roll(run, actor_id="member-2", dice_value=1)
    with pytest.raises(ValueError, match="between 1 and 6"):
        service.roll(run, actor_id="leader", dice_value=7)


def test_movement_is_blocked_during_combat(service: MysticDungeonService) -> None:
    run = _start_team(service)
    run.phase = DungeonPhase.BATTLE_TURN

    with pytest.raises(ValueError, match="ready_to_roll"):
        service.roll(run, actor_id=run.leader_id, dice_value=1)


def test_two_member_leader_transfer_needs_only_the_non_leader_approval(
    service: MysticDungeonService,
) -> None:
    run = _start_team(service)
    vote = service.begin_leader_transfer(
        run,
        actor_id="member-2",
        nominee_id="member-2",
        deadline=NOW + timedelta(minutes=1),
    )

    assert vote.eligible_user_ids == ("member-2",)
    result = service.cast_vote(run, actor_id="member-2", approve=True)

    assert result.passed and not result.failed and not result.pending
    assert run.leader_id == "member-2"
    assert run.phase is DungeonPhase.READY_TO_ROLL


def test_three_member_leader_transfer_requires_both_non_leaders(
    service: MysticDungeonService,
) -> None:
    run = _start_team(service, 3)
    service.begin_leader_transfer(
        run,
        actor_id="member-2",
        nominee_id="member-2",
        deadline=NOW + timedelta(minutes=1),
    )

    first = service.cast_vote(run, actor_id="member-2", approve=True)
    second = service.cast_vote(run, actor_id="member-3", approve=True)

    assert first.pending and not first.passed and not first.failed
    assert second.passed
    assert run.leader_id == "member-2"


def test_successful_leader_transfer_preserves_previous_active_phase(
    service: MysticDungeonService,
) -> None:
    run = _start_team(service, 3)
    run.phase = DungeonPhase.BATTLE_TURN
    service.begin_leader_transfer(
        run,
        actor_id="member-2",
        nominee_id="member-2",
        deadline=NOW + timedelta(minutes=1),
    )

    assert service.cast_vote(run, actor_id="member-2", approve=True).pending
    result = service.cast_vote(run, actor_id="member-3", approve=True)

    assert result.passed
    assert run.leader_id == "member-2"
    assert run.phase is DungeonPhase.BATTLE_TURN


def test_leader_transfer_rejects_ineligible_and_duplicate_votes(
    service: MysticDungeonService,
) -> None:
    run = _start_team(service, 3)
    service.begin_leader_transfer(
        run,
        actor_id="member-2",
        nominee_id="member-2",
        deadline=NOW + timedelta(minutes=1),
    )

    with pytest.raises(PermissionError, match="eligible"):
        service.cast_vote(run, actor_id="leader", approve=True)
    service.cast_vote(run, actor_id="member-2", approve=True)
    with pytest.raises(ValueError, match="already voted"):
        service.cast_vote(run, actor_id="member-2", approve=False)


def test_failed_leader_transfer_restores_previous_phase(service: MysticDungeonService) -> None:
    run = _start_team(service, 3)
    service.begin_leader_transfer(
        run,
        actor_id="member-2",
        nominee_id="member-2",
        deadline=NOW + timedelta(minutes=1),
    )

    result = service.cast_vote(run, actor_id="member-2", approve=False)

    assert result.failed
    assert run.phase is DungeonPhase.READY_TO_ROLL
    assert run.active_vote is None
    assert run.leader_id == "leader"


def test_original_leader_valid_action_cancels_transfer_vote(service: MysticDungeonService) -> None:
    run = _start_team(service)
    service.begin_leader_transfer(
        run,
        actor_id="member-2",
        nominee_id="member-2",
        deadline=NOW + timedelta(minutes=1),
    )

    service.roll(run, actor_id="leader", dice_value=1)

    assert run.active_vote is None
    assert run.leader_id == "leader"
    assert run.phase is not DungeonPhase.AWAITING_LEADER_TRANSFER_VOTE


def test_two_member_abandon_vote_requires_unanimity(service: MysticDungeonService) -> None:
    run = _start_team(service)
    run.temporary_rewards_by_user = {"leader": [{"name": "reward"}], "member-2": []}
    service.begin_abandon_vote(run, actor_id="member-2", deadline=NOW + timedelta(minutes=1))

    first = service.cast_vote(run, actor_id="member-2", approve=True)
    second = service.cast_vote(run, actor_id="leader", approve=True)

    assert first.pending
    assert second.passed
    assert run.phase is DungeonPhase.ABANDONED
    assert run.temporary_rewards_by_user == {}


def test_three_member_abandon_vote_passes_with_two_approvals(service: MysticDungeonService) -> None:
    run = _start_team(service, 3)
    service.begin_abandon_vote(run, actor_id="member-3", deadline=NOW + timedelta(minutes=1))

    assert service.cast_vote(run, actor_id="member-3", approve=True).pending
    assert service.cast_vote(run, actor_id="leader", approve=True).passed
    assert run.phase is DungeonPhase.ABANDONED


def test_failed_abandon_vote_restores_previous_phase(service: MysticDungeonService) -> None:
    run = _start_team(service)
    service.begin_abandon_vote(run, actor_id="member-2", deadline=NOW + timedelta(minutes=1))

    result = service.cast_vote(run, actor_id="member-2", approve=False)

    assert result.failed
    assert run.phase is DungeonPhase.READY_TO_ROLL
    assert run.active_vote is None


def test_run_and_active_vote_round_trip_through_explicit_serialization(
    service: MysticDungeonService,
) -> None:
    run = _start_team(service, 3)
    service.begin_leader_transfer(
        run,
        actor_id="member-2",
        nominee_id="member-3",
        deadline=NOW + timedelta(minutes=1),
    )
    service.cast_vote(run, actor_id="member-2", approve=True)

    saved = MysticDungeonRun.from_dict(run.to_dict())

    assert saved == run
    assert saved.active_vote is not None
    assert saved.active_vote.kind is VoteKind.LEADER_TRANSFER
    assert saved.active_vote.approvals == {"member-2"}


def test_serialization_rejects_unknown_mode_risk_and_phase(service: MysticDungeonService) -> None:
    run = _start_team(service)
    for field, value in (("mode", "raid"), ("risk", "extreme"), ("phase", "lost")):
        payload = run.to_dict()
        payload[field] = value
        with pytest.raises(ValueError, match=f"unknown {field}"):
            MysticDungeonRun.from_dict(payload)


def test_serialization_rejects_unknown_vote_kind(service: MysticDungeonService) -> None:
    run = _start_team(service)
    vote = service.begin_abandon_vote(
        run,
        actor_id="member-2",
        deadline=NOW + timedelta(minutes=1),
    )
    payload = vote.to_dict()
    payload["kind"] = "mutiny"

    with pytest.raises(ValueError, match="unknown vote kind"):
        DungeonVote.from_dict(payload)


def test_serialization_rejects_invalid_roster_sizes_and_corrupt_vote_state(
    service: MysticDungeonService,
) -> None:
    solo, _ = service.create_solo_run(
        "run-solo-corrupt", "100", "solo", DungeonRisk.NORMAL, 4, 7, 11
    )
    solo_payload = solo.to_dict()
    solo_payload["members"]["intruder"] = {
        "user_id": "intruder",
        "nickname": "",
        "ready": True,
        "joined_at": NOW.isoformat(),
        "boss_segment_id": None,
        "boss_segment_cleared": False,
    }
    with pytest.raises(ValueError, match="solo roster"):
        MysticDungeonRun.from_dict(solo_payload)

    team = _start_team(service)
    corrupt_vote_payload = team.to_dict()
    corrupt_vote_payload["phase"] = DungeonPhase.AWAITING_LEADER_TRANSFER_VOTE.value
    corrupt_vote_payload["active_vote"] = None
    with pytest.raises(ValueError, match="active leader transfer vote"):
        MysticDungeonRun.from_dict(corrupt_vote_payload)


@pytest.mark.parametrize(
    ("vote_kind", "eligible_user_ids"),
    [
        (VoteKind.LEADER_TRANSFER, ["leader", "member-2"]),
        (VoteKind.LEADER_TRANSFER, ["member-2"]),
        (VoteKind.ABANDON, ["leader", "member-2"]),
    ],
)
def test_run_deserialization_rejects_corrupt_vote_eligibility(
    service: MysticDungeonService,
    vote_kind: VoteKind,
    eligible_user_ids: list[str],
) -> None:
    run = _start_team(service, 3)
    if vote_kind is VoteKind.LEADER_TRANSFER:
        service.begin_leader_transfer(
            run,
            actor_id="member-2",
            nominee_id="member-2",
            deadline=NOW + timedelta(minutes=1),
        )
    else:
        service.begin_abandon_vote(
            run,
            actor_id="member-2",
            deadline=NOW + timedelta(minutes=1),
        )
    payload = run.to_dict()
    active_vote = payload["active_vote"]
    assert isinstance(active_vote, dict)
    active_vote["eligible_user_ids"] = eligible_user_ids

    with pytest.raises(ValueError, match="eligible"):
        MysticDungeonRun.from_dict(payload)


@pytest.mark.parametrize("vote_kind", [VoteKind.LEADER_TRANSFER, VoteKind.ABANDON])
def test_expired_vote_fails_without_recording_late_ballot(
    catalog: MysticTemplateCatalog,
    vote_kind: VoteKind,
) -> None:
    service = MysticDungeonService(catalog, now=lambda: NOW)
    run = _start_team(service)
    if vote_kind is VoteKind.LEADER_TRANSFER:
        service.begin_leader_transfer(
            run,
            actor_id="member-2",
            nominee_id="member-2",
            deadline=NOW + timedelta(minutes=1),
        )
    else:
        service.begin_abandon_vote(
            run,
            actor_id="member-2",
            deadline=NOW + timedelta(minutes=1),
        )
    expired_service = MysticDungeonService(catalog, now=lambda: NOW + timedelta(minutes=2))

    result = expired_service.cast_vote(run, actor_id="member-2", approve=True)

    assert result.failed and not result.passed and not result.pending
    assert run.active_vote is None
    assert run.phase is DungeonPhase.READY_TO_ROLL
    assert run.leader_id == "leader"


def test_run_deserialization_rejects_abandon_vote_in_lobby(
    service: MysticDungeonService,
) -> None:
    run = _start_team(service)
    service.begin_abandon_vote(
        run,
        actor_id="member-2",
        deadline=NOW + timedelta(minutes=1),
    )
    payload = run.to_dict()
    payload["phase"] = DungeonPhase.LOBBY.value
    active_vote = payload["active_vote"]
    assert isinstance(active_vote, dict)
    active_vote["prior_phase"] = DungeonPhase.LOBBY.value

    with pytest.raises(ValueError, match="abandon vote.*phase"):
        MysticDungeonRun.from_dict(payload)


def test_run_deserialization_rejects_recursive_transfer_prior_phase(
    service: MysticDungeonService,
) -> None:
    run = _start_team(service)
    service.begin_leader_transfer(
        run,
        actor_id="member-2",
        nominee_id="member-2",
        deadline=NOW + timedelta(minutes=1),
    )
    payload = run.to_dict()
    active_vote = payload["active_vote"]
    assert isinstance(active_vote, dict)
    active_vote["prior_phase"] = DungeonPhase.AWAITING_LEADER_TRANSFER_VOTE.value

    with pytest.raises(ValueError, match="leader transfer vote.*prior phase"):
        MysticDungeonRun.from_dict(payload)


def test_run_deserialization_rejects_boss_vote_outside_boss_vote_phase(
    service: MysticDungeonService,
) -> None:
    run = _start_team(service)
    service.begin_abandon_vote(
        run,
        actor_id="member-2",
        deadline=NOW + timedelta(minutes=1),
    )
    payload = run.to_dict()
    active_vote = payload["active_vote"]
    assert isinstance(active_vote, dict)
    active_vote["kind"] = VoteKind.BOSS_CONTINUE.value

    with pytest.raises(ValueError, match="boss continuation vote.*phase"):
        MysticDungeonRun.from_dict(payload)


def test_same_content_seed_builds_same_node_categories(
    catalog: MysticTemplateCatalog,
) -> None:
    template = catalog.normal_templates()[0]
    config = default_mystic_gameplay_config()
    factory = MysticContentFactory()

    first = factory.instantiate(template, 32, content_seed=991, config=config)
    second = factory.instantiate(template, 32, content_seed=991, config=config)

    assert first == second
    graph = template.active_graph(32)
    assert first[graph.start_node_id].kind is NodeKind.START
    assert first[graph.boss_node_id].kind is NodeKind.BOSS
    assert all(
        first[node.node_id].kind in {NodeKind.RESOURCE, NodeKind.REST}
        for node in graph.nodes
        if node.is_safe and node.node_id != graph.start_node_id
    )


def test_content_factory_enforces_consecutive_combat_limit(
    catalog: MysticTemplateCatalog,
) -> None:
    template = catalog.high_risk_templates()[0]
    config = default_mystic_gameplay_config()
    contents = MysticContentFactory().instantiate(template, 48, content_seed=7, config=config)
    streak = 0

    for node in template.active_graph(48).nodes:
        if contents[node.node_id].kind is NodeKind.COMBAT:
            streak += 1
            assert streak <= config.consecutive_combat_limit
        else:
            streak = 0


def test_reward_node_rolls_once_per_fixed_member(
    service: MysticDungeonService,
) -> None:
    run = _start_team(service)
    node_id = next(
        node_id
        for node_id, content in run.node_contents.items()
        if content.kind is NodeKind.RESOURCE
    )
    run.current_node_id = node_id
    run.visited_node_ids.append(node_id)

    result = service.resolve_reward_node(run, node_id=node_id)

    assert set(result.rewards_by_user) == {"leader", "member-2"}
    assert len(result.rewards_by_user["leader"]) == 1
    assert len(result.rewards_by_user["member-2"]) == 1
    assert set(run.temporary_rewards_by_user) == {"leader", "member-2"}


def test_revisited_resolved_node_does_not_reward_twice(
    service: MysticDungeonService,
) -> None:
    run = _start_team(service)
    node_id = next(
        node_id
        for node_id, content in run.node_contents.items()
        if content.kind is NodeKind.RESOURCE
    )
    run.current_node_id = node_id
    run.visited_node_ids.append(node_id)
    service.resolve_reward_node(run, node_id=node_id)

    repeated = service.resolve_reward_node(run, node_id=node_id)

    assert repeated.rewards_by_user == {}
    assert all(len(items) == 1 for items in run.temporary_rewards_by_user.values())


def test_reward_ledger_serializes_settled_keys_in_stable_order() -> None:
    ledger = DungeonRewardLedger()
    assert ledger.add_personal("member", "node-9", {"name": "灵石", "amount": 10})
    assert not ledger.add_personal("member", "node-9", {"name": "灵石", "amount": 10})
    ledger.settled_node_keys.add("node-1:leader")

    restored = DungeonRewardLedger.from_dict(ledger.to_dict())

    assert restored == ledger
    assert ledger.to_dict()["settled_node_keys"] == ["node-1:leader", "node-9:member"]
