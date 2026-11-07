"""R-07：配置契约（Pydantic schema）、结构版本号与 revision 乐观锁。

这些用例守的是「保存失败必须整份不落盘」——配置写坏不会当场报错，而是到运行时
才表现为掉率异常或掉落全空，事后无法回溯到某次保存，所以校验必须硬。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from nonebot_plugin_xiuxian_signin import admin
from nonebot_plugin_xiuxian_signin.config_schema import (
    CURRENT_CONFIG_VERSION,
    RETIRED_MYSTIC_CONFIG_KEYS,
    ConfigConflictError,
    ConfigValidationError,
    ConfigVersionError,
    migrate_config,
    prune_unknown_config,
    validate_config,
)


def _manager(tmp: str) -> admin.AdminManager:
    data_dir = Path(tmp)
    return admin.AdminManager(admin.JsonStore(data_dir), data_dir)


def _default_config() -> dict[str, Any]:
    return json.loads(json.dumps(admin.DEFAULT_ADMIN_CONFIG, ensure_ascii=False))


def _client(app, manager: admin.AdminManager) -> TestClient:
    password = "Test-Password-0123456789"
    manager.auth.env_password = password
    manager.auth.ensure_initialized()
    return TestClient(app, cookies={admin.SESSION_COOKIE_NAME: manager.auth.issue_session()})


def _issues(exc: ConfigValidationError) -> dict[str, str]:
    return {item["path"]: item["message"] for item in exc.issues}


def test_default_config_round_trips_through_schema() -> None:
    """默认值必须能通过校验且往返无损，否则线上首次保存就会失败。"""
    default = _default_config()
    validated = validate_config(default)

    assert validated == default
    # 默认值里出现、schema 里没定义的键会让 extra="forbid" 直接拒收，
    # 这条断言就是把「加了配置项忘了进 schema」变成红灯。
    assert set(validated) == set(default)


def test_unknown_key_rejected_with_path() -> None:
    config = _default_config()
    config["mystic"]["fishing_option_rat"] = 0.05  # 少一个 e 的拼写错误

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(config)

    assert "mystic.fishing_option_rat" in _issues(excinfo.value)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("mystic", "fishing_option_rate"), 1.5),
        (("mystic", "fishing_option_rate"), -0.1),
        (("signin", "extra_fishing_chance_rate"), 2),
        (("mystic", "high_risk_loop_count"), -1),
        (("beast_realm", "card_pool_copies"), -5),
    ],
)
def test_out_of_range_rejected(path: tuple[str, ...], value: Any) -> None:
    config = _default_config()
    section = config
    for key in path[:-1]:
        section = section[key]
    section[path[-1]] = value

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(config)

    assert ".".join(path) in _issues(excinfo.value)


def test_wrong_type_rejected() -> None:
    config = _default_config()
    config["signin"]["extra_fishing_chance_rate"] = "很高"

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(config)

    assert "signin.extra_fishing_chance_rate" in _issues(excinfo.value)


def test_bool_is_not_a_number() -> None:
    """bool 是 int 的子类，不拦住就会被当成 1 静默通过。"""
    config = _default_config()
    config["beast_realm"]["card_pool_copies"] = True

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(config)

    assert "beast_realm.card_pool_copies" in _issues(excinfo.value)


def test_min_map_size_must_not_exceed_max() -> None:
    config = _default_config()
    config["mystic"]["min_map_size"] = 60
    config["mystic"]["max_map_size"] = 48

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(config)

    assert any("min_map_size" in item["message"] for item in excinfo.value.issues)


def test_legacy_category_weights_shape_is_preserved() -> None:
    """旧配置的 {类别: 权重} 形状必须能保存且原样保留，不能被归一化改写。"""
    config = _default_config()
    config["mystic"]["category_weights"] = {"灵器": 1.0}

    validated = validate_config(config)

    assert validated["mystic"]["category_weights"] == {"灵器": 1.0}


def test_prune_unknown_config_drops_only_unknown_keys() -> None:
    config = _default_config()
    config["mystic"]["legacy_key"] = 1
    config["totally_unknown"] = {"a": 1}
    config["equipment_rules"]["artifact_drop_pools"]["0"][0]["legacy_field"] = 2

    pruned = prune_unknown_config(config)

    assert "totally_unknown" not in pruned
    assert "legacy_key" not in pruned["mystic"]
    assert "legacy_field" not in pruned["equipment_rules"]["artifact_drop_pools"]["0"][0]
    # 已知键（含中文键与嵌套列表）必须原样保留。
    assert pruned["mystic"]["category_weights"] == config["mystic"]["category_weights"]
    assert pruned["equipment_rules"]["tier_default_realm"]["仙帝兵"] == config["equipment_rules"][
        "tier_default_realm"
    ]["仙帝兵"]


def test_migrate_strips_retired_keys() -> None:
    config = _default_config()
    for key in RETIRED_MYSTIC_CONFIG_KEYS:
        config["mystic"][key] = 3

    migrated, notes = migrate_config(config)

    for key in RETIRED_MYSTIC_CONFIG_KEYS:
        assert key not in migrated["mystic"]
    assert any("已退役" in note for note in notes)


def test_save_rejects_invalid_config_without_touching_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _manager(tmp)
        manager.load_config()
        before = manager.config_path.read_text(encoding="utf-8")

        config = manager.load_config()
        config["mystic"]["fishing_option_rate"] = 9
        with pytest.raises(ConfigValidationError):
            manager.save_config(config)

        assert manager.config_path.read_text(encoding="utf-8") == before
        assert manager.load_config()["mystic"]["fishing_option_rate"] == 0.05


def test_save_bumps_revision_and_rejects_stale_client() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _manager(tmp)
        first = manager.load_config()
        assert first["revision"] == 0

        saved = manager.save_config(first)
        assert saved["revision"] == 1

        # 旧标签页拿的还是 revision 0（内容已被别处改过）。
        stale = json.loads(json.dumps(saved))
        stale["mystic"]["fishing_option_rate"] = 0.2
        stale["revision"] = 0
        with pytest.raises(ConfigConflictError):
            manager.save_config(stale)

        assert manager.load_config()["mystic"]["fishing_option_rate"] == 0.05


def test_save_rejects_stale_schema_version() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _manager(tmp)
        config = manager.load_config()
        config["version"] = CURRENT_CONFIG_VERSION - 1

        with pytest.raises(ConfigVersionError):
            manager.save_config(config)


def test_put_config_route_returns_field_issues() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _manager(tmp)
        app = admin.create_admin_app(manager=manager)
        client = _client(app, manager)

        config = manager.load_config()
        config["mystic"]["fishing_option_rate"] = 3
        response = client.put("/xiuxian-admin/api/config", json=config)

        assert response.status_code == 400
        payload = response.json()
        assert payload["ok"] is False
        assert "mystic.fishing_option_rate" in {item["path"] for item in payload["issues"]}


def test_put_config_route_returns_409_on_stale_revision() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = _manager(tmp)
        app = admin.create_admin_app(manager=manager)
        client = _client(app, manager)

        config = manager.load_config()
        first = client.put("/xiuxian-admin/api/config", json=config)
        assert first.status_code == 200
        assert first.json()["config"]["revision"] == 1

        config["revision"] = 0  # 模拟隔夜未刷新的页面
        response = client.put("/xiuxian-admin/api/config", json=config)

        assert response.status_code == 409
        assert "刷新" in response.json()["error"]
