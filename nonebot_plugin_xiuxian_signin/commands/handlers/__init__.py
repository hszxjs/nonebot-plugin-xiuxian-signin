"""命令 handler 子包（R-18）。

每个模块只放某一域的 handle_* 函数，import 时把 handler 挂到 commands/matchers.py
里对应的 matcher 上；规则判定在 commands/rules.py。

子模块必须在这里被显式导入：NoneBot 的 handler 注册发生在模块执行期，
少导入一个模块就会整组命令静默消失，而且不会报错。
"""
from __future__ import annotations

from . import (  # noqa: F401
    beast,
    collection,
    craft,
    duel,
    fishing,
    inventory,
    mystic,
    signin,
    status,
    trade,
)

__all__ = [
    "beast",
    "collection",
    "craft",
    "duel",
    "fishing",
    "inventory",
    "mystic",
    "signin",
    "status",
    "trade",
]
