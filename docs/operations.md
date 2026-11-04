# 部署与运维说明

本页描述把工作台作为长期运行服务时需要的配置、健康检查、日志、队列和升级规则。它不改变 V3 的识别/几何行为，也不代表任何精度承诺；精度与实验证据仍以[质量交接](quality/README.md)为准。开发模式仍用 `make dev`。

## 启动入口

```bash
uv sync --frozen --extra dev --extra ml     # 需要模型时加 --extra ml
npm --prefix apps/web ci && npm --prefix apps/web run build
.venv/bin/python -m pv3d --check            # 校验环境变量，不绑定端口
.venv/bin/python -m pv3d                    # 读取 PV3D_* 变量，提供 API 与已构建网页
```

`python -m pv3d` 是唯一推荐的生产入口：它先校验设置、配置日志，再启动 uvicorn；`--host/--port` 可临时覆盖变量。`make serve` 等价于它。`uvicorn pv3d.app:create_app --factory` 仍可用，但不会校验设置、不输出结构化日志。

## 环境变量

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `PV3D_HOST` / `PV3D_PORT` | `127.0.0.1` / `8000` | 绑定地址。服务没有认证；绑定非回环地址时启动会打印警告，必须放在带认证的反向代理之后。 |
| `PV3D_LOG_LEVEL` / `PV3D_LOG_FORMAT` | `INFO` / `text` | `json` 时每行一个 JSON 对象，含 `request_id`、`method`、`path`、`status`、`duration_ms`。 |
| `PV3D_CORS_ORIGINS` | 空 | 逗号分隔的浏览器来源；为空时只允许同源。 |
| `PV3D_DATA_DIR` / `PV3D_MODEL_DIR` | `data/runtime` / `models/huggingface` | 状态目录与模型缓存，见下文。 |
| `PV3D_MAX_PENDING_JOBS` | `8` | 排队＋运行中的推理任务上限（1–64）；满时 API 返回 409。 |
| `PV3D_MULTIVIEW_TIMEOUT_S` | `1800` | 单次 VGGT worker 的硬超时；超时任务标记失败并说明原因。 |
| `PV3D_REFINE_TIMEOUT_S` | `300` | 交互细化等待单 worker 的上限；超时返回 503，排队的细化会被取消并释放名额。 |
| `PV3D_DEVICE` 等 | 见[运行说明](running.md#配置) | 模型设备、SAM 大小、线程数等原有变量不变。 |

无效值会在启动时报错并指出变量名（退出码 2）。`.env.example` 列出全部变量。

## 一个数据目录只能有一个服务

启动时在 `PV3D_DATA_DIR/server.lock` 取独占文件锁（`flock`）。第二个进程会立即退出（退出码 3）并提示占用者的 PID；否则两个进程会互相把对方正在运行的任务标记为“中断”。进程崩溃时内核自动释放锁，不需要手动删除锁文件。基准脚本直接打开 `Store` 不受此锁影响。

## 健康检查与队列

`GET /api/health` 返回：

```json
{"status": "ok", "version": "3.0.0", "model": {...}, "multiview": {...},
 "queue": {"max_pending": 8, "in_flight": 1, "available": 7}}
```

`status` 只说明 HTTP 服务可用；模型是否加载在 `model.state`。容器 `HEALTHCHECK` 与反向代理探活都应使用此端点。`queue.available` 为 0 时新任务返回 409，不排队无限增长。

## 请求关联与响应头

每个响应带 `X-Request-ID`（客户端传入的 1–128 位安全字符会被沿用，否则生成），访问日志同名字段可直接关联。所有 `/api` JSON 响应带 `Cache-Control: no-store`，全部响应带 `X-Content-Type-Options: nosniff` 与 `Referrer-Policy: same-origin`。上传在解析 multipart 之前先按 `Content-Length` 拒绝超过 20 MB 的请求（413），缺少长度返回 411。

## 优雅关闭与中断语义

收到停止信号后，正在运行的任务会完成并保存，排队任务被取消并在数据库中标记为 `interrupted`（与崩溃重启后的处理一致），客户端收到明确错误。关闭期间新的提交返回 503。VGGT worker 子进程在超时或关闭时被终止，不会残留。

## 数据目录、备份与升级

`PV3D_DATA_DIR` 下：`state.sqlite3`（WAL 模式）、`assets/`（规范化 JPEG 与原始上传字节）、`jobs/`、`refinements/`、`multiview/`。备份需停止服务后整目录复制；WAL 文件 `-wal/-shm` 随目录一起复制。数据库记录 `PRAGMA user_version`，比当前版本新的目录会拒绝启动，避免旧代码写坏新格式。原始上传字节保留 EXIF 等元数据，仅对外提供去除元数据的规范化图片；若不希望保留原始字节，请在备份策略中单独处理。

## 容器

`Dockerfile` 构建“无模型”的 API＋网页镜像（默认非 root 用户、健康检查、JSON 日志）；`--build-arg UV_EXTRAS=ml` 加入识别依赖。VGGT 的隔离环境不在镜像内，多图重建需要额外挂载 `services/multiview/.venv` 与模型缓存，或在镜像外运行。本轮未在本机执行 `docker build`（环境无 Docker 守护进程），CI 的 `container` 作业在 GitHub 上构建并探活。

## 检查命令

```bash
make lint        # ruff（后端）+ prettier（前端）
make typecheck   # mypy（后端）+ tsc（前端）
make test        # pytest + vitest
make check       # 以上全部加生产构建
```

CI 的后端/前端/容器三个作业与 `make check` 一致；`pre-commit install` 后本地提交也会执行 lint 与类型检查。
