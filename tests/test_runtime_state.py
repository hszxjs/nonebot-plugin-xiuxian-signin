"""内存对局态跨重启降级（R-21）。

内存里的对局（对决/斗地主/御兽）在进程重启后不可恢复。这里钉住「不假装能恢复、
但要解释清楚」的契约：停机记一笔 → 启动读回 → 玩家下次进场时补一句 → 只补一次。
"""
from __future__ import annotations

import json

import pytest

from nonebot_plugin_xiuxian_signin import runtime_state


@pytest.fixture(autouse=True)
def _clean_pending():
    runtime_state.reset_pending()
    yield
    runtime_state.reset_pending()


def test_snapshot_records_only_active_groups(tmp_path) -> None:
    recorded = runtime_state.record_shutdown_snapshot(
        tmp_path,
        {"doudizhu": ["group:1", "group:2"], "duel": [], "beast": ()},
    )
    assert recorded == {"doudizhu": ["group:1", "group:2"]}
    payload = json.loads(runtime_state.state_path(tmp_path).read_text(encoding="utf-8"))
    assert payload["games"] == {"doudizhu": ["group:1", "group:2"]}
    assert payload["recorded_at"]


def test_snapshot_removes_file_when_nothing_active(tmp_path) -> None:
    path = runtime_state.state_path(tmp_path)
    runtime_state.record_shutdown_snapshot(tmp_path, {"doudizhu": ["group:1"]})
    assert path.exists()

    runtime_state.record_shutdown_snapshot(tmp_path, {"doudizhu": [], "duel": [], "beast": []})
    assert not path.exists(), "没有进行中的对局时不该留下提示文件"


def test_load_consumes_file_and_arms_pending(tmp_path) -> None:
    runtime_state.record_shutdown_snapshot(tmp_path, {"duel": ["group:9"]})
    recovered = runtime_state.load_interrupted(tmp_path)

    assert recovered == {"duel": ["group:9"]}
    assert not runtime_state.state_path(tmp_path).exists(), "读取后应删除文件"
    assert runtime_state.pending_games() == {"duel": ["group:9"]}


def test_notice_is_delivered_once(tmp_path) -> None:
    runtime_state.record_shutdown_snapshot(tmp_path, {"beast": ["group:7"]})
    runtime_state.load_interrupted(tmp_path)

    notice = runtime_state.interruption_notice("beast", "group:7")
    assert notice and "御兽秘境" in notice
    assert runtime_state.interruption_notice("beast", "group:7") is None
    assert runtime_state.pending_games() == {}


def test_notice_ignores_other_group_and_other_game(tmp_path) -> None:
    runtime_state.record_shutdown_snapshot(tmp_path, {"beast": ["group:7"]})
    runtime_state.load_interrupted(tmp_path)

    assert runtime_state.interruption_notice("beast", "group:8") is None
    assert runtime_state.interruption_notice("doudizhu", "group:7") is None
    assert runtime_state.pending_games() == {"beast": ["group:7"]}


def test_second_shutdown_keeps_undelivered_notices(tmp_path) -> None:
    runtime_state.record_shutdown_snapshot(tmp_path, {"doudizhu": ["group:1"]})
    runtime_state.load_interrupted(tmp_path)
    # 还没人来看过就再次重启：旧提示必须保住，同时记上新局
    merged = runtime_state.record_shutdown_snapshot(tmp_path, {"beast": ["group:2"]})
    assert merged == {"doudizhu": ["group:1"], "beast": ["group:2"]}


def test_corrupt_file_is_ignored(tmp_path) -> None:
    path = runtime_state.state_path(tmp_path)
    path.write_text("{not json", encoding="utf-8")

    assert runtime_state.load_interrupted(tmp_path) == {}
    assert not path.exists()
    assert runtime_state.pending_games() == {}


def test_unknown_game_and_empty_keys_are_dropped(tmp_path) -> None:
    path = runtime_state.state_path(tmp_path)
    path.write_text(
        json.dumps({"games": {"doudizhu": ["", "group:1"], "mystery": ["group:2"], "duel": "oops"}}),
        encoding="utf-8",
    )

    assert runtime_state.load_interrupted(tmp_path) == {"doudizhu": ["group:1"]}

    runtime_state.reset_pending()
    runtime_state.record_shutdown_snapshot(tmp_path, {"doudizhu": ["", " "]})
    assert not path.exists()
