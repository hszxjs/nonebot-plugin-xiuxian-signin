# 给 Codex 的目录说明

这个仓库本身就是 NoneBot 插件包目录，顶层 `__init__.py` 是插件入口。不要把运行时代码移动到额外的 `src/` 目录，除非同步修改 `pyproject.toml` 的 `tool.setuptools.package-dir` 和 NoneBot 加载名。

## 顶层文件

- `__init__.py`：NoneBot 插件入口，注册命令、生命周期、`__plugin_meta__`。
- `config.py`：插件配置模型，所有配置必须有默认值，保证零配置加载。
- `domain.py`：修仙系统规则、物品、灵根、境界、战斗和经济逻辑。
- `cards.py`：图片面板渲染，运行时只读取 `assets/` 下的资源。
- `storage.py`：JSON 数据读写，只写入 localstore 或用户配置的数据目录。
- `admin.py`：网页后台服务和 API。
- `beast_realm.py`：御兽秘境卡牌玩法逻辑。
- `character_assets.py`：角色头像 manifest 和图片读取。
- `pyproject.toml`：包元数据、NoneBot 插件名、运行依赖、package-data 白名单。

## 运行时资源

这些目录会进入发布包，只放插件运行必须读取的文件：

- `assets/fonts/`：只保留 `HarmonyOS_Sans_SC.ttf` 和字体授权说明。
- `assets/panel_backgrounds/`：图片面板背景。
- `assets/item_icons/item_icon_records.json`：物品图标映射。
- `assets/item_icons/items/*.png`：物品图标。
- `assets/spirit_root_icons/`：灵根图标和 manifest。
- `assets/realm_quality_icons/`：`quality_*.png` 和 `realm_quality_icon_manifest.json`。
- `assets/ui_sprite/signin/output/sprites/`：签到面板运行时切片。不要提交 html、spec、spritesheet、preview。
- `assets/character_portraits/manifest.json`：角色头像索引。
- `assets/character_portraits/portraits/*.png`：御兽秘境和后台会读取的角色头像。

## 开发与生成目录

- `tools/`：只放可重复运行的生成、切图、预览脚本。
- `build/`：所有预览图、报告、临时切图、GPT 生成运行记录都写到这里。该目录被 `.gitignore` 忽略。

## 不要提交的内容

- `assets/panel_previews/`
- `assets/gpt_source/`
- `assets/ui-sprite-runs/`
- `assets/item_icons/_debug/`
- `assets/item_icons/_backup*/`
- `*_preview.png`、`*_report.json`、`*_mapping.*` 等调试产物
- `assets/ui_sprite/*/output/html/`
- `assets/ui_sprite/*/output/spec/`
- `assets/ui_sprite/*/output/spritesheet/`

## NoneBot 插件规范检查点

- 包名保持 `nonebot_plugin_xiuxian_signin`。
- 项目名保持 `nonebot-plugin-xiuxian-signin`。
- 顶层必须保留 `__plugin_meta__ = PluginMetadata(...)`。
- 运行依赖写入 `pyproject.toml` 的 `[project].dependencies`。
- 玩家数据必须写入 localstore 或 `xiuxian_signin_data_dir`，不要放进仓库。
- 新资源只有被运行时代码读取时才加入 `pyproject.toml` 的 package-data。