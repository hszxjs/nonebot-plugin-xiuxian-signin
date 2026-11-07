# nonebot-plugin-xiuxian-signin 全面评审报告

> README 式自包含文档 · 评审基准 commit `f0f33a7` · 评审日期 2026-11-06
> 评审对象：https://github.com/hszxjs/nonebot-plugin-xiuxian-signin
> 运行实例：`http://192.168.3.152:8081/xiuxian-admin`
>
> **v2 更新（2026-11-06）**：已完成与 ZCode / GLM 独立评审的互评与计划融合。判定结论、事实核查、分歧裁决与可执行的合并 Backlog 见 [`CONSOLIDATED_PLAN.md`](CONSOLIDATED_PLAN.md)；本文件保留为单方评审底稿与证据索引，§10 的单方计划已被 v2 取代。

---

## 0. 评审元信息

| 项 | 说明 |
|---|---|
| 评审类型 | 只读架构评审（代码 + 运行实例 + 文档） |
| 方法 | 全量遍历 `.py` / `.tsx` / `.md` / 构建配置；对运行实例发送 **GET 只读请求**；交叉比对 `git log` |
| 未执行 | 未发送任何写请求（PUT/POST/DELETE）；未修改项目源码；未运行测试套件；未做压力/基准测试；未读取生产数据目录内容 |
| 证据分级 | **A** = 运行实例实测；**B** = 源码行号可复核；**C** = 由 A/B 推导的推断 |
| 版本 | Python 包 `0.5.2`，`requires-python >=3.12` |

### 已知局限（影响结论强度，读者应知悉）

1. 未验证 wheel 实际内容；关于资源打包遗漏的判断基于 `pyproject.toml` 静态配置（**C 级**），需用 `python -m build` 后检查归档内容确认。
2. 未运行 `pytest` / `vitest` / `mypy`，测试覆盖评价基于用例数量与测试文件主题分布，非实际通过率或覆盖率数字。
3. 前端评价基于源码与 HTTP 响应，未做浏览器交互实测（渲染性能、大数据量表格卡顿等为推断）。
4. 性能结论基于 31 名玩家的当前规模与接口响应体积，未做并发压测；增长曲线为推断。
5. 无法确认宿主机是否存在公网端口映射或反向代理；安全建议按"可能暴露"的最坏假设给出。

---

## 1. 执行摘要

**总体判断：功能完成度与领域建模质量显著高于同规模插件的平均水平，但基础设施层存在两处会直接导致数据丢失或未授权访问的结构性缺陷，应在任何新功能之前处理。**

先说值得肯定的部分：

- `domain/` 采用显式 Layer 0–4 分层、纯函数、无 NoneBot/PIL 依赖，并有 `docs/ARCHITECTURE.md` 明确约束依赖方向；这在插件类项目中并不常见。
- 2026-07 的子包化重构（`cards/`、`storage/`、`beast_realm/`、`commands/`、`state.py`）方向正确且有阶段性验证记录。
- 秘境副本实现了状态机、revision 冲突检测与崩溃恢复，工程复杂度不低；测试约 161 个用例，覆盖 domain、秘境、后台鉴权边界。
- 静态资源路径的穿越防护（`safe_item_icon_path` 等）实现规范，实测 `..%2f..%2f` 探测返回 404。

三个最严重的问题：

1. **P0 · 后台默认无鉴权**。`xiuxian_signin_admin_token` 默认为空即视为"不校验"，同时 `admin_host` 默认 `0.0.0.0`、`admin_enabled` 默认 `True`。实测不带任何凭据即可读取全部玩家 QQ 号、昵称、完整存档与配置，并具备写接口。
2. **P0 · 双写者无互斥地并发写同一批 JSON 存档**。后台运行在独立 uvicorn 线程，绕过主 event loop 的 `asyncio.Lock`，且临时文件名固定，两者叠加会破坏存档。仓库已有"存档 JSON 损坏时自愈恢复"提交，属于症状补丁。
3. **P1 · 全量读写 + 无界数据增长**。每次 `save_user` 序列化全体玩家；单玩家存档已达 165 KB；`/api/items` 单次响应 8.1 MB；每条群消息触发全量磁盘读写。当前规模可用，但增长曲线陡峭。

一句话结论：**这是一个"游戏规则写得很好、但地基需要加固"的项目**。修地基不需要重写游戏规则。

---

## 2. 项目基线

| 维度 | 实测值 |
|---|---|
| Python 代码 | 30,352 行 / 34 个模块 |
| 前端代码 | 3,853 行（TSX + TS，含测试） |
| 测试代码 | 4,581 行 / 约 161 个用例 |
| 最大文件 | `__init__.py` 4,751 行、`cards/__init__.py` 2,868、`beast_realm/__init__.py` 2,470、`mystic_dungeon.py` 2,356、`domain/constants.py` 1,829 |
| 命令层 | 58 个 `on_message` matcher + 129 处命令文本判断，集中在 `__init__.py` |
| 运行时数据 | 31 名玩家；单条存档 165,442 B / 52 个顶层字段 / 424 个 `rewards` 条目 |
| 资源体积 | `assets/` 265 MB，其中 `mystic_maps/` 203 MB、字体 20 MB、头像 12 MB |
| 前端 bundle | 2.5 MB（charts 1.3 MB、antd 932 KB、业务 187 KB），未启用压缩中间件 |
| 技术栈 | NoneBot2 + OneBot V11、FastAPI/uvicorn、Pillow、pydantic；React + AntD + SWR + Ky + Vite(Rolldown) |

