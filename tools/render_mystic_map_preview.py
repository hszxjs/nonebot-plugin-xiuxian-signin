from __future__ import annotations

import argparse
import importlib
import sys
import types
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "mystic_map_preview_package"
if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(ROOT)]  # type: ignore[attr-defined]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package

mystic = importlib.import_module(f"{PACKAGE_NAME}.mystic_dungeon")
cards = importlib.import_module(f"{PACKAGE_NAME}.mystic_cards")

MysticMapRenderer = cards.MysticMapRenderer
MysticMapRenderModel = cards.MysticMapRenderModel
RenderedEdge = cards.RenderedEdge
RenderedNode = cards.RenderedNode
MysticTemplateCatalog = mystic.MysticTemplateCatalog
NodeKind = mystic.NodeKind


def _path_to_boss(graph: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    edges = sorted(getattr(graph, "edges"), key=lambda edge: edge.edge_id)
    outgoing: dict[str, list[object]] = {}
    for edge in edges:
        outgoing.setdefault(edge.source_node_id, []).append(edge)
    start = getattr(graph, "start_node_id")
    boss = getattr(graph, "boss_node_id")
    queue: deque[tuple[str, tuple[str, ...], tuple[str, ...]]] = deque([(start, (start,), ())])
    visited = {start}
    while queue:
        current, node_path, edge_path = queue.popleft()
        if current == boss:
            return node_path, edge_path
        for edge in outgoing.get(current, ()):
            if edge.target_node_id in visited:
                continue
            visited.add(edge.target_node_id)
            queue.append(
                (
                    edge.target_node_id,
                    (*node_path, edge.target_node_id),
                    (*edge_path, edge.edge_id),
                )
            )
    raise ValueError("catalog graph has no path from start to boss")


def _node_kind(node: object, start_id: str, boss_id: str) -> NodeKind:
    node_id = getattr(node, "node_id")
    if node_id == start_id:
        return NodeKind.START
    if node_id == boss_id:
        return NodeKind.BOSS
    allowed = sorted(
        (
            kind
            for kind in getattr(node, "allowed_kinds")
            if kind not in {NodeKind.START, NodeKind.BOSS}
        ),
        key=lambda kind: kind.value,
    )
    if not allowed:
        return NodeKind.RANDOM
    return allowed[sum(node_id.encode("utf-8")) % len(allowed)]


def build_model(
    catalog: object,
    theme_id: str,
    size: int,
    team_size: int,
) -> MysticMapRenderModel:
    theme = getattr(catalog, "themes")[theme_id]
    template = getattr(catalog, "templates")[theme.template_id]
    graph = template.active_graph(size)
    node_path, edge_path = _path_to_boss(graph)
    traversed_count = max(1, len(edge_path) // 2)
    traversed_edges = set(edge_path[:traversed_count])
    current_node_id = node_path[traversed_count]
    next_edges = {
        edge.edge_id
        for edge in graph.edges
        if edge.source_node_id == current_node_id
    }
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
    edges = tuple(
        RenderedEdge(
            edge_id=edge.edge_id,
            source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            state=(
                "traversed"
                if edge.edge_id in traversed_edges
                else "next"
                if edge.edge_id in next_edges
                else "future"
            ),
        )
        for edge in graph.edges
    )
    return MysticMapRenderModel(
        title=theme.display_name,
        subtitle=f"{size} 格秘境 · {theme.risk.value}",
        background_path=theme.background_path,
        nodes=nodes,
        edges=edges,
        current_node_id=current_node_id,
        team_size=team_size,
        temporary_reward_summary="灵石 120 · 修为 80",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a deterministic mystic map preview.")
    parser.add_argument("--theme", required=True)
    parser.add_argument("--size", required=True, type=int, choices=(24, 28, 32, 36, 40, 44, 48))
    parser.add_argument("--team-size", required=True, type=int, choices=(1, 2, 3))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    catalog = MysticTemplateCatalog.from_files()
    if args.theme not in catalog.themes:
        parser.error(f"unknown theme: {args.theme}")
    model = build_model(catalog, args.theme, args.size, args.team_size)
    renderer = MysticMapRenderer(allow_placeholder_background=True)
    image = renderer.render(model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
