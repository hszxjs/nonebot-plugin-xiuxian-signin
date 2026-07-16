# nonebot-plugin-xiuxian-signin

面向 OneBot V11 的 NoneBot2 修仙签到插件。插件以图片面板输出，包含签到修炼、境界突破、灵根成长、灵器战力、功法阵盘、神通、秘境探索、交易、御兽秘境和网页后台。

## 安装

使用 NB-CLI：

```bash
nb plugin install nonebot-plugin-xiuxian-signin
```

或使用 pip：

```bash
pip install nonebot-plugin-xiuxian-signin
```

在 NoneBot 项目中加载：

```python
nonebot.load_plugin("nonebot_plugin_xiuxian_signin")
```

也可以写入 NoneBot 项目的 `pyproject.toml`：

```toml
[tool.nonebot]
plugins = ["nonebot_plugin_xiuxian_signin"]
```

## 配置

所有配置都有默认值，插件可零配置启动。常用配置如下：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `xiuxian_signin_data_dir` | 空 | 玩家数据目录；为空时使用 `nonebot-plugin-localstore` |
| `xiuxian_signin_timezone` | `Asia/Shanghai` | 签到与每日刷新时区 |
| `xiuxian_signin_image_width` | `900` | 图片面板宽度 |
| `xiuxian_signin_avatar_timeout` | `8.0` | 拉取 QQ 头像超时时间 |
| `xiuxian_signin_font_path` | 空 | 自定义常规字体路径 |
| `xiuxian_signin_bold_font_path` | 空 | 自定义粗体字体路径 |
| `xiuxian_signin_admin_enabled` | `true` | 是否启动网页后台 |
| `xiuxian_signin_admin_token` | 空 | 后台访问 Token，空表示不校验 |
| `xiuxian_signin_admin_path` | `/xiuxian-admin` | 后台路径 |
| `xiuxian_signin_admin_host` | `0.0.0.0` | 后台监听地址 |
| `xiuxian_signin_admin_port` | `8081` | 后台端口 |

插件包内统一使用 `assets/fonts/HarmonyOS_Sans_SC.ttf`。如需覆盖字体，请使用上方字体路径配置。

## 快速开始

第一次使用发送 `签到`，系统会创建玩家档案并抽取灵根。日常流程通常是：

```text
签到 -> 面板 -> 垂钓 -> 背包 -> 突破 / 秘境 / 御兽秘境
```

## 常用命令

| 模块 | 命令 | 说明 |
| --- | --- | --- |
| 入门 | `签到`、`面板`、`帮助`、`新手教程` | 创建角色、查看状态和基础说明 |
| 修为 | `突破`、`炼化灵液`、`炼化妖丹 1`、`后天灵根` | 提升境界、处理瓶颈和五行补全 |
| 背包 | `背包`、`使用丹药 1`、`批量炼化灵石 全部`、`批量出售 杂物 20` | 使用、炼化和整理物品 |
| 图鉴 | `图鉴`、`图鉴 名称`、`灵器图鉴`、`品相图鉴` | 查询物品、规则和成长路线 |
| 灵器 | `灵器`、`装备灵器 1 主手`、`卸下灵器`、`祭炼本命灵器 1` | 管理装备和本命灵器 |
| 战力 | `战力`、`战力榜`、`pk @群友` | 查看战力、排行和切磋 |
| 功法阵盘 | `功法`、`学习功法 1`、`阵盘`、`布置阵盘 1` | 学习功法、布置阵盘并推演成长 |
| 制作 | `炼丹`、`炼器`、`绘制符箓 1`、`傀儡` | 制作丹药、灵器、符箓和傀儡 |
| 神通 | `神通`、`神通图鉴`、`领悟神通 1` | 查看和领悟神通 |
| 秘境 | `秘境`、`探索 1`、`天机秘境`、`秘境救援 1000` | 探索秘境、挑战首领和救援 |
| 御兽秘境 | `御兽秘境`、`加入御兽秘境`、`开始御兽秘境`、`完成招募` | 多人或私聊 1V2 御兽卡牌玩法 |
| 路线 | `修炼路线`、`选择路线 剑修`、`选择身份 天机阁弟子` | 选择主修路线和身份令牌 |
| 交易 | `商店`、`购买 1`、`万宝楼挂售 灵器 1`、`交易 @对方 灵器 1 100` | 系统商店、寄售和玩家交易 |

## 网页后台

启用后访问：

```text
http://<NoneBot主机>:8081/xiuxian-admin
```

后台可查看玩家档案、备份数据、编辑玩家 JSON、查看物品目录、调整灵器规则、调整秘境掉落和管理御兽秘境卡牌。设置了 `xiuxian_signin_admin_token` 时，页面或 API 请求需要提供 Token。

## 数据与资源

玩家数据、交易记录、群排行和后台配置保存在插件数据目录，不写入代码仓库。运行时资源保留在 `assets/`：字体、图片面板背景、物品图标、灵根图标、境界品相图标、签到 UI 切片和角色头像。

生成预览、切图报告、GPT 生成记录等开发产物统一写入 `build/`，该目录已被忽略，不会进入发布包。

## 开发校验

```bash
python -m unittest discover -s tests -v
python -m py_compile __init__.py admin.py admin_dashboard.py beast_realm.py beast_realm_cards.py cards.py character_assets.py config.py domain.py storage.py tests/test_admin_routes.py tests/test_admin_dashboard.py tests/test_domain_features.py tests/test_xiuxian_admin_rewrite.py
pnpm --dir webui test
pnpm --dir webui build
python tools/render_adventure_preview.py
```

预览输出在 `build/previews/`。发布前请确认 `git status --short` 中没有误加入 `build/`、调试图、预览图或临时报告。
