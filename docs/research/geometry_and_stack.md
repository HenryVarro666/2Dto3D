# 户外光伏设备照片转三维：几何边界、系统栈和验收研究笔记

检索日期：2026-10-30。用途：给总计划提供技术依据，当前不实施、不训练。收到的最新范围是野外光伏电气设备及其支撑结构照片，期望类似 Blender 的旋转查看与零件组成展示；具体设备名称、拍摄方式、硬件和速度目标待确认。以下“建议/推断”是本项目的设计判断，不代表已验证效果。

## 1. 单张照片能恢复什么，真实多视角怎样作为可选增强？

### Takeaway

主入口继续接受一张照片，首版聚焦用户选中的一台设备的外部可见组件。单图可做识别、分割、近似外形和基于先验的补全；真实多视角才增加来自新观测的约束，合成视角、背面补全、参数化模板都必须保留各自来源，不能升级为实测几何。[OpenCV 投影模型](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)、[COLMAP 教程](https://colmap.github.io/tutorial)

### Cited Findings

- COLMAP 的传统路线是 SfM 恢复相机与稀疏点，再由 MVS 估计深度/法线、融合稠密点云，并可网格化。官方拍摄建议包含足够纹理、相近光照、避免高光、足够重叠，以及真正改变相机位置；建议每个对象至少出现在三张图中。[COLMAP 教程](https://colmap.github.io/tutorial)
- VGGT 可从一张或多张真实输入图预测相机参数、点图、深度和轨迹，并可导出 COLMAP 格式，选择加入 bundle adjustment。它不是“输入多图就自动得到可编辑零件装配体”的承诺。作者明确解释其采用 normalized prediction，不能直接把数值当毫米。[官方仓库](https://github.com/facebookresearch/vggt)、[作者在 issue #56 的答复](https://github.com/facebookresearch/vggt/issues/56)
- 时效信息：VGGT 官方仓库在 2026-05 公告 VGGT-Ω，其项目页声称改善精度和效率；本项目尚未在目标照片比较两者。原始 VGGT 权重仍非商用，README 指定的 VGGT-1B-Commercial 是另外的商用权重，不能混写许可。[VGGT 仓库](https://github.com/facebookresearch/vggt)、[VGGT-Ω 官方项目页](https://vggt-omega.github.io/)
- OpenCV 的透视模型是 `s p = K [R|t] P`。从该式可直接推出，在相机相对平移与所有三维点同时缩放时，图像投影不变。因此仅有相机内参并不能自动消除未知物体的绝对尺度不确定性。[OpenCV 相机标定与三维重建](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
- 单应性描述两个平面的映射。ArUco 的已知角点、实际边长和相机标定可用于 `solvePnP` 估计标记相对相机的位姿，平移单位跟随输入的边长单位。这并不直接提供其他未知物体上每一点的深度。[OpenCV 单应性](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html)、[ArUco 官方教程](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html)
- 薄、反光的物体是 RGB-D 和 MVS 已被论文明确讨论的困难对象；NeRF 在这些物体上较好的新视角合成不等于已证明尺寸可用。[NeRF-Supervision，作者论文摘要](https://arxiv.org/abs/2203.01913)
- 原始 3D Gaussian Splatting 以三维高斯和视角相关外观表达场景，目标是新视角渲染；它从标定得到的稀疏点开始优化。该表达与三角网格、参数化 CAD 是不同交付物。[3DGS 官方项目页](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
- CadQuery 支持 STEP、glTF 等导出，但官方说明完整参数化源是其 Python 模型；交换文件不会保留完整参数化程序。一个看起来完整的生成网格不能因此直接称为可制造 CAD。[CadQuery 导入导出](https://cadquery.readthedocs.io/en/latest/importexport.html)

### Inferences

- **单图主线**：用户先点选或框选一台设备，再识别外部组件、显示二维证据和近似三维结果。外壳、盖板、支架等类别只是待领域确认的例子。内部元件、背面的连接件、隐藏的螺栓数以及具体型号，默认 unknown；不能从“典型设备通常有”直接写入真实零件清单。
- **快速预览与重建结果分开**：第一批结果可以是二维类别/掩码和盒体、杆体等低细节占位，以便立即交互；必须显示“占位模型，尚未完成重建”。重建网格异步到达后替换。不得把一个先造好的立方体计作单图重建成功。
- **真实多视角增强**：如果用户允许额外照片或视频，再独立测试 COLMAP 与 VGGT 系列。前者提供传统优化基线；后者提供学习式几何候选。两者都需要本场景验证，不保证对室外金属柜体、重复栅格、细电缆和遮挡有效。不能把额外拍摄变成满足单图需求的前置条件。
- **合成视角**：从同一张照片生成的背面只增加模型先验，不增加独立测量。可用于展示候选形状或网格生成；在数据、界面、评测中写明 synthetic / inferred，不能与实拍视角合并计算“观测覆盖”。这是基于成像约束的推断。[OpenCV 投影模型](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
- **尺度条件**：没有外部尺度时，只提供相对比例；有已知尺寸且可定位的物理参照，可给整体重建做尺度对齐，但前提是该参照和目标在同一可靠重建中，尺度估计无局部变形。单图标尺或平面 ArUco 可支持参考平面上的测量；目标离开该平面后，不能直接沿用同一个像素/毫米比例。即使相机位姿已知，未知像素对应的空间点仍位于一条射线上，还需要目标平面、深度或已知几何等约束。[单应性定义](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html)、[投影模型](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
- **采集控制建议**：在可操作范围内使用清晰近照、稳定曝光、较柔和光照、有重叠的不同视角；框选目标并屏蔽天空/大面积背景。细杆、线缆、薄板边缘和高光区域单独记录失败原因。不会把遮挡补洞、表面平滑后的形状自动视为真实观测。
- **输出选择**：首版优先显式网格 GLB + 独立组件清单，支持选中、高亮、隐藏、隔离和拆开展示。3DGS/NeRF 只在“场景外观浏览”确有需求时增加；CAD 则另设模板拟合与人工尺寸校核阶段。零件归属是额外语义任务，网格连通块不天然等于机械零件。

### Gaps

- 没有用户样例，不能确认是逆变器、变压器、配电柜、组件支撑件还是混合场景；不能先把“光伏变电气”改写为某个已确定设备。
- 没有相机标定、尺寸真值或设备 CAD，不承诺毫米级精度；材料、壁厚、螺纹、内部结构和电气连接关系均不能仅靠外观可靠确定。
- VGGT-Ω 尚未在本项目测试；本文只说明存在这一当前候选，不认定其在目标领域优于已有方案。最新许可须针对最终选定代码和 checkpoint 再逐项固定。

## 2. 怎样用小型系统支撑交互式组件分析和异步三维细化？

### Takeaway

建议一个 Python API、一个独立模型进程、一份本机 SQLite 和文件目录，再配 React/Three.js 查看器。先让“任务状态、证据、组件 ID、模型版本、导出”连通，GPU 推理由适配器替换，不默认引入集群和多套队列。[FastAPI 功能](https://fastapi.tiangolo.com/features/)、[Trimesh 文档](https://trimesh.org/)、[React Three Fiber](https://r3f.docs.pmnd.rs/getting-started/introduction)

### Cited Findings

- FastAPI 基于 Python 类型声明、OpenAPI 与 JSON Schema，适合明确输入输出契约；Pydantic 支持类型注解驱动的校验/序列化、JSON Schema 和 strict mode。[FastAPI 官方](https://fastapi.tiangolo.com/features/)、[Pydantic 官方](https://docs.pydantic.dev/latest/)
- FastAPI 官方把重计算与简单后台小任务区分开，说明重计算可使用独立任务工具。Huey 的 SqliteHuey 使用标准库 sqlite3 存储队列及结果，提供 durable-write 选项；其任务 API 支持重试。[FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)、[Huey API](https://huey.readthedocs.io/en/latest/api.html#SqliteHuey)
- Trimesh 提供网格分析、连通体拆分、边界盒、GLB/glTF 导出；其文档特别提醒，直接 `load_mesh` 可能把多网格实例不可逆地合并，需要保留场景时应使用 `load_scene`。`export_glb` 接受 Scene 导出二进制 glTF。[Trimesh 主文档](https://trimesh.org/)、[glTF 导出 API](https://trimesh.org/trimesh.exchange.gltf.html)
- Open3D 提供三角网格、点云及几何管线，其网格教程明确提供 manifold、自相交、watertight、orientable 检查。[Open3D 网格教程](https://www.open3d.org/docs/release/tutorial/geometry/mesh.html)
- R3F 是 Three.js 的 React renderer；官方目前提醒它的 major 版本需与 React 对应。Three.js GLTFLoader 支持 glTF 2.0。[R3F 官方](https://r3f.docs.pmnd.rs/getting-started/introduction)、[GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html)
- glTF 使用米作为线性单位、支持节点层级和 application-specific extras；name 是可选的显示名称，规范不保证唯一。[Khronos glTF 规范](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
- PyTorch 提供 CUDA 安装路径及 macOS MPS 后端；MPS 的存在不等于每个研究模型或自定义 CUDA 扩展可直接运行在 Mac。COLMAP 官方 FAQ 说明无 CUDA 时可以进行许多 CPU 操作，但内置稠密重建受 GPU 支持条件限制。[PyTorch 安装](https://pytorch.org/get-started/locally/)、[MPS 文档](https://docs.pytorch.org/docs/stable/notes/mps.html)、[COLMAP FAQ](https://colmap.github.io/faq.html)

### Inferences

**建议模块及责任，不是已安装的软件清单：**

| 模块 | 建议 | 边界 |
|---|---|---|
| 浏览器界面 | React + TypeScript + Three.js；团队熟悉 React 时使用 R3F | 上传、框选目标、显示阶段状态、2D/3D 组件联动；不在浏览器运行大型三维模型 |
| API/契约 | Python + FastAPI + Pydantic | 文件校验、任务创建、结果版本、纠错；模型推理不阻塞请求处理 |
| 模型适配 | 独立 PyTorch worker，统一 adapter 输入输出 | 分开 perception、single-image geometry、optional captured-multiview；记录 checkpoint/配置/许可 |
| 几何处理 | OpenCV + Trimesh；确需点云/配准/拓扑检查时加 Open3D | 不让两个库重复承担同一处理步骤；不把 mesh repair 等于真实性修复 |
| 任务和持久化 | SQLite jobs 表 + 单 worker；想复用任务工具时用 SqliteHuey | 先串行 GPU 任务，存阶段和可恢复状态；Huey 可选，不必默认 Redis/Celery |
| 文件 | 本机 input / intermediate / artifact 目录，数据库仅存路径/哈希/元信息 | 初期不用向量库或独立对象存储；网络部署时再按规模迁移 |

这些是基于上表官方能力的工程选择；需要实现时再锁定经测试的版本，避免拼接“最新版本”造成依赖冲突。

**部署选择：**

- CPU/Mac 可先完成上传、API、任务状态、人工组件标注、占位/模板装配体、GLB 查看与结果回放。MPS 仅作为通过模型兼容性和延迟实测后的可选运行后端。
- 完整重模型推理优先试一台 Linux + NVIDIA GPU，把 API、worker、数据库及文件目录放在同一主机；Mac/其他机器通过浏览器或 HTTP 访问。不要让两台主机通过网络文件共享直接并发使用同一 SQLite 文件。
- 尚不知用户硬件，不写具体 GPU 显存门槛或“10 秒可完成”。模型、图像分辨率、视角数和后处理决定内存与时延，先用短名单模型做一组实测。
- 一台机器用一个任务进程也要持久化状态：任务有 attempt、started_at、heartbeat_at、error_code，进程退出后将过期 RUNNING 标为 INTERRUPTED 并允许重试。输出先写临时目录再原子提交，按 job/config/input hash 去重；不声称队列天然提供 exactly once。

**最小 API 草案：**

```text
POST /assets                         上传照片，返回 asset_id 与校验结果
POST /jobs                           asset_ids、target_bbox/mask、mode、可选 reference
GET  /jobs/{id}                       state、stage、progress、warnings、preview_url
GET  /jobs/{id}/result                components、geometry、evidence、artifact URLs
PATCH /jobs/{id}/components/{part_id}  用户修正名称/类别/归属；保留修订版本
POST /jobs/{id}/cancel                请求取消；worker 在阶段边界检查
```

`mode=single_image` 是主路径；`captured_multiview` 必须显式选择并验证输入确为同一目标的实拍。初期 polling 即可，不默认上 WebSocket。

**最小结果契约草案：**

```json
{
  "job_id": "...",
  "schema_version": "1",
  "mode": "single_image",
  "state": "SUCCEEDED_WITH_WARNINGS",
  "representation": "reconstructed_mesh",
  "model_manifest": [{"adapter": "...", "checkpoint": "...", "config_hash": "..."}],
  "geometry": {
    "artifact_glb": "...",
    "coordinate_unit": "m",
    "display_normalized": true,
    "metric_scale_status": "unknown",
    "scale_source": null
  },
  "components": [{
    "part_id": "part_001",
    "label": "外部组件候选",
    "class_status": "unverified",
    "node_ids": ["component_part_001"],
    "mask_asset_id": "...",
    "geometry_evidence": "inferred_from_single_view",
    "evidence_asset_ids": ["photo_001"],
    "confidence_raw": null,
    "dimensions": null,
    "review_required": true
  }],
  "warnings": ["UNKNOWN_METRIC_SCALE", "UNOBSERVED_BACK_SURFACE"]
}
```

- `representation` 至少区分 `placeholder` / `reconstructed_mesh` / `template_fit` / `radiance_field`。`geometry_evidence` 可按组件或面区分 `observed_multiview` / `inferred_from_single_view` / `template_prior` / `manual`，证据数组保留原图 ID 与像素区域。混合来源不能压成单个“准确率”。
- glTF 的坐标单位按规范用米，但无实尺度时只是用于显示的归一化坐标，`metric_scale_status=unknown`、`display_normalized=true` 且 dimensions 为 null；界面关闭毫米测量，不能把“坐标单位是米”误写成“尺寸真实”。获得可靠尺度后记录变换、参照和验证误差。[glTF 单位规范](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
- 节点命名可读，但业务 ID 使用 `part_id` 和 extras/外部 manifest 绑定；不能依赖 glTF name 唯一。导出保持装配层级，单独测试重载后 ID、变换、可选中性和单位。[glTF 节点和名称](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
- `confidence_raw` 是模型原始分数，不冒充校准概率；名称可信度、分割可信度、几何来源、尺度证据、人工复核状态分别存储。尺寸每一项都带 measurement_basis，不能用一个全局“可信”标记覆盖所有部件。
- 状态可用 `QUEUED → VALIDATING → ANALYZING → PREVIEW_READY → RECONSTRUCTING → EXPORTING → SUCCEEDED/SUCCEEDED_WITH_WARNINGS`；分支有 `NEEDS_INPUT`、`FAILED`、`CANCELLED`、`INTERRUPTED`。预览已出但网格失败时保留预览，明确两者状态。
- 失败码建议：INVALID_IMAGE、TARGET_NOT_FOUND、LOW_RESOLUTION、NO_FOREGROUND_MASK、INSUFFICIENT_VIEW_OVERLAP、POSE_ESTIMATION_FAILED、GPU_OOM、TIMEOUT、EMPTY_GEOMETRY、INVALID_MESH、EXPORT_FAILED。尺度未知、背面未观测是结果限制，不应一概当作系统失败。

### Gaps

- 还未确认用户要独立网站、桌面工具、Blender 插件还是仅有 Blender 类似的操作体验。本笔记给的是可独立验证的服务与查看器基础；不提前锁定插件开发。
- 没有现有机器清单和网络/数据部署约束；不假设用户有 Mac GPU、Linux 服务器或某一显卡。
- GLB 组件层级的实际保留和用户点选体验需要端到端导出/重载验证；官方支持格式不等于本项目接口已正确实现。

## 3. 在自定义训练前，最小数据、里程碑和验收怎样设定？

### Takeaway

先做代表性设备的无训练可运行基线，再按实际失败类型决定是否训练。验收同时覆盖组件、可见几何、不可见补全、真实尺寸和端到端时延，防止用“画面漂亮”替代零件正确或尺寸正确。[Open3D 网格检查](https://www.open3d.org/docs/release/tutorial/geometry/mesh.html)、[scikit-learn 分组切分](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html)

### Cited Findings

- scikit-learn 的 GroupShuffleSplit 按给定 group 切分，test_size 指的是 group 的比例/数量而非图片比例。这提供了实现“整台物理设备或整次采集留出”的现成机制。[官方文档](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html)
- 网格有 manifold/watertight 等可检验属性，但这些属于拓扑和几何有效性，不能证明对目标的重建误差；COLMAP 也提示 Poisson 在噪点和大洞下可能生成差的表面。[Open3D](https://www.open3d.org/docs/release/tutorial/geometry/mesh.html)、[COLMAP FAQ](https://colmap.github.io/faq.html)
- VGGT 仓库明确把模型推理与点云可视化耗时分开，后者可能更久。因此论文或仓库中的模型运行时间不能直接当应用端到端响应承诺。[VGGT 可视化说明](https://github.com/facebookresearch/vggt#interactive-demo)

### Inferences

**建议的短里程碑和依赖门槛：**

| 里程碑 | 产物 | 前置依赖与通过条件 |
|---|---|---|
| M0 范围/数据试采 | 选一类设备、外部组件词表、少量代表性照片、人工标注规则 | 确认单图/可多图、最终输出与可接受速度；不以全光伏场景为一期 |
| M1 交互和证据闭环 | 上传、框选、2D 标签/掩码、明确标记的占位模型、组件联动 | 可用固定样例/人工标注验证契约，页面不得声称占位完成重建 |
| M2 无训练几何基线 | 单图适配器、网格 GLB、异步阶段状态、证据与尺度标记 | 用真实照片完成一次端到端路径；记录失败、内存和时延 |
| M3 组件化和对照评估 | 命名子网格、人工修正、可选多实拍视角对照、盲测表 | 对象级留出，不用演示样例代替测试；保留单图基线 |
| M4 决策 | 确定上线试用、补数据、换模型、模板拟合或定向训练 | 仅当某项明确误差是瓶颈且有足够标签时再训练；不默认从头训练大模型 |

M1 可以先独立推进，M2/M3 的质量与速度不能在没有用户样例、硬件和模型测试时保证。排期应在 M0 确认后给估算，不把经验天数写成承诺。

**最小数据建议，属于试验规模而非训练充分性结论：**

- 先请求 10–20 张有代表性的现成照片做错误剖析，涵盖远/近、正/侧、遮挡、强光或阴影、细部是否可辨。每张记录物理设备 object_id、场站/采集 session_id、拍摄方式和标注来源。若都来自同一台设备，只能说明该设备上的可行性。
- 正式小型评测可从约 20–40 个独立物理目标开始，按类别覆盖所选范围；其中预留不参与提示词、阈值和模型选择的对象。这里的数量是预算友好的起点，不是统计精度或模型训练样本量保证。
- 对愿意补拍的一小部分相同目标，采一圈有重叠的照片或短视频来比较单图与多视角；帧数先做小样本资源试验后定，不把补拍设为单图主路径必需条件。尺寸评测另准备经过量具或可信 CAD/扫描验证的关键尺寸。
- 同一物体的相邻视频帧、不同角度、合成视角、裁剪图与增强图必须在同一个 split 内。若关心跨站泛化，再留出 site/session；若只测已知型号的实例，要明确不能推断到未见型号。提示词与模板调优也视作开发过程，最终测试集保持封存。

**验收矩阵建议：**

| 维度 | 需要的真值与指标 | 必须报告的边界 |
|---|---|---|
| 分类/识别 | 外部组件词表；precision/recall、每类 F1、unknown/拒识和混淆表 | 类别名称与具体型号分开；未知不能硬分 |
| 数量 | 可见实例人工计数；count MAE、精确计数率 | 可见零件数与整机实际总数分开，隐藏零件不算漏检真值 |
| 分割 | 人工实例 mask；IoU、边界质量、小部件召回 | 细线/薄边/小螺栓单列，不被大外壳平均分掩盖 |
| 可见几何 | 从输入视点可见的参考表面；轮廓/重投影、可见表面距离/法线误差 | 有 3D 真值才用 Chamfer/F-score 等表面指标，分别报告尺度对齐与实尺度误差 |
| 背面/遮挡补全 | 未输入视角或完整扫描/CAD；hidden-region 单独评估 | 仅用渲染美观度不能证明结构真实；无真值只标“未验证”，不报误差 |
| 组件化 | 2D 实例与 3D 节点对应、部件完整率、误合并/误拆分率 | 网格是否连通与机械部件边界分别检查；观察件与模板件分开 |
| 真实尺寸 | 量具/CAD/扫描真值；关键长宽高、孔距等绝对误差及相对误差 | 无可信尺度时尺寸为 unavailable；不能先做自由缩放对齐再声称毫米准确 |
| 网格/交付 | 是否可加载、有限坐标、面数、法线、自相交/非流形、节点 ID、单位、导出重载 | 可加载或 watertight 仅是格式/拓扑通过，不是对象几何正确 |
| 时延/资源 | 上传到首次可用 2D 结果、到占位预览、到最终 GLB 的 P50/P95；CPU/RAM/VRAM | 冷启动/热启动、网络和队列等待分别记录，固定分辨率、硬件和样本数 |
| 操作价值 | 人工修正时间、用户是否能正确找出目标外部组件 | 开放确认项不能替代实际试用结果 |

指标门槛应在用户指定速度等级（例如 10 秒/1 分钟/3 分钟）与用途后确定。可以先定义“必须有真实重建结果”“允许手工改组件”“尺寸是否需要”的通过条件；不能先承诺某个模型在任意户外照片的成功率。

### Gaps

- 目前没有可计算的项目准确率、重建成功率、P50/P95 或显存数据；所有数值目标必须等待样例与实测。
- 不知道是否能取得独立物理目标与真实几何，若只有少数网图，无法严谨验证跨设备泛化与三维精度。
- 外观照片不能完成电气安全诊断、载荷/结构强度评估或内部元件清点；若后续用户要求这类分析，需要独立输入、方法和验收定义。
