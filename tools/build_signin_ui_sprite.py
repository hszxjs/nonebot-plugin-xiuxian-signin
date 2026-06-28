from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BG_PATH = ROOT / "assets" / "panel_backgrounds" / "signin_background.png"
FONT_PATH = ROOT / "assets" / "fonts" / "NotoSansSC-VF.ttf"
OUT_ROOT = ROOT / "assets" / "ui_sprite" / "signin" / "output"
SPEC_DIR = OUT_ROOT / "spec"
SHEET_DIR = OUT_ROOT / "spritesheet"
SPRITES_DIR = OUT_ROOT / "sprites"
HTML_DIR = OUT_ROOT / "html"

OLD_AVATAR_PATH = Path(
    r"C:\Users\hszxjs\Desktop\b_6fd0a2b19991d594c05b91942159b137.jpg"
)

CANVAS_W = 1536
MARGIN = 24

TEXT = {
    "title": "\u4eca\u65e5\u5df2\u5b8c\u6210\u7b7e\u5230",
    "name": "\u843d\u96e8\u30fb\u4e71\u5fc3\u601d",
    "hint": "\u5bbf\u4e3b\u4eca\u65e5\u6c14\u606f\u7a33\u5b9a\uff0c\u65e0\u9700\u91cd\u590d\u95ed\u5173",
    "root_label": "\u7075\u6839",
    "root_value": "\u53d8\u5f02\u7075\u6839\n\u6781\u54c1\u96f7\u7075\u6839\n\u7531\u706b+\u6c34\u5148\u5929\u5f02\u53d8",
    "purity_label": "\u7075\u6839\u7cbe\u7eaf\u5ea6",
    "purity_value": "\u96f796% / \u706b96% / \u6c3496%\n\u540e\u5929\uff1a\u91d188% / \u672891% / \u571f91%",
    "realm_label": "\u5f53\u524d\u5883\u754c",
    "realm_value": "\u70bc\u865a\u671f\u5dc5\u5cf0",
    "sign_label": "\u7b7e\u5230\u6b21\u6570",
    "sign_value": "6 \u6b21",
    "total_label": "\u7d2f\u8ba1\u4fee\u4e3a",
    "total_value": "9068 \u70b9",
    "progress_label": "\u7ecf\u9a8c\u8fdb\u5ea6",
    "progress_value": "4406/4736",
    "footer": "\u660e\u65e5\u518d\u6765\uff0c\u7075\u6c14\u81ea\u4f1a\u79ef\u84c4",
}

GRID_ITEMS = [
    ("\u7075\u5668", "[\u5929\u9636\u6781\u54c1\u7075\u5668 \u592a\u865a\u65a9\u661f\u5251]"),
    ("\u529f\u6cd5", "[\u5929\u9636\u4e0a\u54c1\u529f\u6cd5 \u79bb\u706b\u70bc\u754c\u7bc7]"),
    ("\u9635\u76d8", "[\u7384\u9636\u6781\u54c1\u9635\u76d8 \u5c0f\u4e94\u884c\u805a\u7075\u76d8]"),
    ("\u9635\u6cd5\u719f\u7ec3", "\u719f\u7ec3\u5ea6 640/900 \u30fb 7.4x"),
    ("\u5883\u754c\u54c1\u76f8", "\u6d1e\u865a\u9053\u4f53"),
    ("\u6218\u6597\u5c5e\u6027", "\u6218\u529b93438 / \u7075\u529b10230"),
    ("\u8def\u7ebf", "\u70bc\u4e39\u5e08"),
    ("\u8eab\u4efd\u4ee4\u724c", "\u5929\u673a\u9601\u5f1f\u5b50"),
    ("\u540e\u5929\u7075\u6839", "\u91d1\u7075\u6839 / +2\u6761"),
]


MaskKind = Literal["none", "rounded", "portrait_overlay", "pill", "ornament"]


