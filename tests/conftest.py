"""pytest 全局初始化。

命令子模块（``commands/*``）在 import 时会经 ``..state`` 取 NoneBot driver，
因此需要先初始化。已在别处初始化过则直接复用，避免重复 init 覆盖全局状态。
"""

from __future__ import annotations

import nonebot

try:
    nonebot.get_driver()
except ValueError:
    nonebot.init()
