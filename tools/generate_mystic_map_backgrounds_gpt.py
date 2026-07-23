from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "assets" / "mystic_maps" / "manifest.json"
RUN_ROOT = ROOT / "ui-sprite-runs" / "2026-07-16-mystic-backgrounds"
SKILL_IMAGE_SCRIPT = Path("C:/Users/hszxjs/.codex/skills/ui-sprite-generator/scripts/openai_image.py")
IMAGE_ENV_FILE = RUN_ROOT.parent / ".env"
PUBLISHED_SIZE = (3840, 2160)

THEME_DETAILS = {
    "ancient_sect_ruins": "ruined mountain sect, broken ceremonial stairs, collapsed scripture halls, sword tombs and overgrown medicine terraces",
    "beast_tide": "vast beast-torn valley, trampled forests, bone ridges, scorched camps and winding river crossings",
    "ancient_cultivator_cave": "immortal cave estate with stone chambers, alchemy vaults, mirror pools, sealed bronze gates and star-lit stairs",
    "star_mine": "ancient celestial mine with open pits, dark tunnels, glowing ore seams, lava fissures and abandoned crane platforms",
    "soul_remnant": "fractured spirit realm with broken bridges, mist forests, soul-sand beaches, ruined divine halls and reflective lakes",
    "bronze_cloud_palace": "bronze palace complex suspended above clouds, monumental stairs, empty courts, broken pools and weathered ritual columns",
    "far_wilderness_boundary": "remote wilderness frontier of giant ravines, primeval forests, fossil plains and distant storm walls",
    "silent_black_mountain": "silent black mountain range with obsidian cliffs, dead forests, ash valleys and sealed cliff monasteries",
    "prime_star_mine": "primordial star-forged abyssal mine, meteor craters, luminous crystal canyons and ancient industrial terraces",
    "fallen_god_ruins": "colossal fallen deity ruins, shattered statues, divine weapon scars, sunken temples and luminous bloodstone fields",
    "immortal_sleep_valley": "serene but uncanny immortal sleeping valley, mist lakes, giant lotus terraces, sealed tomb gardens and moonlit cliffs",
    "reincarnation_tide_eye": "spiraling oceanic tide eye, circular island shelves, flooded shrines, whirlpool channels and pale reincarnation mist",
    "burial_sky_island": "floating burial island above a cloud abyss, broken mausoleums, suspended bridges, stone forests and celestial grave terraces",
    "qiongheng_ancient_hall": "vast ancient hall of cosmic balance, symmetrical courts, astronomical instruments, tilted causeways and ruined archives",
    "five_elements_land": "interlocking fire, water, wood, metal and earth biomes with clear transitions, elemental altars and traversable borders",
    "outer_battlefield": "otherworld battlefield with shattered fortresses, crater fields, alien rifts, abandoned siege lines and broken causeways",
    "nether_spring_demon_sect": "dark demonic sect around a nether spring, crimson halls, black waterfalls, talisman cliffs and poisoned terraces",
    "dust_ruins": "wind-scoured desert ruins, buried streets, eroded towers, dry canals and exposed underground chambers",
    "star_fate_lonely_realm": "isolated star-fate realm, dark celestial plains, luminous observatories, floating fragments and solitary causeways",
    "heaven_gate_battlefield": "ancient battlefield before a colossal heavenly gate, layered ramparts, ruined camps, siege roads and cloud cliffs",
    "seven_constellations_road": "celestial road across seven constellation islands, star bridges, observatory platforms and deep cosmic gaps",
    "bronze_cloud_deep": "deeper forbidden level of the bronze cloud palace, immense inner courts, sealed vaults, collapsed sky bridges and dark cloud wells",
    "thunder_pool": "ancient thunder domain with branching lightning rivers, stone islands, storm towers and conductive crystal ridges",
    "mystic_stone_gate": "mysterious stone gate realm, monumental portals, layered canyon paths, rune plateaus and hidden valley chambers",
    "starfall_remnant": "starfall wasteland with meteor trenches, glass plains, ruined watchtowers and glowing impact basins",
    "green_mystic_shadow": "shadowed green mystic sect, bamboo mountains, moss-covered halls, jade streams, hidden courtyards and misty cliff paths",
}


