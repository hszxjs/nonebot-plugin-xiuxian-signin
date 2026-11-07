# nonebot-plugin-xiuxian-signin

面向 OneBot V11 的 NoneBot2 修仙签到插件。插件以图片面板输出，包含签到修炼、境界突破、灵根成长、灵器战力、功法阵盘、神通、秘境探索、交易、御兽秘境和网页后台。

## 安装

> 插件尚未发布到 PyPI，当前请从 GitHub Release 安装；发布 PyPI 后本节会恢复 `pip install` 说明。

从 [Releases](https://github.com/hszxjs/nonebot-plugin-xiuxian-signin/releases) 下载最新版的 wheel 安装：

```bash
pip install ./nonebot_plugin_xiuxian_signin-<版本>-py3-none-any.whl
```

同一 Release 中的 `mystic_maps.zip` 是秘境背景图资源包（约 200 MB，见下文「资源包」），机器人首次启动会自动下载；离线环境可提前下载后按「资源包」小节放置。

也可以直接从仓库源码安装：

```bash
pip install git+https://github.com/hszxjs/nonebot-plugin-xiuxian-signin.git
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
| `xiuxian_signin_admin_path` | `/xiuxian-admin` | 后台路径 |
| `xiuxian_signin_admin_host` | `0.0.0.0` | 独立端口模式下的后台监听地址 |
| `xiuxian_signin_admin_port` | `8081` | 独立端口模式下的后台端口 |
| `xiuxian_signin_asset_url` | 空 | 秘境资源包下载地址；留空用官方 Release，可指向自建镜像或本地 zip（离线部署） |
| `xiuxian_signin_asset_auto_download` | `true` | 启动时自动下载缺失的秘境背景图资源包 |
| `xiuxian_signin_storage_backend` | `sqlite` | 存储后端：`sqlite`（WAL）或 `json`（旧实现，应急回退）。首次以 sqlite 启动会自动迁移旧 JSON 存档并改名 `*.migrated.bak` 保留 |

插件包内统一使用 `assets/fonts/HarmonyOS_Sans_SC.ttf`。如需覆盖字体，请使用上方字体路径配置。

网页后台使用账号密码登录（HttpOnly 会话 Cookie），不再使用访问 Token。首次启动会自动创建管理员账号并在日志中打印初始密码，登录后强制修改；也可通过环境变量 `XIUXIAN_ADMIN_USER` / `XIUXIAN_ADMIN_PASSWORD` 指定初始账号。

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

后台优先挂载到 NoneBot 主服务的同一端口（FastAPI driver），访问：

```text
http://<NoneBot主机>:<NoneBot端口>/xiuxian-admin
```

若 driver 不支持挂载，则回退为独立端口（`xiuxian_signin_admin_host` / `xiuxian_signin_admin_port`，默认 `0.0.0.0:8081`）：

```text
http://<NoneBot主机>:8081/xiuxian-admin
```

后台使用账号密码登录（HttpOnly 会话 Cookie，不用 Token、不进 URL）。首次启动会在日志中打印一次性初始账号密码（默认用户名 `admin`，登录后强制修改），或用环境变量 `XIUXIAN_ADMIN_USER` / `XIUXIAN_ADMIN_PASSWORD` 指定。

后台可查看玩家档案、备份数据、编辑玩家 JSON、查看物品目录、调整灵器规则、调整秘境掉落和管理御兽秘境卡牌；改配置、改存档、备份等敏感操作均写入审计日志，存档与配置写入前自动留快照（可用于回退）。

## 资源包

`assets/mystic_maps/backgrounds/` 下的 26 张秘境背景原图（约 200 MB）**不打进安装包**（PyPI 单文件上限 100 MB），随 Release 以 `mystic_maps.zip` 分发。安装插件后首次启动会自动后台下载并逐张校验 SHA256，下载期间秘境使用程序化占位背景，不影响其他功能。

三种提供方式（优先级从高到低）：

1. 数据目录 `data_dir/assets/mystic_maps/` 里已有背景图（自动下载或手工放置）；
2. 源码仓库内的 `assets/mystic_maps/`（开发环境无需下载）；
3. 都没有 → 使用占位背景出图，并在日志提示。

离线/内网环境：把 Release 的 `mystic_maps.zip` 提前下载好，将配置项 `xiuxian_signin_asset_url` 指向该 zip 的本地路径（或自建镜像 URL），启动即安装。

## 数据与资源

玩家数据、交易记录、群排行和后台配置保存在插件数据目录，不写入代码仓库。运行时资源保留在 `assets/`：字体、图片面板背景、物品图标、灵根图标、境界品相图标、签到 UI 切片和角色头像。

生成预览、切图报告、GPT 生成记录等开发产物统一写入 `build/`，该目录已被忽略，不会进入发布包。

## 开发校验

```bash
python -m pytest tests/ -q
pnpm --dir webui typecheck
pnpm --dir webui test
pnpm --dir webui lint
pnpm --dir webui build
python -m build
python scripts/check_wheel_contents.py dist/*.whl
python scripts/build_asset_bundle.py --output dist/mystic_maps.zip
```

- pytest 全量单测（含资源包、并发事务、配置 schema 用例）；
- `check_wheel_contents.py` 校验 wheel：体积上限、秘境背景不进包、事件表/日历/图标/后台 SPA 完整；
- `build_asset_bundle.py` 产出随 Release 分发的 `mystic_maps.zip`（26 张背景，约 200 MB）。

预览输出在 `build/previews/`。发布前请确认 `git status --short` 中没有误加入 `build/`、调试图、预览图或临时报告。
