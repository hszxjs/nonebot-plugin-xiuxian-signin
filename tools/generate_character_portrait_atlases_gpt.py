from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import time
import types
import urllib.error
import urllib.request
from io import BytesIO
from collections import OrderedDict
from datetime import date
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
PKG_NAME = "nonebot_plugin_xiuxian_signin"
RUNS_ROOT = ROOT / "build" / "imagegen-runs"
DEFAULT_RUN_DIR = RUNS_ROOT / f"{date.today():%Y-%m-%d}-character-portrait-atlases-gpt-image-2"
ASSET_ROOT = ROOT / "assets" / "character_portraits"
PORTRAIT_DIR = ASSET_ROOT / "portraits"
CODEX_HOME = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
OPENAI_IMAGE_CLI = CODEX_HOME / "skills" / "ui-sprite-generator" / "scripts" / "openai_image.py"

GRID_COLS = 5
PROBLEM_ROW_INSET_OVERRIDES = {
    "魔神": 0.115,
    "邪神": 0.115,
    "系统持有者": 0.115,
}


GRID_ROWS = 6
DEFAULT_ATLAS_SIZE = "1024x1536"
PORTRAIT_SIZE = (360, 520)


def load_builder() -> Any:
    pkg = types.ModuleType(PKG_NAME)
    pkg.__path__ = [str(ROOT)]
    sys.modules.setdefault(PKG_NAME, pkg)
    import importlib.util

    spec = importlib.util.spec_from_file_location("character_portrait_builder", ROOT / "tools" / "build_character_portraits.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load tools/build_character_portraits.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


builder = load_builder()


FACTION_VISUALS = {
    "妖兽": "ancient yaoshou beast lords, sharp horns, scaled or furred armor, fierce intelligent eyes, elemental qi, not cute",
    "散修": "wandering rogue cultivators, weathered cloaks, practical swords and spears, travel-worn xianxia robes",
    "佛修": "Buddhist monk-warrior cultivators, golden dharma halos, prayer beads, serene but battle-ready",
    "邪修": "shadow-path cultivators, dark crimson robes, sealed talisman smoke, cold elegant expressions, non-gory antagonist design",
    "邪神": "ominous fallen deity avatars, symbolic divine eyes, ruined shrine aura, ornate dark ceremonial robes, non-gory mythic design",
    "伪神": "false god claimants, cracked golden halos, imperial ritual crowns, suspicious divine glow, ceremonial antagonist design",
    "魔神": "mythic dark war-god avatars, black-red battle armor, horned crowns, ember aura, non-gory fantasy design",
    "域外天魔": "outer-realm celestial antagonists, starfield cracks, blue-black alien aura, sharp elegant silhouettes",
    "系统持有者": "system holder cultivators, teal holographic game-panel aura, xianxia robes with subtle interface light",
}

VISUAL_VARIATIONS = (
    "jade hairpin", "bronze mask", "long ribbon sleeves", "broken halo", "ink cloak", "ritual crown",
    "obsidian shoulder guard", "floating talisman", "star-silk scarf", "ancient sword hilt", "bead necklace",
    "cloud-pattern mantle", "lacquered gauntlet", "moonlit veil", "cracked jade pendant",
)


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def parse_size_text(value: str) -> tuple[int, int]:
    width_text, height_text = value.lower().split("x", 1)
    width = int(width_text)
    height = int(height_text)
    if width <= 0 or height <= 0:
        raise ValueError(value)
    return width, height


def choose_default_atlas_size(env_size: str | None) -> str:
    if not env_size or env_size == "auto":
        return DEFAULT_ATLAS_SIZE
    try:
        width, height = parse_size_text(env_size)
    except (TypeError, ValueError):
        return DEFAULT_ATLAS_SIZE
    if width > height:
        return f"{height}x{width}"
    return env_size


def ensure_run_dir(run_dir: Path) -> None:
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    gitignore = RUNS_ROOT / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")
    if not (RUNS_ROOT / ".env").exists():
        (RUNS_ROOT / ".env").write_text(
            "# Local image generation credentials. Do not commit this file.\n"
            "IMAGE_API_BASE_URL=\n"
            "IMAGE_API_KEY=\n"
            "IMAGE_API_MODEL=gpt-image-2\n",
            encoding="utf-8",
        )
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (run_dir / "atlas_raw").mkdir(parents=True, exist_ok=True)
    (run_dir / "processed").mkdir(parents=True, exist_ok=True)


def all_records() -> list[dict[str, Any]]:
    return builder.build_character_records()


def records_by_faction(records: list[dict[str, Any]]) -> OrderedDict[str, list[dict[str, Any]]]:
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for record in records:
        groups.setdefault(str(record["faction"]), []).append(record)
    return groups


def slug_for_faction(faction: str) -> str:
    for style in builder.FACTIONS:
        if style.name == faction:
            return str(style.key)
    return faction


def atlas_subject(records: list[dict[str, Any]]) -> str:
    lines = []
    for index, record in enumerate(records, start=1):
        row = (index - 1) // GRID_COLS + 1
        col = (index - 1) % GRID_COLS + 1
        faction = str(record.get("faction") or "")
        realm = str(record.get("realm") or "")
        archetype = str(record.get("archetype") or "")
        variation = VISUAL_VARIATIONS[(index - 1) % len(VISUAL_VARIATIONS)]
        if faction == "妖兽":
            cue = f"ancient beast-lord silhouette, {archetype}, elemental qi aura, distinct horns or crest"
        else:
            cue = f"{faction} role variant {index:02d}, {variation}, distinct face, distinct costume silhouette"
        lines.append(f"R{row}C{col} / portrait {index:02d}. ID {record['id']}; realm {realm}; visual cue: {cue}.")
    return "\n".join(lines)


def build_atlas_prompt_text(faction: str, records: list[dict[str, Any]], size: str) -> str:
    return (
        f"Create one complete character portrait atlas for the {faction} faction.\n"
        f"Canvas: {size}, portrait-oriented atlas.\n"
        f"Grid contract: exactly {GRID_COLS} columns by {GRID_ROWS} rows, exactly 30 equal cells, row-major order. "
        "Every cell must contain one distinct centered chest-up or waist-up character portrait. Use thin clean gutters or subtle frame lines between cells. "
        "Do not merge cells, do not leave empty cells, do not add extra portraits.\n\n"
        "Global style: high-quality Eastern xianxia fantasy anime illustration for a mature game, semi-realistic anime rendering, "
        "refined ink linework, painterly cel shading, ornate Chinese fantasy costume design, dramatic but readable faces, "
        "collectible battle-card portrait polish, consistent camera distance and lighting across all cells.\n"
        f"Faction visual direction: {FACTION_VISUALS.get(faction, 'eastern fantasy cultivators')}。\n"
        "Lighting and palette: mystic qi glow, cinematic rim light, restrained ink-wash shadows, faction-colored accent light, no flat cartoon mascot look.\n"
        "Forbidden: visible text, Chinese characters, numbers, labels, signatures, watermarks, logos, UI panels, gore, horror shock imagery, chibi proportions, cute mascot style, flat vector icon style, photorealistic actors.\n\n"
        "Characters, in exact row-major cell order:\n"
        f"{atlas_subject(records)}\n\n"
        "Quality check before final: 30 cells are visible; each cell has one unique character; heads are fully inside the cell; "
        "the style is Eastern fantasy anime rather than cartoon; no captions or labels are drawn."
    )


def build_atlas_job(faction: str, records: list[dict[str, Any]], model: str, size: str, quality: str) -> dict[str, Any]:
    slug = slug_for_faction(faction)
    return {
        "model": model,
        "faction": faction,
        "size": size,
        "quality": quality,
        "grid": {"columns": GRID_COLS, "rows": GRID_ROWS},
        "prompt_file": f"prompts/atlas_{slug}.prompt.md",
        "out": f"atlas_{slug}.png",
        "records": [
            {
                "index": index,
                "id": record["id"],
                "name": record["name"],
                "realm": record["realm"],
                "portrait": record["portrait"],
            }
            for index, record in enumerate(records, start=1)
        ],
    }


def write_prompt_files(run_dir: Path, groups: OrderedDict[str, list[dict[str, Any]]], size: str) -> None:
    prompt_dir = run_dir / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    for faction, records in groups.items():
        slug = slug_for_faction(faction)
        (prompt_dir / f"atlas_{slug}.prompt.md").write_text(
            build_atlas_prompt_text(faction, records, size),
            encoding="utf-8",
        )


def write_jsonl(path: Path, jobs: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(job, ensure_ascii=False) + "\n" for job in jobs), encoding="utf-8")


