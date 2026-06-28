from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from .domain import (
    ATTRIBUTE_COLORS,
    Root,
    SigninResult,
    UserRecord,
    array_multiplier,
    battle_power,
    battle_summary,
    breakthrough_required_text,
    acquired_root_attribute_text,
    acquired_root_summary,
    normalize_acquired_roots,
    combat_max_mana,
    hehuan_remaining_text,
    is_breakthrough_bottleneck,
    reward_display_name,
    spirit_stone_text,
    tianji_status_text,
    reward_signature,
    artifact_slots,
    REALMS,
)

Color = tuple[int, int, int]
BUNDLED_FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "NotoSansSC-VF.ttf"
SIGNIN_UI_SPRITE_DIR = Path(__file__).parent / "assets" / "ui_sprite" / "signin" / "output" / "sprites"
SIGNIN_PANEL_BG = SIGNIN_UI_SPRITE_DIR / "signin_background_base.png"
SIGNIN_PORTRAIT_FRAME = SIGNIN_UI_SPRITE_DIR / "portrait_frame_overlay.png"
SIGNIN_EXPERIENCE_TROUGH = SIGNIN_UI_SPRITE_DIR / "experience_trough.png"
SIGNIN_EXPERIENCE_LIQUID = SIGNIN_UI_SPRITE_DIR / "experience_trough_1.png"
ADVENTURE_PANEL_BG = Path(__file__).parent / "assets" / "panel_backgrounds" / "adventure_background.png"
ITEM_ICON_ROOT = Path(__file__).parent / "assets" / "item_icons"
ITEM_ICON_RECORDS = ITEM_ICON_ROOT / "item_icon_records.json"
SPIRIT_ROOT_ICON_DIR = Path(__file__).parent / "assets" / "spirit_root_icons"
REALM_QUALITY_ICON_DIR = Path(__file__).parent / "assets" / "realm_quality_icons"
SPIRIT_ROOT_ICON_FILES = {
    "金": "jin.png",
    "木": "mu.png",
    "水": "shui.png",
    "火": "huo.png",
    "土": "tu.png",
    "雷": "lei.png",
    "冰": "bing.png",
    "风": "feng.png",
    "暗": "an.png",
    "光": "guang.png",
    "剑": "jian.png",
    "药": "yao.png",
    "玄阴": "xuanyin.png",
    "玄阳": "xuanyang.png",
    "空": "kong.png",
}
_ITEM_ICON_RECORD_CACHE: Optional[list[dict[str, Any]]] = None
_SPIRIT_ROOT_ICON_CACHE: dict[str, Image.Image] = {}
_REALM_QUALITY_ICON_CACHE: dict[str, Image.Image] = {}
_REALM_QUALITY_ICON_MAP: Optional[dict[str, str]] = None

TIER_COLORS = {
    "帝兵": "#8b1e1e",
    "仙阶": "#dc2626",
    "天阶": "#f97316",
    "地阶": "#d6a21e",
    "玄阶": "#9a6b35",
    "黄阶": "#b9894d",
    "凡阶": "#8f8a83",
    "凡品": "#8f8a83",
}
FONT_CANDIDATES = [
    BUNDLED_FONT_PATH,
    Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/Deng.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansSC-Regular.ttf"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
    Path("/usr/share/fonts/truetype/arphic/ukai.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
]

BOLD_FONT_CANDIDATES = [
    BUNDLED_FONT_PATH,
    Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/Dengb.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansSC-Bold.ttf"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
]



_configured_font_path: Optional[Path] = None
_configured_bold_font_path: Optional[Path] = None


def set_font_paths(font_path: Optional[str], bold_font_path: Optional[str]) -> None:
    global _configured_font_path, _configured_bold_font_path
    _configured_font_path = Path(font_path) if font_path else None
    _configured_bold_font_path = Path(bold_font_path) if bold_font_path else None


def font_candidates(bold: bool) -> list[Path]:
    configured = _configured_bold_font_path if bold else _configured_font_path
    configured_regular = _configured_font_path if bold else None
    candidates = BOLD_FONT_CANDIDATES if bold else FONT_CANDIDATES
    preferred = [path for path in (configured, configured_regular) if path]
    return preferred + candidates


def hex_to_rgb(value: str) -> Color:
    value = value.strip().lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def mix(left: Color, right: Color, ratio: float) -> Color:
    return tuple(int(left[i] * (1 - ratio) + right[i] * ratio) for i in range(3))


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    for path in font_candidates(bold):
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def draw_weighted_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: Any,
    weight: int = 1,
    stroke_width: int = 0,
    stroke_fill: Any = None,
) -> None:
    offsets = [(0, 0)]
    if weight >= 2:
        offsets.append((1, 0))
    if weight >= 3:
        offsets.extend([(0, 1), (1, 1)])
    if weight >= 4:
        offsets.extend([(-1, 0), (0, -1)])
    kwargs: dict[str, Any] = {}
    if stroke_width > 0:
        kwargs["stroke_width"] = stroke_width
        kwargs["stroke_fill"] = stroke_fill if stroke_fill is not None else fill
    for dx, dy in offsets:
        draw.text((xy[0] + dx, xy[1] + dy), text, font=font, fill=fill, **kwargs)


def fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    size: int,
    bold: bool = False,
    min_size: int = 18,
) -> ImageFont.ImageFont:
    for font_size in range(size, min_size - 1, -2):
        font = load_font(font_size, bold=bold)
        if text_size(draw, text, font)[0] <= max_width:
            return font
    return load_font(min_size, bold=bold)


def rounded_layer(
    size: tuple[int, int],
    radius: int,
    fill: tuple[int, int, int, int],
) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=fill)
    return layer


