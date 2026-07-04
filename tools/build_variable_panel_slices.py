from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BACKGROUND_DIR = ROOT / "assets" / "panel_backgrounds"
UI_SPRITE_DIR = ROOT / "build" / "ui_sprite"


@dataclass(frozen=True)
class Crop:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)

    def as_manifest(self) -> dict[str, int]:
        return {
            "x": self.x1,
            "y": self.y1,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class VariablePanelConfig:
    id: str
    source_file: str
    content_id: str
    content_role: str
    content_crop: Crop
    content_top_height: int
    content_body_crop: Crop
    content_bottom_height: int
    header_bottom_y: int
    footer_top_y: int
    demo_content_height: int
    notes: str

    @property
    def content_top_crop(self) -> Crop:
        return Crop(
            self.content_crop.x1,
            self.content_crop.y1,
            self.content_crop.x2,
            self.content_crop.y1 + self.content_top_height,
        )

    @property
    def content_bottom_crop(self) -> Crop:
        return Crop(
            self.content_crop.x1,
            self.content_crop.y2 - self.content_bottom_height,
            self.content_crop.x2,
            self.content_crop.y2,
        )


CONFIGS = [
    VariablePanelConfig(
        id="fishing",
        source_file="fishing_background.png",
        content_id="result_panel",
        content_role="reward_list_panel",
        content_crop=Crop(126, 884, 1130, 1077),
        content_top_height=56,
        content_body_crop=Crop(126, 940, 1130, 1014),
        content_bottom_height=63,
        header_bottom_y=884,
        footer_top_y=1077,
        demo_content_height=520,
        notes=(
            "Use the fixed header for the lake, side panels, and title area. "
            "Place the variable result panel at x=126,y=884, then shift the fixed footer below it."
        ),
    ),
    VariablePanelConfig(
        id="battle",
        source_file="battle_background.png",
        content_id="battle_log_panel",
        content_role="battle_record_panel",
        content_crop=Crop(72, 812, 1182, 1172),
        content_top_height=68,
        content_body_crop=Crop(72, 880, 1182, 922),
        content_bottom_height=48,
        header_bottom_y=812,
        footer_top_y=1172,
        demo_content_height=650,
        notes=(
            "Use the fixed header for the duel portraits and VS area. "
            "Repeat the battle log row slice to fit the number of timeline rows, then shift the fixed footer below it."
        ),
    ),
]


def ensure_dirs(root: Path) -> tuple[Path, Path, Path]:
    sprites_dir = root / "sprites"
    spec_dir = root / "spec"
    previews_dir = root / "previews"
    for path in (sprites_dir, spec_dir, previews_dir):
        path.mkdir(parents=True, exist_ok=True)
    return sprites_dir, spec_dir, previews_dir


def crop_save(source: Image.Image, crop: Crop, output: Path) -> None:
    source.crop(crop.as_tuple()).save(output)


def repeat_vertical(tile: Image.Image, width: int, height: int) -> Image.Image:
    result = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    y = 0
    while y < height:
        part_h = min(tile.height, height - y)
        result.alpha_composite(tile.crop((0, 0, tile.width, part_h)), (0, y))
        y += part_h
    return result


def build_content_panel_preview(config: VariablePanelConfig, source: Image.Image) -> Image.Image:
    top = source.crop(config.content_top_crop.as_tuple()).convert("RGBA")
    body = source.crop(config.content_body_crop.as_tuple()).convert("RGBA")
    bottom = source.crop(config.content_bottom_crop.as_tuple()).convert("RGBA")
    body_height = max(0, config.demo_content_height - top.height - bottom.height)

    preview = Image.new("RGBA", (config.content_crop.width, config.demo_content_height), (0, 0, 0, 0))
    preview.alpha_composite(top, (0, 0))
    preview.alpha_composite(repeat_vertical(body, config.content_crop.width, body_height), (0, top.height))
    preview.alpha_composite(bottom, (0, top.height + body_height))
    return preview


def build_full_preview(config: VariablePanelConfig, source: Image.Image) -> Image.Image:
    header = source.crop((0, 0, source.width, config.header_bottom_y)).convert("RGBA")
    footer = source.crop((0, config.footer_top_y, source.width, source.height)).convert("RGBA")
    panel = build_content_panel_preview(config, source)

    total_height = header.height + panel.height + footer.height
    preview = Image.new("RGBA", (source.width, total_height), (17, 23, 30, 255))
    preview.alpha_composite(header, (0, 0))
    preview.alpha_composite(panel, (config.content_crop.x1, config.header_bottom_y))
    preview.alpha_composite(footer, (0, config.header_bottom_y + panel.height))
    return preview


def draw_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=font)
    draw.rectangle((bbox[0] - 4, bbox[1] - 3, bbox[2] + 4, bbox[3] + 3), fill=(12, 18, 26, 210))
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)