@dataclass(frozen=True)
class Component:
    id: str
    role: str
    description: str
    crop: tuple[int, int, int, int]
    center: str
    mask: MaskKind = "none"
    radius: int = 0
    decorations: tuple[str, ...] = ()

    @property
    def width(self) -> int:
        return self.crop[2] - self.crop[0]

    @property
    def height(self) -> int:
        return self.crop[3] - self.crop[1]


COMPONENTS = [
    Component(
        "signin_background_base",
        "panel_frame",
        "Full square immortal-cultivation sign-in panel background with landscape, jade-gold frame, built-in rounded sections, and bottom progress trough.",
        (0, 0, 1254, 1254),
        "filled",
    ),
    Component(
        "portrait_frame_overlay",
        "portrait_frame",
        "Circular jade and gold avatar frame with top and bottom turquoise gems, exported as a transparent overlay so the avatar can sit below the ornaments.",
        (145, 55, 515, 430),
        "hollow",
        "portrait_overlay",
        decorations=("top turquoise gem", "bottom turquoise gem", "gold leaf ornaments"),
    ),
    Component(
        "upper_landscape_panel",
        "panel_frame",
        "Top rounded landscape panel with pale parchment fill, gold trim, jade corner ornaments, and central mountain scenery.",
        (95, 42, 1158, 405),
        "filled",
        "rounded",
        48,
        ("top center turquoise gem", "corner jade ornaments"),
    ),
    Component(
        "wide_spirit_panel",
        "panel_frame",
        "Wide rounded jade-tinted information panel with soft green corners and thin gold inner dividers.",
        (154, 421, 1102, 576),
        "filled",
        "rounded",
        28,
    ),
    Component(
        "left_stat_panel",
        "slot_square",
        "Left rounded parchment statistic panel with pale gold border.",
        (154, 591, 625, 709),
        "filled",
        "rounded",
        22,
    ),
    Component(
        "right_stat_panel",
        "slot_square",
        "Right rounded parchment statistic panel with pale gold border.",
        (630, 591, 1104, 709),
        "filled",
        "rounded",
        22,
    ),
    Component(
        "nine_grid_panel",
        "panel_frame",
        "Large rounded nine-cell parchment information grid with delicate jade corner decoration and thin gold dividers.",
        (154, 724, 1104, 1006),
        "filled",
        "rounded",
        25,
    ),
    Component(
        "experience_trough",
        "bar_track",
        "Long turquoise jade progress trough with cloud caps at both ends and glowing water texture in the center.",
        (188, 1018, 1065, 1095),
        "filled",
        "pill",
        38,
        ("left cloud cap", "right cloud cap"),
    ),
    Component(
        "left_hanging_jade",
        "decoration",
        "Left hanging jade pendant with gold chains and green tassel.",
        (41, 154, 134, 418),
        "filled",
        "ornament",
        0,
        ("jade pendant", "green tassel"),
    ),
    Component(
        "right_hanging_jade",
        "decoration",
        "Right hanging jade pendant with gold chains and green tassel.",
        (1121, 154, 1215, 419),
        "filled",
        "ornament",
        0,
        ("jade pendant", "green tassel"),
    ),
]


def ensure_dirs() -> None:
    for path in (SPEC_DIR, SHEET_DIR, SPRITES_DIR, HTML_DIR):
        path.mkdir(parents=True, exist_ok=True)


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(0.3))


def pill_mask(size: tuple[int, int]) -> Image.Image:
    return rounded_mask(size, size[1] // 2)


def portrait_overlay_mask(size: tuple[int, int]) -> Image.Image:
    w, h = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)

    # Keep only the circular frame ring; the avatar must remain unobstructed.
    outer = (12, 14, 357, 370)
    inner = (64, 79, 305, 315)
    draw.ellipse(outer, fill=255)
    draw.ellipse(inner, fill=0)

    return mask.filter(ImageFilter.GaussianBlur(0.6))