def draw_card(image: Image.Image, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    size = (x2 - x1, y2 - y1)
    shadow = rounded_layer(size, 28, (18, 22, 32, 72)).filter(ImageFilter.GaussianBlur(14))
    image.alpha_composite(shadow, (x1, y1 + 8))
    image.alpha_composite(rounded_layer(size, 28, (255, 255, 255, 220)), (x1, y1))


def make_background(width: int, height: int, accent: str) -> Image.Image:
    accent_rgb = hex_to_rgb(accent)
    top = mix((26, 35, 51), accent_rgb, 0.22)
    mid = (246, 242, 231)
    bottom = mix((35, 46, 66), accent_rgb, 0.14)
    image = Image.new("RGBA", (width, height), (*top, 255))
    pixels = image.load()
    for y in range(height):
        pos = y / max(1, height - 1)
        color = mix(top, mid, pos / 0.58) if pos < 0.58 else mix(mid, bottom, (pos - 0.58) / 0.42)
        for x in range(width):
            pixels[x, y] = (*color, 255)
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse((-170, -130, 430, 430), fill=(*accent_rgb, 80))
    draw.ellipse((width - 360, height - 430, width + 220, height + 160), fill=(255, 255, 255, 56))
    return Image.alpha_composite(image, layer)


def make_xiuxian_background(width: int, height: int, accent: str) -> Image.Image:
    accent_rgb = hex_to_rgb(accent)
    night_top = mix((15, 27, 36), accent_rgb, 0.18)
    mist_mid = mix((225, 232, 222), accent_rgb, 0.12)
    lake_bottom = mix((20, 38, 45), accent_rgb, 0.28)
    image = Image.new("RGBA", (width, height), (*night_top, 255))
    pixels = image.load()
    for y in range(height):
        pos = y / max(1, height - 1)
        if pos < 0.44:
            color = mix(night_top, mist_mid, pos / 0.44)
        else:
            color = mix(mist_mid, lake_bottom, (pos - 0.44) / 0.56)
        for x in range(width):
            pixels[x, y] = (*color, 255)

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    moon_size = max(180, width // 7)
    draw.ellipse(
        (width - moon_size - 110, 86, width - 110, 86 + moon_size),
        fill=(246, 238, 198, 120),
    )
    draw.ellipse(
        (width - moon_size - 65, 72, width - 65, 72 + moon_size),
        fill=(*night_top, 82),
    )

    for offset, alpha, tone in [
        (0, 185, (33, 65, 58)),
        (118, 150, (26, 53, 49)),
        (246, 116, (19, 43, 44)),
    ]:
        base_y = height - 350 + offset // 5
        points = [
            (-80, height),
            (0, base_y + 100),
            (width * 0.12, base_y + 38),
            (width * 0.25, base_y + 116),
            (width * 0.38, base_y + 24),
            (width * 0.55, base_y + 130),
            (width * 0.72, base_y + 52),
            (width * 0.9, base_y + 124),
            (width + 90, base_y + 64),
            (width + 90, height),
        ]
        draw.polygon(points, fill=(*tone, alpha))

    for index in range(6):
        y = int(height * (0.26 + index * 0.08))
        draw.arc(
            (-width // 7, y, width + width // 7, y + 150),
            8,
            172,
            fill=(255, 255, 255, 18 + index * 5),
            width=3,
        )

    draw.ellipse((-230, -180, 680, 600), fill=(*accent_rgb, 56))
    return Image.alpha_composite(image, layer)


def make_avatar(avatar_bytes: Optional[bytes], size: int, accent: str) -> Image.Image:
    try:
        if not avatar_bytes:
            raise OSError("empty avatar")
        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
        side = min(avatar.size)
        left = (avatar.width - side) // 2
        top = (avatar.height - side) // 2
        avatar = avatar.crop((left, top, left + side, top + side))
    except OSError:
        avatar = Image.new("RGBA", (size, size), (*hex_to_rgb(accent), 255))
        draw = ImageDraw.Draw(avatar)
        font = load_font(max(28, size // 3), bold=True)
        label_w, label_h = text_size(draw, "修", font)
        draw.text(((size - label_w) / 2, (size - label_h) / 2 - size * 0.04), "修", font=font, fill="#ffffff")
    avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(avatar, (0, 0), mask)
    return output


def draw_progress(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], ratio: float, accent: str) -> None:
    x1, y1, x2, y2 = box
    radius = (y2 - y1) // 2
    draw.rounded_rectangle(box, radius=radius, fill="#e7e0d3")
    fill_width = max(y2 - y1, int((x2 - x1) * max(0.0, min(1.0, ratio))))
    draw.rounded_rectangle((x1, y1, x1 + fill_width, y2), radius=radius, fill=accent)
    draw.rounded_rectangle(box, radius=radius, outline="#ffffff", width=2)




def draw_sprite_progress_trough(image: Image.Image, box: tuple[int, int, int, int], ratio: float, accent: str) -> None:
    x1, y1, x2, y2 = box
    size = (x2 - x1, y2 - y1)
    ratio = max(0.0, min(1.0, float(ratio)))
    try:
        frame = Image.open(SIGNIN_EXPERIENCE_TROUGH).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        liquid_raw = Image.open(SIGNIN_EXPERIENCE_LIQUID).convert("RGBA")
    except OSError:
        draw_progress(ImageDraw.Draw(image), box, ratio, accent)
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

def equipped_title(reward: Optional[dict[str, Any]], empty_text: str) -> str:
    if not reward:
        return empty_text
    return reward_display_name(reward)


def array_proficiency_text(record: UserRecord) -> str:
    if not record.equipped_array:
        return "未布置阵盘"
    if not record.equipped_method:
        return "需先参悟功法"
    key = reward_signature(record.equipped_method)
    proficiency = int((record.array_proficiency or {}).get(key, 0))
    return f"熟练度 {proficiency}/900 · {array_multiplier(record):.1f}x"




def root_brief_summary(record: UserRecord) -> str:
    if record.root is None:
        return "\u672a\u89c9\u9192\u7075\u6839"
    if record.root.tier == "\u53d8\u5f02\u7075\u6839":
        sources = "+".join(record.root.sources or [])
        suffix = f"\uff5c\u7531{sources}\u5148\u5929\u5f02\u53d8" if sources else "\uff5c\u5148\u5929\u5f02\u7980"
        return f"{record.root.display_name}{suffix}"
    roots = record.roots
    names = [root.display_name for root in roots]
    if not names:
        return "\u672a\u89c9\u9192\u7075\u6839"
    suffix = f"\uff5c\u4e94\u884c{len(roots)}\u7075\u6839\u91cf\u5316\u8bc4\u5b9a" if len(roots) > 1 else "\uff5c\u5355\u7075\u6839\u91cf\u5316\u8bc4\u5b9a"
    return f"{' + '.join(names)}{suffix}"


def root_panel_summary(record: UserRecord) -> str:
    if record.root is None:
        return "\u672a\u89c9\u9192\u7075\u6839"
    if record.root.tier == "\u53d8\u5f02\u7075\u6839":
        name = record.root.display_name
        prefix = "\u53d8\u5f02\u7075\u6839"
        if name.startswith(prefix):
            name = name[len(prefix):]
        lines = [prefix, name or record.root.display_name]
        sources = "+".join(record.root.sources or [])
        lines.append(f"\u7531{sources}\u5148\u5929\u5f02\u53d8" if sources else "\u5148\u5929\u5f02\u7980")
        return "\n".join(lines)
    roots = record.roots
    if not roots:
        return "\u672a\u89c9\u9192\u7075\u6839"
    lines = [root.display_name for root in roots[:3]]
    if len(roots) > 3:
        lines[-1] = f"{lines[-1]}\u7b49{len(roots)}\u6761"
    return "\n".join(lines)


def root_purity_summary(record: UserRecord) -> str:
    roots = record.roots
    if not roots:
        return "\u6682\u65e0\u7075\u6839\u7cbe\u7eaf\u5ea6"
    parts = []
    for root in roots:
        purity = max(1, min(100, int(root.purity)))
        label = root.attribute if root.attribute == "\u5148\u5929\u9053\u4f53" else f"{root.attribute}\u7075\u6839"
        text = f"{label}{purity}%"
        if root.is_mutation and root.sources:
            purities = root.source_purities or {}
            sources = [f"{source}{int(purities.get(source, purity))}%" for source in root.sources]
            if sources:
                text += f"\uff08{' + '.join(sources)}\uff09"
        parts.append(text)
    acquired_parts = []
    for root in normalize_acquired_roots(record)[:3]:
        acquired_parts.append(f"{acquired_root_attribute_text(root)}{int(root.get('purity', 0))}%")
    if acquired_parts:
        parts.append("后天：" + " / ".join(acquired_parts))
    return " / ".join(parts)


def draw_info_row(
    draw: ImageDraw.ImageDraw,
    label: str,
    value: str,
    xy: tuple[int, int],
    max_width: int,
    accent: str,
) -> None:
    label_font = load_font(36, bold=True)
    value_font = fit_font(draw, value, max_width, 42, bold=True, min_size=28)
    x, y = xy
    draw_weighted_text(draw, (x, y), label, label_font, "#667085", weight=2)
    draw_weighted_text(draw, (x, y + 48), value, value_font, accent, weight=3)



def item_icon_records() -> list[dict[str, Any]]:
    global _ITEM_ICON_RECORD_CACHE
    if _ITEM_ICON_RECORD_CACHE is not None:
        return _ITEM_ICON_RECORD_CACHE
    if not ITEM_ICON_RECORDS.exists():
        _ITEM_ICON_RECORD_CACHE = []
        return _ITEM_ICON_RECORD_CACHE
    try:
        raw = json.loads(ITEM_ICON_RECORDS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = []
    _ITEM_ICON_RECORD_CACHE = [item for item in raw if isinstance(item, dict)]
    return _ITEM_ICON_RECORD_CACHE


def item_icon_path_for(item: Any = None, name: str = "", category: str = "") -> Optional[Path]:
    candidates: list[str] = []
    item_category = category
    if isinstance(item, dict):
        for key in ("name", "item_name", "title"):
            value = str(item.get(key) or "").strip()
            if value and value not in candidates:
                candidates.append(value)
        item_category = item_category or str(item.get("category") or "").strip()
    if name and name not in candidates:
        candidates.append(str(name).strip())
    records = item_icon_records()
    for candidate in candidates:
        if not candidate:
            continue
        for record in records:
            record_name = str(record.get("item_name") or "")
            if candidate == record_name:
                icon = ITEM_ICON_ROOT / str(record.get("icon") or "")
                return icon if icon.exists() else None
        for record in records:
            record_name = str(record.get("item_name") or "")
            if record_name and (candidate in record_name or record_name in candidate):
                icon = ITEM_ICON_ROOT / str(record.get("icon") or "")
                return icon if icon.exists() else None
    if item_category:
        for record in records:
            if str(record.get("category") or "") == item_category:
                icon = ITEM_ICON_ROOT / str(record.get("icon") or "")
                return icon if icon.exists() else None
    return None


def spirit_root_icon_image(attribute: str) -> Optional[Image.Image]:
    filename = SPIRIT_ROOT_ICON_FILES.get(str(attribute or ""))
    if not filename:
        return None
    cached = _SPIRIT_ROOT_ICON_CACHE.get(attribute)
    if cached is not None:
        return cached.copy()
    icon_path = SPIRIT_ROOT_ICON_DIR / filename
    try:
        icon = Image.open(icon_path).convert("RGBA")
    except OSError:
        return None
    _SPIRIT_ROOT_ICON_CACHE[attribute] = icon
    return icon.copy()


def realm_quality_icon_map() -> dict[str, str]:
    global _REALM_QUALITY_ICON_MAP
    if _REALM_QUALITY_ICON_MAP is not None:
        return _REALM_QUALITY_ICON_MAP
    manifest_path = REALM_QUALITY_ICON_DIR / "realm_quality_icon_manifest.json"
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = []
    mapping: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        filename = str(item.get("file") or "").strip()
        if name and filename:
            mapping[name] = filename
    if "普通筑基" in mapping:
        mapping.setdefault("未定品相", mapping["普通筑基"])
    for alias, target in {
        "普通道基": "普通筑基",
        "良好道基": "良好筑基",
        "优秀道基": "优秀筑基",
        "天道道基": "天道筑基",
        "道基未定": "未定品相",
        "天象元婴": "天命元婴",
        "法相化神": "太虚化神",
    }.items():
        if target in mapping:
            mapping.setdefault(alias, mapping[target])
    _REALM_QUALITY_ICON_MAP = mapping
    return mapping


def realm_quality_icon_image(name: str) -> Optional[Image.Image]:
    key = str(name or "").strip().replace(" ", "")
    if not key:
        return None
    resource_aliases = {
        "\u7075\u77f3": "\u7075\u77f3\u50a8\u5907",
        "\u7075\u77f3\u50a8\u5907": "\u7075\u77f3\u50a8\u5907",
        "\u7cbe\u7eaf\u7075\u6db2": "\u7cbe\u7eaf\u7075\u6db2",
        "BOSS\u6311\u6218": "BOSS\u6311\u6218",
        "Boss\u6311\u6218": "BOSS\u6311\u6218",
        "boss\u6311\u6218": "BOSS\u6311\u6218",
        "\u9996\u9886\u6311\u6218": "BOSS\u6311\u6218",
    }
    key = resource_aliases.get(key, key)
    cached = _REALM_QUALITY_ICON_CACHE.get(key)
    if cached is not None:
        return cached.copy()
    filename = realm_quality_icon_map().get(key)
    if not filename and (key.endswith("·空") or key.endswith("空")):
        filename = realm_quality_icon_map().get("未定品相")
    if not filename:
        return None
    icon_path = REALM_QUALITY_ICON_DIR / filename
    try:
        icon = Image.open(icon_path).convert("RGBA")
    except OSError:
        return None
    _REALM_QUALITY_ICON_CACHE[key] = icon
    return icon.copy()


def sample_icon_item(name: str = "", category: str = "", offset: int = 0) -> Optional[dict[str, Any]]:
    records = item_icon_records()
    matched: list[dict[str, Any]] = []
    if name:
        matched = [record for record in records if name in str(record.get("item_name") or "")]
    if not matched and category:
        matched = [record for record in records if str(record.get("category") or "") == category]
    if not matched:
        return None
    record = matched[offset % len(matched)]
    return {"name": record.get("item_name"), "category": record.get("category"), "tier": record.get("tier"), "grade": record.get("grade")}


CATEGORY_ICON_BINDINGS: dict[str, tuple[str, str]] = {
    "\u7075\u5668": ("\u5e9a\u91d1\u9752\u7af9\u8702\u4e91\u5251", "\u7075\u5668"),
    "\u529f\u6cd5": ("\u9752\u5e1d\u957f\u751f\u7ecf", "\u529f\u6cd5"),
    "\u9635\u76d8": ("\u5468\u5929\u661f\u6597\u9635\u76d8", "\u9635\u76d8"),
    "\u9635\u6cd5": ("\u5468\u5929\u661f\u6597\u9635\u76d8", "\u9635\u76d8"),
    "\u7b26\u7b93": ("\u4e7e\u5764\u632a\u79fb\u7b26", "\u7b26\u7b93"),
    "\u5080\u5121": ("\u9752\u7389\u673a\u5173\u4eba", "\u5080\u5121"),
    "\u795e\u901a": ("\u516b\u7981", "\u7279\u6b8a\u80fd\u529b"),
    "\u4ea4\u6613": ("\u4e0a\u54c1\u7075\u77f3\u5323", "\u7075\u77f3"),
    "\u4e07\u5b9d\u697c": ("\u4e0a\u54c1\u7075\u77f3\u5323", "\u7075\u77f3"),
    "\u4e39\u836f": ("\u7b51\u57fa\u4e39", "\u4e39\u836f"),
    "\u70bc\u4e39": ("\u4e39\u971e\u70bc\u6c14\u7089", "\u7075\u5668"),
    "\u7075\u98df": ("\u4e5d\u971e\u7389\u9732\u7fb9", "\u7075\u98df"),
    "\u7075\u690d": ("\u4e5d\u53f6\u4ed9\u83b2", "\u7075\u690d"),
    "\u7075\u6750": ("\u5e9a\u91d1", "\u7075\u6750"),
    "\u7075\u77f3": ("\u4e0a\u54c1\u7075\u77f3\u5323", "\u7075\u77f3"),
    "\u79d8\u5883": ("\u865a\u5929\u9f0e", "\u5947\u7269"),
    "\u56fe\u9274": ("\u9752\u5e1d\u957f\u751f\u7ecf", "\u529f\u6cd5"),
    "\u6597\u6cd5": ("\u4e7e\u5764\u632a\u79fb\u7b26", "\u7b26\u7b93"),
}


def category_icon_item(label: str) -> Optional[dict[str, Any]]:
    binding = CATEGORY_ICON_BINDINGS.get(str(label or ""))
    if binding:
        name, category = binding
        return {"name": name, "category": category}
    return sample_icon_item(category=str(label or ""))


def png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()



def render_signin_card(
    result: SigninResult,
    nickname: str,
    avatar_bytes: Optional[bytes],
    width: int = 900,
) -> bytes:
    record = result.record
    root = record.root or Root("\u51e1\u54c1", 0, "\u4e0b\u54c1", 0, "\u571f")
    accent = ATTRIBUTE_COLORS.get(root.attribute, "#3589d8")

    if not SIGNIN_PANEL_BG.exists() or not SIGNIN_PORTRAIT_FRAME.exists():
        return _render_signin_card_legacy(result, nickname, avatar_bytes, width)

    try:
        image = Image.open(SIGNIN_PANEL_BG).convert("RGBA")
        portrait_frame = Image.open(SIGNIN_PORTRAIT_FRAME).convert("RGBA")
    except OSError:
        return _render_signin_card_legacy(result, nickname, avatar_bytes, width)

    draw = ImageDraw.Draw(image)

    def _measure(value: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
        return text_size(draw, value, fnt)

    def _wrap(value: str, fnt: ImageFont.ImageFont, max_width: int, max_lines: int) -> list[str]:
        lines: list[str] = []
        for paragraph in str(value or "").splitlines() or [""]:
            current = ""
            for char in paragraph:
                trial = current + char
                if not current or _measure(trial, fnt)[0] <= max_width:
                    current = trial
                    continue
                lines.append(current)
                current = char.lstrip()
                if len(lines) >= max_lines:
                    return lines
            if current or not lines:
                lines.append(current)
            if len(lines) >= max_lines:
                return lines
        return lines[:max_lines] or [""]

    def _ellipsis(value: str, fnt: ImageFont.ImageFont, max_width: int) -> str:
        suffix = "..."
        value = str(value or "").rstrip()
        if _measure(value, fnt)[0] <= max_width:
            return value
        if _measure(suffix, fnt)[0] > max_width:
            return ""
        for length in range(len(value), 0, -1):
            candidate = value[:length].rstrip() + suffix
            if _measure(candidate, fnt)[0] <= max_width:
                return candidate
        return suffix

    def _draw_box_text(
        box: tuple[int, int, int, int],
        value: str,
        start_size: int,
        fill: str,
        bold: bool = True,
        max_lines: int = 1,
        weight: int = 2,
        min_size: int = 12,
        line_gap: int = 4,
    ) -> None:
        x1, y1, x2, y2 = box
        max_width = x2 - x1
        max_height = y2 - y1
        for size in range(start_size, min_size - 1, -1):
            fnt = load_font(size, bold=bold)
            lines = _wrap(value, fnt, max_width, max_lines)
            if len(lines) > max_lines:
                lines = lines[:max_lines]
            line_height = _measure("\u4fee", fnt)[1] + line_gap
            total_height = line_height * len(lines) - line_gap
            if total_height <= max_height:
                y = y1
                for index, line in enumerate(lines):
                    if index == len(lines) - 1:
                        line = _ellipsis(line, fnt, max_width)
                    draw_weighted_text(draw, (x1, y), line, fnt, fill, weight=weight)
                    y += line_height
                return
        fnt = load_font(min_size, bold=bold)
        y = y1
        for line in _wrap(value, fnt, max_width, max_lines):
            draw_weighted_text(draw, (x1, y), _ellipsis(line, fnt, max_width), fnt, fill, weight=weight)
            y += _measure("\u4fee", fnt)[1] + line_gap

    def _draw_field(
        label: str,
        value: str,
        label_box: tuple[int, int, int, int],
        value_box: tuple[int, int, int, int],
        value_fill: str,
        value_size: int,
        value_lines: int = 1,
    ) -> None:
        _draw_box_text(label_box, label, 17, "#647084", bold=True, max_lines=1, weight=2, min_size=12)
        _draw_box_text(value_box, value, value_size, value_fill, bold=True, max_lines=value_lines, weight=2, min_size=11)

    def _avatar_for_slot(slot_size: tuple[int, int]) -> Image.Image:
        slot_w, slot_h = slot_size
        try:
            if not avatar_bytes:
                raise OSError("empty avatar")
            avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
            side = min(avatar.size)
            left = (avatar.width - side) // 2
            top = (avatar.height - side) // 2
            avatar = avatar.crop((left, top, left + side, top + side))
        except OSError:
            avatar = Image.new("RGBA", (slot_w, slot_h), (*hex_to_rgb(accent), 255))
            avatar_draw = ImageDraw.Draw(avatar)
            fallback_font = load_font(max(34, min(slot_w, slot_h) // 3), bold=True)
            label = "\u4fee"
            label_w, label_h = text_size(avatar_draw, label, fallback_font)
            avatar_draw.text(((slot_w - label_w) / 2, (slot_h - label_h) / 2 - slot_h * 0.04), label, font=fallback_font, fill="#ffffff")
        avatar = avatar.resize((slot_w, slot_h), Image.Resampling.LANCZOS).convert("RGBA")
        mask = Image.new("L", (slot_w, slot_h), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, slot_w - 1, slot_h - 1), fill=255)
        avatar.putalpha(mask.filter(ImageFilter.GaussianBlur(0.4)))
        return avatar

    avatar_box = (199, 122, 459, 382)
    # Layer order: background, avatar, then portrait frame overlay on top.
    image.alpha_composite(_avatar_for_slot((avatar_box[2] - avatar_box[0], avatar_box[3] - avatar_box[1])), avatar_box[:2])
    image.alpha_composite(portrait_frame, (145, 55))

    header = "\u4eca\u65e5\u7b7e\u5230\u6210\u529f"
    if result.already_signed:
        header = "\u4eca\u65e5\u5df2\u5b8c\u6210\u7b7e\u5230"
    elif result.is_first:
        header = "\u68c0\u6d4b\u5230\u5bbf\u4e3b\u9996\u6b21\u7b7e\u5230"
    hint = "\u5929\u8d4b\u62bd\u53d6\u5b8c\u6210" if result.is_first else "\u4fee\u70bc\u65e5\u5fd7\u5df2\u66f4\u65b0"
    if result.already_signed:
        hint = "\u5bbf\u4e3b\u4eca\u65e5\u6c14\u606f\u7a33\u5b9a\uff0c\u65e0\u9700\u91cd\u590d\u95ed\u5173"

    _draw_box_text((545, 150, 900, 206), header, 42, "#172033", bold=True, weight=3)
    _draw_box_text((545, 214, 930, 254), nickname or f"QQ {record.user_id}", 31, "#4b5565", bold=True, weight=2)
    _draw_box_text((545, 260, 955, 292), hint, 20, "#93702d", bold=True, weight=2)

    root_text = root_panel_summary(record)
    root_purity_text = root_purity_summary(record)
    _draw_field("\u7075\u6839", root_text, (238, 455, 390, 484), (238, 488, 545, 562), accent, 19, 3)
    _draw_field("\u7075\u6839\u7cbe\u7eaf\u5ea6", root_purity_text, (475, 455, 680, 484), (475, 490, 790, 560), accent, 19, 2)
    _draw_field("\u5f53\u524d\u5883\u754c", record.realm, (835, 440, 1005, 468), (835, 472, 1038, 535), "#172033", 34, 1)

    _draw_field("\u7b7e\u5230\u6b21\u6570", f"{record.sign_count} \u6b21", (188, 608, 380, 638), (188, 650, 500, 704), "#172033", 36, 1)
    _draw_field("\u7d2f\u8ba1\u4fee\u4e3a", f"{record.total_exp} \u70b9", (650, 608, 858, 638), (650, 650, 1040, 704), accent, 36, 1)

    array_status = array_proficiency_text(record)
    bottleneck = is_breakthrough_bottleneck(record)
    power_label = "\u74f6\u9888" if bottleneck else "\u6218\u6597\u5c5e\u6027"
    power_value = f"\u9700 {breakthrough_required_text(record)}" if bottleneck else f"\u6218\u529b{battle_power(record)} / \u7075\u529b{combat_max_mana(record)}"
    grid_items = [
        ("\u7075\u5668", equipped_title(record.equipped_artifact, "\u672a\u88c5\u5907\u7075\u5668"), accent),
        ("\u529f\u6cd5", equipped_title(record.equipped_method, "\u672a\u53c2\u609f\u529f\u6cd5"), accent),
        ("\u9635\u76d8", equipped_title(record.equipped_array, "\u672a\u5e03\u7f6e\u9635\u76d8"), accent),
        ("\u9635\u6cd5\u719f\u7ec3", array_status, accent),
        ("\u5883\u754c\u54c1\u76f8", record.realm_quality, accent),
        (power_label, power_value, "#9b3f1e" if bottleneck else accent),
        ("\u8def\u7ebf", record.route_summary, accent),
        ("\u8eab\u4efd\u4ee4\u724c", record.identity_summary, accent),
        ("\u540e\u5929\u7075\u6839", acquired_root_summary(record, limit=1), accent),
    ]
    columns = [(210, 455), (500, 755), (800, 1060)]
    rows = [(754, 820), (842, 908), (930, 996)]
    for index, (label, value, color) in enumerate(grid_items):
        col = index % 3
        row = index // 3
        x1, x2 = columns[col]
        y1, y2 = rows[row]
        _draw_field(label, value, (x1, y1, x2, y1 + 23), (x1, y1 + 27, x2, y2), color, 17, 2)

    required = record.progress_required
    progress_ratio = record.realm_exp / max(1, required)
    draw_sprite_progress_trough(image, (188, 1018, 1065, 1095), progress_ratio, accent)
    progress_text = f"{record.realm_exp}/{required}"
    if bottleneck:
        progress_text = f"{progress_text} \u00b7 \u5dc5\u5cf0"
    _draw_box_text((320, 1045, 520, 1080), "\u7ecf\u9a8c\u8fdb\u5ea6", 24, "#ffffff", bold=True, weight=3)
    _draw_box_text((785, 1045, 1065, 1080), progress_text, 21, "#ffffff", bold=True, weight=2)

    footer_parts = []
    if not result.already_signed:
        footer_parts.append(f"\u4fee\u70bc\u8fdb\u5ea6 +{result.gained_exp}")
    if result.method_bonus_exp:
        footer_parts.append(f"\u529f\u6cd5\u52a0\u6210 +{result.method_bonus_exp}")
    if result.item_bonus_exp:
        footer_parts.append(f"\u7075\u7269\u52a0\u6210 +{result.item_bonus_exp}")
    if result.pending_exp_applied:
        footer_parts.append(f"\u65e5\u699c\u5956\u52b1 +{result.pending_exp_applied}")
    if result.spirit_liquid_gain:
        footer_parts.append(f"\u7cbe\u7eaf\u7075\u6db2 +{result.spirit_liquid_gain}")
    if result.leveled_realms:
        footer_parts.append(f"\u8fde\u7834 {result.leveled_realms} \u5883")
    if record.pending_exp:
        footer_parts.append(f"\u5f85\u9886\u4fee\u4e3a {record.pending_exp}")
    if record.fishing_chances:
        footer_parts.append(f"\u5782\u9493\u6b21\u6570 {record.fishing_chances}")
    if result.encounter and result.encounter.happened:
        footer_parts.append("\u4eca\u65e5\u5947\u9047")
    footer = " \u00b7 ".join(footer_parts) or "\u660e\u65e5\u518d\u6765\uff0c\u7075\u6c14\u81ea\u4f1a\u79ef\u84c4"
    _draw_box_text((760, 1130, 1085, 1160), footer, 16, "#647084", bold=False, weight=1, max_lines=1, min_size=12)
    return png_bytes(image)

def _render_signin_card_legacy(
    result: SigninResult,
    nickname: str,
    avatar_bytes: Optional[bytes],
    width: int = 900,
) -> bytes:
    record = result.record
    root = record.root or Root("凡品", 0, "下品", 0, "土")
    accent = ATTRIBUTE_COLORS.get(root.attribute, "#3589d8")
    width = max(width, 1500)
    height = 1960
    image = make_xiuxian_background(width, height, accent)
    draw = ImageDraw.Draw(image)

    title_font = load_font(90, bold=True)
    subtitle_font = fit_font(draw, nickname or f"QQ {record.user_id}", 900, 70, bold=True, min_size=52)
    normal_font = load_font(58, bold=True)
    small_font = load_font(36, bold=True)
    label_font = load_font(42, bold=True)
    root_text = root_brief_summary(record)
    root_purity_text = root_purity_summary(record)
    realm_font = fit_font(draw, record.realm, 420, 74, bold=True, min_size=50)
    number_font = load_font(82, bold=True)

    draw_card(image, (78, 92, width - 78, height - 78))
    avatar = make_avatar(avatar_bytes, 210, accent)
    image.alpha_composite(avatar, (132, 150))
    draw.ellipse((122, 140, 352, 370), outline=accent, width=9)

    header = "今日签到成功"
    if result.already_signed:
        header = "今日已完成签到"
    elif result.is_first:
        header = "检测到宿主首次签到"
    draw_weighted_text(draw, (410, 138), header, title_font, "#172033", weight=4)
    draw_weighted_text(draw, (414, 248), nickname or f"QQ {record.user_id}", subtitle_font, "#435063", weight=4)

    hint = "天赋抽取完成" if result.is_first else "修炼日志已更新"
    if result.already_signed:
        hint = "宿主今日气息稳定，无需重复闭关"
    draw_weighted_text(draw, (414, 336), hint, small_font, "#7b5b1f", weight=2)

    root_box = (132, 430, width - 132, 740)
    draw.rounded_rectangle(root_box, radius=42, fill=(252, 247, 232, 238), outline="#ead5a7", width=5)
    root_x = 184
    realm_x = width - 590
    root_value_width = max(360, realm_x - root_x - 54)
    root_font, root_lines, root_line_gap = fit_clamped_lines(
        draw, root_text, root_value_width, 92, 62, bold=True, min_size=34, max_lines=2, line_gap=6
    )
    draw_weighted_text(draw, (root_x, 470), "\u7075\u6839", label_font, "#6b7280", weight=2)
    root_line_y = 522
    for root_line in root_lines:
        draw_weighted_text(draw, (root_x, root_line_y), root_line, root_font, accent, weight=4)
        root_line_y += text_size(draw, root_line, root_font)[1] + root_line_gap
    draw_weighted_text(draw, (realm_x, 470), "\u5f53\u524d\u5883\u754c", label_font, "#6b7280", weight=2)
    draw_weighted_text(draw, (realm_x, 542), record.realm, realm_font, "#172033", weight=4)

    purity_box = (root_x, 640, width - 184, 720)
    draw.rounded_rectangle(purity_box, radius=28, fill=(255, 255, 255, 150), outline="#eadfca", width=2)
    purity_label_font = load_font(34, bold=True)
    purity_value_x = root_x + 286
    purity_value_width = max(420, width - purity_value_x - 210)
    purity_font, purity_lines, purity_line_gap = fit_clamped_lines(
        draw, root_purity_text, purity_value_width, 58, 38, bold=True, min_size=26, max_lines=2, line_gap=4
    )
    draw_weighted_text(draw, (root_x + 28, 662), "\u7075\u6839\u7cbe\u7eaf\u5ea6", purity_label_font, "#667085", weight=2)
    purity_line_y = 652 if len(purity_lines) > 1 else 662
    for purity_line in purity_lines:
        draw_weighted_text(draw, (purity_value_x, purity_line_y), purity_line, purity_font, accent, weight=3)
        purity_line_y += text_size(draw, purity_line, purity_font)[1] + purity_line_gap

    stats_top = 800
    stat_gap = 50
    stat_width = (width - 264 - stat_gap) // 2
    for index, (label, value, color) in enumerate(
        [("签到次数", f"{record.sign_count} 次", "#172033"), ("累计修为", f"{record.total_exp} 点", accent)]
    ):
        left = 132 + index * (stat_width + stat_gap)
        draw.rounded_rectangle((left, stats_top, left + stat_width, stats_top + 220), radius=42, fill=(255, 255, 255, 238), outline="#eadfca", width=5)
        draw_weighted_text(draw, (left + 54, stats_top + 38), label, label_font, "#667085", weight=2)
        draw_weighted_text(draw, (left + 54, stats_top + 108), value, number_font, color, weight=4)

    info_top = 1080
    info_box = (132, info_top, width - 132, info_top + 430)
    draw.rounded_rectangle(info_box, radius=42, fill=(255, 255, 255, 236), outline="#eadfca", width=5)
    draw_weighted_text(draw, (184, info_top + 34), "历练状态", label_font, "#172033", weight=3)

    col_gap = 34
    inner_left = 184
    inner_width = width - 368
    col_width = (inner_width - col_gap * 2) // 3
    row1_y = info_top + 126
    row2_y = info_top + 228
    row3_y = info_top + 330
    array_status = array_proficiency_text(record)
    bottleneck = is_breakthrough_bottleneck(record)
    power_label = "\u74f6\u9888" if bottleneck else "\u6218\u6597\u5c5e\u6027"
    power_value = f"\u9700 {breakthrough_required_text(record)}" if bottleneck else f"\u6218\u529b{battle_power(record)} / \u7075\u529b{combat_max_mana(record)}"
    info_rows = [
        ("灵器", equipped_title(record.equipped_artifact, "未装备灵器"), row1_y),
        ("功法", equipped_title(record.equipped_method, "未参悟功法"), row1_y),
        ("阵盘", equipped_title(record.equipped_array, "未布置阵盘"), row1_y),
        ("阵法熟练", array_status, row2_y),
        ("境界品相", record.realm_quality, row2_y),
        (power_label, power_value, row2_y),
        ("路线", record.route_summary, row3_y),
        ("身份令牌", record.identity_summary, row3_y),
        ("后天灵根", acquired_root_summary(record, limit=1), row3_y),
    ]
    for idx, (label, value, row_y) in enumerate(info_rows):
        col = idx % 3
        x = inner_left + col * (col_width + col_gap)
        value_color = "#9a3412" if label == "瓶颈" else accent
        draw_info_row(draw, label, value, (x, row_y), col_width, value_color)

    required = record.progress_required
    ratio = record.realm_exp / max(1, required)
    progress_top = 1605
    draw_weighted_text(draw, (132, progress_top), "经验进度", normal_font, "#172033", weight=3)
    progress_text = f"{record.realm_exp}/{required}"
    if bottleneck:
        progress_text = f"{progress_text} · 巅峰"
    progress_font = fit_font(draw, progress_text, 420, 58, bold=True, min_size=42)
    draw_weighted_text(draw, (width - 510, progress_top + 4), progress_text, progress_font, "#172033", weight=3)
    draw_progress(draw, (132, progress_top + 100, width - 132, progress_top + 170), ratio, accent)

    footer_parts = []
    if not result.already_signed:
        footer_parts.append(f"修炼进度 +{result.gained_exp}")
    if result.method_bonus_exp:
        footer_parts.append(f"功法加成 +{result.method_bonus_exp}")
    if result.leveled_realms:
        footer_parts.append(f"连破 {result.leveled_realms} 境")
    if result.pending_exp_applied:
        footer_parts.append(f"日榜奖励 +{result.pending_exp_applied}")
    if record.pending_exp:
        footer_parts.append(f"待领取修为 {record.pending_exp}")
    if record.fishing_chances:
        footer_parts.append(f"垂钓次数 {record.fishing_chances}")
    if result.encounter and result.encounter.happened:
        footer_parts.append("今日奇遇")
    footer = " · ".join(footer_parts) or "明日再来，灵气自会积蓄"
    footer_font = fit_font(draw, footer, width - 264, 28, min_size=20)
    draw.text((132, height - 104), footer, font=footer_font, fill="#435063")
    return png_bytes(image)

def reward_title(reward: dict[str, Any]) -> str:
    return f"[{reward['tier']}{reward['grade']}{reward['category']} {reward['name']}]"


def render_fishing_card(
    record: UserRecord,
    rewards: list[dict[str, Any]],
    nickname: str,
    avatar_bytes: Optional[bytes],
    width: int = 900,
) -> bytes:
    accent = record.root.color if record.root else "#4f8fd8"
    height = 360 + max(1, len(rewards)) * 86
    image = make_background(width, height, accent)
    draw = ImageDraw.Draw(image)

    title_font = load_font(44, bold=True)
    subtitle_font = load_font(24)
    desc_font = load_font(21)
    small_font = load_font(22)

    draw_card(image, (54, 62, width - 54, height - 58))
    avatar = make_avatar(avatar_bytes, 92, accent)
    image.alpha_composite(avatar, (92, 104))
    draw.ellipse((86, 98, 190, 202), outline=accent, width=4)
    draw.text((220, 104), "诸天万界垂钓", font=title_font, fill="#20283a")
    draw.text((222, 160), nickname or f"QQ {record.user_id}", font=subtitle_font, fill="#596174")
    draw.text((222, 196), f"正在为宿主进行 {len(rewards)} 次垂钓", font=small_font, fill="#7a5d2a")

    y = 262
    for index, reward in enumerate(rewards, start=1):
        tier_color = TIER_COLORS.get(str(reward["tier"]), "#7a7f8f")
        draw.rounded_rectangle((92, y, width - 92, y + 70), radius=18, fill="#fbf8f0", outline="#eee2ca", width=2)
        draw.rounded_rectangle((116, y + 16, 166, y + 54), radius=14, fill=tier_color)
        draw.text((126, y + 21), f"{index:02d}", font=desc_font, fill="#ffffff")
        title = reward_title(reward)
        item_font = fit_font(draw, title, width - 310, 27, bold=True, min_size=19)
        draw.text((186, y + 11), title, font=item_font, fill=tier_color)
        desc = str(reward["description"])
        required_attribute = reward.get("required_attribute")
        if required_attribute:
            compatible = "契合" if reward.get("compatible") else "暂不契合"
            desc = f"{desc} 需求{required_attribute}灵根，{compatible}。"
        desc_font_fit = fit_font(draw, desc, width - 300, 21, min_size=16)
        draw.text((188, y + 44), desc, font=desc_font_fit, fill="#596174")
        y += 86

    draw.text((92, height - 100), f"剩余垂钓次数 {record.fishing_chances}", font=small_font, fill="#596174")
    return png_bytes(image)

PANEL_ICON_ALIASES = {
    "\u7b7e\u5230": "signin",
    "\u7075\u6839": "realm",
    "\u4fee\u4e3a": "realm",
    "\u5883\u754c": "realm",
    "\u72b6\u6001": "realm",
    "\u7a81\u7834": "breakthrough",
    "\u74f6\u9888": "breakthrough",
    "\u6c89\u6dc0": "breakthrough",
    "\u6563\u529f": "breakthrough",
    "\u5782\u9493": "fishing",
    "\u9493\u9c7c": "fishing",
    "\u6392\u884c": "rank",
    "\u699c": "rank",
    "\u6218\u529b": "power",
    "\u5207\u78cb": "duel",
    "PK": "duel",
    "pk": "duel",
    "\u7075\u5668": "artifact",
    "\u6b66\u5668": "artifact",
    "\u5251": "artifact",
    "\u5200": "artifact",
    "\u67aa": "artifact",
    "\u529f\u6cd5": "method",
    "\u4e66": "method",
    "\u7ecf": "method",
    "\u9635\u76d8": "array",
    "\u9635\u6cd5": "array",
    "\u5080\u5121": "puppet",
    "\u7075\u690d": "plant",
    "\u4e39\u836f": "pill",
    "\u7b26\u7b93": "talisman",
    "\u7ed8\u5236": "talisman",
    "\u753b\u7b26": "talisman",
    "\u5236\u7b26": "talisman",
    "\u7075\u77f3": "stone",
    "\u7075\u6db2": "stone",
    "\u7cbe\u7eaf\u7075\u6db2": "stone",
    "\u7075\u6750": "stone",
    "\u6750\u6599": "stone",
    "\u70bc\u5316": "stone",
    "\u7075\u98df": "food",
    "\u5947\u7269": "curio",
    "\u4ed9\u7f18": "curio",
    "\u6742\u7269": "misc",
    "\u9274\u5b9a": "misc",
    "\u80cc\u5305": "bag",
    "\u9053\u5177": "bag",
    "\u7269\u54c1": "bag",
    "\u5956\u52b1": "bag",
    "\u79d8\u5883": "mystic",
    "\u5165\u53e3": "mystic",
    "\u5386\u7ec3": "adventure",
    "\u5e2e\u52a9": "scroll",
    "\u8bf4\u660e": "scroll",
    "\u83dc\u5355": "scroll",
    "\u56fe\u9274": "catalog",
    "\u56fe\u5f55": "catalog",
    "\u8def\u7ebf": "token",
    "\u8eab\u4efd": "token",
    "\u4ee4\u724c": "token",
    "\u4efb\u52a1": "task",
    "\u5546\u5e97": "shop",
    "\u574a\u5e02": "shop",
    "\u70bc\u4e39": "alchemy",
    "\u4e39\u65b9": "alchemy",
    "\u7279\u6b8a\u80fd\u529b": "ability",
    "\u795e\u901a": "ability",
    "\u4e5d\u79d8": "ability",
    "\u516b\u7981": "ability",
    "\u795e\u7981": "ability",
    "\u4f20\u627f": "ability",
    "\u5929\u673a\u5360\u535c": "divination",
    "\u5360\u535c": "divination",
    "\u7b97\u547d": "divination",
    "\u95ee\u5366": "divination",
    "\u8d77\u5366": "divination",
    "\u535c\u5366": "divination",
    "\u6597\u5730\u4e3b": "poker",
    "\u6597\u724c": "poker",
    "\u6251\u514b": "poker",
    "\u624b\u724c": "poker",
    "\u51fa\u724c": "poker",
    "\u52a0\u500d": "poker",
    "\u96f7\u52ab": "poker",
    "\u8b66": "warning",
    "\u9519": "warning",
    "\u7981\u4fee": "warning",
    "\u5931\u8d25": "warning",
}


def icon_key_from_text(text: str, fallback: str = "scroll") -> str:
    for token, icon_key in PANEL_ICON_ALIASES.items():
        if token in text:
            return icon_key
    return fallback


def draw_panel_icon(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], icon_key: str, accent: str) -> None:
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    cx = x1 + w // 2
    cy = y1 + h // 2
    accent_rgb = hex_to_rgb(accent)
    dark = mix(accent_rgb, (21, 32, 48), 0.42)
    light = mix(accent_rgb, (255, 255, 255), 0.52)
    draw.rounded_rectangle(box, radius=max(12, w // 5), fill=(*light, 235), outline=accent, width=max(2, w // 18))

    def line(points, fill=dark, width=max(3, w // 15)):
        draw.line(points, fill=fill, width=width, joint="curve")

    def ellipse(rel_box, fill=None, outline=dark, width=max(3, w // 16)):
        bx = (x1 + int(rel_box[0] * w), y1 + int(rel_box[1] * h), x1 + int(rel_box[2] * w), y1 + int(rel_box[3] * h))
        draw.ellipse(bx, fill=fill, outline=outline, width=width)

    def rect(rel_box, fill=None, outline=dark, width=max(3, w // 16), radius=8):
        bx = (x1 + int(rel_box[0] * w), y1 + int(rel_box[1] * h), x1 + int(rel_box[2] * w), y1 + int(rel_box[3] * h))
        draw.rounded_rectangle(bx, radius=radius, fill=fill, outline=outline, width=width)

    if icon_key == "signin":
        ellipse((0.24, 0.22, 0.76, 0.74), outline=dark)
        line([(x1 + int(0.34 * w), y1 + int(0.51 * h)), (x1 + int(0.46 * w), y1 + int(0.63 * h)), (x1 + int(0.68 * w), y1 + int(0.37 * h))])
        line([(x1 + int(0.32 * w), y1 + int(0.82 * h)), (x1 + int(0.68 * w), y1 + int(0.82 * h))], fill=accent)
    elif icon_key == "realm":
        ellipse((0.28, 0.22, 0.72, 0.66), fill=(255, 255, 255, 100), outline=dark)
        line([(cx, y1 + int(0.16 * h)), (x1 + int(0.64 * w), y1 + int(0.44 * h)), (cx, y1 + int(0.82 * h)), (x1 + int(0.36 * w), y1 + int(0.44 * h)), (cx, y1 + int(0.16 * h))], fill=accent, width=max(3, w // 18))
        ellipse((0.44, 0.40, 0.56, 0.52), fill=dark, outline=dark)
    elif icon_key == "fishing":
        line([(cx, y1 + int(0.18 * h)), (cx, y1 + int(0.62 * h))])
        draw.arc((x1 + int(0.38 * w), y1 + int(0.50 * h), x1 + int(0.76 * w), y1 + int(0.88 * h)), 30, 260, fill=dark, width=max(3, w // 15))
        ellipse((0.22, 0.26, 0.34, 0.38), fill=accent, outline=accent)
    elif icon_key == "artifact":
        blade = [
            (cx, y1 + int(0.12 * h)),
            (x1 + int(0.60 * w), y1 + int(0.46 * h)),
            (cx, y1 + int(0.74 * h)),
            (x1 + int(0.40 * w), y1 + int(0.46 * h)),
        ]
        draw.polygon(blade, fill=(255, 255, 255, 145), outline=dark)
        line([(cx, y1 + int(0.18 * h)), (cx, y1 + int(0.74 * h))], fill=accent, width=max(2, w // 20))
        line([(x1 + int(0.32 * w), y1 + int(0.68 * h)), (x1 + int(0.68 * w), y1 + int(0.68 * h))], fill=dark, width=max(4, w // 13))
        rect((0.44, 0.70, 0.56, 0.88), fill=(*accent_rgb, 130), radius=4)
        ellipse((0.43, 0.84, 0.57, 0.96), fill=dark, outline=dark)
    elif icon_key == "duel":
        line([(x1 + int(0.26 * w), y1 + int(0.20 * h)), (x1 + int(0.74 * w), y1 + int(0.76 * h))], fill=dark, width=max(4, w // 13))
        line([(x1 + int(0.74 * w), y1 + int(0.20 * h)), (x1 + int(0.26 * w), y1 + int(0.76 * h))], fill=dark, width=max(4, w // 13))
        line([(x1 + int(0.38 * w), y1 + int(0.58 * h)), (x1 + int(0.24 * w), y1 + int(0.72 * h))], fill=accent, width=max(3, w // 16))
        line([(x1 + int(0.62 * w), y1 + int(0.58 * h)), (x1 + int(0.76 * w), y1 + int(0.72 * h))], fill=accent, width=max(3, w // 16))
    elif icon_key == "ability":
        rect((0.24, 0.20, 0.70, 0.78), fill=(255, 255, 255, 135), radius=7)
        draw.polygon([
            (x1 + int(0.24 * w), y1 + int(0.20 * h)),
            (x1 + int(0.36 * w), y1 + int(0.14 * h)),
            (x1 + int(0.70 * w), y1 + int(0.20 * h)),
            (x1 + int(0.70 * w), y1 + int(0.78 * h)),
            (x1 + int(0.58 * w), y1 + int(0.84 * h)),
            (x1 + int(0.24 * w), y1 + int(0.78 * h)),
        ], fill=(255, 255, 255, 95), outline=dark)
        line([(x1 + int(0.34 * w), y1 + int(0.34 * h)), (x1 + int(0.58 * w), y1 + int(0.34 * h))], fill=dark, width=max(2, w // 23))
        line([(x1 + int(0.34 * w), y1 + int(0.50 * h)), (x1 + int(0.55 * w), y1 + int(0.50 * h))], fill=dark, width=max(2, w // 23))
        line([(x1 + int(0.34 * w), y1 + int(0.66 * h)), (x1 + int(0.50 * w), y1 + int(0.66 * h))], fill=dark, width=max(2, w // 23))
        draw.arc((x1 + int(0.48 * w), y1 + int(0.24 * h), x1 + int(0.86 * w), y1 + int(0.62 * h)), 205, 35, fill=accent, width=max(3, w // 16))
        draw.arc((x1 + int(0.52 * w), y1 + int(0.34 * h), x1 + int(0.82 * w), y1 + int(0.86 * h)), 25, 230, fill=accent, width=max(3, w // 18))
        ellipse((0.64, 0.42, 0.82, 0.60), fill=(*accent_rgb, 160), outline=dark)
    elif icon_key == "power":
        line([(x1 + int(0.30 * w), y1 + int(0.22 * h)), (x1 + int(0.58 * w), y1 + int(0.22 * h)), (x1 + int(0.46 * w), y1 + int(0.48 * h)), (x1 + int(0.70 * w), y1 + int(0.48 * h)), (x1 + int(0.36 * w), y1 + int(0.84 * h)), (x1 + int(0.48 * w), y1 + int(0.58 * h)), (x1 + int(0.24 * w), y1 + int(0.58 * h))], fill=accent, width=max(4, w // 13))
    elif icon_key == "method":
        rect((0.20, 0.20, 0.78, 0.78), fill=(255, 255, 255, 140), radius=8)
        draw.polygon([
            (x1 + int(0.22 * w), y1 + int(0.20 * h)),
            (x1 + int(0.50 * w), y1 + int(0.28 * h)),
            (x1 + int(0.78 * w), y1 + int(0.20 * h)),
            (x1 + int(0.78 * w), y1 + int(0.78 * h)),
            (x1 + int(0.50 * w), y1 + int(0.70 * h)),
            (x1 + int(0.22 * w), y1 + int(0.78 * h)),
        ], fill=(255, 255, 255, 105), outline=dark)
        line([(cx, y1 + int(0.28 * h)), (cx, y1 + int(0.72 * h))], fill=accent, width=max(2, w // 18))
        for yy in (0.40, 0.52, 0.64):
            line([(x1 + int(0.30 * w), y1 + int(yy * h)), (x1 + int(0.45 * w), y1 + int(yy * h))], width=max(2, w // 25))
            line([(x1 + int(0.56 * w), y1 + int(yy * h)), (x1 + int(0.70 * w), y1 + int(yy * h))], width=max(2, w // 25))
    elif icon_key == "array":
        points = [(cx, y1 + int(0.18 * h)), (x1 + int(0.74 * w), y1 + int(0.34 * h)), (x1 + int(0.74 * w), y1 + int(0.66 * h)), (cx, y1 + int(0.82 * h)), (x1 + int(0.26 * w), y1 + int(0.66 * h)), (x1 + int(0.26 * w), y1 + int(0.34 * h)), (cx, y1 + int(0.18 * h))]
        line(points, width=max(3, w // 18))
        ellipse((0.40, 0.40, 0.60, 0.60), fill=accent, outline=accent)
    elif icon_key == "puppet":
        ellipse((0.36, 0.16, 0.64, 0.42), fill=(255, 255, 255, 130))
        rect((0.28, 0.42, 0.72, 0.78), fill=(255, 255, 255, 80), radius=10)
        line([(x1 + int(0.28 * w), y1 + int(0.54 * h)), (x1 + int(0.16 * w), y1 + int(0.70 * h))])
        line([(x1 + int(0.72 * w), y1 + int(0.54 * h)), (x1 + int(0.84 * w), y1 + int(0.70 * h))])
    elif icon_key == "plant":
        line([(cx, y1 + int(0.78 * h)), (cx, y1 + int(0.34 * h))], fill=dark)
        ellipse((0.22, 0.28, 0.52, 0.56), fill=(*accent_rgb, 120), outline=dark)
        ellipse((0.48, 0.18, 0.78, 0.48), fill=(*accent_rgb, 120), outline=dark)
        line([(x1 + int(0.30 * w), y1 + int(0.82 * h)), (x1 + int(0.70 * w), y1 + int(0.82 * h))], fill=accent)
    elif icon_key == "pill":
        draw.rounded_rectangle((x1 + int(0.22 * w), y1 + int(0.36 * h), x1 + int(0.78 * w), y1 + int(0.62 * h)), radius=w // 8, fill=(255, 255, 255, 150), outline=dark, width=max(3, w // 16))
        line([(cx, y1 + int(0.36 * h)), (cx, y1 + int(0.62 * h))], fill=accent)
    elif icon_key == "talisman":
        rect((0.30, 0.18, 0.70, 0.82), fill=(255, 255, 255, 140), radius=6)
        line([(x1 + int(0.40 * w), y1 + int(0.35 * h)), (x1 + int(0.60 * w), y1 + int(0.35 * h))], fill=accent)
        line([(cx, y1 + int(0.43 * h)), (x1 + int(0.43 * w), y1 + int(0.58 * h)), (x1 + int(0.60 * w), y1 + int(0.64 * h)), (cx, y1 + int(0.76 * h))])
    elif icon_key == "stone":
        points = [(cx, y1 + int(0.18 * h)), (x1 + int(0.76 * w), cy), (cx, y1 + int(0.82 * h)), (x1 + int(0.24 * w), cy), (cx, y1 + int(0.18 * h))]
        line(points)
        line([(x1 + int(0.24 * w), cy), (x1 + int(0.76 * w), cy)], fill=accent, width=max(2, w // 20))
    elif icon_key == "food":
        draw.arc((x1 + int(0.22 * w), y1 + int(0.34 * h), x1 + int(0.78 * w), y1 + int(0.88 * h)), 0, 180, fill=dark, width=max(4, w // 14))
        line([(x1 + int(0.30 * w), y1 + int(0.74 * h)), (x1 + int(0.70 * w), y1 + int(0.74 * h))])
        for xx in (0.38, 0.50, 0.62):
            line([(x1 + int(xx * w), y1 + int(0.25 * h)), (x1 + int((xx - 0.04) * w), y1 + int(0.36 * h))], fill=accent, width=max(2, w // 24))
    elif icon_key == "curio":
        star = [(cx, y1 + int(0.16 * h)), (x1 + int(0.58 * w), y1 + int(0.42 * h)), (x1 + int(0.84 * w), y1 + int(0.42 * h)), (x1 + int(0.64 * w), y1 + int(0.58 * h)), (x1 + int(0.72 * w), y1 + int(0.82 * h)), (cx, y1 + int(0.66 * h)), (x1 + int(0.28 * w), y1 + int(0.82 * h)), (x1 + int(0.36 * w), y1 + int(0.58 * h)), (x1 + int(0.16 * w), y1 + int(0.42 * h)), (x1 + int(0.42 * w), y1 + int(0.42 * h)), (cx, y1 + int(0.16 * h))]
        line(star, fill=accent, width=max(3, w // 18))
    elif icon_key == "bag":
        rect((0.22, 0.34, 0.78, 0.80), fill=(255, 255, 255, 120), radius=10)
        draw.arc((x1 + int(0.34 * w), y1 + int(0.20 * h), x1 + int(0.66 * w), y1 + int(0.50 * h)), 180, 360, fill=dark, width=max(3, w // 16))
        line([(x1 + int(0.34 * w), y1 + int(0.52 * h)), (x1 + int(0.66 * w), y1 + int(0.52 * h))], fill=accent)
    elif icon_key == "misc":
        line([(x1 + int(0.64 * w), y1 + int(0.18 * h)), (x1 + int(0.36 * w), y1 + int(0.74 * h))], fill=dark, width=max(4, w // 14))
        draw.polygon([
            (x1 + int(0.24 * w), y1 + int(0.68 * h)),
            (x1 + int(0.48 * w), y1 + int(0.78 * h)),
            (x1 + int(0.38 * w), y1 + int(0.92 * h)),
            (x1 + int(0.14 * w), y1 + int(0.82 * h)),
        ], fill=(*accent_rgb, 120), outline=dark)
        for offset in (0.18, 0.27, 0.36):
            line([(x1 + int(offset * w), y1 + int(0.78 * h)), (x1 + int((offset + 0.05) * w), y1 + int(0.88 * h))], width=max(2, w // 24))
    elif icon_key == "token":
        rect((0.30, 0.16, 0.70, 0.84), fill=(255, 255, 255, 130), radius=10)
        ellipse((0.43, 0.22, 0.57, 0.36), fill=(*accent_rgb, 160), outline=dark)
        line([(cx, y1 + int(0.36 * h)), (cx, y1 + int(0.68 * h))], fill=accent, width=max(3, w // 17))
        line([(x1 + int(0.40 * w), y1 + int(0.52 * h)), (x1 + int(0.60 * w), y1 + int(0.52 * h))], fill=dark, width=max(2, w // 20))
    elif icon_key == "task":
        rect((0.26, 0.18, 0.74, 0.82), fill=(255, 255, 255, 145), radius=8)
        rect((0.38, 0.12, 0.62, 0.26), fill=(*accent_rgb, 130), radius=5)
        for yy in (0.38, 0.52, 0.66):
            ellipse((0.34, yy - 0.03, 0.40, yy + 0.03), fill=accent, outline=accent)
            line([(x1 + int(0.46 * w), y1 + int(yy * h)), (x1 + int(0.66 * w), y1 + int(yy * h))], width=max(2, w // 24))
    elif icon_key == "catalog":
        rect((0.22, 0.18, 0.78, 0.82), fill=(255, 255, 255, 130), radius=8)
        for xx in (0.36, 0.58):
            line([(x1 + int(xx * w), y1 + int(0.22 * h)), (x1 + int(xx * w), y1 + int(0.78 * h))], fill=accent, width=max(2, w // 24))
        for yy in (0.36, 0.54):
            line([(x1 + int(0.26 * w), y1 + int(yy * h)), (x1 + int(0.74 * w), y1 + int(yy * h))], fill=dark, width=max(2, w // 24))
        rect((0.28, 0.24, 0.34, 0.32), fill=(*accent_rgb, 160), radius=2)
        rect((0.62, 0.60, 0.70, 0.72), fill=(*accent_rgb, 160), radius=2)
    elif icon_key == "shop":
        draw.polygon([
            (x1 + int(0.20 * w), y1 + int(0.26 * h)),
            (x1 + int(0.80 * w), y1 + int(0.26 * h)),
            (x1 + int(0.72 * w), y1 + int(0.44 * h)),
            (x1 + int(0.28 * w), y1 + int(0.44 * h)),
        ], fill=(255, 255, 255, 130), outline=dark)
        for xx in (0.34, 0.50, 0.66):
            line([(x1 + int(xx * w), y1 + int(0.27 * h)), (x1 + int((xx - 0.04) * w), y1 + int(0.43 * h))], fill=accent, width=max(2, w // 22))
        rect((0.28, 0.44, 0.72, 0.78), fill=(255, 255, 255, 100), radius=6)
        line([(x1 + int(0.24 * w), y1 + int(0.78 * h)), (x1 + int(0.76 * w), y1 + int(0.78 * h))], fill=dark)
    elif icon_key == "alchemy":
        draw.arc((x1 + int(0.24 * w), y1 + int(0.38 * h), x1 + int(0.76 * w), y1 + int(0.86 * h)), 0, 180, fill=dark, width=max(4, w // 13))
        rect((0.28, 0.50, 0.72, 0.78), fill=(255, 255, 255, 110), radius=12)
        line([(x1 + int(0.34 * w), y1 + int(0.78 * h)), (x1 + int(0.26 * w), y1 + int(0.92 * h))], fill=dark)
        line([(x1 + int(0.66 * w), y1 + int(0.78 * h)), (x1 + int(0.74 * w), y1 + int(0.92 * h))], fill=dark)
        for xx in (0.40, 0.52, 0.64):
            draw.arc((x1 + int((xx - 0.08) * w), y1 + int(0.16 * h), x1 + int((xx + 0.06) * w), y1 + int(0.42 * h)), 250, 80, fill=accent, width=max(2, w // 24))
    elif icon_key in {"mystic", "breakthrough", "adventure"}:
        if icon_key == "mystic":
            rect((0.24, 0.28, 0.76, 0.80), fill=(255, 255, 255, 80), radius=12)
            draw.arc((x1 + int(0.24 * w), y1 + int(0.12 * h), x1 + int(0.76 * w), y1 + int(0.58 * h)), 180, 360, fill=dark, width=max(4, w // 14))
            line([(cx, y1 + int(0.46 * h)), (cx, y1 + int(0.80 * h))], fill=accent)
        elif icon_key == "breakthrough":
            line([(x1 + int(0.18 * w), y1 + int(0.76 * h)), (x1 + int(0.40 * w), y1 + int(0.44 * h)), (x1 + int(0.54 * w), y1 + int(0.62 * h)), (x1 + int(0.78 * w), y1 + int(0.24 * h))])
            line([(x1 + int(0.68 * w), y1 + int(0.24 * h)), (x1 + int(0.78 * w), y1 + int(0.24 * h)), (x1 + int(0.78 * w), y1 + int(0.34 * h))], fill=accent)
        else:
            line([(x1 + int(0.24 * w), y1 + int(0.72 * h)), (x1 + int(0.42 * w), y1 + int(0.42 * h)), (x1 + int(0.56 * w), y1 + int(0.62 * h)), (x1 + int(0.76 * w), y1 + int(0.32 * h))])
            ellipse((0.34, 0.18, 0.48, 0.32), fill=accent, outline=accent)
    elif icon_key == "rank":
        for i, height_ratio in enumerate((0.52, 0.70, 0.38)):
            left = 0.24 + i * 0.18
            rect((left, 0.82 - height_ratio, left + 0.12, 0.82), fill=(*accent_rgb, 90), radius=6)
    elif icon_key == "divination":
        outer = (x1 + int(0.22 * w), y1 + int(0.18 * h), x1 + int(0.78 * w), y1 + int(0.74 * h))
        draw.ellipse(outer, fill=(255, 255, 255, 150), outline=dark, width=max(3, w // 16))
        draw.pieslice(outer, 90, 270, fill=dark)
        draw.pieslice(outer, 270, 90, fill=(255, 255, 255, 165))
        dot_r = max(3, w // 18)
        draw.ellipse((cx - dot_r, y1 + int(0.32 * h) - dot_r, cx + dot_r, y1 + int(0.32 * h) + dot_r), fill=(255, 255, 255, 220))
        draw.ellipse((cx - dot_r, y1 + int(0.60 * h) - dot_r, cx + dot_r, y1 + int(0.60 * h) + dot_r), fill=dark)
        for yy in (0.82, 0.90):
            line([(x1 + int(0.26 * w), y1 + int(yy * h)), (x1 + int(0.42 * w), y1 + int(yy * h))], fill=accent, width=max(2, w // 24))
            line([(x1 + int(0.58 * w), y1 + int(yy * h)), (x1 + int(0.74 * w), y1 + int(yy * h))], fill=accent, width=max(2, w // 24))
        line([(x1 + int(0.47 * w), y1 + int(0.82 * h)), (x1 + int(0.53 * w), y1 + int(0.82 * h))], fill=dark, width=max(2, w // 24))
        line([(x1 + int(0.47 * w), y1 + int(0.90 * h)), (x1 + int(0.53 * w), y1 + int(0.90 * h))], fill=dark, width=max(2, w // 24))
    elif icon_key == "poker":
        back = (x1 + int(0.22 * w), y1 + int(0.18 * h), x1 + int(0.60 * w), y1 + int(0.76 * h))
        front = (x1 + int(0.38 * w), y1 + int(0.26 * h), x1 + int(0.80 * w), y1 + int(0.86 * h))
        draw.rounded_rectangle(back, radius=max(5, w // 10), fill=(255, 255, 255, 135), outline=dark, width=max(2, w // 20))
        draw.rounded_rectangle(front, radius=max(5, w // 10), fill=(255, 255, 255, 190), outline=accent, width=max(2, w // 18))
        rank_font = load_font(max(12, w // 4), bold=True)
        small_font = load_font(max(10, w // 6), bold=True)
        draw_weighted_text(draw, (x1 + int(0.43 * w), y1 + int(0.30 * h)), "A", rank_font, dark, weight=2)
        draw_weighted_text(draw, (x1 + int(0.63 * w), y1 + int(0.62 * h)), "\u96f7", small_font, accent, weight=2)
        bolt = [
            (x1 + int(0.60 * w), y1 + int(0.36 * h)),
            (x1 + int(0.50 * w), y1 + int(0.55 * h)),
            (x1 + int(0.61 * w), y1 + int(0.55 * h)),
            (x1 + int(0.52 * w), y1 + int(0.78 * h)),
            (x1 + int(0.74 * w), y1 + int(0.49 * h)),
            (x1 + int(0.62 * w), y1 + int(0.49 * h)),
        ]
        draw.polygon(bolt, fill=(*accent_rgb, 185), outline=dark)
    elif icon_key == "warning":
        tri = [(cx, y1 + int(0.18 * h)), (x1 + int(0.80 * w), y1 + int(0.78 * h)), (x1 + int(0.20 * w), y1 + int(0.78 * h)), (cx, y1 + int(0.18 * h))]
        line(tri, fill=accent, width=max(4, w // 14))
        line([(cx, y1 + int(0.38 * h)), (cx, y1 + int(0.58 * h))], fill=dark)
        ellipse((0.47, 0.66, 0.53, 0.72), fill=dark, outline=dark)
    else:
        rect((0.28, 0.22, 0.72, 0.78), fill=(255, 255, 255, 120), radius=8)
        for yy in (0.36, 0.50, 0.64):
            line([(x1 + int(0.36 * w), y1 + int(yy * h)), (x1 + int(0.64 * w), y1 + int(yy * h))], width=max(2, w // 24))


def wrap_panel_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    if not text:
        return [""]
    chunks: list[str] = []
    current = ""
    for char in text:
        trial = current + char
        if current and text_size(draw, trial, font)[0] > max_width:
            chunks.append(current)
            current = char.lstrip()
        else:
            current = trial
    if current:
        chunks.append(current)
    return chunks or [""]



def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.ImageFont,
    fill: str,
    max_width: int,
    line_gap: int = 8,
    weight: int = 1,
    max_lines: int = 3,
) -> int:
    y = xy[1]
    lines = wrap_panel_text(draw, text, font, max_width)
    for part in lines[:max_lines]:
        draw_weighted_text(draw, (xy[0], y), part, font, fill, weight=weight)
        y += text_size(draw, part, font)[1] + line_gap
    return y


def truncate_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    text = str(text or "")
    if text_size(draw, text, font)[0] <= max_width:
        return text
    ellipsis = "..."
    for length in range(len(text), 0, -1):
        candidate = text[:length].rstrip() + ellipsis
        if text_size(draw, candidate, font)[0] <= max_width:
            return candidate
    return ellipsis




def append_ellipsis(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    suffix = "..."
    text = str(text or "").rstrip()
    if text_size(draw, text + suffix, font)[0] <= max_width:
        return text + suffix
    for length in range(len(text), 0, -1):
        candidate = text[:length].rstrip() + suffix
        if text_size(draw, candidate, font)[0] <= max_width:
            return candidate
    return suffix


def draw_clamped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.ImageFont,
    fill: str,
    max_width: int,
    max_lines: int = 1,
    line_gap: int = 6,
    weight: int = 1,
    stroke_width: int = 0,
    stroke_fill: Any = None,
) -> int:
    lines = wrap_panel_text(draw, str(text or ""), font, max_width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = append_ellipsis(draw, lines[-1], font, max_width)
    y = xy[1]
    for part in lines:
        draw_weighted_text(draw, (xy[0], y), part, font, fill, weight=weight, stroke_width=stroke_width, stroke_fill=stroke_fill)
        y += text_size(draw, part, font)[1] + line_gap
    return y




def fit_clamped_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    size: int,
    bold: bool = False,
    min_size: int = 18,
    max_lines: int = 2,
    line_gap: int = 8,
) -> tuple[ImageFont.ImageFont, list[str], int]:
    text = str(text or "")
    for font_size in range(size, min_size - 1, -2):
        font = load_font(font_size, bold=bold)
        lines = wrap_panel_text(draw, text, font, max_width)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = append_ellipsis(draw, lines[-1], font, max_width)
        total_height = sum(text_size(draw, line, font)[1] for line in lines)
        total_height += line_gap * max(0, len(lines) - 1)
        if total_height <= max_height:
            return font, lines, line_gap

    font = load_font(min_size, bold=bold)
    lines = wrap_panel_text(draw, text, font, max_width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = append_ellipsis(draw, lines[-1], font, max_width)
    return font, lines, line_gap

def render_battle_card(
    result: dict[str, Any],
    left_avatar: Optional[bytes] = None,
    right_avatar: Optional[bytes] = None,
    width: int = 1180,
) -> bytes:
    width = max(width, 1180)
    left = dict(result.get("left") or {})
    right = dict(result.get("right") or {})
    timeline = [str(line) for line in list(result.get("timeline") or [])]
    timeline_limit = 18 if result.get("mystic_boss") else 10
    shown_timeline = timeline[:timeline_limit]
    record_row_h = 78
    detail_top = 1040
    detail_h = 132 + max(1, len(shown_timeline)) * record_row_h + (34 if len(timeline) > len(shown_timeline) else 0)
    height = max(1480, detail_top + detail_h + 150)
    accent = "#b91c1c" if result.get("ended_early") else "#7c5ce6"
    image = make_xiuxian_background(width, height, accent)
    draw = ImageDraw.Draw(image)
    draw_card(image, (54, 58, width - 54, height - 58))

    title_text = str(result.get("title") or ("秘境首领生死斗战报" if result.get("mystic_boss") else "普通斗法战报"))
    title_font = fit_font(draw, title_text, width - 320, 64, bold=True, min_size=44)
    subtitle_font = load_font(30, bold=True)
    name_font = load_font(34, bold=True)
    label_font = load_font(23, bold=True)
    body_font = load_font(25, bold=True)
    small_font = load_font(21, bold=True)
    tiny_font = load_font(19, bold=True)
    big_font = load_font(44, bold=True)

    draw_panel_icon(draw, (98, 104, 198, 204), "duel", accent)
    draw_weighted_text(draw, (226, 104), title_text, title_font, "#172033", weight=4)
    subtitle = truncate_text(draw, str(result.get("summary") or "\u6218\u6597\u8bb0\u5f55"), subtitle_font, width - 520)
    draw_weighted_text(draw, (230, 178), subtitle, subtitle_font, "#6b2737", weight=2)
    if result.get("ended_early"):
        remain = int(result.get("remaining_seconds", 0))
        draw_weighted_text(draw, (width - 360, 180), f"\u63d0\u524d\u7ed3\u675f\uff0c\u5269\u4f59 {remain}s", small_font, "#9a3412", weight=2)

    panel_top = 260
    panel_h = 720
    gap = 34
    panel_w = (width - 180 - gap) // 2
    left_box = (90, panel_top, 90 + panel_w, panel_top + panel_h)
    right_box = (90 + panel_w + gap, panel_top, width - 90, panel_top + panel_h)

    def fighter_panel(fighter: dict[str, Any], avatar_bytes: Optional[bytes], box: tuple[int, int, int, int]) -> None:
        x1, y1, x2, y2 = box
        winner = str(result.get("winner_id")) == str(fighter.get("user_id"))
        fill = (255, 255, 255, 235) if winner else (248, 244, 236, 225)
        outline = "#d4af37" if winner else "#eadfca"
        draw.rounded_rectangle(box, radius=30, fill=fill, outline=outline, width=5 if winner else 3)
        avatar = make_avatar(avatar_bytes, 108, accent)
        image.alpha_composite(avatar, (x1 + 30, y1 + 32))
        draw.ellipse((x1 + 24, y1 + 26, x1 + 144, y1 + 146), outline=accent, width=4)
        name = truncate_text(draw, str(fighter.get("nickname") or "\u4fee\u58eb"), name_font, x2 - x1 - 190)
        draw_weighted_text(draw, (x1 + 164, y1 + 34), name, name_font, "#172033", weight=4)
        realm = truncate_text(draw, str(fighter.get("realm") or "\u672a\u77e5\u5883\u754c"), small_font, x2 - x1 - 190)
        draw_weighted_text(draw, (x1 + 166, y1 + 84), realm, small_font, "#667085", weight=2)
        status = "\u80dc\u8005" if winner else "\u8d25\u8005"
        draw_weighted_text(draw, (x1 + 166, y1 + 116), status, body_font, "#b45309" if winner else "#475467", weight=3)

        max_hp = max(1, int(fighter.get("max_hp") or 1))
        hp = max(0, int(fighter.get("hp") or 0))
        draw_weighted_text(draw, (x1 + 30, y1 + 166), f"\u8840\u91cf {hp}/{max_hp}", body_font, "#172033", weight=3)
        draw_progress(draw, (x1 + 30, y1 + 202, x2 - 30, y1 + 234), hp / max_hp, "#dc2626" if hp < max_hp * 0.35 else accent)
        max_mana = max(1, int(fighter.get("max_mana") or 1))
        mana = max(0, int(fighter.get("mana") or 0))
        draw_weighted_text(draw, (x1 + 30, y1 + 244), f"\u7075\u529b {mana}/{max_mana}", body_font, "#172033", weight=3)
        draw_progress(draw, (x1 + 30, y1 + 280, x2 - 30, y1 + 312), mana / max_mana, "#2563eb" if mana >= max_mana * 0.28 else "#9333ea")

        rows = [
            ("\u7075\u6839", str(fighter.get("root") or "\u672a\u77e5"), 2),
            ("\u79cd\u65cf", str(fighter.get("race") or "\u672a\u77e5"), 1),
            ("\u4f53\u8d28", str(fighter.get("physique") or "\u672a\u77e5"), 1),
            ("\u529f\u6cd5", str(fighter.get("method") or "\u672a\u53c2\u609f\u529f\u6cd5"), 1),
            ("\u7c7b\u578b", str(fighter.get("method_kind") or "无"), 1),
            ("\u7b26\u7b93", str(fighter.get("talisman") or "\u672a\u88c5\u5907\u7b26\u7b93"), 1),
        ]
        y = y1 + 334
        value_x = x1 + 104
        value_w = x2 - x1 - 138
        for label, value, max_lines in rows:
            draw_weighted_text(draw, (x1 + 34, y), label, label_font, "#667085", weight=2)
            end_y = draw_clamped_text(draw, value, (value_x, y - 2), small_font, "#344054", value_w, max_lines=max_lines, line_gap=4, weight=1)
            y = max(y + 36, end_y + 4)

        abilities = "\u3001".join(str(item) for item in fighter.get("abilities", [])[:4]) or "\u6682\u672a\u663e\u5316"
        techs = "\u3001".join(str(item) for item in fighter.get("triggered_techniques", [])[:5]) or "\u672a\u89e6\u53d1"
        cd_items = [f"{name}:{turns}\u606f" for name, turns in list(dict(fighter.get("cooldowns") or {}).items())[:2]]
        talisman_power = int(fighter.get("talisman_power") or 0)
        resource = f"\u8017\u7075 {int(fighter.get('mana_spent') or 0)}\uff0c\u4f53\u672f {int(fighter.get('physical_hits') or 0)}\uff0c\u4f53\u8d28 {int(fighter.get('trait_triggers') or 0)}"
        if talisman_power:
            resource += f"\uff0c\u7b26\u7b93+{talisman_power}"
        if cd_items:
            resource += "\uff0cCD " + "\u3001".join(cd_items)
        for label, value, color, weight in [
            ("\u7279\u6b8a", abilities, "#7c2d12", 2),
            ("\u6218\u6280", techs, accent, 2),
            ("\u8d44\u6e90", resource, "#475467", 1),
        ]:
            draw_weighted_text(draw, (x1 + 34, y), label, label_font, "#667085", weight=2)
            end_y = draw_clamped_text(draw, value, (value_x, y - 2), tiny_font, color, value_w, max_lines=2, line_gap=4, weight=weight)
            y = max(y + 36, end_y + 4)

    fighter_panel(left, left_avatar, left_box)
    fighter_panel(right, right_avatar, right_box)

    vs_font = load_font(62, bold=True)
    draw.rounded_rectangle((width // 2 - 54, panel_top + 236, width // 2 + 54, panel_top + 344), radius=54, fill=(255, 255, 255, 230), outline=accent, width=4)
    draw_weighted_text(draw, (width // 2 - 34, panel_top + 255), "VS", vs_font, accent, weight=4)

    detail_bottom = detail_top + detail_h
    draw.rounded_rectangle((90, detail_top, width - 90, detail_bottom), radius=30, fill=(255, 255, 255, 226), outline="#eadfca", width=3)
    draw_weighted_text(draw, (126, detail_top + 32), "\u6218\u6597\u8bb0\u5f55", big_font, "#172033", weight=4)
    draw_weighted_text(draw, (width - 360, detail_top + 44), f"\u7528\u65f6 {int(result.get('elapsed_seconds', 60))}/{int(result.get('duration_seconds', 60))}s", body_font, "#667085", weight=2)

    y = detail_top + 106
    row_text_w = width - 370
    for index, line in enumerate(shown_timeline, start=1):
        draw.rounded_rectangle((126, y, width - 126, y + 66), radius=18, fill=(252, 247, 232, 230), outline="#efe3cb", width=2)
        draw.rounded_rectangle((144, y + 15, 186, y + 49), radius=12, fill=accent)
        draw_weighted_text(draw, (154, y + 17), f"{index}", small_font, "#ffffff", weight=2)
        draw_clamped_text(draw, line, (206, y + 11), body_font, "#344054", row_text_w, max_lines=2, line_gap=2, weight=1)
        y += record_row_h
    if len(timeline) > len(shown_timeline):
        more_text = f"\u8fd8\u6709 {len(timeline) - len(shown_timeline)} \u6761\u6218\u6597\u8bb0\u5f55\u5df2\u6536\u8d77"
        draw_weighted_text(draw, (138, y + 4), more_text, small_font, "#667085", weight=2)

    footer = str(result.get("footer") or "切磋不会消耗修为或损毁装备；符箓栏在普通斗法中生效且不消耗；灵力耗尽后会改用体术、神通或体质特性")
    footer_fit = fit_font(draw, footer, width - 190, 24, bold=True, min_size=18)
    draw_weighted_text(draw, (96, height - 105), footer, footer_fit, "#667085", weight=1)
    return png_bytes(image)



def render_adventure_card(
    record: UserRecord,
    nickname: str = "",
    width: int = 900,
) -> bytes:
    accent = getattr(getattr(record, "root", None), "color", "#7b5cf0") or "#7b5cf0"
    if not ADVENTURE_PANEL_BG.exists():
        summary = battle_summary(record)
        fallback_lines = [
            "\u3010\u5386\u7ec3\u3011",
            f"\u5f53\u524d\u6218\u529b\uff1a{summary['power']}\uff1b{summary['mana_label']}\u4e0a\u9650\uff1a{summary['mana']}",
            f"\u7075\u5668\u69fd\uff1a{summary['artifact_slots']}",
            f"\u672c\u547d\u7075\u5668\uff1a{summary['life_artifact']}",
            f"\u529f\u6cd5\uff1a{summary['method']}",
            f"\u9635\u76d8\uff1a{summary['array']}\uff08{summary['array_multiplier']:.1f}x\uff09",
            f"\u7b26\u7b93\u680f\uff1a{summary['talisman']}\uff08\u6218\u529b+{summary['talisman_power']}\uff09",
            f"\u795e\u901a\uff1a{len(summary['special_abilities'])}\u9879\uff1b\u4f20\u627f\u6750\u6599\uff1a{summary['special_ability_materials']}\u4efd",
            f"\u4fee\u70bc\u8def\u7ebf\uff1a{summary['route']}\uff1b\u8eab\u4efd\uff1a{summary['identity']}",
        ]
        return render_text_panel("\u5386\u7ec3\u9762\u677f", fallback_lines, icon="adventure", accent=accent, width=width)

    try:
        image = Image.open(ADVENTURE_PANEL_BG).convert("RGBA")
    except OSError:
        return render_text_panel("\u5386\u7ec3\u9762\u677f", "\u5386\u7ec3\u5e95\u56fe\u8bfb\u53d6\u5931\u8d25", icon="adventure", accent=accent, width=width)

    draw = ImageDraw.Draw(image)
    summary = battle_summary(record)
    base = 1254
    sx = image.width / base
    sy = image.height / base

    def sbox(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = box
        return (round(x1 * sx), round(y1 * sy), round(x2 * sx), round(y2 * sy))

    def sp(value: int) -> int:
        return max(1, round(value * min(sx, sy)))

    dark = "#111827"
    ink = "#1f2937"
    muted = "#2f4158"
    gold = "#8a571f"
    jade = "#176b56"
    danger = "#8f3218"
    veil = (255, 250, 229, 102)
    veil_soft = (255, 255, 245, 72)
    veil_deep = (52, 36, 70, 78)
    line = (245, 228, 177, 138)

    title_font = load_font(sp(42), bold=True)
    subtitle_font = load_font(sp(24), bold=True)
    label_font = load_font(sp(21), bold=True)
    value_font = load_font(sp(23), bold=True)
    small_font = load_font(sp(20), bold=True)
    tiny_font = load_font(sp(17), bold=True)
    number_font = load_font(sp(30), bold=True)
    text_stroke = (255, 248, 226, 230)
    strong_stroke = (255, 250, 232, 245)

    layout = {
        "title": (242, 64, 1015, 152),
        "left_square": (250, 239, 392, 378),
        "right_square": (872, 239, 1010, 378),
        "left_round": (273, 420, 364, 512),
        "right_round": (895, 425, 984, 510),
        "center_square": (571, 461, 688, 567),
        "badge_1": (337, 580, 425, 659),
        "badge_2": (461, 580, 546, 667),
        "badge_3": (581, 580, 670, 667),
        "badge_4": (708, 579, 793, 664),
        "badge_5": (834, 579, 917, 659),
        "summary": (217, 682, 1045, 768),
        "row_1": (326, 790, 1038, 868),
        "row_2": (326, 871, 1033, 953),
        "row_3": (332, 961, 1032, 1035),
        "cmd_1": (206, 1048, 321, 1158),
        "cmd_2": (347, 1048, 466, 1158),
        "cmd_3": (492, 1048, 609, 1158),
        "cmd_4": (632, 1048, 762, 1158),
        "cmd_5": (773, 1048, 900, 1158),
        "cmd_6": (920, 1048, 1045, 1158),
        "footer": (204, 1162, 1045, 1243),
    }

    def draw_region(box: tuple[int, int, int, int], fill: tuple[int, int, int, int] = veil, radius: int = 18) -> tuple[int, int, int, int]:
        return sbox(box)

    def panel_text(xy: tuple[int, int], text: str, font: ImageFont.ImageFont, fill: Any = ink, weight: int = 2, stroke: int = 2) -> None:
        draw_weighted_text(draw, xy, text, font, fill, weight=weight, stroke_width=sp(stroke), stroke_fill=text_stroke)

    def panel_clamped(
        text: str,
        xy: tuple[int, int],
        font: ImageFont.ImageFont,
        fill: str,
        max_width: int,
        max_lines: int = 1,
        line_gap: int = 6,
        weight: int = 2,
        stroke: int = 2,
    ) -> int:
        return draw_clamped_text(draw, text, xy, font, fill, max_width, max_lines=max_lines, line_gap=line_gap, weight=weight, stroke_width=sp(stroke), stroke_fill=text_stroke)

    def centered_text(box: tuple[int, int, int, int], text: str, font: ImageFont.ImageFont, fill: Any, y_offset: int = 0, weight: int = 2) -> None:
        x1, y1, x2, y2 = sbox(box)
        text = truncate_text(draw, str(text or ""), font, max(10, x2 - x1 - sp(12)))
        tw, th = text_size(draw, text, font)
        draw_weighted_text(draw, (x1 + (x2 - x1 - tw) // 2, y1 + (y2 - y1 - th) // 2 + sp(y_offset)), text, font, fill, weight=weight, stroke_width=sp(2), stroke_fill=text_stroke)

    def slot_text(
        box: tuple[int, int, int, int],
        label: str,
        value: str,
        icon: str = "scroll",
        lines: int = 2,
        fill: tuple[int, int, int, int] = veil,
        label_color: str = muted,
        value_color: str = ink,
    ) -> None:
        x1, y1, x2, y2 = draw_region(box, fill=fill, radius=16)
        panel_clamped(value, (x1 + sp(22), y1 + sp(13)), value_font, value_color, max(20, x2 - x1 - sp(44)), max_lines=lines, line_gap=sp(6), weight=3)

    def paste_generated_icon(
        box: tuple[int, int, int, int],
        item: Any = None,
        name: str = "",
        category: str = "",
        fallback_icon: str = "scroll",
    ) -> bool:
        x1, y1, x2, y2 = box
        icon_path = item_icon_path_for(item, name=name, category=category)
        if not icon_path:
            draw_panel_icon(draw, box, fallback_icon, accent)
            return False
        try:
            icon_img = Image.open(icon_path).convert("RGBA")
        except OSError:
            draw_panel_icon(draw, box, fallback_icon, accent)
            return False
        icon_img.thumbnail((max(1, x2 - x1), max(1, y2 - y1)), Image.Resampling.LANCZOS)
        px = x1 + (x2 - x1 - icon_img.width) // 2
        py = y1 + (y2 - y1 - icon_img.height) // 2
        image.alpha_composite(icon_img, (px, py))
        return True

    def top_slot_display_value(item: Any, value: str, empty: str = "无") -> str:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("item_name") or item.get("title") or "").strip()
            grade = str(item.get("grade") or "").strip()
            if name:
                return f"{grade}{name}" if grade and not name.startswith(grade) else name
        return str(value or empty)

    def top_slot_color(item: Any, fallback: str) -> str:
        if isinstance(item, dict):
            tier = str(item.get("tier") or "").strip()
            return TIER_COLORS.get(tier, fallback)
        return fallback

    def draw_slot_value(
        text: str,
        box: tuple[int, int, int, int],
        color: str,
        start_size: int,
        max_lines: int = 2,
        weight: int = 3,
    ) -> None:
        x1, y1, x2, y2 = box
        max_width = max(10, x2 - x1)
        max_height = max(10, y2 - y1)
        font, lines, line_gap = fit_clamped_lines(
            draw,
            text,
            max_width,
            max_height,
            sp(start_size),
            bold=True,
            min_size=sp(9),
            max_lines=max_lines,
            line_gap=sp(1),
        )
        line_heights = [text_size(draw, line, font)[1] for line in lines]
        total_h = sum(line_heights) + line_gap * max(0, len(lines) - 1)
        y = y1 + max(0, (max_height - total_h) // 2)
        for line, line_h in zip(lines, line_heights):
            tw, _ = text_size(draw, line, font)
            draw_weighted_text(
                draw,
                (x1 + max(0, (max_width - tw) // 2), y),
                line,
                font,
                color,
                weight=weight,
                stroke_width=sp(2),
                stroke_fill=text_stroke,
            )
            y += line_h + line_gap

    def item_slot(box: tuple[int, int, int, int], label: str, value: str, icon: str, value_color: str = ink, item: Any = None) -> None:
        x1, y1, x2, y2 = draw_region(box, fill=veil_soft, radius=20)
        icon_box = (x1 + sp(24), y1 + sp(16), x2 - sp(24), y1 + sp(90))
        has_item = bool(item)
        if has_item:
            paste_generated_icon(icon_box, item=item, name=value, category=str(item.get("category") or "") if isinstance(item, dict) else "", fallback_icon=icon)
        else:
            none_font = load_font(sp(28), bold=True)
            centered_text((box[0] + 8, box[1] + 14, box[2] - 8, box[1] + 72), "无", none_font, muted, weight=3)
        if has_item:
            display_value = top_slot_display_value(item, value, empty="\u672a\u88c5\u5907")
            draw_slot_value(display_value, (x1 + sp(8), y1 + sp(81), x2 - sp(8), y2 - sp(6)), top_slot_color(item, value_color), 17, max_lines=2)
        else:
            draw_slot_value(label, (x1 + sp(8), y1 + sp(82), x2 - sp(8), y2 - sp(8)), muted, 15, max_lines=1)

    def round_slot(
        box: tuple[int, int, int, int],
        label: str,
        value: str,
        icon: str,
        value_color: str = ink,
        item: Any = None,
        empty: bool = False,
        show_label: bool = True,
        icon_dx: int = 0,
    ) -> None:
        x1, y1, x2, y2 = sbox(box)
        has_item = bool(item) and not empty
        if has_item:
            icon_pad_x = sp(17)
            icon_top = sp(6 if show_label else 4)
            icon_bottom = sp(55 if show_label else 48)
            icon_box = (x1 + icon_pad_x + sp(icon_dx), y1 + icon_top, x2 - icon_pad_x + sp(icon_dx), y1 + icon_bottom)
            paste_generated_icon(icon_box, item=item, name=value, category=str(item.get("category") or "") if isinstance(item, dict) else "", fallback_icon=icon)
        else:
            none_font = load_font(sp(26), bold=True)
            centered_text((box[0] + 6, box[1] + 10, box[2] - 6, box[1] + 56), "无", none_font, muted, weight=3)
        if not has_item and show_label:
            centered_text((box[0] + 5, box[1] + 50, box[2] - 5, box[3] - 8), label, tiny_font, muted, weight=2)
        if value and has_item:
            display_value = top_slot_display_value(item, value)
            value_top = y1 + sp(50)
            draw_slot_value(display_value, (x1 + sp(2), value_top, x2 - sp(2), y2 - sp(1)), top_slot_color(item, value_color), 12, max_lines=1)

    def command_slot(box: tuple[int, int, int, int], label: str, command: str, icon: str) -> None:
        x1, y1, x2, y2 = draw_region(box, fill=(255, 250, 229, 86), radius=12)
        icon_item = category_icon_item(label)
        icon_size = min(sp(58), max(sp(42), x2 - x1 - sp(42), y2 - y1 - sp(54)))
        icon_x = x1 + (x2 - x1 - icon_size) // 2
        icon_y = y1 + sp(13)
        paste_generated_icon((icon_x, icon_y, icon_x + icon_size, icon_y + icon_size), item=icon_item, name=label, fallback_icon=icon)
        centered_text((box[0] + 6, box[1] + 74, box[2] - 6, box[3] - 13), label, small_font, dark, weight=3)


    def icon_strip(box: tuple[int, int, int, int], title: str, entries: list[tuple[str, Any, str, str]]) -> None:
        x1, y1, x2, y2 = draw_region(box, fill=(255, 250, 229, 72), radius=16)
        panel_text((x1 + sp(14), y1 + sp(18)), title, small_font, muted, weight=3)
        start_x = x1 + sp(102)
        gap = sp(83)
        base_icon_size = sp(50)
        for index, (label, item, fallback_icon, category) in enumerate(entries[:7]):
            icon_size = sp(54) if category == "realm_quality" else base_icon_size
            icon_top = sp(5) if category == "realm_quality" else sp(8)
            cx = start_x + gap * index
            slot = (cx, y1 + icon_top, cx + icon_size, y1 + icon_top + icon_size)
            if item is None and category == "realm_quality":
                paste_realm_quality_icon(label, slot, fallback_icon)
            else:
                paste_generated_icon(slot, item=item, name=label, category=category, fallback_icon=fallback_icon)
            label_font = fit_font(draw, label, icon_size + sp(12), sp(13), bold=True, min_size=sp(10))
            label_text = truncate_text(draw, label, label_font, icon_size + sp(12))
            lw, _ = text_size(draw, label_text, label_font)
            panel_text((cx + (icon_size - lw) // 2, y2 - sp(22)), label_text, label_font, dark, weight=3, stroke=1)

    def paste_realm_quality_icon(name: str, box: tuple[int, int, int, int], fallback_icon: str = "realm") -> bool:
        x1, y1, x2, y2 = box
        icon_img = realm_quality_icon_image(name)
        if icon_img is None:
            draw_panel_icon(draw, box, fallback_icon, accent)
            return False
        bbox = icon_img.getbbox()
        if bbox:
            icon_img = icon_img.crop(bbox)
        icon_img.thumbnail((max(1, x2 - x1), max(1, y2 - y1)), Image.Resampling.LANCZOS)
        px = x1 + (x2 - x1 - icon_img.width) // 2
        py = y1 + (y2 - y1 - icon_img.height) // 2
        image.alpha_composite(icon_img, (px, py))
        return True

    def resource_strip(box: tuple[int, int, int, int], title: str, entries: list[tuple[str, str, str]]) -> None:
        x1, y1, x2, y2 = draw_region(box, fill=(255, 250, 229, 72), radius=16)
        panel_text((x1 + sp(14), y1 + sp(18)), title, small_font, muted, weight=3)
        start_x = x1 + sp(100)
        area_w = max(1, x2 - start_x - sp(20))
        col_w = area_w // max(1, len(entries))
        for index, (label, value, icon) in enumerate(entries):
            lx = start_x + col_w * index
            icon_size = sp(58)
            paste_realm_quality_icon(label, (lx, y1 + sp(7), lx + icon_size, y1 + sp(65)), icon)
            text_x = lx + sp(68)
            text_w = max(20, col_w - sp(74))
            panel_text((text_x, y1 + sp(9)), label, tiny_font, muted, weight=3, stroke=1)
            value_font_fit = fit_font(draw, value, text_w, sp(18), bold=True, min_size=sp(11))
            panel_clamped(value, (text_x, y1 + sp(34)), value_font_fit, dark, text_w, max_lines=1, line_gap=0, weight=3, stroke=1)
    def compact_realm_quality(value: str) -> str:
        text = str(value or "")
        replacements = {
            "\u666e\u901a\u7b51\u57fa": "\u666e\u901a\u9053\u57fa",
            "\u826f\u597d\u7b51\u57fa": "\u826f\u597d\u9053\u57fa",
            "\u4f18\u79c0\u7b51\u57fa": "\u4f18\u79c0\u9053\u57fa",
            "\u5b8c\u7f8e\u9053\u57fa": "\u5b8c\u7f8e\u9053\u57fa",
            "\u5929\u9053\u7b51\u57fa": "\u5929\u9053\u9053\u57fa",
        }
        return replacements.get(text, text)

    def root_badge(box: tuple[int, int, int, int]) -> None:
        x1, y1, x2, y2 = sbox(box)
        root = getattr(record, "root", None)
        if not root:
            none_font = load_font(sp(30), bold=True)
            centered_text((box[0] + 6, box[1] + 16, box[2] - 6, box[1] + 68), "\u65e0", none_font, muted, weight=3)
            centered_text((box[0] + 6, box[1] + 68, box[2] - 6, box[3] - 6), "\u7075\u6839", tiny_font, muted, weight=2)
            return

        attr = str(getattr(root, "attribute", "") or "\u7075")
        attr_names = {
            "\u91d1": "\u91d1\u7075\u6839",
            "\u6728": "\u6728\u7075\u6839",
            "\u6c34": "\u6c34\u7075\u6839",
            "\u706b": "\u706b\u7075\u6839",
            "\u571f": "\u571f\u7075\u6839",
            "\u96f7": "\u96f7\u7075\u6839",
            "\u51b0": "\u51b0\u7075\u6839",
            "\u98ce": "\u98ce\u7075\u6839",
            "\u6697": "\u6697\u7075\u6839",
            "\u5149": "\u5149\u7075\u6839",
            "\u5251": "\u5251\u7075\u6839",
            "\u836f": "\u836f\u7075\u6839",
            "\u7384\u9634": "\u7384\u9634\u7075\u6839",
            "\u7384\u9633": "\u7384\u9633\u7075\u6839",
            "\u7a7a": "\u7a7a\u7075\u6839",
            "\u65f6": "\u65f6\u7075\u6839",
            "\u5148\u5929\u9053\u4f53": "\u5148\u5929\u9053\u4f53",
        }
        glyph_map = {"\u5148\u5929\u9053\u4f53": "\u9053", "\u7384\u9634": "\u9634", "\u7384\u9633": "\u9633"}
        glyph = glyph_map.get(attr, attr[:1] or "\u7075")
        attr_color = ATTRIBUTE_COLORS.get(attr, getattr(root, "color", accent))
        tier = str(getattr(root, "tier", "") or "")
        grade = str(getattr(root, "grade", "") or "")
        tier_color = TIER_COLORS.get(tier, attr_color)
        root_label = f"{grade}{attr_names.get(attr, attr + '\u7075\u6839')}"

        icon_img = spirit_root_icon_image(attr)
        if icon_img is not None:
            icon_size = max(sp(48), min(x2 - x1, y2 - y1 - sp(22)))
            icon_img.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)
            px = x1 + (x2 - x1 - icon_img.width) // 2
            py = y1 + sp(1) + max(0, icon_size - icon_img.height) // 2
            image.alpha_composite(icon_img, (px, py))
        else:
            glyph_font = load_font(sp(40), bold=True)
            tw, _ = text_size(draw, glyph, glyph_font)
            draw_weighted_text(
                draw,
                (x1 + (x2 - x1 - tw) // 2, y1 + sp(5)),
                glyph,
                glyph_font,
                attr_color,
                weight=4,
                stroke_width=sp(2),
                stroke_fill=text_stroke,
            )
        label_font = fit_font(draw, root_label, max(20, x2 - x1 - sp(4)), sp(13), bold=True, min_size=sp(8))
        label_text = truncate_text(draw, root_label, label_font, max(20, x2 - x1 - sp(4)))
        lw, _ = text_size(draw, label_text, label_font)
        draw_weighted_text(
            draw,
            (x1 + (x2 - x1 - lw) // 2, y1 + sp(57)),
            label_text,
            label_font,
            tier_color,
            weight=3,
            stroke_width=sp(1),
            stroke_fill=text_stroke,
        )


    raw_slots = dict(getattr(record, "equipped_artifacts", None) or {})
    slots = artifact_slots(record)
    if getattr(record, "equipped_artifact", None) and "主手" not in slots:
        slots["主手"] = dict(record.equipped_artifact)

    def slot_item(*names: str) -> Optional[dict[str, Any]]:
        for name in names:
            item = slots.get(name) or raw_slots.get(name)
            if isinstance(item, dict):
                return item
        return None

    def item_name(item: Optional[dict[str, Any]], empty: str = "未装备") -> str:
        return reward_display_name(item) if item else empty

    main_item = slot_item("主手", "武器")
    off_item = slot_item("副手", "护手")
    armor_item = slot_item("护甲", "护盾", "盾", "甲")
    main_weapon = item_name(main_item)
    off_weapon = item_name(off_item)
    armor = item_name(armor_item)
    life_artifact = str(summary.get("life_artifact") or "\u672a\u796d\u70bc")
    talisman = str(summary.get("talisman") or "未装备")
    method = str(summary.get("method") or "\u672a\u53c2\u609f")
    array = str(summary.get("array") or "\u672a\u5e03\u7f6e")
    puppet = str(summary.get("puppet") or "\u672a\u542f\u7528")
    plant = str(summary.get("plant") or "\u672a\u683d\u79cd")
    immortal_seed = str(summary.get("immortal_seed") or "未装备")
    mana_label = str(summary.get("mana_label") or "\u7075\u529b")
    nickname_text = nickname or f"QQ {record.user_id}"

    draw_region(layout["title"], fill=(232, 245, 250, 78), radius=14)
    draw_weighted_text(draw, (sp(274), sp(76)), "\u5386\u7ec3\u9762\u677f", title_font, dark, weight=4, stroke_width=sp(2), stroke_fill=strong_stroke)
    top_line = f"{nickname_text} \u00b7 {summary['realm']} \u00b7 {summary['realm_quality']}"
    panel_clamped(top_line, (sp(274), sp(121)), subtitle_font, muted, max(20, sp(500)), max_lines=1, line_gap=0, weight=3)
    power_text = f"\u6218\u529b {summary['power']}"
    mana_text = f"{mana_label} {summary['mana']}"
    power_font = fit_font(draw, power_text, sp(220), sp(30), bold=True, min_size=sp(20))
    draw_weighted_text(draw, (sp(760), sp(82)), power_text, power_font, accent, weight=4, stroke_width=sp(2), stroke_fill=strong_stroke)
    panel_text((sp(760), sp(120)), mana_text, small_font, gold, weight=3)

    item_slot(layout["left_square"], "主手", main_weapon, "artifact", accent, item=main_item)
    round_slot(layout["left_round"], "副手", off_weapon, "artifact", accent, item=off_item)
    item_slot(layout["right_square"], "功法", method, "method", accent, item=record.equipped_method)
    round_slot(layout["right_round"], "护甲", armor, "artifact", accent, item=armor_item, icon_dx=-5)

    life_item = record.life_artifact
    life_value = reward_display_name(life_item) if life_item else ""
    x1, y1, x2, y2 = draw_region(layout["center_square"], fill=(255, 245, 232, 96), radius=14)
    if life_item:
        paste_generated_icon((x1 + sp(27), y1 + sp(8), x2 - sp(27), y1 + sp(58)), item=life_item, name=life_value, category="\u7075\u5668", fallback_icon="artifact")
        life_display = top_slot_display_value(life_item, life_value)
        draw_slot_value(life_display, (x1 + sp(4), y1 + sp(61), x2 - sp(4), y2 - sp(3)), top_slot_color(life_item, accent), 13, max_lines=2)
    else:
        none_font = load_font(sp(30), bold=True)
        centered_text((layout["center_square"][0] + 6, layout["center_square"][1] + 18, layout["center_square"][2] - 6, layout["center_square"][1] + 68), "无", none_font, muted, weight=3)
        centered_text((layout["center_square"][0] + 6, layout["center_square"][1] + 68, layout["center_square"][2] - 6, layout["center_square"][3] - 6), "\u672c\u547d", tiny_font, muted, weight=2)

    special_names = list(summary.get("special_abilities") or [])
    round_slot(layout["badge_1"], "\u9635\u76d8", f"{summary['array_multiplier']:.1f}x", "array", jade, item=record.equipped_array)
    round_slot(layout["badge_2"], "\u5080\u5121", f"+{summary['puppet_power']}", "puppet", jade, item=record.equipped_puppet)
    root_badge(layout["badge_3"])
    round_slot(layout["badge_4"], "\u7b26\u7b93", f"+{summary['talisman_power']}", "talisman", danger, item=record.equipped_talisman)
    round_slot(layout["badge_5"], "\u4ed9\u79cd", f"+{summary['immortal_seed_power']}", "realm", gold, item=record.equipped_immortal_seed)

    slot_text(
        layout["summary"],
        "",
        f"\u8def\u7ebf\uff1a{summary['route']}\u3000\u8eab\u4efd\uff1a{summary['identity']}\n\u79d8\u5883\uff1a{summary['mystic_realm']}\u3000\u795e\u901a\uff1a{len(special_names)}\u9879\u3000\u4f20\u627f\u6750\u6599\uff1a{summary['special_ability_materials']}\u4efd",
        icon="adventure",
        lines=2,
        fill=veil_deep,
        label_color=muted,
        value_color=ink,
    )


    ability_entries: list[tuple[str, Any, str, str]] = []
    for ability in special_names[:7]:
        ability_entries.append((str(ability), {"name": str(ability), "category": "\u7279\u6b8a\u80fd\u529b"}, "power", "\u7279\u6b8a\u80fd\u529b"))
    if not ability_entries:
        ability_entries.append(("\u6682\u65e0\u795e\u901a", None, "power", ""))

    realm_entries: list[tuple[str, Any, str, str]] = []
    marks = dict(getattr(record, "realm_marks", None) or {})
    for realm_index in range(2, 9):
        realm_name = REALMS[realm_index] if realm_index < len(REALMS) else f"\u7b2c{realm_index}\u5883"
        if realm_index <= int(getattr(record, "realm_index", 0) or 0):
            mark = marks.get(str(realm_index))
            if not mark and realm_index == 2:
                mark = getattr(record, "foundation_type", None)
            label = compact_realm_quality(mark or "\u672a\u5b9a\u54c1\u76f8")
        else:
            label = f"{realm_name}\u00b7\u7a7a"
        realm_entries.append((label, None, "realm", "realm_quality"))

    boss_limit = 4 + max(0, int(getattr(record, "mystic_boss_daily_bonus", 0) or 0))
    boss_used = max(0, int(getattr(record, "mystic_boss_daily_attempts", 0) or 0))
    boss_left = max(0, boss_limit - boss_used)
    resource_entries_text = [
        ("\u7075\u77f3\u50a8\u5907", str(summary.get("spirit_stones_text") or spirit_stone_text(getattr(record, "spirit_stones", 0))), "bag"),
        ("\u7cbe\u7eaf\u7075\u6db2", f"{int(getattr(record, 'spirit_liquid', 0) or 0)}", "curio"),
        ("BOSS\u6311\u6218", f"{boss_left}/{boss_limit}", "duel"),
    ]

    icon_strip(layout["row_1"], "\u795e\u901a", ability_entries)
    icon_strip(layout["row_2"], "\u5883\u754c", realm_entries)
    resource_strip(layout["row_3"], "\u8d44\u6e90", resource_entries_text)

    command_slot(layout["cmd_1"], "\u7075\u5668", "\u88c5\u5907\u7075\u5668", "artifact")
    command_slot(layout["cmd_2"], "\u529f\u6cd5", "\u53c2\u609f\u529f\u6cd5", "method")
    command_slot(layout["cmd_3"], "\u9635\u76d8", "\u5e03\u7f6e\u9635\u76d8", "array")
    command_slot(layout["cmd_4"], "\u7b26\u7b93", "\u88c5\u5907\u7b26\u7b93", "talisman")
    command_slot(layout["cmd_5"], "\u5080\u5121", "\u5524\u9192\u5080\u5121", "puppet")
    command_slot(layout["cmd_6"], "\u4ea4\u6613", "\u4e07\u5b9d\u697c", "bag")

    footer_box = draw_region(layout["footer"], fill=(236, 246, 221, 88), radius=14)
    footer = "\u5e38\u7528\uff1a\u88c5\u5907\u7075\u5668 1 \u4e3b\u624b / \u53c2\u609f\u529f\u6cd5 1 / \u5e03\u7f6e\u9635\u76d8 1 / \u88c5\u5907\u7b26\u7b93 1 / \u6218\u529b\u699c / \u4ea4\u6613\u5217\u8868"
    panel_clamped(footer, (footer_box[0] + sp(22), footer_box[1] + sp(22)), small_font, dark, max(20, footer_box[2] - footer_box[0] - sp(44)), max_lines=1, line_gap=0, weight=3)
    return png_bytes(image)

def render_text_panel(
    title: str,
    content: str | list[str],
    subtitle: str = "",
    icon: str = "scroll",
    accent: str = "#3589d8",
    width: int = 900,
    footer: str = "",
) -> bytes:
    raw_lines = content.splitlines() if isinstance(content, str) else list(content)
    width = max(width, 1180)
    measure = Image.new("RGBA", (width, 120), (0, 0, 0, 0))
    measure_draw = ImageDraw.Draw(measure)
    title_font = fit_font(measure_draw, title, width - 280, 64, bold=True, min_size=42)
    subtitle_font = load_font(28, bold=True)
    body_font = load_font(34, bold=True)
    small_font = load_font(26, bold=True)
    section_font = load_font(32, bold=True)
    max_text_width = width - 260

    layout: list[tuple[str, str, list[str], str, int, int]] = []
    content_height = 0
    for raw in raw_lines or [""]:
        line = str(raw).strip()
        if not line:
            block_h = 18
            gap = 0
            layout.append(("space", "", [""], "scroll", block_h, gap))
            content_height += block_h + gap
            continue
        if line.startswith("\u3010") and line.endswith("\u3011"):
            wrapped = wrap_panel_text(measure_draw, line, section_font, max_text_width)
            block_h = 54 + max(0, len(wrapped) - 1) * 34
            gap = 14
            layout.append(("section", line, wrapped, icon_key_from_text(line, icon), block_h, gap))
            content_height += block_h + gap
            continue
        row_icon = icon_key_from_text(line, icon)
        prefix_width = 86
        wrapped = wrap_panel_text(measure_draw, line, body_font, max_text_width - prefix_width)
        block_h = max(62, 42 * len(wrapped) + 20)
        gap = 12
        layout.append(("row", line, wrapped, row_icon, block_h, gap))
        content_height += block_h + gap

    content_start_y = 268
    content_bottom_padding = 56
    footer_reserved = 60 if footer else 0
    card_outer_bottom = 58
    height = max(520, content_start_y + content_height + footer_reserved + content_bottom_padding + card_outer_bottom)
    image = make_xiuxian_background(width, height, accent)
    draw = ImageDraw.Draw(image)
    draw_card(image, (58, 62, width - 58, height - 58))

    draw_panel_icon(draw, (104, 112, 208, 216), icon, accent)
    draw_weighted_text(draw, (238, 112), title, title_font, "#172033", weight=4)
    if subtitle:
        subtitle_fit = fit_font(draw, subtitle, width - 300, 30, bold=True, min_size=22)
        draw_weighted_text(draw, (242, 184), subtitle, subtitle_fit, "#6b7280", weight=2)

    y = content_start_y
    left = 104
    right = width - 104
    for kind, raw, wrapped, row_icon, block_h, gap in layout:
        if kind == "space":
            y += block_h + gap
            continue
        if kind == "section":
            draw.rounded_rectangle((left, y, right, y + block_h), radius=20, fill=(252, 247, 232, 232), outline="#eadfca", width=2)
            draw_panel_icon(draw, (left + 16, y + 10, left + 56, y + 50), row_icon, accent)
            text_y = y + 12
            for part in wrapped:
                draw_weighted_text(draw, (left + 74, text_y), part, section_font, "#172033", weight=3)
                text_y += 34
            y += block_h + gap
            continue
        row_h = block_h
        draw.rounded_rectangle((left, y, right, y + row_h), radius=18, fill=(255, 255, 255, 222), outline="#eee2ca", width=2)
        draw_panel_icon(draw, (left + 16, y + 12, left + 58, y + 54), row_icon, accent)
        text_y = y + 14
        for part in wrapped:
            draw_weighted_text(draw, (left + 78, text_y), part, body_font, "#344054", weight=2)
            text_y += 42
        y += row_h + gap

    if footer:
        footer_font = fit_font(draw, footer, width - 208, 26, bold=True, min_size=18)
        draw_weighted_text(draw, (104, height - 108), footer, footer_font, "#667085", weight=1)
    return png_bytes(image)
