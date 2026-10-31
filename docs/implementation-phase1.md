# 一期网页工作台实现计划

> **For agentic workers:** Use test-driven-development for behavioral boundaries, execute the approved design without a further confirmation gate, and review the whole change before GitHub synchronization.

**Goal:** 在指定项目根目录跑通照片上传、真实组件识别和有独立组件的三维结构示意网页。

**Architecture:** React／Three.js 网页调用 FastAPI；SQLite 保存上传与任务，单 worker 执行识别和 Trimesh 场景导出。真实 Grounding DINO 提供候选框，SAM 2 可进一步给区域；模型未就绪或无识别时明确报状态并允许人工框选，禁止固定零件冒充识别。

**Tech Stack:** Python 3.12、FastAPI、Pillow、Trimesh、PyTorch／Transformers；React、TypeScript、Vite、Three.js。

**Spec:** [项目方案](plan.md)、[硬件约束](hardware.md)、[扩展方向](roadmap.md)。

## Global constraints

- 一期限定组串式逆变器及外部安装结构；单图优先。
- 首个可旋转结构示意的 10 秒是待测目标，计入上传与加载；冷启动另报。
- 本轮获准搭建并同步 GitHub；用户指定当前根目录，使用当前目录的功能分支，避免把运行数据迁出。
- 原始照片、权重、SQLite 和生成 GLB 不入 Git。所有示意几何标相对尺度、未标定。
- 输入检测框和区域是识别候选，几何深度来自先验；完整真实 BOM 与后台生成式高精模型不属于本次切片。

## Review focus

- 坏文件、伪后缀及超限图片：上传验证后才持久化，不返回任意文件路径。
- 没有识别到组件／模型不可用：保留原图和可操作错误，不能生成固定假零件。
- 原图方向与归一化框：EXIF 先归一化；坏框、NaN、越界参数被拒绝。
- 任务中断与切换照片：状态可追溯，前端不把旧结果套给新照片。
- GLB 导出与联动：组件节点有稳定 ID，隐藏／爆炸不篡改原始导出位姿。

## Task 1：服务、持久化和几何（API owner）

Files: `services/api/src/pv3d/{app,schemas,store,geometry}.py`、`services/api/tests/test_api.py`、`test_geometry.py`。

Consumes: `GroundingDetector.detect(PIL.Image) -> Recognition dict`（见下方契约）；目录由环境 `PV3D_DATA_DIR` 控制，默认根 `data/runtime`。

Produces: `/api/assets`、`/api/jobs`、任务状态和结果、规范化照片、场景 GLB／JSON，详见 [API 契约](api-contract.md)。

- [x] 写上传／错误／重启状态／独立 GLB 节点测试，先运行并观察缺失行为失败。
- [x] 实现图片验证、SQLite、单任务执行、参数化布局及导出。
- [x] 跑完整后端测试；用可控检测结果测试外部模型边界，保留真实文件与数据库操作。

## Task 2：网页工作台（Web owner）

Files: `apps/web/**`。

Consumes: [API 契约](api-contract.md)，Vite `/api` 代理到 127.0.0.1:8000。

Produces: 照片上传、原图候选框、组件列表、真实 GLB 的点选／隐藏／隔离／爆炸／恢复、导出与人工纠正重建。

- [x] 先测试上传后的任务轮询、错误和组件交互行为。
- [x] 实现自适应双视图工作台，保持明确的示意、来源、相对尺度和模型状态提示。
- [x] 运行前端测试与 TypeScript／生产构建；网页端实际检查 WebGL、文件上传和当前窄屏布局。

## Task 3：真实识别与运行集成（root owner）

Files: `services/api/src/pv3d/perception.py`、`services/api/tests/test_perception.py`、`scripts/`、`Makefile`、根依赖与说明。

Produces: Grounding DINO tiny 真实推理、可选 SAM 2 tiny 区域，显式设备／版本／来源和失败状态；可重复启动命令。

- [x] 先测试候选去重、类别映射和归一化边界，运行观察失败。
- [x] 实现懒加载、项目内权重缓存、CPU／MPS／CUDA 选择和模型状态。
- [x] 在已有样图上运行真实模型、HTTP 到 GLB 全流程，记录观测限制和冷／暖时间，不宣称跨设备准确率。
- [x] 完成浏览器验证、全分支审查、文档更新；提交推送并核对远端。

## Execution record

- Baseline: docs-only repository, clean at `8c0b363`; no pre-existing application tests.
- Ruling: 当前目录功能分支 `feat/phase1-workbench`，遵循用户明确指定代码和数据根目录。
- Ruling: 本地网页平台是一期入口，Python 推理服务保留 GPU 迁移边界；本轮不创建云端 Site。
- Backend: witnessed red, full local Python suite 34 passed. Web: witnessed red, 18 passed and production build passed.
- Browser: real upload / GLB render / selection / visibility / explosion / rotation / manual provenance / download verified; notes in [verification](verification.md).
- Ruling: 本切片人工编辑为名称、类别及照片框；直接编辑三维厚度／位姿留待后续，不能标为已实现。
- Independent whole-branch review returned three functional findings. All reproduced and fixed: freeze mutation during rebuild, reserve a private scene root, clear stale health error after recovery. Regression suites passed.
