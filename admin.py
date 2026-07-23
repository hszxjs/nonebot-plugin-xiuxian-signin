from __future__ import annotations

import json
import shutil
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from zoneinfo import ZoneInfo

from . import beast_realm, domain, mystic_dungeon
from .admin_dashboard import build_dashboard_payload
from .mystic_dungeon import (
    DungeonRisk,
    MysticGameplayConfig,
    MysticTemplateCatalog,
    default_mystic_gameplay_config,
)
from .storage import JsonStore

ITEM_ICON_ROOT = Path(__file__).parent / "assets" / "item_icons"
ITEM_ICON_RECORDS = ITEM_ICON_ROOT / "item_icon_records.json"
CHARACTER_PORTRAIT_ROOT = Path(__file__).parent / "assets" / "character_portraits" / "portraits"
BEAST_SPELL_ICON_ROOT = Path(__file__).parent / "assets" / "beast_realm_spell_icons"
ADMIN_WEB_ROOT = Path(__file__).parent / "assets" / "admin_web"
ADMIN_WEB_INDEX = ADMIN_WEB_ROOT / "index.html"
ADMIN_WEB_MISSING_HTML = """<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<title>修仙签到后台</title>
<body style="font-family:system-ui,sans-serif;max-width:720px;margin:48px auto;line-height:1.7">
<h1>后台前端尚未构建</h1>
<p>请在仓库根目录执行 <code>npm --prefix webui install</code> 和 <code>npm --prefix webui run build</code>，然后重新访问后台。</p>
</body>
</html>"""
_ITEM_ICON_RECORD_CACHE: list[dict[str, Any]] | None = None
_ITEM_ICON_LOOKUP_CACHE: tuple[dict[str, str], dict[str, str], list[tuple[str, str]]] | None = None
_MYSTIC_CATALOG = MysticTemplateCatalog.from_files()


def _mystic_theme_ids(risk: DungeonRisk) -> list[str]:
    return sorted(
        theme_id
        for theme_id, theme in _MYSTIC_CATALOG.themes.items()
        if theme.risk is risk
    )