目录职责（`docs/ARCHITECTURE.md` 已有权威说明，此处不重复）：`domain/` 规则层、`cards/` 图片渲染、`storage/` JSON 持久化、`admin.py` 后台、`state.py` 共享单例、`webui/` 前端源码（构建产物回写 `assets/admin_web/`）。

---

## 3. 架构与模块划分

### 3.1 结构评价

分层意图清晰：`__init__.py`（接入）→ `domain/`（规则）→ `cards/`/`mystic_*`（表现与流程）→ `storage/`（持久化）→ `admin.py`（运营后台）。`domain/__init__.py` 作为 facade 对外 re-export，外部模块不感知内部 24 个子模块，这一设计降低了耦合。

### 3.2 问题清单

| 问题 | 证据 | 影响 |
|---|---|---|
| 入口文件成为"上帝模块" | `__init__.py` 4,751 行，含解析、格式化、图片构造、调度、58 个 matcher 注册（`__init__.py:3125+`） | 单文件承担 4 类职责；改动冲突高；无法独立测试命令解析 |
| 命令分发基于文本 `Rule` | 58 处 `on_message(rule=Rule(...))`，129 处 `text == / startswith` 判断 | 无参数模型、无自动帮助生成、优先级靠人工排布；新增命令需在多处同步 |
| 隐式全局可变状态 | `domain/__init__.py` 注入 `_domain_self`；`mystic_drops.py` 用 `global`/`.clear()` 就地改全局容器；读取方须用 `_mystic_drops_module.X` 而非 `from ... import X` | 导入顺序敏感、测试隔离困难、"导入时快照失效"类隐性 bug；文档已明确警告 |
| 会话状态仅存内存 | `state.py:100-107` 的 7 个可变字典（钓鱼 pending、决斗队列、斗地主牌桌、御兽路由） | 进程重启即丢失；与秘境已持久化的状态形成不一致体验 |
| `commands/` 迁移未竟 | 仅 `doudizhu.py` 一个子模块（934 行）迁入 | 重构处于中间态，收益未充分兑现 |

### 3.3 改进方向

命令层改为注册表（Alconna 或 `on_command` + 参数模型），按子系统拆分 `commands/`；配置改为不可变快照 + 显式依赖注入；会话状态统一走持久化或明确声明幂等重建。

---

## 4. 数据存储设计（最关键章节）

### 4.1 现状

`JsonStore` 管理 8 个 JSON 文件（`users.json`、`daily_chat_rank.json`、`group_members.json`、`tianji_divination_hall.json`、`unique_artifacts.json`、`trade_offers.json`、`mystic_rescue.json`、`mystic_dungeons.json`），以一把 `asyncio.Lock` 守护，模式统一为「全量读 → 内存中改 → 全量写」。

```python
# storage/__init__.py:175
self._lock = asyncio.Lock()

# storage/__init__.py:185-189
async def save_user(self, record):
    async with self._lock:
        data = self._read_json(self.user_file_path)       # 读全体玩家
        data[record.user_id] = ...
        self._write_json(self.user_file_path, data)       # 写全体玩家
```

### 4.2 P0：锁的失效与双写者竞争

- `install_admin_routes()`（`admin.py:830`）在全仓**仅被测试调用**；运行时走 `start_admin_server()`，它用 `threading.Thread(target=server.run)` 启动一个**独立 uvicorn 事件循环**（`admin.py:854-869`），由 `@driver.on_startup` 触发（`__init__.py:2660-2679`）。
- `AdminManager` 的 `list_players` / `get_player_record` / `save_player_record`（`admin.py:289-331`）直接调用同步的 `_read_json` / `_write_json`，**完全不经过 `asyncio.Lock`**，且该锁绑定在 NoneBot 主 loop，跨线程本就无效。
- 结论：命令处理与后台写操作是两个无互斥的写者，构成典型的 lost update 与文件级竞态。**证据等级 B（源码）+ A（实例确为独立 uvicorn 服务）**。

### 4.3 P0：固定临时文件名放大了竞态

```python
# storage/__init__.py:1517-1522
def _write_json(self, path, data):
    temp_path = path.with_suffix(".tmp")     # 固定名字，非唯一
    with temp_path.open("w", ...) as fp:
        json.dump(data, fp, ...)
    temp_path.replace(path)                   # 原子替换，但 tmp 被两个写者共用
```

