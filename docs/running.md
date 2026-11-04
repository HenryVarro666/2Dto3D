# V3 本地工作台运行说明

保留单图路径：组串式逆变器照片上传 → Grounding DINO 组件候选 → SAM 2 区域 → 参数化结构示意 → 网页查看与 GLB／JSON 导出。V3 新增同设备多图联合几何、组件点云融合及逐图修正。高精单图生成、完整 CAD 和其他设备类别尚未接入。

## 安装与启动

在项目根目录执行：

```bash
make setup
make models
make setup-multiview
make models-multiview
make dev
```

`make setup` 安装锁定的 Python 与前端依赖。`make models` 使用官方模型缓存机制准备 `IDEA-Research/grounding-dino-tiny` 和 `facebook/sam2.1-hiera-tiny`，不上传照片。首次网络下载可能较慢，需要能访问 Hugging Face。

`make setup-multiview` 安装单独锁定的 VGGT 环境（NumPy 1.x），`make models-multiview` 缓存约 5GB 研究权重。单图模式无需此环境。缓存／版本与非商业权重限制见 [V3 模型说明](v3/models.md)。

浏览器打开 `http://127.0.0.1:5173`，API 在 `http://127.0.0.1:8000`。按 Ctrl+C 会关闭此启动器创建的两项服务，不会终止已有端口的其他进程。若端口已有服务，先确认并停止自己的旧实例。

若不使用 Make，也可分别运行：

```bash
uv sync --frozen --extra dev --extra ml
npm --prefix apps/web ci
uv run --extra ml python -m uvicorn pv3d.app:create_app --factory --host 127.0.0.1 --port 8000
```

另一个终端运行：

```bash
npm --prefix apps/web run dev
```

执行 `make build` 后，`make serve` 可以只启动 8000 端口，同时提供静态网页和 API；开发模式有 5173 与 8000 两个服务。

## 多图页面

顶部切换“多角度点云”，选择同一设备 2–8 张不同视角照片，明确点击“融合并识别组件”。相机／深度联合推理完成后逐图检测，再融合和导出 POINTS GLB／PLY／JSON。左侧可切换视角、框选并加正负点；下方可关联同一全局组件或拆开误关联。“应用校正到点云”仅更新点归属，不重复 VGGT。细节与补拍建议见 [拍摄指南](v3/capture-guide.md)。

模式／照片切换在运行或草稿中禁用；语言切换仍可用。两个模式在本次打开后各自保留内存工作区；刷新后不自动恢复整个组，持久结果可经 API 取回。失败保留照片组；几何诊断、无组件或零点组件会提示核对。默认三图 336 已在 MPS 测试，8 图／518 和 RTX 5080 尚未测试。

## 单图页面（保留 V2）

在右上角选择中文、English 或 Español，页面、进度和操作提示即时更新。选择仅保存在当前浏览器的当前站点；5173 开发站点与 8000 构建站点各自记忆。切换语言不重新运行识别，也不清空照片、组件选择、隐藏状态或人工编辑。

1. 选择或拖入 JPEG／PNG／WebP；服务校验真实文件内容并处理 EXIF 方向，最长边缩至 2048。
2. 自动任务运行真实模型。网页显示六阶段进度条、当前步骤和已用时间：上传、准备模型、识别组件、提取区域、构建三维、载入视图。当前阶段持续动画，首次模型加载／下载可能较久；超过十秒仍正常处理，不因时长自动失败。
3. 上传前选择“单设备／多设备”。单设备优先一个主要柜体及其附近支持组件；多设备不应用该筛选，仍受检测召回、去重和最多 12 个自动候选限制。已有结果时切换范围不自动执行，须点击“按当前范围重新识别”；这会以新任务的自动候选替换当前工作区，请先下载需要保留的人工结果。
4. 在三维视图中旋转、缩放、选择；用列表隐藏、隔离组件，或调整爆炸视图后恢复。
5. 对遗漏点击“添加组件框”，在照片拖框进入草稿。SAM 自动细化，选择“保留物体”在框内点目标、“排除背景”点背景；撤销／清空会重新细化。填名称、选类别并“确认区域”，然后“重新生成结构”。已有组件用“编辑 → 细化边界”，沿用组件 ID。草稿可取消、重新框选、失败后重试或“仅用框保存”，不会自动假设模型成功。
6. 下载当前结果 GLB 或 JSON。GLB 导出保持原始布局，不保存查看器的临时爆炸偏移。

