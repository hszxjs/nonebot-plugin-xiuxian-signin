from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "admin_dashboard.py"
SPEC = importlib.util.spec_from_file_location("admin_dashboard", MODULE_PATH)
admin_dashboard = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(admin_dashboard)

DOMAIN_PATH = Path(__file__).resolve().parents[1] / "domain.py"
DOMAIN_SPEC = importlib.util.spec_from_file_location("domain", DOMAIN_PATH)
domain = importlib.util.module_from_spec(DOMAIN_SPEC)
sys.modules["domain"] = domain
assert DOMAIN_SPEC and DOMAIN_SPEC.loader
DOMAIN_SPEC.loader.exec_module(domain)


class AdminDashboardTests(unittest.TestCase):
    def test_dashboard_empty_users(self) -> None:
        payload = admin_dashboard.build_dashboard_payload({}, date(2026, 7, 8), {})

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "snapshot")
        self.assertEqual(payload["metrics"]["total_players"], 0)
        self.assertEqual(payload["metrics"]["signed_today"], 0)
        self.assertEqual(payload["realm_distribution"], [])
        self.assertFalse(payload["health_flags"]["has_players"])

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

        self.assertEqual(payload["metrics"]["total_players"], 3)
        self.assertEqual(payload["metrics"]["signed_today"], 1)
        self.assertEqual(payload["metrics"]["recent_active"], 1)
        self.assertEqual(payload["metrics"]["inactive_risk"], 2)
        self.assertEqual(payload["metrics"]["total_spirit_stones"], 1000)
        self.assertEqual(payload["top_battle_power"][0]["user_id"], "1002")
        self.assertEqual(payload["recent_signins"][0]["nickname"], "云舟")
        self.assertEqual(payload["inactive_players"][0]["user_id"], "1003")
        self.assertFalse(payload["capabilities"]["historical_trends"])

    def test_dashboard_malformed_numeric_and_date_values(self) -> None:
        users = {
            "bad": {
                "nickname": "破损记录",
                "realm_index": float("inf"),
                "battle_power": float("nan"),
                "spirit_stones": "inf",
                "last_sign_date": "not-a-date",
            },
            "overflow": {
                "battle_power": "1e309",
                "spirit_stones": "-inf",
                "last_sign_date": "2026/07/08",
            },
        }

        payload = admin_dashboard.build_dashboard_payload(users, date(2026, 7, 8), {})

        self.assertEqual(payload["metrics"]["total_players"], 2)
        self.assertEqual(payload["metrics"]["total_spirit_stones"], 0)
        self.assertEqual(payload["metrics"]["average_battle_power"], 0)
        self.assertEqual(payload["top_battle_power"][0]["battle_power"], 0)
        self.assertEqual(payload["top_battle_power"][1]["battle_power"], 0)
        self.assertEqual(payload["recent_signins"][0]["user_id"], "overflow")
        self.assertEqual(payload["inactive_players"][0]["user_id"], "bad")
        self.assertEqual(payload["inactive_players"][0]["last_sign_date"], "")

    def test_dashboard_resolves_real_user_record_battle_power(self) -> None:
        record = domain.UserRecord(
            user_id="real",
            realm_index=3,
            realm_exp=120,
            total_exp=450,
            sign_count=8,
            spirit_stones=88,
            last_sign_date="2026-07-08",
        )
        raw = record.to_dict()
        self.assertNotIn("battle_power", raw)

        def battle_power_resolver(user_id: str, data: dict[str, object]) -> int:
            payload = dict(data)
            payload["user_id"] = user_id
            return domain.battle_power(domain.UserRecord.from_dict(payload))

        payload = admin_dashboard.build_dashboard_payload(
            {"real": raw},
            date(2026, 7, 8),
            {3: "筑基"},
            battle_power_resolver,
        )

        expected_power = domain.battle_power(record)
        self.assertGreater(expected_power, 0)
        self.assertEqual(payload["metrics"]["average_battle_power"], expected_power)
        self.assertEqual(payload["top_battle_power"][0]["battle_power"], expected_power)
