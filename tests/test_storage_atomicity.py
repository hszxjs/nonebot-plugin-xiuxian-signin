"""阶段 0 回归：存储层不得静默清库，且并发写必须保持文件完整。

覆盖两条 P0：
- R-02：``_read_json`` 在 OSError / 不可恢复损坏时抛 ``StorageCorruptError``，
  绝不返回空 dict（否则后续「读-改-写」会把空状态写回，清空全部存档）。
- R-01：落盘使用唯一临时名 + fsync + ``os.replace``；跨线程读改写共用一把
  进程级锁，并发下账目守恒、文件不出现「新旧内容拼接」。
"""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
import threading
import types
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


PACKAGE_NAME = "storage_atomicity_test_package"
PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "nonebot_plugin_xiuxian_signin"
if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package

storage = importlib.import_module(f"{PACKAGE_NAME}.storage")

JsonStore = storage.JsonStore
StorageCorruptError = storage.StorageCorruptError


@pytest.fixture()
def store() -> JsonStore:
    with TemporaryDirectory() as tmp:
        yield JsonStore(Path(tmp))


def test_missing_file_returns_empty_mapping(store: JsonStore) -> None:
    # 首次运行是合法场景，缺失文件仍应返回空 dict，不能被当成损坏。
    assert store._read_json(store.user_file_path) == {}


def test_unrecoverable_corruption_raises_and_keeps_bytes(store: JsonStore) -> None:
    store.data_dir.mkdir(parents=True, exist_ok=True)
    store.user_file_path.write_text('{"broken": ', encoding="utf-8")

    with pytest.raises(StorageCorruptError) as excinfo:
        store._read_json(store.user_file_path)

    # 必须给出可定位的信息，且损坏内容被另存为备份而不是被清空覆盖。
    assert store.user_file_path.name in str(excinfo.value)
    assert excinfo.value.backup is not None
    assert excinfo.value.backup.exists()
    assert not store.user_file_path.exists()


def test_recoverable_corruption_restores_last_complete_segment(store: JsonStore) -> None:
    store.data_dir.mkdir(parents=True, exist_ok=True)
    good = {"u1": {"user_id": "u1"}}
    # 历史并发写留下的典型形态：完整 JSON + 旧内容残留
    store.user_file_path.write_text(
        json.dumps(good, ensure_ascii=False) + '{"u2": {"user_id": "u2"',
        encoding="utf-8",
    )

    assert store._read_json(store.user_file_path) == good
    # 恢复后应写出干净文件，而不是让坏内容留在原地
    assert json.loads(store.user_file_path.read_text(encoding="utf-8")) == good


def test_read_oserror_raises_instead_of_empty(store: JsonStore) -> None:
    store.data_dir.mkdir(parents=True, exist_ok=True)
    # 用目录占位同名文件：任何平台的 open() 都会以 OSError 失败
    store.user_file_path.mkdir()

    with pytest.raises(StorageCorruptError):
        store._read_json(store.user_file_path)


def test_atomic_write_leaves_no_temp_files(store: JsonStore) -> None:
    store.data_dir.mkdir(parents=True, exist_ok=True)
    store._write_json(store.user_file_path, {"a": 1})

    leftovers = [p.name for p in store.data_dir.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []
    assert json.loads(store.user_file_path.read_text(encoding="utf-8")) == {"a": 1}


def test_concurrent_thread_writes_never_tear_the_file(store: JsonStore) -> None:
    store.data_dir.mkdir(parents=True, exist_ok=True)
    payload = {f"u{index}": {"user_id": f"u{index}", "nickname": "修" * 50} for index in range(40)}
    errors: list[BaseException] = []

    def writer(offset: int) -> None:
        try:
            for _ in range(15):
                store._write_json(store.user_file_path, payload)
                # 读回必须始终是完整 JSON：拼接/截断会让这里抛 JSONDecodeError
                json.loads(store.user_file_path.read_text(encoding="utf-8"))
                _ = offset
        except BaseException as exc:  # pragma: no cover - 失败时才走到
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert json.loads(store.user_file_path.read_text(encoding="utf-8")) == payload


def test_update_json_sync_conserves_increments(store: JsonStore) -> None:
    store.data_dir.mkdir(parents=True, exist_ok=True)
    store._write_json(store.user_file_path, {"counter": 0})

    def bump(data: dict) -> None:
        data["counter"] = int(data.get("counter") or 0) + 1

    def worker() -> None:
        for _ in range(25):
            store.update_json_sync(store.user_file_path, bump)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert store._read_json(store.user_file_path)["counter"] == 200


def test_async_and_sync_writers_share_the_same_lock(store: JsonStore) -> None:
    store.data_dir.mkdir(parents=True, exist_ok=True)
    record = importlib.import_module(f"{PACKAGE_NAME}.domain").UserRecord(user_id="u1")

    async def async_writer() -> None:
        for _ in range(20):
            await store.save_user(record)

    def sync_writer() -> None:
        for _ in range(20):
            store.update_json_sync(
                store.user_file_path,
                lambda data: data.__setitem__("marker", "sync"),
            )

    thread = threading.Thread(target=sync_writer)
    thread.start()
    asyncio.run(async_writer())
    thread.join()

    data = json.loads(store.user_file_path.read_text(encoding="utf-8"))
    assert "u1" in data
    assert data["marker"] == "sync"
