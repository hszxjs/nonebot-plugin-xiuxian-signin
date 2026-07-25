from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from . import beast_realm as br
from .cards import load_font, png_bytes, text_size, wrap_panel_text

ROOT = Path(__file__).resolve().parent
BG_PATH = ROOT / "assets" / "panel_backgrounds" / "beast_realm_background.png"
REPORT_BG_PATH = ROOT / "assets" / "panel_backgrounds" / "beast_realm_background_vertical.png"
PORTRAIT_DIR = ROOT / "assets" / "character_portraits" / "portraits"
SPELL_ICON_DIR = ROOT / "assets" / "beast_realm_spell_icons"
CARD_ART_RATIO = 0.70
REPORT_BG_IMAGE_H = 1080
REPORT_BG_FADE_H = 160
REPORT_BG_COLOR = (11, 17, 29)

_BEAST_CARD_BY_NAME: dict[str, dict[str, Any]] | None = None


def _card_lookup() -> dict[str, dict[str, Any]]:
    global _BEAST_CARD_BY_NAME
    if _BEAST_CARD_BY_NAME is None:
        lookup: dict[str, dict[str, Any]] = {}
        for card in list(br.BEAST_REALM_CARDS) + list(br.BEAST_REALM_SPELLS):
            name = str(card.get("name") or "")
            if name:
                lookup.setdefault(name, dict(card))
        _BEAST_CARD_BY_NAME = lookup
    return _BEAST_CARD_BY_NAME


def _cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = image.size
    scale = max(target_w / max(1, src_w), target_h / max(1, src_h))
    resized = image.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _cover_resize_focus(image: Image.Image, size: tuple[int, int], focus_x: float = 0.5, focus_y: float = 0.36) -> Image.Image:
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


