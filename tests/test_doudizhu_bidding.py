"""斗地主叫分/抢地主状态机（R-19 补零）。

``test_doudizhu_commands.py`` 已覆盖发牌、牌型识别、压牌与整局机器人对局，但叫分到抢地主
这一段的迁移完全没测过——而它是「一句话决定谁是地主」的入口，出错表现为整局拿不到地主，
玩家只看到面板卡在叫分阶段。

本文件覆盖：
1. ``ddz_parse_bid`` 的各类输入（含越界值——1..3 的钳制在 handler 层，这里锁定分工）；
2. 无人叫分必须重新洗牌，有人叫到 3 分必须直接进入抢地主；
3. 抢地主阶段「除候选地主外全部表态」才结算，且候选地主不参与；
4. 定地主后地主手牌 20 张、出牌顺序从地主开始；
5. 机器人加倍判断与威压概率的取值范围。
"""
from __future__ import annotations

import pytest

from nonebot_plugin_xiuxian_signin.commands import doudizhu as ddz


def _table() -> dict:
    return {
        "group_id": "10000",
        "players": [
            {"id": str(index), "name": f"p{index}", "bot": False, "hand": [], "bid": None}
            for index in range(3)
        ],
    }


@pytest.mark.parametrize(
    ("text", "highest", "expected"),
    [
        ("不叫", 0, 0),
        ("叫分 1", 0, 1),
        ("叫分 2", 1, 2),
        ("叫地主", 0, 1),
        ("叫地主", 2, 3),
        ("叫地主", 3, 3),
        ("随便说点什么", 0, None),
        ("叫分", 0, None),
    ],
)
def test_parse_bid(text: str, highest: int, expected) -> None:
    assert ddz.ddz_parse_bid(text, highest) == expected


def test_parse_bid_does_not_clamp_digit_form() -> None:
    """数字形式不在解析层钳制：越界值由 handler 判为「叫分失败」，两层分工不能混。

    这条断言看起来反直觉，但它锁住的是「叫分 99 不会被静默当成叫分 3」——
    如果哪天有人在解析层加 clamp，玩家输入越界会得到静默降级而不是明确报错。
    """
    assert ddz.ddz_parse_bid("叫分 99", 0) == 99


def test_apply_bid_tracks_highest_and_candidate() -> None:
    table = _table()
    first, second = table["players"][0], table["players"][1]

    assert "叫分 1" in ddz.ddz_apply_bid(table, first, 1)
    assert table["highest_bid"] == 1
    assert table["landlord_candidate"] == "0"
    assert table["bid_count"] == 1

    assert "不叫" in ddz.ddz_apply_bid(table, second, 0)
    assert table["highest_bid"] == 1, "低分不应覆盖最高分"
    assert table["landlord_candidate"] == "0"
    assert table["bid_count"] == 2


def test_after_bid_with_no_bidder_redeals() -> None:
    table = _table()
    ddz.ddz_deal(table)
    for player in table["players"]:
        ddz.ddz_apply_bid(table, player, 0)
    result = ddz.ddz_after_bid(table)
    assert result is not None and "重新洗牌" in result
    assert table["phase"] == "bidding"
    assert table["highest_bid"] == 0
    assert table["bid_count"] == 0
    assert all(len(player["hand"]) == 17 for player in table["players"])


def test_after_bid_with_three_points_enters_rob() -> None:
    table = _table()
    ddz.ddz_deal(table)
    ddz.ddz_apply_bid(table, table["players"][0], 3)
    result = ddz.ddz_after_bid(table)
    assert result is not None and "抢地主阶段" in result
    assert table["phase"] == "rob"
    assert table["landlord_candidate"] == "0"
    assert table["original_landlord"] == "0"
    assert table["rob_passes"] == set()


def test_after_bid_advances_turn_when_undecided() -> None:
    table = _table()
    ddz.ddz_deal(table)
    table["current"] = 0
    ddz.ddz_apply_bid(table, table["players"][0], 1)
    assert ddz.ddz_after_bid(table) is None
    assert table["current"] == 1, "未定地主时应轮到下一位叫分"


def test_rob_requires_every_other_player() -> None:
    table = _table()
    ddz.ddz_deal(table)
    ddz.ddz_apply_bid(table, table["players"][0], 3)
    ddz.ddz_after_bid(table)

    assert not ddz.ddz_rob_needed_done(table)
    table["rob_passes"].add("1")
    assert not ddz.ddz_rob_needed_done(table), "还有人没表态时不能结算"
    table["rob_passes"].add("2")
    assert ddz.ddz_rob_needed_done(table)


def test_candidate_is_excluded_from_rob_requirement() -> None:
    table = _table()
    ddz.ddz_deal(table)
    ddz.ddz_apply_bid(table, table["players"][2], 3)
    ddz.ddz_after_bid(table)
    table["rob_passes"].update({"0", "1"})
    assert ddz.ddz_rob_needed_done(table), "候选地主自己不参与抢地主"
    # 候选地主即使被塞进 rob_passes 也不影响判定
    table["rob_passes"].add("2")
    assert ddz.ddz_rob_needed_done(table)


def test_finalize_landlord_deals_bottom_and_starts_from_landlord() -> None:
    table = _table()
    ddz.ddz_deal(table)
    table["current"] = 2
    ddz.ddz_finalize_landlord(table, "1")

    assert table["landlord"] == "1"
    assert table["phase"] == "double"
    assert len(table["players"][1]["hand"]) == 20
    assert len(table["players"][0]["hand"]) == 17

    ddz.ddz_start_play(table)
    assert table["phase"] == "playing"
    assert ddz.ddz_current_player(table)["id"] == "1", "出牌必须从地主开始"


def test_user_can_act_only_on_turn() -> None:
    table = _table()
    ddz.ddz_deal(table)
    table["current"] = 1
    assert ddz.ddz_user_can_act(table, "1")
    assert not ddz.ddz_user_can_act(table, "0")


def test_find_hint_returns_legal_play_or_none() -> None:
    hand = ["3", "3", "5", "小王", "大王"]
    hint = ddz.ddz_find_hint(hand, None)
    assert hint, "首出必须有可出的牌"
    analyzed = ddz.ddz_analyze_cards(hint)
    assert analyzed is not None
    assert ddz.ddz_has_cards(hand, hint)

    rocket = ddz.ddz_analyze_cards(["小王", "大王"])
    assert rocket is not None
    assert ddz.ddz_find_hint(["3", "4", "5"], rocket) is None, "压不过天罚雷劫时应返回 None"


@pytest.mark.parametrize("hand", [["小王", "大王", "3"], ["9", "9", "9", "9"]])
def test_bot_should_double_with_strong_hand(hand: list[str]) -> None:
    assert ddz.ddz_bot_should_double({"hand": hand})


def test_bot_should_not_double_with_weak_hand() -> None:
    assert not ddz.ddz_bot_should_double({"hand": ["3", "4", "5", "6", "7"]})


def test_pressure_chance_is_bounded_and_monotonic() -> None:
    strong = ddz.ddz_pressure_chance(10000, 1000)
    even = ddz.ddz_pressure_chance(1000, 1000)
    weak = ddz.ddz_pressure_chance(100, 10000)
    assert strong >= even >= weak
    for chance in (strong, even, weak):
        assert 0.10 <= chance <= 0.85
    assert ddz.ddz_pressure_chance(1000, 1000, pressure=True) > even
