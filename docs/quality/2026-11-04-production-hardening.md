# 2026-11-04 生产化加固与全面代码审查（HARDEN-001）

- 关联ID：OPS-001–OPS-009、SEC-001–SEC-003、TEST-002、UI-010、DOC-002
- 状态：已实现并通过本机检查；容器镜像未在本机构建（无 Docker 守护进程），由 CI `container` 作业验证
- 基线：`81f4549`（claude/exciting-ride-xaa0qp，与 main 同步点）；本轮不改变任何识别、几何、测量算法与冻结脚本
- 环境：Linux 容器、Python 3.12.3、Node 22.23.4、uv 0.11、ruff 0.17.3、mypy 2.4.1；无 GPU；未下载模型权重

## 范围与方法

1. 通读 `services/api/src/pv3d`、`services/multiview/infer.py`、`scripts/`、`apps/web/src`，记录生产环境缺口。
2. 由独立审查代理对相同代码做只读对抗审查，逐条用脚本复现后再决定是否修复；未复现或与冻结协议冲突的项只记录。
3. 每项修复先写失败测试再改代码；最后完整回归（后端 198 通过/2 可选 ML 跳过，前端 85 通过，mypy/ruff/prettier/tsc 与生产构建通过）。

## 不改动的内容

- `scripts/*_benchmark.py` 与 `services/multiview/infer.py` 被 `docs/measurement/*.json` 以 SHA256 绑定，本轮零改动；lint 规则对 `scripts/*` 的 E701/E702/E731 显式豁免。
- `pointcloud.py`、`geometry.py`、`measurement.py`、`undistortion.py`、`metric_benchmark.py` 仅增加类型注解或 `type: ignore` 注释，无语义变化；E09/E10-M 的数值结论不受影响。
- 未启用 `ruff format`：29 个文件会被重排，与冻结证据脚本冲突，且非正确性问题。

## 发现与修复

| ID | 发现（含复现） | 修复与验证 |
|---|---|---|
| OPS-001 | 无统一配置：绑定地址、端口、日志、队列上限等散落在 `os.environ`，无校验；错误值运行时才暴露 | `pv3d/config.py` `Settings.from_env()`，非法值在启动时报变量名；`python -m pv3d --check`；`test_config.py` 14 用例 |
| OPS-002 | 无生产入口与结构化日志；uvicorn 访问日志无请求关联 | `python -m pv3d`、`observability.configure_logging`（text/json）、`RequestContextMiddleware` 产生 `X-Request-ID` 与访问日志；测试覆盖 JSON 行与访问记录字段 |
| OPS-003 | 关闭时 `executor.shutdown(wait=True)` 只等运行中任务，已排队任务永久停留在 `queued` | `close()` 取消排队 future 并调用 `interrupt_unfinished()`；关闭期间新提交 503；测试 `test_shutdown_finishes_running_work_and_interrupts_queued_jobs` |
| OPS-004 | 同一 `PV3D_DATA_DIR` 可被两个服务同时打开，启动/关闭时互相把对方运行中的任务改成 `interrupted`（审查代理用两个实例复现） | `DataDirectoryLock`（`flock`，崩溃自动释放），第二个进程退出码 3 并提示占用者；测试覆盖嵌套实例被拒与释放后恢复 |
| OPS-005 | VGGT worker 超时硬编码 1800s，超时与失败信息相同；worker 输出非对象 JSON 行时 `message.get` 崩溃 | `PV3D_MULTIVIEW_TIMEOUT_S`，超时错误明确说明；进度行只接受 dict；两条测试（0.5s 超时、混合输出） |
| OPS-006 | 交互细化 `future.result()` 无上限等待单 worker；多图任务运行时细化请求可挂起至 30 分钟，重试会堆积名额 | `PV3D_REFINE_TIMEOUT_S`（默认 300s），超时取消未开始的 future 并释放名额，返回 503；测试用 1s 超时验证 `in_flight` 回落 |
| OPS-007 | `/api/health` 不暴露版本与队列余量，无法做容量探活 | 增加 `version` 与 `queue{max_pending,in_flight,available}`；`PV3D_MAX_PENDING_JOBS` 可配置；测试覆盖 |
| OPS-008 | SQLite 无 schema 版本；`synchronous=NORMAL` 只对初始化连接生效；缺少外键索引 | `PRAGMA user_version` 校验（新版本目录拒绝启动）、每连接 PRAGMA、三个索引；测试覆盖版本拒绝 |
| OPS-009 | 无容器与运维文档；CI 无类型检查、无格式检查、无并发取消 | `Dockerfile`/`.dockerignore`/`.env.example`/`.pre-commit-config.yaml`、`docs/operations.md`、三作业 CI（后端 lint+mypy+pytest+入口检查；前端 prettier+tsc+vitest+build；容器构建＋探活） |
| SEC-001 | 上传体积限制在 Starlette 解析并落盘整个 multipart 之后才生效（60 MB 请求先被完整写入临时文件） | `BodyLimitMiddleware` 按 `Content-Length` 预先拒绝（413/411）；测试覆盖 21 MB 与缺长度 |
| SEC-002 | 响应缺少 `nosniff`/`Referrer-Policy`/`no-store`；CORS 不可配置 | 中间件统一加头；`PV3D_CORS_ORIGINS` 显式开启；测试覆盖预检允许/拒绝 |
| SEC-003 | `upload_asset` 为 `async def` 却在事件循环上做 PIL 解码/缩放/哈希（审查代理测得 18 MB 上传阻塞循环约 0.9s） | CPU 与磁盘工作移入 `run_in_threadpool`；失败时清理资产目录 |
| TEST-002 | 前端套件在 4 核机器并行 20 个 worker 时，重交互用例超过 5s 默认超时，3/82 失败且不稳定 | `testTimeout/hookTimeout 20s`、`maxWorkers 2`、`asyncUtilTimeout 3s`（断言不变）；连续三轮全通过后记录 |
| UI-010 | 手动标注使用 `crypto.randomUUID()`，仅安全上下文可用；通过局域网 HTTP 访问时画框静默失败 | `core/ids.ts` 回退到 `getRandomValues` 的 v4 UUID；5 处调用替换；单元测试覆盖无 `randomUUID`/无 `crypto` |
| UI-011 | `32-character job ID` 占位符未翻译；新增 503/忙碌/缺失掩码三条服务端消息无三语 | 词典与 `serverMessages` 补齐中英西 |
| DOC-002 | 缺少部署、健康检查、日志、备份与升级说明 | `docs/operations.md`，README 中英文入口，`docs/running.md` 变量表更新 |
| 其他 | `get_refinement_mask` 文件缺失返回 500；MPO（多帧 JPEG）被拒；错误方法返回 404 而非 405；mypy 33 处错误 | 404/接受 MPO/405；mypy 零错误并纳入 CI |