def build_debug_overlay(config: VariablePanelConfig, source: Image.Image) -> Image.Image:
    debug = source.convert("RGBA").copy()
    overlay = Image.new("RGBA", debug.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    boxes = [
        ("fixed_header", Crop(0, 0, source.width, config.header_bottom_y), (72, 149, 239, 180)),
        ("content_top", config.content_top_crop, (34, 197, 94, 210)),
        ("repeat_body", config.content_body_crop, (250, 204, 21, 230)),
        ("content_bottom", config.content_bottom_crop, (236, 72, 153, 210)),
        ("fixed_footer", Crop(0, config.footer_top_y, source.width, source.height), (14, 165, 233, 180)),
    ]
    for label, crop, color in boxes:
        draw.rectangle(crop.as_tuple(), outline=color, width=4)
        draw.rectangle(crop.as_tuple(), fill=(color[0], color[1], color[2], 30))
        draw_label(draw, (crop.x1 + 10, crop.y1 + 10), label)

    return Image.alpha_composite(debug, overlay)


def write_manifest(config: VariablePanelConfig, source: Image.Image, sprites_dir: Path, spec_dir: Path) -> None:
    stem = config.id
    top_file = f"{stem}_{config.content_id}_top.png"
    body_file = f"{stem}_{config.content_id}_body_repeat.png"
    bottom_file = f"{stem}_{config.content_id}_bottom.png"
    header_file = f"{stem}_fixed_header.png"
    footer_file = f"{stem}_fixed_footer.png"
    base_file = f"{stem}_background_base.png"

    sprites = [
        ("background_base", "panel_frame", Crop(0, 0, source.width, source.height), base_file, "fixed"),
        ("fixed_header", "fixed_canvas_section", Crop(0, 0, source.width, config.header_bottom_y), header_file, "fixed"),
        (
            "fixed_footer",
            "fixed_canvas_section",
            Crop(0, config.footer_top_y, source.width, source.height),
            footer_file,
            "fixed",
        ),
        (f"{config.content_id}_top", config.content_role, config.content_top_crop, top_file, "fixed"),
        (f"{config.content_id}_body_repeat", config.content_role, config.content_body_crop, body_file, "repeat_y"),
        (f"{config.content_id}_bottom", config.content_role, config.content_bottom_crop, bottom_file, "fixed"),
    ]

    layout = {
        "image_size": {"width": source.width, "height": source.height},
        "sprites": [
            {
                "id": sprite_id,
                "filename": filename,
                "x": crop.x1,
                "y": crop.y1,
                "width": crop.width,
                "height": crop.height,
                "display_width": crop.width,
                "display_height": crop.height,
                "role": role,
                "repeat": repeat,
            }
            for sprite_id, role, crop, filename, repeat in sprites
        ],
    }

    manifest = {
        "id": config.id,
        "source": str((BACKGROUND_DIR / config.source_file).relative_to(ROOT)).replace("\\", "/"),
        "source_size": {"width": source.width, "height": source.height},
        "notes": config.notes,
        "fixed_canvas": {
            "header": {
                "file": f"../sprites/{header_file}",
                "source_crop": Crop(0, 0, source.width, config.header_bottom_y).as_manifest(),
            },
            "footer": {
                "file": f"../sprites/{footer_file}",
                "source_crop": Crop(0, config.footer_top_y, source.width, source.height).as_manifest(),
            },
            "footer_source_y": config.footer_top_y,
        },
        "variable_content_panel": {
            "id": config.content_id,
            "role": config.content_role,
            "origin": {"x": config.content_crop.x1, "y": config.content_crop.y1},
            "source_crop": config.content_crop.as_manifest(),
            "min_height": config.content_top_crop.height + config.content_body_crop.height + config.content_bottom_crop.height,
            "source_height": config.content_crop.height,
            "assembly_order": [
                {
                    "id": f"{config.content_id}_top",
                    "file": f"../sprites/{top_file}",
                    "height": config.content_top_crop.height,
                    "repeat": "none",
                },
                {
                    "id": f"{config.content_id}_body_repeat",
                    "file": f"../sprites/{body_file}",
                    "height": config.content_body_crop.height,
                    "repeat": "vertical",
                },
                {
                    "id": f"{config.content_id}_bottom",
                    "file": f"../sprites/{bottom_file}",
                    "height": config.content_bottom_crop.height,
                    "repeat": "none",
                },
            ],
            "footer_shift_formula": "new_footer_y = origin.y + requested_content_height",
        },
    }
    (spec_dir / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
    (spec_dir / "variable_panel_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build(config: VariablePanelConfig) -> None:
    source_path = BACKGROUND_DIR / config.source_file
    out_root = UI_SPRITE_DIR / config.id / "output"
    sprites_dir, spec_dir, previews_dir = ensure_dirs(out_root)
    source = Image.open(source_path).convert("RGBA")

    crop_save(source, Crop(0, 0, source.width, source.height), sprites_dir / f"{config.id}_background_base.png")
    crop_save(source, Crop(0, 0, source.width, config.header_bottom_y), sprites_dir / f"{config.id}_fixed_header.png")
    crop_save(source, Crop(0, config.footer_top_y, source.width, source.height), sprites_dir / f"{config.id}_fixed_footer.png")
    crop_save(source, config.content_top_crop, sprites_dir / f"{config.id}_{config.content_id}_top.png")
    crop_save(source, config.content_body_crop, sprites_dir / f"{config.id}_{config.content_id}_body_repeat.png")
    crop_save(source, config.content_bottom_crop, sprites_dir / f"{config.id}_{config.content_id}_bottom.png")

    write_manifest(config, source, sprites_dir, spec_dir)
    build_content_panel_preview(config, source).save(previews_dir / f"{config.id}_{config.content_id}_variable_preview.png")
    build_full_preview(config, source).save(previews_dir / f"{config.id}_full_variable_demo.png")
    build_debug_overlay(config, source).save(sprites_dir / "debug_variable_slices.png")


def main() -> None:
    for config in CONFIGS:
        build(config)
        print(UI_SPRITE_DIR / config.id / "output")


if __name__ == "__main__":
    main()
