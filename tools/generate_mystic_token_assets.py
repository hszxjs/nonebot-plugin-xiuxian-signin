"""生成秘境令牌图标与缺少令牌提示背景图。

风格对齐:
- 图标: 128x128 RGBA,手绘写实 + 柔和光晕,玉石/令牌造型
- 背景: 冷调青灰水墨,带古老石门剪影 + 雾气,与 mystic_stone_gate.png 风格一致

输出到 assets/mystic_dungeon_ui/:
- token_normal.png        普通秘境令牌(玄阶·中品,冷青玉色)
- token_high.png          高风险秘境令牌(地阶·上品,赤金暗紫)
- no_token_background.png 缺少令牌提示背景(1254x1254,暗调水墨)
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ASSET_DIR = Path(__file__).resolve().parent.parent / "nonebot_plugin_xiuxian_signin" / "assets"
UI_DIR = ASSET_DIR / "mystic_dungeon_ui"
UI_DIR.mkdir(parents=True, exist_ok=True)

ICON_SIZE = 128
BG_SIZE = 1254


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _radial_glow(size: int, center: tuple[float, float], radius: float,
                 color: tuple[int, int, int], intensity: float = 1.0) -> Image.Image:
    """生成径向光晕图层。"""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = layer.load()
    cx, cy = center
    for y in range(size):
        for x in range(size):
            dist = math.hypot(x - cx, y - cy)
            if dist < radius:
                t = 1.0 - dist / radius
                alpha = int(255 * intensity * t * t)
                px[x, y] = (*color, alpha)
    return layer


def _token_shape_mask(body_left, body_top, body_right, body_bottom) -> Image.Image:
    """生成令牌牌身形状的 mask(圆角矩形 + 顶部拱形)。"""
    mask = Image.new("L", (ICON_SIZE, ICON_SIZE), 0)
    mdraw = ImageDraw.Draw(mask)
    # 主体圆角矩形
    mdraw.rounded_rectangle(
        [body_left, body_top, body_right, body_bottom],
        radius=14, fill=255,
    )
    # 顶部拱形(让顶部呈圆弧)
    arch_h = 20
    mdraw.pieslice(
        [body_left - 2, body_top - arch_h, body_right + 2, body_top + arch_h],
        180, 360, fill=255,
    )
    return mask


def _draw_jade_token(
    base: Image.Image,
    *,
    body_color: tuple[int, int, int],
    edge_color: tuple[int, int, int],
    glow_color: tuple[int, int, int],
    rune_color: tuple[int, int, int],
) -> None:
    """在 128x128 画布上绘制一枚玉牌令牌(分层合成,清晰可靠)。"""
    cx, cy = 64, 64
    body_left, body_top = cx - 28, cy - 34
    body_right, body_bottom = cx + 28, cy + 38

    # 层 0:外层光晕(底)
    glow = _radial_glow(ICON_SIZE, (cx, cy), 58.0, glow_color, intensity=0.55)
    base.alpha_composite(glow)

    # 层 1:牌身渐变(按形状 mask 合成)
    body_full = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(body_full)
    body_height = body_bottom - body_top
    for i in range(body_height + 30):  # 多画一些覆盖拱形区域
        t = min(i / max(1, body_height), 1.0)
        c = _lerp(
            _lerp(body_color, (255, 255, 255), 0.28),
            _lerp(body_color, edge_color, 0.45),
            t,
        )
        bdraw.line(
            [(body_left - 4, body_top - 20 + i), (body_right + 4, body_top - 20 + i)],
            fill=(*c, 255),
        )
    shape_mask = _token_shape_mask(body_left, body_top, body_right, body_bottom)
    body_shaped = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    body_shaped.paste(body_full, (0, 0), shape_mask)
    base.alpha_composite(body_shaped)

    draw = ImageDraw.Draw(base)

    # 层 2:牌身边缘描边(金/铜色)
    edge_layer = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    edraw = ImageDraw.Draw(edge_layer)
    edraw.rounded_rectangle(
        [body_left, body_top, body_right, body_bottom],
        radius=14, outline=edge_color, width=3,
    )
    edraw.arc(
        [body_left - 2, body_top - 20, body_right + 2, body_top + 20],
        180, 360, fill=edge_color, width=3,
    )
    base.alpha_composite(edge_layer)
    draw = ImageDraw.Draw(base)

    # 层 3:顶部穿孔 + 系绳(令牌特征)
    draw.ellipse([cx - 5, body_top - 12, cx + 5, body_top - 2], fill=(40, 30, 25, 255))
    ribbon_pts = [
        (cx - 3, body_top - 8),
        (cx - 10, body_top - 2),
        (cx - 6, body_top + 6),
        (cx, body_top),
    ]
    draw.line(ribbon_pts, fill=(*edge_color, 255), width=3, joint="curve")

    # 层 4:中央符文(菱形 + 点,简化"秘"字意象)
    rune_size = 14
    rune_cx, rune_cy = cx, cy + 2
    rune_pts = [
        (rune_cx, rune_cy - rune_size),
        (rune_cx + rune_size, rune_cy),
        (rune_cx, rune_cy + rune_size),
        (rune_cx - rune_size, rune_cy),
    ]
    draw.line(rune_pts + [rune_pts[0]], fill=rune_color, width=2)
    draw.ellipse([rune_cx - 2, rune_cy - 2, rune_cx + 2, rune_cy + 2], fill=rune_color)

    # 底部纹饰(两道横纹)
    for offset in (-10, -4):
        draw.line(
            [(body_left + 8, rune_cy + rune_size + 8 + offset),
             (body_right - 8, rune_cy + rune_size + 8 + offset)],
            fill=(*_lerp(rune_color, edge_color, 0.4), 200), width=1,
        )

    # 层 5:顶部高光(玉石质感)
    highlight = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(highlight)
    hdraw.ellipse(
        [cx - 16, body_top + 4, cx + 6, body_top + 14],
        fill=(255, 255, 255, 70),
    )
    highlight = highlight.filter(ImageFilter.GaussianBlur(radius=2))
    base.alpha_composite(highlight)


def make_token_normal() -> None:
    """普通秘境令牌:玄阶·中品,冷青玉色。"""
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    _draw_jade_token(
        img,
        body_color=(90, 150, 160),      # 冷青玉
        edge_color=(180, 140, 70),       # 古铜边
        glow_color=(120, 200, 210),      # 青色光晕
        rune_color=(40, 80, 90),         # 深青符文
    )
    img.save(UI_DIR / "token_normal.png")
    print(f"  ✓ token_normal.png ({ICON_SIZE}x{ICON_SIZE})")


def make_token_high() -> None:
    """高风险秘境令牌:地阶·上品,赤金暗紫。"""
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    _draw_jade_token(
        img,
        body_color=(150, 80, 110),       # 暗紫红玉
        edge_color=(230, 180, 70),       # 赤金边
        glow_color=(220, 120, 90),       # 赤金光晕
        rune_color=(70, 25, 45),         # 深紫符文
    )
    img.save(UI_DIR / "token_high.png")
    print(f"  ✓ token_high.png ({ICON_SIZE}x{ICON_SIZE})")


def _draw_stone_gate_silhouette(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """绘制远处古老石门剪影(水墨意境)。"""
    cx = w // 2
    # 石门基座
    base_top = int(h * 0.45)
    base_bottom = int(h * 0.82)
    pillar_w = int(w * 0.08)
    # 左柱
    draw.rectangle(
        [cx - int(w * 0.18), base_top, cx - int(w * 0.18) + pillar_w, base_bottom],
        fill=(28, 40, 44, 240),
    )
    # 右柱
    draw.rectangle(
        [cx + int(w * 0.18) - pillar_w, base_top, cx + int(w * 0.18), base_bottom],
        fill=(28, 40, 44, 240),
    )
    # 横梁
    draw.rectangle(
        [cx - int(w * 0.20), base_top - int(h * 0.04),
         cx + int(w * 0.20), base_top + int(h * 0.03)],
        fill=(24, 36, 40, 245),
    )
    # 门洞(透出冷光/雾)
    gate_left = cx - int(w * 0.18) + pillar_w
    gate_right = cx + int(w * 0.18) - pillar_w
    gate_top = base_top + int(h * 0.03)
    gate_bottom = base_bottom
    # 门洞内的冷光渐变
    for i in range(gate_bottom - gate_top):
        t = i / max(1, gate_bottom - gate_top)
        c = _lerp((180, 200, 205), (40, 60, 65), t)
        draw.line(
            [(gate_left, gate_top + i), (gate_right, gate_top + i)],
            fill=(*c, int(120 * (1 - t * 0.5))),
        )
    # 顶部拱形(门洞)
    draw.pieslice(
        [gate_left, gate_top - (gate_right - gate_left) // 2,
         gate_right, gate_top + (gate_right - gate_left) // 2],
        180, 360, fill=(28, 40, 44, 240),
    )


def make_no_token_background() -> None:
    """缺少令牌提示背景:冷调青灰水墨 + 石门剪影 + 雾气。"""
    w = h = BG_SIZE
    random.seed(20260725)
    # 底色:夜空青灰渐变(上深下稍亮,雾气感)
    night_top = (14, 24, 30)
    mist_mid = (78, 96, 100)
    lake_bottom = (24, 42, 48)
    img = Image.new("RGBA", (w, h), (*night_top, 255))
    px = img.load()
    for y in range(h):
        pos = y / (h - 1)
        if pos < 0.5:
            c = _lerp(night_top, mist_mid, pos / 0.5)
        else:
            c = _lerp(mist_mid, lake_bottom, (pos - 0.5) / 0.5)
        for x in range(w):
            px[x, y] = (*c, 255)

    # 石门剪影
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    _draw_stone_gate_silhouette(ImageDraw.Draw(overlay), w, h)
    img.alpha_composite(overlay)

    # 雾气层(多个低 alpha 白色模糊圆)
    mist = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mdraw = ImageDraw.Draw(mist)
    for _ in range(18):
        mx = random.randint(0, w)
        my = random.randint(int(h * 0.35), int(h * 0.9))
        mr = random.randint(int(w * 0.12), int(w * 0.28))
        mdraw.ellipse([mx - mr, my - mr // 2, mx + mr, my + mr // 2],
                      fill=(220, 228, 230, 28))
    mist = mist.filter(ImageFilter.GaussianBlur(radius=40))
    img.alpha_composite(mist)

    # 远处微光(门洞透出的冷光)
    light = _radial_glow(w, (w // 2, int(h * 0.58)), w * 0.22, (150, 190, 200), intensity=0.18)
    img.alpha_composite(light)

    # 顶部暗角(聚焦视线)
    vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    for i in range(8):
        alpha = 20 + i * 8
        vdraw.rectangle(
            [0, 0, w, int(h * 0.15) + i * 10],
            fill=(0, 0, 0, alpha),
        )
    img.alpha_composite(vignette)

    img.save(UI_DIR / "no_token_background.png")
    print(f"  ✓ no_token_background.png ({w}x{h})")


def main() -> None:
    print("生成秘境令牌素材到", UI_DIR)
    make_token_normal()
    make_token_high()
    make_no_token_background()
    print("完成。")


if __name__ == "__main__":
    main()
