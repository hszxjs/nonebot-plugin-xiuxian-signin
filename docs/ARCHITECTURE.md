# 插件架构说明

本文档说明 `nonebot_plugin_xiuxian_signin` 的目录结构与模块职责，便于后续维护与功能新增。

## 顶层布局

```
nonebot_plugin_xiuxian_signin/        # 仓库根 = Python 包根
├── nonebot_plugin_xiuxian_signin/    # 实际插件包（pip 安装的顶层包）
│   ├── __init__.py                   # NoneBot 插件入口：plugin_meta + 生命周期 + 命令分发
│   ├── config.py                     # 插件配置模型（Config，零配置可启动）
│   ├── assets/                       # 运行时资源（字体/图标/背景/地图/头像）
│   ├── domain/                       # 修仙领域逻辑（纯函数，按子系统分子模块）
│   ├── cards/                        # 图片面板渲染（PIL）
│   ├── beast_realm/                  # 御兽秘境卡牌玩法
│   ├── storage/                      # JSON 持久化
│   ├── admin.py                      # 网页后台（FastAPI）+ AdminManager
│   ├── admin_dashboard.py            # 后台仪表盘数据聚合
│   ├── beast_realm_cards.py          # 御兽秘境面板渲染
│   ├── character_assets.py           # 角色头像 manifest 读取
│   ├── mystic_dungeon.py             # 秘境副本状态机 + 地图
│   ├── mystic_battle.py              # 秘境战斗引擎
│   ├── mystic_cards.py               # 秘境地图渲染
│   ├── mystic_runtime.py             # 秘境流程编排
│   └── mystic_menu.py                # 秘境菜单文本
├── webui/                            # 后台前端源码（React + AntD，构建到 assets/admin_web/）
├── tools/                            # 资源生成脚本（头像/图标/预览）
├── tests/                            # 测试套件
├── docs/                             # 文档
├── pyproject.toml                    # 包元数据 + packaging 配置
└── README.md
```

## 资源组织（assets/）

资源按类型分子目录，运行时代码统一用 `Path(__file__).parent / "assets" / <子目录>` 访问：

| 子目录 | 内容 | 读取方 |
| --- | --- | --- |
| `assets/fonts/` | 字体（HarmonyOS_Sans_SC.ttf） | `cards/` |
| `assets/panel_backgrounds/` | 面板背景图 | `cards/` |
| `assets/item_icons/` | 物品图标 + item_icon_records.json | `cards/`、`admin.py` |
| `assets/spirit_root_icons/` | 灵根图标 + manifest | `cards/` |
| `assets/realm_quality_icons/` | 境界品相图标 + manifest | `cards/` |
| `assets/character_portraits/` | 角色头像 + manifest.json | `character_assets.py`、`beast_realm/`、`admin.py` |
| `assets/beast_realm_spell_icons/` | 御兽秘境法术图标 | `beast_realm/`、`admin.py` |
| `assets/ui_sprite/signin/output/sprites/` | 签到面板 UI 切片 | `cards/` |
| `assets/mystic_maps/` | 秘境地图背景 + manifest + templates | `mystic_dungeon.py`、`mystic_cards.py` |
| `assets/mystic_dungeon_ui/` | 秘境副本 UI 元素 | `mystic_cards.py` |
| `assets/admin_web/` | webui 构建产物（index.html + js/css） | `admin.py`（由 webui/ 构建） |

**规则**：新资源放对应类型子目录；只有被运行时代码读取的资源才加入 `pyproject.toml` 的 `package-data`。生成产物（预览/报告）写 `build/`（已 gitignore）。

## domain/ — 修仙领域逻辑（按依赖分层）

`domain/` 是全部修仙规则逻辑，纯函数 + 数据表，无 NoneBot/PIL 依赖。按依赖关系分 5 层，**子模块只能 import 比自己低的层**：

```
Layer 0（基础，仅依赖标准库）
  constants.py    全部数据表（境界/灵根/物品/突破/战斗/经济…）+ 派生初始化
  utils.py        纯叶子工具（weighted_choice/stable_int/grade_ratio…）
  models.py       9 个 dataclass（UserRecord/Root/SigninResult/CombatRuntimeState…）

Layer 1（环打破器）
  rewards.py      物品/奖励核心（reward_*/normalize_reward/append_reward…）
                  被几乎所有子系统依赖，集中提取以消除循环依赖

Layer 2（基础子系统）
  roots.py        灵根/五行/丹器灵根/妖丹
  realms.py       境界/突破流程/瓶颈锁定/境界品质
  methods_arrays.py 功法/阵盘层数与熟练度/成长追踪

Layer 3（复合子系统）
  equipment.py    灵器/符箓/傀儡/灵植/仙源装备 + 各 power
  abilities.py    神通系统
  crafting.py     炼丹/炼器/消耗品使用
  mystic_drops.py 秘境掉落配置 + apply_admin_config + 运行时可变状态
  economy.py      商店/出售/交易/每日任务/路线身份/双修/天机占卜

Layer 4（顶层）
  combat.py       战斗引擎/战力/pk/排行奖励
  codex.py        图鉴与物品列表（available_*/admin_item_catalog）
  signin.py       签到/奇遇/钓鱼应用
```

