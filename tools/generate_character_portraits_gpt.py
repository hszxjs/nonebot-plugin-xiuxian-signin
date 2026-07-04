from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import types
from datetime import date
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PKG_NAME = "nonebot_plugin_xiuxian_signin"
CARD_SIZE = (360, 520)
GPT_SIZE = "768x1152"
RUNS_ROOT = ROOT / "build" / "imagegen-runs"
DEFAULT_RUN_DIR = RUNS_ROOT / f"{date.today():%Y-%m-%d}-character-portraits-gpt-image-2"
ASSET_ROOT = ROOT / "assets" / "character_portraits"
PORTRAIT_DIR = ASSET_ROOT / "portraits"
CODEX_HOME = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
IMAGE_GEN_CLI = CODEX_HOME / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"


def load_build_module() -> Any:
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


builder = load_build_module()


FACTION_VISUALS = {
    "妖兽": "ancient yaoshou beast sovereign, sharp horns, scale armor, fierce intelligent eyes, elemental aura, not cute",
    "散修": "wandering rogue cultivator, weathered cloak, practical sword or spear, travel-worn xianxia robes",
    "佛修": "Buddhist cultivator, monk-warrior robes, golden dharma halo, prayer beads, serene but battle-ready",
    "邪修": "evil cultivator, dark crimson robes, forbidden talisman smoke, dangerous elegant expression",
    "邪神": "heretical god avatar, unsettling divine eyes, ruined shrine aura, ornate dark ceremonial robes",
    "伪神": "false god claimant, cracked golden halo, imperial ritual crown, bright but suspicious divine glow",
    "魔神": "demon god warrior, black-red battle armor, horns or crown, abyssal flame aura",
    "域外天魔": "outer-realm celestial demon, starfield cracks, blue-black alien aura, sharp elegant silhouette",
    "系统持有者": "system holder cultivator, teal holographic game panel aura, xianxia robe mixed with subtle interface light",
}


