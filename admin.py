from __future__ import annotations

import json
import shutil
import threading
from datetime import date, datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mimetypes import guess_type
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
from zoneinfo import ZoneInfo

from . import beast_realm, domain
from .admin_dashboard import build_dashboard_payload
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
        "enabled_types": list(domain.MYSTIC_REALM_TYPES),
        "enabled_high_risk_types": list(domain.HIGH_RISK_MYSTIC_REALM_TYPES),
        "category_weights": domain.default_mystic_category_weights(),
        "drop_overrides": {},
    },
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
        data = dict(data)
        data["user_id"] = str(user_id)
        record = domain.UserRecord.from_dict(data)
        users = self.store._read_json(self.store.user_file_path)
        users[str(user_id)] = record.to_dict()
        self.store._write_json(self.store.user_file_path, users)
        return users[str(user_id)]

    def mystic_payload(self) -> dict[str, Any]:
        config = self.load_config()
        mystic = config.get("mystic", {}) if isinstance(config.get("mystic"), dict) else {}
        return {
            "types": list(domain.MYSTIC_REALM_TYPES),
            "high_risk_types": list(domain.HIGH_RISK_MYSTIC_REALM_TYPES),
            "enabled_types": mystic.get("enabled_types", list(domain.MYSTIC_REALM_TYPES)),
            "enabled_high_risk_types": mystic.get("enabled_high_risk_types", list(domain.HIGH_RISK_MYSTIC_REALM_TYPES)),
            "category_weights": mystic.get("category_weights", {}),
            "drop_overrides": mystic.get("drop_overrides", {}),
            "categories": list(domain.REWARD_CATEGORIES) + [domain.IMMORTAL_SEED_CATEGORY],
            "tiers": list(domain.TIER_ORDER),
            "grades": list(domain.GRADE_ORDER),
        }

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
        return build_dashboard_payload(users, self.today(), realm_names)

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
def json_response(data: Any, status: int = 200) -> Any:
    from starlette.responses import JSONResponse

    return JSONResponse(data, status_code=status)


def token_from_request(request: Any) -> str:
    return str(request.headers.get("x-xiuxian-token") or request.query_params.get("token") or "").strip()


def authorized(manager: AdminManager, request: Any) -> bool:
    return not manager.token or token_from_request(request) == manager.token


def unauthorized() -> Any:
    return json_response({"ok": False, "error": "unauthorized"}, 401)


def admin_web_asset_path(path_text: str = "") -> Path | None:
    if not ADMIN_WEB_INDEX.exists():
        return None
    requested = path_text.replace("\\", "/").strip("/")
    target = ADMIN_WEB_INDEX if not requested else ADMIN_WEB_ROOT / requested
    try:
        resolved = target.resolve()
        root = ADMIN_WEB_ROOT.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError):
        return ADMIN_WEB_INDEX
    if resolved.is_file():
        return resolved
    return ADMIN_WEB_INDEX


def admin_web_static_asset_path(path_text: str) -> Path | None:
    requested = path_text.replace("\\", "/").strip("/")
    if not requested.startswith("assets/"):
        return None
    try:
        resolved = (ADMIN_WEB_ROOT / requested).resolve()
        asset_root = (ADMIN_WEB_ROOT / "assets").resolve()
        resolved.relative_to(asset_root)
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


