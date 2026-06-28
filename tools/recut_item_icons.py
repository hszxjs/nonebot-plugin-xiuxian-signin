from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ICON_ROOT = ROOT / "assets" / "item_icons"
ITEM_DIR = ICON_ROOT / "items"
GRID_PATH = ICON_ROOT / "sheet_grid_detection.json"
RECORD_PATH = ICON_ROOT / "item_icon_records.json"
REPORT_PATH = ICON_ROOT / "edge_connected_recut_report.json"
PREVIEW_PATH = ICON_ROOT / "edge_connected_recut_preview.png"
KNOWN_ICON_SWAP_PAIRS = [(index, index + 10) for index in range(456, 466)]


def is_connected_background(r: int, g: int, b: int, a: int) -> bool:
    if a < 12:
        return True
    bright = (r + g + b) / 3
    saturation = max(r, g, b) - min(r, g, b)
    # Remove only pale/low-saturation pixels when they are connected to the
    # cell border. Closed white regions inside bottles, pills, pearls, etc.
    # are not reached by the flood fill and remain opaque.
    return (r >= 230 and g >= 230 and b >= 230) or (bright >= 202 and saturation <= 42)


def edge_connected_background_mask(image: Image.Image) -> set[tuple[int, int]]:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    seen: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    def try_add(x: int, y: int) -> None:
        if (x, y) in seen:
            return
        r, g, b, a = pixels[x, y]
        if is_connected_background(r, g, b, a):
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
    return seen


def crop_cell(sheet: Image.Image, xlines: list[float], ylines: list[float], col: int, row: int) -> Image.Image:
    # Keep away from the generated sheet grid. The grid lines sit on cell
    # borders and do not pass through icons, so a small inset is safer than
    # deleting thin lines from icon interiors.
    inset = 7
    left = max(0, int(round(xlines[col - 1])) + inset)
    top = max(0, int(round(ylines[row - 1])) + inset)
    right = min(sheet.width, int(round(xlines[col])) - inset)
    bottom = min(sheet.height, int(round(ylines[row])) - inset)
    if right <= left or bottom <= top:
        left = max(0, int(round(xlines[col - 1])) + 1)
        top = max(0, int(round(ylines[row - 1])) + 1)
        right = min(sheet.width, int(round(xlines[col])) - 1)
        bottom = min(sheet.height, int(round(ylines[row])) - 1)
    return sheet.crop((left, top, right, bottom)).convert("RGBA")


def transparent_background(cell: Image.Image) -> Image.Image:
    result = cell.convert("RGBA")
    pixels = result.load()
    for x, y in edge_connected_background_mask(result):
        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
    return result


def alpha_components(image: Image.Image) -> list[tuple[int, int, int, int, int, list[tuple[int, int]]]]:
    alpha = image.getchannel("A")
    width, height = image.size
    pixels = alpha.load()
    seen: set[tuple[int, int]] = set()
    components: list[tuple[int, int, int, int, int, list[tuple[int, int]]]] = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0 or (x, y) in seen:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                cx, cy = queue.popleft()
                points.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and pixels[nx, ny] > 0 and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            components.append((min(xs), min(ys), max(xs) + 1, max(ys) + 1, len(points), points))
    return components


def remove_thin_line_artifacts(image: Image.Image) -> tuple[Image.Image, int]:
    result = image.convert("RGBA")
    pixels = result.load()
    width, height = result.size
    removed: set[tuple[int, int]] = set()

    # Remove standalone strip-like components, regardless of their color.
    for x1, y1, x2, y2, area, points in alpha_components(result):
        component_w = x2 - x1
        component_h = y2 - y1
        vertical_strip = component_w <= 3 and component_h >= max(24, int(height * 0.42))
        horizontal_strip = component_h <= 3 and component_w >= max(24, int(width * 0.42))
        if vertical_strip or horizontal_strip:
            removed.update(points)

    for x, y in removed:
        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)

    # Remove long rows/columns only when they hug the content edge. This catches
    # grid lines connected to tiny antialias fragments while leaving central
    # swords, spears, brush strokes, and scroll ties intact.
    alpha = result.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is not None:
        left, top, right, bottom = bbox
        bbox_w = right - left
        bbox_h = bottom - top
        edge_span = 10
        row_threshold = max(16, int(bbox_w * 0.55))
        col_threshold = max(16, int(bbox_h * 0.55))
        alpha_pixels = alpha.load()
        edge_rows = list(range(top, min(bottom, top + edge_span))) + list(range(max(top, bottom - edge_span), bottom))
        edge_cols = list(range(left, min(right, left + edge_span))) + list(range(max(left, right - edge_span), right))
        for y in edge_rows:
            row_count = sum(1 for x in range(left, right) if alpha_pixels[x, y] > 0)
            if row_count >= row_threshold:
                for x in range(left, right):
                    if alpha_pixels[x, y] > 0:
                        removed.add((x, y))
        for x in edge_cols:
            col_count = sum(1 for y in range(top, bottom) if alpha_pixels[x, y] > 0)
            if col_count >= col_threshold:
                for y in range(top, bottom):
                    if alpha_pixels[x, y] > 0:
                        removed.add((x, y))

    for x, y in removed:
        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
    return result, len(removed)