def normalize_openai_base_url(value: str) -> str:
    url = str(value or "").strip().rstrip("/")
    for suffix in ("/images/generations", "/images/edits"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values


def ensure_run_files(run_dir: Path) -> None:
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    gitignore = RUNS_ROOT / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")
    env_path = RUNS_ROOT / ".env"
    if not env_path.exists():
        env_path.write_text(
            "# Local image generation credentials. Do not commit this file.\n"
            "# Used by tools/generate_character_portraits_gpt.py when invoking the imagegen CLI.\n"
            "OPENAI_API_KEY=\n"
            "IMAGE_API_MODEL=gpt-image-2\n",
            encoding="utf-8",
        )
    elif "OPENAI_API_KEY=" not in env_path.read_text(encoding="utf-8"):
        with env_path.open("a", encoding="utf-8") as handle:
            handle.write("\n# Used by tools/generate_character_portraits_gpt.py when invoking the imagegen CLI.\nOPENAI_API_KEY=\n")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    (run_dir / "processed").mkdir(parents=True, exist_ok=True)


def style_prompt(record: dict[str, Any]) -> str:
    faction = str(record.get("faction") or "")
    visual = FACTION_VISUALS.get(faction, "eastern fantasy cultivator")
    return (
        "high-quality Eastern xianxia fantasy anime illustration, mature game character portrait, "
        "semi-realistic anime rendering, refined ink linework, painterly cel shading, ornate Chinese fantasy costume, "
        "cinematic rim light, rich but controlled detail, unified collectible card portrait style; "
        f"{visual}"
    )


def subject_prompt(record: dict[str, Any]) -> str:
    faction = str(record.get("faction") or "")
    name = str(record.get("name") or "")
    realm = str(record.get("realm") or "")
    archetype = str(record.get("archetype") or "")
    story = str(record.get("story") or "")
    if faction == "妖兽":
        return (
            f"{name}, a {archetype} mythical beast boss at {realm}; upper-body bust portrait, "
            "bestial head and powerful shoulders visible, ornate natural armor, elemental aura tied to its bloodline; "
            f"lore cue: {story}"
        )
    return (
        f"{name}, {faction} faction enemy character at {realm}, archetype {archetype}; "
        "waist-up character portrait, face clearly visible, elegant xianxia silhouette, hands or weapon partially visible; "
        f"lore cue: {story}"
    )


def build_job(record: dict[str, Any], size: str, quality: str, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "prompt": "Create one polished game-ready character portrait for a cultivation RPG enemy roster.",
        "use_case": "stylized-concept",
        "subject": subject_prompt(record),
        "style": style_prompt(record),
        "composition": (
            "vertical portrait, centered chest-up to waist-up framing, full head visible, no cropped face, "
            "single character only, poker-card aspect composition, clean silhouette, no text area"
        ),
        "lighting": "mystic xianxia aura glow with soft atmospheric depth, readable face and costume, dramatic but not overexposed",
        "palette": "muted ink-wash base with faction-colored accent light; consistent across the whole roster",
        "materials": "silk robes, jade, bronze, talismans, scales, horns, armor, ethereal qi effects as appropriate",
        "constraints": (
            "no visible text, no Chinese characters, no labels, no watermark, no logo, no UI, no chibi, "
            "no mascot style, no simplified cartoon, no low-detail icon, no duplicate characters, no extra people"
        ),
        "negative": (
            "cartoon mascot, childlike proportions, round blob face, flat vector icon, western superhero, photorealistic actor, "
            "text, label, signature, watermark, cropped head, full-body tiny figure, cluttered background"
        ),
        "size": size,
        "quality": quality,
        "output_format": "png",
        "out": str(record.get("portrait") or f"{record['id']}.png"),
    }


def selected_records(faction: str | None, limit: int | None) -> list[dict[str, Any]]:
    records = builder.build_character_records()
    if faction:
        records = [record for record in records if str(record.get("faction")) == faction]
    if limit is not None:
        records = records[: max(0, limit)]
    return records


def write_jsonl(path: Path, jobs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(job, ensure_ascii=False) + "\n" for job in jobs), encoding="utf-8")


