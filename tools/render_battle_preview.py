from __future__ import annotations

import importlib.util
import sys
import types
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_NAME = "nonebot_plugin_xiuxian_signin"

pkg = types.ModuleType(PKG_NAME)
pkg.__path__ = [str(ROOT)]
sys.modules[PKG_NAME] = pkg
for mod_name in ["domain", "cards"]:
    spec = importlib.util.spec_from_file_location(f"{PKG_NAME}.{mod_name}", ROOT / f"{mod_name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"{PKG_NAME}.{mod_name}"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)

cards = sys.modules[f"{PKG_NAME}.cards"]
def fetch_player_avatar(user_id: str) -> bytes | None:
    if not user_id or not user_id.isdigit():
        return None
    url = f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = response.read()
    except Exception:
        return None
    return data or None


def fighter(
    user_id: str,
    nickname: str,
    realm: str,
    root: str,
    race: str,
    physique: str,
    method: str,
    method_kind: str,
    talisman: str,
    abilities: list[str],
    techniques: list[str],
    hp: int,
    max_hp: int,
    mana: int,
    max_mana: int,
    mana_spent: int,
    physical_hits: int,
    trait_triggers: int,
    talisman_power: int,
    cooldowns: dict[str, int],
) -> dict[str, object]:
    return {
        "user_id": user_id,
        "nickname": nickname,
        "realm": realm,
        "root": root,
        "race": race,
        "physique": physique,
        "method": method,
        "method_kind": method_kind,
        "talisman": talisman,
        "abilities": abilities,
        "triggered_techniques": techniques,
        "hp": hp,
        "max_hp": max_hp,
        "mana": mana,
        "max_mana": max_mana,
        "mana_spent": mana_spent,
        "physical_hits": physical_hits,
        "trait_triggers": trait_triggers,
        "talisman_power": talisman_power,
        "cooldowns": cooldowns,
    }


result = {
    "title": "普通斗法战报",
    "summary": "落雨修士 以星律流影破阵，六十息内完成普通斗法",
    "winner_id": "preview_left",
    "elapsed_seconds": 48,
    "duration_seconds": 60,
    "left": fighter(
        "3305167706",
        "落雨修士",
        "化神后期 · 法相化神",
        "极品变异雷灵根",
        "人族",
        "剑心通明",
        "青衡长生经",
        "剑修",
        "金甲护身符",
        ["初阈", "星律-流影篇", "风掣疾行"],
        ["流影斩", "雷引剑诀", "阵眼压制"],
        8650,
        9800,
        2140,
        3600,
        1460,
        3,
        2,
        620,
        {"星律-流影篇": 2},
    ),
    "right": fighter(
        "10001",
        "云台剑客",
        "炼虚初期 · 洞虚道体",
        "上品冰灵根",
        "人族",
        "玄霜剑骨",
        "玄霜照影诀",
        "剑修",
        "裂隙护符",
        ["玄霜照影", "踏雪无痕", "剑气凝冰"],
        ["霜河剑", "冰魄回环", "寒灯守心"],
        0,
        11200,
        380,
        4200,
        3820,
        5,
        4,
        780,
        {"玄霜照影": 4, "踏雪无痕": 1},
    ),
    "timeline": [
        "第01息：落雨修士踏入剑阵，青衡长生经运转，灵力护住周身经脉。",
        "第05息：云台剑客以霜河剑试探，剑气沿阵幕结成薄冰。",
        "第09息：落雨修士发动初阈，识海短暂澄明，提前捕捉到对手身法落点。",
        "第14息：流影斩连破三重剑幕，云台剑客生命跌至七成，玄霜照影进入冷却。",
        "第20息：冰魄回环触发，落雨修士被迫消耗灵力维持剑阵中枢。",
        "第27息：风掣疾行绕至背后，雷引剑诀击穿寒灯守心的护势。",
        "第33息：星律-流影篇展开，剑光与阵纹重合，云台剑客无法再次拉开距离。",
        "第41息：落雨修士以阵眼压制封锁冰魄回环，反手一剑破开霜河。",
        "第48息：云台剑客灵力归零，斗法结束，胜者为落雨修士。",
    ],
    "footer": "预览：普通斗法战报会展示双方血量、灵力、神通、战技、资源消耗与时间线。",
}

left_avatar = fetch_player_avatar(str(result["left"]["user_id"]))
right_avatar = fetch_player_avatar(str(result["right"]["user_id"]))

out = ROOT / "build" / "previews" / "battle_preview_latest.png"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(cards.render_battle_card(result, left_avatar=left_avatar, right_avatar=right_avatar))
print(out)
