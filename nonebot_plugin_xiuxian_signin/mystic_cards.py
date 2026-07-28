from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw, ImageOps

from .cards import (
    draw_panel_icon,
    draw_weighted_text,
    fit_font,
    hex_to_rgb,
    load_font,
    make_xiuxian_background,
    png_bytes,
    text_size,
    wrap_panel_text,
)
from .mystic_dungeon import NodeKind

_NO_TOKEN_BG_PATH = Path(__file__).parent / "assets" / "mystic_dungeon_ui" / "no_token_background.png"
_TOKEN_NORMAL_ICON_PATH = Path(__file__).parent / "assets" / "mystic_dungeon_ui" / "token_normal.png"
_TOKEN_HIGH_ICON_PATH = Path(__file__).parent / "assets" / "mystic_dungeon_ui" / "token_high.png"


@dataclass(frozen=True)
class PixelBox:
    left: int
    top: int
    right: int
    bottom: int

    def within(self, size: tuple[int, int]) -> bool:
        width, height = size
        return (
            0 <= self.left < self.right <= width
            and 0 <= self.top < self.bottom <= height
        )

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)


@dataclass(frozen=True)
class RenderedNode:
    node_id: str
    x: float
    y: float
    kind: NodeKind
    label: str
    boss_portrait_path: Path | None = None

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("rendered node id must not be empty")
        if not 0.0 <= self.x <= 1.0 or not 0.0 <= self.y <= 1.0:
            raise ValueError("rendered node coordinates must be normalized")


@dataclass(frozen=True)
class RenderedEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    state: str

    def __post_init__(self) -> None:
        if not self.edge_id or not self.source_node_id or not self.target_node_id:
            raise ValueError("rendered edge identifiers must not be empty")
        if self.state not in {"future", "traversed", "next"}:
            raise ValueError(f"unsupported rendered edge state: {self.state!r}")


