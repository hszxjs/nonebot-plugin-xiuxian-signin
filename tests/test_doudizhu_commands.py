"""斗地主命令模块回归测试。

起因：R-18 拆分 ``commands/doudizhu.py`` 时漏掉全部标准库导入，且把本地函数写成
``_g.`` 调用、入口 helper 反而裸用。``ddz_new_deck()`` 一调用就 NameError，
即斗地主开桌/发牌在线上必然崩溃，而当时没有任何测试覆盖这个模块。

本文件守住三件事：
1. 模块可导入且牌引擎可实际执行（防漏 import 回归）；
2. 牌型识别与压牌规则符合预期；
3. 整局机器人对局能跑到底（防状态机中途抛异常）。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from nonebot_plugin_xiuxian_signin.commands import doudizhu as ddz

DOUDIZHU_SOURCE = Path(ddz.__file__)


def _new_table() -> dict:
    return {
        "group_id": "10000",
        "players": [
            {"id": str(index), "name": f"p{index}", "bot": True, "hand": [], "bid": None}
            for index in range(3)
        ],
    }


def test_new_deck_has_54_cards() -> None:
    deck = ddz.ddz_new_deck()
    assert len(deck) == 54
    assert deck.count("小王") == 1
    assert deck.count("大王") == 1
    # 牌面不含花色，13 种点数各 4 张。
    counts: dict[str, int] = {}
    for card in deck:
        counts[card] = counts.get(card, 0) + 1
    assert len(counts) == 15
    assert all(count == 4 for card, count in counts.items() if card not in {"小王", "大王"})


def test_deal_splits_17_17_17_and_bottom() -> None:
    table = _new_table()
    ddz.ddz_deal(table)
    hands = [player["hand"] for player in table["players"]]
    assert [len(hand) for hand in hands] == [17, 17, 17]
    assert len(table["bottom"]) == 3
    assert table["phase"] == "bidding"
    dealt = sum(hands, []) + list(table["bottom"])
    assert sorted(dealt) == sorted(ddz.ddz_new_deck())


@pytest.mark.parametrize(
    ("cards", "label"),
    [
        (["3"], "单牌"),
        (["3", "4", "5", "6", "7"], "5连顺"),
        (["3", "3", "3", "3"], "3重雷劫"),
        (["小王", "大王"], "天罚雷劫"),
        (["5", "5", "5", "9"], "三带一"),
        (["3", "3", "3", "4", "4", "4", "7", "8"], "飞舟带翼2舱"),
    ],
)
def test_analyze_cards_recognizes_types(cards: list[str], label: str) -> None:
    analyzed = ddz.ddz_analyze_cards(cards)
    assert analyzed is not None, f"{cards} 应被识别为合法牌型"
    assert analyzed["label"] == label


def test_analyze_cards_rejects_invalid() -> None:
    assert ddz.ddz_analyze_cards(["3", "4"]) is None


def test_can_beat_rules() -> None:
    five = ddz.ddz_analyze_cards(["5"])
    nine = ddz.ddz_analyze_cards(["9"])
    bomb = ddz.ddz_analyze_cards(["4", "4", "4", "4"])
    rocket = ddz.ddz_analyze_cards(["小王", "大王"])
    assert five and nine and bomb and rocket
    assert ddz.ddz_can_beat(nine, five)
    assert not ddz.ddz_can_beat(five, nine)
    assert ddz.ddz_can_beat(bomb, nine)
    assert ddz.ddz_can_beat(rocket, bomb)
    assert not ddz.ddz_can_beat(bomb, rocket)


def test_full_bot_game_finishes_without_error() -> None:
    table = _new_table()
    ddz.ddz_deal(table)
    ddz.ddz_finalize_landlord(table, "0")
    ddz.ddz_start_play(table)
    assert len(table["players"][0]["hand"]) == 20  # 地主 17 + 底牌 3

    remaining = sum(len(player["hand"]) for player in table["players"])
    winner = None
    for _ in range(500):
        player = ddz.ddz_current_player(table)
        if table.get("last_play") and str(table.get("last_player")) != str(player.get("id")):
            played, _line = ddz.ddz_bot_play(player, table)
            if not played:
                table["pass_count"] = int(table.get("pass_count", 0)) + 1
                if int(table.get("pass_count", 0)) >= 2:
                    for index, candidate in enumerate(table["players"]):
                        if str(candidate.get("id")) == str(table.get("last_player")):
                            table["current"] = index
                            break
                    table["last_play"] = None
                    table["pass_count"] = 0
                    continue
        else:
            ddz.ddz_bot_play(player, table)
        total = sum(len(candidate["hand"]) for candidate in table["players"])
        assert total < remaining or total == remaining
        remaining = total
        if not player.get("hand"):
            winner = player["id"]
            break
        ddz.ddz_next_turn(table)

    assert winner is not None, "500 回合内应有人出完手牌"
    assert table["players"][int(winner)]["hand"] == []


def test_deferred_g_attributes_match_entry_module() -> None:
    """``_g.`` 的指向必须与模块边界一致（纯静态检查）。

    拆分时出现的真实故障：本地定义的 ``start_forced_normal_duel`` 被写成
    ``_g.start_forced_normal_duel``（入口模块里没有），入口 helper 反而裸用。
    ruff 的 F821 只能发现后者，前者是合法属性访问、静态检查看不出来。

    这里不用 ``import nonebot_plugin_xiuxian_signin``：几个历史测试会往
    ``sys.modules`` 塞空壳父包以绕开 NoneBot 初始化，导入顺序会影响结果。
    直接对两份源码做 AST 比对，不受导入状态影响。
    """
    entry_source = (DOUDIZHU_SOURCE.parents[1] / "__init__.py").read_text(encoding="utf-8")
    command_source = DOUDIZHU_SOURCE.read_text(encoding="utf-8")

    referenced = set(re.findall(r"_g\.([A-Za-z_][A-Za-z0-9_]*)", command_source))
    assert referenced, "预期存在 _g 延迟访问"

    local_names = _top_level_names(command_source)
    entry_names = _top_level_names(entry_source)

    should_be_local = sorted(referenced & local_names)
    assert not should_be_local, f"这些名字本地已定义，不该走 _g：{should_be_local}"

    missing = sorted(referenced - entry_names)
    assert not missing, f"插件入口模块没有这些名字，_g 会 AttributeError：{missing}"


def _top_level_names(source: str) -> set[str]:
    """收集模块顶层可直接访问的名字（def/class/赋值/import 别名）。"""
    import ast

    names: set[str] = set()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return names
