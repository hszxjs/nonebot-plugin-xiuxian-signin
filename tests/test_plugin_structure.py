"""入口模块拆分后的结构约束（R-18）。

这些测试不验证玩法，只钉住「拆分后不允许退化」的三条底线：

1. ``commands/`` 子模块之间必须保持单向分层，不得出现循环导入；
2. ``commands/`` 子模块不得反向 import 插件入口（否则入口与子模块互相依赖）；
3. 入口模块体量只许下降，不许回升。
"""
from __future__ import annotations

import ast
import pathlib

import pytest

PACKAGE = pathlib.Path(__file__).resolve().parents[1] / "nonebot_plugin_xiuxian_signin"
COMMANDS = PACKAGE / "commands"

# 分层：数字小的模块不许导入数字大的模块。新增模块时在这里登记。
LAYERS = {
    "texts": 0,
    "parsing": 1,
    "panels": 2,
    "ranking": 2,
    "duel": 3,
    "formatting": 3,
    "beast": 3,
    # 斗地主自包含（自带触发词、matcher 与 handler），只被 rules 引用做兜底判定。
    "doudizhu": 3,
    "rules": 4,
}

# 允许 commands/ 从包根导入的模块名（都是与入口并列的功能包，不是入口本身）。
ALLOWED_ROOT_IMPORTS = {"beast_realm"}


def _command_modules() -> list[pathlib.Path]:
    return sorted(p for p in COMMANDS.glob("*.py") if p.name != "__init__.py")


def _sibling_imports(path: pathlib.Path) -> set[str]:
    """返回该模块从 commands/ 兄弟模块导入的名字来源（``from .x import``）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            found.add(node.module.split(".")[0])
    return found


def _root_imports(path: pathlib.Path) -> set[str]:
    """返回 ``from .. import x`` 里引用的名字。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 2 and not node.module:
            found.update(alias.name for alias in node.names)
    return found


@pytest.mark.parametrize("path", _command_modules(), ids=lambda p: p.stem)
def test_commands_layers_are_acyclic(path: pathlib.Path) -> None:
    name = path.stem
    if name not in LAYERS:
        pytest.skip(f"{name} 未登记分层，跳过（新增模块请补 LAYERS）")
    for dep in _sibling_imports(path):
        if dep not in LAYERS:
            continue
        assert LAYERS[dep] < LAYERS[name], (
            f"{name}(L{LAYERS[name]}) 依赖了 {dep}(L{LAYERS[dep]})，"
            f"会造成循环或反向依赖"
        )


@pytest.mark.parametrize("path", _command_modules(), ids=lambda p: p.stem)
def test_commands_never_import_entry_module(path: pathlib.Path) -> None:
    source = path.read_text(encoding="utf-8")
    assert "import nonebot_plugin_xiuxian_signin\n" not in source
    extra = _root_imports(path) - ALLOWED_ROOT_IMPORTS
    assert not extra, f"{path.stem} 从包根导入了非白名单对象：{sorted(extra)}"


def test_entry_module_does_not_grow() -> None:
    """入口模块只许变薄。R-18 目标 < 1000 行，每完成一批拆分下调此上限。"""
    lines = (PACKAGE / "__init__.py").read_text(encoding="utf-8").count("\n") + 1
    assert lines < 2600, f"入口模块已增长到 {lines} 行，请把新逻辑放进 commands/ 子模块"