两个写者并发写同一文件时会共用 `users.tmp`，互相覆盖，可产生截断或新旧内容拼接的坏 JSON。`_recover_json_file()` 的注释（`storage/__init__.py:1465-1468`）已明确写出「文件损坏（典型形态：历史并发写导致新旧内容拼接）」；`git log` 中的 `7e47521 fix: 存档 JSON 损坏时自愈恢复` 佐证该问题**已在生产发生**。

> **判断**：自愈机制是有价值的兜底，但它恢复的是"最后一段完整 JSON"，仍可能丢失最后若干次写入；且它掩盖了根因，使并发缺陷持续存在。修复顺序应当是"消除并发 → 保留自愈作为灾备"，而非仅依赖自愈。

### 4.4 其他存储问题

| 问题 | 证据 | 影响 |
|---|---|---|
| 无界增长 | 实测单玩家 424 个 `rewards`、165 KB（`GET /api/players/3305167706`） | `save_user` 是 O(总存档体积)；玩家数与背包深度双线性增长 |
| 无跨文件事务 | 交易/救援涉及 `users.json` + `trade_offers.json` + `mystic_rescue.json` 多次独立写 | 中途失败会留下不一致状态 |
| 无 schema 版本与迁移 | `admin_config.json` 用 `deep_update` 与默认值合并（`admin.py:253-264`） | 结构演进只能靠兼容读取，无法显式迁移 |
| 备份无轮转 | `backup_users()` 每次生成新文件（`admin.py:278-287`） | 磁盘空间随点击次数无限增长 |
| 高频热路径 | `add_chat_count` 每条群消息全量读写两个文件（`storage/__init__.py:201-228`），由 `chat_rank_counter`（priority=99, `block=False`）触发（`__init__.py:4724`） | 活跃群的磁盘 IO 与消息量同阶 |

### 4.5 已有的好设计

- `MysticRunConflict` / `MysticEncounterConflict`（`storage/__init__.py:31-45`）等于用应用层 revision 乐观锁模拟事务，迁移到数据库后可保留作幂等保护。
- `_recover_json_file` 用 `raw_decode` 逐段解析 + 备份坏文件，思路稳妥。
- `sanitize_user_record_data` 在写入前统一修复历史数据兼容性。

---

## 5. 安全评估

### 5.1 实测证据（均为不带任何 token 的 GET 请求）

| 请求 | 状态 | 返回 |
|---|---|---|
| `/xiuxian-admin/api/dashboard` | 200 | 8,711 B，全部玩家统计 |
| `/xiuxian-admin/api/players` | 200 | 3,557 B，31 个 QQ 号 / 昵称 / 灵石 / 战力 |
| `/xiuxian-admin/api/players/3305167706` | 200 | **165,442 B 完整存档** |
| `/xiuxian-admin/api/config` | 200 | 9,681 B，全部可调规则 |
| `/xiuxian-admin/api/items` | 200 | 8,147,839 B |
| `/openapi.json` | 200 | 15,902 B，未鉴权，暴露完整路由清单 |
| `/xiuxian-admin/assets/item-icons/..%2f..%2fadmin_config.json` | 404 | 路径穿越被正确拦截 |

### 5.2 根因

```python
# config.py:13-17
xiuxian_signin_admin_enabled: bool = True
xiuxian_signin_admin_token: Optional[str] = None
xiuxian_signin_admin_host: str = "0.0.0.0"

# admin.py:583-589
def _authorized(manager, header_token, query_token):
    return not manager.token or _token_from_parts(...) == manager.token
```

"零配置可启动"与"安全默认"被混为一谈：**未配置 token 被解释为开放访问**，且默认监听所有网卡。配合 `PUT /api/players/{id}`、`PUT /api/config`、`POST /api/backup`，任何能访问该端口的人都可任意改档、改数值规则、触发备份。

### 5.3 其他安全问题

| 项 | 证据 | 评级 |
|---|---|---|
| Token 走 query string 与 localStorage，且前端把 token 拼进图片 URL | `webui/src/lib/api.ts:59-88` | 中：易进入访问日志、浏览器历史、Referer |
| 明文 `==` 比较 token | `admin.py:584` | 低：时序侧信道，应改 `hmac.compare_digest` |
| `PUT /api/config` 全量覆盖，除秘境主题外无 schema 校验 | `admin.py:640-659` | 中高：畸形值注入全局可变状态，可导致运行时异常或数值绕过 |
| 改档无写前快照、无审计日志、无限流 | `admin.py:680-691` | 中：误操作不可追溯、不可回滚 |
| `openapi_url` 未关闭 | `admin.py:612` 仅关 `docs_url`/`redoc_url` | 低：信息泄露 |
| 静态资源路由不鉴权 | `admin.py:777-781` | 低：仅前端 bundle，但与"后台整体受保护"预期不一致 |
| 全链路 HTTP 明文 | 运行实例 | 中：内网嗅探可截获 token |

### 5.4 做得好的部分

`safe_item_icon_path` / `safe_character_portrait_path` / `safe_beast_spell_icon_path` / `_safe_static_file` 均用 `resolve()` + `relative_to()` 做根目录校验；测试套件包含 401/404 鉴权边界断言（`tests/test_admin_routes.py:266-272, 484-539`）。**问题不在实现细节，而在默认策略**。

