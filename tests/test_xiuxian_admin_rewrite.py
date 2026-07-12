from __future__ import annotations

import json
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "_xiuxian_admin_rewrite_package"

package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
sys.modules.setdefault(PACKAGE_NAME, package)

spec = importlib.util.spec_from_file_location(
    f"{PACKAGE_NAME}.admin",
    PACKAGE_ROOT / "admin.py",
)
assert spec is not None
assert spec.loader is not None
admin = importlib.util.module_from_spec(spec)
sys.modules[f"{PACKAGE_NAME}.admin"] = admin
spec.loader.exec_module(admin)


ADMIN_PY = Path(admin.__file__)


class FakeManager:
    def __init__(self, data_dir: Path, token: str = "") -> None:
        self.data_dir = data_dir
        self.token = token
        self.config: dict[str, Any] = {"version": 1, "signin": {"extra_fishing_chance_rate": 0.1}}
        self.players: dict[str, dict[str, Any]] = {
            "10001": {
                "user_id": "10001",
                "nickname": "青衡",
                "realm": "筑基境",
                "realm_index": 2,
                "spirit_stones": 1200,
            }
        }

    def dashboard_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "mode": "snapshot",
            "generated_date": "2026-07-12",
            "metrics": {"total_players": 1, "signed_today": 1},
            "realm_distribution": [{"realm": "筑基境", "count": 1}],
            "top_battle_power": [{"user_id": "10001", "nickname": "青衡", "battle_power": 3200}],
            "recent_signins": [{"user_id": "10001", "nickname": "青衡"}],
            "inactive_players": [],
            "health_flags": {"has_players": True},
            "capabilities": {"snapshot_dashboard": True},
        }

    def load_config(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.config, ensure_ascii=False))

    def save_config(self, data: dict[str, Any]) -> None:
        self.config = json.loads(json.dumps(data, ensure_ascii=False))

    def apply_config(self) -> None:
        return None

    def list_players(self, query: str = "") -> list[dict[str, Any]]:
        return [
            {
                "user_id": "10001",
                "nickname": "青衡",
                "realm": "筑基境",
                "spirit_stones": 1200,
                "battle_power": 3200,
            }
        ]

    def get_player_record(self, user_id: str) -> dict[str, Any] | None:
        return self.players.get(user_id)

    def save_player_record(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self.players[user_id] = dict(data, user_id=user_id)
        return self.players[user_id]

    def player_meta(self) -> dict[str, Any]:
        return {
            "realms": [{"index": 2, "name": "筑基境"}],
            "attributes": ["metal", "wood"],
            "tiers": ["凡品", "黄阶"],
            "grades": ["下品", "中品"],
        }

    def backup_users(self) -> dict[str, Any]:
        return {"ok": True, "path": str(self.data_dir / "backups" / "users.json")}

    def item_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "items": [{"name": "聚气丹", "category": "丹药", "tiers": ["凡品"], "customized": False}],
            "meta": {"categories": ["丹药"], "tiers": ["凡品"], "grades": ["下品"]},
        }

    def beast_card_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "cards": [{"id": "fox_001", "name": "灵狐", "customized": False}],
            "meta": {"default_pool_copies": 10},
        }

    def mystic_payload(self) -> dict[str, Any]:
        return {
            "types": ["普通秘境"],
            "enabled_types": ["普通秘境"],
            "category_weights": {"丹药": 1},
            "drop_overrides": {},
            "fishing_option_rate": 0.05,
            "extra_fishing_chance_rate": 0.1,
            "categories": ["丹药"],
            "tiers": ["凡品"],
            "grades": ["下品"],
        }

    def equipment_rules(self) -> dict[str, Any]:
        return {"realm_tier_unlocks": {"0": ["凡品"]}}

    def equipment_meta(self) -> dict[str, Any]:
        return {
            "realms": [{"index": 0, "name": "炼气境"}],
            "tiers": ["凡品"],
            "grades": ["下品"],
            "attributes": ["metal"],
            "attribute_labels": {"metal": "金"},
            "artifacts": [{"name": "青锋剑", "tier": "凡品", "grade": "下品"}],
        }


class XiuxianAdminRewriteTest(unittest.TestCase):
    def test_admin_module_no_embedded_html_or_stdlib_http_server(self) -> None:
        source = ADMIN_PY.read_text(encoding="utf-8")
        self.assertNotIn("ADMIN_HTML", source)
        self.assertNotIn("BaseHTTPRequestHandler", source)
        self.assertNotIn("ThreadingHTTPServer", source)

    def test_create_admin_app_serves_spa_and_existing_api_contract(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            static_root = root / "admin_web"
            static_root.mkdir()
            (static_root / "index.html").write_text(
                "<!doctype html><html><body><div id='root'></div><script src='./assets/app.js'></script></body></html>",
                encoding="utf-8",
            )
            app = admin.create_admin_app(
                manager=FakeManager(root),
                base_path="/xiuxian-admin",
                static_root=static_root,
            )
            client = TestClient(app)

            page = client.get("/xiuxian-admin")
            self.assertEqual(page.status_code, 200)
            self.assertIn("/xiuxian-admin/assets/app.js", page.text)

            dashboard = client.get("/xiuxian-admin/api/dashboard")
            self.assertEqual(dashboard.status_code, 200)
            self.assertTrue(dashboard.json()["ok"])

            players = client.get("/xiuxian-admin/api/players")
            self.assertEqual(players.status_code, 200)
            self.assertEqual(players.json()["players"][0]["user_id"], "10001")

            config = client.put("/xiuxian-admin/api/config", json={"version": 2})
            self.assertEqual(config.status_code, 200)
            self.assertEqual(config.json()["config"]["version"], 2)

    def test_create_admin_app_enforces_token_for_pages_and_api(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            static_root = root / "admin_web"
            static_root.mkdir()
            (static_root / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
            app = admin.create_admin_app(
                manager=FakeManager(root, token="secret"),
                base_path="/xiuxian-admin",
                static_root=static_root,
            )
            client = TestClient(app)

            self.assertEqual(client.get("/xiuxian-admin").status_code, 401)
            self.assertEqual(client.get("/xiuxian-admin/api/dashboard").status_code, 401)
            self.assertEqual(
                client.get("/xiuxian-admin/api/dashboard", headers={"X-Xiuxian-Token": "secret"}).status_code,
                200,
            )


if __name__ == "__main__":
    unittest.main()
