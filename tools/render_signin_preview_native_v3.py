from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BG_PATH = ROOT / "assets/panel_backgrounds/signin_background.png"
OLD_PATH = Path(
    r"C:\Users\hszxjs\Documents\Tencent Files\3305167706\nt_qq\nt_data\Pic\2026-06\Ori\6013980e9e6913183936ee99485ced48.png"
)
FONT_PATH = ROOT / "assets/fonts/NotoSansSC-VF.ttf"
OUT_DIR = ROOT / "assets/panel_previews"
OUT_PATH = OUT_DIR / "signin_preview_native_bg_v3.png"

ACCENT = "#7b5cf0"
DARK = "#172033"
MUTED = "#647084"
GOLD = "#93702d"
DANGER = "#9b3f1e"

TEXT = {
    "title": "\u4eca\u65e5\u5df2\u5b8c\u6210\u7b7e\u5230",
    "name": "\u843d\u96e8\u30fb\u4e71\u5fc3\u601d",
    "hint": "\u5bbf\u4e3b\u4eca\u65e5\u6c14\u606f\u7a33\u5b9a\uff0c\u65e0\u9700\u91cd\u590d\u95ed\u5173",
    "root_label": "\u7075\u6839",
    "root_value": "\u53d8\u5f02\u7075\u6839\u6781\u54c1\u96f7\u7075\u6839 | \u7531\u706b+\u6c34\u5148\u5929\u5f02\u53d8",
    "realm_label": "\u5f53\u524d\u5883\u754c",
    "realm_value": "\u70bc\u865a\u671f\u5dc5\u5cf0",
    "purity_label": "\u7075\u6839\u7cbe\u7eaf\u5ea6",
    "purity_value": "\u96f7\u7075\u683996%\uff08\u706b96%+\u6c3496%\uff09 / \u540e\u5929\uff1a\u91d188% / \u672891% / \u571f91%",
    "sign_label": "\u7b7e\u5230\u6b21\u6570",
    "sign_value": "5 \u6b21",
    "total_label": "\u7d2f\u8ba1\u4fee\u4e3a",
    "total_value": "9398 \u70b9",
    "progress_label": "\u7ecf\u9a8c\u8fdb\u5ea6",
    "progress_value": "4736/4736 \u30fb \u5dc5\u5cf0",
    "footer": "\u660e\u65e5\u518d\u6765\uff0c\u7075\u6c14\u81ea\u4f1a\u79ef\u84c4",
}

GRID_ITEMS = [
    ("\u7075\u5668", "[\u5929\u9636\u6781\u54c1\u7075\u5668 \u592a\u865a\u65a9\u661f\u5251]"),
    ("\u529f\u6cd5", "[\u5929\u9636\u4e0a\u54c1\u529f\u6cd5 \u79bb\u706b\u70bc\u754c\u7bc7]"),
    ("\u9635\u76d8", "[\u7384\u9636\u6781\u54c1\u9635\u76d8 \u5c0f\u4e94\u884c\u805a\u7075\u76d8]"),
    ("\u9635\u6cd5\u719f\u7ec3", "\u719f\u7ec3\u5ea6 610/900 \u30fb 7.1x"),
    ("\u5883\u754c\u54c1\u76f8", "\u6d1e\u865a\u9053\u4f53"),
    ("\u74f6\u9888", "\u9700 \u5408\u9053\u6b8b\u7ae0 / \u5408\u4f53\u4e39 / \u6cd5\u8eab\u5408\u5951\u7b26"),
    ("\u8def\u7ebf", "\u70bc\u4e39\u5e08"),
    ("\u8eab\u4efd\u4ee4\u724c", "\u5929\u673a\u9601\u5f1f\u5b50"),
    ("\u540e\u5929\u7075\u6839", "\u91d1\u7075\u6839 / +2\u6761"),
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def measure(draw: ImageDraw.ImageDraw, value: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), value, font=font)
    return box[2] - box[0], box[3] - box[1]


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    font: ImageFont.ImageFont,
    color: str,
    weight: int = 1,
) -> None:
    x, y = xy
    offsets = [(0, 0)]
    if weight >= 2:
        offsets += [(1, 0), (0, 1)]
    if weight >= 3:
        offsets += [(-1, 0), (0, -1)]
    for ox, oy in offsets:
        draw.text((x + ox, y + oy), value, font=font, fill=color)


def wrap_text(
    draw: ImageDraw.ImageDraw,
    value: str,
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in value:
        trial = current + char
        if measure(draw, trial, font)[0] <= max_width or not current:
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
    value: str,
    start_size: int,
    color: str,
    weight: int = 2,
    max_lines: int = 1,
    min_size: int = 12,
    line_gap: int = 4,
) -> None:
    x1, y1, x2, y2 = box
    max_width = x2 - x1
    max_height = y2 - y1
    for size in range(start_size, min_size - 1, -1):
        font = load_font(size)
        lines = wrap_text(draw, value, font, max_width, max_lines)
        line_h = measure(draw, "\u4fee", font)[1] + line_gap
        total_h = line_h * len(lines) - line_gap
        if total_h <= max_height:
            y = y1
            for line in lines:
                draw_text(draw, (x1, y), line, font, color, weight)
                y += line_h
            return
    font = load_font(min_size)
    y = y1
    for line in wrap_text(draw, value, font, max_width, max_lines):
        draw_text(draw, (x1, y), line, font, color, weight)
        y += measure(draw, "\u4fee", font)[1] + line_gap