### 5.5 改进方向与验收标准

默认绑定 `127.0.0.1`；token 为空时拒绝启动或仅允许本地回环；`openapi_url=None`；token 仅走自定义 header 或 HttpOnly Cookie；`compare_digest`；写操作强制审计日志与写前快照；失败限流；`PUT /api/config` 用 Pydantic 模型全量校验。

验收：不带 token 访问任意 `/api/*` 返回 401；`/openapi.json` 返回 404；错误 token 返回 401；改档后审计表出现对应记录且快照文件存在。

---

## 6. 性能评估

| 现象 | 实测 / 证据 | 影响 |
|---|---|---|
| `/api/items` 8.1 MB / 10,127 条 | `domain/codex.py:81-215` 每次请求重新遍历静态表构造全量目录，`item_catalog()` 无缓存 | 无分页、无字段裁剪、无 gzip（未挂任何中间件）；前端一次载入 8 MB JSON |
| `/api/equipment-rules` 1.4 MB | 同上，规则表全量回传 | 同上 |
| dashboard 每 10 秒全量重算 | `webui/src/lib/api.ts:171-175` + `admin_dashboard.py:100-161` | 每次读全量 `users.json` 并对每个玩家执行复杂 `battle_power()`；人数增长线性恶化 |
| 每条群消息触发全量落盘 | `storage/__init__.py:201-228` + `__init__.py:4724-4726` | 最高频磁盘热路径，且与其他写操作争抢同一把锁 |
| PIL 渲染阻塞 event loop | `build_signin_image` 在 `async def` 中同步调 `render_signin_card`（`__init__.py:1440-1447`），全仓无 `to_thread`/`run_in_executor` | 高峰期出图会拖慢所有消息响应 |
| 前端 2.5 MB bundle | `assets/admin_web/assets/`（charts 1.3 MB + antd 932 KB） | 首屏加载慢；charts 未按需加载 |
| 265 MB 资源打进 wheel | `pyproject.toml:60-82` | 安装体积与分发成本；`mystic_maps/` 占 203 MB |

改进方向：静态目录结果缓存 + 分页/字段裁剪 + `GZipMiddleware`；dashboard 改增量推送或降频（如 60s / 手动刷新）；群消息计数内存累加 + 定时批量落盘；渲染进线程池并预加载字体与底图；charts 懒加载；大资源拆可选包或运行时按需获取。

---

## 7. 代码质量与工程化

**加分项**：`ruff`（line-length 120）、`mypy`、`biome`、`vitest` 均已配置；`tests/` 约 161 个用例，秘境状态机与后台鉴权边界有专门测试；`docs/superpowers/specs/` 保留了 WebUI 重做与秘境重做的设计文档；提交信息规范，重构分阶段可追溯。

**扣分项**：

| 项 | 证据 |
|---|---|
| mypy 检查强度偏低 | `pyproject.toml:91-104` 仅列 6 个文件，且 `follow_imports = "skip"`，覆盖约 6/34 模块 |
| 无 CI、无 pre-commit | 仓库无 `.github/workflows/`，无 hook 配置；质量保障依赖开发者手动执行 |
| README 已过时 | "开发校验"段仍引用重构前的 `admin.py` / `cards.py` / `beast_realm.py` / `storage.py` 顶层路径，`python -m py_compile` 命令会失败 |
| 打包资源遗漏（**C 级推断，待验证**） | `pyproject.toml:60-82` 的 `package-data` 未含 `assets/mystic_events/*.json`（26 个事件库，544 KB）与 `assets/signin_calendar/*.png`（2.1 MB）；而 `mystic_events.py:20` 与 `cards/__init__.py:2697` 会在运行时读取它们。仓库无 `MANIFEST.in`、无 `setuptools-scm`、无 `setup.py`，因此 `include-package-data = true` 无额外文件来源 → pip 安装的 wheel 很可能缺少秘境事件与签到日历底图 |
| 测试缺口 | 无并发写冲突用例、无性能回归、无 wheel 内容校验 |

验证打包问题的最小命令：`python -m build && python -c "import zipfile,glob; z=zipfile.ZipFile(glob.glob('dist/*.whl')[0]); print([n for n in z.namelist() if 'mystic_events' in n or 'signin_calendar' in n])"`。

---

## 8. 优先级改进清单

