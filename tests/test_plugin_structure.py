"""入口模块拆分后的结构约束（R-18）。

这些测试不验证玩法，只钉住三条底线：

1. ``commands/`` 子模块之间必须保持单向分层，不得出现循环导入；
2. ``commands/`` 子模块不得反向 import 插件入口（否则入口与子模块互相依赖）；
3. 入口模块体量只许下降，不许回升。

注意相对导入的层级随模块位置而变：``commands/x.py`` 的兄弟模块在 level 1，
``commands/handlers/x.py`` 的兄弟模块在 level 2、包根在 level 3。早期版本只按
level 1 取依赖，导致 handler 的全部依赖（``from ..matchers import``）实际未被检查。
"""
from __future__ import annotations

import ast
import pathlib

import pytest

PACKAGE = pathlib.Path(__file__).resolve().parents[1] / "nonebot_plugin_xiuxian_signin"
COMMANDS = PACKAGE / "commands"
HANDLED = COMMANDS / "handlers"

# 分层：数字小的模块不许导入数字大的模块。新增模块时在这里登记。
LAYERS = {
    "texts": 0,
    "picmenu": 0,
    "parsing": 1,
    "panels": 2,
    "ranking": 2,
    "duel": 3,
    "formatting": 3,
    "beast": 3,
    # 斗地主自包含（自带触发词、matcher 与 handler），用的是 panels/duel 这些 helper。
    "doudizhu": 4,
    "rewards": 3,
    "mystic_result": 4,
    "rules": 5,
    "matchers": 6,
}

# commands/handlers/ 下每个模块只允许依赖上表里的实现层。
HANDLER_LAYER = 7

# 允许 commands/ 从包根导入的子包名（是包根下的子包，不是入口本身）。
ALLOWED_ROOT_IMPORTS = {"beast_realm"}


def _command_modules() -> list[pathlib.Path]:
    top = [p for p in COMMANDS.glob("*.py") if p.name != "__init__.py"]
    nested = [p for p in HANDLED.glob("*.py") if p.name != "__init__.py"]
    return sorted(top + nested)


HANDLER_NAMES = {p.stem for p in HANDLED.glob("*.py") if p.name != "__init__"}


def _layer(path: pathlib.Path) -> int:
    """handler 统一在最上层；其余模块取分层表（未登记直接失败，不静默跳过）。"""
    if path.parent == HANDLED:
        return HANDLER_LAYER
    layer = LAYERS.get(path.stem)
    assert layer is not None, f"{path.stem} 未在 LAYERS 登记层号，新增模块请补登记"
    return layer


def _import_levels(path: pathlib.Path) -> tuple[int, int, int]:
    """返回 ``(同目录 level, 实现层 level, 包根 level)``。

    ``commands/duel.py``: 实现层在 1（``from .panels import``），包根在 2。
    ``commands/handlers/duel.py``: 同目录在 1（``from .x import`` 只可能是另一个 handler），
    实现层在 2（``from ..duel import`` 指的是 ``commands/duel.py``，不是 ``handlers/duel.py``），
    包根在 3。
    """
    if path.parent == HANDLED:
        return 1, 2, 3
    return 0, 1, 2


def _imports_at(path: pathlib.Path, level: int) -> set[str]:
    """取指定相对层级上的导入来源；``from . import x`` 取别名本身。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level != level:
            continue
        if node.module:
            found.add(node.module.split(".")[0])
        else:
            found.update(alias.name for alias in node.names)
    return found


def _implementation_imports(path: pathlib.Path) -> set[str]:
    """该模块依赖的 commands/ 实现层模块名（L0-L6）。"""
    _, impl_level, _ = _import_levels(path)
    return _imports_at(path, impl_level)


def _handler_peer_imports(path: pathlib.Path) -> set[str]:
    """handlers 之间的同目录依赖（只有 handlers 有这一层）。"""
    local_level, _, _ = _import_levels(path)
    if path.parent != HANDLED:
        return set()
    return _imports_at(path, local_level)


def _root_imports(path: pathlib.Path) -> set[str]:
    """返回 ``from <包根> import x`` 里引用的名字（子模块写法不算导入入口）。"""
    _, _, root_level = _import_levels(path)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == root_level and not node.module:
            found.update(alias.name for alias in node.names)
    return found


def test_layer_table_covers_every_command_module() -> None:
    """新增模块必须登记层号：漏登记会让分层测试静默失效。"""
    top_level = {p.stem for p in COMMANDS.glob("*.py") if p.name != "__init__.py"}
    assert top_level == set(LAYERS), (
        "分层表与 commands/ 下的模块不一致；请在 LAYERS 登记层号。"
        f"多余登记：{sorted(set(LAYERS) - top_level)}，未登记：{sorted(top_level - set(LAYERS))}"
    )


@pytest.mark.parametrize("path", _command_modules(), ids=lambda p: p.stem)
def test_commands_layers_are_acyclic(path: pathlib.Path) -> None:
    layer = _layer(path)
    for dep in _implementation_imports(path):
        dep_layer = LAYERS.get(dep)
        assert dep_layer is not None, f"{path.stem} 导入了未登记的实现层模块 {dep}"
        assert dep_layer < layer, (
            f"{path.stem}(L{layer}) 依赖了 {dep}(L{dep_layer})，会造成循环或反向依赖"
        )


@pytest.mark.parametrize("path", _command_modules(), ids=lambda p: p.stem)
def test_handlers_do_not_depend_on_each_other(path: pathlib.Path) -> None:
    """handlers 之间横向 import 说明共享逻辑该下沉到实现层。"""
    peers = _handler_peer_imports(path) & HANDLER_NAMES
    assert not peers, (
        f"handlers/{path.stem} 依赖了同层 handler {sorted(peers)}，"
        "请把共享逻辑下沉到 commands/ 实现层"
    )


@pytest.mark.parametrize("path", _command_modules(), ids=lambda p: p.stem)
def test_commands_never_import_entry_module(path: pathlib.Path) -> None:
    source = path.read_text(encoding="utf-8")
    assert "import nonebot_plugin_xiuxian_signin\n" not in source
    assert "from nonebot_plugin_xiuxian_signin" not in source, "包内模块请使用相对导入"
    extra = _root_imports(path) - ALLOWED_ROOT_IMPORTS
    assert not extra, f"{path.stem} 从包根导入了非白名单对象：{sorted(extra)}"


def test_entry_module_does_not_grow() -> None:
    """入口模块只许变薄。R-18 目标 < 1000 行，每完成一批拆分下调此上限。"""
    lines = (PACKAGE / "__init__.py").read_text(encoding="utf-8").count("\n") + 1
    assert lines < 800, f"入口模块已增长到 {lines} 行，请把新逻辑放进 commands/ 子模块"