## 已记录但未改动

- 原始上传字节 `assets/<id>/original.bin` 保留 EXIF/GPS 且无清理策略（审查代理指出）。保留以维持输入哈希证据链，已在运维文档说明备份时单独处理。
- pydantic 校验信息按既定策略原文显示（`docs/i18n.md`），未翻译。
- 前端 Three.js 独立 bundle 仍超过 Vite 500 kB 提示阈值，与此前记录一致。

## 验证命令与结果

```bash
.venv/bin/ruff check services/api scripts services/multiview/infer.py   # All checks passed
.venv/bin/mypy                                                         # Success: no issues found in 20 source files
.venv/bin/python -m pytest -p no:cacheprovider                         # 198 passed, 2 skipped
npm --prefix apps/web run lint && npm --prefix apps/web run typecheck   # prettier/tsc 通过
npm --prefix apps/web test                                             # 85 passed（三轮）
npm --prefix apps/web run build                                        # 构建通过
PV3D_DATA_DIR=/tmp/x .venv/bin/python -m pv3d --check                  # settings ok
```

首次推送后 GitHub 运行 [41783231730](https://github.com/HenryVarro666/2Dto3D/actions/runs/41783231730)：前端作业通过；后端作业在 mypy 步失败（`uv.lock` 未随 dev extra 更新，`.venv/bin/mypy` 不存在）；容器作业在网页构建失败（前端从 `docs/measurement/*.json` 导入冻结记录，而 `.dockerignore` 排除了 `docs`）。两处均为本轮引入的交付缺陷，修复：`uv lock` 仅新增 mypy 及其依赖（干净 `uv sync --frozen --extra dev` 后 mypy 通过）；Dockerfile 的 web 阶段复制 `docs/measurement`，`.dockerignore` 例外该目录，并在本机按镜像目录布局模拟 `npm ci && npm run build` 通过。后续运行结果以 Actions 页面为准。

## 追加：HARDEN-002 令牌认证与完整镜像（同日）

- **SEC-004**：新增可选 `PV3D_API_TOKEN`。纯 ASGI 中间件在路由与请求体解析之前拒绝未认证的 `/api` 调用（401＋`WWW-Authenticate`），`/api/health` 与 `/api/session` 开放；`POST /api/session` 用常量时间比较校验令牌并下发 HttpOnly/SameSite=Strict 的 HMAC Cookie（不含令牌），`DELETE` 退出。网页 `client.ts` 把 401 转成 `AuthRequiredError` 并广播，`AccessTokenPanel` 在顶栏显示登录框（中英西），下载链接随 Cookie 通过。后端新增 8 个测试（设置校验、路由覆盖、Cookie、伪造 Cookie、未认证大上传不解析、无令牌时开放），前端新增 3 个。本机：后端 205 通过、前端 88 通过、mypy/ruff/prettier/tsc 通过。
- **OPS-010**：`Dockerfile` 改为 `WITH_MODELS` 构建参数：`1` 时安装 git、`--extra ml` 与 `services/multiview` 的锁定环境；默认镜像不变。`docker-compose.yml` 与 `.env.example` 加入令牌；CI 容器作业改为用令牌启动并验证 401/404；`container-full.yml` 手动工作流构建完整镜像并导入 `vggt/torch/numpy`。本机用 `uv sync --project services/multiview --frozen` 在 Linux x86_64 验证锁可安装（torch 2.8.0+cu128、numpy 1.26.4），未执行 `docker build`。
- 未改动：令牌为共享密钥、不区分用户、不提供 TLS；公网部署仍需 TLS 终止代理（运维文档已写明）。