| 优先级 | 编号 | 事项 | 动作 | 验收标准 |
|---|---|---|---|---|
| **P0** | P0-1 | 后台默认无鉴权 | 默认绑 `127.0.0.1`；token 为空则拒绝启动或仅回环可访问；关 `openapi_url`；`compare_digest`；token 移出 query/图片 URL；加审计与限流 | 不带 token 访问任意 `/api/*` → 401；`/openapi.json` → 404；错误 token → 401 |
| **P0** | P0-2 | 双写者并发损坏存档 | 优先把后台挂进 NoneBot 的 FastAPI `server_app`（复用已有 `install_admin_routes`），删除独立 uvicorn 线程；过渡期至少加进程级 `threading.RLock` + 唯一临时文件名（`mkstemp`）+ `fsync` | 并发 100 次签到 + 100 次后台改档后，`users.json` 可解析且无记录丢失；并发用例进入测试套件 |
| **P0** | P0-3 | 写操作不可回滚 | 改档/改配置前自动快照，备份轮转（保留 N 份） | 每次写操作产生快照；备份目录文件数有上限 |
| **P1** | P1-1 | 存储 O(N) 与事务缺失 | 引入 Repository + SQLite WAL（见 §10 路线分歧） | 单玩家读写不随玩家总数增长；跨表操作具备原子性 |
| **P1** | P1-2 | 配置无 schema 校验 | Pydantic 全量校验 + 配置版本号 + 迁移函数 | 非法配置返回 400 且不落盘（现有主题校验已覆盖一部分，需扩展到全量） |
| **P1** | P1-3 | 打包资源遗漏 | 补 `package-data`，加 wheel 内容校验到发布流程 | wheel 内包含事件库与日历底图 |
| **P1** | P1-4 | 接口负载 | 静态目录缓存 + 分页/字段裁剪 + `GZipMiddleware`；dashboard 降频/增量 | `/api/items` 首次之后走缓存；响应体积显著下降；dashboard 不再 10s 全量重算 |
| **P2** | P2-1 | 热路径卸载 | PIL 渲染进线程池；字体/底图预加载；群消息计数批量落盘 | 渲染期间消息处理延迟不被阻塞（可用并发基准验证） |
| **P2** | P2-2 | 命令层重构 | 命令注册表 + 参数模型，按子系统拆 `commands/` | `__init__.py` 降至 1,000 行以内；帮助文本由注册表生成 |
| **P2** | P2-3 | 隐式全局状态 | 显式依赖注入替代 `_domain`；配置改不可变快照 | 无 `global`/`.clear()` 式运行时改写；测试可并行隔离 |
| **P2** | P2-4 | 工程化 | CI 接入 ruff/mypy/pytest/vitest/build；扩大 mypy 覆盖；修正 README | PR 触发全量检查；README 命令可直接执行 |
| **P3** | P3-1 | 运营与内容能力 | 事件流支撑趋势分析（当前 `historical_trends: false`）；背包上限与自动堆叠；赛季/成就；内容包与代码解耦 | dashboard 可出留存曲线与经济监控 |
| **P3** | P3-2 | 资源治理 | 265 MB 资源外置或拆可选包；前端 charts 懒加载 | wheel 体积下降，首屏体积下降 |

---

## 9. 若重新设计：目标架构与理由

### 9.1 已锁定的前提约束（用户于本轮确认）

- 单实例、单机器人运行；**不存在多机器人/多进程共用同一份数据**。
- 数据全部存储在**宿主机本地**，无网络存储。
- 推论：排除分布式锁、跨实例同步、PostgreSQL/Redis、对象存储、后台服务化。**一致性问题被降维为"单进程内两个写者"**，可用少量代码根治；SQLite 足以覆盖可见生命周期。

### 9.2 目标架构

| 层 | 职责 | 关键约束 |
|---|---|---|
| 接入层 | NoneBot 命令注册表（Alconna）+ 事件总线 | 命令定义、参数校验、帮助生成同源 |
| 应用/用例层 | 用例编排与事务边界 | 一个用例 = 一个事务；领域事件在此产出 |
| 领域层 | 纯函数规则 + 静态数据表（保留现有 `domain/`） | 不依赖 IO；配置以不可变快照注入 |
| 基础设施层 | `Repository` 接口 → SQLite WAL；事件存储；图片资源本地缓存 | 单一写者；所有持久化经 Repository |
| 表现层 | 图片渲染 worker（线程池）+ Web 后台（**挂载在同一个 FastAPI app**）+ RBAC/审计 | 一个 event loop、一份配置、一次生命周期 |

### 9.3 三个关键决策及理由

1. **后台复用 driver，不起独立线程/端口。** 从架构上消灭双写者，同时去掉 `AdminServerHandle` 的线程 join 复杂度。理由：单实例前提下，独立端口没有任何收益，只有额外的一致性成本。
2. **Repository + 事务，而非"大 JSON"。** 单玩家读写从 O(总存档) 降到 O(1)；原子性由数据库保证；`_recover_json_file()` 可退化为灾备而非常态路径。理由：现有 `MysticRunConflict` 等 revision 机制可保留作幂等保护，迁移不需要推倒重来。
3. **领域事件 + 版本化配置。** 签到、掉落、交易、改档记录为事件流，规则与运营配置版本化、可回滚。理由：当前 dashboard 自认 `historical_trends: false`，因为只有快照；事件流同时解决趋势分析、经济监控与后台改档审计三个需求。

### 9.4 功能设计补充

