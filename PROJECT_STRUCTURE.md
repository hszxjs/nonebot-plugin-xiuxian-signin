# 目录说明

这个仓库本身就是 NoneBot 插件包目录。**物理结构反映 Python 包层次**：仓库根下的 `nonebot_plugin_xiuxian_signin/` 是实际的插件包目录，其内代码即 `nonebot_plugin_xiuxian_signin` 包。

> 不要把运行时代码放回仓库根，也不要改回"仓库根=包根"的旧布局——那会让 setuptools 把仓库根的子目录（tests/tools/webui）误识别为顶层包。详见 `docs/ARCHITECTURE.md`。

## 顶层文件

- `nonebot_plugin_xiuxian_signin/__init__.py`：NoneBot 插件入口，注册命令、生命周期、`__plugin_meta__`。
- `pyproject.toml`：包元数据、NoneBot 插件名、运行依赖、package-data 白名单。
- `PROJECT_STRUCTURE.md` / `docs/ARCHITECTURE.md`：目录与架构说明。

## 插件包 `nonebot_plugin_xiuxian_signin/`

- `__init__.py`：插件入口（命令分发 + 生命周期 + 单例）。
- `config.py`：插件配置模型，所有配置都有默认值，保证零配置加载。
- `domain/`：修仙领域逻辑子包，按依赖分 5 层（constants/utils/models → rewards → roots/realms/methods_arrays → equipment/abilities/crafting/mystic_drops/economy → combat/codex/signin）。详见 `docs/ARCHITECTURE.md`。
- `cards/`：图片面板渲染（PIL），运行时只读取 `assets/` 下的资源。
- `beast_realm/`：御兽秘境卡牌玩法逻辑。
- `beast_realm_cards.py`：御兽秘境面板渲染。
- `storage/`：JSON 数据读写，只写入 localstore 或用户配置的数据目录。
- `admin.py`：网页后台服务和 API。
- `admin_dashboard.py`：后台仪表盘数据聚合。
- `mystic_dungeon.py` / `mystic_battle.py` / `mystic_cards.py` / `mystic_runtime.py` / `mystic_menu.py`：秘境副本子系统（状态机/战斗/渲染/编排/菜单）。
- `character_assets.py`：角色头像 manifest 和图片读取。

## 运行时资源 `assets/`

按类型分子目录（fonts/panel_backgrounds/item_icons/spirit_root_icons/realm_quality_icons/character_portraits/beast_realm_spell_icons/ui_sprite/mystic_maps/mystic_dungeon_ui/admin_web）。详见 `docs/ARCHITECTURE.md` 的"资源组织"表。

只放插件运行必须读取的文件。**不要提交**：`panel_previews/`、`gpt_source/`、`ui-sprite-runs/`、`item_icons/_debug/`、`item_icons/_backup*/`、`*_preview.png`、`*_report.json` 等调试产物。

## 开发与生成目录

- `tools/`：可重复运行的生成、切图、预览脚本。
- `webui/`：后台前端源码（React + AntD），构建到 `assets/admin_web/`。
- `build/`：预览图、报告、临时切图、生成记录，被 `.gitignore` 忽略。
- `tests/`：测试套件（unittest + pytest）。

## NoneBot 插件规范检查点

- 包名保持 `nonebot_plugin_xiuxian_signin`（物理目录与逻辑包名一致）。
- 项目名保持 `nonebot-plugin-xiuxian-signin`。
- `__init__.py` 必须保留 `__plugin_meta__ = PluginMetadata(...)`。
- packaging 用 `[tool.setuptools.packages.find]` 自动发现子包；新子包无需改配置。
- 运行依赖写入 `pyproject.toml` 的 `[project].dependencies`。
- 玩家数据写入 localstore 或 `xiuxian_signin_data_dir`，不进仓库。
- 新资源只有被运行时代码读取时才加入 `pyproject.toml` 的 package-data。
