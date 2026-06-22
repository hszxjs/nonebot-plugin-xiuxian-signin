from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .domain import (
    ATTRIBUTE_COLORS,
    Root,
    SigninResult,
    UserRecord,
    array_multiplier,
    battle_power,
    breakthrough_required_text,
    hehuan_remaining_text,
    is_breakthrough_bottleneck,
    reward_display_name,
    spirit_stone_text,
    tianji_status_text,
    reward_signature,
)

Color = tuple[int, int, int]
BUNDLED_FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "NotoSansSC-VF.ttf"

TIER_COLORS = {
    "天阶": "#f0c85a",
    "地阶": "#70bf82",
    "玄阶": "#6599e8",
    "黄阶": "#b9894d",
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
) -> None:
    offsets = [(0, 0)]
    if weight >= 2:
        offsets.append((1, 0))
    if weight >= 3:
        offsets.extend([(0, 1), (1, 1)])
    if weight >= 4:
        offsets.extend([(-1, 0), (0, -1)])
    for dx, dy in offsets:
        draw.text((xy[0] + dx, xy[1] + dy), text, font=font, fill=fill)


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
    root = record.root or Root("凡品", 0, "下品", 0, "土")
    accent = ATTRIBUTE_COLORS.get(root.attribute, "#3589d8")
    width = max(width, 1500)
    height = 1900
    image = make_xiuxian_background(width, height, accent)
    draw = ImageDraw.Draw(image)

    title_font = load_font(90, bold=True)
    subtitle_font = fit_font(draw, nickname or f"QQ {record.user_id}", 900, 70, bold=True, min_size=52)
    normal_font = load_font(58, bold=True)
    small_font = load_font(36, bold=True)
    label_font = load_font(42, bold=True)
    root_text = record.root_summary
    strong_font = fit_font(draw, root_text, 900, 78, bold=True, min_size=52)
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

    root_box = (132, 430, width - 132, 690)
    draw.rounded_rectangle(root_box, radius=42, fill=(252, 247, 232, 238), outline="#ead5a7", width=5)
    draw_weighted_text(draw, (184, 478), "灵根", label_font, "#6b7280", weight=2)
    draw_weighted_text(draw, (184, 550), root_text, strong_font, accent, weight=4)
    draw_weighted_text(draw, (width - 590, 478), "当前境界", label_font, "#6b7280", weight=2)
    draw_weighted_text(draw, (width - 590, 550), record.realm, realm_font, "#172033", weight=4)

    stats_top = 750
    stat_gap = 50
    stat_width = (width - 264 - stat_gap) // 2
    for index, (label, value, color) in enumerate(
        [("签到次数", f"{record.sign_count} 次", "#172033"), ("累计修为", f"{record.total_exp} 点", accent)]
    ):
        left = 132 + index * (stat_width + stat_gap)
        draw.rounded_rectangle((left, stats_top, left + stat_width, stats_top + 220), radius=42, fill=(255, 255, 255, 238), outline="#eadfca", width=5)
        draw_weighted_text(draw, (left + 54, stats_top + 38), label, label_font, "#667085", weight=2)
        draw_weighted_text(draw, (left + 54, stats_top + 108), value, number_font, color, weight=4)

    info_top = 1030
    info_box = (132, info_top, width - 132, info_top + 430)
    draw.rounded_rectangle(info_box, radius=42, fill=(255, 255, 255, 236), outline="#eadfca", width=5)
    draw_weighted_text(draw, (184, info_top + 34), "历练状态", label_font, "#172033", weight=3)

    col_gap = 34
    inner_left = 184
    inner_width = width - 368
    col_width = (inner_width - col_gap * 2) // 3
    row1_y = info_top + 96
    row2_y = info_top + 198
    row3_y = info_top + 300
    array_status = array_proficiency_text(record)
    bottleneck = is_breakthrough_bottleneck(record)
    power_label = "瓶颈" if bottleneck else "战力"
    power_value = f"需 {breakthrough_required_text(record)}" if bottleneck else str(battle_power(record))
    info_rows = [
        ("灵器", equipped_title(record.equipped_artifact, "未装备灵器"), row1_y),
        ("功法", equipped_title(record.equipped_method, "未参悟功法"), row1_y),
        ("阵盘", equipped_title(record.equipped_array, "未布置阵盘"), row1_y),
        ("阵法熟练", array_status, row2_y),
        ("境界品相", record.realm_quality, row2_y),
        (power_label, power_value, row2_y),
        ("路线", record.route_summary, row3_y),
        ("身份令牌", record.identity_summary, row3_y),
        ("特殊次数", f"天机{tianji_status_text(record)} / 双修{hehuan_remaining_text(record)}", row3_y),
    ]
    for idx, (label, value, row_y) in enumerate(info_rows):
        col = idx % 3
        x = inner_left + col * (col_width + col_gap)
        value_color = "#9a3412" if label == "瓶颈" else accent
        draw_info_row(draw, label, value, (x, row_y), col_width, value_color)

    required = record.progress_required
    ratio = record.realm_exp / max(1, required)
    progress_top = 1560
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
    "签到": "signin",
    "灵根": "realm",
    "修为": "realm",
    "境界": "realm",
    "突破": "breakthrough",
    "垂钓": "fishing",
    "排行": "rank",
    "榜": "rank",
    "战力": "power",
    "切磋": "duel",
    "PK": "duel",
    "pk": "duel",
    "灵器": "artifact",
    "功法": "method",
    "阵盘": "array",
    "阵法": "array",
    "傀儡": "puppet",
    "灵植": "plant",
    "丹药": "pill",
    "符箓": "talisman",
    "灵石": "stone",
    "灵食": "food",
    "奇物": "curio",
    "杂物": "misc",
    "背包": "bag",
    "道具": "bag",
    "秘境": "mystic",
    "历练": "adventure",
    "警": "warning",
    "错": "warning",
    "仙缘": "curio",
    "灵材": "stone",
    "奖励": "bag",
    "入口": "mystic",
    "状态": "realm",
    "禁修": "warning",
    "失败": "warning",
    "路线": "token",
    "身份": "token",
    "令牌": "token",
    "任务": "task",
    "商店": "shop",
    "坊市": "shop",
    "炼丹": "alchemy",
    "丹方": "alchemy",
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

    layout: list[tuple[str, str, list[str], str]] = []
    content_height = 0
    for raw in raw_lines or [""]:
        line = str(raw).strip()
        if not line:
            layout.append(("space", "", [""], "scroll"))
            content_height += 18
            continue
        if line.startswith("【") and line.endswith("】"):
            wrapped = wrap_panel_text(measure_draw, line, section_font, max_text_width)
            layout.append(("section", line, wrapped, icon_key_from_text(line, icon)))
            content_height += 62 + max(0, len(wrapped) - 1) * 36
            continue
        row_icon = icon_key_from_text(line, icon)
        prefix_width = 86
        wrapped = wrap_panel_text(measure_draw, line, body_font, max_text_width - prefix_width)
        layout.append(("row", line, wrapped, row_icon))
        content_height += max(68, 42 * len(wrapped) + 24)

    footer_height = 52 if footer else 0
    height = max(520, 230 + content_height + footer_height + 110)
    image = make_xiuxian_background(width, height, accent)
    draw = ImageDraw.Draw(image)
    draw_card(image, (58, 62, width - 58, height - 58))

    draw_panel_icon(draw, (104, 112, 208, 216), icon, accent)
    draw_weighted_text(draw, (238, 112), title, title_font, "#172033", weight=4)
    if subtitle:
        subtitle_fit = fit_font(draw, subtitle, width - 300, 30, bold=True, min_size=22)
        draw_weighted_text(draw, (242, 184), subtitle, subtitle_fit, "#6b7280", weight=2)

    y = 268
    left = 104
    right = width - 104
    for kind, raw, wrapped, row_icon in layout:
        if kind == "space":
            y += 18
            continue
        if kind == "section":
            block_h = 54 + max(0, len(wrapped) - 1) * 34
            draw.rounded_rectangle((left, y, right, y + block_h), radius=20, fill=(252, 247, 232, 232), outline="#eadfca", width=2)
            draw_panel_icon(draw, (left + 16, y + 10, left + 56, y + 50), row_icon, accent)
            text_y = y + 12
            for part in wrapped:
                draw_weighted_text(draw, (left + 74, text_y), part, section_font, "#172033", weight=3)
                text_y += 34
            y += block_h + 14
            continue
        row_h = max(62, 42 * len(wrapped) + 20)
        draw.rounded_rectangle((left, y, right, y + row_h), radius=18, fill=(255, 255, 255, 222), outline="#eee2ca", width=2)
        draw_panel_icon(draw, (left + 16, y + 12, left + 58, y + 54), row_icon, accent)
        text_y = y + 14
        for part in wrapped:
            draw_weighted_text(draw, (left + 78, text_y), part, body_font, "#344054", weight=2)
            text_y += 42
        y += row_h + 12

    if footer:
        footer_font = fit_font(draw, footer, width - 208, 26, bold=True, min_size=18)
        draw_weighted_text(draw, (104, height - 108), footer, footer_font, "#667085", weight=1)
    return png_bytes(image)

