
from __future__ import annotations

import importlib.util
import sys
import types
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

domain = sys.modules[f"{PKG_NAME}.domain"]
cards = sys.modules[f"{PKG_NAME}.cards"]


def reward(tier: str, grade: str, category: str, name: str) -> dict[str, str]:
    return {"tier": tier, "grade": grade, "category": category, "name": name, "item_name": name, "description": name}


record = domain.UserRecord(
    user_id="3305167706",
    root=domain.Root(
        "\u53d8\u5f02\u7075\u6839",
        5,
        "\u6781\u54c1",
        3,
        "\u96f7",
        purity=98,
        sources=["\u91d1", "\u6c34"],
        mutated=True,
    ),
    sign_count=88,
    total_exp=66666,
    realm_index=5,
    realm_exp=1888,
    spirit_stones=1234567,
    spirit_liquid=2680,
    foundation_type="\u5929\u9053\u7b51\u57fa",
    realm_marks={"2": "\u5929\u9053\u7b51\u57fa", "3": "\u4e00\u54c1\u91d1\u4e39", "4": "\u5929\u8c61\u5143\u5a74", "5": "\u6cd5\u76f8\u5316\u795e"},
    cultivation_route="\u5251\u4fee",
    faction_identity="\u5929\u673a\u9601\u957f\u8001",
    special_abilities=["\u516b\u7981", "\u4e5d\u79d8\u00b7\u884c\u5b57\u79d8", "\u9cb2\u9e4f\u6781\u901f"],
    mystic_boss_daily_attempts=1,
    mystic_boss_daily_bonus=1,
)
record.equipped_artifacts = {
    "\u4e3b\u624b": reward("\u4ed9\u9636", "\u6781\u54c1", "\u7075\u5668", "\u592a\u865a\u65a9\u661f\u5251"),
    "\u526f\u624b": reward("\u5730\u9636", "\u4e0a\u54c1", "\u7075\u5668", "\u7384\u94c1\u9547\u9b42\u76fe"),
    "\u62a4\u7532": reward("\u5929\u9636", "\u4e2d\u54c1", "\u7075\u5668", "\u4e91\u7eb9\u62a4\u5fc3\u7532"),
}
record.equipped_artifact = record.equipped_artifacts["\u4e3b\u624b"]
record.equipped_method = reward("\u5929\u9636", "\u6781\u54c1", "\u529f\u6cd5", "\u9752\u5e1d\u957f\u751f\u7ecf")
record.equipped_array = reward("\u5929\u9636", "\u4e0a\u54c1", "\u9635\u76d8", "\u5468\u5929\u661f\u6597\u9635\u76d8")
record.equipped_talisman = reward("\u7384\u9636", "\u4e0a\u54c1", "\u7b26\u7b93", "\u91d1\u7532\u62a4\u8eab\u7b26")
record.equipped_puppet = reward("\u5730\u9636", "\u4e2d\u54c1", "\u5080\u5121", "\u9752\u7389\u673a\u5173\u4eba")
record.life_artifact = reward("\u4ed9\u9636", "\u6781\u54c1", "\u7075\u5668", "\u9752\u7af9\u8702\u4e91\u5251")
record.equipped_immortal_seed = reward("\u4ed9\u9636", "\u4e0a\u54c1", "\u4ed9\u79cd", "\u67f3\u795e\u6d85\u69c3\u4ed9\u79cd")
record.array_proficiency = {"\u5468\u5929\u661f\u6597\u9635\u76d8": 320}

out = ROOT / "assets" / "panel_previews" / "adventure_preview_latest.png"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(cards.render_adventure_card(record, nickname="\u843d\u96e8\u4fee\u58eb"))
print(out)