def build_prompt(theme_id: str, display_name: str, risk: str) -> str:
    details = THEME_DETAILS[theme_id]
    risk_text = "dangerous high-tier atmosphere" if risk == "high" else "adventurous mid-tier atmosphere"
    return (
        "MANDATORY OUTPUT FORMAT: landscape 16:9 aspect ratio. "
        "Do not generate a square or portrait image. "
        f"Chinese xianxia game dungeon map background for {display_name}, cinematic high-angle "
        "environmental concept art, wide 16:9 composition, one continuous explorable landscape, "
        "clear visual landmarks distributed across the whole frame, enough readable terrain to "
        f"place up to 48 small irregular route nodes, central and edge areas both usable, {risk_text}, {details}. "
        "Background plate only: no route lines, no nodes, no arrows, no UI, no text, no letters, "
        "no characters, no monsters, no watermark, no frame, no vignette, no blur."
    )


def build_spec(theme_id: str, display_name: str, risk: str) -> dict[str, Any]:
    risk_text = "high-risk" if risk == "high" else "normal-risk"
    details = THEME_DETAILS[theme_id]
    full_bbox = {"x": 0, "y": 0, "w": PUBLISHED_SIZE[0], "h": PUBLISHED_SIZE[1]}
    return {
        "schema_version": "1.2",
        "source_image": {
            "path": f"generated/{theme_id}.png",
            "width": PUBLISHED_SIZE[0],
            "height": PUBLISHED_SIZE[1],
        },
        "style": {
            "description": f"{display_name} {risk_text} xianxia dungeon map background plate.",
            "ui_style": "minimal game-map surface reserved for irregular route-node overlays",
            "background_style": f"cinematic high-angle xianxia environment, {details}",
            "palette": ["deep jade", "weathered bronze", "mineral blue", "muted crimson accents"],
            "materials": ["stone", "aged bronze", "mist", "water", "weathered vegetation", "luminous mineral traces"],
            "lighting": "directional atmospheric light with readable landmarks and gentle depth haze",
            "ornament_language": "restrained xianxia ruins, natural terrain silhouettes, no interface ornament",
            "negative_constraints": [
                "no route lines",
                "no route nodes",
                "no arrows",
                "no interface panels",
                "no text or letters",
                "no characters or monsters",
                "no watermark",
                "no border or vignette",
                "do not turn the image into a regular grid",
            ],
        },
        "background": {
            "description": "Continuous explorable terrain with landmark variation across the full canvas.",
            "visible_regions": [
                {"id": "full_canvas", "bbox": full_bbox},
                {"id": "edge_landmarks", "bbox": {"x": 0, "y": 0, "w": 3840, "h": 2160}},
            ],
            "occluded_regions": [
                {
                    "id": "route_overlay_area",
                    "bbox": {"x": 240, "y": 180, "w": 3360, "h": 1800},
                    "occluded_by": ["irregular_route_nodes", "route_edges", "status_overlay"],
                    "inpaint_hint": "Keep terrain detail coherent beneath future route nodes and colored edge overlays.",
                }
            ],
            "mask_strategy": "Generate the complete background plate without route graphics; overlay nodes and edges in the web renderer.",
        },
        "components": [
            {
                "id": "background_plate",
                "role": "custom_mystic_dungeon_background",
                "visual_description": f"Full-canvas {display_name} environment with {details}; continuous terrain and distinct landmarks.",
                "attached_decorations": [],
                "center": "filled",
                "surface_policy": "textured_fill",
                "occlusion": {
                    "status": "unoccluded",
                    "occluders": [],
                    "reconstruction": "Generate the complete unobstructed landscape across the source canvas.",
                },
                "render_pattern": "background_image",
                "render_params": {"fit": "cover", "position": "center"},
                "resolution_policy": {
                    "minimum_source_scale": 1,
                    "recommended_generation_scale": 1,
                    "target_px": {"w": PUBLISHED_SIZE[0], "h": PUBLISHED_SIZE[1]},
                    "allow_downscale": True,
                },
                "atlas_policy": {"group": "background_plates", "can_share_sheet": False, "minimum_gutter": 0},
                "states": ["default"],
                "companions": [],
            }
        ],
        "instances": [
            {
                "id": "background_plate_instance",
                "uses": "background_plate",
                "source_bbox": full_bbox,
                "layering": {"z_index": 0, "anchor": "top_left"},
                "display_size": {"w": PUBLISHED_SIZE[0], "h": PUBLISHED_SIZE[1]},
                "rendered": True,
            }
        ],
    }


