from __future__ import annotations

import math
from collections import Counter
from datetime import date, datetime
from typing import Any, Callable


RECENT_ACTIVE_DAYS = 7
INACTIVE_RISK_DAYS = 14


def parse_record_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def number_value(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(result):
        return default
    return result


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(number_value(value, float(default)))
    except (OverflowError, ValueError, TypeError):
        return default


def player_display_name(record: dict[str, Any], fallback_user_id: str) -> str:
    for key in ("nickname", "name", "user_name"):
        value = str(record.get(key) or "").strip()
        if value:
            return value
    return fallback_user_id


def realm_name(record: dict[str, Any], realm_names: dict[int, str]) -> str:
    index = int_value(record.get("realm_index"), -1)
    if index in realm_names:
        return realm_names[index]
    value = str(record.get("realm") or "").strip()
    return value or "未知境界"


BattlePowerResolver = Callable[[str, dict[str, Any]], Any]


def resolve_battle_power(
    user_id: str,
    record: dict[str, Any],
    battle_power_resolver: BattlePowerResolver | None,
) -> Any:
    if battle_power_resolver is None:
        return record.get("battle_power")
    try:
        return battle_power_resolver(user_id, record)
    except Exception:
        return record.get("battle_power")


def summarize_player(
    user_id: str,
    record: dict[str, Any],
    today: date,
    realm_names: dict[int, str],
    battle_power_resolver: BattlePowerResolver | None = None,
) -> dict[str, Any]:
    last_sign = parse_record_date(record.get("last_sign_date"))
    days_since_sign = (today - last_sign).days if last_sign else None
    return {
        "user_id": user_id,
        "nickname": player_display_name(record, user_id),
        "realm": realm_name(record, realm_names),
        "realm_index": int_value(record.get("realm_index"), -1),
        "battle_power": int_value(resolve_battle_power(user_id, record, battle_power_resolver)),
        "spirit_stones": int_value(record.get("spirit_stones")),
        "last_sign_date": last_sign.isoformat() if last_sign else "",
        "days_since_sign": days_since_sign,
        "signed_today": last_sign == today,
        "recent_active": days_since_sign is not None and 0 <= days_since_sign <= RECENT_ACTIVE_DAYS,
        "inactive_risk": days_since_sign is None or days_since_sign >= INACTIVE_RISK_DAYS,
    }


def build_dashboard_payload(
    users: dict[str, Any],
    today: date,
    realm_names: dict[int, str] | None = None,
    battle_power_resolver: BattlePowerResolver | None = None,
) -> dict[str, Any]:
    realm_names = realm_names or {}
    summaries: list[dict[str, Any]] = []
    for user_id, raw in users.items():
        if isinstance(raw, dict):
            summaries.append(summarize_player(str(user_id), raw, today, realm_names, battle_power_resolver))

    total_players = len(summaries)
    signed_today = sum(1 for item in summaries if item["signed_today"])
    recent_active = sum(1 for item in summaries if item["recent_active"])
    inactive_risk = sum(1 for item in summaries if item["inactive_risk"])
    total_stones = sum(int(item["spirit_stones"]) for item in summaries)
    total_power = sum(int(item["battle_power"]) for item in summaries)
    realm_counter = Counter(str(item["realm"]) for item in summaries)

    top_power = sorted(summaries, key=lambda item: int(item["battle_power"]), reverse=True)[:10]
    recent_signins = sorted(
        [item for item in summaries if item["last_sign_date"]],
        key=lambda item: item["last_sign_date"],
        reverse=True,
    )[:12]
    inactive_players = sorted(
        [item for item in summaries if item["inactive_risk"]],
        key=lambda item: item["days_since_sign"] if item["days_since_sign"] is not None else 9999,
        reverse=True,
    )[:12]

    return {
        "ok": True,
        "mode": "snapshot",
        "generated_date": today.isoformat(),
        "metrics": {
            "total_players": total_players,
            "signed_today": signed_today,
            "recent_active": recent_active,
            "inactive_risk": inactive_risk,
            "total_spirit_stones": total_stones,
            "average_spirit_stones": round(total_stones / total_players, 2) if total_players else 0,
            "average_battle_power": round(total_power / total_players, 2) if total_players else 0,
        },
        "realm_distribution": [
            {"realm": realm, "count": count}
            for realm, count in realm_counter.most_common()
        ],
        "top_battle_power": top_power,
        "recent_signins": recent_signins,
        "inactive_players": inactive_players,
        "health_flags": {
            "has_players": total_players > 0,
            "inactive_ratio": round(inactive_risk / total_players, 4) if total_players else 0,
            "today_signin_ratio": round(signed_today / total_players, 4) if total_players else 0,
        },
        "capabilities": {
            "historical_trends": False,
            "snapshot_dashboard": True,
        },
    }
