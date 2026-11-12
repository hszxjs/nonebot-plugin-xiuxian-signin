"""domain 包：数据表、工具、数据类与各玩法子系统。

分层顺序固定，下层不得 import 上层；反向调用（下层需要上层函数）一律在**函数体内** import，
模块级不再持有 ``_domain`` 全局访问器，也不存在由 ``__init__`` 注入的隐式依赖。

constants → utils → models → rewards → roots → realms → methods_arrays
→ equipment → abilities → crafting → mystic_drops → economy → combat → codex → signin
"""

from __future__ import annotations

from .constants import *  # noqa: F401,F403  # 数据表与派生初始化
from .utils import *  # noqa: F401,F403  # 通用工具函数
from .models import *  # noqa: F401,F403  # 数据类
from .rewards import *  # noqa: F401,F403  # 物品/奖励核心（Layer 1 环打破器）
from .roots import *  # noqa: F401,F403  # 灵根子系统
from .realms import *  # noqa: F401,F403  # 境界与突破子系统
from .methods_arrays import *  # noqa: F401,F403  # 功法与阵盘子系统
from .equipment import *  # noqa: F401,F403  # 装备子系统
from .mystic_drops import *  # noqa: F401,F403  # 秘境掉落与令牌
from .economy import *  # noqa: F401,F403  # 经济与商店
from .combat import *  # noqa: F401,F403  # 战斗与结算
from .codex import *  # noqa: F401,F403  # 图鉴与功法/阵盘查询
from .signin import *  # noqa: F401,F403  # 签到与每日结算
