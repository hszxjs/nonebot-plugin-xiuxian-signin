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
        path_params: dict[str, str] | None = None,
    ) -> None:
        self.headers = HeaderMap({"x-xiuxian-token": token} if token else {})
        self.query_params = {"token": query_token} if query_token else {}
        self.path_params = path_params or {}


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

            paths = [route["path"] for route in driver.server_app.routes]
            unknown_path = "/xiuxian-admin/api/{api_path:path}"
            self.assertIn(unknown_path, paths)
            known_api_paths = {
                "/xiuxian-admin/api/dashboard",
                "/xiuxian-admin/api/config",
                "/xiuxian-admin/api/players",
                "/xiuxian-admin/api/players/{user_id}",
                "/xiuxian-admin/api/backup",
                "/xiuxian-admin/api/items",
                "/xiuxian-admin/api/beast-realm/cards",
                "/xiuxian-admin/api/mystic",
                "/xiuxian-admin/api/equipment-rules",
            }
            for known_api_path in known_api_paths:
                self.assertLess(paths.index(known_api_path), paths.index(unknown_path))
            public_asset_path = "/xiuxian-admin/assets/{asset_path:path}"
            runtime_asset_paths = {
                "/xiuxian-admin/assets/item-icons/{icon_path:path}",
                "/xiuxian-admin/assets/character-portraits/{portrait_name}",
                "/xiuxian-admin/assets/beast-spell-icons/{icon_name}",
            }
            for runtime_asset_path in runtime_asset_paths:
                self.assertLess(paths.index(runtime_asset_path), paths.index(public_asset_path))
            self.assertLess(paths.index(public_asset_path), paths.index(unknown_path))
            self.assertLess(paths.index(unknown_path), paths.index("/xiuxian-admin/{asset_path:path}"))

            unknown_route = driver.server_app.routes[paths.index(unknown_path)]
            self.assertEqual(set(unknown_route["methods"]), {"GET", "POST", "PUT"})

            unauthorized = asyncio.run(unknown_route["endpoint"](FakeRequest()))
            self.assertEqual(unauthorized.status_code, 401)
            self.assertEqual(unauthorized.data["error"], "unauthorized")

            authorized = asyncio.run(unknown_route["endpoint"](FakeRequest(token="secret")))
            self.assertEqual(authorized.status_code, 404)
            self.assertEqual(authorized.data["error"], "not found")

            dashboard_route = driver.server_app.routes[paths.index("/xiuxian-admin/api/dashboard")]
            dashboard = asyncio.run(dashboard_route["endpoint"](FakeRequest(token="secret")))
            self.assertEqual(dashboard.status_code, 200)
            self.assertEqual(dashboard.data["source"], "dashboard")

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