| 方向 | 现状 | 建议 |
|---|---|---|
| 背包经济 | `rewards` 无上限，实测单玩家 424 条 | 加上限、自动堆叠/分解，建立产出—消耗闭环 |
| 长期留存 | 仅"每日签到快照 + 连签" | 赛季、成就、图鉴收集进度、排行榜历史 |
| 运营可视化 | 快照 dashboard，`historical_trends: false` | 事件流驱动留存曲线、灵石通胀、掉落分布 |
| 内容工程 | 26 主题约 2,160 条秘境事件 JSON 与代码同仓 | 独立内容包 + schema 校验 + 预览工具链，内容迭代不发版 |

### 9.5 与原方案的对比

| 维度 | 现状 | 目标 | 代价 |
|---|---|---|---|
| 一致性 | 应用层锁 + 跨线程失效 | 单 loop + 数据库事务 | 需迁移脚本 |
| 读写复杂度 | O(总存档) | O(单玩家) | 引入 schema 管理 |
| 配置 | 运行时可变全局 dict | 版本化不可变快照 | 热更新需显式 reload |
| 后台 | 独立端口/线程 | 复用 driver | 需处理路由前缀与现有部署习惯 |
| 可观测性 | 快照 | 事件流 + 审计 | 额外存储与写入量 |

---

## 10. 综合实施计划

> 说明：本章为**单方评审阶段的初版计划**，已被 [`CONSOLIDATED_PLAN.md`](CONSOLIDATED_PLAN.md) 的双评审融合版取代，仅保留作演进记录。原「存储迁移路线（两阶段 vs 一次性）」待决项标记为 `决策点 D1`，融合版已给出建议结论（两阶段）并新增 D2/D3。

### 阶段 0 · 止血（不改数据格式，最高优先级）

- **目标**：消除未授权访问与存档损坏风险。
- **改动**：P0-1（鉴权默认值 + openapi + 审计）、P0-2（后台并入主 loop 或进程级锁 + 唯一 tmp 名 + fsync）、P0-3（写前快照 + 备份轮转）。
- **验收**：§8 中 P0 三项的验收标准全部通过；新增并发写回归用例；不带 token 的探测全部 401。
- **回滚**：纯配置与写入路径改动，反向提交即可；无数据格式变更。
- **依赖**：无。

### 阶段 1 · 存储与配置治理

- **目标**：把 O(N) 全量读写、无事务、配置无校验三个问题一次性收敛。
- **决策点 D1**：`A→C 两阶段迁移`（推荐：先止血再迁 SQLite，风险解耦、每步可回滚）vs `一次性直迁 SQLite`（省中间态，回滚需整体回退）。**该项尚未确认**。
- **改动**：`PlayerRepository`/`ConfigRepository` 抽象；SQLite WAL 实现 + `revision` 乐观锁；一次性导入脚本，旧 JSON 只读保留 7 天作为回退锚点；Pydantic 配置 schema + 版本迁移；补 `package-data` 与 wheel 校验。
- **验收**：导入前后 31 名玩家的关键字段逐条比对一致；单玩家读写耗时不随玩家数增长；非法配置 400 且不落盘；wheel 含事件库与日历底图。
- **回滚**：保留旧 JSON + 特性开关，可在不恢复数据的情况下切回 `JsonStore`。

### 阶段 2 · 性能与工程化

- **改动**：静态目录缓存/分页/gzip、dashboard 降频或增量、渲染线程池、群消息计数批量落盘；CI 接入 ruff/mypy/pytest/vitest/build；扩大 mypy 覆盖；修正 README；前端 charts 懒加载。
- **验收**：`/api/items` 二次请求走缓存；渲染并发下消息延迟无显著劣化；PR 触发全量检查；README 命令可直接执行。

### 阶段 3 · 架构演进与运营能力

- **改动**：命令注册表拆分 `__init__.py`；消除隐式全局状态；会话状态持久化；事件流 + 趋势分析；背包上限与堆叠；内容包解耦；资源外置。
- **验收**：`__init__.py` ≤ 1,000 行；帮助由注册表生成；dashboard 可出留存/通胀曲线；wheel 体积显著下降。

### 阶段依赖

`阶段 0 → 阶段 1（D1 决策）→ 阶段 2 → 阶段 3`。阶段 0 与阶段 2 中的"接口缓存、前端优化"可并行；阶段 3 依赖阶段 1 的 Repository 抽象。

---

## 11. 双模型互评

### 11.0 互评结论（已完成，v2）

对方的 `评审报告-xiuxian-signin.md` 与 `改进backlog-xiuxian-signin.md`（评审方 ZCode / GLM，即用户所称 glm5.3-flash）已收到并逐条核查。按 §11.2 矩阵（权重 20/20/15/20/15/10）打分：

| 维度 | Z 方 | H 方 |
|---|---|---|
| 证据可验证性 | 4.5 | 4.5 |
| 根因定位深度 | **5.0** | 4.0 |
| 覆盖完整性 | **5.0** | 3.8 |
| 结论可执行性 | 4.5 | 4.5 |
| 权衡与边界意识 | 3.0 | **4.5** |
| 表达与可复核性 | 4.0 | **4.3** |
| **加权总分** | **4.40** | **4.28** |