def draw_field(
    draw: ImageDraw.ImageDraw,
    label: str,
    value: str,
    label_box: tuple[int, int, int, int],
    value_box: tuple[int, int, int, int],
    value_color: str = ACCENT,
    value_size: int = 22,
    value_lines: int = 1,
) -> None:
    draw_clamped(draw, label_box, label, 16, MUTED, weight=2, max_lines=1, min_size=12)
    draw_clamped(draw, value_box, value, value_size, value_color, weight=2, max_lines=value_lines, min_size=11)


def old_avatar_inner(size: int) -> Image.Image:
    old = Image.open(OLD_PATH).convert("RGBA")
    crop = old.crop((143, 160, 330, 347))
    return crop.resize((size, size), Image.Resampling.LANCZOS)


def avatar_for_frame(size: int) -> Image.Image:
    avatar = old_avatar_inner(size)
    mask = Image.new("L", avatar.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((3, 3, size - 4, size - 4), fill=255)

    # Protect the top jade ornament in the generated avatar frame.
    cut = Image.new("L", avatar.size, 0)
    cut_draw = ImageDraw.Draw(cut)
    cut_draw.ellipse((int(size * 0.34), int(-size * 0.14), int(size * 0.66), int(size * 0.16)), fill=255)

    mask_arr = bytearray(mask.tobytes())
    cut_arr = cut.tobytes()
    for index, alpha in enumerate(cut_arr):
        if alpha:
            mask_arr[index] = 0
    mask = Image.frombytes("L", avatar.size, bytes(mask_arr)).filter(ImageFilter.GaussianBlur(0.45))
    avatar.putalpha(mask)
    return avatar


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.open(BG_PATH).convert("RGBA")
    draw = ImageDraw.Draw(image)

    # Avatar: bigger and shifted to the generated circular frame center.
    avatar = avatar_for_frame(222)
    image.alpha_composite(avatar, (108, 98))

    # Header: shifted right into the blank mountain area.
    draw_clamped(draw, (430, 112, 960, 168), TEXT["title"], 42, DARK, weight=3)
    draw_clamped(draw, (432, 178, 960, 222), TEXT["name"], 31, "#4b5565", weight=2)
    draw_clamped(draw, (432, 232, 952, 266), TEXT["hint"], 20, GOLD, weight=2)

    # Root / realm: lower placement.
    draw_field(
        draw,
        TEXT["root_label"],
        TEXT["root_value"],
        (130, 390, 270, 418),
        (130, 426, 770, 490),
        ACCENT,
        28,
        2,
    )
    draw_field(
        draw,
        TEXT["realm_label"],
        TEXT["realm_value"],
        (820, 390, 1020, 418),
        (820, 426, 1128, 488),
        DARK,
        34,
        1,
    )
    draw_field(
        draw,
        TEXT["purity_label"],
        TEXT["purity_value"],
        (146, 522, 305, 548),
        (328, 516, 1080, 568),
        ACCENT,
        18,
        2,
    )

    # Stats: sign count moves right/up; total exp moves left/up.
    draw_field(draw, TEXT["sign_label"], TEXT["sign_value"], (188, 608, 380, 638), (188, 650, 500, 704), DARK, 36, 1)
    draw_field(draw, TEXT["total_label"], TEXT["total_value"], (642, 608, 850, 638), (642, 650, 1035, 704), ACCENT, 36, 1)

    # Nine-grid: remove module title; move cell content upward inside cells.
    columns = [(130, 440), (470, 780), (810, 1120)]
    rows = [(760, 824), (846, 910), (932, 996)]
    for index, (label, value) in enumerate(GRID_ITEMS):
        col = index % 3
        row = index // 3
        x1, x2 = columns[col]
        y1, y2 = rows[row]
        draw_field(
            draw,
            label,
            value,
            (x1, y1, x2, y1 + 22),
            (x1, y1 + 25, x2, y2),
            DANGER if label == "\u74f6\u9888" else ACCENT,
            17,
            2,
        )

    # Experience text sits in the green jade trough. No progress bar is drawn.
    draw_clamped(draw, (218, 1030, 420, 1065), TEXT["progress_label"], 24, DARK, weight=3)
    draw_clamped(draw, (800, 1030, 1075, 1065), TEXT["progress_value"], 21, DARK, weight=2)
    draw_clamped(draw, (470, 1073, 790, 1100), TEXT["footer"], 16, MUTED, weight=1)

    image.save(OUT_PATH)
    print(OUT_PATH)
    print(image.size)


if __name__ == "__main__":
    main()
