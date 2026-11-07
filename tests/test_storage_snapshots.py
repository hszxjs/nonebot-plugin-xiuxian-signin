"""R-05：写前快照、轮转与审计日志。"""

from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

import pytest

PACKAGE_NAME = "storage_snapshot_test_package"
PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "nonebot_plugin_xiuxian_signin"
if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package

storage = importlib.import_module(f"{PACKAGE_NAME}.storage")
audit_module = importlib.import_module(f"{PACKAGE_NAME}.storage.audit")
snapshots = importlib.import_module(f"{PACKAGE_NAME}.storage.snapshots")

JsonStore = storage.JsonStore
atomic_write_json = storage.atomic_write_json
read_audit = storage.read_audit


@pytest.fixture(autouse=True)
def _reset_throttle() -> None:
    snapshots.reset_throttle()
    yield
    snapshots.reset_throttle()


def _snapshots_of(path: Path) -> list[Path]:
    return snapshots.list_snapshots(path)


def test_first_write_has_nothing_to_snapshot(tmp_path: Path) -> None:
    target = tmp_path / "users.json"

    atomic_write_json(target, {"a": 1})

    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}
    assert _snapshots_of(target) == []


def test_second_write_keeps_previous_version(tmp_path: Path) -> None:
    target = tmp_path / "users.json"
    atomic_write_json(target, {"a": 1})

    atomic_write_json(target, {"a": 2})

    snapshot_files = _snapshots_of(target)
    assert len(snapshot_files) == 1
    assert json.loads(snapshot_files[0].read_text(encoding="utf-8")) == {"a": 1}
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 2}


def test_auto_snapshot_is_throttled_but_forced_is_not(tmp_path: Path) -> None:
    target = tmp_path / "users.json"
    atomic_write_json(target, {"v": 0})
    atomic_write_json(target, {"v": 1})  # 第一份自动快照
    atomic_write_json(target, {"v": 2})  # 5 分钟内：节流跳过
    assert len(_snapshots_of(target)) == 1

    snapshots.capture_before_write(target, reason="admin")  # 显式来源不受节流
    assert len(_snapshots_of(target)) == 2


def test_unchanged_content_is_not_snapshotted_twice(tmp_path: Path) -> None:
    target = tmp_path / "users.json"
    atomic_write_json(target, {"v": 1})
    atomic_write_json(target, {"v": 2})
    atomic_write_json(target, {"v": 2})

    assert len(_snapshots_of(target)) == 1


def test_snapshots_rotate_and_keep_latest(tmp_path: Path) -> None:
    target = tmp_path / "users.json"
    atomic_write_json(target, {"v": 0})
    for index in range(1, 26):
        atomic_write_json(target, {"v": index})
        snapshots.capture_before_write(target, reason="admin", keep=5)

    snapshot_files = _snapshots_of(target)
    assert len(snapshot_files) == 5


def test_snapshot_failure_never_blocks_the_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "users.json"
    atomic_write_json(target, {"a": 1})

    def _boom(*_args: object, **_kwargs: object) -> Path:
        raise RuntimeError("snapshot exploded")

    monkeypatch.setattr(storage, "capture_before_write", _boom)
    atomic_write_json(target, {"a": 2})

    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 2}


def test_audit_appends_jsonl_and_reads_newest_first(tmp_path: Path) -> None:
    audit_module.audit(tmp_path, "admin.login", ip="127.0.0.1", result="ok")
    audit_module.audit(tmp_path, "admin.save_config", ip="127.0.0.1")

    entries = read_audit(tmp_path, limit=10)

    assert [entry["event"] for entry in entries] == ["admin.save_config", "admin.login"]
    assert entries[1]["ip"] == "127.0.0.1"
    assert entries[1]["result"] == "ok"
    assert entries[0]["ts"]


def test_audit_rotates_when_file_exceeds_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit_module, "MAX_BYTES", 80)
    audit_module.audit(tmp_path, "first", payload="x" * 40)
    audit_module.audit(tmp_path, "second", payload="y" * 40)
    audit_module.audit(tmp_path, "third", payload="z" * 40)

    assert (tmp_path / "audit.log.1").is_file()
    assert [entry["event"] for entry in read_audit(tmp_path, limit=10)] == ["third"]


def test_store_exposes_snapshot_and_audit_helpers(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    store.audit("mystic.close_run", run_id="r-1")

    assert [entry["event"] for entry in store.read_audit()] == ["mystic.close_run"]
    assert store.snapshot_directory(store.user_file_path) == tmp_path / "snapshots" / "users.json"