def content_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    alpha = image.getchannel("A")
    return alpha.getbbox()


def normalize_icon(image: Image.Image, size: int = 128, padding: int = 10) -> Image.Image:
    bbox = content_bbox(image)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if bbox is None:
        return canvas
    content = image.crop(bbox)
    max_side = max(1, size - padding * 2)
    content.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    x = (size - content.width) // 2
    y = (size - content.height) // 2
    canvas.alpha_composite(content, (x, y))
    return canvas


def opaque_pixels(image: Image.Image) -> int:
    return sum(1 for value in image.getchannel("A").getdata() if value > 0)


def build_preview(records: list[dict[str, Any]], limit: int = 48) -> None:
    cell = 96
    cols = 8
    rows = (min(limit, len(records)) + cols - 1) // cols
    preview = Image.new("RGBA", (cols * cell, rows * (cell + 18)), (245, 241, 230, 255))
    draw = ImageDraw.Draw(preview)
    for index, record in enumerate(records[:limit]):
        icon_path = ICON_ROOT / str(record.get("icon") or "")
        if not icon_path.exists():
            continue
        icon = Image.open(icon_path).convert("RGBA")
        icon.thumbnail((82, 82), Image.Resampling.LANCZOS)
        x = (index % cols) * cell + (cell - icon.width) // 2
        y = (index // cols) * (cell + 18) + 4
        preview.alpha_composite(icon, (x, y))
        draw.text(((index % cols) * cell + 4, y + 84), str(record.get("index")), fill=(40, 40, 40, 255))
    preview.save(PREVIEW_PATH)


def apply_known_icon_corrections(records: list[dict[str, Any]]) -> None:
    record_by_index = {int(record.get("index", 0)): record for record in records}
    for left, right in KNOWN_ICON_SWAP_PAIRS:
        left_record = record_by_index.get(left)
        right_record = record_by_index.get(right)
        if not left_record or not right_record:
            continue
        left_path = ICON_ROOT / str(left_record.get("icon") or "")
        right_path = ICON_ROOT / str(right_record.get("icon") or "")
        if not left_path.exists() or not right_path.exists():
            continue
        left_img = Image.open(left_path).convert("RGBA")
        right_img = Image.open(right_path).convert("RGBA")
        right_img.save(left_path)
        left_img.save(right_path)
        left_record["opaque_pixels"] = opaque_pixels(right_img)
        right_record["opaque_pixels"] = opaque_pixels(left_img)


def main() -> None:
    grid = json.loads(GRID_PATH.read_text(encoding="utf-8"))
    records = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    ITEM_DIR.mkdir(parents=True, exist_ok=True)

    sheet_cache: dict[int, Image.Image] = {}
    report: list[dict[str, Any]] = []
    updated_records: list[dict[str, Any]] = []

    for record in records:
        sheet_index = int(record["sheet_index"])
        info = grid[str(sheet_index)]
        if sheet_index not in sheet_cache:
            sheet_path = ROOT / str(info["file"])
            sheet_cache[sheet_index] = Image.open(sheet_path).convert("RGBA")
        sheet = sheet_cache[sheet_index]
        cell = crop_cell(sheet, info["xlines"], info["ylines"], int(record["col"]), int(record["row"]))
        old_path = ICON_ROOT / str(record["icon"])
        old_opaque = 0
        if old_path.exists():
            try:
                old_opaque = opaque_pixels(Image.open(old_path).convert("RGBA"))
            except OSError:
                old_opaque = 0
        cleaned = transparent_background(cell)
        removed_before_normalize = 0
        removed_after_normalize = 0
        icon = normalize_icon(cleaned)
        new_opaque = opaque_pixels(icon)
        icon.save(old_path)
        updated = dict(record)
        updated["opaque_pixels"] = new_opaque
        updated_records.append(updated)
        report.append(
            {
                "index": record.get("index"),
                "item_name": record.get("item_name"),
                "icon": record.get("icon"),
                "old_opaque_pixels": old_opaque,
                "new_opaque_pixels": new_opaque,
                "delta_opaque_pixels": new_opaque - old_opaque,
                "removed_line_pixels": removed_before_normalize + removed_after_normalize,
            }
        )

    apply_known_icon_corrections(updated_records)
    RECORD_PATH.write_text(json.dumps(updated_records, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    build_preview(updated_records)
    print(f"recut {len(updated_records)} icons")
    print(REPORT_PATH)
    print(PREVIEW_PATH)


if __name__ == "__main__":
    main()
