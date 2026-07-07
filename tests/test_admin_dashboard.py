from __future__ import annotations

import importlib.util
import unittest
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "admin_dashboard.py"
SPEC = importlib.util.spec_from_file_location("admin_dashboard", MODULE_PATH)
admin_dashboard = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(admin_dashboard)


class AdminDashboardTests(unittest.TestCase):
    def test_dashboard_empty_users(self) -> None:
        payload = admin_dashboard.build_dashboard_payload({}, date(2026, 7, 8), {})

        assert payload["ok"] is True
        assert payload["mode"] == "snapshot"
        assert payload["metrics"]["total_players"] == 0
        assert payload["metrics"]["signed_today"] == 0
        assert payload["realm_distribution"] == []
        assert payload["health_flags"]["has_players"] is False

    def test_dashboard_mixed_activity(self) -> None:
        users = {
            "1001": {
                "nickname": "云舟",
                "realm_index": 3,
                "battle_power": 1200,
                "spirit_stones": 300,
                "last_sign_date": "2026-07-08",
            },
            "1002": {
                "nickname": "眠山",
                "realm_index": 5,
                "battle_power": "2400",
                "spirit_stones": "700",
                "last_sign_date": "2026-06-20",
            },
            "1003": {
                "realm": "散修",
                "battle_power": 100,
                "spirit_stones": 0,
                "last_sign_date": "",
            },
        }

        payload = admin_dashboard.build_dashboard_payload(
            users,
            date(2026, 7, 8),
            {3: "筑基", 5: "金丹"},
        )

        assert payload["metrics"]["total_players"] == 3
        assert payload["metrics"]["signed_today"] == 1
        assert payload["metrics"]["recent_active"] == 1
        assert payload["metrics"]["inactive_risk"] == 2
        assert payload["metrics"]["total_spirit_stones"] == 1000
        assert payload["top_battle_power"][0]["user_id"] == "1002"
        assert payload["recent_signins"][0]["nickname"] == "云舟"
        assert payload["inactive_players"][0]["user_id"] == "1003"
        assert payload["capabilities"]["historical_trends"] is False