**判定：Z 方报告综合水平略胜（+0.12）。** 优势在评审的核心价值——发现更多真实缺陷：本方遗漏了 **TOCTOU 丢更新**（`get_user`/`save_user` 分离，仅 5 处原子 `apply_to_user`）、**`_read_json` 返回 `{}` 导致清库**（`storage:1458-1475`，函数注释自身即承认该后果）、**`on_shutdown` 漏取消 `rank_scheduler_task`**，以及玩法数值与线上运营数据洞察。本方胜在证据分级、验收闭环、回滚设计与接口负载量化（8.1 MB `/api/items` 等，Z 方完全未涉及）。

**本方复核纠正对方两处**：① P1-5 / ZB-10「丢弃 sanitize 返回值 → 脏数据入库」**不成立**——`sanitize_user_record_data`（`domain/rewards.py:210-242`）是就地修改，应降级为 P3 防御性写法；② `REALMS` 实测 **35 项**而非「36 境」。另独立复核通过：PyPI JSON API 返回 404、`2 ** realm_index` 与 `clamp [0.1,0.9]` 公式、12 个 >800 行文件、React 19 / AntD 6 / Vite 8。

完整核查表、三处分歧裁决、融合后的 33 条 Backlog 与执行路线见 [`CONSOLIDATED_PLAN.md`](CONSOLIDATED_PLAN.md)。评分规则修订说明见该文档 §1。

### 11.1 历史状态（初版，已被 11.0 取代）

初版撰写时对方报告尚未提供，因此当时明确声明：不代写、不推测、不模拟另一模型的观点，"谁更有水平"的判定在信息缺失时不可作出，并预先给出评分矩阵、本方自评与融合规则。该立场在收到对方材料后仍被遵守——§11.0 的结论全部建立在可复核的核查之上。以下 §11.2–§11.5 为初版框架，保留作为方法学记录。

### 11.2 互评评分矩阵（建议双方共用同一套标准）

| 维度 | 权重 | 1 分锚点 | 3 分锚点 | 5 分锚点 |
|---|---|---|---|---|
| 证据可验证性 | 20% | 结论无出处 | 部分给出文件/接口 | 每条关键结论附文件行号或实测响应，可复现 |
| 根因定位深度 | 20% | 只描述现象 | 定位到模块 | 定位到具体代码路径并给出因果链，区分症状与根因 |
| 覆盖完整性 | 15% | 单一维度 | 覆盖架构/安全/性能 | 覆盖架构、模块、存储、安全、性能、工程化、测试并给出基线量化 |
| 结论可执行性 | 20% | 只有原则性建议 | 有优先级 | 有优先级、具体动作、验收标准、回滚与阶段依赖 |
| 权衡与边界意识 | 15% | 单方案断言 | 提到取舍 | 列出多方案 pros/cons，标注事实/推断/未验证项与适用边界 |
| 表达与可复核性 | 10% | 结构混乱 | 可读 | 结构化、术语一致、含证据索引与复现命令 |

**裁决规则（避免主观印象分）**：任一维度出现"把推断当事实陈述"或"结论无法追溯到证据"，该维度上限 3 分；出现事实性错误（如行号错误、接口状态错误）则该维度计 0 分。

> **v2 修订**：上述"事实性错误即计 0 分"条款在实测中过于刚性，单处非核心错误不足以否定整份报告的证据体系。实际互评对双方统一采用修订口径——每处可复核的事实错误扣 1 分，导致核心结论反转的扣 2 分；"把推断当事实上限 3 分"条款保留并实际执行。详见 `CONSOLIDATED_PLAN.md` §1。

### 11.3 本方自评（按同一矩阵，含已知短板）

| 维度 | 初版自评 | v2 复核 | 依据 / 保留意见 |
|---|---|---|---|
| 证据可验证性 | 4.5 | 4.5 | 关键结论附路径行号与 HTTP 实测；但打包遗漏为静态推断，未实际构建 wheel |
| 根因定位深度 | 4.5 | **4.0 ↓** | 双写者因果链完整并与 `git log` 互证；但遗漏 TOCTOU 与清库风险两条独立 P0 根因，初版自评偏高 |
| 覆盖完整性 | 4 | **3.8 ↓** | 七个维度均覆盖；但缺玩法数值、线上运营数据、生命周期、发布状态与 WebUI 交互观察，且未跑测试/压测 |
| 结论可执行性 | 4.5 | 4.5 | P0–P3 含动作与验收，阶段含回滚与依赖；但 `决策点 D1` 未决、无工作量估算 |
| 权衡与边界意识 | 4.5 | 4.5 | 标注证据分级 A/B/C、列出 5 条局限、多方案 pros/cons；对未验证项明确说明 |
| 表达与可复核性 | 4 | **4.3 ↑** | 含证据索引与复现命令；初版低估，按同一标准复核后上调 |

**初版自评合计约 4.3 / 5；按 v2 统一口径复核后为 4.28 / 5。** 本方自认的三处短板：① 未执行任何动态验证（测试、压测、构建产物校验）；② 未读取生产数据目录本身，数据规模通过 API 反推；③ 前端评价基于源码与响应体积，不是真实浏览器体验。互评后须追加第四处：**遗漏了两条 P0 级数据正确性缺陷**，这直接决定了根因深度维度的失分。