ADMIN_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>修仙签到后台</title>
<style>
*{box-sizing:border-box}:root{--bg:#f4f7fb;--panel:#fff;--line:#d7e0ea;--text:#172033;--muted:#667085;--blue:#1864ab;--blue-soft:#e7f2ff;--gold:#9a6b24;--green:#027a48;--red:#b42318}body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);font:14px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.shell{width:min(100%,1920px);margin:0 auto;padding:clamp(12px,2vw,26px)}.top{display:flex;gap:16px;align-items:center;justify-content:space-between}.brand{font-size:23px;font-weight:800}.muted{color:var(--muted)}.toolbar,.tabs,.row,.chips{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.tabs{margin:14px 0}.tab.active{background:var(--blue-soft);border-color:#9dccf5;color:#0b5394}button,input,textarea,select{font:inherit}button{border:1px solid var(--line);background:#fff;border-radius:6px;padding:7px 10px;cursor:pointer}.primary{background:var(--blue);border-color:var(--blue);color:#fff}input,textarea,select{border:1px solid var(--line);border-radius:6px;background:#fff;padding:7px 9px;min-width:0}textarea{width:100%;resize:vertical;line-height:1.45}.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;min-width:0}.hidden{display:none!important}.status{margin:8px 0;color:var(--muted)}.ok{color:var(--green)}.err{color:var(--red)}.grid{display:grid;grid-template-columns:minmax(400px,30vw) minmax(720px,1fr);gap:14px;align-items:start}.table{overflow:auto;max-height:calc(100vh - 235px);border:1px solid var(--line);border-radius:6px}table{border-collapse:collapse;width:100%;background:#fff}th,td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;white-space:nowrap;vertical-align:top}th{position:sticky;top:0;background:#f8fafc;z-index:1}.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.field{display:flex;flex-direction:column;gap:4px}.field label{font-size:12px;color:var(--muted);font-weight:700}.field input,.field textarea,.field select{width:100%}.field select[multiple]{min-height:118px}.item-actions{margin-bottom:10px}.field.wide{grid-column:1/-1}.player-editor textarea{min-height:104px;font-family:Consolas,"SFMono-Regular",monospace;font-size:12px}.item-layout{display:grid;grid-template-columns:minmax(360px,42vw) minmax(420px,1fr);gap:14px;align-items:start}.item-tools{display:grid;grid-template-columns:1fr minmax(130px,180px) minmax(130px,180px) auto;gap:8px;margin-bottom:10px}.item-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(164px,1fr));gap:10px;max-height:calc(100vh - 258px);overflow:auto;padding-right:4px}.item-card{border:1px solid var(--line);border-radius:8px;background:#fff;padding:10px;display:grid;grid-template-columns:54px 1fr;gap:9px;align-items:center;cursor:pointer;min-height:86px}.item-card.active{border-color:#77b7ef;box-shadow:0 0 0 2px #d7edff}.item-icon{width:54px;height:54px;border:1px solid #e5ebf2;border-radius:8px;background:#f8fafc;display:grid;place-items:center;overflow:hidden}.item-icon img{max-width:48px;max-height:48px;display:block}.placeholder{color:#98a2b3;font-size:12px}.item-name{font-weight:800;line-height:1.25}.item-meta{font-size:12px;color:var(--muted);margin-top:3px}.chip{display:inline-flex;align-items:center;border:1px solid #e4d2aa;background:#fff8e6;color:#765214;border-radius:999px;padding:1px 7px;font-size:12px;margin:2px 4px 2px 0}.detail-head{display:flex;gap:12px;align-items:center;margin-bottom:10px}.detail-icon{width:78px;height:78px;border:1px solid var(--line);border-radius:8px;background:#f8fafc;display:grid;place-items:center;overflow:hidden}.detail-icon img{max-width:70px;max-height:70px}.detail-title{font-size:20px;font-weight:800}.detail textarea{min-height:78px}.config-textarea{min-height:calc(100vh - 310px);font-family:Consolas,"SFMono-Regular",monospace;font-size:12px}.mini-textarea{min-height:130px;font-family:Consolas,"SFMono-Regular",monospace;font-size:12px}.config-list{display:grid;gap:10px;max-height:calc(100vh - 238px);overflow:auto;padding-right:4px}.realm-block{border:1px solid var(--line);border-radius:8px;background:#fff;padding:10px}.realm-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}.realm-title{font-weight:800}.rule-table{width:100%;border-collapse:collapse}.rule-table th,.rule-table td{padding:5px;border-bottom:1px solid #edf2f7}.rule-table select,.rule-table input{width:100%;padding:5px 7px}.icon-btn{width:30px;height:30px;padding:0;display:inline-grid;place-items:center;font-weight:800}.check-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:7px}.check-item{display:flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:6px;padding:6px 8px;background:#fff}.check-item input{min-width:auto}.field label small{display:block;color:#98a2b3;font-weight:500}.summary-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-bottom:10px}.summary-card{border:1px solid var(--line);border-radius:8px;background:#fbfcfe;padding:10px}.summary-card b{display:block;font-size:20px}.section-title{font-size:16px;font-weight:800;margin:0 0 8px}.card-thumb{width:54px;height:74px;border:1px solid #e5ebf2;border-radius:6px;background:#101827;display:grid;place-items:center;overflow:hidden}.card-thumb img{width:100%;height:100%;object-fit:cover;display:block}.card-preview{width:118px;height:158px;border:1px solid #d8bf82;border-radius:8px;background:linear-gradient(180deg,#242b39,#111722);display:grid;place-items:center;overflow:hidden}.card-preview img{width:100%;height:100%;object-fit:cover}.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;max-height:calc(100vh - 258px);overflow:auto;padding-right:4px}.beast-card{border:1px solid var(--line);border-radius:8px;background:#fff;padding:9px;display:grid;grid-template-columns:54px 1fr;gap:9px;align-items:center;cursor:pointer;min-height:94px}.beast-card.active{border-color:#77b7ef;box-shadow:0 0 0 2px #d7edff}.beast-card .item-name{font-size:14px}.rules-textarea{min-height:180px;font-family:Consolas,"SFMono-Regular",monospace;font-size:12px}@media(max-width:1180px){.grid,.item-layout{grid-template-columns:1fr}.item-grid{max-height:46vh}.top{align-items:flex-start;flex-direction:column}.item-tools{grid-template-columns:1fr 1fr}}@media(max-width:720px){.shell{padding:10px}.tabs button,.toolbar button{flex:1 1 auto}.item-tools{grid-template-columns:1fr}.detail-head{align-items:flex-start}.table{max-height:42vh}}
</style>
</head>
<body>
<div class="shell">
  <div class="top"><div><div class="brand">修仙签到后台</div><div class="muted">玩家档案、物品图鉴、御兽卡牌、灵器规则、秘境掉落配置</div></div><div class="toolbar"><input id="token" placeholder="管理 Token"><button onclick="saveToken()">保存 Token</button><button onclick="backupUsers()">备份档案</button></div></div>
  <div class="tabs"><button class="tab active" onclick="showTab('players',this)">玩家档案</button><button class="tab" onclick="showTab('items',this)">物品图鉴</button><button class="tab" onclick="showTab('beastCards',this)">御兽卡牌</button><button class="tab" onclick="showTab('equipment',this)">灵器规则</button><button class="tab" onclick="showTab('mystic',this)">秘境掉落</button><button class="tab" onclick="showTab('config',this)">原始配置</button></div>
  <div id="status" class="status"></div>
  <section id="players" class="grid">
    <div class="panel"><div class="row"><input id="playerSearch" placeholder="搜索玩家 ID / 昵称"><button onclick="loadPlayers()">刷新</button></div><div class="table"><table><thead><tr><th>玩家</th><th>境界</th><th>战力</th><th>灵石</th></tr></thead><tbody id="playersBody"></tbody></table></div></div>
    <div class="panel player-editor"><div class="row"><b id="playerTitle">未选择玩家</b><span class="muted">字段会保存回玩家档案</span></div><div id="playerFields" class="form-grid"></div><div class="row"><button class="primary" onclick="savePlayer()">保存玩家</button><button onclick="resetPlayerForm()">撤回未保存修改</button></div></div>
  </section>
  <section id="items" class="item-layout hidden">
    <div class="panel"><div class="item-tools"><input id="itemSearch" placeholder="搜索名称 / 类别 / 用途 / 故事 / 获取途径" oninput="renderItems()"><select id="itemCategory" onchange="renderItems()"><option value="">全部类别</option></select><select id="itemTier" onchange="renderItems()"><option value="">全部阶级</option></select><button onclick="loadItems()">刷新</button></div><div id="itemGrid" class="item-grid"></div></div>
    <div class="panel detail"><div class="detail-head"><div id="detailIcon" class="detail-icon"><span class="placeholder">图标</span></div><div><div id="detailName" class="detail-title">请选择物品</div><div id="detailChips" class="chips"></div></div></div><div class="row item-actions"><button class="primary" onclick="saveItem()">保存图鉴条目</button><button onclick="resetItemForm()">撤回未保存修改</button><button onclick="clearItemOverride()">恢复默认</button></div><div class="form-grid"><div class="field"><label>名称</label><input id="itemName" readonly></div><div class="field"><label>类别</label><select id="itemCategoryField"></select></div><div class="field"><label>可能阶级</label><select id="itemTiers" multiple size="5"></select></div><div class="field"><label>可能品质</label><select id="itemGrades" multiple size="4"></select></div><div class="field"><label>所需境界</label><select id="itemRealm"></select></div><div class="field"><label>所需属性</label><select id="itemAttr"></select></div><div class="field wide"><label>用途</label><textarea id="itemUsage"></textarea></div><div class="field wide"><label>获取途径</label><textarea id="itemSource"></textarea></div><div class="field wide"><label>故事</label><textarea id="itemStory"></textarea></div><div class="field wide"><label>后台参数说明</label><textarea id="itemNote" readonly></textarea></div></div></div>
  </section>
  <section id="beastCards" class="item-layout hidden">
    <div class="panel"><div id="beastSummary" class="summary-cards"></div><div class="row item-actions"><div class="field"><label>默认卡池数量</label><input id="beastPoolDefault" type="number" min="0" step="1"></div><button class="primary" onclick="saveBeastRealmGlobal()">保存全局配置</button><button onclick="loadBeastCards()">刷新</button></div><div class="item-tools"><input id="cardSearch" placeholder="搜索名称 / ID / 阵营 / 效果 / 故事" oninput="renderBeastCards()"><select id="cardKindFilter" onchange="renderBeastCards()"><option value="">全部卡牌</option><option value="beast">随从牌</option><option value="spell">法术牌</option></select><select id="cardFactionFilter" onchange="renderBeastCards()"><option value="">全部阵营</option></select><button onclick="renderBeastCards()">筛选</button></div><div id="beastCardGrid" class="card-grid"></div></div>
    <div class="panel detail"><div class="detail-head"><div id="cardPreview" class="card-preview"><span class="placeholder">头像</span></div><div><div id="cardTitle" class="detail-title">请选择卡牌</div><div id="cardChips" class="chips"></div></div></div><div class="row item-actions"><button class="primary" onclick="saveBeastCard()">保存卡牌</button><button onclick="resetBeastCardForm()">撤回未保存修改</button><button onclick="clearBeastCardOverride()">恢复默认</button></div><div class="form-grid"><div class="field"><label>ID</label><input id="cardId" readonly></div><div class="field"><label>类型</label><input id="cardKind" readonly></div><div class="field"><label>名称</label><input id="cardName"></div><div class="field"><label>境界序号</label><select id="cardTier"></select></div><div class="field"><label>境界名称</label><input id="cardRealm"></div><div class="field"><label>攻击</label><input id="cardAttack" type="number" min="0" step="1"></div><div class="field"><label>防御</label><input id="cardDefense" type="number" min="1" step="1"></div><div class="field"><label>费用</label><input id="cardCost" type="number" min="0" step="1"></div><div class="field"><label>卡池数量</label><input id="cardPoolCopies" type="number" min="0" step="1"></div><div class="field"><label>阵营/种族</label><input id="cardFaction"></div><div class="field"><label>元素</label><input id="cardElement"></div><div class="field"><label>法术类别</label><input id="cardCategory"></div><div class="field"><label>法术目标</label><select id="cardTarget"></select></div><div class="field"><label>头像 ID</label><input id="cardPortraitId"></div><div class="field"><label>图标 ID</label><input id="cardIconId"></div><div class="field"><label>原始境界</label><input id="cardSourceRealm"></div><div class="field wide"><label>原型/标签</label><input id="cardArchetype"></div><div class="field wide"><label>效果描述</label><textarea id="cardEffect"></textarea></div><div class="field wide"><label>故事</label><textarea id="cardStory"></textarea></div><div class="field wide"><label>规则 JSON</label><textarea id="cardRules" class="rules-textarea"></textarea></div></div></div>
  </section>  <section id="equipment" class="grid hidden"><div class="panel muted"><h3 class="section-title">灵器规则</h3>配置每个境界可能刷新出的灵器、阶级范围、品质和权重；玩家可获得任意境界灵器，但装备仍受灵器自身境界限制。<div class="row"><button onclick="loadEquipment()">刷新</button><button class="primary" onclick="saveEquipment()">保存</button></div><details><summary>战力倍率等高级配置</summary><textarea id="equipmentJson" class="mini-textarea"></textarea></details></div><div class="panel"><div id="equipmentPools" class="config-list"></div></div></section>
  <section id="mystic" class="grid hidden"><div class="panel muted"><h3 class="section-title">秘境掉落</h3>勾选开启的秘境，并为每个秘境配置类别权重和固定掉落。<div class="row"><button onclick="loadMystic()">刷新</button><button class="primary" onclick="saveMystic()">保存</button></div><h3 class="section-title">普通秘境</h3><div id="mysticTypeChecks" class="check-grid"></div><h3 class="section-title">高危险地</h3><div id="mysticHighRiskChecks" class="check-grid"></div><details><summary>原始秘境配置</summary><textarea id="mysticJson" class="mini-textarea"></textarea></details></div><div class="panel"><div id="mysticConfigList" class="config-list"></div></div></section>
  <section id="config" class="grid hidden"><div class="panel muted"><h3 class="section-title">原始配置</h3>完整 admin_config.json，保存后立刻应用。<div class="row"><button onclick="loadConfig()">刷新</button><button class="primary" onclick="saveConfig()">保存</button></div></div><div class="panel"><textarea id="configJson" class="config-textarea"></textarea></div></section>
</div>
<script>
let selectedUser='',selectedRecord=null,players=[],items=[],selectedItem=null,itemMeta={},beastCards=[],selectedBeastCard=null,beastMeta={};
const API_BASE=window.location.pathname.replace(/[/]$/,'');
const playerFieldOrder=['user_id','root','realm_index','realm_exp','total_exp','sign_count','spirit_stones','fishing_chances','pending_exp','spirit_liquid','cultivation_route','faction_identity','foundation_type','realm_marks','special_abilities','rewards','equipped_artifacts','equipped_method','equipped_array','equipped_talisman','life_artifact','immortal_seeds','equipped_immortal_seed','mystic_realm'];
function bindDomIdGlobals(){document.querySelectorAll('[id]').forEach(el=>{let id=el.id;if(!/^[A-Za-z_$][A-Za-z0-9_$]*$/.test(id)||Object.prototype.hasOwnProperty.call(window,id))return;Object.defineProperty(window,id,{configurable:true,get(){return document.getElementById(id)}})})}
bindDomIdGlobals();
function status(t,c=''){let e=document.getElementById('status');e.textContent=t;e.className='status '+c}
function tok(){return document.getElementById('token').value||localStorage.getItem('xiuxianAdminToken')||''}
function api(p,o={}){let h=Object.assign({'Content-Type':'application/json'},o.headers||{});if(tok())h['X-Xiuxian-Token']=tok();return fetch(API_BASE+p,Object.assign({},o,{headers:h})).then(async r=>{let d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||r.statusText);return d})}
function saveToken(){localStorage.setItem('xiuxianAdminToken',document.getElementById('token').value.trim());status('Token 已保存。','ok');if(selectedItem)selectItem(selectedItem.name)}
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function pretty(x){return JSON.stringify(x,null,2)}
function showTab(id,tab){document.querySelectorAll('section').forEach(x=>x.classList.toggle('hidden',x.id!==id));document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));if(tab)tab.classList.add('active');if(id==='players')loadPlayers();if(id==='items')loadItems();if(id==='beastCards')loadBeastCards();if(id==='equipment')loadEquipment();if(id==='mystic')loadMystic();if(id==='config')loadConfig()}
function iconUrl(icon){if(!icon)return '';let path=String(icon).split('/').map(encodeURIComponent).join('/');let suffix=tok()?'?token='+encodeURIComponent(tok()):'';return API_BASE+'/assets/item-icons/'+path+suffix}
function iconHtml(icon,name){let url=iconUrl(icon);return url?`<img src="${url}" alt="${esc(name)}" loading="lazy">`:`<span class="placeholder">无图</span>`}
async function loadPlayers(){try{let q=document.getElementById('playerSearch').value.trim();let d=await api('/api/players'+(q?'?q='+encodeURIComponent(q):''));players=d.players||[];document.getElementById('playersBody').innerHTML=players.map(p=>`<tr onclick="selectPlayer('${esc(p.user_id)}')"><td><b>${esc(p.nickname||p.user_id)}</b><br><span class="muted">${esc(p.user_id)}</span></td><td>${esc(p.realm)}</td><td>${esc(p.battle_power)}</td><td>${esc(p.spirit_stones)}</td></tr>`).join('');status('已载入 '+players.length+' 个玩家。','ok')}catch(e){status(e.message,'err')}}
async function selectPlayer(id){try{selectedUser=id;let d=await api('/api/players/'+encodeURIComponent(id));selectedRecord=d.record||{};renderPlayerForm();status('玩家档案已载入。','ok')}catch(e){status(e.message,'err')}}
function renderPlayerForm(){document.getElementById('playerTitle').textContent='玩家 '+selectedUser;let keys=[...playerFieldOrder.filter(k=>Object.prototype.hasOwnProperty.call(selectedRecord,k)),...Object.keys(selectedRecord).filter(k=>!playerFieldOrder.includes(k))];document.getElementById('playerFields').innerHTML=keys.map(k=>fieldHtml(k,selectedRecord[k])).join('')}
function fieldHtml(k,v){let complex=v&&typeof v==='object';let label=esc(k);if(complex){return `<div class="field wide"><label>${label}</label><textarea data-key="${label}" data-type="json">${esc(pretty(v))}</textarea></div>`}return `<div class="field"><label>${label}</label><input data-key="${label}" data-type="scalar" value="${esc(v??'')}"></div>`}
function collectPlayerForm(){let next=Object.assign({},selectedRecord||{});document.querySelectorAll('#playerFields [data-key]').forEach(el=>{let k=el.dataset.key;let raw=el.value;if(el.dataset.type==='json'){next[k]=raw.trim()?JSON.parse(raw):null}else if(raw===''){next[k]=null}else if(/^-?\\d+$/.test(raw)){next[k]=Number(raw)}else if(raw==='true'||raw==='false'){next[k]=raw==='true'}else{next[k]=raw}});return next}
function resetPlayerForm(){if(selectedRecord)renderPlayerForm()}
async function savePlayer(){try{if(!selectedUser)throw new Error('请先选择玩家');let data=collectPlayerForm();await api('/api/players/'+encodeURIComponent(selectedUser),{method:'PUT',body:pretty(data)});status('玩家档案已保存。','ok');await selectPlayer(selectedUser);loadPlayers()}catch(e){status(e.message,'err')}}
async function backupUsers(){try{let d=await api('/api/backup',{method:'POST',body:'{}'});status('已备份到 '+d.path,'ok')}catch(e){status(e.message,'err')}}
async function loadItems(){try{let keep=selectedItem&&selectedItem.name;let d=await api('/api/items');items=d.items||[];itemMeta=d.meta||{};fillItemFilters();renderItems();if(keep&&items.some(x=>x.name===keep))selectItem(keep);else if(items.length)selectItem(items[0].name);status('已载入 '+items.length+' 个物品。','ok')}catch(e){status(e.message,'err')}}
function fillItemFilters(){let cats=[...new Set(items.map(x=>x.category).filter(Boolean))].sort();let tiers=[...new Set(items.flatMap(x=>x.tiers||[]).filter(Boolean))];itemCategory.innerHTML='<option value="">全部类别</option>'+cats.map(x=>`<option>${esc(x)}</option>`).join('');itemTier.innerHTML='<option value="">全部阶级</option>'+tiers.map(x=>`<option>${esc(x)}</option>`).join('')}
function filteredItems(){let q=(itemSearch.value||'').toLowerCase();let c=itemCategory.value;let t=itemTier.value;return items.filter(x=>(!q||pretty(x).toLowerCase().includes(q))&&(!c||x.category===c)&&(!t||(x.tiers||[]).includes(t))).slice(0,600)}
function renderItems(){let rows=filteredItems();itemGrid.innerHTML=rows.map(x=>`<article class="item-card ${selectedItem&&selectedItem.name===x.name?'active':''}" onclick="selectItem('${esc(x.name)}')"><div class="item-icon">${iconHtml(x.icon,x.name)}</div><div><div class="item-name">${esc(x.name)}</div><div class="item-meta">${esc(x.category||'未分类')}</div><div>${(x.tiers||[]).slice(0,2).map(v=>`<span class="chip">${esc(v)}</span>`).join('')}</div></div></article>`).join('')}
function asList(v){return Array.isArray(v)?v.map(x=>String(x)).filter(Boolean):String(v||'').split(/[、,，\\n]/).map(x=>x.trim()).filter(Boolean)}
function optionPool(values,selected){let pool=(values||[]).map(x=>String(x)).filter(Boolean);asList(selected).forEach(v=>{if(v&&!pool.includes(v))pool.unshift(v)});return pool}
function setField(id,v){document.getElementById(id).value=Array.isArray(v)?v.join('、'):(v??'')}
function setSelectField(id,values,value,emptyLabel){let el=document.getElementById(id);let current=String(value||'');let html=emptyLabel===null?'':'<option value="">'+esc(emptyLabel||'未指定')+'</option>';html+=optionPool(values,current).map(v=>'<option value="'+esc(v)+'" '+(v===current?'selected':'')+'>'+esc(v)+'</option>').join('');el.innerHTML=html;el.value=current}
function setMultiField(id,values,current){let el=document.getElementById(id);let chosen=new Set(asList(current));el.innerHTML=optionPool(values,current).map(v=>'<option value="'+esc(v)+'" '+(chosen.has(v)?'selected':'')+'>'+esc(v)+'</option>').join('')}
function selectedValues(id){return Array.from(document.getElementById(id).selectedOptions).map(o=>o.value).filter(Boolean)}
function selectItem(name){selectedItem=items.find(x=>x.name===name)||null;renderItems();let x=selectedItem;if(!x)return;detailIcon.innerHTML=iconHtml(x.icon,x.name);detailName.textContent=x.name;detailChips.innerHTML=[x.category,...(x.tiers||[]).slice(0,3),...(x.grades||[]).slice(0,2),x.customized?'已修改':''].filter(Boolean).map(v=>`<span class="chip">${esc(v)}</span>`).join('');setField('itemName',x.name);setSelectField('itemCategoryField',itemMeta.categories||[],x.category,'未分类');setMultiField('itemTiers',itemMeta.tiers||[],x.tiers||[]);setMultiField('itemGrades',itemMeta.grades||[],x.grades||[]);setSelectField('itemRealm',itemMeta.realms||[],x.required_realm||x.realm||'','未指定');setSelectField('itemAttr',itemMeta.attributes||[],x.required_attribute||'','无属性要求');setField('itemUsage',x.usage||'');setField('itemSource',x.source||'');setField('itemStory',x.story||'');setField('itemNote',x.parameter_note||'')}
function itemFormPayload(){if(!selectedItem)throw new Error('请先选择物品');return {category:itemCategoryField.value,tiers:selectedValues('itemTiers'),grades:selectedValues('itemGrades'),required_realm:itemRealm.value,required_attribute:itemAttr.value,usage:itemUsage.value,source:itemSource.value,story:itemStory.value}}
function resetItemForm(){if(selectedItem)selectItem(selectedItem.name)}
async function saveItem(){try{if(!selectedItem)throw new Error('请先选择物品');let name=selectedItem.name;let payload=itemFormPayload();let d=await api('/api/config');let cfg=d.config||{};cfg.item_overrides=cfg.item_overrides&&typeof cfg.item_overrides==='object'?cfg.item_overrides:{};cfg.item_overrides[name]=payload;await api('/api/config',{method:'PUT',body:pretty(cfg)});await loadItems();selectItem(name);status('物品图鉴已保存。','ok')}catch(e){status(e.message,'err')}}
async function clearItemOverride(){try{if(!selectedItem)throw new Error('请先选择物品');let name=selectedItem.name;let d=await api('/api/config');let cfg=d.config||{};if(cfg.item_overrides&&typeof cfg.item_overrides==='object')delete cfg.item_overrides[name];await api('/api/config',{method:'PUT',body:pretty(cfg)});await loadItems();selectItem(name);status('物品图鉴已恢复默认。','ok')}catch(e){status(e.message,'err')}}
async function loadEquipment(){try{let d=await api('/api/equipment-rules');equipmentJson.value=pretty(d.rules||{});status('灵器规则已载入。','ok')}catch(e){status(e.message,'err')}}
async function saveEquipment(){try{let r=JSON.parse(equipmentJson.value);let d=await api('/api/config');d.config.equipment_rules=r;await api('/api/config',{method:'PUT',body:pretty(d.config)});status('灵器规则已保存。','ok')}catch(e){status(e.message,'err')}}
async function loadMystic(){try{let d=await api('/api/mystic');mysticJson.value=pretty(d.mystic||{});status('秘境配置已载入。','ok')}catch(e){status(e.message,'err')}}
async function saveMystic(){try{let m=JSON.parse(mysticJson.value);let d=await api('/api/config');d.config.mystic={category_weights:m.category_weights||{},drop_overrides:m.drop_overrides||{}};await api('/api/config',{method:'PUT',body:pretty(d.config)});status('秘境配置已保存。','ok')}catch(e){status(e.message,'err')}}
async function loadConfig(){try{let d=await api('/api/config');configJson.value=pretty(d.config||{});status('配置已载入。','ok')}catch(e){status(e.message,'err')}}
async function saveConfig(){try{await api('/api/config',{method:'PUT',body:configJson.value});status('配置已保存。','ok')}catch(e){status(e.message,'err')}}