`domain/__init__.py` 是 facade：`from .X import *` re-export 全部公开 API，外部（`__init__.py`/`cards`/`admin` 等）只需 `from .domain import X`，不感知内部子模块。

### 延迟访问机制（`_domain`）

部分 dataclass 的 property / 部分子系统函数反向调用其它子系统（如 `UserRecord.is_bottleneck` 调 `is_breakthrough_bottleneck`）。为避免循环导入，各子模块定义 `_domain = None`，由 `domain/__init__.py` 在加载完成后注入为 domain 主模块：

```python
# domain/__init__.py
_domain_self = sys.modules[__name__]
from . import models as _models_module
_models_module._domain = _domain_self   # 子模块内用 _domain.FUNC(...) 延迟访问
```

子模块内跨层调用用 `_domain.FUNC(...)` 而非直接引用，运行时（包已加载完毕）解析。

### 运行时可变状态（apply_admin_config）

`mystic_drops.py` 持有秘境掉落的运行时可变状态（`MYSTIC_CATEGORY_WEIGHTS` 等 5 个容器 + 6 个可调标量）。`apply_admin_config` 用 `global`/`.clear()`/`.update()` 就地修改。读取这些标量的代码用 `_mystic_drops_module.X`（模块属性引用）拿最新值，**不可**用 `from .mystic_drops import X`（那是导入时的快照，重绑后失效）。

## cards/ — 图片面板渲染

PIL 渲染，仅依赖 `domain`。公开 API：`render_signin_card`/`render_fishing_card`/`render_battle_card`/`render_adventure_card`/`render_text_panel`/`set_font_paths`。资源路径用 `Path(__file__).parent.parent / "assets"`（cards 是子包，多一层）。

## beast_realm/ — 御兽秘境

自包含卡牌玩法（无 sibling 依赖）。`beast_realm_cards.py` 是其面板渲染。`ROOT = Path(__file__).parent.parent`（子包，指向包根读 assets）。

## storage/ — 持久化

`JsonStore` 类，一把 `asyncio.Lock` 守护，按数据类型分组方法（玩家/排行/交易/救援/秘境）。数据写入 localstore 或 `xiuxian_signin_data_dir`，不进仓库。

## __init__.py — 插件入口

- `__plugin_meta__` / `__version__`：NoneBot 插件元数据（必须在此）
- 单例实例化：`config`/`store`/`admin_manager`/`mystic_coordinator` + 6 个游戏状态字典
- 生命周期：`@driver.on_startup`（启动后台/恢复秘境/排行调度）、`@driver.on_shutdown`
- 57 个 `on_message` matcher + handler：命令分发（签到/面板/突破/背包/…/秘境/御兽/交易）
- 兜底 matcher：`chat_rank_counter`（p99，群聊统计）、`normal_duel_chat`（p8，斗法）

## 添加新功能的指引

| 场景 | 位置 |
| --- | --- |
| 新增修仙规则/数据 | `domain/` 对应子系统；纯数据加 `constants.py` |
| 新增领域函数 | 归入 `domain/` 的 Layer 2-4 对应模块；跨层调用用 `_domain.` |
| 新增图片面板 | `cards/`（新 render 函数） |
| 新增命令 | `__init__.py` 的 matcher + handler（未来可迁 `commands/` 子包） |
| 新增后台页面 | `webui/src/`（前端）+ `admin.py`（API 路由） |
| 新增资源 | `assets/` 对应子目录 + `pyproject.toml` package-data |
| 新增秘境内容 | `mystic_dungeon.py`（状态机）/ `assets/mystic_maps/`（地图） |

## 测试

`tests/` 用 `importlib` 动态加载模块。加载 domain 子包时用「伪造父包」模式（伪造 `nonebot_plugin_xiuxian_signin` 的 `__path__`，避免触发插件入口的 NoneBot 初始化）。运行：

```bash
.venv/Scripts/python.exe -m unittest discover -s tests   # unittest 套件
.venv/Scripts/python.exe -m pytest tests/                 # pytest 套件（mystic 等）
.venv/Scripts/python.exe -m mypy                          # 类型检查
```
