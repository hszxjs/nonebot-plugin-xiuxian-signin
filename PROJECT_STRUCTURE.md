# 目录说明

这个仓库本身就是 NoneBot 插件包目录。**物理结构反映 Python 包层次**：仓库根下的 `nonebot_plugin_xiuxian_signin/` 是实际的插件包目录，其内代码即 `nonebot_plugin_xiuxian_signin` 包。

> 不要把运行时代码放回仓库根，也不要改回"仓库根=包根"的旧布局——那会让 setuptools 把仓库根的子目录（tests/tools/webui）误识别为顶层包。详见 `docs/ARCHITECTURE.md`。

## 顶层文件

- `nonebot_plugin_xiuxian_signin/__init__.py`：NoneBot 插件入口，注册命令、生命周期、`__plugin_meta__`。
- `pyproject.toml`：包元数据、NoneBot 插件名、运行依赖、package-data 白名单。
- `PROJECT_STRUCTURE.md` / `docs/ARCHITECTURE.md`：目录与架构说明。

## 插件包 `nonebot_plugin_xiuxian_signin/`

- `__init__.py`：插件入口。**只放元数据、生命周期（startup/shutdown）与子模块导入**，命令实现一律在 `commands/`；`tests/test_plugin_structure.py` 钉住行数上限 800。
- `state.py`：共享单例（`config` / `store` / `admin_manager` / `mystic_*` 服务）与内存对局态字典。命令子模块通过 `from ...state import store` 获取，避免循环导入。
- `runtime_state.py`：内存对局态的跨重启降级——停机记「哪个群还有局」、启动转成一次性提示，不序列化牌局本身。
- `config.py`：插件配置模型，所有配置都有默认值，保证零配置加载。
- `config_schema.py`：后台配置的 Pydantic v2 schema、版本迁移与「裁掉未定义键」。**必需 pydantic ≥ 2.0**。
- `net.py`：共享 httpx 客户端与头像 LRU 缓存（含关闭钩子）。
- `resource_pack.py`：秘境背景图外置资源包的下载/校验/解析（202 MB 不进 wheel）。
- `commands/`：命令子包，按 8 层单向依赖组织（`texts`/`picmenu` → `parsing` → `panels`/`ranking` → `duel`/`formatting`/`beast`/`rewards` → `doudizhu`/`mystic_result` → `rules` → `matchers` → `handlers/*`）。新增命令的固定路径：`rules.py` 判定 → `matchers.py` 注册 → `handlers/<域>.py` 实现 → `texts.py` 文案。
- `domain/`：修仙领域逻辑子包，15 个模块按依赖单向分层（constants → utils → models → rewards → roots → realms → methods_arrays → equipment → abilities → crafting → mystic_drops → economy → combat → codex → signin）。反向依赖只在**函数体内** import。详见 `docs/ARCHITECTURE.md`。
- `cards/`：图片面板渲染原语（PIL）：字体/背景缓存、圆角卡片、加权文字、渐变背景。
- `beast_realm/`：御兽秘境卡牌玩法逻辑（卡表、生成规则、九阵营、反阵）。
- `beast_realm_cards.py`：御兽秘境面板渲染。
- `mystic_dungeon.py` / `mystic_battle.py` / `mystic_cards.py` / `mystic_runtime.py` / `mystic_events.py` / `mystic_menu.py`：秘境副本子系统（状态机 / 战斗 / 渲染 / 编排 / 事件 / 菜单）。R-40 将整套重建。
- `storage/`：持久化层。默认 **SQLite（WAL）**，`xiuxian_signin_storage_backend=json` 可应急回退到 JSON。含原子写、覆盖前快照、审计日志、版本化结构步骤（`apply_schema_steps`）与 JSON→SQLite 幂等迁移。
- `admin.py`：后台管理服务与 API（账号+会话 Cookie 鉴权，`openapi_url` 关闭）。HTTP 层是可选依赖（`[admin]` extra）。
- `admin_auth.py`：后台账号、密码哈希（16 字符下限）与 7 天会话。
- `admin_dashboard.py`：后台仪表盘数据聚合。
- `character_assets.py`：角色头像 manifest 与图片读取。**当前在包内没有任何引用方**（2026-11-14 全仓核对），头像的实际渲染走 `cards/` 与 `beast_realm/`；保留它是因为 R-37/R-40 可能复用，清理前请先确认。

## 运行时资源 `assets/`

按类型分子目录（fonts/panel_backgrounds/item_icons/spirit_root_icons/realm_quality_icons/character_portraits/beast_realm_spell_icons/ui_sprite/mystic_maps/mystic_dungeon_ui/admin_web）。详见 `docs/ARCHITECTURE.md` 的"资源组织"表。

只放插件运行必须读取的文件。**不要提交**：`panel_previews/`、`gpt_source/`、`ui-sprite-runs/`、`item_icons/_debug/`、`item_icons/_backup*/`、`*_preview.png`、`*_report.json` 等调试产物。

## 开发与生成目录

- `tools/`：可重复运行的生成、切图、预览脚本。
- `webui/`：后台前端源码（React + AntD），构建到 `assets/admin_web/`。
- `build/`：预览图、报告、临时切图、生成记录，被 `.gitignore` 忽略。
- `tests/`：测试套件（unittest + pytest）。

## 文档

- `PROJECT_STRUCTURE.md`（本文件）：目录与模块职责清单。
- `docs/ARCHITECTURE.md`：分层约束、依赖规则、资源组织、新增功能指引。
- `docs/NUMBERS.md`：数值口径（境界 / 修为需求 / 收益区间 / 灵石价值表）。
- `docs/ASSESSMENT_REPORT.md`、`docs/CONSOLIDATED_PLAN.md`：重构前的评审底稿与综合计划，保留作为溯源材料，**不作为执行依据**。

## NoneBot 插件规范检查点

- 包名保持 `nonebot_plugin_xiuxian_signin`（物理目录与逻辑包名一致）。
- 项目名保持 `nonebot-plugin-xiuxian-signin`。
- `__init__.py` 必须保留 `__plugin_meta__ = PluginMetadata(...)`。
- packaging 用 `[tool.setuptools.packages.find]` 自动发现子包；新子包无需改配置。
- 运行依赖写入 `pyproject.toml` 的 `[project].dependencies`。
- 玩家数据写入 localstore 或 `xiuxian_signin_data_dir`，不进仓库。
- 新资源只有被运行时代码读取时才加入 `pyproject.toml` 的 package-data。
