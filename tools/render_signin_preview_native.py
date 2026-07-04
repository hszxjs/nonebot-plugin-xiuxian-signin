from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BG_PATH = ROOT / "assets/panel_backgrounds/signin_background.png"
OLD_PATH = Path(
    r"C:\Users\hszxjs\Documents\Tencent Files\3305167706\nt_qq\nt_data\Pic\2026-06\Ori\6013980e9e6913183936ee99485ced48.png"
)
FONT_PATH = ROOT / "assets/fonts/HarmonyOS_Sans_SC.ttf"
OUT_DIR = ROOT / "build/previews"
OUT_PATH = OUT_DIR / "signin_preview_native_bg_v2.png"

ACCENT = "#7b5cf0"
CYAN = "#35bdc8"
DARK = "#172033"
MUTED = "#647084"
GOLD = "#93702d"
DANGER = "#9b3f1e"


def load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def draw_weighted_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    weight: int = 1,
) -> None:
    x, y = xy
    offsets = [(0, 0)]
    if weight >= 2:
        offsets += [(1, 0), (0, 1)]
    if weight >= 3:
        offsets += [(-1, 0), (0, -1)]
    for ox, oy in offsets:
        draw.text((x + ox, y + oy), text, font=font, fill=fill)


def fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    start_size: int,
    min_size: int = 14,
) -> ImageFont.ImageFont:
    for size in range(start_size, min_size - 1, -2):
        font = load_font(size)
        if text_size(draw, text, font)[0] <= max_width:
            return font
    return load_font(min_size)


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        trial = current + char
        if text_size(draw, trial, font)[0] <= max_width or not current:
            current = trial
            continue
        lines.append(current)
        current = char
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines]


def draw_clamped(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    start_size: int,
    color: str,
    weight: int = 2,
    max_lines: int = 1,
    line_gap: int = 4,
    min_size: int = 14,
) -> None:
    x1, y1, x2, y2 = box
    max_width = x2 - x1
    max_height = y2 - y1
    for size in range(start_size, min_size - 1, -2):
        font = load_font(size)
        lines = wrap_text(draw, text, font, max_width, max_lines)
        line_height = text_size(draw, "修", font)[1] + line_gap
        total_height = line_height * len(lines) - line_gap
        if total_height <= max_height:
            y = y1
            for line in lines:
                draw_weighted_text(draw, (x1, y), line, font, color, weight)
                y += line_height
            return
    font = load_font(min_size)
    y = y1
    for line in wrap_text(draw, text, font, max_width, max_lines):
        draw_weighted_text(draw, (x1, y), line, font, color, weight)
        y += text_size(draw, "修", font)[1] + line_gap


def old_avatar_inner() -> Image.Image:
    old = Image.open(OLD_PATH).convert("RGBA")
    return old.crop((143, 160, 330, 347)).resize((164, 164), Image.Resampling.LANCZOS)


def avatar_for_generated_frame() -> Image.Image:
    avatar = old_avatar_inner()
    mask = Image.new("L", avatar.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, avatar.width - 1, avatar.height - 1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.45))
    avatar.putalpha(mask)
    return avatar


def draw_field(
    draw: ImageDraw.ImageDraw,
    label: str,
    value: str,
    label_box: tuple[int, int, int, int],
    value_box: tuple[int, int, int, int],
    value_color: str = ACCENT,
    value_size: int = 24,
    value_lines: int = 1,
) -> None:
    draw_clamped(draw, label_box, label, 18, MUTED, weight=2, max_lines=1, min_size=14)
    draw_clamped(draw, value_box, value, value_size, value_color, weight=2, max_lines=value_lines, min_size=13)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.open(BG_PATH).convert("RGBA")
    draw = ImageDraw.Draw(image)

    avatar = avatar_for_generated_frame()
    # Native generated background coordinates. This centers the avatar inside the existing oval frame.
    image.alpha_composite(avatar, (128, 134))

    # Personal information goes only in the blank landscape area to the right of the avatar.
    draw_clamped(draw, (340, 112, 820, 168), "今日已完成签到", 42, DARK, weight=3)
    draw_clamped(draw, (342, 178, 820, 222), "落雨・乱心思", 31, "#4b5565", weight=2)
    draw_clamped(draw, (342, 230, 815, 266), "宿主今日气息稳定，无需重复闭关", 20, GOLD, weight=2)

    # Root / realm broad frame.
    draw_field(
        draw,
        "灵根",
        "变异灵根极品雷灵根 | 由火+水先天异变",
        (130, 354, 270, 384),
        (130, 390, 760, 454),
        ACCENT,
        28,
        2,
    )
    draw_field(
        draw,
        "当前境界",
        "炼虚期巅峰",
        (820, 354, 1020, 384),
        (820, 392, 1125, 452),
        DARK,
        34,
        1,
    )
    draw_field(
        draw,
        "灵根精纯度",
        "雷灵根96%（火96%+水96%） / 后天：金88% / 木91% / 土91%",
        (146, 505, 305, 532),
        (328, 500, 1080, 552),
        ACCENT,
        18,
        2,
    )

    # Stats boxes.
    draw_field(draw, "签到次数", "5 次", (130, 630, 320, 660), (130, 675, 465, 730), DARK, 36, 1)
    draw_field(draw, "累计修为", "9398 点", (690, 630, 900, 660), (690, 675, 1085, 730), ACCENT, 36, 1)

    # Adventure status frame. Three columns, three rows, each value clamped inside its cell.
    draw_clamped(draw, (125, 804, 380, 842), "历练状态", 25, DARK, weight=3)
    columns = [(130, 440), (470, 780), (810, 1120)]
    rows = [(870, 936), (966, 1032), (1062, 1128)]
    entries = [
        ("灵器", "[天阶极品灵器 星阙断岳剑]"),
        ("功法", "[天阶上品功法 离火炼界篇]"),
        ("阵盘", "[玄阶极品阵盘 小五行聚灵盘]"),
        ("阵法熟练", "熟练度 610/900 ・ 7.1x"),
        ("境界品相", "洞虚道体"),
        ("瓶颈", "需 合道残章 / 合体丹 / 法身合契符"),
        ("路线", "炼丹师"),
        ("身份令牌", "天机阁弟子"),
        ("后天灵根", "金灵根 / +2条"),
    ]
    for index, (label, value) in enumerate(entries):
        col = index % 3
        row = index // 3
        x1, x2 = columns[col]
        y1, y2 = rows[row]
        draw_field(
            draw,
            label,
            value,
            (x1, y1, x2, y1 + 24),
            (x1, y1 + 28, x2, y2),
            DANGER if label == "瓶颈" else ACCENT,
            17,
            2,
        )

    # No progress bar in this preview. Keep only progress text inside the bottom-right frame.
    draw_clamped(draw, (112, 1165, 330, 1205), "经验进度", 25, DARK, weight=3)
    draw_clamped(draw, (820, 1165, 1116, 1205), "4736/4736 ・ 巅峰", 22, DARK, weight=2)
    draw_clamped(draw, (112, 1210, 520, 1240), "明日再来，灵气自会积蓄", 17, MUTED, weight=1)

    image.save(OUT_PATH)
    print(OUT_PATH)
    print(image.size)


if __name__ == "__main__":
    main()
