from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import json
import sys
import tempfile
import types
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator


PACKAGE_NAME = "nonebot_plugin_xiuxian_signin"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_admin_module() -> Any:
    if PACKAGE_NAME not in sys.modules:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
        package.__package__ = PACKAGE_NAME
        sys.modules[PACKAGE_NAME] = package
    module_name = f"{PACKAGE_NAME}.admin"
    spec = importlib.util.spec_from_file_location(module_name, PACKAGE_ROOT / "admin.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


admin = _load_admin_module()


class FakeManager:
    def __init__(self, token: str = "secret") -> None:
        self.token = token
        self.apply_config_calls = 0
        self.players: dict[str, dict[str, Any]] = {
            "42": {
                "user_id": "42",
                "realm_index": 0,
                "root": {"attribute": "金", "tier": "凡品", "grade": "中品"},
            }
        }

    def apply_config(self) -> None:
        self.apply_config_calls += 1

    def dashboard_payload(self) -> dict[str, Any]:
        return {"ok": True, "source": "dashboard"}

    def load_config(self) -> dict[str, Any]:
        return {}

    def save_config(self, data: dict[str, Any]) -> None:
        return None

    def list_players(self, query: str = "") -> list[dict[str, Any]]:
        return []

    def get_player_record(self, user_id: str) -> dict[str, Any] | None:
        return self.players.get(str(user_id))

    def save_player_record(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        record = dict(data)
        record["user_id"] = str(user_id)
        self.players[str(user_id)] = record
        return record

    def player_meta(self) -> dict[str, Any]:
        return {
            "realms": [{"index": 0, "name": "炼气境"}, {"index": 1, "name": "筑基境"}],
            "attributes": ["金", "木"],
            "attribute_labels": {"金": "金灵根", "木": "木灵根"},
            "tiers": ["凡品", "黄阶"],
            "grades": ["下品", "中品"],
            "categories": ["灵器"],
            "mystic_types": ["上古宗门遗址"],
            "cultivation_routes": ["剑修", "术修"],
            "foundation_quality_titles": ["普通筑基", "天道筑基"],
            "realm_quality_titles": {"1": ["凡品", "极品"]},
            "quality_titles": ["普通筑基", "凡品", "极品"],
        }

    def backup_users(self) -> dict[str, Any]:
        return {"ok": True, "path": "backup.json"}

    def item_payload(self) -> dict[str, Any]:
        return {"ok": True, "items": [], "meta": {}}

    def beast_card_payload(self) -> dict[str, Any]:
        return {"ok": True, "cards": []}

    def mystic_payload(self) -> dict[str, Any]:
        return {}

    def equipment_rules(self) -> dict[str, Any]:
        return {}

    def equipment_meta(self) -> dict[str, Any]:
        return {}


class HeaderMap(dict[str, str]):
    def get(self, key: str, default: Any = None) -> Any:
        return super().get(key.lower(), default)


class FakeRequest:
    def __init__(
        self,
        *,
        token: str = "",
        query_token: str = "",
        json_data: Any | None = None,
        path_params: dict[str, str] | None = None,
    ) -> None:
        self.headers = HeaderMap({"x-xiuxian-token": token} if token else {})
        self.query_params = {"token": query_token} if query_token else {}
        self._json_data = json_data
        self.path_params = path_params or {}

    async def json(self) -> Any:
        return self._json_data if self._json_data is not None else {}


class FakeJSONResponse:
    def __init__(self, data: Any, status_code: int = 200) -> None:
        self.data = data
        self.status_code = status_code
        self.body = json.dumps(data, ensure_ascii=False).encode("utf-8")


class FakeResponse:
    def __init__(self, content: bytes = b"", media_type: str = "", status_code: int = 200) -> None:
        self.body = content
        self.media_type = media_type
        self.status_code = status_code


class FakeFileResponse(FakeResponse):
    def __init__(self, path: Path) -> None:
        super().__init__(Path(path).read_bytes(), status_code=200)
        self.path = Path(path)


class FakeHTMLResponse(FakeResponse):
    def __init__(self, content: str, status_code: int = 200) -> None:
        super().__init__(content.encode("utf-8"), "text/html", status_code)


@contextlib.contextmanager
def _fake_starlette_modules() -> Iterator[None]:
    module_names = ("starlette", "starlette.requests", "starlette.responses")
    saved = {name: sys.modules.get(name) for name in module_names}
    try:
        starlette = types.ModuleType("starlette")
        requests = types.ModuleType("starlette.requests")
        responses = types.ModuleType("starlette.responses")
        requests.Request = FakeRequest
        responses.JSONResponse = FakeJSONResponse
        responses.Response = FakeResponse
        responses.FileResponse = FakeFileResponse
        responses.HTMLResponse = FakeHTMLResponse
        sys.modules.update(
            {
                "starlette": starlette,
                "starlette.requests": requests,
                "starlette.responses": responses,
            }
        )
        yield
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


class FakeStarletteApp:
    def __init__(self) -> None:
        self.routes: list[dict[str, Any]] = []

    def add_route(self, path: str, endpoint: Any, methods: list[str]) -> None:
        self.routes.append({"path": path, "endpoint": endpoint, "methods": methods})


class FakeDriver:
    def __init__(self) -> None:
        self.server_app = FakeStarletteApp()


def _http_request(port: int, path: str, *, method: str = "GET", token: str = "") -> tuple[int, str, bytes]:
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method)
    if token:
        request.add_header("X-Xiuxian-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, exc.headers.get("Content-Type", ""), exc.read()
        finally:
            exc.close()


def _json_body(body: bytes) -> dict[str, Any]:
    return json.loads(body.decode("utf-8"))


class AdminRouteTests(unittest.TestCase):
    def test_starlette_unknown_api_route_is_json_and_ordered_after_known_routes(self) -> None:
        driver = FakeDriver()
        manager = FakeManager()

        with _fake_starlette_modules():
            installed = admin.install_admin_routes(driver, manager)

            self.assertTrue(installed)
            self.assertEqual(manager.apply_config_calls, 1)

            def route_index(path: str, method: str) -> int:
                for index, route in enumerate(driver.server_app.routes):
                    if route["path"] == path and method in route["methods"]:
                        return index
                self.fail(f"Missing route {method} {path}")

            unknown_path = "/xiuxian-admin/api/{api_path:path}"
            known_api_routes = (
                ("GET", "/xiuxian-admin/api/dashboard"),
                ("GET", "/xiuxian-admin/api/config"),
                ("PUT", "/xiuxian-admin/api/config"),
                ("GET", "/xiuxian-admin/api/players"),
                ("GET", "/xiuxian-admin/api/players/{user_id}"),
                ("PUT", "/xiuxian-admin/api/players/{user_id}"),
                ("POST", "/xiuxian-admin/api/backup"),
                ("GET", "/xiuxian-admin/api/items"),
                ("GET", "/xiuxian-admin/api/beast-realm/cards"),
                ("GET", "/xiuxian-admin/api/mystic"),
                ("GET", "/xiuxian-admin/api/equipment-rules"),
            )
            for method, known_api_path in known_api_routes:
                self.assertLess(route_index(known_api_path, method), route_index(unknown_path, method))

            public_asset_path = "/xiuxian-admin/assets/{asset_path:path}"
            runtime_asset_paths = (
                "/xiuxian-admin/assets/item-icons/{icon_path:path}",
                "/xiuxian-admin/assets/character-portraits/{portrait_name}",
                "/xiuxian-admin/assets/beast-spell-icons/{icon_name}",
            )
            for runtime_asset_path in runtime_asset_paths:
                self.assertLess(route_index(runtime_asset_path, "GET"), route_index(public_asset_path, "GET"))
            self.assertLess(route_index(public_asset_path, "GET"), route_index(unknown_path, "GET"))
            self.assertLess(route_index(unknown_path, "GET"), route_index("/xiuxian-admin/{asset_path:path}", "GET"))

            unknown_route = driver.server_app.routes[route_index(unknown_path, "GET")]
            self.assertEqual(set(unknown_route["methods"]), {"GET", "POST", "PUT"})

            unauthorized = asyncio.run(unknown_route["endpoint"](FakeRequest()))
            self.assertEqual(unauthorized.status_code, 401)
            self.assertEqual(unauthorized.data["error"], "unauthorized")

            authorized = asyncio.run(unknown_route["endpoint"](FakeRequest(token="secret")))
            self.assertEqual(authorized.status_code, 404)
            self.assertEqual(authorized.data["error"], "not found")

            dashboard_route = driver.server_app.routes[route_index("/xiuxian-admin/api/dashboard", "GET")]
            dashboard = asyncio.run(dashboard_route["endpoint"](FakeRequest(token="secret")))
            self.assertEqual(dashboard.status_code, 200)
            self.assertEqual(dashboard.data["source"], "dashboard")

            player_get_route = driver.server_app.routes[route_index("/xiuxian-admin/api/players/{user_id}", "GET")]
            player_get = asyncio.run(
                player_get_route["endpoint"](FakeRequest(token="secret", path_params={"user_id": "42"}))
            )
            self.assertEqual(player_get.status_code, 200)
            self.assertEqual(player_get.data["record"]["user_id"], "42")
            self.assertEqual(player_get.data["meta"]["realms"][0]["name"], "炼气境")
            self.assertIn("金", player_get.data["meta"]["attributes"])
            self.assertIn("普通筑基", player_get.data["meta"]["foundation_quality_titles"])

            player_put_route = driver.server_app.routes[route_index("/xiuxian-admin/api/players/{user_id}", "PUT")]
            player_put = asyncio.run(
                player_put_route["endpoint"](
                    FakeRequest(
                        token="secret",
                        path_params={"user_id": "42"},
                        json_data={"realm_index": 1, "root": {"attribute": "木"}},
                    )
                )
            )
            self.assertEqual(player_put.status_code, 200)
            self.assertEqual(player_put.data["record"]["user_id"], "42")
            self.assertEqual(player_put.data["record"]["realm_index"], 1)
            self.assertIn("cultivation_routes", player_put.data["meta"])

    def test_admin_manager_save_player_record_preserves_structured_editor_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            manager = admin.AdminManager(admin.JsonStore(data_dir), data_dir)
            saved = manager.save_player_record(
                "42",
                {
                    "realm_index": 0,
                    "root": {
                        "tier": "凡品",
                        "tier_rank": 0,
                        "grade": "中品",
                        "grade_rank": 1,
                        "attribute": "金",
                        "extra_label": "保留灵根备注",
                    },
                    "custom_note": "保留顶层备注",
                },
            )

            self.assertEqual(saved["user_id"], "42")
            self.assertEqual(saved["custom_note"], "保留顶层备注")
            self.assertEqual(saved["root"]["extra_label"], "保留灵根备注")
            self.assertNotIn("pending_fishing", saved)
            self.assertEqual(manager.get_player_record("42"), saved)

    def test_admin_manager_save_player_record_repairs_empty_reward_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            manager = admin.AdminManager(admin.JsonStore(data_dir), data_dir)
            saved = manager.save_player_record(
                "42",
                {
                    "realm_index": 0,
                    "rewards": [
                        {
                            "tier": "仙阶",
                            "grade": "极品",
                            "category": "功法",
                            "name": "",
                            "description": "离火炼界篇玄妙难言，参悟后可增添斗法底蕴。",
                        }
                    ],
                },
            )

            self.assertEqual(saved["rewards"][0]["name"], "离火炼界篇")
            self.assertEqual(manager.get_player_record("42"), saved)

    def test_admin_entrypoint_uses_scoped_asset_paths(self) -> None:
        html = admin.scoped_admin_index_html(
            b'<script src="./assets/app.js"></script><link href="./assets/app.css">',
            "/xiuxian-admin",
        )

        self.assertIn("/xiuxian-admin/assets/", html)
        self.assertNotIn("./assets/", html)


    def test_admin_manager_exposes_mystic_and_signin_probability_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            manager = admin.AdminManager(admin.JsonStore(data_dir), data_dir)

            config = manager.load_config()
            self.assertEqual(config["mystic"]["fishing_option_rate"], 0.05)
            self.assertEqual(config["signin"]["extra_fishing_chance_rate"], 0.10)

            config["mystic"]["fishing_option_rate"] = 0.25
            config["signin"]["extra_fishing_chance_rate"] = 0.35
            manager.save_config(config)

            payload = manager.mystic_payload()
            self.assertEqual(payload["fishing_option_rate"], 0.25)
            self.assertEqual(payload["extra_fishing_chance_rate"], 0.35)

    def test_fallback_server_matches_unknown_api_and_asset_auth_boundaries(self) -> None:
        manager = FakeManager()
        old_root = admin.ADMIN_WEB_ROOT
        old_index = admin.ADMIN_WEB_INDEX

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "assets").mkdir()
            (root / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
            (root / "assets" / "app.js").write_text("console.log('ready')", encoding="utf-8")
            admin.ADMIN_WEB_ROOT = root
            admin.ADMIN_WEB_INDEX = root / "index.html"

            handle = admin.start_admin_server(manager, host="127.0.0.1", port=0)
            try:
                port = handle.port
                for method in ("GET", "POST", "PUT"):
                    status, content_type, body = _http_request(port, "/xiuxian-admin/api/missing", method=method)
                    self.assertEqual(status, 401)
                    self.assertIn("application/json", content_type)
                    self.assertEqual(_json_body(body)["error"], "unauthorized")

                    status, content_type, body = _http_request(
                        port,
                        "/xiuxian-admin/api/missing",
                        method=method,
                        token="secret",
                    )
                    self.assertEqual(status, 404)
                    self.assertIn("application/json", content_type)
                    self.assertEqual(_json_body(body)["error"], "not found")

                status, content_type, body = _http_request(
                    port,
                    "/xiuxian-admin/api/dashboard",
                    token="secret",
                )
                self.assertEqual(status, 200)
                self.assertIn("application/json", content_type)
                self.assertEqual(_json_body(body)["source"], "dashboard")

                status, content_type, body = _http_request(
                    port,
                    "/xiuxian-admin/api/players/42",
                    token="secret",
                )
                self.assertEqual(status, 200)
                self.assertIn("application/json", content_type)
                player_detail = _json_body(body)
                self.assertEqual(player_detail["record"]["user_id"], "42")
                self.assertIn("realms", player_detail["meta"])

                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/xiuxian-admin/api/players/42",
                    data=json.dumps({"realm_index": 1, "custom_note": "fallback"}, ensure_ascii=False).encode("utf-8"),
                    method="PUT",
                )
                request.add_header("X-Xiuxian-Token", "secret")
                request.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    player_saved = _json_body(response.read())
                self.assertEqual(player_saved["record"]["custom_note"], "fallback")
                self.assertIn("cultivation_routes", player_saved["meta"])

                status, _, body = _http_request(port, "/xiuxian-admin/assets/app.js")
                self.assertEqual(status, 200)
                self.assertIn(b"console.log", body)

                for asset_path in (
                    "/xiuxian-admin/assets/item-icons/items/item_001.png",
                    "/xiuxian-admin/assets/character-portraits/beast_001.png",
                    "/xiuxian-admin/assets/beast-spell-icons/br_spell_001.png",
                ):
                    status, content_type, body = _http_request(port, asset_path)
                    self.assertEqual(status, 401)
                    self.assertIn("application/json", content_type)
                    self.assertEqual(_json_body(body)["error"], "unauthorized")
            finally:
                handle.stop()
                admin.ADMIN_WEB_ROOT = old_root
                admin.ADMIN_WEB_INDEX = old_index


if __name__ == "__main__":
    unittest.main()
