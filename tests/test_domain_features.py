from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path


DOMAIN_PATH = Path(__file__).resolve().parents[1] / "domain.py"
DOMAIN_SPEC = importlib.util.spec_from_file_location("domain", DOMAIN_PATH)
assert DOMAIN_SPEC is not None and DOMAIN_SPEC.loader is not None
domain = importlib.util.module_from_spec(DOMAIN_SPEC)
sys.modules["domain"] = domain
DOMAIN_SPEC.loader.exec_module(domain)


def root() -> object:
    return domain.Root("天阶", 4, "极品", 3, "金", 100, ["金"])


def artifact(name: str, realm_index: int, *, uid: str = "") -> dict[str, object]:
    item: dict[str, object] = {
        "tier": "玄阶",
        "grade": "中品",
        "category": domain.ARTIFACT_CATEGORY,
        "name": name,
        "realm_index": realm_index,
    }
    if uid:
        item["instance_uid"] = uid
    return item


class DomainFeatureTests(unittest.TestCase):
    def tearDown(self) -> None:
        domain.apply_admin_config({})

    def test_user_record_ignores_legacy_mystic_runtime_fields(self) -> None:
        legacy_keys = {
            "mystic_realm",
            "last_failed_mystic_realm",
            "mystic_boss_successes",
            "mystic_boss_daily_date",
            "mystic_boss_daily_attempts",
            "mystic_boss_daily_bonus",
            "mystic_boss_week_key",
            "mystic_boss_week_attempts",
            "mystic_boss_week_claimed",
        }
        payload = domain.UserRecord(user_id="42", root=root()).to_dict()
        payload.update(
            {
                "mystic_realm": {"steps_left": 8},
                "last_failed_mystic_realm": {"type": "上古宗门遗址"},
                "mystic_boss_successes": {"2026-07-16": ["legacy"]},
                "mystic_boss_daily_date": "2026-07-16",
                "mystic_boss_daily_attempts": 2,
                "mystic_boss_daily_bonus": 1,
                "mystic_boss_week_key": "2026-W29",
                "mystic_boss_week_attempts": 3,
                "mystic_boss_week_claimed": [3],
            }
        )

        record = domain.UserRecord.from_dict(payload)

        self.assertTrue(all(not hasattr(record, key) for key in legacy_keys))
        self.assertTrue(legacy_keys.isdisjoint(record.to_dict()))

    def test_signin_reports_and_applies_extra_fishing_chance(self) -> None:
        domain.apply_admin_config({"signin": {"extra_fishing_chance_rate": 1.0}})
        record = domain.UserRecord(user_id="42", root=root())

        result = domain.apply_signin(record, date(2026, 7, 9))

        self.assertEqual(record.fishing_chances, 2)
        self.assertEqual(record.pending_fishing, 2)
        self.assertEqual(result.fishing_chances_gained, 2)

    def test_signin_can_grant_configured_mystic_tokens(self) -> None:
        domain.apply_admin_config(
            {
                "mystic": {
                    "signin_normal_token_count": 1,
                    "signin_high_risk_token_count": 1,
                }
            }
        )
        record = domain.UserRecord(user_id="42", root=root())

        domain.apply_signin(record, date(2026, 7, 16))

        self.assertEqual(domain.reward_count_by_names(record, ["普通秘境令牌"]), 1)
        self.assertEqual(domain.reward_count_by_names(record, ["高风险秘境令牌"]), 1)

    def test_mystic_token_grant_counts_are_clamped_to_zero_through_ten(self) -> None:
        domain.apply_admin_config(
            {
                "mystic": {
                    "signin_normal_token_count": 99,
                    "signin_high_risk_token_count": -4,
                }
            }
        )
        record = domain.UserRecord(user_id="42", root=root())

        domain.apply_signin(record, date(2026, 7, 16))

        self.assertEqual(domain.reward_count_by_names(record, ["普通秘境令牌"]), 10)
        self.assertEqual(domain.reward_count_by_names(record, ["高风险秘境令牌"]), 0)

    def test_daily_task_can_grant_configured_mystic_tokens(self) -> None:
        domain.apply_admin_config(
            {
                "mystic": {
                    "daily_task_normal_token_count": 1,
                    "daily_task_high_risk_token_count": 1,
                }
            }
        )
        record = domain.UserRecord(user_id="42", root=root())
        domain.generate_daily_tasks(record, date(2026, 7, 16))

        success, _ = domain.complete_daily_task(record, 1, date(2026, 7, 16))

        self.assertTrue(success)
        self.assertEqual(domain.reward_count_by_names(record, ["普通秘境令牌"]), 1)
        self.assertEqual(domain.reward_count_by_names(record, ["高风险秘境令牌"]), 1)

    def test_mystic_tokens_are_admin_items_but_not_fishing_drops(self) -> None:
        token_names = set(domain.MYSTIC_TOKEN_DEFINITIONS)
        fishing_names = {str(item[3]) for item in domain.FISHING_REWARDS}
        catalog_names = {str(item["name"]) for item in domain.admin_item_catalog()}

        self.assertTrue(token_names <= catalog_names)
        self.assertTrue(token_names.isdisjoint(fishing_names))

    def test_batch_sell_low_realm_artifacts_keeps_equipped_unique_and_current_realm_items(self) -> None:
        equipped = artifact("旧剑", 1, uid="equipped")
        record = domain.UserRecord(
            user_id="42",
            root=root(),
            realm_index=3,
            spirit_stones=10,
            equipped_artifacts={"主手": equipped},
            rewards=[
                artifact("旧剑", 1, uid="equipped"),
                artifact("旧甲", 1, uid="sold"),
                artifact("同境法器", 3, uid="same"),
                artifact(domain.EMPEROR_ARTIFACT_NAMES[0], 1, uid="unique"),
                {"tier": "凡品", "grade": "下品", "category": "灵材", "name": "玄铁"},
            ],
        )

        success, message = domain.batch_sell_low_realm_artifacts(record)

        self.assertTrue(success)
        self.assertIn("批量出售低阶灵器 1 件", message)
        self.assertEqual(record.spirit_stones, 10 + domain.recycle_price(artifact("旧甲", 1, uid="sold")))
        self.assertEqual(
            [item.get("instance_uid") for item in record.rewards if item.get("category") == domain.ARTIFACT_CATEGORY],
            ["equipped", "same", "unique"],
        )

    def test_normalize_reward_recovers_empty_name_from_description(self) -> None:
        reward = domain.normalize_reward(
            {
                "tier": "凡品",
                "grade": "下品",
                "category": domain.ARTIFACT_CATEGORY,
                "name": "",
                "description": "锻骨素纹沧澜初成珠出自月照泉。相传炼体守炉弟子拾得水系灵胚。",
                "realm_index": 0,
            }
        )

        self.assertEqual(reward["name"], "锻骨素纹沧澜初成珠")
        self.assertNotIn("无名", reward["name"])

    def test_sanitize_user_record_data_only_repairs_empty_names(self) -> None:
        data = domain.UserRecord(user_id="42", root=root()).to_dict()
        data["equipped_artifact"] = {
            "tier": "凡品",
            "grade": "下品",
            "category": domain.ARTIFACT_CATEGORY,
            "name": "",
            "description": "锻骨素纹沧澜初成珠出自月照泉。相传炼体守炉弟子拾得水系灵胚。",
            "compatible": True,
        }
        data["rewards"] = [
            {
                "tier": "天阶",
                "grade": "极品",
                "category": domain.ARTIFACT_CATEGORY,
                "name": "太虚斩星剑",
                "description": "太虚斩星剑灵光内敛，装备后可计入战力。",
            }
        ]

        cleaned = domain.sanitize_user_record_data(data)

        self.assertEqual(cleaned["equipped_artifact"]["name"], "锻骨素纹沧澜初成珠")
        self.assertIs(cleaned["equipped_artifact"]["compatible"], True)
        self.assertEqual(cleaned["rewards"][0]["name"], "太虚斩星剑")

    def test_true_immortal_quality_inherits_fake_immortal_mark(self) -> None:
        fake_index = domain.fake_immortal_realm_index()
        true_index = domain.true_immortal_realm_index()
        record = domain.UserRecord(
            user_id="42",
            root=root(),
            realm_index=fake_index,
            immortal_conversion_days=6,
            realm_marks={str(fake_index): "玄妙真仙"},
        )

        converted, message = domain.progress_fake_immortal_conversion(record, date(2026, 7, 9))

        self.assertTrue(converted)
        self.assertEqual(record.realm_index, true_index)
        self.assertEqual(record.realm_marks[str(fake_index)], "玄妙真仙")
        self.assertEqual(record.realm_marks[str(true_index)], "玄妙真仙")
        self.assertEqual(domain.realm_quality_text(record), "玄妙真仙")
        self.assertIn("继承假仙境", message)


if __name__ == "__main__":
    unittest.main()