function cardAssetUrl(card){let suffix=tok()?'?token='+encodeURIComponent(tok()):'';if(card&&card.kind==='spell'&&card.icon){return API_BASE+'/assets/beast-spell-icons/'+encodeURIComponent(card.icon)+suffix}let pid=String((card&&card.portrait_id)||'').trim();if(!pid)return '';return API_BASE+'/assets/character-portraits/'+encodeURIComponent(pid+'.png')+suffix}
function cardPortraitHtml(card){let url=cardAssetUrl(card);return url?'<img src="'+url+'" alt="'+esc(card.name||card.id)+'" loading="lazy">':'<span class="placeholder">无图</span>'}
async function loadBeastCards(){try{let keep=selectedBeastCard&&selectedBeastCard.id;let d=await api('/api/beast-realm/cards');beastCards=d.cards||[];beastMeta=d.meta||{};if(document.getElementById('beastPoolDefault'))beastPoolDefault.value=String(beastMeta.default_pool_copies??10);fillBeastFilters();renderBeastCards();if(keep&&beastCards.some(x=>x.id===keep))selectBeastCard(keep);else if(beastCards.length)selectBeastCard(beastCards[0].id);status('已载入 '+beastCards.length+' 张御兽秘境卡牌。','ok')}catch(e){status(e.message,'err')}}
function fillBeastFilters(){let factions=[...new Set(beastCards.map(x=>x.faction||x.category).filter(Boolean))].sort();cardFactionFilter.innerHTML='<option value="">全部阵营</option>'+factions.map(x=>'<option>'+esc(x)+'</option>').join('');cardTier.innerHTML=(beastMeta.realms||[]).map((name,i)=>'<option value="'+(i+1)+'">'+(i+1)+' · '+esc(name)+'</option>').join('');cardTarget.innerHTML=selectOptions(beastMeta.targets||['ally','team','enemy'],'','未指定')}
function filteredBeastCards(){let q=(cardSearch.value||'').toLowerCase();let k=cardKindFilter.value;let f=cardFactionFilter.value;return beastCards.filter(x=>(!q||pretty(x).toLowerCase().includes(q))&&(!k||x.kind===k)&&(!f||(x.faction===f||x.category===f))).slice(0,900)}
function renderBeastSummary(rows){rows=rows||filteredBeastCards();let followers=beastCards.filter(x=>x.kind==='beast').length;let spells=beastCards.filter(x=>x.kind==='spell').length;let customized=beastCards.filter(x=>x.customized).length;beastSummary.innerHTML='<div class="summary-card"><b>'+rows.length+'</b><span class="muted">当前筛选</span></div><div class="summary-card"><b>'+followers+'</b><span class="muted">随从牌</span></div><div class="summary-card"><b>'+spells+'</b><span class="muted">法术牌</span></div><div class="summary-card"><b>'+customized+'</b><span class="muted">已覆写</span></div>'}
function renderBeastCards(){let rows=filteredBeastCards();renderBeastSummary(rows);beastCardGrid.innerHTML=rows.map(x=>'<article class="beast-card '+(selectedBeastCard&&selectedBeastCard.id===x.id?'active':'')+'" onclick="selectBeastCard(\\''+esc(x.id)+'\\')"><div class="card-thumb">'+cardPortraitHtml(x)+'</div><div><div class="item-name">'+esc(x.name)+'</div><div class="item-meta">'+esc(x.kind==='spell'?'法术牌':'随从牌')+' · '+esc(x.realm||'')+' · '+esc((x.cost??0)+'灵石')+'</div><div><span class="chip">'+esc(x.faction||x.category||'无阵营')+'</span>'+(x.customized?'<span class="chip">已修改</span>':'')+'</div></div></article>').join('')}
function selectBeastCard(id){selectedBeastCard=beastCards.find(x=>x.id===id)||null;renderBeastCards();let x=selectedBeastCard;if(!x)return;cardPreview.innerHTML=cardPortraitHtml(x);cardTitle.textContent=x.name||x.id;cardChips.innerHTML=[x.id,x.kind==='spell'?'法术牌':'随从牌',x.realm,(x.cost??0)+'灵石',x.faction||x.category,x.customized?'已修改':''].filter(Boolean).map(v=>'<span class="chip">'+esc(v)+'</span>').join('');setField('cardId',x.id);setField('cardKind',x.kind);setField('cardName',x.name||'');cardTier.value=String(x.tier||1);setField('cardRealm',x.realm||'');setField('cardAttack',x.attack??0);setField('cardDefense',x.defense??1);setField('cardCost',x.cost??(x.kind==='spell'?Math.max(2,Number(x.tier||1)+1):3));setField('cardPoolCopies',x.pool_copies??(beastMeta.default_pool_copies??10));setField('cardFaction',x.faction||'');setField('cardElement',x.element||'');setField('cardCategory',x.category||'');setSelectField('cardTarget',beastMeta.targets||['ally','team','enemy'],x.target||'','未指定');setField('cardPortraitId',x.portrait_id||'');setField('cardIconId',x.icon_id||'');setField('cardSourceRealm',x.source_realm||'');setField('cardArchetype',x.archetype||'');setField('cardEffect',x.effect||'');setField('cardStory',x.story||'');setField('cardRules',pretty(x.rules||{}))}
function beastCardPayload(){if(!selectedBeastCard)throw new Error('请先选择卡牌');let rulesText=(cardRules.value||'').trim();let rules=rulesText?JSON.parse(rulesText):(selectedBeastCard.kind==='spell'?[]:{});return {portrait_id:cardPortraitId.value,icon_id:cardIconId.value,name:cardName.value,tier:numberValue(cardTier.value,1),realm:cardRealm.value,attack:numberValue(cardAttack.value,0),defense:numberValue(cardDefense.value,1),cost:numberValue(cardCost.value,3),pool_copies:numberValue(cardPoolCopies.value,beastMeta.default_pool_copies||10),faction:cardFaction.value,element:cardElement.value,category:cardCategory.value,target:cardTarget.value,effect:cardEffect.value,story:cardStory.value,rules:rules,source_realm:cardSourceRealm.value,archetype:cardArchetype.value}}
function resetBeastCardForm(){if(selectedBeastCard)selectBeastCard(selectedBeastCard.id)}
async function saveBeastRealmGlobal(){try{let d=await api('/api/config');let cfg=d.config||{};cfg.beast_realm=cfg.beast_realm&&typeof cfg.beast_realm==='object'?cfg.beast_realm:{};cfg.beast_realm.card_pool_copies=numberValue(beastPoolDefault.value,beastMeta.default_pool_copies||10);cfg.beast_realm.card_overrides=cfg.beast_realm.card_overrides&&typeof cfg.beast_realm.card_overrides==='object'?cfg.beast_realm.card_overrides:{};await api('/api/config',{method:'PUT',body:pretty(cfg)});await loadBeastCards();status('御兽秘境全局卡池配置已保存。','ok')}catch(e){status(e.message,'err')}}
async function saveBeastCard(){try{if(!selectedBeastCard)throw new Error('请先选择卡牌');let id=selectedBeastCard.id;let payload=beastCardPayload();let d=await api('/api/config');let cfg=d.config||{};cfg.beast_realm=cfg.beast_realm&&typeof cfg.beast_realm==='object'?cfg.beast_realm:{};cfg.beast_realm.card_overrides=cfg.beast_realm.card_overrides&&typeof cfg.beast_realm.card_overrides==='object'?cfg.beast_realm.card_overrides:{};cfg.beast_realm.card_overrides[id]=payload;await api('/api/config',{method:'PUT',body:pretty(cfg)});await loadBeastCards();selectBeastCard(id);status('御兽秘境卡牌已保存。','ok')}catch(e){status(e.message,'err')}}
async function clearBeastCardOverride(){try{if(!selectedBeastCard)throw new Error('请先选择卡牌');let id=selectedBeastCard.id;let d=await api('/api/config');let cfg=d.config||{};if(cfg.beast_realm&&cfg.beast_realm.card_overrides)delete cfg.beast_realm.card_overrides[id];await api('/api/config',{method:'PUT',body:pretty(cfg)});await loadBeastCards();selectBeastCard(id);status('卡牌已恢复默认。','ok')}catch(e){status(e.message,'err')}}const PLAYER_FIELD_LABELS={
  user_id:'用户 ID',root:'主灵根',acquired_roots:'已获得灵根',sign_count:'签到次数',total_exp:'累计修为',realm_index:'境界序号',realm_exp:'当前境界修为',last_sign_date:'上次签到日期',last_encounter_date:'上次奇遇日期',fishing_chances:'垂钓次数',pending_fishing:'待同步垂钓次数',pending_exp:'待结算修为',spirit_liquid:'精纯灵液',bottleneck_days:'瓶颈沉淀天数',bottleneck_realm_index:'瓶颈境界序号',last_bottleneck_date:'上次瓶颈日期',rewards:'背包物品',equipped_artifact:'旧版已装备灵器',equipped_artifacts:'已装备灵器槽',equipped_talisman:'已装备符箓',equipped_method:'已修功法',equipped_array:'已布阵盘',equipped_puppet:'已唤醒傀儡',planted_spirit_plant:'已栽灵植',array_proficiency:'阵盘熟练度',array_layers:'阵盘层数',spirit_stones:'灵石',foundation_type:'筑基品相',realm_marks:'境界品相记录',extra_roots:'额外灵根',mystic_realm:'当前秘境',cultivation_lock_until:'禁修截止日期',cultivation_route:'修炼路线',evil_cultivator:'是否邪修',faction_identity:'宗门身份',identity_sign_days:'身份签到天数',daily_tasks:'每日任务',dual_cultivation_date:'双修日期',dual_cultivation_used:'双修次数',last_tianji_mystic_date:'上次天机秘境日期',combat_race:'斗法种族',physique:'体质',special_abilities:'神通',method_layers:'功法层数',method_proficiency:'功法熟练度',life_artifact:'本命灵器',immortal_seeds:'仙源列表',equipped_immortal_seed:'已纳入仙源',immortal_conversion_days:'仙元转化天数',last_immortal_conversion_date:'上次仙元转化日期',last_failed_mystic_realm:'上次失败秘境',mystic_boss_successes:'秘境首领通关记录',mystic_boss_daily_date:'首领日挑战日期',mystic_boss_daily_attempts:'首领日挑战次数',mystic_boss_daily_bonus:'首领日奖励次数',mystic_boss_week_key:'首领周挑战周期',mystic_boss_week_attempts:'首领周挑战次数',mystic_boss_week_claimed:'首领周奖励领取'
};
let equipmentRules={},equipmentMeta={},mysticPayload={};
function fieldLabel(k){let name=PLAYER_FIELD_LABELS[k]||k;return name===k?esc(k):esc(name)+' <small>'+esc(k)+'</small>'}
function fieldHtml(k,v){let complex=v&&typeof v==='object';let key=esc(k);let label=fieldLabel(k);if(complex){return '<div class="field wide"><label>'+label+'</label><textarea data-key="'+key+'" data-type="json">'+esc(pretty(v))+'</textarea></div>'}return '<div class="field"><label>'+label+'</label><input data-key="'+key+'" data-type="scalar" value="'+esc(v??'')+'"></div>'}
function optionLabel(v,labels){let s=String(v);return labels&&Object.prototype.hasOwnProperty.call(labels,s)?String(labels[s]):s}
function selectOptions(values,selected,emptyLabel,labels){let html=emptyLabel===null?'':'<option value="">'+esc(emptyLabel||'不限')+'</option>';(values||[]).forEach(v=>{let s=String(v);let label=optionLabel(s,labels);html+='<option value="'+esc(s)+'" '+(s===String(selected||'')?'selected':'')+'>'+esc(label)+'</option>'});return html}
function numberValue(v,fallback){let n=Number(v);return Number.isFinite(n)?n:fallback}
function artifactNameOptions(realmIndex,selected){let names=(equipmentMeta.artifacts||[]).filter(a=>Number(a.realm_index)===Number(realmIndex)).map(a=>a.name);if(selected&&!names.includes(selected))names.unshift(selected);let html='<option value="">任意名称</option>';names.forEach(n=>{html+='<option value="'+esc(n)+'" '+(n===selected?'selected':'')+'>'+esc(n)+'</option>'});return html}
function blankArtifactRow(realmIndex){let tiers=equipmentMeta.tiers||['凡品','黄阶','玄阶','地阶','天阶','仙阶'];return {tier_min:tiers[0]||'',tier_max:tiers[Math.max(0,tiers.length-2)]||tiers[0]||'',grade:'',attribute:'',name:'',weight:1}}
function equipmentRowHtml(realmIndex,row,index){row=row||blankArtifactRow(realmIndex);return '<tr class="equipment-row" data-realm="'+realmIndex+'"><td><select data-field="tier_min" onchange="updateEquipmentFromDom()">'+selectOptions(equipmentMeta.tiers,row.tier_min,'不限')+'</select></td><td><select data-field="tier_max" onchange="updateEquipmentFromDom()">'+selectOptions(equipmentMeta.tiers,row.tier_max,'不限')+'</select></td><td><select data-field="grade" onchange="updateEquipmentFromDom()">'+selectOptions(equipmentMeta.grades,row.grade,'任意品质')+'</select></td><td><select data-field="attribute" onchange="updateEquipmentFromDom()">'+selectOptions(equipmentMeta.attributes,row.attribute,'任意属性',equipmentMeta.attribute_labels)+'</select></td><td><select data-field="name" onchange="updateEquipmentFromDom()">'+artifactNameOptions(realmIndex,row.name||'')+'</select></td><td><input data-field="weight" type="number" min="0.01" step="0.01" value="'+esc(row.weight??1)+'" onchange="updateEquipmentFromDom()"></td><td><button class="icon-btn" title="删除" onclick="removeEquipmentRow('+realmIndex+','+index+')">-</button></td></tr>'}
function renderEquipmentEditor(){let pools=(equipmentRules.artifact_drop_pools=equipmentRules.artifact_drop_pools||{});let realms=equipmentMeta.realms||[];let box=document.getElementById('equipmentPools');box.innerHTML=realms.map(r=>{let idx=Number(r.index);let rows=Array.isArray(pools[String(idx)])?pools[String(idx)]:[];let body=rows.map((row,i)=>equipmentRowHtml(idx,row,i)).join('')||'<tr><td colspan="7" class="muted">此境界暂无灵器刷新配置</td></tr>';return '<div class="realm-block"><div class="realm-head"><div class="realm-title">'+esc(r.name)+' <span class="muted">#'+idx+'</span></div><button onclick="addEquipmentRow('+idx+')">+ 添加</button></div><table class="rule-table"><thead><tr><th>最低阶</th><th>最高阶</th><th>品质</th><th>属性</th><th>灵器名称</th><th>权重</th><th></th></tr></thead><tbody>'+body+'</tbody></table></div>'}).join('');syncEquipmentJson()}
function updateEquipmentFromDom(){let next={};document.querySelectorAll('#equipmentPools .realm-block').forEach(block=>{block.querySelectorAll('.equipment-row').forEach(row=>{let realm=row.dataset.realm;let item={};row.querySelectorAll('[data-field]').forEach(el=>{let key=el.dataset.field;item[key]=key==='weight'?numberValue(el.value,1):el.value});if(item.tier_min||item.tier_max||item.grade||item.attribute||item.name||item.weight){(next[realm]=next[realm]||[]).push(item)}})});equipmentRules.artifact_drop_pools=next;syncEquipmentJson()}
function syncEquipmentJson(){let el=document.getElementById('equipmentJson');if(el)el.value=pretty(equipmentRules||{})}
function addEquipmentRow(realmIndex){updateEquipmentFromDom();let key=String(realmIndex);(equipmentRules.artifact_drop_pools[key]=equipmentRules.artifact_drop_pools[key]||[]).push(blankArtifactRow(realmIndex));renderEquipmentEditor()}
function removeEquipmentRow(realmIndex,rowIndex){updateEquipmentFromDom();let key=String(realmIndex);let rows=equipmentRules.artifact_drop_pools[key]||[];rows.splice(rowIndex,1);if(rows.length)equipmentRules.artifact_drop_pools[key]=rows;else delete equipmentRules.artifact_drop_pools[key];renderEquipmentEditor()}
async function loadEquipment(){try{let d=await api('/api/equipment-rules');equipmentRules=d.rules||{};equipmentMeta=d.meta||{};renderEquipmentEditor();status('灵器规则已载入。','ok')}catch(e){status(e.message,'err')}}
async function saveEquipment(){try{let raw=JSON.parse(document.getElementById('equipmentJson').value||'{}');updateEquipmentFromDom();raw.artifact_drop_pools=equipmentRules.artifact_drop_pools||{};let d=await api('/api/config');d.config.equipment_rules=raw;await api('/api/config',{method:'PUT',body:pretty(d.config)});equipmentRules=raw;syncEquipmentJson();status('灵器规则已保存。','ok')}catch(e){status(e.message,'err')}}
function allMysticTypes(){let seen=[];['default'].concat(mysticPayload.types||[],mysticPayload.high_risk_types||[]).forEach(t=>{if(t&&!seen.includes(t))seen.push(t)});return seen}
function typeAt(i){return allMysticTypes()[Number(i)]||'default'}
function renderMysticChecks(){let normal=new Set(mysticPayload.enabled_types||[]);let high=new Set(mysticPayload.enabled_high_risk_types||[]);document.getElementById('mysticTypeChecks').innerHTML=(mysticPayload.types||[]).map((t,i)=>'<label class="check-item"><input type="checkbox" '+(normal.has(t)?'checked':'')+' onchange="setMysticEnabled(0,'+i+',this.checked)">'+esc(t)+'</label>').join('');document.getElementById('mysticHighRiskChecks').innerHTML=(mysticPayload.high_risk_types||[]).map((t,i)=>'<label class="check-item"><input type="checkbox" '+(high.has(t)?'checked':'')+' onchange="setMysticEnabled(1,'+i+',this.checked)">'+esc(t)+'</label>').join('')}
function setMysticEnabled(kind,index,checked){let list=kind?(mysticPayload.enabled_high_risk_types=mysticPayload.enabled_high_risk_types||[]):(mysticPayload.enabled_types=mysticPayload.enabled_types||[]);let source=kind?(mysticPayload.high_risk_types||[]):(mysticPayload.types||[]);let name=source[index];if(!name)return;if(checked&&!list.includes(name))list.push(name);if(!checked){let p=list.indexOf(name);if(p>=0)list.splice(p,1)}syncMysticJson()}
function itemNameOptions(category,selected){let pool=(items||[]).filter(x=>!category||x.category===category).slice(0,900).map(x=>x.name);if(selected&&!pool.includes(selected))pool.unshift(selected);let html='<option value="">随机/不指定</option>';pool.forEach(n=>{html+='<option value="'+esc(n)+'" '+(n===selected?'selected':'')+'>'+esc(n)+'</option>'});return html}
function categoryRowHtml(typeIndex,row,rowIndex){row=row||{category:'灵材',weight:1};return '<tr class="mystic-category-row" data-type-index="'+typeIndex+'"><td><select data-field="category" onchange="updateMysticFromDom()">'+selectOptions(mysticPayload.categories,row.category,'类别')+'</select></td><td><input data-field="weight" type="number" min="0.01" step="0.01" value="'+esc(row.weight??1)+'" onchange="updateMysticFromDom()"></td><td><button class="icon-btn" title="删除" onclick="removeMysticCategory('+typeIndex+','+rowIndex+')">-</button></td></tr>'}
function dropRowHtml(typeIndex,row,rowIndex){row=row||{category:'灵材',tier:'',grade:'',name:'',weight:1};return '<tr class="mystic-drop-row" data-type-index="'+typeIndex+'"><td><select data-field="category" onchange="updateMysticFromDom();renderMysticEditor()">'+selectOptions(mysticPayload.categories,row.category,'类别')+'</select></td><td><select data-field="tier" onchange="updateMysticFromDom()">'+selectOptions(mysticPayload.tiers,row.tier,'任意阶')+'</select></td><td><select data-field="grade" onchange="updateMysticFromDom()">'+selectOptions(mysticPayload.grades,row.grade,'任意品质')+'</select></td><td><select data-field="name" onchange="updateMysticFromDom()">'+itemNameOptions(row.category,row.name||'')+'</select></td><td><input data-field="weight" type="number" min="0.01" step="0.01" value="'+esc(row.weight??1)+'" onchange="updateMysticFromDom()"></td><td><button class="icon-btn" title="删除" onclick="removeMysticDrop('+typeIndex+','+rowIndex+')">-</button></td></tr>'}
function renderMysticEditor(){renderMysticChecks();let types=allMysticTypes();let cw=mysticPayload.category_weights=mysticPayload.category_weights||{};let dr=mysticPayload.drop_overrides=mysticPayload.drop_overrides||{};document.getElementById('mysticConfigList').innerHTML=types.map((t,i)=>{let cats=Array.isArray(cw[t])?cw[t]:[];let drops=Array.isArray(dr[t])?dr[t]:[];let catBody=cats.map((row,j)=>categoryRowHtml(i,row,j)).join('')||'<tr><td colspan="3" class="muted">未配置时使用系统默认权重</td></tr>';let dropBody=drops.map((row,j)=>dropRowHtml(i,row,j)).join('')||'<tr><td colspan="6" class="muted">无固定掉落，按类别权重随机</td></tr>';return '<div class="realm-block"><div class="realm-head"><div class="realm-title">'+esc(t==='default'?'默认掉落':t)+'</div></div><div class="row"><b>类别权重</b><button onclick="addMysticCategory('+i+')">+ 类别</button></div><table class="rule-table"><thead><tr><th>类别</th><th>权重</th><th></th></tr></thead><tbody>'+catBody+'</tbody></table><div class="row"><b>固定掉落</b><button onclick="addMysticDrop('+i+')">+ 掉落</button></div><table class="rule-table"><thead><tr><th>类别</th><th>阶级</th><th>品质</th><th>物品</th><th>权重</th><th></th></tr></thead><tbody>'+dropBody+'</tbody></table></div>'}).join('');syncMysticJson()}
function updateMysticFromDom(){let types=allMysticTypes();let cw={},dr={};document.querySelectorAll('.mystic-category-row').forEach(row=>{let t=types[Number(row.dataset.typeIndex)];let item={};row.querySelectorAll('[data-field]').forEach(el=>{let k=el.dataset.field;item[k]=k==='weight'?numberValue(el.value,1):el.value});if(t&&item.category)(cw[t]=cw[t]||[]).push(item)});document.querySelectorAll('.mystic-drop-row').forEach(row=>{let t=types[Number(row.dataset.typeIndex)];let item={};row.querySelectorAll('[data-field]').forEach(el=>{let k=el.dataset.field;item[k]=k==='weight'?numberValue(el.value,1):el.value});if(t&&(item.category||item.name))(dr[t]=dr[t]||[]).push(item)});mysticPayload.category_weights=cw;mysticPayload.drop_overrides=dr;syncMysticJson()}
function syncMysticJson(){let data={enabled_types:mysticPayload.enabled_types||[],enabled_high_risk_types:mysticPayload.enabled_high_risk_types||[],category_weights:mysticPayload.category_weights||{},drop_overrides:mysticPayload.drop_overrides||{}};let el=document.getElementById('mysticJson');if(el)el.value=pretty(data)}
function addMysticCategory(typeIndex){updateMysticFromDom();let t=typeAt(typeIndex);(mysticPayload.category_weights[t]=mysticPayload.category_weights[t]||[]).push({category:'灵材',weight:1});renderMysticEditor()}
function removeMysticCategory(typeIndex,rowIndex){updateMysticFromDom();let t=typeAt(typeIndex);let rows=mysticPayload.category_weights[t]||[];rows.splice(rowIndex,1);if(rows.length)mysticPayload.category_weights[t]=rows;else delete mysticPayload.category_weights[t];renderMysticEditor()}
function addMysticDrop(typeIndex){updateMysticFromDom();let t=typeAt(typeIndex);(mysticPayload.drop_overrides[t]=mysticPayload.drop_overrides[t]||[]).push({category:'灵材',tier:'',grade:'',name:'',weight:1});renderMysticEditor()}
function removeMysticDrop(typeIndex,rowIndex){updateMysticFromDom();let t=typeAt(typeIndex);let rows=mysticPayload.drop_overrides[t]||[];rows.splice(rowIndex,1);if(rows.length)mysticPayload.drop_overrides[t]=rows;else delete mysticPayload.drop_overrides[t];renderMysticEditor()}
async function ensureItemOptions(){if(items.length)return;let d=await api('/api/items');items=d.items||[];itemMeta=d.meta||itemMeta||{}}
async function loadMystic(){try{let d=await api('/api/mystic');mysticPayload=d.mystic||{};await ensureItemOptions();renderMysticEditor();status('秘境配置已载入。','ok')}catch(e){status(e.message,'err')}}
async function saveMystic(){try{updateMysticFromDom();let raw=JSON.parse(document.getElementById('mysticJson').value||'{}');let d=await api('/api/config');d.config.mystic={enabled_types:raw.enabled_types||[],enabled_high_risk_types:raw.enabled_high_risk_types||[],category_weights:raw.category_weights||{},drop_overrides:raw.drop_overrides||{}};await api('/api/config',{method:'PUT',body:pretty(d.config)});status('秘境配置已保存。','ok')}catch(e){status(e.message,'err')}}
const urlToken=new URLSearchParams(window.location.search).get('token')||'';if(urlToken){localStorage.setItem('xiuxianAdminToken',urlToken)}document.getElementById('token').value=urlToken||localStorage.getItem('xiuxianAdminToken')||'';loadPlayers();
</script>
</body>
</html>"""


def install_admin_routes(driver: Any, manager: AdminManager, base_path: str = "/xiuxian-admin") -> bool:
    app = getattr(driver, "server_app", None)
    if app is None:
        return False
    base_path = "/" + str(base_path or "xiuxian-admin").strip("/")

    try:
        from starlette.requests import Request
        from starlette.responses import Response
    except ModuleNotFoundError:
        return False

    async def page(request: Request) -> Any:
        from starlette.responses import FileResponse, HTMLResponse

        asset_path = str(request.path_params.get("asset_path", ""))
        if not authorized(manager, request):
            return HTMLResponse(
                "<html><body><form><h3>修仙签到后台</h3>"
                "<label>管理 Token <input name='token'></label><button>进入</button></form></body></html>"
            )
        asset = admin_web_asset_path(asset_path)
        if asset is None:
            return HTMLResponse(ADMIN_WEB_MISSING_HTML, status_code=503)
        return FileResponse(asset)

    async def unknown_api(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        return json_response({"ok": False, "error": "not found"}, 404)

    async def admin_web_static_asset(request: Request) -> Any:
        from starlette.responses import FileResponse, Response

        asset = admin_web_static_asset_path("assets/" + str(request.path_params["asset_path"]))
        if asset is None:
            return Response(status_code=404)
        return FileResponse(asset)

    async def dashboard(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        return json_response(manager.dashboard_payload())

    async def get_config(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        return json_response({"ok": True, "config": manager.load_config()})

    async def put_config(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        data = await request.json()
        if not isinstance(data, dict):
            return json_response({"ok": False, "error": "config must be an object"}, 400)
        manager.save_config(data)
        manager.apply_config()
        return json_response({"ok": True, "config": manager.load_config()})

    async def list_players(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        users = manager.store._read_json(manager.store.user_file_path)
        groups = manager.store._read_json(manager.store.group_file_path)
        nicknames: dict[str, str] = {}
        for group in groups.values():
            if isinstance(group, dict):
                for user_id, info in dict(group.get("users") or {}).items():
                    if isinstance(info, dict) and info.get("nickname"):
                        nicknames[str(user_id)] = str(info.get("nickname"))
        query = str(request.query_params.get("q") or "").lower()
        players = []
        for user_id, raw in users.items():
            if not isinstance(raw, dict):
                continue
            nickname = nicknames.get(str(user_id), "")
            if query and query not in str(user_id).lower() and query not in nickname.lower():
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
        return json_response({"ok": True, "players": players})

    async def get_player(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        user_id = str(request.path_params["user_id"])
        raw = manager.store._read_json(manager.store.user_file_path).get(user_id)
        if not isinstance(raw, dict):
            return json_response({"ok": False, "error": "player not found"}, 404)
        return json_response({"ok": True, "record": raw})

    async def put_player(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        user_id = str(request.path_params["user_id"])
        data = await request.json()
        if not isinstance(data, dict):
            return json_response({"ok": False, "error": "record must be an object"}, 400)
        data["user_id"] = user_id
        record = domain.UserRecord.from_dict(data)
        users = manager.store._read_json(manager.store.user_file_path)
        users[user_id] = record.to_dict()
        manager.store._write_json(manager.store.user_file_path, users)
        return json_response({"ok": True, "record": users[user_id]})

    async def backup(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        return json_response(manager.backup_users())

    async def items(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        return json_response(manager.item_payload())

    async def beast_cards(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        return json_response(manager.beast_card_payload())

    async def item_icon(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        icon_path = safe_item_icon_path(str(request.path_params["icon_path"]))
        if icon_path is None:
            return json_response({"ok": False, "error": "icon not found"}, 404)
        return Response(icon_path.read_bytes(), media_type="image/png")

    async def character_portrait(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        portrait_path = safe_character_portrait_path(str(request.path_params["portrait_name"]))
        if portrait_path is None:
            return json_response({"ok": False, "error": "portrait not found"}, 404)
        return Response(portrait_path.read_bytes(), media_type="image/png")


    async def beast_spell_icon(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        icon_path = safe_beast_spell_icon_path(str(request.path_params["icon_name"]))
        if icon_path is None:
            return json_response({"ok": False, "error": "spell icon not found"}, 404)
        return Response(icon_path.read_bytes(), media_type="image/png")

    async def mystic(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        return json_response({"ok": True, "mystic": manager.mystic_payload()})

    async def equipment_rules(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        return json_response({"ok": True, "rules": manager.equipment_rules(), "meta": manager.equipment_meta()})

    for path, endpoint, methods in (
        (base_path, page, ["GET"]),
        (base_path + "/api/dashboard", dashboard, ["GET"]),
        (base_path + "/api/config", get_config, ["GET"]),
        (base_path + "/api/config", put_config, ["PUT"]),
        (base_path + "/api/players", list_players, ["GET"]),
        (base_path + "/api/players/{user_id}", get_player, ["GET"]),
        (base_path + "/api/players/{user_id}", put_player, ["PUT"]),
        (base_path + "/api/backup", backup, ["POST"]),
        (base_path + "/api/items", items, ["GET"]),
        (base_path + "/api/beast-realm/cards", beast_cards, ["GET"]),
        (base_path + "/assets/item-icons/{icon_path:path}", item_icon, ["GET"]),
        (base_path + "/assets/character-portraits/{portrait_name}", character_portrait, ["GET"]),
        (base_path + "/assets/beast-spell-icons/{icon_name}", beast_spell_icon, ["GET"]),
        (base_path + "/assets/{asset_path:path}", admin_web_static_asset, ["GET"]),
        (base_path + "/api/mystic", mystic, ["GET"]),
        (base_path + "/api/equipment-rules", equipment_rules, ["GET"]),
        (base_path + "/api/{api_path:path}", unknown_api, ["GET", "POST", "PUT"]),
        (base_path + "/{asset_path:path}", page, ["GET"]),
    ):
        app.add_route(path, endpoint, methods=methods)
    manager.apply_config()
    return True


class AdminServerHandle:
    def __init__(self, httpd: ThreadingHTTPServer, thread: threading.Thread, host: str, port: int, base_path: str) -> None:
        self.httpd = httpd
        self.thread = thread
        self.host = host
        self.port = port
        self.base_path = base_path

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)


def _normalize_base_path(base_path: str) -> str:
    return "/" + str(base_path or "xiuxian-admin").strip("/")


def start_admin_server(
    manager: AdminManager,
    host: str = "0.0.0.0",
    port: int = 8081,
    base_path: str = "/xiuxian-admin",
) -> AdminServerHandle:
    bind_host = str(host or "0.0.0.0")
    bind_port = 8081 if port is None or str(port) == "" else int(port)
    normalized_base_path = _normalize_base_path(base_path)

    class ReusableThreadingHTTPServer(ThreadingHTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    class AdminRequestHandler(BaseHTTPRequestHandler):
        server_version = "XiuxianAdmin/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self._send_common_headers("application/json")
            self.end_headers()

        def do_GET(self) -> None:
            self._handle_request("GET")

        def do_POST(self) -> None:
            self._handle_request("POST")

        def do_PUT(self) -> None:
            self._handle_request("PUT")

        def _handle_request(self, method: str) -> None:
            try:
                parsed = urlparse(self.path)
                request_path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
                query = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
                if request_path == "/":
                    self._send_redirect(normalized_base_path)
                    return
                if request_path == normalized_base_path:
                    self._send_page(query)
                    return
                if not request_path.startswith(normalized_base_path + "/"):
                    self._send_json({"ok": False, "error": "not found"}, 404)
                    return
                api_path = request_path[len(normalized_base_path) :]
                if method == "GET" and api_path.startswith("/assets/") and not self._is_runtime_asset_path(api_path):
                    self._send_admin_web_static_asset(api_path)
                    return
                if not self._authorized(query):
                    self._send_json({"ok": False, "error": "unauthorized"}, 401)
                    return
                if api_path.startswith("/assets/item-icons/") and method == "GET":
                    self._send_item_icon(api_path[len("/assets/item-icons/") :])
                    return
                if api_path.startswith("/assets/character-portraits/") and method == "GET":
                    self._send_character_portrait(api_path[len("/assets/character-portraits/") :])
                    return
                if api_path.startswith("/assets/beast-spell-icons/") and method == "GET":
                    self._send_beast_spell_icon(api_path[len("/assets/beast-spell-icons/") :])
                    return
                if method == "GET" and not api_path.startswith("/api/"):
                    self._send_admin_web_asset(api_path)
                    return
                self._handle_api(method, api_path, query)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc) or exc.__class__.__name__}, 500)

        def _handle_api(self, method: str, api_path: str, query: dict[str, str]) -> None:
            if api_path == "/api/dashboard" and method == "GET":
                self._send_json(manager.dashboard_payload())
                return
            if api_path == "/api/config" and method == "GET":
                self._send_json({"ok": True, "config": manager.load_config()})
                return
            if api_path == "/api/config" and method == "PUT":
                data = self._read_json_body()
                if not isinstance(data, dict):
                    self._send_json({"ok": False, "error": "config must be an object"}, 400)
                    return
                manager.save_config(data)
                manager.apply_config()
                self._send_json({"ok": True, "config": manager.load_config()})
                return
            if api_path == "/api/players" and method == "GET":
                self._send_json({"ok": True, "players": manager.list_players(query.get("q", ""))})
                return
            if api_path.startswith("/api/players/"):
                user_id = unquote(api_path[len("/api/players/") :])
                if method == "GET":
                    raw = manager.get_player_record(user_id)
                    if raw is None:
                        self._send_json({"ok": False, "error": "player not found"}, 404)
                        return
                    self._send_json({"ok": True, "record": raw})
                    return
                if method == "PUT":
                    data = self._read_json_body()
                    if not isinstance(data, dict):
                        self._send_json({"ok": False, "error": "record must be an object"}, 400)
                        return
                    self._send_json({"ok": True, "record": manager.save_player_record(user_id, data)})
                    return
            if api_path == "/api/backup" and method == "POST":
                self._send_json(manager.backup_users())
                return
            if api_path == "/api/items" and method == "GET":
                self._send_json(manager.item_payload())
                return
            if api_path == "/api/beast-realm/cards" and method == "GET":
                self._send_json(manager.beast_card_payload())
                return
            if api_path == "/api/mystic" and method == "GET":
                self._send_json({"ok": True, "mystic": manager.mystic_payload()})
                return
            if api_path == "/api/equipment-rules" and method == "GET":
                self._send_json({"ok": True, "rules": manager.equipment_rules(), "meta": manager.equipment_meta()})
                return
            self._send_json({"ok": False, "error": "not found"}, 404)

        def _authorized(self, query: dict[str, str]) -> bool:
            token = str(self.headers.get("X-Xiuxian-Token") or query.get("token") or "").strip()
            return not manager.token or token == manager.token

        def _is_runtime_asset_path(self, api_path: str) -> bool:
            return api_path.startswith(
                ("/assets/item-icons/", "/assets/character-portraits/", "/assets/beast-spell-icons/")
            )

        def _send_page(self, query: dict[str, str]) -> None:
            if manager.token and not self._authorized(query):
                self._send_html(
                    "<html><body><form><h3>修仙签到后台</h3>"
                    "<label>管理 Token <input name='token'></label><button>进入</button></form></body></html>"
                )
                return
            if not ADMIN_WEB_INDEX.exists():
                self._send_html(ADMIN_WEB_MISSING_HTML, 503)
                return
            body = ADMIN_WEB_INDEX.read_bytes()
            self.send_response(200)
            self._send_common_headers("text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self) -> Any:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)

        def _send_item_icon(self, rel_path: str) -> None:
            icon_path = safe_item_icon_path(unquote(rel_path))
            if icon_path is None:
                self._send_json({"ok": False, "error": "icon not found"}, 404)
                return
            try:
                body = icon_path.read_bytes()
            except OSError:
                self._send_json({"ok": False, "error": "icon not readable"}, 404)
                return
            self.send_response(200)
            self._send_common_headers("image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_character_portrait(self, file_name: str) -> None:
            portrait_path = safe_character_portrait_path(unquote(file_name))
            if portrait_path is None:
                self._send_json({"ok": False, "error": "portrait not found"}, 404)
                return
            try:
                body = portrait_path.read_bytes()
            except OSError:
                self._send_json({"ok": False, "error": "portrait not readable"}, 404)
                return
            self.send_response(200)
            self._send_common_headers("image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


        def _send_beast_spell_icon(self, file_name: str) -> None:
            icon_path = safe_beast_spell_icon_path(unquote(file_name))
            if icon_path is None:
                self._send_json({"ok": False, "error": "spell icon not found"}, 404)
                return
            try:
                body = icon_path.read_bytes()
            except OSError:
                self._send_json({"ok": False, "error": "spell icon not readable"}, 404)
                return
            self.send_response(200)
            self._send_common_headers("image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_admin_web_asset(self, api_path: str) -> None:
            asset = admin_web_asset_path(unquote(api_path))
            if asset is None:
                self._send_html(ADMIN_WEB_MISSING_HTML, 503)
                return
            self._send_file(asset)

        def _send_admin_web_static_asset(self, api_path: str) -> None:
            asset = admin_web_static_asset_path(unquote(api_path))
            if asset is None:
                self._send_json({"ok": False, "error": "asset not found"}, 404)
                return
            self._send_file(asset)

        def _send_file(self, path: Path) -> None:
            try:
                body = path.read_bytes()
            except OSError:
                self._send_json({"ok": False, "error": "asset not readable"}, 404)
                return
            self.send_response(200)
            self._send_common_headers(guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_common_headers(self, content_type: str) -> None:
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Xiuxian-Token")
            self.send_header("Cache-Control", "no-store")

        def _send_json(self, data: Any, status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._send_common_headers("application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str, status: int = 200) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self._send_common_headers("text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_redirect(self, location: str) -> None:
            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

    httpd = ReusableThreadingHTTPServer((bind_host, bind_port), AdminRequestHandler)
    actual_port = int(httpd.server_address[1])
    manager.apply_config()
    thread = threading.Thread(target=httpd.serve_forever, name="xiuxian-admin-http", daemon=True)
    thread.start()
    return AdminServerHandle(httpd, thread, bind_host, actual_port, normalized_base_path)