人工校正后重建会改为三阶段进度，不显示未执行的模型识别。停止等待或失败后保留最近阶段；“停止等待”只停止浏览器等待，后端可能继续处理。未识别到有效组件进入待确认，查看器加载失败也不会显示进度全部完成。分割关闭或不可用时，区域步骤标为“仅候选框”。

边界细化草稿单独显示“正在等待或细化边界”和已用时间；它不提供模型内部百分比。快速加点会合并等待中的修改，旧响应不能确认覆盖新点。取消或更换照片会停止等待，已排队的服务计算可能继续；单 worker 保证不同时占用推理设备。修改名称／类别或切换语言不重复分割。确认区域保留完整 PNG，简化多轮廓用于 JSON；结构生成仅使用可见区域的外接框和类别先验，掩码孔洞不会自动成为三维开孔。

## 配置

使用 shell 环境变量，例如 `PV3D_DEVICE=cpu make dev`。

| 变量 | 默认 | 作用 |
| --- | --- | --- |
| `PV3D_DEVICE` | `auto` | `cuda` 优先，其次 `mps`，否则 `cpu`；也可显式指定。自动识别的 MPS 失败会尝试 CPU；交互细化失败则保留草稿和仅框选项，可改用 CPU 重启。 |
| `PV3D_SEGMENT` | `1` | `0` 仅跳过自动识别的 SAM，保留真实候选框；不禁用用户主动发起的边界细化。 |
| `PV3D_SAM_SIZE` | `tiny` | `tiny`／`small`／`base-plus`／`large`，只能选允许的固定 checkpoint revision；影响自动分割和交互细化。服务重启生效，大模型需另行下载。 |
| `PV3D_MODEL_DIR` | `models/huggingface/` | API 模型缓存目录。CLI 可用 `--cache-dir` 指定同一目录。 |
| `PV3D_DATA_DIR` | `data/runtime/` | SQLite、规范化图片和每个任务产物；保持在本机。 |
| `PV3D_MULTIVIEW_DEVICE` | 继承 `PV3D_DEVICE` | 多图 `auto/cuda/mps/cpu`；auto 优先 CUDA、其次 MPS。 |
| `PV3D_VGGT_SIZE` | `336` | 多图输入 `224/336/518`，启动时固定。更高分辨率消耗更多内存，未承诺更好。 |
| `PV3D_MULTIVIEW_PYTHON` | `services/multiview/.venv/bin/python` | 隔离 VGGT 环境的 Python 可执行文件。 |
| `PV3D_API_URL` | `http://127.0.0.1:8000` | 仅 Vite 开发代理目标，可用于独立测试端口；生产同源服务不需要。 |
| `PV3D_TORCH_THREADS` | `4` | PyTorch CPU 线程数。 |
| `PV3D_HOST` / `PV3D_PORT` | `127.0.0.1` / `8000` | `python -m pv3d` 的绑定地址与端口；非回环地址会打印警告。 |
| `PV3D_LOG_LEVEL` / `PV3D_LOG_FORMAT` | `INFO` / `text` | 日志级别与格式（`text`/`json`），含每请求访问日志与 `X-Request-ID`。 |
| `PV3D_CORS_ORIGINS` | 空 | 允许跨域的浏览器来源列表；为空仅同源。 |
| `PV3D_MAX_PENDING_JOBS` | `8` | 排队＋运行中任务上限，满时返回 409。 |
| `PV3D_MULTIVIEW_TIMEOUT_S` | `1800` | 单次 VGGT worker 硬超时（秒）。 |
| `PV3D_REFINE_TIMEOUT_S` | `300` | 交互细化等待推理 worker 的上限（秒），超时返回 503。 |
| `PV3D_API_TOKEN` | 空 | 设置后 API 需要 Bearer 令牌或登录 Cookie；网页出现登录框。 |
| `PV3D_SESSION_MAX_AGE_S` | `43200` | 登录 Cookie 有效期（秒）。 |

生产部署、健康检查、日志、目录锁与容器见[部署与运维说明](operations.md)。

本轮 M4 Pro 为 24GB 内存；已执行 MPS 真实模型调用。5080 尚未接入测试，不能据此宣称其延迟或环境可用。GPU 机器的系统／驱动和服务部署方式见 [硬件方案](hardware.md)。