def write_atlas_map(path: Path, groups: OrderedDict[str, list[dict[str, Any]]], requested_size: str) -> None:
    payload = {
        "schema_version": "1.1",
        "requested_atlas_size": requested_size,
        "grid": {"columns": GRID_COLS, "rows": GRID_ROWS},
        "slice_policy": {
            "source": "gpt-image-2 atlas generated through ui-sprite-generator/scripts/openai_image.py",
            "cell_order": "row-major",
            "portrait_size": {"width": PORTRAIT_SIZE[0], "height": PORTRAIT_SIZE[1]},
        },
        "atlases": [],
    }
    for faction, records in groups.items():
        payload["atlases"].append(
            {
                "faction": faction,
                "atlas": f"atlas_{slug_for_faction(faction)}.png",
                "prompt": f"prompts/atlas_{slug_for_faction(faction)}.prompt.md",
                "records": [
                    {
                        "index": index,
                        "row": (index - 1) // GRID_COLS,
                        "column": (index - 1) % GRID_COLS,
                        "id": record["id"],
                        "name": record["name"],
                        "portrait": record["portrait"],
                    }
                    for index, record in enumerate(records, start=1)
                ],
            }
        )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_prompt_index(path: Path, groups: OrderedDict[str, list[dict[str, Any]]], model: str, size: str) -> None:
    lines = [
        "# gpt-image-2 角色半身像 Atlas 队列",
        "",
        f"模型：`{model}`",
        f"Atlas 尺寸：`{size}`，固定 `{GRID_COLS}x{GRID_ROWS}` 网格，每张 30 个角色。",
        "生成方式：每个势力生成 1 张 atlas，再机械切片为扑克牌大小半身像。",
        "",
        "| Atlas | Prompt | 势力 | 角色数 |",
        "| --- | --- | --- | --- |",
    ]
    for faction, records in groups.items():
        slug = slug_for_faction(faction)
        lines.append(f"| `atlas_{slug}.png` | `prompts/atlas_{slug}.prompt.md` | {faction} | {len(records)} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    src_w, src_h = image.size
    dst_w, dst_h = size
    src_ratio = src_w / src_h
    dst_ratio = dst_w / dst_h
    if src_ratio > dst_ratio:
        new_w = int(src_h * dst_ratio)
        left = (src_w - new_w) // 2
        image = image.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / dst_ratio)
        top = max(0, (src_h - new_h) // 2)
        image = image.crop((0, top, src_w, top + new_h))
    return image.resize(size, Image.Resampling.LANCZOS).convert("RGBA")


def contain_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGBA")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    return image


def add_card_finish(image: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = image.size
    draw.rounded_rectangle((4, 4, w - 5, h - 5), radius=18, outline=(245, 232, 198, 130), width=2)
    draw.rounded_rectangle((1, 1, w - 2, h - 2), radius=22, outline=(50, 42, 38, 165), width=3)
    return Image.alpha_composite(image, overlay)


def portrait_from_cell(cell: Image.Image) -> Image.Image:
    return cover_resize(cell, PORTRAIT_SIZE)


def cell_bounds(atlas_size: tuple[int, int], row: int, col: int, inset_ratio: float) -> tuple[int, int, int, int]:
    width, height = atlas_size
    x1 = round(col * width / GRID_COLS)
    x2 = round((col + 1) * width / GRID_COLS)
    y1 = round(row * height / GRID_ROWS)
    y2 = round((row + 1) * height / GRID_ROWS)
    inset_x = max(0, round((x2 - x1) * inset_ratio))
    inset_y = max(0, round((y2 - y1) * inset_ratio))
    if x2 - x1 > inset_x * 2 + 12:
        x1 += inset_x
        x2 -= inset_x
    if y2 - y1 > inset_y * 2 + 12:
        y1 += inset_y
        y2 -= inset_y
    return x1, y1, x2, y2

def effective_cell_inset_ratio(faction: str, index: int, default: float) -> float:
    if faction in PROBLEM_ROW_INSET_OVERRIDES and index >= GRID_COLS:
        return max(default, PROBLEM_ROW_INSET_OVERRIDES[faction])
    return default



def slice_atlases(
    groups: OrderedDict[str, list[dict[str, Any]]],
    raw_dir: Path,
    processed_dir: Path,
    cell_inset_ratio: float,
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    for faction, records in groups.items():
        atlas_path = raw_dir / f"atlas_{slug_for_faction(faction)}.png"
        if not atlas_path.is_file():
            raise FileNotFoundError(f"missing atlas: {atlas_path}")
        with Image.open(atlas_path) as source:
            atlas = source.convert("RGBA")
        for index, record in enumerate(records):
            row = index // GRID_COLS
            col = index % GRID_COLS
            inset_ratio = effective_cell_inset_ratio(faction, index, cell_inset_ratio)
            cell = atlas.crop(cell_bounds(atlas.size, row, col, inset_ratio))
            portrait_from_cell(cell).save(processed_dir / str(record["portrait"]))


def install_processed(records: list[dict[str, Any]], processed_dir: Path, clean: bool) -> None:
    PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)
    if clean:
        for path in PORTRAIT_DIR.glob("*.png"):
            path.unlink()
    for record in records:
        source = processed_dir / str(record["portrait"])
        if not source.is_file():
            raise FileNotFoundError(f"missing processed portrait: {source}")
        shutil.copy2(source, PORTRAIT_DIR / str(record["portrait"]))
    catalog_records = builder.build_character_records()
    builder.write_catalog(catalog_records)
    builder.write_contact_sheet(catalog_records)



def valid_image_bytes(data: bytes) -> bool:
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        return True
    except Exception:
        return False


def iter_response_strings(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_response_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_response_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def decode_possible_image_base64(value: str) -> bytes | None:
    text = value.strip()
    if text.startswith("data:image/") and "," in text:
        text = text.split(",", 1)[1]
    if len(text) < 200:
        return None
    if not re.fullmatch(r"[A-Za-z0-9+/=_\-\s]+", text):
        return None
    for candidate in (text, text.replace("-", "+").replace("_", "/")):
        try:
            data = base64.b64decode(candidate, validate=False)
        except (TypeError, ValueError):
            continue
        if valid_image_bytes(data):
            return data
    return None


def sanitized_response_shape(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "..."
    if isinstance(value, dict):
        return {key: sanitized_response_shape(child, depth + 1) for key, child in value.items()}
    if isinstance(value, list):
        return [sanitized_response_shape(value[0], depth + 1)] if value else []
    if isinstance(value, str):
        return f"<str len={len(value)}>"
    return type(value).__name__


def extract_image_bytes_flexible(response_body: bytes, content_type: str) -> bytes:
    if content_type.startswith("image/") and valid_image_bytes(response_body):
        return response_body
    try:
        payload = json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("image API returned non-JSON and non-image response") from exc

    for path, value in iter_response_strings(payload):
        if value.startswith("http://") or value.startswith("https://"):
            try:
                with urllib.request.urlopen(value, timeout=60) as response:
                    data = response.read()
            except (urllib.error.URLError, TimeoutError):
                continue
            if valid_image_bytes(data):
                print(f"extracted image URL at {path}")
                return data
        data = decode_possible_image_base64(value)
        if data:
            print(f"extracted base64 image at {path}")
            return data

    shape = json.dumps(sanitized_response_shape(payload), ensure_ascii=False)[:1200]
    raise RuntimeError(f"image API response did not contain recognizable image bytes; shape={shape}")


def direct_image_payload(args: argparse.Namespace, job: dict[str, Any], response_format: str | None = None) -> dict[str, Any]:
    env_values = read_env_file(RUNS_ROOT / ".env")
    prompt = (args.run_dir / str(job["prompt_file"])).read_text(encoding="utf-8")
    payload: dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
        "size": args.size,
        "quality": args.quality,
        "n": 1,
    }
    selected_response_format = response_format or args.response_format or env_values.get("IMAGE_API_RESPONSE_FORMAT")
    if selected_response_format:
        payload["response_format"] = selected_response_format
    return payload


def call_direct_image_api(args: argparse.Namespace, job: dict[str, Any], response_format: str | None = None) -> None:
    env_values = read_env_file(RUNS_ROOT / ".env")
    base_url = env_values.get("IMAGE_API_BASE_URL")
    api_key = env_values.get("IMAGE_API_KEY")
    if not base_url:
        raise RuntimeError(f"IMAGE_API_BASE_URL is not set in {RUNS_ROOT / '.env'}")
    if not api_key:
        raise RuntimeError(f"IMAGE_API_KEY is not set in {RUNS_ROOT / '.env'}")
    timeout = int(args.timeout or env_values.get("IMAGE_API_TIMEOUT") or 180)
    body = json.dumps(direct_image_payload(args, job, response_format=response_format), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base_url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read()
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"image API HTTP error: response status {exc.code}; {detail}") from exc
    except (urllib.error.URLError, TimeoutError, http.client.RemoteDisconnected) as exc:
        raise RuntimeError(f"image API request failed: {exc}") from exc

    image_bytes = extract_image_bytes_flexible(response_body, content_type)
    output = args.run_dir / "atlas_raw" / str(job["out"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(image_bytes)
    print(f"Saved image through direct IMAGE_API_* driver: {output}")


def call_direct_image_api_with_retries(args: argparse.Namespace, job: dict[str, Any], response_format: str | None = None) -> None:
    attempts = max(1, args.retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            call_direct_image_api(args, job, response_format=response_format)
            return
        except RuntimeError as exc:
            if attempt >= attempts:
                raise
            delay = min(20, 4 * attempt)
            print(f"direct IMAGE_API_* attempt {attempt} failed for {job['out']}: {exc}; retrying in {delay}s")
            time.sleep(delay)

def image_command(args: argparse.Namespace, job: dict[str, Any], response_format: str | None = None) -> list[str]:
    command = [
        sys.executable,
        str(OPENAI_IMAGE_CLI),
        "--run-dir",
        str(args.run_dir),
        "--mode",
        "generations",
        "--prompt-file",
        str(args.run_dir / str(job["prompt_file"])),
        "--output",
        str(args.run_dir / "atlas_raw" / str(job["out"])),
        "--purpose",
        "atlas",
        "--model",
        args.model,
        "--size",
        args.size,
        "--quality",
        args.quality,
    ]
    selected_response_format = response_format or args.response_format
    if selected_response_format:
        command.extend(["--response-format", selected_response_format])
    if args.timeout:
        command.extend(["--timeout", str(args.timeout)])
    return command


def run_openai_image_cli(args: argparse.Namespace, jobs: list[dict[str, Any]], raw_dir: Path) -> None:
    if args.api_driver == "helper" and not OPENAI_IMAGE_CLI.is_file():
        raise FileNotFoundError(f"missing ui-sprite-generator image helper: {OPENAI_IMAGE_CLI}")
    for job in jobs:
        output = raw_dir / str(job["out"])
        if output.exists() and not args.force:
            print(f"skip existing atlas: {output}")
            continue
        if args.dry_run:
            if args.api_driver == "direct":
                print("DRY RUN direct IMAGE_API_*:", output)
            else:
                print("DRY RUN:", subprocess.list2cmdline(image_command(args, job)))
            continue
        if args.api_driver == "direct":
            call_direct_image_api_with_retries(args, job)
            continue

        command = image_command(args, job)
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            print(f"ui-sprite-generator helper failed for {job['out']}; retrying with direct IMAGE_API_* driver")
            try:
                call_direct_image_api_with_retries(args, job)
                continue
            except RuntimeError as direct_exc:
                print(f"direct IMAGE_API_* fallback failed: {direct_exc}")
            if not args.url_fallback or args.response_format == "url":
                raise
            fallback = image_command(args, job, response_format="url")
            print(f"retrying {job['out']} with helper response_format=url")
            subprocess.run(fallback, check=True)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a few gpt-image-2 atlas sheets and slice them into 270 portraits.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--model", default=None)
    parser.add_argument("--size", default=None, help="Defaults to IMAGE_API_SIZE rotated to portrait, or 1024x1536.")
    parser.add_argument("--quality", default=None, choices=["low", "medium", "high", "auto"])
    parser.add_argument("--response-format", choices=["b64_json", "url"], default=None)
    parser.add_argument("--api-driver", choices=["helper", "direct"], default="helper")
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--retries", type=int, default=2, help="Retries per atlas for transient API disconnects.")
    parser.add_argument("--faction", help="Only generate/slice one faction, e.g. 妖兽")
    parser.add_argument("--cell-inset-ratio", type=float, default=0.065)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--process-only", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--no-url-fallback", dest="url_fallback", action="store_false")
    parser.set_defaults(url_fallback=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_run_dir(args.run_dir)
    env_values = read_env_file(RUNS_ROOT / ".env")
    if args.model is None:
        args.model = env_values.get("IMAGE_API_MODEL") or "gpt-image-2"
    if args.size is None:
        args.size = choose_default_atlas_size(env_values.get("IMAGE_API_SIZE"))
    if args.quality is None:
        args.quality = env_values.get("IMAGE_API_QUALITY") or "high"
    if args.timeout is None and env_values.get("IMAGE_API_TIMEOUT"):
        args.timeout = int(env_values["IMAGE_API_TIMEOUT"])

    records = all_records()
    groups = records_by_faction(records)
    if args.faction:
        groups = OrderedDict((faction, items) for faction, items in groups.items() if faction == args.faction)
        if not groups:
            raise SystemExit(f"unknown faction: {args.faction}")
        records = [record for items in groups.values() for record in items]

    jobs = [build_atlas_job(faction, items, args.model, args.size, args.quality) for faction, items in groups.items()]
    input_jsonl = args.run_dir / "character_portrait_atlases.gpt-image-2.jsonl"
    atlas_map = args.run_dir / "character_portrait_atlas_map.json"
    prompt_index = args.run_dir / "character_portrait_atlases.gpt-image-2.md"
    raw_dir = args.run_dir / "atlas_raw"
    processed_dir = args.run_dir / "processed"

    write_prompt_files(args.run_dir, groups, args.size)
    write_jsonl(input_jsonl, jobs)
    write_atlas_map(atlas_map, groups, args.size)
    write_prompt_index(prompt_index, groups, args.model, args.size)

    if not args.prepare_only and not args.process_only:
        run_openai_image_cli(args, jobs, raw_dir)
    if args.process_only or (not args.prepare_only and not args.dry_run):
        slice_atlases(groups, raw_dir, processed_dir, args.cell_inset_ratio)
        if args.install:
            install_processed(records, processed_dir, clean=not args.faction)

    print(f"prepared {len(jobs)} atlas jobs for {sum(len(items) for items in groups.values())} portraits")
    print(input_jsonl)
    print(atlas_map)


if __name__ == "__main__":
    main()
