from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import random
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PKG_NAME = "nonebot_plugin_xiuxian_signin"
OUT_DIR = ROOT / "assets" / "character_portraits"
PORTRAIT_DIR = OUT_DIR / "portraits"
CATALOG_DIR = ROOT / "build" / "character_portraits"
CARD_SIZE = (288, 416)
RENDER_SCALE = 1


def load_domain_module() -> Any:
    pkg = types.ModuleType(PKG_NAME)
    pkg.__path__ = [str(ROOT)]
    sys.modules.setdefault(PKG_NAME, pkg)
    spec = importlib.util.spec_from_file_location(f"{PKG_NAME}.domain", ROOT / "domain.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load domain.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{PKG_NAME}.domain"] = module
    spec.loader.exec_module(module)
    return module


domain = load_domain_module()


@dataclass(frozen=True)
class FactionStyle:
    key: str
    name: str
    role_type: str
    accent: tuple[int, int, int]
    accent_dark: tuple[int, int, int]
    aura: tuple[int, int, int]
    symbol: str
    story_seed: str


FACTIONS = [
    FactionStyle("beast", "妖兽", "beast", (181, 72, 42), (74, 38, 32), (236, 148, 78), "claw", "兽潮深处"),
    FactionStyle("rogue", "散修", "human", (104, 116, 92), (42, 56, 48), (188, 178, 128), "blade", "荒路旧约"),
    FactionStyle("buddhist", "佛修", "human", (190, 142, 48), (93, 64, 28), (238, 198, 102), "halo", "古刹钟声"),
    FactionStyle("evil_cultivator", "邪修", "human", (126, 50, 68), (52, 28, 42), (198, 60, 96), "rune", "血灯暗巷"),
    FactionStyle("evil_god", "邪神", "human", (80, 78, 132), (28, 30, 58), (150, 122, 220), "eye", "残庙神谕"),
    FactionStyle("false_god", "伪神", "human", (176, 158, 96), (72, 66, 50), (226, 210, 140), "crown", "金身裂纹"),
    FactionStyle("demon_god", "魔神", "human", (120, 42, 42), (46, 24, 28), (220, 72, 54), "horns", "魔渊王座"),
    FactionStyle("outer_demon", "域外天魔", "human", (58, 88, 142), (22, 34, 60), (92, 182, 210), "star", "界外裂隙"),
    FactionStyle("system_holder", "系统持有者", "human", (46, 132, 128), (22, 62, 68), (90, 220, 200), "grid", "异数面板"),
]

REALM_STAGES = ("初期", "中期", "后期", "圆满")
HUMAN_SURNAMES = "顾沈陆萧林叶许秦韩楚苏谢江洛白纪宁孟方夏温钟宋姜尹祁卓程"
FACTION_TITLES = {
    "散修": ("孤剑", "归尘", "寒灯", "破阵", "渡河", "拾星", "逆旅", "听雨", "残碑", "野渡"),
    "佛修": ("净莲", "梵钟", "明王", "渡厄", "燃灯", "金刚", "慈航", "空相", "照夜", "无垢"),
    "邪修": ("血幡", "噬魂", "阴烛", "断魄", "魇骨", "赤瘴", "夜哭", "残心", "鬼契", "逆命"),
    "邪神": ("荒瞳", "旧日", "诡月", "蚀梦", "残星", "无面", "幽契", "黑莲", "祟光", "瘟火"),
    "伪神": ("金阙", "伪敕", "玉册", "神龛", "镀光", "天诏", "灵座", "圣像", "玄冕", "封禅"),
    "魔神": ("玄戮", "焚狱", "赤魇", "断岳", "血旌", "魔铠", "裂空", "烬王", "沉锋", "灭道"),
    "域外天魔": ("星噬", "界裂", "虚舟", "逆星", "银瞳", "寂环", "空渊", "玄矩", "夜航", "离界"),
    "系统持有者": ("序列", "天赋", "任务", "面板", "权限", "回档", "词条", "掠夺", "模拟", "终端"),
}
GIVEN_NAMES = ("行舟", "照玄", "问棠", "栖衡", "逐渊", "守微", "临川", "怀烬", "见素", "归藏")


def stable_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12], 16)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        ROOT / "assets" / "fonts" / "HarmonyOS_Sans_SC.ttf",
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def shade(color: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, channel + amount)) for channel in color)


