from __future__ import annotations

import importlib.util
import json
import sys
import types
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import beast_realm as br  # noqa: E402

OUT_PATH = ROOT / "build" / "previews" / "beast_realm_preview_latest.png"
OUT_ALL_CARDS_PATH = ROOT / "build" / "previews" / "beast_realm_all_cards_preview.png"
PORTRAIT_DIR = ROOT / "assets" / "character_portraits" / "portraits"
SPELL_ICON_DIR = ROOT / "assets" / "beast_realm_spell_icons"
FONT_PATH = ROOT / "assets" / "fonts" / "HarmonyOS_Sans_SC.ttf"
BG_PATH = ROOT / "assets" / "panel_backgrounds" / "beast_realm_background.png"
REPORT_BG_PATH = ROOT / "assets" / "panel_backgrounds" / "beast_realm_background_vertical.png"
CARD_ART_RATIO = 0.70

W, H = 1680, 1080
REPORT_BG_IMAGE_H = H
REPORT_BG_FADE_H = 160
REPORT_BG_COLOR = (11, 17, 29)


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = image.size
    scale = max(target_w / src_w, target_h / src_h)
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def cover_resize_focus(image: Image.Image, size: tuple[int, int], focus_x: float = 0.5, focus_y: float = 0.36) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = image.size
    scale = max(target_w / max(1, src_w), target_h / max(1, src_h))
    resized = image.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))), Image.Resampling.LANCZOS)
    max_left = max(0, resized.width - target_w)
    max_top = max(0, resized.height - target_h)
    left = int(resized.width * focus_x - target_w * 0.5)
    top = int(resized.height * focus_y - target_h * 0.36)
    left = min(max(0, left), max_left)
    top = min(max(0, top), max_top)
    return resized.crop((left, top, left + target_w, top + target_h))