def _portrait_on_focused_background(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    canvas = _cover_resize_focus(image.convert("RGBA"), size)
    shade = Image.new("RGBA", size, (8, 10, 16, 28))
    canvas = Image.alpha_composite(canvas, shade)
    vignette = Image.new("RGBA", size, (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    vdraw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=8, outline=(255, 239, 190, 52), width=8)
    return Image.alpha_composite(canvas, vignette.filter(ImageFilter.GaussianBlur(2)))


def _contain_on_blurred_background(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    base = _cover_resize(image.convert("RGBA"), size).filter(ImageFilter.GaussianBlur(5))
    shade = Image.new("RGBA", size, (8, 10, 16, 58))
    canvas = Image.alpha_composite(base, shade)
    foreground = image.convert("RGBA")
    foreground.thumbnail((max(1, size[0] - 8), max(1, size[1] - 8)), Image.Resampling.LANCZOS)
    x = (size[0] - foreground.width) // 2
    y = (size[1] - foreground.height) // 2
    canvas.alpha_composite(foreground, (x, y))
    vignette = Image.new("RGBA", size, (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    vdraw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=8, outline=(255, 239, 190, 52), width=8)
    return Image.alpha_composite(canvas, vignette.filter(ImageFilter.GaussianBlur(2)))


def _make_bg(size: tuple[int, int], blur: float = 1.1, shade: int = 128) -> Image.Image:
    if BG_PATH.exists():
        bg = _cover_resize(Image.open(BG_PATH).convert("RGB"), size)
        bg = ImageEnhance.Color(bg).enhance(0.92)
        bg = ImageEnhance.Brightness(bg).enhance(0.76)
        bg = bg.filter(ImageFilter.GaussianBlur(blur))
    else:
        bg = Image.new("RGB", size, "#18233a")
    overlay = Image.new("RGBA", size, (8, 13, 24, shade))
    return Image.alpha_composite(bg.convert("RGBA"), overlay)



def _make_report_bg(size: tuple[int, int], blur: float = 1.1, shade: int = 128) -> Image.Image:
    width, height = size
    if REPORT_BG_PATH.exists():
        bg = _cover_resize(Image.open(REPORT_BG_PATH).convert("RGB"), size)
        bg = ImageEnhance.Color(bg).enhance(0.94)
        bg = ImageEnhance.Brightness(bg).enhance(0.78)
        overlay = Image.new("RGBA", size, (8, 13, 24, shade))
        return Image.alpha_composite(bg.convert("RGBA"), overlay)
    if height <= REPORT_BG_IMAGE_H:
        return _make_bg(size, blur=blur, shade=shade)
    canvas = Image.new("RGBA", size, (*REPORT_BG_COLOR, 255))
    image_h = min(REPORT_BG_IMAGE_H, height)
    canvas.alpha_composite(_make_bg((width, image_h), blur=blur, shade=shade), (0, 0))
    fade_h = min(REPORT_BG_FADE_H, image_h)
    if fade_h > 0:
        fade = Image.new("RGBA", (width, fade_h), (0, 0, 0, 0))
        fade_draw = ImageDraw.Draw(fade)
        for row in range(fade_h):
            alpha = int(255 * (row + 1) / fade_h)
            fade_draw.line((0, row, width, row), fill=(*REPORT_BG_COLOR, alpha))
        canvas.alpha_composite(fade, (0, image_h - fade_h))
    return canvas

def _round(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: Any, outline: Any = None, width: int = 1, radius: int = 8) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_size: int, min_size: int = 10, bold: bool = False):
    for size in range(max_size, min_size - 1, -1):
        font = load_font(size, bold=bold)
        if text_size(draw, text, font)[0] <= max_width:
            return font
    return load_font(min_size, bold=bold)


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    max_size: int,
    fill: str,
    min_size: int = 9,
    bold: bool = False,
) -> None:
    x1, y1, x2, y2 = box
    max_width = max(1, x2 - x1)
    max_height = max(1, y2 - y1)
    for size in range(max_size, min_size - 1, -1):
        font = load_font(size, bold=bold)
        lines: list[str] = []
        for part in str(text or "").splitlines() or [""]:
            lines.extend(wrap_panel_text(draw, part, font, max_width))
        line_h = text_size(draw, "国", font)[1] + max(2, size // 5)
        if line_h * len(lines) <= max_height:
            for idx, line in enumerate(lines):
                draw.text((x1, y1 + idx * line_h), line, font=font, fill=fill)
            return
    font = load_font(min_size, bold=bold)
    lines = []
    for part in str(text or "").splitlines() or [""]:
        lines.extend(wrap_panel_text(draw, part, font, max_width))
    line_h = text_size(draw, "国", font)[1] + 2
    max_lines = max(1, max_height // max(1, line_h))
    for idx, line in enumerate(lines[:max_lines]):
        if idx == max_lines - 1 and len(lines) > max_lines:
            suffix = "..."
            while line and text_size(draw, line + suffix, font)[0] > max_width:
                line = line[:-1]
            line = (line + suffix) if line else suffix
        draw.text((x1, y1 + idx * line_h), line, font=font, fill=fill)


def _draw_chip(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, size: int = 18, fill: Any = (50, 65, 78, 204)) -> None:
    _round(draw, box, fill, outline=(218, 194, 133, 110), width=1, radius=8)
    font = _fit_text(draw, text, box[2] - box[0] - 18, size, 10, bold=True)
    tw, th = text_size(draw, text, font)
    x1, y1, x2, y2 = box
    draw.text((x1 + (x2 - x1 - tw) // 2, y1 + (y2 - y1 - th) // 2 - 1), text, font=font, fill="#f6e5bd")


def _draw_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, transparent: bool = False) -> None:
    fill = None if transparent else (18, 24, 36, 204)
    outline = (232, 204, 132, 170) if transparent else (217, 194, 132, 130)
    _round(draw, box, fill, outline=outline, width=2, radius=8)
    x1, y1, x2, _ = box
    draw.text((x1 + 22, y1 + 16), title, font=load_font(24, bold=True), fill="#f6df9b")
    line_fill = (232, 204, 132, 115) if transparent else (218, 194, 133, 100)
    draw.line((x1 + 18, y1 + 56, x2 - 18, y1 + 56), fill=line_fill, width=1)


def _draw_header(draw: ImageDraw.ImageDraw, title: str, subtitle: str, width: int, chip: str) -> None:
    draw.text((54, 38), "御兽秘境", font=load_font(50, bold=True), fill="#fff0c6")
    sub = subtitle or title
    draw.text((58, 104), sub, font=load_font(22, bold=True), fill="#cdd8e9")
    _draw_chip(draw, (width - 354, 48, width - 58, 98), chip, size=18)


def _content_lines(content: str | list[str]) -> list[str]:
    if isinstance(content, str):
        raw = content.splitlines()
    else:
        raw = [str(item) for item in content]
    return [line.rstrip() for line in raw]


def _portrait_for(name: str) -> Image.Image | None:
    card = _card_lookup().get(name)
    portrait_id = str((card or {}).get("portrait_id") or "")
    if not portrait_id:
        return None
    path = PORTRAIT_DIR / f"{portrait_id}.png"
    if not path.exists():
        return None
    try:
        return Image.open(path).convert("RGBA")
    except OSError:
        return None


def _spell_icon_for(card: dict[str, Any]) -> Image.Image | None:
    icon_id = str(card.get("icon_id") or card.get("id") or "").strip().replace("\\", "/").split("/")[-1]
    if not icon_id or icon_id in {".", ".."}:
        return None
    if not icon_id.endswith(".png"):
        icon_id = f"{icon_id}.png"
    path = SPELL_ICON_DIR / icon_id
    if not path.exists():
        return None
    try:
        return Image.open(path).convert("RGBA")
    except OSError:
        return None


def _parse_card_line(line: str) -> dict[str, Any] | None:
    match = re.match(r"^(\d+)\.\s*【([^】]+)】([^｜]+)｜(.+)$", line.strip())
    if not match:
        return None
    index, label, name, rest = match.groups()
    parts = rest.split("｜")
    card: dict[str, Any] = {"index": int(index), "label": label, "name": name.strip(), "raw": line.strip()}
    known = _card_lookup().get(card["name"])
    if known:
        card.update(known)
    if label == "法术" or str((known or {}).get("kind")) == "spell":
        card["kind"] = "spell"
        card["realm"] = parts[0] if len(parts) > 0 else str(card.get("realm", ""))
        card["category"] = parts[1] if len(parts) > 1 else str(card.get("category", "法术"))
        cost = ""
        effect_start = 2
        if len(parts) > 2 and "灵石" in parts[2]:
            cost = parts[2]
            effect_start = 3
        card["cost_text"] = cost
        card["effect"] = "｜".join(parts[effect_start:]) or str(card.get("effect", ""))
        return card
    card["kind"] = "beast"
    card["realm"] = parts[0] if len(parts) > 0 else str(card.get("realm", ""))
    if len(parts) > 1:
        stat_match = re.search(r"(\d+)\s*/\s*(\d+)", parts[1])
        if stat_match:
            card["attack"] = int(stat_match.group(1))
            card["defense"] = int(stat_match.group(2))
    if len(parts) > 2 and "·" in parts[2]:
        faction, element = parts[2].split("·", 1)
        card["faction"] = faction
        card["element"] = element
    effect_start = 3
    if len(parts) > 3 and "灵石" in parts[3]:
        card["cost_text"] = parts[3]
        effect_start = 4
    card["effect"] = "｜".join(parts[effect_start:]) or str(card.get("effect", ""))
    return card


def _parse_unit_line(line: str) -> dict[str, Any] | None:
    match = re.match(r"^(\d+)\.\s*([^·\s]+)·(.+?)\s+(\d+)\s*/\s*(\d+)｜(.+)$", line.strip())
    if not match:
        return None
    index, realm, name, attack, defense, rest = match.groups()
    card: dict[str, Any] = {"index": int(index), "label": "战局", "kind": "beast", "realm": realm, "name": name, "attack": int(attack), "defense": int(defense), "effect": rest, "raw": line.strip()}
    known = _card_lookup().get(name)
    if known:
        card.update({key: value for key, value in known.items() if key not in {"attack", "defense"}})
    if "｜" in rest:
        first, extra = rest.split("｜", 1)
        card["effect"] = extra
    else:
        first = rest
    if "·" in first:
        faction, element = first.split("·", 1)
        card["faction"] = faction
        card["element"] = element
    return card


def _draw_runtime_card(canvas: Image.Image, card: dict[str, Any], box: tuple[int, int, int, int], selected: bool = False) -> None:
    draw = ImageDraw.Draw(canvas)
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    border = "#e8c978" if selected else "#9f8654"
    fill = (30, 34, 45, 232) if card.get("kind") != "spell" else (36, 30, 50, 232)
    _round(draw, box, fill, outline=border, width=3 if selected else 2, radius=8)

    pad = max(7, int(w * 0.045))
    idx = str(card.get("index", ""))
    frame_outline = (77, 162, 218, 220)
    frame_fill = (13, 31, 45, 210)
    portrait_gap = max(6, int(h * 0.025))
    art_bottom = y1 + int(h * CARD_ART_RATIO)
    portrait_box = (x1 + pad, y1 + pad, x2 - pad, art_bottom)
    effect_box = (x1 + pad, portrait_box[3] + portrait_gap, x2 - pad, y2 - pad)
    info_h = min(58, max(48, int((portrait_box[3] - portrait_box[1]) * 0.3)))
    info_box = (portrait_box[0] + 2, portrait_box[3] - info_h, portrait_box[2] - 2, portrait_box[3] - 2)

    if card.get("kind") == "spell":
        _round(draw, portrait_box, (34, 29, 52, 226), outline=frame_outline, width=2, radius=7)
        icon = _spell_icon_for(card)
        if icon is not None:
            inner = (portrait_box[0] + 4, portrait_box[1] + 4, portrait_box[2] - 4, portrait_box[3] - 4)
            icon = _contain_on_blurred_background(icon, (inner[2] - inner[0], inner[3] - inner[1]))
            mask = Image.new("L", icon.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, icon.width, icon.height), radius=6, fill=255)
            canvas.paste(icon, inner[:2], mask)
        else:
            glyph = {"丹药": "丹", "符箓": "符", "神通": "通", "阵法": "阵"}.get(str(card.get("category") or ""), "术")
            glyph_area_h = max(1, info_box[1] - portrait_box[1])
            gf = load_font(max(46, min(72, glyph_area_h - 16)), bold=True)
            gw, gh = text_size(draw, glyph, gf)
            draw.text(
                (portrait_box[0] + (portrait_box[2] - portrait_box[0] - gw) // 2, portrait_box[1] + (glyph_area_h - gh) // 2 - 2),
                glyph,
                font=gf,
                fill="#f1d58c",
            )
    else:
        _round(draw, portrait_box, frame_fill, outline=frame_outline, width=2, radius=7)
        portrait = _portrait_for(str(card.get("name") or ""))
        if portrait is not None:
            inner = (portrait_box[0] + 4, portrait_box[1] + 4, portrait_box[2] - 4, portrait_box[3] - 4)
            portrait = _portrait_on_focused_background(portrait, (inner[2] - inner[0], inner[3] - inner[1]))
            mask = Image.new("L", portrait.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, portrait.width, portrait.height), radius=6, fill=255)
            canvas.paste(portrait, inner[:2], mask)
        atk = str(card.get("attack", "?"))
        defense = str(card.get("defense", "?"))
        stat_font = load_font(13, bold=True)
        stat_y = max(portrait_box[1] + 42, info_box[1] - 25)
        attack_text = f"攻 {atk}"
        defense_text = f"御 {defense}"
        defense_w, _ = text_size(draw, defense_text, stat_font)
        draw.text((portrait_box[0] + 9, stat_y + 1), attack_text, font=stat_font, fill=(0, 0, 0, 185))
        draw.text((portrait_box[2] - 7 - defense_w, stat_y + 1), defense_text, font=stat_font, fill=(0, 0, 0, 185))
        draw.text((portrait_box[0] + 8, stat_y), attack_text, font=stat_font, fill="#ffd7cf")
        draw.text((portrait_box[2] - 8 - defense_w, stat_y), defense_text, font=stat_font, fill="#cfecff")

    meta = str(card.get("realm") or "")
    if card.get("kind") == "spell":
        meta = f"{meta}  {card.get('category', '')}".strip()
    else:
        meta = f"{meta}  {card.get('faction', '')}·{card.get('element', '')}".strip(" ·")
    if card.get("cost_text"):
        meta = f"{meta}  {card.get('cost_text')}".strip()
    draw.rounded_rectangle(info_box, radius=6, fill=(8, 15, 25, 190))
    _draw_text_block(draw, str(card.get("name") or "无名"), (info_box[0] + 7, info_box[1] + 5, info_box[2] - 7, info_box[1] + 30), 18, "#fff1d2", 10, bold=True)
    _draw_text_block(draw, meta, (info_box[0] + 7, info_box[1] + 31, info_box[2] - 7, info_box[3] - 4), 12, "#c8d7e8", 8)
    _round(draw, portrait_box, None, outline=frame_outline, width=2, radius=7)
    _draw_chip(draw, (x1 + pad, y1 + pad, x1 + pad + 38, y1 + pad + 32), idx, size=14, fill=(70, 82, 96, 220))

    _round(draw, effect_box, (10, 18, 28, 210), outline=frame_outline, width=2, radius=7)
    _draw_text_block(
        draw,
        str(card.get("effect") or card.get("raw") or ""),
        (effect_box[0] + 6, effect_box[1] + 5, effect_box[2] - 6, effect_box[3] - 5),
        13,
        "#d8d1bd",
        8,
    )

def _leader_options(lines: list[str]) -> list[dict[str, Any]]:
    leaders: list[dict[str, Any]] = []
    idx = 0
    while idx < len(lines):
        match = re.match(r"^(\d+)\.\s*(.+?)(?:（当前）)?｜生命(\d+)", lines[idx].strip())
        if not match:
            idx += 1
            continue
        number, name, health = match.groups()
        skill = ""
        if idx + 1 < len(lines):
            skill = re.sub(r"^\s*技能：", "", lines[idx + 1].strip())
        leaders.append({"index": int(number), "name": name, "health": int(health), "skill": skill, "selected": "当前" in lines[idx]})
        idx += 2
    return leaders


def _draw_leader_card(canvas: Image.Image, leader: dict[str, Any], box: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(canvas)
    selected = bool(leader.get("selected"))
    border = "#f2d17a" if selected else "#8fa6b8"
    fill = (38, 42, 54, 232) if selected else (27, 34, 47, 222)
    _round(draw, box, fill, outline=border, width=3 if selected else 1, radius=8)
    x1, y1, x2, y2 = box
    draw.text((x1 + 18, y1 + 15), str(leader.get("name", "峰主")), font=load_font(23, bold=True), fill="#fff0c6")
    _draw_chip(draw, (x2 - 138, y1 + 13, x2 - 18, y1 + 45), f"生命 {leader.get('health', 0)}", size=15, fill=(105, 74, 56, 210))
    draw.line((x1 + 16, y1 + 56, x2 - 16, y1 + 56), fill=(224, 198, 132, 96), width=1)
    _draw_text_block(draw, str(leader.get("skill", "")), (x1 + 18, y1 + 68, x2 - 18, y2 - 56), 17, "#dfe6ee", 10, bold=True)
    _draw_chip(draw, (x1 + 18, y2 - 44, x1 + 156, y2 - 14), f"选择峰主 {leader.get('index', 1)}", size=14, fill=(58, 75, 90, 210))


def _render_leader_choice(title: str, lines: list[str], subtitle: str, width: int, footer: str) -> bytes:
    width = max(1180, width)
    height = 780
    canvas = _make_bg((width, height))
    draw = ImageDraw.Draw(canvas)
    _draw_header(draw, "峰主选择", subtitle or "私聊 · 随机三选一峰主", width, "开局前选择")
    leaders = _leader_options(lines)
    info_lines = [line for line in lines[1:] if line.strip() and not re.match(r"^\d+\.\s*", line.strip()) and not line.strip().startswith("技能：")]
    _draw_panel(draw, (54, 150, width - 54, 300), "选择说明")
    _draw_text_block(draw, "\n".join(info_lines[:4]), (84, 220, width - 84, 284), 24, "#e8dfcb", 13, bold=True)
    card_gap = 18
    card_w = (width - 108 - card_gap * 2) // 3
    y = 330
    for index, leader in enumerate(leaders[:3]):
        x = 54 + index * (card_w + card_gap)
        _draw_leader_card(canvas, leader, (x, y, x + card_w, y + 310))
    bottom_text = footer or "所有修士选定峰主后，群聊由峰主发送“开始御兽秘境”。"
    _round(draw, (54, height - 86, width - 54, height - 28), (14, 20, 31, 188), outline=(215, 187, 117, 100), width=1, radius=8)
    _draw_text_block(draw, bottom_text, (82, height - 70, width - 82, height - 38), 20, "#e8dcc0", 10, bold=True)
    return png_bytes(canvas)


def _split_sections(lines: list[str]) -> tuple[list[str], list[tuple[str, list[str]]], list[str]]:
    header: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    commands: list[str] = []
    current_title = ""
    current_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("指令："):
            commands.append(stripped)
            continue
        sec = re.match(r"^【(.+)】", stripped)
        if sec:
            if current_title:
                sections.append((current_title, current_lines))
            elif header:
                pass
            current_title = sec.group(1)
            current_lines = []
            rest = stripped[sec.end():].strip()
            if rest:
                current_lines.append(rest)
            continue
        if current_title:
            current_lines.append(stripped)
        else:
            header.append(stripped)
    if current_title:
        sections.append((current_title, current_lines))
    return header, sections, commands


def _section_items(section_lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    cards: list[dict[str, Any]] = []
    plain: list[str] = []
    for line in section_lines:
        parsed = _parse_card_line(line) or _parse_unit_line(line)
        if parsed:
            cards.append(parsed)
        else:
            plain.append(line)
    return cards, plain


def _card_section_height(
    width: int,
    card_count: int,
    plain_count: int,
    max_cols: int = 5,
    compact_cards: bool = False,
) -> int:
    left, right = 54, width - 54
    if card_count:
        cols = min(max_cols, max(1, card_count))
        gap = 14
        card_w = (right - left - 44 - gap * (cols - 1)) // cols
        card_h = 230 if compact_cards else (250 if card_w < 190 else 270)
        rows = (card_count + cols - 1) // cols
        return 82 + rows * card_h + max(0, rows - 1) * 16 + 24
    return max(110, 76 + plain_count * 34)


def _render_card_section(
    canvas: Image.Image,
    y: int,
    title: str,
    cards: list[dict[str, Any]],
    plain: list[str],
    width: int,
    max_cols: int = 5,
    compact_cards: bool = False,
    transparent: bool = False,
) -> int:
    draw = ImageDraw.Draw(canvas)
    left, right = 54, width - 54
    if cards:
        cols = min(max_cols, max(1, len(cards)))
        gap = 14
        card_w = (right - left - 44 - gap * (cols - 1)) // cols
        card_h = 230 if compact_cards else (250 if card_w < 190 else 270)
        rows = (len(cards) + cols - 1) // cols
        panel_h = 82 + rows * card_h + max(0, rows - 1) * 16 + 24
        _draw_panel(draw, (left, y, right, y + panel_h), title, transparent=transparent)
        for idx, card in enumerate(cards):
            row = idx // cols
            col = idx % cols
            x = left + 22 + col * (card_w + gap)
            cy = y + 72 + row * (card_h + 16)
            _draw_runtime_card(canvas, card, (x, cy, x + card_w, cy + card_h), selected=idx == 0 and title in {"任务堂卡牌", "三连奖励"})
        return y + panel_h + 22
    panel_h = max(110, 76 + len(plain) * 34)
    _draw_panel(draw, (left, y, right, y + panel_h), title, transparent=transparent)
    _draw_text_block(draw, "\n".join(plain) if plain else "暂无。", (left + 26, y + 72, right - 26, y + panel_h - 18), 21, "#e8dfcb", 10, bold=True)
    return y + panel_h + 20


def _render_task_hall(title: str, lines: list[str], subtitle: str, width: int, footer: str) -> bytes:
    width = max(1180, width)
    header, sections, commands = _split_sections(lines)
    status_title = "玩家状态"
    if not header and sections and "任务堂" in sections[0][0]:
        status_title = sections[0][0]
        header = list(sections[0][1])
        sections = sections[1:]
    section_payloads = []
    total_h = 172 + 160
    for section_title, section_lines in sections:
        cards, plain = _section_items(section_lines)
        board_like = "战局" in section_title
        max_cols = 7 if board_like else 5
        compact_cards = board_like and len(cards) > 5
        section_payloads.append((section_title, cards, plain, max_cols, compact_cards))
        total_h += _card_section_height(width, len(cards), len(plain), max_cols=max_cols, compact_cards=compact_cards) + 22
    total_h += 92 if commands or footer else 38
    height = max(860, min(2400, total_h))
    canvas = _make_bg((width, height))
    draw = ImageDraw.Draw(canvas)
    _draw_header(draw, title or "任务堂", subtitle or "私聊准备 · 任务堂购买随从", width, "任务堂招募")
    _draw_panel(draw, (54, 150, width - 54, 306), status_title)
    _draw_text_block(draw, "\n".join(header[:4]), (82, 218, width - 82, 286), 22, "#e8dfcb", 11, bold=True)
    y = 330
    for section_title, cards, plain, max_cols, compact_cards in section_payloads:
        y = _render_card_section(canvas, y, section_title, cards, plain, width, max_cols=max_cols, compact_cards=compact_cards)
        if y > height - 140:
            break
    bottom = footer or "\n".join(commands[:1])
    if bottom:
        _round(draw, (54, height - 84, width - 54, height - 28), (14, 20, 31, 188), outline=(215, 187, 117, 100), width=1, radius=8)
        _draw_text_block(draw, bottom, (82, height - 69, width - 82, height - 38), 18, "#e8dcc0", 10, bold=True)
    return png_bytes(canvas)


def _render_report_or_text(title: str, lines: list[str], subtitle: str, width: int, footer: str) -> bytes:
    width = max(1180, width)
    header, sections, commands = _split_sections(lines)
    if not sections and header:
        sections = [(title or "御兽秘境", header)]
        header = []
    is_battle_report = "战报" in title or any("战报" in section_title for section_title, _lines in sections)
    section_payloads: list[tuple[str, list[dict[str, Any]], list[str]]] = []
    total_h = 150
    if header:
        total_h += max(120, 76 + len(header) * 34) + 24
    for section_title, section_lines in sections:
        cards, plain = _section_items(section_lines)
        section_payloads.append((section_title, cards, plain))
        total_h += _card_section_height(width, len(cards), len(plain)) + 22
    bottom = footer or "\n".join(commands[:1])
    total_h += 92 if bottom else 38
    height = max(720, total_h if is_battle_report else min(1500, total_h))
    canvas = _make_report_bg((width, height)) if is_battle_report else _make_bg((width, height))
    draw = ImageDraw.Draw(canvas)
    chip = "战报" if is_battle_report else "运行面板"
    _draw_header(draw, title or "御兽秘境", subtitle or "群聊与私聊同步推进", width, chip)
    y = 150
    if header:
        panel_h = max(120, 76 + len(header) * 34)
        _draw_panel(draw, (54, y, width - 54, y + panel_h), "摘要", transparent=is_battle_report)
        _draw_text_block(draw, "\n".join(header), (82, y + 68, width - 82, y + panel_h - 18), 21, "#e8dfcb", 10, bold=True)
        y += panel_h + 24
    for section_title, cards, plain in section_payloads:
        y = _render_card_section(canvas, y, section_title, cards, plain, width, transparent=is_battle_report)
        if not is_battle_report and y > height - 120:
            break
    if bottom:
        _round(draw, (54, height - 84, width - 54, height - 28), (14, 20, 31, 188), outline=(215, 187, 117, 100), width=1, radius=8)
        _draw_text_block(draw, bottom, (82, height - 69, width - 82, height - 38), 18, "#e8dcc0", 10, bold=True)
    return png_bytes(canvas)

def _render_catalog(title: str, lines: list[str], subtitle: str, width: int, footer: str) -> bytes:
    width = max(1180, width)
    header, sections, commands = _split_sections(lines)
    if not sections and header:
        sections = [(title or "御兽秘境图鉴", header)]
        header = []
    section_payloads: list[tuple[str, list[dict[str, Any]], list[str]]] = []
    total_h = 150
    if header:
        total_h += 144
    for section_title, section_lines in sections:
        cards, plain = _section_items(section_lines)
        section_payloads.append((section_title, cards, plain))
        total_h += _card_section_height(width, len(cards), len(plain), max_cols=6, compact_cards=True) + 22
    total_h += 92 if commands or footer else 38
    height = max(900, total_h)
    canvas = _make_bg((width, height), blur=1.4, shade=138)
    draw = ImageDraw.Draw(canvas)
    _draw_header(draw, title or "御兽秘境图鉴", subtitle or "随从与法术完整牌库", width, "全牌库")
    y = 150
    if header:
        _draw_panel(draw, (54, y, width - 54, y + 120), "摘要")
        _draw_text_block(draw, "\n".join(header[:3]), (82, y + 68, width - 82, y + 105), 21, "#e8dfcb", 10, bold=True)
        y += 144
    for section_title, cards, plain in section_payloads:
        y = _render_card_section(canvas, y, section_title, cards, plain, width, max_cols=6, compact_cards=True)
    bottom = footer or "\n".join(commands[:1])
    if bottom:
        _round(draw, (54, height - 84, width - 54, height - 28), (14, 20, 31, 188), outline=(215, 187, 117, 100), width=1, radius=8)
        _draw_text_block(draw, bottom, (82, height - 69, width - 82, height - 38), 18, "#e8dcc0", 10, bold=True)
    return png_bytes(canvas)


def render_beast_realm_panel(
    title: str,
    content: str | list[str],
    subtitle: str = "",
    width: int = 1180,
    footer: str = "",
) -> bytes:
    lines = _content_lines(content)
    joined = "\n".join(lines)
    if "峰主选择" in title or "【峰主选择】" in joined:
        return _render_leader_choice(title, lines, subtitle, width, footer)
    if "图鉴" in title or "【御兽秘境全牌库】" in joined or "【法术牌库】" in joined:
        return _render_catalog(title, lines, subtitle, width, footer)
    if "战报" in title or "【御兽秘境战报" in joined:
        return _render_report_or_text(title, lines, subtitle, width, footer)
    if "任务堂" in title or "【任务堂卡牌】" in joined or "【当前战局】" in joined:
        return _render_task_hall(title, lines, subtitle, width, footer)
    return _render_report_or_text(title, lines, subtitle, width, footer)