def load_manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    themes = data.get("themes")
    if not isinstance(themes, dict):
        raise ValueError("mystic map manifest themes must be an object")
    if set(themes) != set(THEME_DETAILS):
        raise ValueError("theme detail dictionary must exactly match manifest themes")
    return data


def write_prompt(theme_id: str, prompt: str, *, run_root: Path = RUN_ROOT) -> Path:
    theme_dir = run_root / theme_id
    theme_dir.mkdir(parents=True, exist_ok=True)
    path = theme_dir / "prompt.md"
    path.write_text(prompt, encoding="utf-8")
    return path


def write_spec(
    theme_id: str,
    display_name: str,
    risk: str,
    *,
    run_root: Path = RUN_ROOT,
) -> Path:
    theme_dir = run_root / theme_id
    theme_dir.mkdir(parents=True, exist_ok=True)
    path = theme_dir / "spec.yaml"
    path.write_text(json.dumps(build_spec(theme_id, display_name, risk), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def prepare_theme(manifest: dict[str, Any], theme_id: str, *, run_root: Path = RUN_ROOT) -> Path:
    raw_theme = manifest["themes"][theme_id]
    display_name = str(raw_theme["display_name"])
    risk = str(raw_theme["risk"])
    write_prompt(theme_id, build_prompt(theme_id, display_name, risk), run_root=run_root)
    return write_spec(theme_id, display_name, risk, run_root=run_root)


def run_skill_generation(theme_dir: Path, *, model: str, quality: str) -> Path:
    if not SKILL_IMAGE_SCRIPT.is_file():
        raise FileNotFoundError(f"ui-sprite-generator helper not found: {SKILL_IMAGE_SCRIPT}")
    spec_path = theme_dir / "spec.yaml"
    prompt_path = theme_dir / "prompt.md"
    output_path = theme_dir / "background_plate.png"
    command = [
        sys.executable,
        str(SKILL_IMAGE_SCRIPT),
        "--env-file",
        str(IMAGE_ENV_FILE),
        "--run-dir",
        str(theme_dir),
        "--spec",
        str(spec_path),
        "--purpose",
        "background",
        "--size",
        "auto",
        "--quality",
        quality,
        "--model",
        model,
        "--mode",
        "auto",
        "--normalize-background-to-source",
        "--prompt-file",
        str(prompt_path),
        "--output",
        str(output_path),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    return output_path


def publish_image(source_path: Path, output_path: Path) -> str:
    try:
        with Image.open(source_path) as source:
            if source.size != PUBLISHED_SIZE:
                raise ValueError(f"generated image has size {source.size}, expected {PUBLISHED_SIZE}")
            if source.mode not in {"RGB", "RGBA"}:
                raise ValueError(f"generated image has mode {source.mode}, expected RGB or RGBA")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            source.save(output_path, format="PNG", optimize=True)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"generated image could not be decoded: {source_path}") from exc
    return hashlib.sha256(output_path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate mystic dungeon backgrounds with ui-sprite-generator.")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--theme-id", action="append", default=[])
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--model", default="gpt-image-2")
    parser.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="high")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = load_manifest()
        selected = sorted(manifest["themes"]) if args.all else list(dict.fromkeys(args.theme_id))
        if not selected:
            raise ValueError("select --all or at least one --theme-id")
        unknown = set(selected) - set(manifest["themes"])
        if unknown:
            raise ValueError(f"unknown theme ids: {sorted(unknown)}")
        for theme_id in selected:
            prepare_theme(manifest, theme_id)
        if args.prepare_only:
            print(f"prepared {len(selected)} specs and prompts under {RUN_ROOT}")
            return 0
        for theme_id in selected:
            theme_dir = RUN_ROOT / theme_id
            source_path = run_skill_generation(theme_dir, model=args.model, quality=args.quality)
            raw_theme = manifest["themes"][theme_id]
            output_path = MANIFEST_PATH.parent / str(raw_theme["background"])
            raw_theme["sha256"] = publish_image(source_path, output_path)
            MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"published {theme_id}")
        return 0
    except (FileNotFoundError, OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as exc:
        print(f"background generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
