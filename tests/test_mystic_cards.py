from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

from PIL import Image, ImageDraw


PACKAGE_NAME = "mystic_cards_test_package"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package

mystic = importlib.import_module(f"{PACKAGE_NAME}.mystic_dungeon")
cards = importlib.import_module(f"{PACKAGE_NAME}.mystic_cards")
backgrounds = importlib.import_module(
    f"{PACKAGE_NAME}.tools.generate_mystic_map_backgrounds_gpt"
)

MysticTemplateCatalog = mystic.MysticTemplateCatalog
NodeKind = mystic.NodeKind
MysticMapRenderer = cards.MysticMapRenderer
MysticMapRenderModel = cards.MysticMapRenderModel
RenderedEdge = cards.RenderedEdge
RenderedNode = cards.RenderedNode


def _background(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "background.png"
    image = Image.new("RGB", (3840, 2160), (18, 32, 50))
    draw = ImageDraw.Draw(image)
    for y in range(0, 2160, 12):
        draw.rectangle(
            (0, y, 3840, min(2160, y + 11)),
            fill=(18 + y // 24 % 90, 32 + y // 18 % 110, 50 + y // 12 % 120),
        )
    image.save(path)
    return path


def _node_kind(node: object, start_id: str, boss_id: str) -> object:
    node_id = getattr(node, "node_id")
    if node_id == start_id:
        return NodeKind.START
    if node_id == boss_id:
        return NodeKind.BOSS
    allowed = getattr(node, "allowed_kinds")
    return next(kind for kind in allowed if kind not in {NodeKind.START, NodeKind.BOSS})


def _catalog_model(tmp_path: Path, *, size: int, team_size: int) -> MysticMapRenderModel:
    catalog = MysticTemplateCatalog.from_files()
    theme = catalog.themes["ancient_sect_ruins"]
    graph = catalog.templates[theme.template_id].active_graph(size)
    nodes = tuple(
        RenderedNode(
            node_id=node.node_id,
            x=node.x,
            y=node.y,
            kind=_node_kind(node, graph.start_node_id, graph.boss_node_id),
            label=node.node_id,
        )
        for node in graph.nodes
    )
    traversed_ids = {edge.edge_id for edge in graph.edges[:3]}
    current_node_id = graph.edges[2].target_node_id
    next_ids = {
        edge.edge_id
        for edge in graph.edges
        if edge.source_node_id == current_node_id
    }
    edges = tuple(
        RenderedEdge(
            edge_id=edge.edge_id,
            source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            state=(
                "traversed"
                if edge.edge_id in traversed_ids
                else "next"
                if edge.edge_id in next_ids
                else "future"
            ),
        )
        for edge in graph.edges
    )
    return MysticMapRenderModel(
        title=theme.display_name,
        subtitle=f"{size} 格秘境",
        background_path=_background(tmp_path),
        nodes=nodes,
        edges=edges,
        current_node_id=current_node_id,
        team_size=team_size,
        temporary_reward_summary="灵石 120 · 修为 80",
    )


def _colored_route_model(tmp_path: Path) -> MysticMapRenderModel:
    nodes = (
        RenderedNode("start", 0.10, 0.55, NodeKind.START, "入口"),
        RenderedNode("current", 0.35, 0.42, NodeKind.RANDOM, "当前"),
        RenderedNode("battle", 0.65, 0.55, NodeKind.COMBAT, "战斗"),
        RenderedNode("boss", 0.90, 0.42, NodeKind.BOSS, "首领"),
    )
    edges = (
        RenderedEdge("walked", "start", "current", "traversed"),
        RenderedEdge("next", "current", "battle", "next"),
        RenderedEdge("future", "battle", "boss", "future"),
    )
    return MysticMapRenderModel(
        title="路线状态",
        subtitle="颜色验证",
        background_path=_background(tmp_path),
        nodes=nodes,
        edges=edges,
        current_node_id="current",
        team_size=2,
        temporary_reward_summary="灵石 20",
    )


def test_renderer_contains_all_active_nodes_for_24_and_48_sizes(tmp_path: Path) -> None:
    renderer = MysticMapRenderer()
    for size in (24, 48):
        model = _catalog_model(tmp_path / str(size), size=size, team_size=3)
        image = renderer.render(model)

        assert image.size == (1600, 900)
        for node in model.nodes:
            assert renderer.node_box(node, model).within(image.size)


def test_route_colors_and_icon_sizes_are_stable(tmp_path: Path) -> None:
    renderer = MysticMapRenderer()
    model = _colored_route_model(tmp_path)
    image = renderer.render(model)

    assert image.getpixel(renderer.edge_midpoint(model.edges[0], model)) == renderer.TRAVERSED_GREEN
    assert image.getpixel(renderer.edge_midpoint(model.edges[1], model)) == renderer.NEXT_RED
    assert renderer.REGULAR_NODE_SIZE == 20
    assert renderer.BOSS_NODE_SIZE == 25


def test_crop_box_is_clamped_and_uses_sixteen_by_nine_ratio(tmp_path: Path) -> None:
    renderer = MysticMapRenderer()
    model = _catalog_model(tmp_path, size=24, team_size=1)

    left, top, right, bottom = renderer.crop_box(model)

    assert 0 <= left < right <= 3840
    assert 0 <= top < bottom <= 2160
    assert abs(((right - left) / (bottom - top)) - (16 / 9)) < 0.01


def test_rendered_map_is_not_blank(tmp_path: Path) -> None:
    renderer = MysticMapRenderer()
    image = renderer.render(_catalog_model(tmp_path, size=48, team_size=2))
    colors = image.convert("RGB").getcolors(maxcolors=image.width * image.height)

    assert colors is not None
    assert len(colors) > 50


def test_text_fallback_contains_position_team_and_reward(tmp_path: Path) -> None:
    renderer = MysticMapRenderer()
    model = _colored_route_model(tmp_path)

    fallback = renderer.text_fallback(model)

    assert "current" in fallback
    assert "2/3" in fallback
    assert "灵石 20" in fallback


def test_background_prompts_cover_every_manifest_theme() -> None:
    manifest = json.loads(
        (PACKAGE_ROOT / "assets" / "mystic_maps" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    theme_ids = set(manifest["themes"])

    assert theme_ids == set(backgrounds.THEME_DETAILS)
    for theme_id, raw_theme in manifest["themes"].items():
        prompt = backgrounds.build_prompt(
            theme_id,
            str(raw_theme["display_name"]),
            str(raw_theme["risk"]),
        )
        assert "MANDATORY OUTPUT FORMAT: landscape 16:9 aspect ratio" in prompt
        assert "Do not generate a square or portrait image" in prompt
        assert "up to 48 small irregular route nodes" in prompt
        assert "no route lines, no nodes, no arrows" in prompt
        assert backgrounds.THEME_DETAILS[theme_id] in prompt


def test_background_spec_matches_ui_sprite_contract() -> None:
    spec = backgrounds.build_spec("ancient_sect_ruins", "上古宗门遗址", "normal")

    assert spec["schema_version"] == "1.2"
    assert spec["source_image"] == {
        "path": "generated/ancient_sect_ruins.png",
        "width": 3840,
        "height": 2160,
    }
    assert spec["background"]["visible_regions"]
    assert spec["background"]["occluded_regions"]
    assert spec["components"][0]["render_pattern"] == "background_image"
    assert spec["instances"][0]["uses"] == "background_plate"


def test_write_spec_creates_skill_run_contract(tmp_path: Path) -> None:
    path = backgrounds.write_spec(
        "ancient_sect_ruins",
        "上古宗门遗址",
        "normal",
        run_root=tmp_path,
    )

    assert path == tmp_path / "ancient_sect_ruins" / "spec.yaml"
    spec = json.loads(path.read_text(encoding="utf-8"))
    assert spec["schema_version"] == "1.2"


def test_publish_image_requires_skill_normalized_dimensions(tmp_path: Path) -> None:
    source = tmp_path / "background_plate.png"
    output = tmp_path / "published.png"
    Image.new("RGB", (3840, 2160), (18, 32, 50)).save(source)

    digest = backgrounds.publish_image(source, output)

    assert output.exists()
    assert len(digest) == 64