### 11.4 融合规则

1. **证据优先**：两份报告冲突时，以能复现的证据（源码行号、实测响应、命令输出）为准；无证据的一方降级为"待验证假设"。
2. **互补合并**：维度互不重叠的结论直接取并集；重叠且一致的结论合并并保留更强证据。
3. **根因冲突**：分别列出各自因果链，用最小实验裁决（例如并发写是否真会损坏文件，可用并发脚本复现）。
4. **计划融合**：以 P0 收敛项为公共底座；双方各自提出的独有高价值项进入候选池，按"风险削减 / 改动成本"比值排序后插入阶段。
5. **输出**：一份 `综合计划 v2`，标注每条结论的来源（本方 / 对方 / 双方一致 / 待验证）。

### 11.5 执行结果（已完成）

1. ✅ 按 §11.2（v2 修订口径）对两份报告逐维度打分，得分表与依据见 §11.0 与 `CONSOLIDATED_PLAN.md` §1；
2. ✅ 按 §11.4 裁决三处分歧，产出"谁更有水平"的有依据结论：**Z 方 4.40 > H 方 4.28**，分维度各有胜负；
3. ✅ 修订 §10 计划，输出 `CONSOLIDATED_PLAN.md`（33 条融合 Backlog + 五阶段路线 + 验收总表），给出 `D1` 建议结论并新增 `D2`/`D3`；
4. ✅ 将互评结论回写进本文档 §11.0、§11.3 与顶部 v2 提示；§10 标注为已被取代的初版。

> **可执行的唯一交付物**：[`CONSOLIDATED_PLAN.md`](CONSOLIDATED_PLAN.md)。阶段 0（止血）不依赖任何待决决策，可立即开工；`D2`（是否发布 PyPI）仅影响发布门禁，`D3`（玩法调参）可与阶段 3 并行。

---

## 附录 A · 证据索引

| 结论 | 位置 |
|---|---|
| 后台默认无鉴权 | `nonebot_plugin_xiuxian_signin/config.py:13-17`、`admin.py:583-589`、`admin.py:612` |
| 独立 uvicorn 线程 | `admin.py:854-869`、`__init__.py:2660-2679`；`install_admin_routes` 仅见于 `admin.py:830` 与 `tests/test_admin_routes.py:224` |
| `asyncio.Lock` 与全量读写 | `storage/__init__.py:175, 177-189, 1458-1475` |
| 固定 tmp 名 | `storage/__init__.py:1517-1522` |
| 损坏自愈与注释 | `storage/__init__.py:1465-1468, 1477-1515`；`git log` `7e47521` |
| 改档/配置写入 | `admin.py:640-659, 680-691, 289-331, 253-270` |
| 备份无轮转 | `admin.py:278-287` |
| 静态资源不鉴权 | `admin.py:777-781` |
| 路径穿越防护 | `admin.py:142-179, 554-564` |
| 消息热路径 | `storage/__init__.py:201-228`、`__init__.py:4724-4726` |
| 同步 PIL 渲染 | `__init__.py:1440-1447, 1532, 1837, 4530` |
| dashboard 全量重算 | `admin_dashboard.py:100-161`、`webui/src/lib/api.ts:171-175` |
| token 拼接进资源 URL | `webui/src/lib/api.ts:59-88` |
| 物品目录全量构造 | `domain/codex.py:81-215` |
| mypy 覆盖 | `pyproject.toml:91-104` |
| package-data | `pyproject.toml:60-82` |
| 运行时读取的事件/日历资源 | `mystic_events.py:20, 48-54`、`cards/__init__.py:2697` |
| README 过时命令 | `README.md`「开发校验」段 |
| 运行实例实测 | 见 §5.1、§2 表格（2026-11-06，仅 GET） |

## 附录 B · 复现命令

```bash
# 只读探测（不产生写入）
curl -i http://192.168.3.152:8081/xiuxian-admin/api/dashboard
curl -i http://192.168.3.152:8081/openapi.json
curl -s http://192.168.3.152:8081/xiuxian-admin/api/players | python -c "import sys,json; print(len(json.load(sys.stdin)['players']))"
curl -s http://192.168.3.152:8081/xiuxian-admin/api/items | python -c "import sys,json; print(len(json.load(sys.stdin)['items']))"

# 验证打包遗漏（会生成 dist/，属构建产物，非运行数据）
python -m build && python -c "import zipfile,glob; z=zipfile.ZipFile(glob.glob('dist/*.whl')[0]); print([n for n in z.namelist() if 'mystic_events' in n or 'signin_calendar' in n])"

# 代码规模
find nonebot_plugin_xiuxian_signin -name '*.py' -print0 | xargs -0 wc -l | tail -1
du -sh nonebot_plugin_xiuxian_signin/assets/*/ | sort -rh | head
```

---

*本报告为只读评审产物，未对运行实例执行写操作，未修改项目源码。*