def ornament_mask(crop: Image.Image) -> Image.Image:
    rgb = crop.convert("RGB")
    pixels = rgb.load()
    mask = Image.new("L", crop.size, 0)
    out = mask.load()
    w, h = crop.size
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            # Preserve saturated jade/gold ornaments and tassels, drop pale background.
            colorful = max(r, g, b) - min(r, g, b)
            darker = r < 228 or g < 228 or b < 214
            if colorful > 18 and darker:
                out[x, y] = 255
    return mask.filter(ImageFilter.GaussianBlur(0.8))


def apply_component_mask(crop: Image.Image, component: Component) -> Image.Image:
    crop = crop.convert("RGBA")
    if component.mask == "none":
        return crop
    if component.mask == "rounded":
        mask = rounded_mask(crop.size, component.radius)
    elif component.mask == "pill":
        mask = pill_mask(crop.size)
    elif component.mask == "portrait_overlay":
        mask = portrait_overlay_mask(crop.size)
    elif component.mask == "ornament":
        mask = ornament_mask(crop)
    else:
        raise ValueError(f"Unknown mask kind: {component.mask}")
    crop.putalpha(mask)
    return crop


def pack_components(bg: Image.Image) -> tuple[Image.Image, list[dict[str, object]]]:
    x = 0
    y = 0
    row_h = 0
    placements: list[tuple[Component, Image.Image, int, int]] = []

    for component in COMPONENTS:
        crop = bg.crop(component.crop)
        sprite = apply_component_mask(crop, component)
        if x and x + sprite.width > CANVAS_W:
            x = 0
            y += row_h + MARGIN
            row_h = 0
        placements.append((component, sprite, x, y))
        x += sprite.width + MARGIN
        row_h = max(row_h, sprite.height)

    sheet_h = y + row_h
    sheet = Image.new("RGBA", (CANVAS_W, sheet_h), (0, 0, 0, 0))
    sprites: list[dict[str, object]] = []
    for component, sprite, px, py in placements:
        sheet.alpha_composite(sprite, (px, py))
        sprites.append(
            {
                "id": component.id,
                "filename": f"{component.id}.png",
                "x": px,
                "y": py,
                "width": sprite.width,
                "height": sprite.height,
                "display_width": sprite.width,
                "display_height": sprite.height,
                "role": component.role,
                "center": component.center,
            }
        )
    return sheet, sprites