def write_prompt_index(path: Path, records: list[dict[str, Any]]) -> None:
    lines = [
        "# gpt-image-2 角色半身像生成队列",
        "",
        "模型：`gpt-image-2`",
        f"目标尺寸：先生成 `{GPT_SIZE}`，再裁切缩放为 `{CARD_SIZE[0]}x{CARD_SIZE[1]}`。",
        "",
        "| ID | 名称 | 势力 | 境界 | 输出 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(f"| `{record['id']}` | {record['name']} | {record['faction']} | {record['realm']} | `{record['portrait']}` |")
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


def add_subtle_card_finish(image: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = image.size
    draw.rounded_rectangle((5, 5, w - 6, h - 6), radius=18, outline=(242, 230, 198, 150), width=2)
    draw.rounded_rectangle((1, 1, w - 2, h - 2), radius=22, outline=(56, 42, 36, 170), width=3)
    return Image.alpha_composite(image, overlay)


def process_raw_images(records: list[dict[str, Any]], raw_dir: Path, processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    for record in records:
        filename = str(record["portrait"])
        raw_path = raw_dir / filename
        if not raw_path.is_file():
            missing.append(filename)
            continue
        image = add_subtle_card_finish(cover_resize(Image.open(raw_path), CARD_SIZE))
        image.save(processed_dir / filename)
    if missing:
        preview = ", ".join(missing[:8])
        raise FileNotFoundError(f"missing {len(missing)} raw images, first missing: {preview}")


def install_processed_images(records: list[dict[str, Any]], processed_dir: Path) -> None:
    PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)
    for record in records:
        filename = str(record["portrait"])
        shutil.copy2(processed_dir / filename, PORTRAIT_DIR / filename)
    builder.write_catalog(builder.build_character_records())


def run_imagegen_cli(args: argparse.Namespace, input_jsonl: Path, raw_dir: Path) -> None:
    if not IMAGE_GEN_CLI.is_file():
        raise FileNotFoundError(f"imagegen CLI not found: {IMAGE_GEN_CLI}")
    env = os.environ.copy()
    env_file_values = read_env_file(RUNS_ROOT / ".env")
    if not env.get("OPENAI_API_KEY") and env_file_values.get("OPENAI_API_KEY"):
        env["OPENAI_API_KEY"] = env_file_values["OPENAI_API_KEY"]
    if not env.get("OPENAI_API_KEY") and env_file_values.get("IMAGE_API_KEY"):
        env["OPENAI_API_KEY"] = env_file_values["IMAGE_API_KEY"]
    if env_file_values.get("IMAGE_API_BASE_URL") and not env.get("OPENAI_BASE_URL"):
        env["OPENAI_BASE_URL"] = normalize_openai_base_url(env_file_values["IMAGE_API_BASE_URL"])
    if not env.get("OPENAI_API_KEY") and not args.dry_run:
        raise RuntimeError(
            f"OPENAI_API_KEY is not set. Put it in {RUNS_ROOT / '.env'} or set it as a system environment variable."
        )
    command = [
        sys.executable,
        str(IMAGE_GEN_CLI),
        "generate-batch",
        "--model",
        args.model,
        "--size",
        args.size,
        "--quality",
        args.quality,
        "--output-format",
        "png",
        "--input",
        str(input_jsonl),
        "--out-dir",
        str(raw_dir),
        "--concurrency",
        str(args.concurrency),
        "--fail-fast",
    ]
    if args.force:
        command.append("--force")
    if args.dry_run:
        command.append("--dry-run")
    subprocess.run(command, check=True, env=env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate character portraits through the bundled gpt-image-2 CLI workflow.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--model", default=None)
    parser.add_argument("--size", default=GPT_SIZE)
    parser.add_argument("--quality", default="medium", choices=["low", "medium", "high", "auto"])
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--faction", help="Only generate one faction, e.g. 妖兽")
    parser.add_argument("--limit", type=int, help="Only prepare/run the first N selected records")
    parser.add_argument("--prepare-only", action="store_true", help="Write prompt JSONL only; do not call the API.")
    parser.add_argument("--dry-run", action="store_true", help="Call image_gen.py with --dry-run; no API request.")
    parser.add_argument("--force", action="store_true", help="Pass --force to image_gen.py for reruns.")
    parser.add_argument("--process-only", action="store_true", help="Only process existing raw outputs into 360x520 portraits.")
    parser.add_argument("--install", action="store_true", help="After processing, copy images into assets/character_portraits/portraits.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_run_files(args.run_dir)
    env_file_values = read_env_file(RUNS_ROOT / ".env")
    if args.model is None:
        args.model = env_file_values.get("IMAGE_API_MODEL") or "gpt-image-2"
    records = selected_records(args.faction, args.limit)
    jobs = [build_job(record, args.size, args.quality, args.model) for record in records]
    input_jsonl = args.run_dir / "character_portraits.gpt-image-2.jsonl"
    prompt_index = args.run_dir / "character_portraits.gpt-image-2.md"
    raw_dir = args.run_dir / "raw"
    processed_dir = args.run_dir / "processed"
    write_jsonl(input_jsonl, jobs)
    write_prompt_index(prompt_index, records)
    if not args.prepare_only and not args.process_only:
        run_imagegen_cli(args, input_jsonl, raw_dir)
    if args.process_only or (not args.prepare_only and not args.dry_run):
        process_raw_images(records, raw_dir, processed_dir)
        if args.install:
            install_processed_images(records, processed_dir)
    print(f"prepared {len(records)} gpt-image-2 jobs")
    print(input_jsonl)
    print(prompt_index)


if __name__ == "__main__":
    main()