@dataclass(frozen=True)
class MysticMapRenderModel:
    title: str
    subtitle: str
    background_path: Path
    nodes: tuple[RenderedNode, ...]
    edges: tuple[RenderedEdge, ...]
    current_node_id: str
    team_size: int
    temporary_reward_summary: str
    footer_prompt: str = ""
    footer_notice: str = ""

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("mystic map render model requires nodes")
        if not 1 <= self.team_size <= 3:
            raise ValueError("mystic map team size must be between one and three")
        node_ids = {node.node_id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("mystic map render nodes must be unique")
        if self.current_node_id not in node_ids:
            raise ValueError("mystic map current node must exist")
        edge_ids = {edge.edge_id for edge in self.edges}
        if len(edge_ids) != len(self.edges):
            raise ValueError("mystic map render edges must be unique")
        if any(
            edge.source_node_id not in node_ids or edge.target_node_id not in node_ids
            for edge in self.edges
        ):
            raise ValueError("mystic map render edge references an unknown node")


class MysticMapRenderer:
    OUTPUT_SIZE: Final = (1600, 900)
    SOURCE_SIZE: Final = (3840, 2160)
    REGULAR_NODE_SIZE: Final = 20
    BOSS_NODE_SIZE: Final = 25
    TRAVERSED_GREEN: Final = (60, 190, 95, 230)
    NEXT_RED: Final = (224, 62, 62, 240)
    FUTURE_GRAY: Final = (220, 225, 230, 150)

    _ASPECT_RATIO: Final = 16 / 9
    _BOSS_LABEL_MAX_SIZE: Final = (92, 34)

    def __init__(
        self,
        boss_label_path: Path | None = None,
        *,
        allow_placeholder_background: bool = False,
    ) -> None:
        self._boss_label_path = boss_label_path or (
            Path(__file__).resolve().parent
            / "assets"
            / "mystic_dungeon_ui"
            / "boss_label.png"
        )
        self._allow_placeholder_background = allow_placeholder_background
        self._boss_label: Image.Image | None = None

    def render(self, model: MysticMapRenderModel) -> Image.Image:
        crop = self.crop_box(model)
        background = self._load_background(model.background_path)
        image = background.crop(crop).resize(
            self.OUTPUT_SIZE,
            Image.Resampling.LANCZOS,
        )
        image = image.convert("RGBA")
        self._draw_chrome(image, model)
        draw = ImageDraw.Draw(image, "RGBA")
        nodes_by_id = {node.node_id: node for node in model.nodes}

        for edge in model.edges:
            if edge.state == "future":
                self._draw_edge(draw, edge, model, nodes_by_id)
        for edge in model.edges:
            if edge.state == "traversed":
                self._draw_edge(draw, edge, model, nodes_by_id)
        for edge in model.edges:
            if edge.state == "next":
                self._draw_edge(draw, edge, model, nodes_by_id)

        for node in model.nodes:
            self._draw_node(image, draw, node, model)
        return image

    def crop_box(self, model: MysticMapRenderModel) -> tuple[int, int, int, int]:
        source_width, source_height = self.SOURCE_SIZE
        source_x = [node.x * source_width for node in model.nodes]
        source_y = [node.y * source_height for node in model.nodes]
        margin_x = max(180.0, (max(source_x) - min(source_x)) * 0.08)
        margin_y = max(130.0, (max(source_y) - min(source_y)) * 0.10)
        left = min(source_x) - margin_x
        right = max(source_x) + margin_x
        top = min(source_y) - margin_y
        bottom = max(source_y) + margin_y

        width = max(640.0, right - left)
        height = max(360.0, bottom - top)
        if width / height < self._ASPECT_RATIO:
            width = height * self._ASPECT_RATIO
        else:
            height = width / self._ASPECT_RATIO
        width = min(float(source_width), width)
        height = min(float(source_height), height)

        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        left = min(max(0.0, center_x - width / 2), source_width - width)
        top = min(max(0.0, center_y - height / 2), source_height - height)
        right = left + width
        bottom = top + height
        return (
            int(round(left)),
            int(round(top)),
            int(round(right)),
            int(round(bottom)),
        )

    def text_fallback(self, model: MysticMapRenderModel) -> str:
        return (
            f"{model.title} | {model.subtitle}\n"
            f"当前位置: {model.current_node_id} | 队伍: {model.team_size}/3\n"
            f"临时收获: {model.temporary_reward_summary or '无'}"
        )

    def node_box(
        self,
        node: RenderedNode,
        model: MysticMapRenderModel,
    ) -> PixelBox:
        center_x, center_y = self._project(node.x, node.y, self.crop_box(model))
        size = self.BOSS_NODE_SIZE if node.kind is NodeKind.BOSS else self.REGULAR_NODE_SIZE
        left = int(round(center_x - size / 2))
        top = int(round(center_y - size / 2))
        return PixelBox(left, top, left + size, top + size)

    def edge_midpoint(
        self,
        edge: RenderedEdge,
        model: MysticMapRenderModel,
    ) -> tuple[int, int]:
        nodes = {node.node_id: node for node in model.nodes}
        source = nodes[edge.source_node_id]
        target = nodes[edge.target_node_id]
        crop = self.crop_box(model)
        source_x, source_y = self._project(source.x, source.y, crop)
        target_x, target_y = self._project(target.x, target.y, crop)
        return (
            int(round((source_x + target_x) / 2)),
            int(round((source_y + target_y) / 2)),
        )

    def _load_background(self, path: Path) -> Image.Image:
        try:
            with Image.open(path) as source:
                background = source.convert("RGB")
        except (FileNotFoundError, OSError):
            if not self._allow_placeholder_background:
                raise
            background = self._placeholder_background()
        if background.size != self.SOURCE_SIZE:
            background = ImageOps.fit(
                background,
                self.SOURCE_SIZE,
                method=Image.Resampling.LANCZOS,
            )
        return background

    def _placeholder_background(self) -> Image.Image:
        image = Image.new("RGB", self.SOURCE_SIZE, (18, 30, 38))
        draw = ImageDraw.Draw(image)
        for y in range(0, self.SOURCE_SIZE[1], 24):
            color = (18 + y // 72 % 38, 30 + y // 48 % 52, 38 + y // 36 % 64)
            draw.rectangle((0, y, self.SOURCE_SIZE[0], y + 23), fill=color)
        return image

    def _draw_chrome(self, image: Image.Image, model: MysticMapRenderModel) -> None:
        overlay = Image.new("RGBA", self.OUTPUT_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, "RGBA")
        draw.rectangle((0, 0, 1600, 96), fill=(8, 12, 18, 132))
        draw.rectangle((0, 838, 1600, 900), fill=(8, 12, 18, 148))
        title_font = load_font(34, bold=True)
        subtitle_font = load_font(20)
        reward_font = load_font(21, bold=True)
        draw.text((36, 17), model.title, font=title_font, fill=(245, 246, 238, 255))
        draw.text((38, 60), model.subtitle, font=subtitle_font, fill=(205, 214, 220, 235))
        reward_text = f"临时收获  {model.temporary_reward_summary or '无'}"
        draw.text((36, 855), reward_text, font=reward_font, fill=(233, 236, 226, 245))
        # 底部右侧：下一步命令提示（醒目）+ 次要信息（骰子点数等）。
        # 这两段原本只在 result.message 文本里，但图片发送成功后文本被丢弃，
        # 玩家看不到“该发什么命令/掷了多少点”，故烤进图片底部。
        if model.footer_prompt:
            prompt_font = fit_font(draw, model.footer_prompt, 820, 28, bold=True, min_size=18)
            prompt_width = text_size(draw, model.footer_prompt, prompt_font)[0]
            prompt_x = 1564  # 右边界，anchor="ra" 右对齐
            draw.text(
                (prompt_x, 852),
                model.footer_prompt,
                font=prompt_font,
                fill=(232, 176, 74, 255),
                anchor="ra",
            )
            if model.footer_notice:
                notice_font = load_font(21)
                notice_x = prompt_x - prompt_width - 24
                draw.text(
                    (notice_x, 855),
                    model.footer_notice,
                    font=notice_font,
                    fill=(205, 214, 220, 230),
                    anchor="ra",
                )
        elif model.footer_notice:
            draw.text(
                (1564, 855),
                model.footer_notice,
                font=load_font(21),
                fill=(205, 214, 220, 230),
                anchor="ra",
            )
        image.alpha_composite(overlay)

    def _draw_edge(
        self,
        draw: ImageDraw.ImageDraw,
        edge: RenderedEdge,
        model: MysticMapRenderModel,
        nodes_by_id: dict[str, RenderedNode],
    ) -> None:
        crop = self.crop_box(model)
        source = nodes_by_id[edge.source_node_id]
        target = nodes_by_id[edge.target_node_id]
        start = self._project(source.x, source.y, crop)
        end = self._project(target.x, target.y, crop)
        if edge.state == "future":
            self._draw_dashed_line(draw, start, end, self.FUTURE_GRAY, width=3)
            return
        color = self.TRAVERSED_GREEN if edge.state == "traversed" else self.NEXT_RED
        draw.line((start, end), fill=color, width=4)

    def _draw_dashed_line(
        self,
        draw: ImageDraw.ImageDraw,
        start: tuple[float, float],
        end: tuple[float, float],
        color: tuple[int, int, int, int],
        *,
        width: int,
    ) -> None:
        delta_x = end[0] - start[0]
        delta_y = end[1] - start[1]
        distance = math.hypot(delta_x, delta_y)
        if distance <= 0:
            return
        dash_length = 10.0
        gap_length = 7.0
        position = 0.0
        while position < distance:
            dash_end = min(distance, position + dash_length)
            start_ratio = position / distance
            end_ratio = dash_end / distance
            draw.line(
                (
                    (start[0] + delta_x * start_ratio, start[1] + delta_y * start_ratio),
                    (start[0] + delta_x * end_ratio, start[1] + delta_y * end_ratio),
                ),
                fill=color,
                width=width,
            )
            position += dash_length + gap_length

    def _draw_node(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        node: RenderedNode,
        model: MysticMapRenderModel,
    ) -> None:
        box = self.node_box(node, model)
        if node.kind is NodeKind.BOSS:
            self._draw_boss_node(image, box, node.boss_portrait_path)
            return
        if node.node_id == model.current_node_id:
            self._draw_current_node(draw, box, model.team_size)
            return

        fill = (24, 31, 39, 170)
        outline = (226, 231, 229, 215)
        if node.kind is NodeKind.RESOURCE:
            fill = (30, 126, 72, 176)
            outline = (116, 234, 154, 230)
        draw.ellipse(box.as_tuple(), fill=fill, outline=outline, width=1)
        self._draw_node_glyph(draw, box, node.kind)

    def _draw_node_glyph(
        self,
        draw: ImageDraw.ImageDraw,
        box: PixelBox,
        kind: NodeKind,
    ) -> None:
        center_x = (box.left + box.right) // 2
        center_y = (box.top + box.bottom) // 2
        if kind is NodeKind.RANDOM:
            draw.text(
                (center_x, center_y),
                "?",
                font=load_font(13, bold=True),
                fill=(255, 255, 255, 245),
                anchor="mm",
            )
        elif kind is NodeKind.COMBAT:
            draw.line((box.left + 5, box.top + 4, box.right - 5, box.bottom - 4), fill=(255, 238, 224, 245), width=2)
            draw.line((box.right - 5, box.top + 4, box.left + 5, box.bottom - 4), fill=(255, 238, 224, 245), width=2)
        elif kind is NodeKind.RESOURCE:
            draw.rectangle((box.left + 4, box.top + 7, box.right - 4, box.bottom - 4), outline=(224, 255, 231, 245), width=1)
            draw.line((box.left + 4, box.top + 10, box.right - 4, box.top + 10), fill=(224, 255, 231, 245), width=1)
        elif kind is NodeKind.TRAP:
            draw.polygon(
                ((center_x, box.top + 3), (box.right - 3, box.bottom - 3), (box.left + 3, box.bottom - 3)),
                outline=(255, 224, 126, 245),
            )
            draw.line((center_x, box.top + 7, center_x, box.bottom - 7), fill=(255, 224, 126, 245), width=1)
        elif kind is NodeKind.REST:
            draw.ellipse((box.left + 5, box.top + 4, box.right - 5, box.bottom - 4), fill=(225, 240, 255, 245))
            draw.ellipse((box.left + 8, box.top + 2, box.right - 3, box.bottom - 7), fill=(24, 31, 39, 255))
        else:
            draw.ellipse((box.left + 5, box.top + 5, box.right - 5, box.bottom - 5), outline=(255, 255, 255, 240), width=2)

    def _draw_current_node(
        self,
        draw: ImageDraw.ImageDraw,
        box: PixelBox,
        team_size: int,
    ) -> None:
        draw.ellipse(box.as_tuple(), fill=(235, 238, 230, 235), outline=(120, 232, 184, 255), width=2)
        draw.pieslice(box.as_tuple(), 90, 270, fill=(20, 27, 31, 255))
        radius = max(2, (box.right - box.left) // 4)
        center_x = (box.left + box.right) // 2
        center_y = (box.top + box.bottom) // 2
        draw.ellipse((center_x - radius, box.top, center_x + radius, center_y), fill=(235, 238, 230, 255))
        draw.ellipse((center_x - radius, center_y, center_x + radius, box.bottom), fill=(20, 27, 31, 255))
        draw.ellipse((center_x - 1, box.top + radius - 1, center_x + 1, box.top + radius + 1), fill=(20, 27, 31, 255))
        draw.ellipse((center_x - 1, box.bottom - radius - 1, center_x + 1, box.bottom - radius + 1), fill=(235, 238, 230, 255))
        if team_size > 1:
            draw.text(
                (box.right + 5, center_y),
                f"{team_size}/3",
                font=load_font(16, bold=True),
                fill=(240, 246, 238, 255),
                stroke_width=2,
                stroke_fill=(9, 14, 17, 230),
                anchor="lm",
            )

    def _draw_boss_node(
        self,
        image: Image.Image,
        box: PixelBox,
        portrait_path: Path | None,
    ) -> None:
        portrait = self._load_portrait(portrait_path, self.BOSS_NODE_SIZE)
        image.alpha_composite(portrait, (box.left, box.top))
        label = self._load_boss_label()
        label_x = int(round((box.left + box.right - label.width) / 2))
        label_y = box.top - label.height - 5
        label_x = min(max(0, label_x), self.OUTPUT_SIZE[0] - label.width)
        label_y = max(0, label_y)
        image.alpha_composite(label, (label_x, label_y))

    def _load_portrait(self, path: Path | None, size: int) -> Image.Image:
        portrait: Image.Image | None = None
        if path is not None:
            try:
                with Image.open(path) as source:
                    portrait = ImageOps.fit(
                        source.convert("RGBA"),
                        (size, size),
                        method=Image.Resampling.LANCZOS,
                    )
            except (FileNotFoundError, OSError):
                portrait = None
        if portrait is None:
            portrait = Image.new("RGBA", (size, size), (108, 20, 26, 255))
            draw = ImageDraw.Draw(portrait, "RGBA")
            draw.ellipse((4, 3, size - 4, size - 5), fill=(213, 150, 120, 255))
            draw.polygon(((3, 9), (size // 2, 1), (size - 3, 9)), fill=(54, 18, 23, 255))
            draw.ellipse((7, 10, 10, 13), fill=(255, 70, 70, 255))
            draw.ellipse((size - 10, 10, size - 7, 13), fill=(255, 70, 70, 255))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        portrait.putalpha(mask)
        ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((0, 0, size - 1, size - 1), outline=(246, 67, 67, 255), width=2)
        portrait.alpha_composite(ring)
        return portrait

    def _load_boss_label(self) -> Image.Image:
        if self._boss_label is not None:
            return self._boss_label.copy()
        try:
            with Image.open(self._boss_label_path) as source:
                label = source.convert("RGBA")
        except (FileNotFoundError, OSError) as exc:
            raise FileNotFoundError(
                f"mystic boss label is unavailable: {self._boss_label_path}"
            ) from exc
        label.thumbnail(self._BOSS_LABEL_MAX_SIZE, Image.Resampling.LANCZOS)
        self._boss_label = label.copy()
        return label

    def _project(
        self,
        normalized_x: float,
        normalized_y: float,
        crop: tuple[int, int, int, int],
    ) -> tuple[float, float]:
        left, top, right, bottom = crop
        source_x = normalized_x * self.SOURCE_SIZE[0]
        source_y = normalized_y * self.SOURCE_SIZE[1]
        return (
            (source_x - left) / (right - left) * self.OUTPUT_SIZE[0],
            (source_y - top) / (bottom - top) * self.OUTPUT_SIZE[1],
        )


def _load_token_icon(path: Path, size: int) -> Image.Image:
    """加载令牌图标并缩放到指定尺寸,失败时返回占位图。"""
    try:
        with Image.open(path) as source:
            icon = source.convert("RGBA")
    except (FileNotFoundError, OSError):
        icon = Image.new("RGBA", (128, 128), (90, 140, 150, 255))
    if icon.size != (size, size):
        icon = icon.resize((size, size), Image.Resampling.LANCZOS)
    return icon


def render_no_token_panel(
    *,
    normal_count: int,
    high_count: int,
    normal_theme_names: tuple[str, ...] = (),
    high_theme_names: tuple[str, ...] = (),
    width: int = 1180,
) -> bytes:
    """渲染“缺少秘境令牌”专属提示图。

    参数:
        normal_count: 普通秘境令牌持有数
        high_count: 高风险秘境令牌持有数
        normal_theme_names: 普通令牌本可进入的秘境主题名(用于提示“错过了什么”)
        high_theme_names: 高风险令牌本可进入的秘境主题名
        width: 面板宽度

    返回 PNG bytes。当两种令牌都为 0 时,整图强调“无法进入任何秘境”;
    当仅其中一种为 0 时,只提示该种令牌不足。
    """
    accent = "#c8613a"  # 赤金/铜色,呼应“禁入/警示”
    width = max(width, 1180)

    measure = Image.new("RGBA", (width, 120), (0, 0, 0, 0))
    measure_draw = ImageDraw.Draw(measure)
    title_text = "令牌不足"
    title_font = fit_font(measure_draw, title_text, width - 280, 64, bold=True, min_size=42)
    subtitle_font = load_font(30, bold=True)
    body_font = load_font(34, bold=True)
    hint_font = load_font(30, bold=True)
    small_font = load_font(28, bold=True)
    max_text_width = width - 260

    # 构造内容行
    rows: list[tuple[str, str, str]] = []  # (kind, text, token_type)
    if normal_count <= 0:
        rows.append(("token", "普通秘境令牌 ×0", "normal"))
    if high_count <= 0:
        rows.append(("token", "高风险秘境令牌 ×0", "high"))
    # 获取途径
    rows.append(("hint", "每日签到概率掉落 · 完成带令牌的每日任务必得(每日1个)", ""))
    # 可进入的秘境
    if normal_count <= 0 and normal_theme_names:
        names = "、".join(normal_theme_names[:6])
        if len(normal_theme_names) > 6:
            names += "等"
        rows.append(("themes", f"普通秘境可进入: {names}", "normal"))
    if high_count <= 0 and high_theme_names:
        names = "、".join(high_theme_names[:6])
        if len(high_theme_names) > 6:
            names += "等"
        rows.append(("themes", f"高风险秘境可进入: {names}", "high"))

    # 预排版文本以计算高度
    layout: list[tuple[str, str, list[str], str, int, int]] = []  # (kind, raw, wrapped, token_type, block_h, gap)
    content_height = 0
    for kind, text, token_type in rows:
        if kind == "token":
            wrapped = [text]
            block_h = 110  # 留出图标空间
            gap = 16
        elif kind == "hint":
            wrapped = wrap_panel_text(measure_draw, text, hint_font, max_text_width - 86)
            block_h = max(62, 42 * len(wrapped) + 20)
            gap = 14
        else:  # themes
            wrapped = wrap_panel_text(measure_draw, text, body_font, max_text_width - 86)
            block_h = max(62, 42 * len(wrapped) + 20)
            gap = 14
        layout.append((kind, text, wrapped, token_type, block_h, gap))
        content_height += block_h + gap

    content_start_y = 268
    content_bottom_padding = 64
    height = max(560, content_start_y + content_height + content_bottom_padding + 58)

    # 背景:优先加载专属底图,失败回退到程序化水墨背景
    image: Image.Image
    themed_background = False
    try:
        with Image.open(_NO_TOKEN_BG_PATH) as source:
            bg = source.convert("RGBA")
        image = bg.resize((width, height), Image.Resampling.LANCZOS)
        themed_background = True
    except (FileNotFoundError, OSError):
        image = make_xiuxian_background(width, height, accent)

    draw = ImageDraw.Draw(image)

    # 卡片底框:主题背景存在时用高不透明度米白卷轴蒙版(让文字落在干净底色上,
    # AI 背景只从卡片外缘透出烘托氛围);否则用半透明蒙版配程序化背景。
    card_fill = (255, 250, 238, 218) if themed_background else (255, 250, 238, 92)
    draw.rounded_rectangle(
        (58, 62, width - 58, height - 58),
        radius=28,
        fill=card_fill,
        outline=(234, 218, 184, 200),
        width=2,
    )

    # 标题栏图标(warning) + 标题(米白底用深色文字,程序化背景用浅色文字)
    title_color = "#7a2a1a" if themed_background else "#fff3e6"
    subtitle_color = "#8a5a3a" if themed_background else "#e8d9c2"
    title_stroke = (255, 240, 220, 0) if themed_background else (60, 20, 12, 200)
    draw_panel_icon(draw, (104, 112, 208, 216), "warning", accent)
    draw_weighted_text(draw, (238, 112), title_text, title_font, title_color, weight=4,
                       stroke_width=0 if themed_background else 2,
                       stroke_fill=title_stroke)
    draw_weighted_text(draw, (242, 184), "无对应令牌,无法开启秘境", subtitle_font, subtitle_color, weight=2)

    # 内容行
    y = content_start_y
    left = 104
    right = width - 104
    for kind, raw, wrapped, token_type, block_h, gap in layout:
        if kind == "token":
            # 令牌行:左侧大图标 + 右侧文字
            draw.rounded_rectangle(
                (left, y, right, y + block_h),
                radius=18, fill=(255, 255, 255, 210), outline="#eee2ca", width=2,
            )
            icon_size = 78
            icon_path = _TOKEN_NORMAL_ICON_PATH if token_type == "normal" else _TOKEN_HIGH_ICON_PATH
            icon = _load_token_icon(icon_path, icon_size)
            icon_x = left + 18
            icon_y = y + (block_h - icon_size) // 2
            image.alpha_composite(icon, (icon_x, icon_y))
            # 文字
            label_color = "#8a4a2a" if token_type == "normal" else "#7a2a3a"
            draw_weighted_text(draw, (left + 112, y + 20), wrapped[0], body_font, label_color, weight=3)
            draw_weighted_text(
                draw, (left + 112, y + 62),
                "玄阶·中品" if token_type == "normal" else "地阶·上品",
                small_font, "#9a8a70", weight=1,
            )
        elif kind == "hint":
            draw.rounded_rectangle(
                (left, y, right, y + block_h),
                radius=18, fill=(252, 247, 232, 220), outline="#eadfca", width=2,
            )
            draw_panel_icon(draw, (left + 16, y + 12, left + 58, y + 54), "scroll", accent)
            text_y = y + 14
            for part in wrapped:
                draw_weighted_text(draw, (left + 78, text_y), part, hint_font, "#5a4a36", weight=2)
                text_y += 42
        else:  # themes
            draw.rounded_rectangle(
                (left, y, right, y + block_h),
                radius=18, fill=(255, 255, 255, 200), outline="#eee2ca", width=2,
            )
            theme_accent = "#3a7a8a" if token_type == "normal" else "#8a3a5a"
            draw_panel_icon(draw, (left + 16, y + 12, left + 58, y + 54), "mystic", theme_accent)
            text_y = y + 14
            for part in wrapped:
                draw_weighted_text(draw, (left + 78, text_y), part, body_font, "#344054", weight=2)
                text_y += 42
        y += block_h + gap

    # 底部引导
    footer_font = fit_font(draw, "发送 秘境 可随时查看可进入的秘境列表", width - 208, 26, bold=True, min_size=18)
    footer_color = "#9a8a6a" if themed_background else "#d8c8a8"
    draw_weighted_text(
        draw, (104, height - 108),
        "获取令牌后,发送 秘境 查看可进入的秘境列表",
        footer_font, footer_color, weight=1,
    )
    return png_bytes(image)
