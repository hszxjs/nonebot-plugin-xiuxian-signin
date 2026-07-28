"""秘境节点事件系统：按主题/难度/点位加载事件文案与绑定奖励。

原先踩到资源/陷阱/休整/随机节点只有三句万能模板话，没有任何描述。这里引入
按 (theme_id, map_size 难度档, node_kind) 组织的事件库，每条事件带专属文案和
具体奖励，让秘境探索有叙事感、奖励有来源。

事件库以 JSON 文件存放于 assets/mystic_events/<theme_id>.json，未覆盖的主题/
难度/点位自动兜底（返回 None，调用方走原逻辑），保证渐进式补全不破坏现有体验。
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_EVENTS_DIR = (
    Path(__file__).resolve().parent / "assets" / "mystic_events"
)

# 难度档：按 map_size（格子数）划分，与 map_size_for_boss 的境界分层对齐。
# 24/28 → 低修为，32/36 → 中修为，40/44/48 → 高修为。
_TIER_LOW_SIZES = {24, 28}
_TIER_MID_SIZES = {32, 36}
_TIER_HIGH_SIZES = {40, 44, 48}


def map_size_tier(map_size: int) -> str:
    """把格子数转成难度档 key：low / mid / high。未知尺寸归到 mid。"""
    size = int(map_size)
    if size in _TIER_LOW_SIZES:
        return "low"
    if size in _TIER_HIGH_SIZES:
        return "high"
    return "mid"


# 主题事件库缓存：theme_id → 解析后的 dict（或 None 表示无库）
_event_cache: dict[str, Optional[dict[str, Any]]] = {}


def load_theme_events(theme_id: str) -> Optional[dict[str, Any]]:
    """加载某主题的事件库（带缓存）。文件不存在返回 None。"""
    if theme_id in _event_cache:
        return _event_cache[theme_id]
    path = _EVENTS_DIR / f"{theme_id}.json"
    if not path.is_file():
        _event_cache[theme_id] = None
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _event_cache[theme_id] = None
        return None
    _event_cache[theme_id] = data
    return data


def clear_cache() -> None:
    """清空事件库缓存（测试 / 热更新时用）。"""
    _event_cache.clear()


@dataclass(frozen=True)
class EventPick:
    """命中事件库后返回的一条事件：文案 + 绑定奖励描述。"""

    text: str
    reward: Optional[dict[str, Any]] = None


def pick_node_event(
    run: Any,
    node_id: str,
    node_kind_value: str,
) -> Optional[EventPick]:
    """为指定节点确定性选取一条事件。

    用 content_seed:theme_id:node_id 做 hash 选取，保证同一节点对同一玩家稳定
    （重试不会刷出不同文案），与 _personal_node_reward 的确定性哲学一致。

    Args:
        run: MysticDungeonRun，需有 content_seed / theme_id / map_size 字段
        node_id: 节点 id
        node_kind_value: NodeKind 的 value（resource/trap/rest/random）

    Returns:
        命中返回 EventPick；该主题无库 / 该难度或点位无事件时返回 None（调用方兜底）
    """
    theme_id = getattr(run, "theme_id", "") or ""
    library = load_theme_events(theme_id)
    if not library:
        return None
    events = library.get("events") or {}
    tier = map_size_tier(getattr(run, "map_size", 32))
    tier_events = events.get(tier) or {}
    options = tier_events.get(node_kind_value) or []
    if not options:
        return None
    content_seed = getattr(run, "content_seed", "")
    digest = hashlib.sha256(
        f"{content_seed}:{theme_id}:{node_id}".encode("utf-8")
    ).hexdigest()
    index = int(digest[:8], 16) % len(options)
    entry = options[index]
    if not isinstance(entry, dict):
        return None
    text = str(entry.get("text") or "").strip()
    if not text:
        return None
    reward = entry.get("reward")
    if reward is not None and not isinstance(reward, dict):
        reward = None
    return EventPick(text=text, reward=reward)


def event_reward_to_payload(
    reward: dict[str, Any],
    *,
    reward_multiplier: float = 1.0,
    rng: Optional[random.Random] = None,
) -> dict[str, Any]:
    """把事件的 reward 描述转成实际奖励 payload（与 _personal_node_reward 同构）。

    支持的 reward 形态：
    - {"category": "灵石"|"修为"|"垂钓次数", "amount": [min, max]}
    - {"category": "灵材", "name": ..., "tier": ..., "grade": ..., "description": ...}

    amount 区间在 [min, max] 内随机（受 reward_multiplier 加成），物品类直接透传。
    """
    rng = rng or random.Random()
    category = str(reward.get("category") or "")
    if category in {"灵石", "修为", "垂钓次数"}:
        amount_spec = reward.get("amount")
        if isinstance(amount_spec, list) and len(amount_spec) >= 2:
            low = max(1, int(amount_spec[0]))
            high = max(low, int(amount_spec[1]))
            base = rng.randint(low, high)
        elif isinstance(amount_spec, (int, float)):
            base = max(1, int(amount_spec))
        else:
            base = 1
        amount = max(1, int(base * reward_multiplier))
        return {"category": category, "name": category, "amount": amount}
    # 物品类（灵材/丹药/灵器等）：透传字段，补默认值
    payload: dict[str, Any] = {
        "category": category or "杂物",
        "name": str(reward.get("name") or "秘境所得"),
    }
    for key in ("tier", "grade", "description", "price"):
        if key in reward:
            payload[key] = reward[key]
    return payload