def item_icon_records() -> list[dict[str, Any]]:
    global _ITEM_ICON_RECORD_CACHE
    if _ITEM_ICON_RECORD_CACHE is not None:
        return _ITEM_ICON_RECORD_CACHE
    try:
        raw = json.loads(ITEM_ICON_RECORDS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = []
    _ITEM_ICON_RECORD_CACHE = [item for item in raw if isinstance(item, dict)]
    return _ITEM_ICON_RECORD_CACHE


def item_icon_lookup() -> tuple[dict[str, str], dict[str, str], list[tuple[str, str]]]:
    global _ITEM_ICON_LOOKUP_CACHE
    if _ITEM_ICON_LOOKUP_CACHE is not None:
        return _ITEM_ICON_LOOKUP_CACHE
    exact: dict[str, str] = {}
    categories: dict[str, str] = {}
    names: list[tuple[str, str]] = []
    for record in item_icon_records():
        icon = str(record.get("icon") or "").replace("\\", "/").lstrip("/")
        if not icon or not safe_item_icon_path(icon):
            continue
        item_name = str(record.get("item_name") or "").strip()
        if item_name:
            exact.setdefault(item_name, icon)
            names.append((item_name, icon))
        category = str(record.get("category") or "").strip()
        if category:
            categories.setdefault(category, icon)
    _ITEM_ICON_LOOKUP_CACHE = (exact, categories, names)
    return _ITEM_ICON_LOOKUP_CACHE


def item_icon_rel_path_for(name: str, category: str = "") -> str:
    exact, categories, names = item_icon_lookup()
    candidate = str(name or "").strip()
    if candidate:
        icon = exact.get(candidate)
        if icon:
            return icon
        for record_name, icon in names:
            if candidate in record_name or record_name in candidate:
                return icon
    if category:
        return categories.get(str(category).strip(), "")
    return ""


def safe_item_icon_path(rel_path: str) -> Path | None:
    rel = str(rel_path or "").replace("\\", "/").lstrip("/")
    if not rel or any(part in {"", ".", ".."} for part in rel.split("/")):
        return None
    try:
        root = ITEM_ICON_ROOT.resolve()
        path = (ITEM_ICON_ROOT / rel).resolve()
        path.relative_to(root)
    except (OSError, ValueError):
        return None
    return path if path.is_file() else None



def safe_character_portrait_path(file_name: str) -> Path | None:
    name = str(file_name or "").replace("\\", "/").split("/")[-1]
    if not name or name in {".", ".."} or not name.endswith(".png"):
        return None
    try:
        root = CHARACTER_PORTRAIT_ROOT.resolve()
        path = (CHARACTER_PORTRAIT_ROOT / name).resolve()
        path.relative_to(root)
    except (OSError, ValueError):
        return None
    return path if path.is_file() else None


def safe_beast_spell_icon_path(file_name: str) -> Path | None:
    name = str(file_name or "").replace("\\", "/").split("/")[-1]
    if not name or name in {".", ".."} or not name.endswith(".png"):
        return None
    try:
        root = BEAST_SPELL_ICON_ROOT.resolve()
        path = (BEAST_SPELL_ICON_ROOT / name).resolve()
        path.relative_to(root)
    except (OSError, ValueError):
        return None
    return path if path.is_file() else None
def _default_realm_tier_unlocks() -> dict[str, list[str]]:
    fake_immortal = domain.REALMS.index("假仙境")
    return {
        str(index): ["凡品", "黄阶", "玄阶", "地阶", "天阶"] + (["仙阶"] if index >= fake_immortal else [])
        for index in range(len(domain.REALMS))
    }


DEFAULT_ADMIN_CONFIG: dict[str, Any] = {
    "version": 1,
    "equipment_rules": {
        "realm_tier_unlocks": _default_realm_tier_unlocks(),
        "tier_default_realm": {
            "凡品": 0,
            "黄阶": 0,
            "玄阶": 2,
            "地阶": 3,
            "天阶": 4,
            "仙阶": domain.REALMS.index("假仙境"),
            "仙帝兵": domain.REALMS.index("太乙境"),
        },
        "artifact_drop_pools": domain.default_artifact_drop_pools(),
        "artifact_power_base": dict(domain.ARTIFACT_POWER_BASE),
        "artifact_realm_power_base": {str(key): value for key, value in domain.ARTIFACT_REALM_POWER_BASE.items()},
        "artifact_tier_power_ratio": dict(domain.ARTIFACT_TIER_POWER_RATIO),
        "artifact_grade_ratio": dict(domain.ARTIFACT_GRADE_RATIO),
        "artifact_immortal_upgrade_rate": domain.ARTIFACT_IMMORTAL_UPGRADE_RATE,
    },
    "mystic": {
        **default_mystic_gameplay_config().to_mapping(),
        "enabled_types": _mystic_theme_ids(DungeonRisk.NORMAL),
        "enabled_high_risk_types": _mystic_theme_ids(DungeonRisk.HIGH),
        "category_weights": domain.default_mystic_category_weights(),
        "drop_overrides": {},
        "fishing_option_rate": 0.05,
        "signin_normal_token_count": 0,
        "signin_high_risk_token_count": 0,
        "daily_task_normal_token_count": 0,
        "daily_task_high_risk_token_count": 0,
    },
    "signin": {"extra_fishing_chance_rate": 0.10},
    "item_overrides": {},
    "beast_realm": {"card_pool_copies": 10, "card_overrides": {}},
}


ITEM_OVERRIDE_TEXT_FIELDS = {"category", "required_realm", "required_attribute", "usage", "source", "story"}
ITEM_OVERRIDE_LIST_FIELDS = {"tiers", "grades"}


def deep_update(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = value
    return target


class AdminManager:
    def __init__(self, store: JsonStore, data_dir: Path, token: str = "", timezone: str = "Asia/Shanghai") -> None:
        self.store = store
        self.data_dir = data_dir
        self.config_path = data_dir / "admin_config.json"
        self.token = token.strip()
        self.timezone = str(timezone or "Asia/Shanghai").strip() or "Asia/Shanghai"

    def today(self) -> date:
        try:
            return datetime.now(ZoneInfo(self.timezone)).date()
        except Exception:
            return datetime.now().date()

    def load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            self.save_config(DEFAULT_ADMIN_CONFIG)
            return json.loads(json.dumps(DEFAULT_ADMIN_CONFIG, ensure_ascii=False))
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        merged = json.loads(json.dumps(DEFAULT_ADMIN_CONFIG, ensure_ascii=False))
        deep_update(merged, data if isinstance(data, dict) else {})
        return merged

    def save_config(self, data: dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.config_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.config_path)

    def apply_config(self) -> None:
        config = self.load_config()
        domain.apply_admin_config(config)
        beast_realm.apply_admin_config(config)
        mystic_dungeon.apply_admin_config(config)

    def backup_users(self) -> dict[str, Any]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        backup_dir = self.data_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        dst = backup_dir / f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        if self.store.user_file_path.exists():
            shutil.copy2(self.store.user_file_path, dst)
        else:
            dst.write_text("{}", encoding="utf-8")
        return {"ok": True, "path": str(dst)}

    def list_players(self, query: str = "") -> list[dict[str, Any]]:
        users = self.store._read_json(self.store.user_file_path)
        groups = self.store._read_json(self.store.group_file_path)
        nicknames: dict[str, str] = {}
        for group in groups.values():
            if isinstance(group, dict):
                for user_id, info in dict(group.get("users") or {}).items():
                    if isinstance(info, dict) and info.get("nickname"):
                        nicknames[str(user_id)] = str(info.get("nickname"))
        query_text = str(query or "").lower()
        players: list[dict[str, Any]] = []
        for user_id, raw in users.items():
            if not isinstance(raw, dict):
                continue
            nickname = nicknames.get(str(user_id), "")
            if query_text and query_text not in str(user_id).lower() and query_text not in nickname.lower():
                continue
            record = domain.UserRecord.from_dict(raw)
            players.append(
                {
                    "user_id": str(user_id),
                    "nickname": nickname,
                    "realm": record.realm,
                    "spirit_stones": int(record.spirit_stones),
                    "battle_power": domain.battle_power(record),
                }
            )
        players.sort(key=lambda item: item["battle_power"], reverse=True)
        return players

    def get_player_record(self, user_id: str) -> dict[str, Any] | None:
        raw = self.store._read_json(self.store.user_file_path).get(str(user_id))
        return raw if isinstance(raw, dict) else None

    def save_player_record(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        saved = dict(data)
        saved["user_id"] = str(user_id)
        domain.UserRecord.from_dict(saved)
        domain.sanitize_user_record_data(saved)
        users = self.store._read_json(self.store.user_file_path)
        users[str(user_id)] = saved
        self.store._write_json(self.store.user_file_path, users)
        return users[str(user_id)]

    def player_meta(self) -> dict[str, Any]:
        realm_quality_titles = {str(key): list(value) for key, value in domain.REALM_QUALITY_TITLES.items()}
        quality_titles = list(
            dict.fromkeys(
                list(domain.FOUNDATION_QUALITY_TITLES)
                + [title for titles in domain.REALM_QUALITY_TITLES.values() for title in titles]
            )
        )
        categories = list(dict.fromkeys(list(domain.REWARD_CATEGORIES) + [domain.IMMORTAL_SEED_CATEGORY]))
        mystic_types = list(
            dict.fromkeys(list(domain.MYSTIC_REALM_TYPES) + list(domain.HIGH_RISK_MYSTIC_REALM_TYPES))
        )
        return {
            "realms": [{"index": index, "name": name} for index, name in enumerate(domain.REALMS)],
            "attributes": list(domain.ROOT_ATTRIBUTES),
            "attribute_labels": {attr: domain.root_attribute_label(attr) for attr in domain.ROOT_ATTRIBUTES},
            "tiers": list(domain.ROOT_TIER_ORDER),
            "grades": list(domain.GRADE_ORDER),
            "categories": categories,
            "mystic_types": mystic_types,
            "cultivation_routes": list(domain.CULTIVATION_ROUTES),
            "foundation_quality_titles": list(domain.FOUNDATION_QUALITY_TITLES),
            "realm_quality_titles": realm_quality_titles,
            "quality_titles": quality_titles,
        }

    def mystic_payload(self) -> dict[str, Any]:
        config = self.load_config()
        mystic = config.get("mystic", {}) if isinstance(config.get("mystic"), dict) else {}
        signin = config.get("signin", {}) if isinstance(config.get("signin"), dict) else {}
        gameplay = MysticGameplayConfig.from_mapping(mystic).to_mapping()
        themes = [
            {
                "theme_id": theme_id,
                "display_name": theme.display_name,
                "risk": theme.risk.value,
                "template_id": theme.template_id,
                "background_path": str(theme.background_path),
                "background_exists": theme.background_path.is_file(),
                "template_exists": theme.template_id in _MYSTIC_CATALOG.templates,
            }
            for theme_id, theme in sorted(_MYSTIC_CATALOG.themes.items())
        ]
        return {
            **gameplay,
            "types": _mystic_theme_ids(DungeonRisk.NORMAL),
            "high_risk_types": _mystic_theme_ids(DungeonRisk.HIGH),
            "enabled_types": mystic.get(
                "enabled_types",
                _mystic_theme_ids(DungeonRisk.NORMAL),
            ),
            "enabled_high_risk_types": mystic.get(
                "enabled_high_risk_types",
                _mystic_theme_ids(DungeonRisk.HIGH),
            ),
            "supported_map_sizes": list({rule["node_count"] for rule in gameplay["map_size_rules"]}),
            "themes": themes,
            "token_definitions": dict(domain.MYSTIC_TOKEN_DEFINITIONS),
            "category_weights": mystic.get("category_weights", {}),
            "drop_overrides": mystic.get("drop_overrides", {}),
            "fishing_option_rate": mystic.get("fishing_option_rate", 0.05),
            "signin_normal_token_count": mystic.get("signin_normal_token_count", 0),
            "signin_high_risk_token_count": mystic.get("signin_high_risk_token_count", 0),
            "daily_task_normal_token_count": mystic.get("daily_task_normal_token_count", 0),
            "daily_task_high_risk_token_count": mystic.get("daily_task_high_risk_token_count", 0),
            "extra_fishing_chance_rate": signin.get("extra_fishing_chance_rate", 0.10),
            "categories": list(domain.REWARD_CATEGORIES) + [domain.IMMORTAL_SEED_CATEGORY],
            "tiers": list(domain.TIER_ORDER),
            "grades": list(domain.GRADE_ORDER),
        }

    def save_mystic_config(self, data: dict[str, Any]) -> dict[str, Any]:
        validated = MysticGameplayConfig.from_mapping(data).to_mapping()
        normal_ids = set(_mystic_theme_ids(DungeonRisk.NORMAL))
        high_risk_ids = set(_mystic_theme_ids(DungeonRisk.HIGH))
        enabled_types = [str(item) for item in data.get("enabled_types", normal_ids)]
        enabled_high_risk_types = [
            str(item)
            for item in data.get("enabled_high_risk_types", high_risk_ids)
        ]
        if not set(enabled_types) <= normal_ids:
            raise ValueError("enabled_types contains an unknown normal theme")
        if not set(enabled_high_risk_types) <= high_risk_ids:
            raise ValueError("enabled_high_risk_types contains an unknown high-risk theme")
        validated["enabled_types"] = enabled_types
        validated["enabled_high_risk_types"] = enabled_high_risk_types
        config = self.load_config()
        current_mystic = config.get("mystic", {})
        preserved = dict(current_mystic) if isinstance(current_mystic, dict) else {}
        preserved.update(validated)
        config["mystic"] = preserved
        self.save_config(config)
        self.apply_config()
        return self.mystic_payload()

    def equipment_rules(self) -> dict[str, Any]:
        return self.load_config().get("equipment_rules", {})

    def equipment_meta(self) -> dict[str, Any]:
        return {
            "realms": [{"index": index, "name": name} for index, name in enumerate(domain.REALMS)],
            "tiers": list(domain.ARTIFACT_REALM_BOUND_TIERS),
            "grades": list(domain.GRADE_ORDER),
            "attributes": list(domain.ARTIFACT_ATTRIBUTES),
            "attribute_labels": {attr: domain.root_attribute_label(attr) for attr in domain.ARTIFACT_ATTRIBUTES},
            "artifacts": [
                {
                    "name": str(item.get("name", "")),
                    "realm_index": int(item.get("realm_index", 0)),
                    "realm": str(item.get("realm", "")),
                    "tier": str(item.get("tier", "")),
                    "grade": str(item.get("grade", "")),
                    "attribute": str(item.get("attribute", "")),
                    "attribute_label": domain.root_attribute_label(str(item.get("attribute", ""))),
                }
                for item in domain.ARTIFACT_REALM_CATALOG
            ],
        }

    def dashboard_payload(self) -> dict[str, Any]:
        users = self.store._read_json(self.store.user_file_path)
        realm_names = {
            int(item["index"]): str(item["name"])
            for item in self.equipment_meta().get("realms", [])
            if isinstance(item, dict) and "index" in item and "name" in item
        }

        def battle_power_resolver(user_id: str, raw: dict[str, Any]) -> int:
            data = dict(raw)
            data["user_id"] = str(data.get("user_id") or user_id)
            return domain.battle_power(domain.UserRecord.from_dict(data))

        return build_dashboard_payload(users, self.today(), realm_names, battle_power_resolver)

    def item_meta(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        categories = list(dict.fromkeys(list(domain.REWARD_CATEGORIES) + [domain.IMMORTAL_SEED_CATEGORY]))
        for item in items:
            category = str(item.get("category") or "").strip()
            if category and category not in categories:
                categories.append(category)
        return {
            "categories": categories,
            "tiers": list(domain.TIER_ORDER),
            "grades": list(domain.GRADE_ORDER),
            "realms": ["随品阶或具体配置变化"] + list(domain.REALMS),
            "attributes": list(domain.ROOT_ATTRIBUTES),
        }

    def item_overrides(self) -> dict[str, dict[str, Any]]:
        raw = self.load_config().get("item_overrides", {})
        if not isinstance(raw, dict):
            return {}
        overrides: dict[str, dict[str, Any]] = {}
        for name, value in raw.items():
            if isinstance(value, dict):
                overrides[str(name)] = value
        return overrides

    def item_catalog(self) -> list[dict[str, Any]]:
        items = domain.admin_item_catalog()
        overrides = self.item_overrides()
        for item in items:
            override = overrides.get(str(item.get("name") or ""))
            if override:
                for field in ITEM_OVERRIDE_TEXT_FIELDS:
                    if field in override:
                        item[field] = str(override.get(field) or "")
                for field in ITEM_OVERRIDE_LIST_FIELDS:
                    value = override.get(field)
                    if isinstance(value, list):
                        item[field] = [str(part) for part in value if str(part).strip()]
                item["customized"] = True
            icon = item_icon_rel_path_for(str(item.get("name") or ""), str(item.get("category") or ""))
            if icon:
                item["icon"] = icon
        return items

    def item_payload(self) -> dict[str, Any]:
        items = self.item_catalog()
        return {"ok": True, "items": items, "meta": self.item_meta(items)}

    def beast_card_payload(self) -> dict[str, Any]:
        payload = beast_realm.admin_card_payload()
        config = self.load_config().get("beast_realm", {})
        overrides = config.get("card_overrides", {}) if isinstance(config, dict) else {}
        if not isinstance(overrides, dict):
            overrides = {}
        for card in payload.get("cards", []):
            if isinstance(card, dict):
                card["customized"] = str(card.get("id")) in overrides
        return payload
def _normalize_base_path(base_path: str) -> str:
    return "/" + str(base_path or "xiuxian-admin").strip("/")


def _static_root(static_root: Path | None = None) -> Path:
    return static_root or ADMIN_WEB_ROOT


def _static_index(static_root: Path | None = None) -> Path:
    return _static_root(static_root) / "index.html"


def _safe_static_file(root: Path, request_path: str) -> Path | None:
    requested = str(request_path or "").replace("\\", "/").lstrip("/")
    if not requested:
        requested = "index.html"
    try:
        root_resolved = root.resolve()
        candidate = (root / requested).resolve()
        candidate.relative_to(root_resolved)
    except (OSError, ValueError):
        return None
    return candidate if candidate.is_file() else None


def _scoped_admin_index_html(index_bytes: bytes, base_path: str) -> str:
    asset_prefix = _normalize_base_path(base_path) + "/assets/"
    text = index_bytes.decode("utf-8")
    text = text.replace("./assets/", asset_prefix)
    text = text.replace('href="/assets/', f'href="{asset_prefix}')
    text = text.replace('src="/assets/', f'src="{asset_prefix}')
    return text


scoped_admin_index_html = _scoped_admin_index_html


def _token_from_parts(header_token: str | None, query_token: str | None) -> str:
    return str(header_token or query_token or "").strip()


def _authorized(manager: AdminManager, header_token: str | None, query_token: str | None) -> bool:
    return not manager.token or _token_from_parts(header_token, query_token) == manager.token


def _require_authorized(manager: AdminManager, header_token: str | None, query_token: str | None) -> None:
    if not _authorized(manager, header_token, query_token):
        raise HTTPException(status_code=401, detail="unauthorized")


def _json_error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status_code)


async def _json_object_or_error(request: Request, object_error: str) -> tuple[dict[str, Any] | None, JSONResponse | None]:
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, _json_error("invalid json body", 400)
    if not isinstance(data, dict):
        return None, _json_error(object_error, 400)
    return data, None


def create_admin_app(
    *,
    manager: AdminManager,
    base_path: str = "/xiuxian-admin",
    static_root: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Xiuxian Signin Admin", docs_url=None, redoc_url=None)
    normalized_base_path = _normalize_base_path(base_path)
    root = _static_root(static_root)

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return _json_error(str(exc.detail or "error"), exc.status_code)

    def authorize(x_xiuxian_token: str | None, token: str | None) -> None:
        _require_authorized(manager, x_xiuxian_token, token)

    async def root_redirect() -> RedirectResponse:
        return RedirectResponse(normalized_base_path)

    async def dashboard(
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        return manager.dashboard_payload()

    async def get_config(
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        return {"ok": True, "config": manager.load_config()}

    async def put_config(
        request: Request,
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        data, error = await _json_object_or_error(request, "config must be an object")
        if error is not None:
            return error
        assert data is not None
        manager.save_config(data)
        manager.apply_config()
        return {"ok": True, "config": manager.load_config()}

    async def list_players(
        q: str = Query(default=""),
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        return {"ok": True, "players": manager.list_players(q)}

    async def get_player(
        user_id: str,
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        raw = manager.get_player_record(user_id)
        if not isinstance(raw, dict):
            return _json_error("player not found", 404)
        return {"ok": True, "record": raw, "meta": manager.player_meta()}

    async def put_player(
        user_id: str,
        request: Request,
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        data, error = await _json_object_or_error(request, "record must be an object")
        if error is not None:
            return error
        assert data is not None
        return {"ok": True, "record": manager.save_player_record(user_id, data), "meta": manager.player_meta()}

    async def backup(
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        return manager.backup_users()

    async def items(
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        return manager.item_payload()

    async def beast_cards(
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        return manager.beast_card_payload()

    async def mystic(
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        return {"ok": True, "mystic": manager.mystic_payload()}

    async def put_mystic(
        request: Request,
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        data, error = await _json_object_or_error(request, "mystic config must be an object")
        if error is not None:
            return error
        assert data is not None
        try:
            payload = manager.save_mystic_config(data)
        except ValueError as exc:
            return _json_error(str(exc), 400)
        return {"ok": True, "mystic": payload}

    async def equipment_rules(
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        return {"ok": True, "rules": manager.equipment_rules(), "meta": manager.equipment_meta()}

    async def item_icon(
        icon_path: str,
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        path = safe_item_icon_path(unquote(icon_path))
        if path is None:
            return _json_error("icon not found", 404)
        return FileResponse(path, media_type="image/png")

    async def character_portrait(
        portrait_name: str,
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        path = safe_character_portrait_path(unquote(portrait_name))
        if path is None:
            return _json_error("portrait not found", 404)
        return FileResponse(path, media_type="image/png")

    async def beast_spell_icon(
        icon_name: str,
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        path = safe_beast_spell_icon_path(unquote(icon_name))
        if path is None:
            return _json_error("spell icon not found", 404)
        return FileResponse(path, media_type="image/png")

    async def static_asset(asset_path: str) -> Any:
        asset = _safe_static_file(root / "assets", asset_path)
        if asset is None:
            return _json_error("asset not found", 404)
        return FileResponse(asset)

    async def spa_page(
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        index = _static_index(root)
        if not index.is_file():
            return PlainTextResponse("Xiuxian admin WebUI has not been built.", status_code=503)
        return Response(
            _scoped_admin_index_html(index.read_bytes(), normalized_base_path),
            media_type="text/html; charset=utf-8",
        )

    async def unknown_api(
        token: str | None = Query(default=None),
        x_xiuxian_token: str | None = Header(default=None, alias="X-Xiuxian-Token"),
    ) -> Any:
        authorize(x_xiuxian_token, token)
        return _json_error("not found", 404)

    app.add_api_route("/", root_redirect, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/api/dashboard", dashboard, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/api/config", get_config, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/api/config", put_config, methods=["PUT"])
    app.add_api_route(f"{normalized_base_path}/api/players", list_players, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/api/players/{{user_id}}", get_player, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/api/players/{{user_id}}", put_player, methods=["PUT"])
    app.add_api_route(f"{normalized_base_path}/api/backup", backup, methods=["POST"])
    app.add_api_route(f"{normalized_base_path}/api/items", items, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/api/beast-realm/cards", beast_cards, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/api/mystic", mystic, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/api/mystic", put_mystic, methods=["PUT"])
    app.add_api_route(f"{normalized_base_path}/api/equipment-rules", equipment_rules, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/api/{{api_path:path}}", unknown_api, methods=["GET", "POST", "PUT"])
    app.add_api_route(f"{normalized_base_path}/assets/item-icons/{{icon_path:path}}", item_icon, methods=["GET"])
    app.add_api_route(
        f"{normalized_base_path}/assets/character-portraits/{{portrait_name}}",
        character_portrait,
        methods=["GET"],
    )
    app.add_api_route(f"{normalized_base_path}/assets/beast-spell-icons/{{icon_name}}", beast_spell_icon, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/assets/{{asset_path:path}}", static_asset, methods=["GET"])
    app.add_api_route(normalized_base_path, spa_page, methods=["GET"])
    app.add_api_route(f"{normalized_base_path}/{{asset_path:path}}", spa_page, methods=["GET"])
    return app


def install_admin_routes(driver: Any, manager: AdminManager, base_path: str = "/xiuxian-admin") -> bool:
    server_app = getattr(driver, "server_app", None)
    if server_app is None:
        return False
    admin_app = create_admin_app(manager=manager, base_path=base_path)
    for route in admin_app.router.routes:
        server_app.router.routes.append(route)
    manager.apply_config()
    return True


class AdminServerHandle:
    def __init__(self, server: uvicorn.Server, thread: threading.Thread, host: str, port: int, base_path: str) -> None:
        self.server = server
        self.thread = thread
        self.host = host
        self.port = port
        self.base_path = base_path

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=3)


def start_admin_server(
    manager: AdminManager,
    host: str = "0.0.0.0",
    port: int = 8081,
    base_path: str = "/xiuxian-admin",
) -> AdminServerHandle:
    bind_host = str(host or "0.0.0.0")
    bind_port = 8081 if port is None or str(port) == "" else int(port)
    normalized_base_path = _normalize_base_path(base_path)
    app = create_admin_app(manager=manager, base_path=normalized_base_path)
    config = uvicorn.Config(app, host=bind_host, port=bind_port, log_level="warning")
    server = uvicorn.Server(config)
    manager.apply_config()
    thread = threading.Thread(target=server.run, name="xiuxian-admin-http", daemon=True)
    thread.start()
    return AdminServerHandle(server, thread, bind_host, bind_port, normalized_base_path)
