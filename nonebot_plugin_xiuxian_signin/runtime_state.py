"""内存对局状态的跨重启降级（R-21）。

斗地主 / 对决 / 御兽秘境的对局态全部只存在于 ``state.py`` 的内存字典里。进程重启
（包括 ``systemctl restart`` 这种最平常的重新部署）之后这些字典清空，玩家那边
却是「牌局突然没了、指令又提示暂无牌桌」——没有任何解释。

本模块不试图把对局态写盘（牌局对象里混着 ``time.monotonic()`` 计时、渲染句柄、
私聊通道，序列化等于把半个游戏状态机搬进存储层，性价比极低）。做的是两件小事：

1. **停机时记一笔**：把「此刻还有对局的群」写进 ``interrupted_games.json``；
2. **重启后说一句**：该群下次发本游戏入口命令时，先补一条「上局因重启中断」，
   然后照常开新局。

写入只在停机时发生（一次、几十字节），不参与热路径；读取只在启动时发生一次。
文件在启动读取后被删除，notice 转存内存——因此「重启后没人来玩」不会留下
永远发不出去的脏数据；再次重启时会把尚未消费的 notice 合并回去。
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from .storage import atomic_write_json

STATE_FILE_NAME = "interrupted_games.json"

# 游戏标识 → 玩家看到的说法。新玩法接入时在这里加一行。
GAME_LABELS: dict[str, str] = {
    "duel": "对决",
    "doudizhu": "斗地主",
    "beast": "御兽秘境",
}

# 本进程内尚未送达的 notice：game -> {group_key}。
_pending: dict[str, set[str]] = {}


def state_path(data_dir: str | Path) -> Path:
    return Path(data_dir) / STATE_FILE_NAME


def _clean(payload: Any) -> dict[str, list[str]]:
    """把任意读到的 JSON 收敛成 ``{game: [group_key, ...]}``，未知游戏整条丢弃。"""
    result: dict[str, list[str]] = {}
    if not isinstance(payload, dict):
        return result
    games = payload.get("games", payload)
    if not isinstance(games, dict):
        return result
    for game, keys in games.items():
        if game not in GAME_LABELS or not isinstance(keys, list):
            continue
        cleaned = sorted({str(key).strip() for key in keys if str(key).strip()})
        if cleaned:
            result[game] = cleaned
    return result


def load_interrupted(data_dir: str | Path) -> dict[str, list[str]]:
    """启动时调用：读出上次停机留下的记录，转存内存并删除文件。

    文件损坏/不可读一律当作「没有中断」——这条提示是锦上添花，绝不能因为
    它让插件起不来。
    """
    path = state_path(data_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    recovered = _clean(payload)
    for game, keys in recovered.items():
        _pending.setdefault(game, set()).update(keys)
    return recovered


def record_shutdown_snapshot(
    data_dir: str | Path,
    active: dict[str, Iterable[str]],
) -> dict[str, list[str]]:
    """停机时调用：把仍在进行的对局连同「尚未送达的 notice」一起落盘。

    没有任何对局时删除文件，避免下一次启动凭空冒出一条中断提示。
    """
    merged: dict[str, list[str]] = {}
    for game in GAME_LABELS:
        keys = {str(key).strip() for key in active.get(game, ()) if str(key).strip()}
        keys |= _pending.get(game, set())
        if keys:
            merged[game] = sorted(keys)
    if not merged:
        try:
            state_path(data_dir).unlink(missing_ok=True)
        except OSError:
            pass
        return {}
    atomic_write_json(
        state_path(data_dir),
        {"recorded_at": datetime.now().isoformat(timespec="seconds"), "games": merged},
        snapshot_reason=None,
    )
    return merged


def pending_games() -> dict[str, list[str]]:
    """当前内存里的待送达 notice（供启动日志/审计使用）。"""
    return {game: sorted(keys) for game, keys in _pending.items() if keys}


def consume(game: str, group_key: str) -> bool:
    """取走某群某玩法的 notice：返回 True 表示「上局确实被重启打断了」。"""
    keys = _pending.get(game)
    if not keys or group_key not in keys:
        return False
    keys.discard(group_key)
    if not keys:
        _pending.pop(game, None)
    return True


def interruption_notice(game: str, group_key: str) -> str | None:
    """消费并返回给玩家看的一句话；没有待送达通知时返回 None。"""
    if not consume(game, group_key):
        return None
    label = GAME_LABELS.get(game, "对局")
    return f"上次重启打断了这里的{label}，残局已无法恢复，本群已经重置。重新开始即可。"


def reset_pending() -> None:
    """测试与热重载用：清空内存中的待送达 notice。"""
    _pending.clear()
