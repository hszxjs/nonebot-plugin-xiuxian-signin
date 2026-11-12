"""domain 包的显式依赖约束（R-20）。

重构前，``domain`` 用「模块级 ``_domain`` 全局访问器 + ``__init__`` 注入」来打破循环导入：
每个子模块先占位 ``_domain = None``，包初始化完成后再把包自身注入回去。这让依赖关系变成隐式的——
读代码看不到「谁依赖谁」，只能靠运行时注入，且注入失效时报的是 ``NoneType has no attribute``。

现在改为：

1. 分层单向：低层模块只星号导入更低层模块，顺序固定；
2. 反向依赖（低层要用高层函数）一律在**函数体内** import，模块加载期不产生环；
3. 不再存在 ``_domain`` 占位/注入，也没有模块互相改写属性的隐式接线。

本文件把这些约束钉死，防止后续又被「一个全局访问器最省事」绕回去。
"""
from __future__ import annotations

import ast
import pathlib

import pytest

PACKAGE = pathlib.Path(__file__).resolve().parents[1] / "nonebot_plugin_xiuxian_signin"
DOMAIN = PACKAGE / "domain"

# 分层表：键是模块名，值越小越底层。数字大的模块可以星号导入数字小的，反之不行。
LAYERS = {
    "constants": 0,
    "utils": 1,
    "models": 2,
    "rewards": 3,
    "roots": 4,
    "realms": 5,
    "methods_arrays": 6,
    "equipment": 7,
    "abilities": 8,
    "crafting": 9,
    "mystic_drops": 10,
    "economy": 11,
    "combat": 12,
    "codex": 13,
    "signin": 14,
}


def _domain_modules() -> list[pathlib.Path]:
    return sorted(p for p in DOMAIN.glob("*.py") if p.name != "__init__.py")


def test_layer_table_covers_every_domain_module() -> None:
    actual = {p.stem for p in _domain_modules()}
    assert actual == set(LAYERS), "分层表与 domain/ 下的模块不一致，新增模块请登记层号"


def test_star_imports_only_go_downward() -> None:
    offenders: list[str] = []
    for path in _domain_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        own = LAYERS[path.stem]
        for node in tree.body:
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if not any(alias.name == "*" for alias in node.names):
                continue
            target = node.module.split(".")[-1]
            if target not in LAYERS:
                offenders.append(f"{path.stem}: 未登记的星号导入来源 {target}")
                continue
            if LAYERS[target] > own:
                offenders.append(
                    f"{path.stem}(L{own}) 星号导入了更高层 {target}(L{LAYERS[target]})"
                )
    assert not offenders, "星号导入出现反向依赖（应改为函数内 import）：\n" + "\n".join(offenders)


def test_no_domain_accessor_survives() -> None:
    """``_domain`` 占位/注入不得复活。"""
    offenders: list[str] = []
    for path in [*_domain_modules(), DOMAIN / "__init__.py"]:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "_domain":
                offenders.append(f"{path.name}:{node.lineno} 仍引用 _domain")
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "_domain"
            ):
                offenders.append(f"{path.name}:{node.lineno} 仍访问 _domain.{node.attr}")
    assert not offenders, "隐式全局访问器仍在：\n" + "\n".join(offenders)


def test_backward_calls_are_function_local_imports() -> None:
    """反向调用只允许出现在函数体内，不允许回到模块级。"""
    offenders: list[str] = []
    for path in _domain_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        own = LAYERS[path.stem]
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(fn):
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                target = node.module.split(".")[-1]
                if target not in LAYERS:
                    offenders.append(f"{path.stem}:{node.lineno} 函数内导入未知模块 {target}")
    assert not offenders, "函数内 import 指向了 domain 之外的模块名：\n" + "\n".join(offenders)


def test_mystic_tuning_snapshot_is_read_only() -> None:
    """秘境可调参数是只读快照，外部改不动。"""
    from nonebot_plugin_xiuxian_signin import domain

    tuning = domain.current_mystic_tuning()
    assert isinstance(tuning, domain.MysticTuning)
    assert isinstance(tuning.enabled_types, frozenset)
    assert isinstance(tuning.artifact_drop_pools, type(tuning.category_weights))
    with pytest.raises(TypeError):
        tuning.artifact_drop_pools[0] = ()  # type: ignore[index]
    with pytest.raises(Exception):
        tuning.fishing_option_rate = 0.5  # type: ignore[misc]


def test_apply_admin_config_swaps_snapshot_without_touching_old_one() -> None:
    """调参整对象替换：已发出的旧快照保持原值，读取方不会读到中间态。"""
    from nonebot_plugin_xiuxian_signin import domain

    before = domain.current_mystic_tuning()
    domain.apply_admin_config(
        {
            "mystic": {"fishing_option_rate": 0.4},
            "signin": {"extra_fishing_chance_rate": 0.35},
        }
    )
    try:
        after = domain.current_mystic_tuning()
        assert after is not before
        assert after.fishing_option_rate == pytest.approx(0.4)
        assert after.signin_extra_fishing_chance_rate == pytest.approx(0.35)
        # 旧快照是冻结对象，不受新配置影响
        assert before.fishing_option_rate == pytest.approx(0.05)
        assert before.signin_extra_fishing_chance_rate == pytest.approx(0.10)
    finally:
        domain.apply_admin_config({})


def test_artifact_drop_pools_follow_snapshot() -> None:
    """掉落池来自快照；未配置时回落到内置默认表。"""
    from nonebot_plugin_xiuxian_signin import domain

    default_entries = domain.configured_artifact_drop_entries()
    assert default_entries, "默认掉落池不应为空"

    domain.apply_admin_config(
        {
            "equipment_rules": {
                "artifact_drop_pools": {"0": [{"grade": "下品", "weight": 2.5}]},
            }
        }
    )
    try:
        entries = domain.configured_artifact_drop_entries()
        assert len(entries) == 1
        assert entries[0]["realm_index"] == 0
        assert entries[0]["weight"] == pytest.approx(2.5)
    finally:
        domain.apply_admin_config({})
    assert len(domain.configured_artifact_drop_entries()) == len(default_entries)
