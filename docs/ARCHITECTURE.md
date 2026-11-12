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
  mystic_drops.py 秘境掉落配置 + apply_admin_config + 不可变调参快照
  economy.py      商店/出售/交易/每日任务/路线身份/双修

Layer 4（顶层）
  combat.py       战斗引擎/战力/pk/排行奖励
  codex.py        图鉴与物品列表（available_*/admin_item_catalog）
  signin.py       签到/奇遇/钓鱼应用
```

`domain/__init__.py` 是 facade：`from .X import *` re-export 全部公开 API，外部（`__init__.py`/`cards`/`admin` 等）只需 `from .domain import X`，不感知内部子模块。

### 反向依赖：只在函数体内 import

部分 dataclass 的 property / 部分子系统函数需要调用**更上层**的函数（如 `UserRecord.is_bottleneck` 调 `realms.is_breakthrough_bottleneck`、`rewards.advance_method_by_duplicate` 调 `methods_arrays.method_layer`）。

处理方式只有一种：**在该函数体首行 `from .<模块> import <名字>`**。模块加载期不产生回边，所以没有循环导入；调用发生在运行期，那时包已加载完毕。

```python
def is_bottleneck(self) -> bool:
    from .realms import is_breakthrough_bottleneck
    ...
```

历史实现是「各子模块占位 `_domain = None` + `domain/__init__.py` 加载后注入包自身 + 调用点写 `_domain.FUNC(...)`」，已于 R-20 全部删除。**不要复活它**：`tests/test_domain_layering.py` 会同时钉住「分层单向」与「`_domain` 不得出现」。

### 运行时可变状态：不可变快照 + 整对象替换

`mystic_drops.py` 的秘境调参不再是散落的可变全局。所有可调值收在一个冻结的 `MysticTuning` 里（映射字段是 `MappingProxyType`、集合是 `frozenset`、行列表是 `tuple`），由 `_TuningHolder` 单点持有：

```python
tuning = current_mystic_tuning()          # 读取方唯一入口
tuning.artifact_drop_pools                # 只读视图，写入抛 TypeError
```

`apply_admin_config` 解析完配置后**构造一个新快照整对象替换**（`_install_mystic_tuning`），不再 `global` 重绑标量、不再 `.clear()/.update()` 容器。因此读取方要么看到旧版本、要么看到新版本，不会读到「被清空到一半」的中间态；已取出的旧快照也永远保持构造时的值。

## cards/ — 图片面板渲染

PIL 渲染，仅依赖 `domain`。公开 API：`render_signin_card`/`render_fishing_card`/`render_battle_card`/`render_adventure_card`/`render_text_panel`/`set_font_paths`。资源路径用 `Path(__file__).parent.parent / "assets"`（cards 是子包，多一层）。

## beast_realm/ — 御兽秘境

自包含卡牌玩法（无 sibling 依赖）。`beast_realm_cards.py` 是其面板渲染。`ROOT = Path(__file__).parent.parent`（子包，指向包根读 assets）。

## storage/ — 持久化

`JsonStore` 类，一把 `asyncio.Lock` 守护，按数据类型分组方法（玩家/排行/交易/救援/秘境）。数据写入 localstore 或 `xiuxian_signin_data_dir`，不进仓库。

## __init__.py — 插件入口

726 行，只保留四类内容（R-18 拆分后）：

- `__plugin_meta__` / `__version__`：NoneBot 插件元数据（必须在此）
- 单例与工具的回导：`store`/`config`/`local_today` 等仍供本文件的生命周期钩子使用
- 生命周期：`@driver.on_startup`（启动后台/恢复秘境/排行调度）、`@driver.on_shutdown`
- 命令子模块导入：`commands.matchers`（注册 matcher）与 `commands.handlers`（挂 handler），**靠 import 副作用生效**

**不要再往里加 handler、规则或格式化函数**：`tests/test_plugin_structure.py::test_entry_module_does_not_grow` 会在超过 800 行时失败。

## state.py — 共享单例

集中持有所有命令子模块需要的共享对象，避免循环导入：
- 单例：`config`/`store`/`admin_manager`/`mystic_coordinator`/`mystic_catalog`
- 工具：`local_now`/`local_today`/`get_data_dir`/`load_config`
- 可变游戏状态：6 个字典（`pending_fishing_users`/`doudizhu_tables` 等）
- 生命周期句柄：`rank_scheduler_task`/`admin_http_server`

命令子模块通过 `from ..state import store, config` 获取单例。

## commands/ — 命令子包

命令层按「文本 → 解析 → 渲染 → 判定 → 注册」单向分层，`tests/test_plugin_structure.py` 用 AST 钉住这条分层，**新增模块必须登记到该测试的 `LAYERS` 表**：

| 层 | 模块 | 职责 |
| --- | --- | --- |
| L0 | `commands/texts.py` | 触发词、前缀、面板文案常量（纯数据，不引用运行时对象） |
| L0 | `commands/picmenu.py` | `PICMENU_NEXT_FUNCS` 菜单数据 + `command_hint` 底部提示 |
| L1 | `commands/parsing.py` | 玩家输入 → 结构化参数；群名片/昵称读取 |
| L2 | `commands/panels.py` | 唯一发消息出口：群聊/私聊面板、签到场次图片、`BEAST_REALM_ICON` |
| L2 | `commands/ranking.py` | 修为榜/战力榜取数与结算时刻判定 |
| L3 | `commands/duel.py` | 普通斗法的准备、结算与招式记录 |
| L3 | `commands/formatting.py` | 各面板纯文本装配（`format_*`，不发消息、不读写存档） |
| L3 | `commands/beast.py` | 御兽秘境分组播报 |
| L3 | `commands/rewards.py` | 唯一道具归一化（全服仅存一件的判定与复制） |
| L4 | `commands/doudizhu.py` | 斗地主完整子系统（触发词 + 卡牌引擎 + matcher + handler） |
| L4 | `commands/mystic_result.py` | 秘境命令结果 `MysticCommandResult` → 图片/文本的统一播报 |
| L5 | `commands/rules.py` | `is_*_message` 判定 + 秘境战斗期阻断其他插件的 `event_preprocessor` |
| L6 | `commands/matchers.py` | 55 个 `on_message` 注册（顺序即同优先级匹配顺序） |
| L7 | `commands/handlers/*.py` | 按域划分的 `handle_*`，见下表 |

`commands/handlers/` 按业务域拆分，**handler 之间不允许互相 import**（共享逻辑要下沉到 L0–L5 的实现层，测试会拦）：

| 模块 | 覆盖命令 |
| --- | --- |
| `signin.py` | 签到、签到日历、补签 |
| `status.py` | 面板、突破/散功、路线、每日任务、战力、历练、双修 |
| `collection.py` | 帮助、新手教程、图鉴、背包/灵器/功法/阵盘列表、排行榜、话痨榜 |
| `inventory.py` | 灵器/符箓/功法/阵盘的装备与卸下、丹药/灵液/灵植使用 |
| `craft.py` | 商店、炼丹、炼器、阵法推演、本命灵器、仙源、绘制符箓、唯一装备图鉴 |
| `trade.py` | 直交易、万宝楼、秘境救援 |
| `mystic.py` | 秘境群聊/私聊入口、天机秘境 |
| `beast.py` | 御兽秘境群聊/私聊 |
| `duel.py` | 普通斗法申请、群内招式、结算 |
| `fishing.py` | 灵河垂钓 |

约定：

- 子模块**不得 import 插件入口**（避免循环），共享单例走 `from ..state import store, config`；
- 需要入口里的 helper 时，说明该 helper 还没下沉到合适的层，应优先下沉而不是加反向依赖；
- 斗地主已改为直接 `from .panels import finish_panel`，不再有 `_g` 延迟访问（`tests/test_doudizhu_commands.py` 守着）。

## 添加新功能的指引

| 场景 | 位置 |
| --- | --- |
| 新增修仙规则/数据 | `domain/` 对应子系统；纯数据加 `constants.py` |
| 新增领域函数 | 归入 `domain/` 对应层级的模块；需要调上层函数时在函数体内 import（禁止 `_domain` 访问器） |
| 新增图片面板 | `cards/`（新 render 函数） |
| 新增命令 | 判定 `commands/rules.py` → matcher `commands/matchers.py` → handler `commands/handlers/<域>.py`；文案 `commands/texts.py` |
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