## 测试与复现

```bash
make lint
make typecheck
make test
make build
```

`make check` 依次执行以上四项，与 CI 相同。

常规 Python 测试用可控检测结果替代慢模型边界，实际校验上传、SQLite、队列、错误和 GLB；前端测试校验轮询、过期响应、编辑和组件状态。它们不证明真实识别精度。真实模型的本地调用可以单独执行：

```bash
uv run --extra ml python -m pv3d.perception photos/string_inverters/candidate_energetica_sg250hx.png
```

这里的候选照片不在 Git 中；新克隆请使用自己的图片。两张现有样图不是独立测试集，重复运行也不能当作新增独立样本。模型版本、设备、冷启动状态与分阶段耗时记录在结果 JSON；浏览器首个三维可交互时间还包括上传、轮询和渲染，不能用单次模型耗时替代。

识别权重按适配器中的固定 Hugging Face revision 加载，DINO 与 SAM 2 的版本均写入结果。更换 checkpoint 需要单独验证并更新版本记录，不能只替换目录里的权重文件。

例如 `PV3D_SAM_SIZE=base-plus make models` 先缓存所选 SAM，再用 `PV3D_SAM_SIZE=base-plus make dev` 启动相同配置。此开关不更换 Grounding DINO，不会自动提高漏检召回。当前只实测了 tiny，其余大小提供配置接入，未完成实机验证。选型、环境要求与比较方法见 [V2 模型说明](v2/model-options.md)。

## 多图常见问题

- 未安装／模型失败：先执行两个 multiview setup／models 命令，查看本地 `data/runtime/multiview/<job-id>/worker.log`；多图 worker 不静默制造替代结果。
- 相同照片被拒绝：选择有视差的真实不同视角，不用复制件／裁剪件充数。
- 融合差、线缆缺失：补拍有重叠的近照、避免纯旋转／移动物体，保持图像清晰。默认336细线可能不足一个像素；大 SAM 仅改善掩码。
- 内存不足：先使用2–3张／224，重启时显式选择 `PV3D_MULTIVIEW_DEVICE=cpu` 也可尝试，但速度未测。
- 有背景但无语义：点云仍可查看，在各张照片手动补框；真实类别必须核对。

## 单图能力边界

识别结果是开放词表模型的候选，仍可能把邻近结构当作安装件；需要人工核对。SAM 2 区域可改善可见边界，但三维箱体、杆件和线缆束的深度来自类别先验，不是从照片测量。三根示意线只表达线缆束，不表示真实数量或布线。参数化几何保持相对尺度，没有毫米测量或内部结构恢复。

本地任务采用单 worker 和有界队列；满载返回明确状态。服务重启会把未完成任务标为中断，初版通过新任务重试，不自动恢复 GPU 推理。当前没有身份认证、云端托管或多人协作部署，服务默认只监听本机地址。

下一阶段见 [设备扩展路线](roadmap.md)，一期设计见 [计划书](plan.md)。

多语言维护和名称／导出边界见 [多语言说明](i18n.md)。

## 已知长度标定与无模型演示

按 [README](../README.md#先运行不下载模型的演示) 创建解析点云，再按脚本 Job ID 恢复。此流程只需 `uv sync --frozen --extra dev` 和前端依赖，不下载/调用模型。`.venv/bin/python scripts/measurement_demo.py --evaluate` 追加记录，不覆盖历史；不要使用缺少 FastAPI 的系统 Python。

真实多图结果也能选点/标定/验证。GLB/PLY 不改变，测量 JSON 单独下载；详见[测量指南](measurement/README.md)。来源、备注、ID 与数值不随界面语言改写。

启动前指定 `PV3D_DATA_DIR`；不同目录有不同任务和测量历史。克隆不复制 ignored 数据库/照片/GLB，继续同一实验需停止写入后私下迁移完整运行目录。测量 JSON 不能独自重建场景。

并行开发可用 `PV3D_API_URL=http://127.0.0.1:8002 npm --prefix apps/web run dev -- --port 5175 --strictPort`，API 另用 uvicorn `--port 8002`，保留其他会话的 8000/5173。生产检查 `make build` 后 `make serve`。本次 Three.js 独立 bundle 超过 Vite 500 kB 提示阈值，构建成功；未隐藏提示，也未据此声称加载性能合格。