def rgba(color: tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return (*color, max(0, min(255, alpha)))


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


def stage_realm(index: int) -> str:
    realms = list(getattr(domain, "REALMS"))
    realm = realms[1 + (index % (len(realms) - 1))]
    return f"{realm}{REALM_STAGES[index % len(REALM_STAGES)]}"


def archetype_for_beast(name: str) -> str:
    config = getattr(domain, "boss_archetype_config")({"boss_name": name})
    return str(config.get("race") or "妖族-远荒异兽")


def style_for_faction(faction: str) -> FactionStyle:
    for style in FACTIONS:
        if style.name == faction:
            return style
    raise KeyError(faction)


def character_story(faction: str, name: str, realm: str, index: int, archetype: str = "") -> str:
    style = style_for_faction(faction)
    if faction == "妖兽":
        return (
            f"{name}盘踞在{style.story_seed}，{archetype.replace('妖族-', '') or '远荒血脉'}随境界涨落而苏醒。"
            f"传闻它每到{realm}便会换鳞重生，留下的妖丹能映出旧日兽潮。"
        )
    motives = {
        "散修": "不入宗门谱牒，只信手中旧兵与一口不肯低头的气。",
        "佛修": "以戒律锁住杀念，掌中佛光却常被战火逼出怒相。",
        "邪修": "借禁术续命，灵台深处仍藏着一段不可告人的旧愿。",
        "邪神": "回应残庙香火而来，言语像神谕，也像陷阱。",
        "伪神": "披着敕封金光收拢信众，金身裂缝里尽是凡心。",
        "魔神": "从魔渊战名中醒来，把每一场斗法都当作祭礼。",
        "域外天魔": "随界外裂隙降临，熟悉修士梦境中最薄弱的一念。",
        "系统持有者": "身负异数面板，能把战场拆成任务、奖励与冷却。"
    }
    hook = motives.get(faction, "行踪难测，常在战局最乱处现身。")
    return f"{name}现身于{style.story_seed}，修为约在{realm}。{hook}"


def build_character_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    beast_names = list(getattr(domain, "BEAST_NAMES"))
    for index, name in enumerate(beast_names[:30], start=1):
        archetype = archetype_for_beast(name)
        realm = stage_realm(index - 1)
        records.append(
            {
                "id": f"beast_{index:03d}",
                "name": name,
                "faction": "妖兽",
                "realm": realm,
                "archetype": archetype,
                "portrait": f"beast_{index:03d}.png",
                "style_tags": ["东方玄幻动漫半身像", "妖兽半身像", archetype],
                "story": character_story("妖兽", name, realm, index, archetype),
            }
        )

    for style in FACTIONS:
        if style.name == "妖兽":
            continue
        titles = FACTION_TITLES[style.name]
        for index in range(1, 31):
            title = titles[(index - 1) % len(titles)]
            surname = HUMAN_SURNAMES[(index + stable_int(style.key)) % len(HUMAN_SURNAMES)]
            given = GIVEN_NAMES[(index * 3 + stable_int(style.name)) % len(GIVEN_NAMES)]
            if style.name in {"邪神", "伪神", "魔神", "域外天魔"}:
                name = f"{title}{style.name.replace('域外', '')}{index:02d}"
            elif style.name == "系统持有者":
                name = f"{title}持有者{surname}{given}"
            else:
                name = f"{title}{surname}{given}"
            realm = stage_realm(index + stable_int(style.key) % 17)
            records.append(
                {
                    "id": f"{style.key}_{index:03d}",
                    "name": name,
                    "faction": style.name,
                    "realm": realm,
                    "archetype": title,
                    "portrait": f"{style.key}_{index:03d}.png",
                    "style_tags": ["东方玄幻动漫半身像", "半身像", style.name, title],
                    "story": character_story(style.name, name, realm, index),
                }
            )
    return records


def add_texture(image: Image.Image, seed: str) -> None:
    rng = random.Random(stable_int(seed))
    pixels = image.load()
    width, height = image.size
    for y in range(height):
        for x in range(width):
            if rng.random() < 0.035:
                r, g, b, a = pixels[x, y]
                delta = rng.randint(-10, 11)
                pixels[x, y] = (max(0, min(255, r + delta)), max(0, min(255, g + delta)), max(0, min(255, b + delta)), a)


def draw_card_background(draw: ImageDraw.ImageDraw, width: int, height: int, style: FactionStyle, seed: str) -> None:
    for y in range(height):
        t = y / max(1, height - 1)
        base = mix((236, 229, 211), shade(style.accent, 80), t * 0.42)
        draw.line((0, y, width, y), fill=rgba(base, 255))
    rng = random.Random(stable_int(seed))
    for _ in range(42):
        x = rng.randint(-width // 5, width)
        y = rng.randint(0, height)
        rx = rng.randint(width // 8, width // 2)
        ry = rng.randint(height // 18, height // 5)
        color = rgba(style.aura, rng.randint(18, 48))
        draw.ellipse((x, y, x + rx, y + ry), fill=color)
    for _ in range(14):
        x1 = rng.randint(-40, width)
        y1 = rng.randint(50, height - 70)
        x2 = x1 + rng.randint(80, 230)
        y2 = y1 + rng.randint(-80, 90)
        draw.line((x1, y1, x2, y2), fill=rgba(style.accent_dark, rng.randint(28, 50)), width=rng.randint(2, 5))


def draw_symbol(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: int, style: FactionStyle) -> None:
    color = rgba(style.accent_dark, 150)
    bright = rgba(style.aura, 150)
    if style.symbol == "claw":
        for offset in (-22, 0, 22):
            draw.line((cx + offset, cy + 38, cx + offset + 16, cy - 42), fill=color, width=7)
    elif style.symbol == "blade":
        draw.polygon([(cx - 8, cy + 42), (cx + 10, cy + 42), (cx + 22, cy - 44), (cx + 2, cy - 66)], fill=color)
    elif style.symbol == "halo":
        draw.ellipse((cx - 52, cy - 52, cx + 52, cy + 52), outline=bright, width=8)
        draw.ellipse((cx - 28, cy - 28, cx + 28, cy + 28), outline=color, width=5)
    elif style.symbol == "rune":
        draw.polygon([(cx, cy - 58), (cx + 48, cy), (cx, cy + 58), (cx - 48, cy)], outline=color, width=7)
        draw.line((cx - 30, cy, cx + 30, cy), fill=bright, width=6)
    elif style.symbol == "eye":
        draw.ellipse((cx - 58, cy - 28, cx + 58, cy + 28), outline=color, width=7)
        draw.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=bright)
    elif style.symbol == "crown":
        points = [(cx - 56, cy + 30), (cx - 44, cy - 28), (cx - 14, cy + 4), (cx, cy - 48), (cx + 14, cy + 4), (cx + 44, cy - 28), (cx + 56, cy + 30)]
        draw.line(points, fill=color, width=8, joint="curve")
    elif style.symbol == "horns":
        draw.arc((cx - 72, cy - 58, cx - 8, cy + 56), 190, 338, fill=color, width=8)
        draw.arc((cx + 8, cy - 58, cx + 72, cy + 56), 202, 350, fill=color, width=8)
    elif style.symbol == "star":
        points = []
        for i in range(10):
            radius = 58 if i % 2 == 0 else 23
            angle = -math.pi / 2 + i * math.pi / 5
            points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        draw.polygon(points, outline=color, fill=rgba(style.aura, 34))
    elif style.symbol == "grid":
        for offset in (-36, 0, 36):
            draw.line((cx - 56, cy + offset, cx + 56, cy + offset), fill=color, width=5)
            draw.line((cx + offset, cy - 56, cx + offset, cy + 56), fill=color, width=5)


def draw_humanoid(draw: ImageDraw.ImageDraw, width: int, height: int, style: FactionStyle, seed: str) -> None:
    rng = random.Random(stable_int(seed))
    cx = width // 2
    shoulder_y = int(height * 0.72)
    robe = style.accent
    dark = style.accent_dark
    skin = (210 + rng.randint(-8, 8), 176 + rng.randint(-10, 10), 142 + rng.randint(-8, 8))
    hair = shade(dark, rng.randint(-14, 14))

    draw_symbol(draw, cx + rng.randint(-8, 8), int(height * 0.31), 1, style)
    draw.ellipse((cx - 102, 118, cx + 102, 322), fill=rgba(style.aura, 44))
    draw.polygon([(cx - 138, shoulder_y + 88), (cx - 94, shoulder_y - 56), (cx, shoulder_y - 84), (cx + 94, shoulder_y - 56), (cx + 138, shoulder_y + 88)], fill=rgba(dark, 238))
    draw.polygon([(cx - 116, shoulder_y + 88), (cx - 72, shoulder_y - 44), (cx, shoulder_y - 68), (cx + 72, shoulder_y - 44), (cx + 116, shoulder_y + 88)], fill=rgba(robe, 242))
    draw.polygon([(cx - 18, shoulder_y - 74), (cx + 18, shoulder_y - 74), (cx + 36, shoulder_y + 48), (cx - 34, shoulder_y + 48)], fill=rgba(shade(robe, 36), 235))
    draw.line((cx, shoulder_y - 70, cx, shoulder_y + 68), fill=rgba((245, 236, 204), 170), width=5)
    draw.ellipse((cx - 56, 166, cx + 56, 286), fill=rgba(skin, 255), outline=rgba(dark, 185), width=4)
    draw.pieslice((cx - 68, 126, cx + 68, 238), 178, 362, fill=rgba(hair, 255))
    draw.rectangle((cx - 42, 204, cx + 42, 244), fill=rgba(skin, 255))
    draw.arc((cx - 30, 218, cx - 2, 238), 205, 330, fill=rgba(dark, 150), width=3)
    draw.arc((cx + 2, 218, cx + 30, 238), 210, 335, fill=rgba(dark, 150), width=3)
    draw.line((cx - 18, 260, cx + 18, 260), fill=rgba(dark, 145), width=3)

    if style.symbol in {"horns", "eye", "star"}:
        draw.polygon([(cx - 42, 142), (cx - 92, 82), (cx - 62, 176)], fill=rgba(dark, 230))
        draw.polygon([(cx + 42, 142), (cx + 92, 82), (cx + 62, 176)], fill=rgba(dark, 230))
    if style.symbol == "halo":
        draw.ellipse((cx - 90, 124, cx + 90, 304), outline=rgba(style.aura, 120), width=9)
    if style.symbol == "grid":
        panel = (cx + 56, 178, cx + 128, 262)
        draw.rounded_rectangle(panel, radius=8, fill=rgba((22, 42, 48), 185), outline=rgba(style.aura, 190), width=3)
        for i in range(3):
            y = panel[1] + 18 + i * 22
            draw.line((panel[0] + 12, y, panel[2] - 12, y), fill=rgba(style.aura, 160), width=2)


def draw_beast(draw: ImageDraw.ImageDraw, width: int, height: int, style: FactionStyle, seed: str) -> None:
    rng = random.Random(stable_int(seed))
    cx = width // 2
    body = mix(style.accent, (96, 74, 58), 0.32)
    dark = style.accent_dark
    aura = style.aura
    draw_symbol(draw, cx, int(height * 0.28), 1, style)
    draw.ellipse((cx - 132, 204, cx + 132, 494), fill=rgba(dark, 236))
    draw.ellipse((cx - 108, 178, cx + 108, 380), fill=rgba(body, 255), outline=rgba(dark, 210), width=7)
    snout_w = 40 + rng.randint(0, 30)
    draw.ellipse((cx - snout_w, 250, cx + snout_w, 326), fill=rgba(shade(body, 24), 255), outline=rgba(dark, 160), width=3)
    eye_y = 238 + rng.randint(-8, 8)
    for side in (-1, 1):
        ex = cx + side * (36 + rng.randint(0, 8))
        draw.ellipse((ex - 14, eye_y - 10, ex + 14, eye_y + 10), fill=rgba((25, 22, 18), 255))
        draw.ellipse((ex - 5, eye_y - 5, ex + 5, eye_y + 5), fill=rgba(aura, 255))
    draw.polygon([(cx - 74, 192), (cx - 132, 96), (cx - 80, 226)], fill=rgba(dark, 245))
    draw.polygon([(cx + 74, 192), (cx + 132, 96), (cx + 80, 226)], fill=rgba(dark, 245))
    for side in (-1, 1):
        horn = [(cx + side * 44, 178), (cx + side * 88, 76), (cx + side * 20, 160)]
        draw.polygon(horn, fill=rgba((224, 202, 150), 238), outline=rgba(dark, 150))
    for i in range(6):
        y = 332 + i * 22
        draw.arc((cx - 88, y - 42, cx + 88, y + 58), 20, 160, fill=rgba(shade(body, 46), 90), width=4)
    draw.line((cx - 34, 316, cx, 338, cx + 34, 316), fill=rgba(dark, 180), width=5)
    draw.polygon([(cx - 56, 342), (cx - 10, 384), (cx - 2, 438), (cx - 72, 412)], fill=rgba(shade(body, -12), 240))
    draw.polygon([(cx + 56, 342), (cx + 10, 384), (cx + 2, 438), (cx + 72, 412)], fill=rgba(shade(body, -12), 240))


def draw_beast_variant(draw: ImageDraw.ImageDraw, width: int, height: int, style: FactionStyle, record: dict[str, Any]) -> None:
    archetype = str(record.get("archetype") or "")
    name = str(record.get("name") or "")
    cx = width // 2
    dark = style.accent_dark
    aura = style.aura
    if "金羽" in archetype or any(token in name for token in ("鹏", "鹰", "羽", "电", "雷")):
        for side in (-1, 1):
            wing = [(cx + side * 24, 262), (cx + side * 150, 170), (cx + side * 116, 352)]
            draw.polygon(wing, fill=rgba((50, 58, 78), 132), outline=rgba(aura, 120))
            for i in range(3):
                draw.line((cx + side * (48 + i * 25), 225 + i * 18, cx + side * (112 + i * 8), 330), fill=rgba(aura, 110), width=3)
    if "真龙" in archetype or any(token in name for token in ("蛟", "龙", "鲛", "麟")):
        for side in (-1, 1):
            draw.line((cx + side * 28, 258, cx + side * 142, 230), fill=rgba((232, 210, 156), 190), width=4)
            draw.line((cx + side * 22, 278, cx + side * 134, 296), fill=rgba((232, 210, 156), 160), width=3)
        draw.arc((cx - 70, 138, cx + 70, 232), 205, 335, fill=rgba((232, 210, 156), 180), width=6)
    if "火脉" in archetype or any(token in name for token in ("火", "焰", "赤", "离")):
        for i in range(6):
            x = cx - 86 + i * 34
            draw.polygon([(x, 198), (x + 16, 102 + (i % 2) * 24), (x + 36, 198)], fill=rgba((226, 92, 42), 155), outline=rgba((255, 207, 95), 90))
    if "玄冰" in archetype or any(token in name for token in ("冰", "霜", "寒")):
        for i in range(7):
            x = cx - 96 + i * 32
            draw.polygon([(x, 190), (x + 14, 112 - (i % 2) * 22), (x + 32, 190)], fill=rgba((196, 226, 236), 165), outline=rgba(dark, 85))
    if "搬山" in archetype or any(token in name for token in ("山", "龟", "象", "犀", "石", "甲")):
        for i in range(5):
            x = cx - 86 + i * 43
            draw.polygon([(x, 350), (x + 28, 318), (x + 55, 352), (x + 38, 400), (x + 8, 398)], fill=rgba((92, 86, 70), 145), outline=rgba(dark, 100))
    if "幽冥" in archetype or any(token in name for token in ("冥", "血", "月", "魔", "蜃")):
        for i in range(6):
            x = cx - 120 + i * 45
            draw.arc((x, 132 + i % 2 * 22, x + 86, 430), 210, 306, fill=rgba((76, 42, 88), 110), width=5)
    if "万毒" in archetype or any(token in name for token in ("蛇", "蛛", "蟾", "蜈")):
        for side in (-1, 1):
            draw.polygon([(cx + side * 24, 314), (cx + side * 10, 368), (cx + side * 4, 318)], fill=rgba((238, 236, 205), 220))
            for i in range(3):
                y = 304 + i * 33
                draw.line((cx + side * 72, y, cx + side * (150 + i * 10), y + 24), fill=rgba((48, 86, 54), 150), width=5)

def faction_variant_color(style: FactionStyle, record: dict[str, Any], amount: int = 0) -> tuple[int, int, int]:
    seed = stable_int(str(record.get("id") or record.get("name") or style.key))
    drift = (seed % 41) - 20 + amount
    return shade(style.accent, drift)


def draw_polyline(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], color: tuple[int, int, int, int], width: int = 3) -> None:
    if len(points) >= 2:
        draw.line(points, fill=color, width=width, joint="curve")


def draw_anime_aura(draw: ImageDraw.ImageDraw, width: int, height: int, style: FactionStyle, record: dict[str, Any]) -> None:
    seed = str(record.get("id") or record.get("name") or style.key)
    rng = random.Random(stable_int(f"aura:{seed}"))
    cx = width // 2
    for radius, alpha in ((122, 36), (92, 48), (58, 54)):
        draw.ellipse((cx - radius, 72, cx + radius, 72 + radius * 2), outline=rgba(style.aura, alpha), width=4)
    for _ in range(12):
        x = rng.randint(48, width - 48)
        y = rng.randint(88, height - 92)
        length = rng.randint(28, 74)
        draw.line((x, y, x + rng.randint(-20, 24), y - length), fill=rgba(style.aura, rng.randint(42, 88)), width=2)


def draw_anime_face(draw: ImageDraw.ImageDraw, cx: int, top: int, skin: tuple[int, int, int], ink: tuple[int, int, int], eye: tuple[int, int, int], stern: bool) -> None:
    face = [(cx - 48, top + 36), (cx - 42, top + 104), (cx - 24, top + 142), (cx, top + 154), (cx + 24, top + 142), (cx + 42, top + 104), (cx + 48, top + 36)]
    draw.polygon(face, fill=rgba(skin, 255), outline=rgba(ink, 170))
    draw.polygon([(cx - 42, top + 40), (cx + 42, top + 40), (cx + 28, top + 104), (cx - 22, top + 112)], fill=rgba(shade(skin, 14), 55))
    eye_y = top + 82
    tilt = -3 if stern else 2
    for side in (-1, 1):
        ex = cx + side * 22
        draw.line((ex - 18, eye_y + side * tilt, ex + 14, eye_y - side * tilt), fill=rgba(ink, 215), width=4)
        draw.ellipse((ex - 8, eye_y - 4, ex + 8, eye_y + 9), fill=rgba((248, 246, 230), 235))
        draw.ellipse((ex - 4, eye_y - 1, ex + 4, eye_y + 8), fill=rgba(eye, 245))
    draw.line((cx - 7, top + 101, cx + 2, top + 116), fill=rgba(ink, 105), width=2)
    mouth_y = top + 130
    draw.arc((cx - 15, mouth_y - 8, cx + 15, mouth_y + 8), 12 if stern else 190, 168 if stern else 350, fill=rgba(ink, 130), width=2)


def draw_anime_hair(draw: ImageDraw.ImageDraw, cx: int, top: int, hair: tuple[int, int, int], aura: tuple[int, int, int], variant: int) -> None:
    draw.pieslice((cx - 62, top - 12, cx + 62, top + 112), 180, 360, fill=rgba(hair, 255))
    draw.ellipse((cx - 52, top + 12, cx + 52, top + 92), fill=rgba(hair, 255))
    bang_count = 5 + variant % 3
    for i in range(bang_count):
        x = cx - 48 + i * (96 // max(1, bang_count - 1))
        tip = cx - 34 + i * (68 // max(1, bang_count - 1)) + ((variant + i) % 9 - 4)
        draw.polygon([(x - 18, top + 28), (x + 20, top + 24), (tip, top + 96 + (i % 2) * 14)], fill=rgba(shade(hair, 8 - i * 2), 250))
    for side in (-1, 1):
        draw.polygon([(cx + side * 42, top + 18), (cx + side * 82, top + 118), (cx + side * 34, top + 170)], fill=rgba(shade(hair, -14), 238))
    if variant % 4 == 0:
        draw.ellipse((cx - 16, top - 22, cx + 16, top + 10), fill=rgba(hair, 245), outline=rgba(aura, 130), width=2)
        draw.line((cx, top - 42, cx, top - 8), fill=rgba(aura, 150), width=3)


def draw_xuanhuan_humanoid(draw: ImageDraw.ImageDraw, width: int, height: int, style: FactionStyle, record: dict[str, Any]) -> None:
    seed = str(record.get("id") or record.get("name") or style.key)
    rng = random.Random(stable_int(f"anime-human:{seed}"))
    cx = width // 2
    ink = style.accent_dark
    robe = faction_variant_color(style, record, 8)
    robe_dark = mix(style.accent_dark, robe, 0.18)
    skin = (214 + rng.randint(-10, 8), 178 + rng.randint(-8, 12), 146 + rng.randint(-10, 10))
    hair_options = [(28, 34, 40), (38, 30, 42), (52, 42, 34), (32, 46, 58)]
    hair = hair_options[stable_int(seed) % len(hair_options)]
    if style.name in {"邪神", "魔神", "域外天魔"}:
        hair = mix(hair, style.accent_dark, 0.45)
    face_top = 128
    shoulder_y = 360

    draw_anime_aura(draw, width, height, style, record)
    draw_symbol(draw, cx + rng.randint(-18, 18), 112, 1, style)
    # Back hair and mantle.
    draw.polygon([(cx - 74, face_top + 44), (cx - 106, 330), (cx - 62, 430), (cx + 62, 430), (cx + 106, 330), (cx + 74, face_top + 44)], fill=rgba(shade(hair, -10), 235))
    draw.polygon([(cx - 148, height - 44), (cx - 118, shoulder_y - 34), (cx - 48, shoulder_y - 76), (cx, shoulder_y - 88), (cx + 48, shoulder_y - 76), (cx + 118, shoulder_y - 34), (cx + 148, height - 44)], fill=rgba(robe_dark, 250), outline=rgba(ink, 180))
    draw.polygon([(cx - 118, height - 44), (cx - 82, shoulder_y - 48), (cx - 20, shoulder_y - 76), (cx, shoulder_y + 18), (cx + 20, shoulder_y - 76), (cx + 82, shoulder_y - 48), (cx + 118, height - 44)], fill=rgba(robe, 248))
    draw.polygon([(cx - 42, shoulder_y - 74), (cx, shoulder_y + 18), (cx - 20, height - 56), (cx - 78, height - 44)], fill=rgba(shade(robe, 36), 208))
    draw.polygon([(cx + 42, shoulder_y - 74), (cx, shoulder_y + 18), (cx + 20, height - 56), (cx + 78, height - 44)], fill=rgba(shade(robe, -10), 220))
    draw.line((cx, shoulder_y - 78, cx, height - 58), fill=rgba((244, 232, 190), 155), width=5)
    for side in (-1, 1):
        pauldron = [(cx + side * 64, shoulder_y - 58), (cx + side * 142, shoulder_y - 14), (cx + side * 116, shoulder_y + 54), (cx + side * 48, shoulder_y + 20)]
        draw.polygon(pauldron, fill=rgba(mix(robe_dark, (232, 210, 158), 0.24), 235), outline=rgba(ink, 155))
        draw.line((cx + side * 58, shoulder_y - 18, cx + side * 124, shoulder_y + 26), fill=rgba(style.aura, 105), width=3)

    draw_anime_face(draw, cx, face_top, skin, ink, style.aura, style.name in {"邪修", "邪神", "伪神", "魔神", "域外天魔"})
    draw_anime_hair(draw, cx, face_top, hair, style.aura, stable_int(seed) % 11)
    # Faction-specific details.
    if style.symbol == "halo":
        draw.ellipse((cx - 96, face_top - 42, cx + 96, face_top + 150), outline=rgba(style.aura, 135), width=5)
        draw.ellipse((cx - 74, face_top - 20, cx + 74, face_top + 128), outline=rgba((250, 235, 170), 105), width=3)
    elif style.symbol in {"horns", "eye", "star"}:
        for side in (-1, 1):
            draw.polygon([(cx + side * 36, face_top + 12), (cx + side * 86, face_top - 58), (cx + side * 62, face_top + 56)], fill=rgba(style.accent_dark, 235), outline=rgba(style.aura, 120))
    elif style.symbol == "grid":
        panel = (cx + 74, face_top + 42, cx + 142, face_top + 126)
        draw.rounded_rectangle(panel, radius=8, fill=rgba((18, 44, 48), 198), outline=rgba(style.aura, 185), width=3)
        for i in range(4):
            y = panel[1] + 14 + i * 16
            draw.line((panel[0] + 10, y, panel[2] - 10, y), fill=rgba(style.aura, 150), width=2)
    elif style.symbol == "blade":
        draw.polygon([(cx - 124, 390), (cx - 106, 394), (cx - 38, 164), (cx - 52, 158)], fill=rgba((226, 218, 188), 160), outline=rgba(ink, 120))
    elif style.symbol == "rune":
        draw.polygon([(cx, 92), (cx + 42, 126), (cx, 160), (cx - 42, 126)], outline=rgba(style.aura, 140), width=4)


def draw_xuanhuan_beast(draw: ImageDraw.ImageDraw, width: int, height: int, style: FactionStyle, record: dict[str, Any]) -> None:
    seed = str(record.get("id") or record.get("name") or style.key)
    rng = random.Random(stable_int(f"anime-beast:{seed}"))
    cx = width // 2
    name = str(record.get("name") or "")
    archetype = str(record.get("archetype") or "")
    ink = style.accent_dark
    base = faction_variant_color(style, record, 4)
    mane = shade(ink, 20)
    draw_anime_aura(draw, width, height, style, record)
    # Back silhouette: wings, shell, or spectral smoke by archetype.
    if "雷鹏" in name or "鹰" in name or "鹏" in name or "金羽" in archetype:
        for side in (-1, 1):
            draw.polygon([(cx + side * 18, 284), (cx + side * 164, 122), (cx + side * 136, 372)], fill=rgba((38, 50, 76), 188), outline=rgba(style.aura, 108))
            for i in range(5):
                draw.line((cx + side * (38 + i * 22), 220 + i * 16, cx + side * (128 + i * 6), 354), fill=rgba(style.aura, 90), width=3)
    if "搬山" in archetype or any(token in name for token in ("龟", "象", "犀", "山", "石", "甲")):
        draw.polygon([(cx - 142, 304), (cx - 86, 170), (cx, 132), (cx + 86, 170), (cx + 142, 304), (cx + 102, 428), (cx - 102, 428)], fill=rgba((82, 78, 62), 205), outline=rgba(ink, 140))
    if "幽冥" in archetype or any(token in name for token in ("冥", "血", "月", "魔", "蜃")):
        for i in range(8):
            x = cx - 150 + i * 42
            draw.arc((x, 96 + (i % 2) * 28, x + 100, 470), 212, 310, fill=rgba((74, 38, 88), 105), width=5)

    # Torso and long beast head.
    draw.polygon([(cx - 118, height - 42), (cx - 94, 330), (cx - 52, 268), (cx, 252), (cx + 52, 268), (cx + 94, 330), (cx + 118, height - 42)], fill=rgba(ink, 245), outline=rgba(ink, 190))
    draw.polygon([(cx - 86, height - 46), (cx - 64, 342), (cx, 306), (cx + 64, 342), (cx + 86, height - 46)], fill=rgba(base, 240))
    head = [(cx - 72, 180), (cx - 52, 124), (cx, 86), (cx + 52, 124), (cx + 72, 180), (cx + 58, 284), (cx + 20, 326), (cx, 338), (cx - 20, 326), (cx - 58, 284)]
    draw.polygon(head, fill=rgba(base, 255), outline=rgba(ink, 210))
    draw.polygon([(cx - 58, 138), (cx - 116, 62), (cx - 86, 194)], fill=rgba(mane, 245), outline=rgba(style.aura, 90))
    draw.polygon([(cx + 58, 138), (cx + 116, 62), (cx + 86, 194)], fill=rgba(mane, 245), outline=rgba(style.aura, 90))
    for side in (-1, 1):
        horn_len = 86 + rng.randint(0, 38)
        draw.polygon([(cx + side * 28, 122), (cx + side * 62, 122 - horn_len), (cx + side * 8, 106)], fill=rgba((232, 211, 160), 235), outline=rgba(ink, 120))
        eye_x = cx + side * 28
        draw.polygon([(eye_x - side * 20, 210), (eye_x + side * 16, 204), (eye_x + side * 24, 218), (eye_x - side * 12, 224)], fill=rgba((22, 18, 16), 240))
        draw.ellipse((eye_x - 4, 208, eye_x + 4, 218), fill=rgba(style.aura, 255))
    snout = [(cx - 42, 252), (cx - 18, 298), (cx, 312), (cx + 18, 298), (cx + 42, 252), (cx + 28, 278), (cx, 292), (cx - 28, 278)]
    draw.polygon(snout, fill=rgba(shade(base, 26), 245), outline=rgba(ink, 140))
    draw.line((cx, 288, cx, 318), fill=rgba(ink, 150), width=3)
    for i in range(6):
        y = 342 + i * 22
        draw.arc((cx - 78, y - 44, cx + 78, y + 50), 20, 160, fill=rgba(shade(base, 54), 96), width=4)
    if "玄冰" in archetype or any(token in name for token in ("冰", "霜", "寒")):
        for i in range(7):
            x = cx - 96 + i * 32
            draw.polygon([(x, 184), (x + 14, 90 - (i % 2) * 18), (x + 32, 184)], fill=rgba((198, 228, 238), 175), outline=rgba(ink, 70))
    if "火脉" in archetype or any(token in name for token in ("火", "焰", "赤", "离")):
        for i in range(7):
            x = cx - 102 + i * 34
            draw.polygon([(x, 196), (x + 18, 92 + (i % 2) * 20), (x + 38, 196)], fill=rgba((230, 92, 40), 150), outline=rgba((255, 211, 92), 95))
    if "万毒" in archetype or any(token in name for token in ("蛇", "蛛", "蟾", "蜈")):
        for side in (-1, 1):
            draw.polygon([(cx + side * 26, 286), (cx + side * 10, 360), (cx + side * 2, 290)], fill=rgba((238, 236, 205), 225))
            draw.line((cx + side * 64, 330, cx + side * 148, 382), fill=rgba((42, 92, 58), 150), width=6)
def draw_frame(draw: ImageDraw.ImageDraw, width: int, height: int, style: FactionStyle) -> None:
    margin = 18
    draw.rounded_rectangle((margin, margin, width - margin, height - margin), radius=28, outline=rgba(style.accent_dark, 230), width=8)
    draw.rounded_rectangle((margin + 10, margin + 10, width - margin - 10, height - margin - 10), radius=22, outline=rgba((250, 238, 202), 190), width=3)
    for x, y in ((38, 38), (width - 38, 38), (38, height - 38), (width - 38, height - 38)):
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=rgba(style.accent, 220), outline=rgba(style.accent_dark, 200), width=3)


def render_portrait(record: dict[str, Any]) -> Image.Image:
    scale = RENDER_SCALE
    width, height = CARD_SIZE[0] * scale, CARD_SIZE[1] * scale
    style = style_for_faction(record["faction"])
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw_card_background(draw, width, height, style, record["id"])
    add_texture(image, record["id"])
    draw = ImageDraw.Draw(image)
    if style.role_type == "beast":
        draw_xuanhuan_beast(draw, width, height, style, record)
    else:
        draw_xuanhuan_humanoid(draw, width, height, style, record)
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    vdraw.rounded_rectangle((0, 0, width, height), radius=32 * scale, outline=rgba(style.accent_dark, 90), width=30)
    image = Image.alpha_composite(image, vignette.filter(ImageFilter.GaussianBlur(8 * scale)))
    draw = ImageDraw.Draw(image)
    draw_frame(draw, width, height, style)
    image = image.resize(CARD_SIZE, Image.Resampling.LANCZOS)
    return image


def clean_portrait_dir() -> None:
    PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)
    for path in PORTRAIT_DIR.glob("*.png"):
        path.unlink()


def write_catalog(records: list[dict[str, Any]]) -> None:
    manifest = {
        "schema_version": "1.0",
        "style_name": "东方玄幻动漫半身像",
        "card_size": {"width": CARD_SIZE[0], "height": CARD_SIZE[1]},
        "usage": "统一角色画像库，可供秘境首领战报、斗兽、对战卡牌和图鉴复用。",
        "factions": [
            {"key": style.key, "name": style.name, "role_type": style.role_type, "symbol": style.symbol}
            for style in FACTIONS
        ],
        "characters": records,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (CATALOG_DIR / "catalog.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 角色图鉴",
        "",
        "统一风格：东方玄幻动漫半身像。所有角色均可按 `id` 或名称从 `assets/character_portraits/manifest.json` 调用。",
        "",
        "| ID | 名称 | 势力 | 境界 | 故事 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in records:
        story = str(record["story"]).replace("|", "、")
        lines.append(f"| `{record['id']}` | {record['name']} | {record['faction']} | {record['realm']} | {story} |")
    (CATALOG_DIR / "catalog.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_contact_sheet(records: list[dict[str, Any]]) -> None:
    thumb_w, thumb_h = 90, 130
    label_h = 34
    cols = 10
    rows = math.ceil(len(records) / cols)
    sheet = Image.new("RGBA", (cols * thumb_w, rows * (thumb_h + label_h)), (246, 242, 231, 255))
    draw = ImageDraw.Draw(sheet)
    font = load_font(11)
    for index, record in enumerate(records):
        col = index % cols
        row = index // cols
        x = col * thumb_w
        y = row * (thumb_h + label_h)
        portrait = Image.open(PORTRAIT_DIR / record["portrait"]).convert("RGBA").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.alpha_composite(portrait, (x, y))
        label = f"{record['name']}"
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + label_h), fill=(246, 242, 231, 255))
        draw.text((x + 4, y + thumb_h + 4), label[:8], font=font, fill=(38, 42, 46))
        draw.text((x + 4, y + thumb_h + 18), str(record["faction"])[:8], font=font, fill=(96, 90, 76))
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(CATALOG_DIR / "contact_sheet.jpg", quality=88)


def main() -> None:
    records = build_character_records()
    clean_portrait_dir()
    for record in records:
        render_portrait(record).save(PORTRAIT_DIR / record["portrait"])
    write_catalog(records)
    write_contact_sheet(records)
    print(f"wrote {len(records)} portraits to {PORTRAIT_DIR}")


if __name__ == "__main__":
    main()