def portrait_on_focused_background(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    canvas = cover_resize_focus(image.convert("RGBA"), size)
    shade = Image.new("RGBA", size, (8, 10, 16, 28))
    canvas = Image.alpha_composite(canvas, shade)
    vignette = Image.new("RGBA", size, (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    vdraw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=8, outline=(255, 239, 190, 52), width=8)
    return Image.alpha_composite(canvas, vignette.filter(ImageFilter.GaussianBlur(2)))


def contain_on_blurred_background(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    base = cover_resize(image.convert("RGBA"), size).filter(ImageFilter.GaussianBlur(5))
    shade_layer = Image.new("RGBA", size, (8, 10, 16, 58))
    canvas = Image.alpha_composite(base, shade_layer)
    foreground = image.convert("RGBA")
    foreground.thumbnail((max(1, size[0] - 8), max(1, size[1] - 8)), Image.Resampling.LANCZOS)
    x = (size[0] - foreground.width) // 2
    y = (size[1] - foreground.height) // 2
    canvas.alpha_composite(foreground, (x, y))
    vignette = Image.new("RGBA", size, (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    vdraw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=8, outline=(255, 239, 190, 52), width=8)
    return Image.alpha_composite(canvas, vignette.filter(ImageFilter.GaussianBlur(2)))




def make_bg(size: tuple[int, int] = (W, H), blur: float = 1.2, shade: int = 126) -> Image.Image:
    if BG_PATH.exists():
        bg = cover_resize(Image.open(BG_PATH).convert("RGB"), size)
        bg = ImageEnhance.Color(bg).enhance(0.9)
        bg = ImageEnhance.Brightness(bg).enhance(0.78)
        bg = bg.filter(ImageFilter.GaussianBlur(blur))
    else:
        bg = Image.new("RGB", size, "#18233a")
    overlay = Image.new("RGBA", size, (10, 16, 28, shade))
    return Image.alpha_composite(bg.convert("RGBA"), overlay)


def make_report_bg(size: tuple[int, int], blur: float = 1.2, shade: int = 126) -> Image.Image:
    width, height = size
    if REPORT_BG_PATH.exists():
        bg = cover_resize(Image.open(REPORT_BG_PATH).convert("RGB"), size)
        bg = ImageEnhance.Color(bg).enhance(0.94)
        bg = ImageEnhance.Brightness(bg).enhance(0.78)
        overlay = Image.new("RGBA", size, (10, 16, 28, shade))
        return Image.alpha_composite(bg.convert("RGBA"), overlay)
    if height <= REPORT_BG_IMAGE_H:
        return make_bg(size, blur=blur, shade=shade)
    canvas = Image.new("RGBA", size, (*REPORT_BG_COLOR, 255))
    image_h = min(REPORT_BG_IMAGE_H, height)
    canvas.alpha_composite(make_bg((width, image_h), blur=blur, shade=shade), (0, 0))
    fade_h = min(REPORT_BG_FADE_H, image_h)
    if fade_h > 0:
        fade = Image.new("RGBA", (width, fade_h), (0, 0, 0, 0))
        fade_draw = ImageDraw.Draw(fade)
        for row in range(fade_h):
            alpha = int(255 * (row + 1) / fade_h)
            fade_draw.line((0, row, width, row), fill=(*REPORT_BG_COLOR, alpha))
        canvas.alpha_composite(fade, (0, image_h - fade_h))
    return canvas


def round_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str | tuple[int, int, int, int] | None,
    outline=None,
    width: int = 1,
    radius: int = 8,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in str(text):
        candidate = current + char
        if text_size(draw, candidate, fnt)[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = char
    if current:
        lines.append(current)
    return lines or [""]


def fit_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    max_size: int,
    min_size: int = 8,
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    for size in range(max_size, min_size - 1, -1):
        fnt = font(size)
        lines = wrap_lines(draw, text, fnt, max_width)
        line_h = text_size(draw, "国", fnt)[1] + max(1, size // 5)
        if line_h * len(lines) <= max_height:
            return fnt, lines, line_h
    fnt = font(min_size)
    lines = wrap_lines(draw, text, fnt, max_width)
    line_h = text_size(draw, "国", fnt)[1] + 1
    return fnt, lines, line_h


def badge_size(draw: ImageDraw.ImageDraw, text: str, size: int) -> tuple[int, int]:
    fnt = font(size)
    tw, th = text_size(draw, text, fnt)
    return tw + max(12, size), th + max(6, size // 2)


def stat_badge(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: str, size: int = 20) -> tuple[int, int]:
    x, y = xy
    fnt = font(size)
    tw, th = text_size(draw, text, fnt)
    pad_x = max(6, size // 2)
    pad_y = max(3, size // 5)
    box = (x, y, x + tw + pad_x * 2, y + th + pad_y * 2)
    round_rect(draw, box, fill, outline=(255, 236, 190, 130), width=1, radius=7)
    draw.text((x + pad_x, y + pad_y - 1), text, font=fnt, fill="#fff5df")
    return box[2] - box[0], box[3] - box[1]


def portrait_for(card: dict) -> Image.Image:
    portrait_id = str(card.get("portrait_id") or "")
    path = PORTRAIT_DIR / f"{portrait_id}.png"
    if path.exists():
        return Image.open(path).convert("RGBA")
    return Image.new("RGBA", (360, 520), (35, 42, 58, 255))


def spell_icon_for(card: dict) -> Image.Image | None:
    icon_id = str(card.get("icon_id") or card.get("id") or "").strip().replace("\\", "/").split("/")[-1]
    if not icon_id or icon_id in {".", ".."}:
        return None
    if not icon_id.endswith(".png"):
        icon_id = f"{icon_id}.png"
    path = SPELL_ICON_DIR / icon_id
    if path.exists():
        return Image.open(path).convert("RGBA")
    return None


def draw_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    max_size: int,
    fill: str,
    min_size: int = 8,
) -> None:
    x1, y1, x2, y2 = box
    max_width = max(1, x2 - x1)
    max_height = max(1, y2 - y1)
    fnt, lines, line_h = fit_lines(draw, text, max_width, max_height, max_size, min_size)
    max_lines = max(1, max_height // max(1, line_h))
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        line = lines[-1]
        suffix = "..."
        while line and text_size(draw, line + suffix, fnt)[0] > max_width:
            line = line[:-1]
        lines[-1] = (line + suffix) if line else suffix
    for idx, line in enumerate(lines[:max_lines]):
        draw.text((x1, y1 + idx * line_h), line, font=fnt, fill=fill)


def draw_beast_card(canvas: Image.Image, card: dict, box: tuple[int, int, int, int], selected: bool = False) -> None:
    draw = ImageDraw.Draw(canvas)
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    compact = w < 190 or h < 280
    border = "#e8c978" if selected else "#9f8654"
    round_rect(draw, box, (28, 32, 42, 228), outline=border, width=3 if selected else 2, radius=8)

    pad = max(6, int(w * 0.035))
    art_bottom = y1 + int(h * CARD_ART_RATIO)
    inner = (x1 + pad, y1 + pad, x2 - pad, art_bottom)
    portrait = portrait_on_focused_background(portrait_for(card), (inner[2] - inner[0], inner[3] - inner[1]))
    portrait = ImageEnhance.Contrast(portrait).enhance(1.08)
    mask = Image.new("L", portrait.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, portrait.width, portrait.height), radius=6, fill=255)
    canvas.paste(portrait, inner[:2], mask)
    draw.rounded_rectangle(inner, radius=6, outline=(255, 239, 190, 92), width=1)

    info_h = min(58 if not compact else 52, max(46, int((inner[3] - inner[1]) * 0.30)))
    info_box = (inner[0] + 2, inner[3] - info_h - 2, inner[2] - 2, inner[3] - 2)
    round_rect(draw, info_box, (8, 15, 25, 190), radius=6)

    badge_font = 14 if compact else 18
    atk_text = f"攻 {card['attack']}"
    def_text = f"御 {card['defense']}"
    def_w, def_h = badge_size(draw, def_text, badge_font)
    badge_y = max(inner[1] + 6, info_box[1] - def_h - 5)
    stat_badge(draw, (inner[0] + 6, badge_y), atk_text, "#9f463d", badge_font)
    stat_badge(draw, (inner[2] - def_w - 6, badge_y), def_text, "#356f8f", badge_font)

    content_x = info_box[0] + 7
    content_w = info_box[2] - info_box[0] - 14
    name_y = info_box[1] + 5
    name_height = 26 if compact else 30
    draw_text_block(draw, str(card["name"]), (content_x, name_y, content_x + content_w, name_y + name_height), 18 if compact else 22, "#fff1d2", 11)
    meta_y = name_y + name_height
    meta = f"{card['realm']}  {card['faction']}·{card['element']}"
    draw_text_block(draw, meta, (content_x, meta_y, content_x + content_w, info_box[3] - 4), 11 if compact else 15, "#c8d7e8", 8)

    effect_top = inner[3] + max(5, int(h * 0.025))
    effect_box = (x1 + pad, effect_top, x2 - pad, y2 - pad)
    round_rect(draw, effect_box, (21, 24, 32, 178), outline=(207, 178, 112, 70), width=1, radius=6)
    draw_text_block(
        draw,
        str(card["effect"]),
        (effect_box[0] + 6, effect_box[1] + 4, effect_box[2] - 6, effect_box[3] - 4),
        13 if compact else 16,
        "#d8d1bd",
        8,
    )


def draw_spell_card(canvas: Image.Image, card: dict, box: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(canvas)
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    compact = w < 190 or h < 280
    pad = max(6, int(w * 0.04))
    round_rect(draw, box, (35, 31, 54, 232), outline="#bda56a", width=2, radius=8)

    icon_box = (x1 + pad, y1 + pad, x2 - pad, y1 + int(h * CARD_ART_RATIO))
    round_rect(draw, icon_box, (67, 51, 88, 228), outline=(232, 208, 151, 100), width=1, radius=8)
    icon = spell_icon_for(card)
    if icon is not None:
        inner = (icon_box[0] + 4, icon_box[1] + 4, icon_box[2] - 4, icon_box[3] - 4)
        icon = contain_on_blurred_background(icon, (inner[2] - inner[0], inner[3] - inner[1]))
        mask = Image.new("L", icon.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, icon.width, icon.height), radius=6, fill=255)
        canvas.paste(icon, inner[:2], mask)
    else:
        glyph = {"丹药": "丹", "符箓": "符", "神通": "通", "阵法": "阵"}.get(str(card["category"]), "术")
        glyph_font = font(42 if compact else 58)
        gw, gh = text_size(draw, glyph, glyph_font)
        draw.text((icon_box[0] + (icon_box[2] - icon_box[0] - gw) // 2, icon_box[1] + (icon_box[3] - icon_box[1] - gh) // 2 - 2), glyph, font=glyph_font, fill="#f1d58c")

    info_h = min(58 if not compact else 52, max(46, int((icon_box[3] - icon_box[1]) * 0.30)))
    info_box = (icon_box[0] + 2, icon_box[3] - info_h - 2, icon_box[2] - 2, icon_box[3] - 2)
    round_rect(draw, info_box, (8, 15, 25, 190), radius=6)

    cost_text = f"{br.card_cost(card)} 灵石"
    cost_size = 13 if compact else 18
    cost_w, cost_h = badge_size(draw, cost_text, cost_size)
    cost_y = max(icon_box[1] + 6, info_box[1] - cost_h - 5)
    stat_badge(draw, (icon_box[2] - cost_w - 6, cost_y), cost_text, "#6f5a33", cost_size)

    content_x = info_box[0] + 7
    content_w = info_box[2] - info_box[0] - 14
    name_y = info_box[1] + 5
    name_height = 26 if compact else 30
    draw_text_block(draw, str(card["name"]), (content_x, name_y, content_x + content_w, name_y + name_height), 18 if compact else 22, "#fff1d2", 11)
    meta_y = name_y + name_height
    draw_text_block(draw, f"{card['realm']}  {card['category']}", (content_x, meta_y, content_x + content_w, info_box[3] - 4), 11 if compact else 15, "#c8d7e8", 8)

    effect_top = icon_box[3] + max(5, int(h * 0.025))
    effect_box = (x1 + pad, effect_top, x2 - pad, y2 - pad)
    round_rect(draw, effect_box, (24, 22, 34, 178), outline=(207, 178, 112, 70), width=1, radius=6)
    draw_text_block(
        draw,
        str(card["effect"]),
        (effect_box[0] + 6, effect_box[1] + 4, effect_box[2] - 6, effect_box[3] - 4),
        13 if compact else 16,
        "#d8d1bd",
        8,
    )


def draw_card(canvas: Image.Image, card: dict, box: tuple[int, int, int, int], selected: bool = False) -> None:
    if card.get("kind") == "spell":
        draw_spell_card(canvas, card, box)
    else:
        draw_beast_card(canvas, card, box, selected=selected)


PLAYER_AVATAR_PATH = ROOT / "assets" / "ui_sprite" / "signin" / "output" / "html" / "sample_avatar.png"
OUT_JOIN_PATH = ROOT / "build" / "previews" / "beast_realm_join_preview.png"
OUT_TASK_HALL_PATH = ROOT / "build" / "previews" / "beast_realm_task_hall_preview.png"
OUT_BATTLE_REPORT_PATH = ROOT / "build" / "previews" / "beast_realm_battle_report_preview.png"
OUT_HELP_PANEL_PATH = ROOT / "build" / "previews" / "beast_realm_help_panel_preview.png"
OUT_LOBBY_PANEL_PATH = ROOT / "build" / "previews" / "beast_realm_lobby_panel_preview.png"
OUT_LEADER_PANEL_PATH = ROOT / "build" / "previews" / "beast_realm_leader_choice_panel_preview.png"
OUT_START_ROUND_PANEL_PATH = ROOT / "build" / "previews" / "beast_realm_start_round_panel_preview.png"
OUT_STATUS_PANEL_PATH = ROOT / "build" / "previews" / "beast_realm_status_panel_preview.png"
OUT_TASK_PANEL_PATH = ROOT / "build" / "previews" / "beast_realm_runtime_task_panel.png"
OUT_ACTION_PANEL_PATH = ROOT / "build" / "previews" / "beast_realm_action_result_panel_preview.png"
OUT_RUNTIME_BATTLE_PANEL_PATH = ROOT / "build" / "previews" / "beast_realm_runtime_battle_report_panel.png"
OUT_FULL_LIBRARY_PANEL_PATH = ROOT / "build" / "previews" / "beast_realm_full_card_library_preview.png"
OUT_SPELL_LIBRARY_PANEL_PATH = ROOT / "build" / "previews" / "beast_realm_spell_library_preview.png"
OUT_PREVIEW_MANIFEST_PATH = ROOT / "build" / "previews" / "beast_realm_preview_manifest.json"
OUT_CONTACT_SHEET_PATH = ROOT / "build" / "previews" / "beast_realm_preview_contact_sheet.png"


def draw_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str) -> None:
    round_rect(draw, box, (18, 24, 36, 204), outline=(217, 194, 132, 130), width=2, radius=8)
    x1, y1, x2, _ = box
    draw.text((x1 + 22, y1 + 16), title, font=font(26), fill="#f6df9b")
    draw.line((x1 + 18, y1 + 58, x2 - 18, y1 + 58), fill=(218, 194, 133, 100), width=1)


def draw_outline_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str) -> None:
    round_rect(draw, box, None, outline=(232, 204, 132, 170), width=2, radius=8)
    x1, y1, x2, _ = box
    draw.text((x1 + 22, y1 + 16), title, font=font(26), fill="#f6df9b")
    draw.line((x1 + 18, y1 + 58, x2 - 18, y1 + 58), fill=(232, 204, 132, 115), width=1)


def draw_chip(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fill: str | tuple[int, int, int, int] = (52, 66, 78, 204),
    outline: tuple[int, int, int, int] = (218, 194, 133, 110),
    size: int = 20,
) -> None:
    round_rect(draw, box, fill, outline=outline, width=1, radius=8)
    fnt = font(size)
    tw, th = text_size(draw, text, fnt)
    x1, y1, x2, y2 = box
    draw.text((x1 + (x2 - x1 - tw) // 2, y1 + (y2 - y1 - th) // 2 - 1), text, font=fnt, fill="#f6e5bd")


def draw_lines(draw: ImageDraw.ImageDraw, lines: list[str], xy: tuple[int, int], size: int, fill: str, line_h: int | None = None) -> None:
    x, y = xy
    fnt = font(size)
    step = line_h or int(size * 1.62)
    for index, line in enumerate(lines):
        draw.text((x, y + index * step), line, font=fnt, fill=fill)


def player_avatar() -> Image.Image:
    if PLAYER_AVATAR_PATH.exists():
        return Image.open(PLAYER_AVATAR_PATH).convert("RGBA")
    return Image.new("RGBA", (512, 512), (57, 73, 91, 255))


def draw_avatar(canvas: Image.Image, box: tuple[int, int, int, int], ring: str = "#e8c978") -> None:
    draw = ImageDraw.Draw(canvas)
    x1, y1, x2, y2 = box
    size = (x2 - x1, y2 - y1)
    avatar = cover_resize(player_avatar(), size)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size[0] - 1, size[1] - 1), fill=255)
    canvas.paste(avatar, (x1, y1), mask)
    draw.ellipse(box, outline=ring, width=3)


def draw_message(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    name: str,
    lines: list[str],
    avatar: bool = True,
    accent: str = "#6a7d92",
) -> None:
    draw = ImageDraw.Draw(canvas)
    round_rect(draw, box, (28, 35, 48, 218), outline=(209, 186, 121, 90), width=1, radius=8)
    x1, y1, x2, _ = box
    text_x = x1 + 92 if avatar else x1 + 22
    if avatar:
        draw_avatar(canvas, (x1 + 18, y1 + 18, x1 + 70, y1 + 70), accent)
    draw.text((text_x, y1 + 14), name, font=font(20), fill="#f3d991")
    draw_lines(draw, lines, (text_x, y1 + 48), 22, "#e8dfcb", 34)


def draw_player_row(canvas: Image.Image, box: tuple[int, int, int, int], name: str, detail: str, status: str, ring: str) -> None:
    draw = ImageDraw.Draw(canvas)
    round_rect(draw, box, (30, 38, 50, 196), outline=(170, 151, 104, 88), width=1, radius=8)
    x1, y1, x2, y2 = box
    draw_avatar(canvas, (x1 + 14, y1 + 12, x1 + 76, y1 + 74), ring)
    draw.text((x1 + 92, y1 + 16), name, font=font(24), fill="#fff0c6")
    draw.text((x1 + 92, y1 + 50), detail, font=font(18), fill="#cbd8e6")
    draw_chip(draw, (x2 - 112, y1 + 22, x2 - 22, y2 - 22), status, fill=(64, 76, 72, 205), size=17)


def draw_leader_card(canvas: Image.Image, leader: dict, box: tuple[int, int, int, int], selected: bool = False) -> None:
    draw = ImageDraw.Draw(canvas)
    x1, y1, x2, y2 = box
    border = "#f2d17a" if selected else "#8fa6b8"
    fill = (38, 42, 54, 232) if selected else (27, 34, 47, 222)
    round_rect(draw, box, fill, outline=border, width=3 if selected else 1, radius=8)
    draw.text((x1 + 16, y1 + 14), str(leader.get("name", "峰主")), font=font(24), fill="#fff0c6")
    stat_badge(draw, (x2 - 132, y1 + 12), f"生命 {leader.get('health', 0)}", "#6c4d3a", 16)
    draw.line((x1 + 14, y1 + 54, x2 - 14, y1 + 54), fill=(224, 198, 132, 96), width=1)
    draw_text_block(
        draw,
        str(leader.get("skill", "")),
        (x1 + 16, y1 + 68, x2 - 16, y2 - 16),
        18,
        "#dfe6ee",
        10,
    )


def draw_board_mat(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str) -> None:
    x1, y1, x2, y2 = box
    round_rect(draw, box, (16, 25, 34, 218), outline=(229, 199, 120, 128), width=2, radius=8)
    inner = (x1 + 20, y1 + 50, x2 - 20, y2 - 18)
    draw.rounded_rectangle(inner, radius=8, fill=None, outline=(166, 136, 82, 150), width=2)
    mid_y = inner[1] + (inner[3] - inner[1]) // 2
    draw.line((inner[0] + 18, mid_y, inner[2] - 18, mid_y), fill=(221, 199, 141, 132), width=2)
    draw.text((x1 + 22, y1 + 16), title, font=font(26), fill="#f6df9b")


def draw_board_row(
    canvas: Image.Image,
    cards: list[dict],
    y: int,
    selected_index: int | None = None,
    slots: int = 7,
) -> None:
    draw = ImageDraw.Draw(canvas)
    left, right = 218, 1558
    card_w, card_h = 148, 220
    gap = (right - left - slots * card_w) // max(1, slots - 1)
    for idx in range(slots):
        x = left + idx * (card_w + gap)
        slot = (x - 5, y - 5, x + card_w + 5, y + card_h + 5)
        draw.rounded_rectangle(slot, radius=8, fill=None, outline=(213, 185, 113, 105), width=1)
        if idx < len(cards):
            draw_beast_card(canvas, cards[idx], (x, y, x + card_w, y + card_h), selected=selected_index == idx)

def pick_card(faction: str | None = None, tier: int | None = None, offset: int = 0) -> dict:
    cards = list(br.BEAST_REALM_CARDS)
    if faction is not None:
        cards = [card for card in cards if str(card.get("faction")) == faction]
    if tier is not None:
        cards = [card for card in cards if int(card.get("tier", 1)) == tier]
    if not cards:
        cards = list(br.BEAST_REALM_CARDS)
    return cards[offset % len(cards)]


def cards_by_factions(factions: list[str], tier: int, offset: int = 0) -> list[dict]:
    return [pick_card(faction, tier, index + offset) for index, faction in enumerate(factions)]


def render_join_preview() -> Image.Image:
    canvas = make_bg()
    draw = ImageDraw.Draw(canvas)
    draw.text((62, 42), "御兽秘境", font=font(56), fill="#fff0c6")
    draw.text((66, 112), "群聊开局 · 玩家加入游戏 · 私聊随机三选一峰主", font=font(26), fill="#cdd8e9")
    draw_chip(draw, (1246, 54, 1588, 108), "PVE 4V4 等待房  2/4", fill=(50, 65, 78, 202), size=22)

    draw_panel(draw, (56, 168, 978, 910), "群聊 · 御兽秘境大厅")
    draw_message(canvas, (86, 246, 910, 340), "林间客", ["御兽秘境开局 PVE", "开启4V4秘境演武，等待修士加入。"], True, "#e4bc70")
    draw_message(canvas, (160, 372, 910, 548), "系统", ["【御兽秘境等待房】4V4 PVE", "峰主：林间客    人数：1/4", "房主已收到峰主候选，请私聊选择峰主。"], False, "#86a5bb")
    draw_message(canvas, (86, 584, 910, 678), "云栖", ["加入御兽秘境"], True, "#88b4d8")
    draw_message(canvas, (160, 710, 910, 852), "系统", ["云栖已加入队伍，当前 2/4。", "峰主候选已发送到私聊；全部选定后才能开始。"], False, "#86a5bb")

    draw_panel(draw, (1010, 168, 1624, 910), "私聊 · 峰主选择")
    draw.text((1040, 236), "随机弹出 3 位峰主", font=font(25), fill="#f6df9b")
    leaders = [br.BEAST_REALM_LEADERS[1], br.BEAST_REALM_LEADERS[7], br.BEAST_REALM_LEADERS[16]]
    for idx, leader in enumerate(leaders):
        y = 292 + idx * 158
        draw_leader_card(canvas, leader, (1040, y, 1594, y + 128), selected=idx == 0)
        stat_badge(draw, (1052, y + 88), f"选择峰主 {idx + 1}", "#455f73", 15)
    draw.text((1040, 782), "峰主决定初始生命和专属技能；开始前可重新选择。", font=font(21), fill="#e8dfcb")
    round_rect(draw, (56, 936, 1624, 1010), (14, 20, 31, 188), outline=(215, 187, 117, 100), width=1, radius=8)
    draw.text((84, 956), "加入阶段仍在群聊完成；峰主选择与后续任务堂购买都在私聊完成。", font=font(24), fill="#e8dcc0")
    return canvas

def render_task_hall_preview() -> Image.Image:
    canvas = make_bg()
    draw = ImageDraw.Draw(canvas)
    draw.text((62, 42), "御兽秘境", font=font(56), fill="#fff0c6")
    draw.text((66, 112), "私聊准备 · 任务堂购买随从 · 金色卡牌与三连奖励", font=font(26), fill="#cdd8e9")
    draw_chip(draw, (1148, 54, 1588, 108), "第 3 回合  灵石 8/8  任务堂：金丹期", fill=(50, 65, 78, 202), size=21)

    draw_panel(draw, (56, 168, 448, 910), "玩家与手牌")
    draw_avatar(canvas, (92, 240, 174, 322), "#e8c978")
    draw.text((196, 242), "林间客", font=font(28), fill="#fff0c6")
    draw.text((196, 282), "青岚兽主 · 生命 42/42", font=font(20), fill="#cbd8e6")
    draw_text_block(draw, "峰主技：每回合开始随机友方+1/+1", (92, 342, 402, 396), 19, "#e8dfcb", 10)
    hand_cards = [pick_card("散修", 4, 2), pick_card("妖兽", 4, 3), pick_card("佛修", 4, 1)]
    draw.text((92, 430), "三连奖励 · 手牌", font=font(24), fill="#f6df9b")
    for idx, card in enumerate(hand_cards):
        x = 92 + idx * 108
        draw_beast_card(canvas, card, (x, 480, x + 92, 642), selected=idx == 1)
    draw_chip(draw, (92, 696, 402, 746), "选择1/2/3 · 奖励进手牌", fill=(52, 66, 78, 204), size=19)
    draw_chip(draw, (92, 766, 402, 816), "上阵 1 · 从手牌召唤", fill=(52, 66, 78, 204), size=19)

    draw_board_mat(draw, (480, 168, 1624, 702), "当前牌桌 · 战局")
    board_cards = [pick_card("佛修", 2, 1), pick_card("妖兽", 3, 4), pick_card("系统持有者", 3, 2), pick_card("散修", 2, 3), pick_card("邪修", 3, 5)]
    for idx, card in enumerate(board_cards):
        x = 528 + idx * 204
        draw_beast_card(canvas, card, (x, 292, x + 176, 590), selected=idx == 1)
    draw.text((514, 720), "任务堂商店", font=font(26), fill="#f6df9b")
    shop_cards = [pick_card("妖兽", 3, 2), pick_card("散修", 3, 1), pick_card("佛修", 2, 4), pick_card("系统持有者", 3, 0), br.BEAST_REALM_SPELL_BY_ID["br_spell_009"]]
    card_w = 178
    for idx, card in enumerate(shop_cards, start=1):
        x = 514 + (idx - 1) * 214
        box = (x, 764, x + card_w, 1018)
        draw_card(canvas, card, box, selected=idx == 1)
        stat_badge(draw, (box[0] + 8, box[1] + 8), str(idx), "#4f5f71", 15)
    draw_chip(draw, (1360, 718, 1588, 758), "购买1 / 施法5 2 / 升堂", fill=(45, 56, 67, 208), size=18)
    return canvas

def render_battle_report_preview() -> Image.Image:
    leader_lines = [
        "林间客 · 青岚兽主  生命 42/42  随机友方+1/+1",
        "云栖 · 阵箓宗师  生命 40/40  施法后布反阵",
        "执事一 · 任务堂补位  生命 36/36",
        "执事二 · 任务堂补位  生命 36/36",
    ]
    report = [
        "云栖的玄甲禅卫触发护卫，承受魔神残影一击。",
        "林间客的赤焰妖虎击破邪神眷属，攻击+5。",
        "域外天魔离场余威扫过敌阵，青岚前排攻击-4。",
        "峰主青岚兽主触发，随机友方获得+1/+1。",
        "修士队击退本轮兽潮，残存战力折算威压 12。",
    ]
    info_top = 792
    leader_line_h = 38
    report_line_h = 34
    info_h = max(154, 82 + len(leader_lines) * leader_line_h)
    report_h = max(154, 82 + len(report) * report_line_h)
    lower_h = max(info_h, report_h)
    height = max(1018, info_top + lower_h + 62)
    canvas = make_report_bg((W, height))
    draw = ImageDraw.Draw(canvas)
    draw.text((62, 42), "御兽秘境", font=font(56), fill="#fff0c6")
    draw.text((66, 112), "群聊回合开始 · 4V4 牌桌战报 · 自动推送", font=font(26), fill="#cdd8e9")
    draw_chip(draw, (1250, 54, 1588, 108), "第 4 回合战报  自动推送", fill=(50, 65, 78, 202), size=21)

    draw_board_mat(draw, (56, 156, 1624, 772), "群聊 · 牌桌战报")
    enemy_cards = [
        pick_card("邪神", 4, 2),
        pick_card("魔神", 4, 1),
        pick_card("域外天魔", 3, 3),
        pick_card("邪修", 4, 5),
        pick_card("邪神", 3, 6),
        pick_card("魔神", 3, 7),
        pick_card("域外天魔", 4, 8),
    ]
    ally_cards = [
        pick_card("佛修", 4, 0),
        pick_card("妖兽", 4, 1),
        pick_card("系统持有者", 3, 4),
        pick_card("散修", 3, 6),
        pick_card("天羽", 4, 2),
        pick_card("真龙遗脉", 4, 3),
        pick_card("佛修", 3, 7),
    ]
    draw_board_row(canvas, enemy_cards, 232)
    draw_board_row(canvas, ally_cards, 504, selected_index=1)
    draw_chip(draw, (710, 460, 970, 504), "VS · 自动结算", fill=(68, 48, 54, 225), size=22)
    draw.text((92, 236), "秘境敌阵", font=font(24), fill="#f6df9b")
    draw.text((92, 598), "青岚修士队", font=font(24), fill="#f6df9b")

    draw_outline_panel(draw, (56, info_top, 780, info_top + lower_h), "生命与峰主")
    draw_lines(draw, leader_lines, (88, info_top + 72), 21, "#e8dfcb", leader_line_h)

    draw_outline_panel(draw, (810, info_top, 1624, info_top + lower_h), "战报摘要")
    for idx, line in enumerate(report):
        y = info_top + 66 + idx * report_line_h
        draw_text_block(draw, line, (842, y, 1588, y + 30), 18, "#eee2c8", 10)
    return canvas

def render_preview() -> Image.Image:
    return render_task_hall_preview()


def render_all_cards_preview() -> Image.Image:
    cols = 9
    card_w, card_h = 170, 246
    margin_x, gap_x, gap_y = 36, 12, 16
    width = margin_x * 2 + cols * card_w + (cols - 1) * gap_x
    header_h = 150
    follower_rows = (len(br.BEAST_REALM_CARDS) + cols - 1) // cols
    spell_rows = (len(br.BEAST_REALM_SPELLS) + cols - 1) // cols
    section_gap = 84
    height = header_h + follower_rows * card_h + (follower_rows - 1) * gap_y + section_gap + spell_rows * card_h + (spell_rows - 1) * gap_y + 78
    canvas = make_bg((width, height), blur=2.0, shade=152)
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 34), "御兽秘境 · 全卡预览", font=font(42), fill="#fff0c6")
    draw.text((40, 94), f"{len(br.BEAST_REALM_CARDS)}张随从牌 + {len(br.BEAST_REALM_SPELLS)}张法术牌，随从阵营按妖兽、散修、佛修等角色种族区分。", font=font(20), fill="#cdd8e9")

    y = header_h
    draw.text((36, y - 42), "随从牌", font=font(26), fill="#f6df9b")
    for idx, card in enumerate(br.BEAST_REALM_CARDS):
        row, col = divmod(idx, cols)
        x = margin_x + col * (card_w + gap_x)
        yy = y + row * (card_h + gap_y)
        draw_beast_card(canvas, card, (x, yy, x + card_w, yy + card_h), selected=False)
    y += follower_rows * card_h + (follower_rows - 1) * gap_y + section_gap
    draw.text((36, y - 42), "法术牌", font=font(26), fill="#f6df9b")
    for idx, card in enumerate(br.BEAST_REALM_SPELLS):
        row, col = divmod(idx, cols)
        x = margin_x + col * (card_w + gap_x)
        yy = y + row * (card_h + gap_y)
        draw_spell_card(canvas, card, (x, yy, x + card_w, yy + card_h))
    return canvas



_RUNTIME_PACKAGE = "_beast_realm_preview_runtime"


def runtime_modules() -> tuple[Any, Any]:
    pkg = sys.modules.get(_RUNTIME_PACKAGE)
    if pkg is None:
        pkg = types.ModuleType(_RUNTIME_PACKAGE)
        pkg.__path__ = [str(ROOT)]
        sys.modules[_RUNTIME_PACKAGE] = pkg
    for mod_name in ["domain", "cards", "beast_realm", "beast_realm_cards"]:
        full_name = f"{_RUNTIME_PACKAGE}.{mod_name}"
        if full_name in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(full_name, ROOT / f"{mod_name}.py")
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load runtime module: {mod_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = module
        spec.loader.exec_module(module)
    return sys.modules[f"{_RUNTIME_PACKAGE}.beast_realm"], sys.modules[f"{_RUNTIME_PACKAGE}.beast_realm_cards"]


def render_runtime_panel_image(title: str, content: str, subtitle: str = "", footer: str = "", width: int = 1180) -> Image.Image:
    _runtime_br, runtime_cards = runtime_modules()
    data = runtime_cards.render_beast_realm_panel(title=title, content=content, subtitle=subtitle, width=width, footer=footer)
    return Image.open(BytesIO(data)).convert("RGB")


def save_preview_image(path: Path, image: Image.Image, manifest: list[dict[str, Any]], quality: int = 95) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = image.convert("RGB")
    output.save(path, quality=quality)
    manifest.append({"name": path.stem, "file": str(path), "width": output.width, "height": output.height})


def save_runtime_panel(path: Path, title: str, content: str, manifest: list[dict[str, Any]], subtitle: str = "", footer: str = "", width: int = 1180) -> None:
    save_preview_image(path, render_runtime_panel_image(title, content, subtitle=subtitle, footer=footer, width=width), manifest)


def set_preview_leader(player: dict[str, Any], choices: list[int], selected: int | None = 0) -> None:
    player["leader_choices"] = [str(br.BEAST_REALM_LEADERS[index]["id"]) for index in choices]
    if selected is not None:
        ok, message = br.choose_leader(player, selected + 1)
        if not ok:
            raise RuntimeError(message)


def preview_unit(player: dict[str, Any], faction: str, tier: int, offset: int = 0, golden: bool = False) -> dict[str, Any]:
    unit = br.unit_from_card(deepcopy(pick_card(faction, tier, offset)), golden=golden)
    unit["owner_id"] = str(player.get("id"))
    return unit


def build_lobby_preview_table() -> dict[str, Any]:
    table = br.create_table("preview-group", "10001", "林间客", "pve")
    br.add_player(table, "10002", "云栖")
    br.add_player(table, "10003", "照夜")
    players = br.active_human_players(table)
    set_preview_leader(players[0], [0, 7, 16], selected=0)
    players[1]["leader_choices"] = [str(br.BEAST_REALM_LEADERS[index]["id"]) for index in [1, 8, 17]]
    set_preview_leader(players[2], [2, 9, 18], selected=2)
    return table


def build_leader_preview_player() -> dict[str, Any]:
    player = br.create_human_player("10001", "林间客")
    set_preview_leader(player, [1, 7, 16], selected=1)
    return player


def build_recruit_preview_table() -> tuple[dict[str, Any], dict[str, Any]]:
    br.random.seed(20260705)
    table = br.create_table("preview-group", "10001", "林间客", "pve")
    for user_id, name in [("10002", "云栖"), ("10003", "照夜"), ("10004", "松月")]:
        br.add_player(table, user_id, name)
    players = br.active_human_players(table)
    for index, player in enumerate(players):
        set_preview_leader(player, [index, index + 6, index + 12], selected=0)
    ok, message = br.start_table(table)
    if not ok:
        raise RuntimeError(message)
    table["turn"] = 3
    table["phase"] = "recruit"
    for index, player in enumerate(players):
        player["peak_level"] = 3
        player["max_gold"] = 8
        player["gold"] = max(4, 8 - index)
        player["health"] = max(18, int(player.get("max_health", 36)) - index * 4)
        player["ready"] = index in {1, 3}
        player["board"] = [
            preview_unit(player, "妖兽", 3, index),
            preview_unit(player, "散修", 2, index + 1),
            preview_unit(player, "佛修", 3, index + 2),
        ]
        player["shop"] = [
            deepcopy(pick_card("妖兽", 3, index + 2)),
            deepcopy(pick_card("散修", 3, index + 3)),
            deepcopy(pick_card("佛修", 2, index + 4)),
            deepcopy(pick_card("系统持有者", 3, index)),
            deepcopy(br.BEAST_REALM_SPELL_BY_ID["br_spell_009"]),
        ]
        player["hand"] = [deepcopy(pick_card("天羽", 4, index)), deepcopy(pick_card("真龙遗脉", 4, index + 1))]
        player["discover"] = None
    focus = players[0]
    focus["ready"] = False
    focus["gold"] = 8
    focus["board"] = [
        preview_unit(focus, "佛修", 3, 1, golden=True),
        preview_unit(focus, "妖兽", 3, 4),
        preview_unit(focus, "系统持有者", 3, 2),
        preview_unit(focus, "散修", 2, 3),
    ]
    focus["hand"] = [deepcopy(pick_card("天羽", 4, 2)), deepcopy(pick_card("真龙遗脉", 4, 3))]
    focus["discover"] = {
        "source_card": str(pick_card("佛修", 3, 1).get("id")),
        "tier": 4,
        "choices": [deepcopy(pick_card("妖兽", 4, 1)), deepcopy(pick_card("散修", 4, 2)), deepcopy(pick_card("佛修", 4, 3))],
    }
    focus["shop"] = [
        deepcopy(pick_card("妖兽", 3, 2)),
        deepcopy(pick_card("散修", 3, 1)),
        deepcopy(pick_card("佛修", 2, 4)),
        deepcopy(pick_card("系统持有者", 3, 0)),
        deepcopy(br.BEAST_REALM_SPELL_BY_ID["br_spell_009"]),
    ]
    table["enemies"] = br.create_pve_enemies(3, len(players), table)
    return table, focus


def spell_library_text() -> str:
    return "\n".join(["【法术牌库】"] + [br.card_summary_line(card, index, "法术") for index, card in enumerate(br.BEAST_REALM_SPELLS, start=1)])


def generate_runtime_panel_previews(manifest: list[dict[str, Any]]) -> None:
    lobby_table = build_lobby_preview_table()
    leader_player = build_leader_preview_player()
    recruit_table, focus_player = build_recruit_preview_table()
    action_table, action_player = build_recruit_preview_table()
    action_title, action_content = br.private_action(action_table, action_player, "施法 5 1")
    battle_table, _battle_focus = build_recruit_preview_table()
    battle_report = br.resolve_round(battle_table)

    save_runtime_panel(OUT_HELP_PANEL_PATH, "御兽秘境", br.help_text(), manifest, subtitle="玩法帮助")
    save_runtime_panel(OUT_LOBBY_PANEL_PATH, "御兽秘境开局", br.lobby_text(lobby_table) + "\n\n峰主候选已发送到私聊，请发送 选择峰主 1/2/3。", manifest, subtitle="群聊等待房")
    save_runtime_panel(OUT_LEADER_PANEL_PATH, "峰主选择", br.leader_choice_text(leader_player), manifest, subtitle="私聊 · 随机三选一峰主")
    save_runtime_panel(OUT_START_ROUND_PANEL_PATH, "御兽秘境", br.start_round_text(recruit_table), manifest, subtitle="群聊 · 回合开始")
    save_runtime_panel(OUT_STATUS_PANEL_PATH, "御兽秘境状态", br.status_text(recruit_table), manifest, subtitle="群聊 · 当前局势")
    save_runtime_panel(OUT_TASK_PANEL_PATH, "任务堂", br.player_text(focus_player, recruit_table), manifest, subtitle="私聊 · 招募与战局")
    save_runtime_panel(OUT_ACTION_PANEL_PATH, action_title, action_content, manifest, subtitle="私聊 · 操作反馈")
    save_runtime_panel(OUT_RUNTIME_BATTLE_PANEL_PATH, "御兽秘境战报", battle_report, manifest, subtitle="群聊 · 自动结算")
    save_runtime_panel(OUT_FULL_LIBRARY_PANEL_PATH, "御兽秘境图鉴", br.catalog_text(), manifest, subtitle="当前运行态牌库预览")
    save_runtime_panel(OUT_SPELL_LIBRARY_PANEL_PATH, "御兽秘境图鉴", spell_library_text(), manifest, subtitle="法术牌库预览")



def save_contact_sheet(manifest: list[dict[str, Any]]) -> None:
    source_items = list(manifest)
    cols = 3
    thumb_w, thumb_h = 360, 260
    label_h, gap = 34, 18
    rows = (len(source_items) + cols - 1) // cols
    width = gap + cols * thumb_w + (cols - 1) * gap + gap
    height = 72 + rows * (thumb_h + label_h + gap) + gap
    sheet = Image.new("RGB", (width, height), "#101824")
    draw = ImageDraw.Draw(sheet)
    draw.text((gap, 22), "御兽秘境 · 页面预览总览", font=font(28), fill="#fff0c6")
    draw.text((gap, 52), f"共 {len(source_items)} 张预览，运行 tools/render_beast_realm_preview.py 可全部重建", font=font(15), fill="#cdd8e9")
    for index, item in enumerate(source_items):
        row, col = divmod(index, cols)
        x = gap + col * (thumb_w + gap)
        y = 82 + row * (thumb_h + label_h + gap)
        image = Image.open(item["file"]).convert("RGB")
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        draw.rounded_rectangle((x, y, x + thumb_w, y + thumb_h), radius=8, fill="#182233", outline="#8d784d", width=1)
        px = x + (thumb_w - image.width) // 2
        py = y + (thumb_h - image.height) // 2
        sheet.paste(image, (px, py))
        label = str(item.get("name") or Path(item["file"]).stem)
        draw.text((x + 8, y + thumb_h + 8), label[:42], font=font(14), fill="#e8dfcb")
    sheet.save(OUT_CONTACT_SHEET_PATH, quality=94)
    manifest.append({"name": OUT_CONTACT_SHEET_PATH.stem, "file": str(OUT_CONTACT_SHEET_PATH), "width": sheet.width, "height": sheet.height})

def main() -> None:
    manifest: list[dict[str, Any]] = []
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    join_preview = render_join_preview().convert("RGB")
    task_hall_preview = render_task_hall_preview().convert("RGB")
    battle_report_preview = render_battle_report_preview().convert("RGB")
    all_cards = render_all_cards_preview().convert("RGB")

    save_preview_image(OUT_JOIN_PATH, join_preview, manifest)
    save_preview_image(OUT_TASK_HALL_PATH, task_hall_preview, manifest)
    save_preview_image(OUT_BATTLE_REPORT_PATH, battle_report_preview, manifest)
    save_preview_image(OUT_PATH, task_hall_preview, manifest)
    save_preview_image(OUT_ALL_CARDS_PATH, all_cards, manifest, quality=92)
    generate_runtime_panel_previews(manifest)
    save_contact_sheet(manifest)

    OUT_PREVIEW_MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT_PREVIEW_MANIFEST_PATH)
    for item in manifest:
        print(item["file"])


if __name__ == "__main__":
    main()
