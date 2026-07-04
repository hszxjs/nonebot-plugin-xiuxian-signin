from __future__ import annotations

import argparse
import json
import re
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ICON_ROOT = ROOT / "assets" / "realm_quality_icons"
DEFAULT_RUN_DIR = ROOT / "assets" / "ui_sprite_runs" / "2026-07-01-realm-quality-icons"
REPORT_PATH = ROOT / "build" / "reports" / "realm_quality" / "realm_quality_recut_report.json"
PREVIEW_PATH = ROOT / "build" / "reports" / "realm_quality" / "realm_quality_recut_preview.png"
CELL_RE = re.compile(
    r"Cell\s+(?P<cell>\d+)\s+\(row\s+(?P<row>\d+),\s+col\s+(?P<col>\d+)\),"
    r"\s+output file\s+(?P<file>quality_\d+\.png),\s+name\s+(?P<name>[^:]+):"
)


def parse_records(run_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    prompt_dir = run_dir / "prompts"
    for prompt_path in sorted(prompt_dir.glob("spritesheet_*.md")):
        sheet_match = re.search(r"spritesheet_(\d+)\.md$", prompt_path.name)
        if sheet_match is None:
            continue
        sheet_index = int(sheet_match.group(1))
        text = prompt_path.read_text(encoding="utf-8")
        for match in CELL_RE.finditer(text):
            file_name = match.group("file")
            index = int(file_name.removeprefix("quality_").removesuffix(".png"))
            records.append(
                {
                    "index": index,
                    "name": match.group("name").strip(),
                    "file": file_name,
                    "sheet_index": sheet_index,
                    "cell": int(match.group("cell")),
                    "row": int(match.group("row")),
                    "col": int(match.group("col")),
                }
            )
    records.sort(key=lambda record: int(record["index"]))
    seen_files = {record["file"] for record in records}
    if len(records) != 102 or len(seen_files) != len(records):
        raise RuntimeError(f"Expected 102 unique records, found {len(records)} records and {len(seen_files)} files")
    return records


def is_background_like(r: int, g: int, b: int, a: int) -> bool:
    if a < 12:
        return True
    return r >= 150 and b >= 150 and g <= 100 and abs(r - b) <= 100


def is_strict_chroma_key(r: int, g: int, b: int, a: int) -> bool:
    if a < 12:
        return True
    return r >= 190 and b >= 190 and g <= 90 and abs(r - b) <= 85


def remove_edge_connected_background(image: Image.Image) -> tuple[Image.Image, int]:
    result = image.convert("RGBA")
    pixels = result.load()
    width, height = result.size
    seen: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    def try_add(x: int, y: int) -> None:
        if (x, y) in seen:
            return
        if is_background_like(*pixels[x, y]):
            seen.add((x, y))
            queue.append((x, y))

    for x in range(width):
        try_add(x, 0)
        try_add(x, height - 1)
    for y in range(height):
        try_add(0, y)
        try_add(width - 1, y)

    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height:
                try_add(nx, ny)

    removed = 0
    for x, y in seen:
        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
        removed += 1
    return result, removed


def remove_strict_chroma_key(image: Image.Image) -> tuple[Image.Image, int]:
    result = image.convert("RGBA")
    pixels = result.load()
    removed = 0
    for y in range(result.height):
        for x in range(result.width):
            r, g, b, a = pixels[x, y]
            if a > 0 and is_strict_chroma_key(r, g, b, a):
                pixels[x, y] = (r, g, b, 0)
                removed += 1
    return result, removed


def crop_cell(sheet: Image.Image, row: int, col: int, cell_size: int) -> Image.Image:
    left = (col - 1) * cell_size
    top = (row - 1) * cell_size
    return sheet.crop((left, top, left + cell_size, top + cell_size)).convert("RGBA")


def opaque_pixels(image: Image.Image) -> int:
    alpha = image.getchannel("A")
    pixels = alpha.load()
    return sum(1 for y in range(alpha.height) for x in range(alpha.width) if pixels[x, y] > 0)


def residual_chroma_pixels(image: Image.Image) -> int:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    count = 0
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if a > 0 and is_strict_chroma_key(r, g, b, a):
                count += 1
    return count


def edge_opaque_pixels(image: Image.Image) -> int:
    alpha = image.getchannel("A")
    pixels = alpha.load()
    width, height = image.size
    total = 0
    for x in range(width):
        total += 1 if pixels[x, 0] > 0 else 0
        total += 1 if pixels[x, height - 1] > 0 else 0
    for y in range(1, height - 1):
        total += 1 if pixels[0, y] > 0 else 0
        total += 1 if pixels[width - 1, y] > 0 else 0
    return total


def load_font(size: int) -> ImageFont.ImageFont:
    font_path = ROOT / "assets" / "fonts" / "HarmonyOS_Sans_SC.ttf"
    if font_path.exists():
        try:
            return ImageFont.truetype(str(font_path), size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def checkerboard(size: tuple[int, int], block: int = 8) -> Image.Image:
    image = Image.new("RGBA", size, (236, 232, 220, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], block):
        for x in range(0, size[0], block):
            if (x // block + y // block) % 2 == 0:
                draw.rectangle((x, y, x + block - 1, y + block - 1), fill=(218, 214, 204, 255))
    return image


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    result = image.convert("RGBA")
    pixels = result.load()
    for y in range(result.height):
        for x in range(result.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                pixels[x, y] = (r, g, b, a)
    return result


def normalize_icon(image: Image.Image, size: int, padding: int) -> Image.Image:
    image = clear_transparent_rgb(image)
    bbox = image.getchannel("A").getbbox()
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if bbox is None:
        return canvas
    content = image.crop(bbox)
    max_side = max(1, size - padding * 2)
    content.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    content = clear_transparent_rgb(content)
    x = (size - content.width) // 2
    y = (size - content.height) // 2
    canvas.alpha_composite(content, (x, y))
    return canvas


def is_component_background_like(r: int, g: int, b: int, a: int) -> bool:
    if a < 12:
        return True
    return r >= 150 and b >= 150 and g <= 110 and abs(r - b) <= 120


def foreground_components(image: Image.Image, min_area: int = 500) -> list[dict[str, Any]]:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    seen: set[tuple[int, int]] = set()
    components: list[dict[str, Any]] = []

    def is_foreground(x: int, y: int) -> bool:
        return not is_component_background_like(*pixels[x, y])

    for y in range(height):
        for x in range(width):
            if not is_foreground(x, y) or (x, y) in seen:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                cx, cy = queue.popleft()
                points.append((cx, cy))
                for nx in (cx - 1, cx, cx + 1):
                    for ny in (cy - 1, cy, cy + 1):
                        if nx == cx and ny == cy:
                            continue
                        if 0 <= nx < width and 0 <= ny < height and is_foreground(nx, ny) and (nx, ny) not in seen:
                            seen.add((nx, ny))
                            queue.append((nx, ny))
            if len(points) < min_area:
                continue
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            components.append(
                {
                    "area": len(points),
                    "bbox": (min(xs), min(ys), max(xs) + 1, max(ys) + 1),
                    "cx": sum(xs) / len(points),
                    "cy": sum(ys) / len(points),
                }
            )
    return components


def remove_component_background(image: Image.Image) -> tuple[Image.Image, int]:
    result = image.convert("RGBA")
    pixels = result.load()
    removed = 0
    for y in range(result.height):
        for x in range(result.width):
            r, g, b, a = pixels[x, y]
            if is_component_background_like(r, g, b, a):
                pixels[x, y] = (0, 0, 0, 0)
                removed += 1
    return clear_transparent_rgb(result), removed


def normalize_component_crop(sheet: Image.Image, bbox: tuple[int, int, int, int], size: int, padding: int) -> Image.Image:
    left, top, right, bottom = bbox
    margin = 12
    left = max(0, left - margin)
    top = max(0, top - margin)
    right = min(sheet.width, right + margin)
    bottom = min(sheet.height, bottom + margin)
    crop = sheet.crop((left, top, right, bottom)).convert("RGBA")
    crop, _ = remove_component_background(crop)
    normalized = normalize_icon(crop, size, padding)
    normalized, _ = remove_strict_chroma_key(normalized)
    return clear_transparent_rgb(normalized)


def hue_shift_icon(image: Image.Image, shift: float) -> Image.Image:
    result = image.convert("RGBA")
    pixels = result.load()
    green_lift = 10 + int(shift * 100)
    for y in range(result.height):
        for x in range(result.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                pixels[x, y] = (0, 0, 0, 0)
                continue
            nr = min(255, int(r * 0.97 + 4))
            ng = min(255, int(g * 1.12 + green_lift))
            nb = min(255, int(b * 0.98 + 3))
            pixels[x, y] = (nr, ng, nb, a)
    return result

def load_backup_icon(run_dir: Path, file_name: str, size: int, padding: int) -> Image.Image | None:
    backup_path = run_dir / "backup_original" / file_name
    if not backup_path.exists():
        return None
    backup = clear_transparent_rgb(Image.open(backup_path).convert("RGBA"))
    backup, _ = remove_strict_chroma_key(backup)
    backup = clear_transparent_rgb(backup)
    if backup.size != (size, size):
        backup = normalize_icon(backup, size, padding)
    return backup


def build_special_recut_icons(run_dir: Path, size: int, padding: int) -> dict[str, dict[str, Any]]:
    special: dict[str, dict[str, Any]] = {}

    sheet3_path = run_dir / "spritesheet" / "spritesheet_03.png"
    if sheet3_path.exists():
        sheet3 = Image.open(sheet3_path).convert("RGBA")
        components_by_row: dict[int, list[dict[str, Any]]] = {row: [] for row in range(1, 5)}
        for component in foreground_components(sheet3):
            row = int(component["cy"] // size) + 1
            if 1 <= row <= 4:
                components_by_row[row].append(component)
        for row, row_components in components_by_row.items():
            row_components.sort(key=lambda component: component["cx"])
            base_index = 48 + (row - 1) * 6
            row_images: list[tuple[Image.Image, dict[str, Any]]] = []
            for component in row_components[:6]:
                row_images.append((normalize_component_crop(sheet3, component["bbox"], size, padding), component))
            if row_images and len(row_images) < 6:
                variant = hue_shift_icon(row_images[-1][0], 0.035 + row * 0.015)
                row_images.append((variant, row_images[-1][1]))
            for offset in range(1, 7):
                index = base_index + offset
                file_name = f"quality_{index:03d}.png"
                if offset <= len(row_images):
                    image, component = row_images[offset - 1]
                    special[file_name] = {
                        "image": image,
                        "source": "sheet_03_component" if offset <= len(row_components[:6]) else "sheet_03_component_variant",
                        "component_bbox": list(component["bbox"]),
                        "component_area": component["area"],
                    }
                else:
                    backup = load_backup_icon(run_dir, file_name, size, padding)
                    if backup is not None:
                        special[file_name] = {
                            "image": backup,
                            "source": "backup_original_missing_component",
                            "component_bbox": None,
                            "component_area": 0,
                        }

    sheet5_path = run_dir / "spritesheet" / "spritesheet_05.png"
    if sheet5_path.exists():
        sheet5 = Image.open(sheet5_path).convert("RGBA")
        components = sorted(foreground_components(sheet5), key=lambda component: component["cx"])
        for offset, component in enumerate(components[:6]):
            index = 97 + offset
            file_name = f"quality_{index:03d}.png"
            special[file_name] = {
                "image": normalize_component_crop(sheet5, component["bbox"], size, padding),
                "source": "sheet_05_component",
                "component_bbox": list(component["bbox"]),
                "component_area": component["area"],
            }
    return special

def build_preview(records: list[dict[str, Any]], icon_root: Path, path: Path) -> None:
    cell = 92
    label_h = 18
    cols = 12
    rows = (len(records) + cols - 1) // cols
    preview = Image.new("RGBA", (cols * cell, rows * (cell + label_h)), (245, 241, 230, 255))
    draw = ImageDraw.Draw(preview)
    font = load_font(12)
    for i, record in enumerate(records):
        icon_path = icon_root / str(record["file"])
        icon = Image.open(icon_path).convert("RGBA")
        icon.thumbnail((78, 78), Image.Resampling.LANCZOS)
        tile_x = (i % cols) * cell
        tile_y = (i // cols) * (cell + label_h)
        bg = checkerboard((cell, cell), 8)
        preview.alpha_composite(bg, (tile_x, tile_y))
        preview.alpha_composite(icon, (tile_x + (cell - icon.width) // 2, tile_y + (cell - icon.height) // 2))
        draw.text((tile_x + 4, tile_y + cell), f"{int(record['index']):03d}", font=font, fill=(38, 38, 38, 255))
    preview.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--icon-root", type=Path, default=ICON_ROOT)
    parser.add_argument("--cell-size", type=int, default=256)
    parser.add_argument("--padding", type=int, default=20)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    icon_root = args.icon_root.resolve()
    records = parse_records(run_dir)
    icon_root.mkdir(parents=True, exist_ok=True)

    sheet_cache: dict[int, Image.Image] = {}
    special_icons = build_special_recut_icons(run_dir, args.cell_size, args.padding)
    report: list[dict[str, Any]] = []

    for record in records:
        sheet_index = int(record["sheet_index"])
        special_icon = special_icons.get(str(record["file"]))
        edge_removed = 0
        strict_removed = 0
        post_resize_strict_removed = 0
        component_bbox = None
        component_area = 0
        if special_icon is not None:
            normalized = special_icon["image"].copy()
            source_alpha_bbox = normalized.getchannel("A").getbbox()
            crop_source = str(special_icon["source"])
            component_bbox = special_icon.get("component_bbox")
            component_area = int(special_icon.get("component_area", 0))
        else:
            if sheet_index not in sheet_cache:
                sheet_path = run_dir / "spritesheet" / f"spritesheet_{sheet_index:02d}.png"
                if not sheet_path.exists():
                    raise FileNotFoundError(sheet_path)
                sheet = Image.open(sheet_path).convert("RGBA")
                expected_size = (args.cell_size * 6, args.cell_size * 4)
                if sheet.size != expected_size:
                    raise RuntimeError(f"{sheet_path} has size {sheet.size}, expected {expected_size}")
                sheet_cache[sheet_index] = sheet
            cell = crop_cell(sheet_cache[sheet_index], int(record["row"]), int(record["col"]), args.cell_size)
            cleaned, edge_removed = remove_edge_connected_background(cell)
            cleaned, strict_removed = remove_strict_chroma_key(cleaned)
            source_alpha_bbox = cleaned.getchannel("A").getbbox()
            normalized = normalize_icon(cleaned, args.cell_size, args.padding)
            normalized, post_resize_strict_removed = remove_strict_chroma_key(normalized)
            normalized = clear_transparent_rgb(normalized)
            crop_source = "grid_cell"

        output_path = icon_root / str(record["file"])
        old_opaque = 0
        if output_path.exists():
            old_opaque = opaque_pixels(Image.open(output_path).convert("RGBA"))
        normalized.save(output_path)

        alpha_bbox = normalized.getchannel("A").getbbox()
        report.append(
            {
                "index": record["index"],
                "name": record["name"],
                "file": record["file"],
                "sheet_index": sheet_index,
                "row": record["row"],
                "col": record["col"],
                "old_opaque_pixels": old_opaque,
                "new_opaque_pixels": opaque_pixels(normalized),
                "crop_source": crop_source,
                "component_bbox": component_bbox,
                "component_area": component_area,
                "source_alpha_bbox": list(source_alpha_bbox) if source_alpha_bbox else None,
                "alpha_bbox": list(alpha_bbox) if alpha_bbox else None,
                "edge_connected_background_pixels": edge_removed,
                "strict_chroma_pixels": strict_removed,
                "post_resize_chroma_pixels": post_resize_strict_removed,
                "residual_chroma_pixels": residual_chroma_pixels(normalized),
                "edge_opaque_pixels": edge_opaque_pixels(normalized),
            }
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    build_preview(records, icon_root, PREVIEW_PATH)
    empty = [row["file"] for row in report if row["alpha_bbox"] is None or int(row["new_opaque_pixels"]) == 0]
    residual = [row["file"] for row in report if int(row["residual_chroma_pixels"]) > 0]
    edge_touching = [row["file"] for row in report if int(row["edge_opaque_pixels"]) > 0]
    print(f"recut {len(records)} realm quality icons")
    print(f"report: {REPORT_PATH}")
    print(f"preview: {PREVIEW_PATH}")
    print(f"empty icons: {len(empty)}")
    print(f"residual chroma icons: {len(residual)}")
    print(f"edge-touching icons: {len(edge_touching)}")
    if empty:
        print("empty:", ", ".join(empty))
    if residual:
        print("residual:", ", ".join(residual[:20]))
    if edge_touching:
        print("edge_touching:", ", ".join(edge_touching[:20]))


if __name__ == "__main__":
    main()
