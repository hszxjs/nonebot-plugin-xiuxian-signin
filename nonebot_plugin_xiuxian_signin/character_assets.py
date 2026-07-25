from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

ASSET_ROOT = Path(__file__).parent / "assets" / "character_portraits"
PORTRAIT_DIR = ASSET_ROOT / "portraits"
MANIFEST_PATH = ASSET_ROOT / "manifest.json"


@lru_cache(maxsize=1)
def character_portrait_manifest() -> dict[str, Any]:
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"characters": []}


def all_character_records() -> list[dict[str, Any]]:
    return [
        entry
        for entry in character_portrait_manifest().get("characters", [])
        if isinstance(entry, dict)
    ]


def characters_by_faction(faction: str) -> list[dict[str, Any]]:
    expected = str(faction or "").strip()
    return [
        entry
        for entry in all_character_records()
        if str(entry.get("faction") or "").strip() == expected
    ]


@lru_cache(maxsize=1)
def _character_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for entry in character_portrait_manifest().get("characters", []):
        if not isinstance(entry, dict):
            continue
        role_id = str(entry.get("id") or "").strip()
        name = str(entry.get("name") or "").strip()
        if role_id:
            by_id[role_id] = entry
        if name:
            by_name[name] = entry
    return by_id, by_name


def character_record(role_id_or_name: str) -> Optional[dict[str, Any]]:
    key = str(role_id_or_name or "").strip()
    if not key:
        return None
    by_id, by_name = _character_indexes()
    return by_id.get(key) or by_name.get(key)


def character_portrait_path(role_id_or_name: str) -> Optional[Path]:
    entry = character_record(role_id_or_name)
    if not entry:
        return None
    filename = str(entry.get("portrait") or "").strip()
    if not filename:
        return None
    path = PORTRAIT_DIR / filename
    return path if path.is_file() else None


def character_portrait_bytes(role_id_or_name: str) -> Optional[bytes]:
    path = character_portrait_path(role_id_or_name)
    if not path:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def beast_name_from_text(text: str) -> Optional[str]:
    value = str(text or "").strip()
    if not value:
        return None
    by_id, by_name = _character_indexes()
    if value in by_name and str(by_name[value].get("faction")) == "妖兽":
        return value
    if "·" in value:
        tail = value.rsplit("·", 1)[-1].strip()
        if tail in by_name and str(by_name[tail].get("faction")) == "妖兽":
            return tail
    for name, entry in by_name.items():
        if str(entry.get("faction")) == "妖兽" and name in value:
            return name
    return None


def beast_portrait_bytes(name_or_battle_label: str) -> Optional[bytes]:
    beast_name = beast_name_from_text(name_or_battle_label)
    return character_portrait_bytes(beast_name) if beast_name else None