def write_spec() -> None:
    spec = {
        "style": {
            "description": "Eastern immortal-cultivation game UI with pale parchment panels, jade ornaments, thin gold trim, soft ink-wash mountain scenery, and turquoise spiritual light.",
            "primary_material": "pale parchment and polished jade frame with soft watercolor texture",
            "primary_color": "#f2ead3",
            "trim_material": "delicate gold filigree with turquoise gemstone inlays",
            "trim_color": "#c5a35d",
            "fill_material": "translucent parchment wash with faint cloud and mountain texture",
            "fill_color": "#efe7cf",
            "negative_constraints": [
                "no western magic runes",
                "no thick sci-fi metal",
                "no flat plastic buttons",
                "no dark gothic stone",
            ],
        },
        "components": [
            {
                "id": component.id,
                "role": component.role,
                "description": component.description,
                "attached_decorations": list(component.decorations),
                "center": component.center,
                "approximate_aspect_ratio": f"{component.width}:{component.height}",
                "relative_size": "large"
                if component.width * component.height > 250000
                else "medium"
                if component.width * component.height > 45000
                else "small",
                "quantity_on_screen": 1,
            }
            for component in COMPONENTS
        ],
    }
    (SPEC_DIR / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")


def write_layout(sheet: Image.Image, sprites: list[dict[str, object]]) -> None:
    layout = {"image_size": {"width": sheet.width, "height": sheet.height}, "sprites": sprites}
    (SPEC_DIR / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")


def load_sample_avatar(size: int = 512) -> Image.Image:
    if OLD_AVATAR_PATH.exists():
        raw = Image.open(OLD_AVATAR_PATH).convert("RGBA")
        side = min(raw.size)
        left = (raw.width - side) // 2
        top = (raw.height - side) // 2
        cropped = raw.crop((left, top, left + side, top + side))
        return cropped.resize((size, size), Image.Resampling.LANCZOS)

    avatar = Image.new("RGBA", (size, size), (24, 32, 48, 255))
    draw = ImageDraw.Draw(avatar)
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(38 + 58 * t)
        g = int(54 + 24 * t)
        b = int(88 + 96 * t)
        draw.line((0, y, size, y), fill=(r, g, b, 255))
    draw.ellipse((size * 0.22, size * 0.15, size * 0.78, size * 0.78), fill=(116, 86, 180, 255))
    return avatar


def render_avatar_layer(size: tuple[int, int]) -> Image.Image:
    w, h = size
    source = load_sample_avatar(max(w, h) + 80)
    scale = max(w / source.width, h / source.height)
    resized = source.resize((math.ceil(source.width * scale), math.ceil(source.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - w) // 2
    top = (resized.height - h) // 2
    avatar = resized.crop((left, top, left + w, top + h)).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w - 1, h - 1), fill=255)
    avatar.putalpha(mask.filter(ImageFilter.GaussianBlur(0.4)))
    return avatar


def text_size(draw: ImageDraw.ImageDraw, value: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), value, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_weighted(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    fnt: ImageFont.ImageFont,
    fill: str,
    weight: int = 1,
) -> None:
    offsets = [(0, 0)]
    if weight >= 2:
        offsets.extend([(1, 0), (0, 1)])
    if weight >= 3:
        offsets.extend([(-1, 0), (0, -1)])
    x, y = xy
    for ox, oy in offsets:
        draw.text((x + ox, y + oy), value, font=fnt, fill=fill)


def wrap(draw: ImageDraw.ImageDraw, value: str, fnt: ImageFont.ImageFont, max_width: int, max_lines: int) -> list[str]:
    result: list[str] = []
    for paragraph in value.splitlines() or [""]:
        current = ""
        for char in paragraph:
            trial = current + char
            if not current or text_size(draw, trial, fnt)[0] <= max_width:
                current = trial
                continue
            result.append(current)
            current = char
            if len(result) >= max_lines:
                return result
        result.append(current)
        if len(result) >= max_lines:
            return result
    return result[:max_lines]


def draw_box_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    value: str,
    size: int,
    fill: str,
    weight: int = 2,
    max_lines: int = 1,
    min_size: int = 12,
    line_gap: int = 5,
) -> None:
    x1, y1, x2, y2 = box
    max_w = x2 - x1
    max_h = y2 - y1
    for current_size in range(size, min_size - 1, -1):
        fnt = font(current_size)
        lines = wrap(draw, value, fnt, max_w, max_lines)
        line_h = text_size(draw, "\u4fee", fnt)[1] + line_gap
        if lines and line_h * len(lines) - line_gap <= max_h:
            y = y1
            for line in lines:
                draw_weighted(draw, (x1, y), line, fnt, fill, weight)
                y += line_h
            return


def draw_field(
    draw: ImageDraw.ImageDraw,
    label: str,
    value: str,
    label_box: tuple[int, int, int, int],
    value_box: tuple[int, int, int, int],
    value_fill: str,
    value_size: int,
    value_lines: int = 1,
) -> None:
    draw_box_text(draw, label_box, label, 17, "#647084", weight=2)
    draw_box_text(draw, value_box, value, value_size, value_fill, weight=2, max_lines=value_lines)



def progress_ratio_from_text(value: str) -> float:
    head = str(value).split()[0]
    if "/" not in head:
        return 0.0
    current, required = head.split("/", 1)
    try:
        return max(0.0, min(1.0, int(current) / max(1, int(required))))
    except ValueError:
        return 0.0


def draw_sprite_progress_trough_preview(image: Image.Image, box: tuple[int, int, int, int], ratio: float) -> None:
    x1, y1, x2, y2 = box
    size = (x2 - x1, y2 - y1)
    ratio = max(0.0, min(1.0, float(ratio)))
    frame_path = SPRITES_DIR / "experience_trough.png"
    liquid_path = SPRITES_DIR / "experience_trough_1.png"
    try:
        frame = Image.open(frame_path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        liquid_raw = Image.open(liquid_path).convert("RGBA")
    except OSError:
        return

    liquid_scale = size[1] / max(1, liquid_raw.height)
    liquid_size = (max(1, int(liquid_raw.width * liquid_scale)), size[1])
    liquid = liquid_raw.resize(liquid_size, Image.Resampling.LANCZOS)
    liquid_x = x1 + (size[0] - liquid.width) // 2
    image.alpha_composite(liquid, (liquid_x, y1))

    fill_width = max(0, min(liquid.width, int(liquid.width * ratio)))
    if fill_width < liquid.width:
        liquid_alpha = liquid.getchannel("A")
        dim_gate = Image.new("L", liquid.size, 0)
        ImageDraw.Draw(dim_gate).rectangle((fill_width, 0, liquid.width, liquid.height), fill=255)
        dim_alpha = ImageChops.multiply(liquid_alpha, dim_gate).point(lambda value: int(value * 0.55))
        dim_layer = Image.new("RGBA", liquid.size, (24, 28, 42, 255))
        dim_layer.putalpha(dim_alpha)
        image.alpha_composite(dim_layer, (liquid_x, y1))

    image.alpha_composite(frame, (x1, y1))

def render_preview(bg: Image.Image, portrait_overlay: Image.Image) -> None:
    image = bg.convert("RGBA").copy()
    avatar_bbox = (199, 122, 459, 382)
    avatar = render_avatar_layer((avatar_bbox[2] - avatar_bbox[0], avatar_bbox[3] - avatar_bbox[1]))
    # Layer order: background, avatar, then portrait frame overlay on top.
    image.alpha_composite(avatar, avatar_bbox[:2])
    image.alpha_composite(portrait_overlay, (145, 55))

    draw = ImageDraw.Draw(image)
    dark = "#172033"
    muted = "#647084"
    accent = "#7b5cf0"
    gold = "#93702d"
    danger = "#9b3f1e"

    draw_box_text(draw, (545, 150, 900, 206), TEXT["title"], 42, dark, weight=3)
    draw_box_text(draw, (545, 214, 930, 254), TEXT["name"], 31, "#4b5565", weight=2)
    draw_box_text(draw, (545, 260, 955, 292), TEXT["hint"], 20, gold, weight=2)

    draw_field(draw, TEXT["root_label"], TEXT["root_value"], (238, 455, 390, 484), (238, 488, 545, 562), accent, 19, 3)
    draw_field(draw, TEXT["purity_label"], TEXT["purity_value"], (475, 455, 680, 484), (475, 492, 790, 560), accent, 22, 2)
    draw_field(draw, TEXT["realm_label"], TEXT["realm_value"], (835, 440, 1005, 468), (835, 472, 1038, 535), dark, 34, 1)

    draw_field(draw, TEXT["sign_label"], TEXT["sign_value"], (188, 608, 380, 638), (188, 650, 500, 704), dark, 36, 1)
    draw_field(draw, TEXT["total_label"], TEXT["total_value"], (650, 608, 858, 638), (650, 650, 1040, 704), accent, 36, 1)

    columns = [(210, 455), (500, 755), (800, 1060)]
    rows = [(754, 820), (842, 908), (930, 996)]
    for index, (label, value) in enumerate(GRID_ITEMS):
        col = index % 3
        row = index // 3
        x1, x2 = columns[col]
        y1, y2 = rows[row]
        draw_field(
            draw,
            label,
            value,
            (x1, y1, x2, y1 + 23),
            (x1, y1 + 27, x2, y2),
            danger if index == 5 else accent,
            17,
            2,
        )

    draw_sprite_progress_trough_preview(image, (188, 1018, 1065, 1095), progress_ratio_from_text(TEXT["progress_value"]))
    draw_box_text(draw, (320, 1045, 520, 1080), TEXT["progress_label"], 24, "#ffffff", weight=3)
    draw_box_text(draw, (785, 1045, 1065, 1080), TEXT["progress_value"], 21, "#ffffff", weight=2)
    draw_box_text(draw, (760, 1130, 1085, 1160), TEXT["footer"], 16, muted, weight=1)
    image.save(HTML_DIR / "signin_ui_sprite_preview.png")


def write_html() -> None:
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=1254, initial-scale=1" />
  <title>Xiuxian Signin Panel</title>
  <style>
    @font-face {{
      font-family: XiuxianUI;
      src: url("../../../../fonts/NotoSansSC-VF.ttf") format("truetype");
      font-weight: 100 900;
    }}
    html, body {{
      margin: 0;
      width: 1254px;
      height: 1254px;
      background: transparent;
      font-family: XiuxianUI, "Noto Sans SC", sans-serif;
    }}
    .ui-root {{
      position: relative;
      width: 1254px;
      height: 1254px;
      overflow: hidden;
      color: #172033;
    }}
    .sprite {{
      position: absolute;
      background-repeat: no-repeat;
      background-size: 100% 100%;
      pointer-events: none;
    }}
    .bg {{
      left: 0;
      top: 0;
      width: 1254px;
      height: 1254px;
      background-image: url("../sprites/signin_background_base.png");
      z-index: 0;
    }}
    .avatar {{
      position: absolute;
      left: 199px;
      top: 122px;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      overflow: hidden;
      z-index: 2;
    }}
    .avatar img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transform: scale(1.0);
    }}
    .portrait-frame {{
      left: 145px;
      top: 55px;
      width: 370px;
      height: 375px;
      background-image: url("../sprites/portrait_frame_overlay.png");
      z-index: 4;
    }}
    .text {{
      position: absolute;
      z-index: 5;
      overflow: hidden;
      line-height: 1.18;
      letter-spacing: 0;
      text-shadow: 0 1px 0 rgba(255,255,255,.42);
    }}
    .title {{ left: 545px; top: 150px; width: 355px; height: 56px; font-size: 42px; font-weight: 780; color: #172033; }}
    .name {{ left: 545px; top: 214px; width: 385px; height: 40px; font-size: 31px; font-weight: 560; color: #4b5565; }}
    .hint {{ left: 545px; top: 260px; width: 410px; height: 32px; font-size: 20px; font-weight: 650; color: #93702d; }}
    .label {{ font-size: 17px; font-weight: 720; color: #647084; }}
    .value {{ color: #7b5cf0; font-weight: 680; }}
    .realm-value {{ color: #172033; font-size: 34px; font-weight: 740; }}
    .root-label {{ left: 238px; top: 455px; width: 152px; height: 29px; }}
    .root-value {{ left: 238px; top: 488px; width: 307px; height: 74px; font-size: 19px; }}
    .purity-label {{ left: 475px; top: 455px; width: 205px; height: 29px; }}
    .purity-value {{ left: 475px; top: 492px; width: 315px; height: 68px; font-size: 22px; }}
    .realm-label {{ left: 835px; top: 440px; width: 170px; height: 28px; }}
    .realm-value {{ left: 835px; top: 472px; width: 205px; height: 63px; }}
    .sign-label {{ left: 188px; top: 608px; width: 192px; height: 30px; }}
    .sign-value {{ left: 188px; top: 650px; width: 312px; height: 54px; color: #172033; font-size: 36px; font-weight: 650; }}
    .total-label {{ left: 650px; top: 608px; width: 208px; height: 30px; }}
    .total-value {{ left: 650px; top: 650px; width: 390px; height: 54px; font-size: 36px; }}
    .cell-label {{ font-size: 17px; font-weight: 760; color: #647084; }}
    .cell-value {{ font-size: 17px; font-weight: 680; color: #7b5cf0; }}
    .danger {{ color: #9b3f1e; }}
    .progress-label {{ left: 320px; top: 1045px; width: 200px; height: 35px; font-size: 24px; font-weight: 780; color: #ffffff; }}
    .progress-value {{ left: 785px; top: 1045px; width: 280px; height: 35px; font-size: 21px; font-weight: 650; color: #ffffff; }}
    .footer {{ left: 760px; top: 1130px; width: 325px; height: 30px; font-size: 16px; color: #647084; text-align: right; }}
  </style>
</head>
<body>
  <div class="ui-root">
    <div class="sprite bg"></div>
    <div class="avatar"><img src="sample_avatar.png" alt=""></div>
    <div class="sprite portrait-frame"></div>
    <div class="text title">{TEXT["title"]}</div>
    <div class="text name">{TEXT["name"]}</div>
    <div class="text hint">{TEXT["hint"]}</div>
    <div class="text label root-label">{TEXT["root_label"]}</div>
    <div class="text value root-value">{TEXT["root_value"].replace(chr(10), "<br>")}</div>
    <div class="text label purity-label">{TEXT["purity_label"]}</div>
    <div class="text value purity-value">{TEXT["purity_value"].replace(chr(10), "<br>")}</div>
    <div class="text label realm-label">{TEXT["realm_label"]}</div>
    <div class="text realm-value">{TEXT["realm_value"]}</div>
    <div class="text label sign-label">{TEXT["sign_label"]}</div>
    <div class="text sign-value">{TEXT["sign_value"]}</div>
    <div class="text label total-label">{TEXT["total_label"]}</div>
    <div class="text value total-value">{TEXT["total_value"]}</div>
"""
    columns = [(210, 455), (500, 755), (800, 1060)]
    rows = [(754, 820), (842, 908), (930, 996)]
    for index, (label, value) in enumerate(GRID_ITEMS):
        col = index % 3
        row = index // 3
        x1, x2 = columns[col]
        y1, y2 = rows[row]
        cls = "cell-value danger" if index == 5 else "cell-value"
        html += f"""    <div class="text cell-label" style="left:{x1}px;top:{y1}px;width:{x2-x1}px;height:23px;">{label}</div>
    <div class="text {cls}" style="left:{x1}px;top:{y1+27}px;width:{x2-x1}px;height:{y2-y1-27}px;">{value}</div>
"""
    html += f"""    <div class="text progress-label">{TEXT["progress_label"]}</div>
    <div class="text progress-value">{TEXT["progress_value"]}</div>
    <div class="text footer">{TEXT["footer"]}</div>
  </div>
</body>
</html>
"""
    (HTML_DIR / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    bg = Image.open(BG_PATH).convert("RGBA")
    sheet, sprites = pack_components(bg)
    sheet.save(SHEET_DIR / "spritesheet.png")
    write_spec()
    write_layout(sheet, sprites)

    portrait_component = next(component for component in COMPONENTS if component.id == "portrait_frame_overlay")
    portrait = apply_component_mask(bg.crop(portrait_component.crop), portrait_component)
    load_sample_avatar().save(HTML_DIR / "sample_avatar.png")
    render_preview(bg, portrait)
    write_html()

    print(SHEET_DIR / "spritesheet.png")
    print(SPEC_DIR / "spec.json")
    print(SPEC_DIR / "layout.json")
    print(HTML_DIR / "index.html")
    print(HTML_DIR / "signin_ui_sprite_preview.png")


if __name__ == "__main__":
    main()
