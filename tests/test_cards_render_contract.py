"""渲染原语契约（R-19 / 为 R-37 铺路）。

R-37 要把斗地主改成「全图形、无文本降级」，渲染可靠性就从锦上添花变成功能可用性的前提。
这里先把最底层的绘图原语钉住，避免图形化改造时把基础行为改坏却无人察觉：

1. 同样的输入必须产出逐像素相同的图（渲染线程池 + LRU 缓存下，不确定性会变成偶发错图）；
2. ``draw_card`` 真的把卡片画在指定位置（不是偏移、不是透明）；
3. ``rounded_layer`` 的圆角必须透明，否则叠在背景上是方块；
4. ``load_panel_background`` 必须返回副本——调用方会在背景上作画，共享原对象会互相涂改。

刻意不做「与基准 PNG 逐字节比对」的黄金图：字体与 Pillow 版本变化会让这类断言变成
环境噪声。逐字节黄金图留到 R-38——那时 54 张牌面与 4 类局面图是固定资产，比对才有意义。
"""
from __future__ import annotations

from PIL import Image

from nonebot_plugin_xiuxian_signin.cards import (
    draw_card,
    draw_weighted_text,
    fit_font,
    hex_to_rgb,
    load_font,
    load_panel_background,
    make_background,
    mix,
    rounded_layer,
    text_size,
)


def test_hex_to_rgb_and_mix() -> None:
    assert hex_to_rgb("#ff8000") == (255, 128, 0)
    assert hex_to_rgb("ff8000") == (255, 128, 0)
    assert mix((0, 0, 0), (100, 100, 100), 0.5) == (50, 50, 50)
    assert mix((0, 0, 0), (100, 100, 100), 0.0) == (0, 0, 0)
    assert mix((0, 0, 0), (100, 100, 100), 1.0) == (100, 100, 100)


def test_make_background_is_deterministic_and_gradient() -> None:
    first = make_background(64, 96, "#3f6fd8")
    second = make_background(64, 96, "#3f6fd8")
    assert first.size == (64, 96) and first.mode == "RGBA"
    assert first.tobytes() == second.tobytes(), "相同输入的背景必须逐像素一致"

    top = first.getpixel((32, 0))
    middle = first.getpixel((32, 48))
    assert top != middle, "背景应是渐变，不能是纯色"

    other = make_background(64, 96, "#d84f3f")
    assert other.getpixel((0, 0)) != top, "不同 accent 应产出不同底色"


def test_rounded_layer_corners_are_transparent() -> None:
    layer = rounded_layer((120, 80), 20, (255, 255, 255, 200))
    assert layer.size == (120, 80)
    assert layer.getpixel((0, 0))[3] == 0, "圆角处必须透明"
    assert layer.getpixel((60, 40))[3] == 200, "中心应保留填充透明度"


def test_draw_card_draws_at_requested_box() -> None:
    canvas = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
    draw_card(canvas, (20, 20, 220, 200))
    inside = canvas.getpixel((120, 110))
    outside = canvas.getpixel((2, 2))
    assert inside[3] > 150, "卡片内部应被填充"
    assert outside[3] == 0, "卡片外不应被涂色"


def test_draw_weighted_text_increases_ink() -> None:
    def ink(weight: int) -> int:
        canvas = Image.new("RGBA", (160, 60), (0, 0, 0, 0))
        from PIL import ImageDraw

        draw_weighted_text(ImageDraw.Draw(canvas), (4, 4), "修仙", load_font(24), (0, 0, 0, 255), weight=weight)
        return sum(1 for pixel in canvas.getdata() if pixel[3] > 0)

    assert ink(4) > ink(1), "加粗应当画出更多像素"


def test_fit_font_respects_max_width() -> None:
    from PIL import ImageDraw

    canvas = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # 能放下时：选到的字号必须真的放得下
    text = "御兽秘境任务堂"
    font = fit_font(draw, text, max_width=300, size=48)
    assert text_size(draw, text, font)[0] <= 300

    # 放不下时：收敛到 min_size 而不是无限缩字（可读性下限，不是 bug）
    long_text = "御兽秘境任务堂" * 6
    tiny = fit_font(draw, long_text, max_width=120, size=48, min_size=18)
    assert text_size(draw, long_text, tiny)[0] > 120
    assert tiny.size >= 18


def test_text_size_grows_with_font_size() -> None:
    from PIL import ImageDraw

    canvas = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    small = text_size(draw, "签到", load_font(16))[0]
    large = text_size(draw, "签到", load_font(32))[0]
    assert large > small


def test_load_panel_background_returns_copy_and_falls_back(tmp_path) -> None:
    source = tmp_path / "bg.png"
    Image.new("RGBA", (200, 200), (10, 20, 30, 255)).save(source)

    image, from_file = load_panel_background(source, 100, 100, "#3f6fd8")
    assert from_file is True
    assert image.size == (100, 100)

    # 调用方作画不得污染缓存
    image.paste((255, 0, 0, 255), (0, 0, 10, 10))
    cached, again_from_file = load_panel_background(source, 100, 100, "#3f6fd8")
    assert again_from_file is True
    assert cached.getpixel((0, 0)) != (255, 0, 0, 255), "必须返回背景副本，否则并发渲染会互相涂改"

    fallback, missing_from_file = load_panel_background(tmp_path / "nope.png", 100, 100, "#3f6fd8")
    assert missing_from_file is False
    assert fallback.size == (100, 100), "缺图时应返回程序化兜底背景而不是抛错"
