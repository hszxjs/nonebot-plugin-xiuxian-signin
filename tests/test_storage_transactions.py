"""R-03：跨用户货币操作的原子性（apply_to_users / transfer_spirit_stones）。"""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from pathlib import Path

import pytest

PACKAGE_NAME = "storage_transaction_test_package"
PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "nonebot_plugin_xiuxian_signin"
if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package

storage = importlib.import_module(f"{PACKAGE_NAME}.storage")
JsonStore = storage.JsonStore
InsufficientSpiritStones = storage.InsufficientSpiritStones
SqliteStore = importlib.import_module(f"{PACKAGE_NAME}.storage.sqlite_store").SqliteStore


@pytest.fixture(params=["json", "sqlite"])
def make_store(request: pytest.FixtureRequest):
    """R-16：同一套原子性用例对 JSON 与 SQLite 两个后端都成立。"""

    def _make(tmp_path: Path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        if request.param == "sqlite":
            return SqliteStore(tmp_path)
        return JsonStore(tmp_path)

    return _make


def _seed(store, user_id: str, stones: int) -> None:
    def _updater(records: dict[str, object]) -> None:
        records[user_id].spirit_stones = stones  # type: ignore[attr-defined]

    asyncio.run(store.apply_to_users([user_id], _updater))


def test_transfer_moves_stones_atomically(tmp_path: Path, make_store) -> None:
    store = make_store(tmp_path)
    _seed(store, "a", 100)
    _seed(store, "b", 20)

    records = asyncio.run(store.transfer_spirit_stones("a", "b", 30))

    assert records["a"].spirit_stones == 70
    assert records["b"].spirit_stones == 50
    assert asyncio.run(store.get_user("a")).spirit_stones == 70
    assert asyncio.run(store.get_user("b")).spirit_stones == 50


def test_insufficient_stones_leaves_both_sides_untouched(tmp_path: Path, make_store) -> None:
    store = make_store(tmp_path)
    _seed(store, "a", 10)
    _seed(store, "b", 0)

    with pytest.raises(InsufficientSpiritStones) as excinfo:
        asyncio.run(store.transfer_spirit_stones("a", "b", 11))

    assert excinfo.value.user_id == "a"
    assert excinfo.value.available == 10
    # 关键：异常路径下不得有任何一侧落盘（不能出现"扣了钱没到账"）。
    assert asyncio.run(store.get_user("a")).spirit_stones == 10
    assert asyncio.run(store.get_user("b")).spirit_stones == 0


def test_transfer_rejects_non_positive_amount(tmp_path: Path, make_store) -> None:
    store = make_store(tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(store.transfer_spirit_stones("a", "b", 0))


def test_concurrent_transfers_conserve_total(tmp_path: Path, make_store) -> None:
    store = make_store(tmp_path)
    _seed(store, "a", 500)
    _seed(store, "b", 0)

    async def run() -> None:
        await asyncio.gather(*(store.transfer_spirit_stones("a", "b", 1) for _ in range(200)))

    asyncio.run(run())

    payer = asyncio.run(store.get_user("a")).spirit_stones
    payee = asyncio.run(store.get_user("b")).spirit_stones
    assert payer == 300
    assert payee == 200
    assert payer + payee == 500


def test_concurrent_transfers_never_overdraw(tmp_path: Path, make_store) -> None:
    """并发下不能把余额扣成负数（旧实现先校验后扣款，存在双花窗口）。"""
    store = make_store(tmp_path)
    _seed(store, "a", 50)
    _seed(store, "b", 0)

    async def run() -> list[BaseException]:
        results = await asyncio.gather(
            *(store.transfer_spirit_stones("a", "b", 10) for _ in range(20)),
            return_exceptions=True,
        )
        return [item for item in results if isinstance(item, BaseException)]

    failures = asyncio.run(run())

    assert len(failures) == 15
    assert all(isinstance(item, InsufficientSpiritStones) for item in failures)
    assert asyncio.run(store.get_user("a")).spirit_stones == 0
    assert asyncio.run(store.get_user("b")).spirit_stones == 50


def test_reopen_trade_offer_restores_open_status(tmp_path: Path, make_store) -> None:
    store = make_store(tmp_path)
    created = asyncio.run(
        store.create_trade_offer("g1", "seller", "卖家", "", {"name": "青竹剑"}, 100)
    )

    taken = asyncio.run(store.take_trade_offer("g1", created["id"], "buyer"))
    assert taken is not None

    assert asyncio.run(store.reopen_trade_offer("g1", created["id"])) is True
    offers = asyncio.run(store.list_trade_offers("g1", market=False))
    assert [offer["id"] for offer in offers] == [created["id"]]
    assert offers[0]["status"] == "open"
    assert "buyer_id" not in offers[0]
