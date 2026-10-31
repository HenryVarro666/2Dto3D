# 单张野外光伏电气设备照片转 3D：候选模型与边界

核查日期：2026-10-30（用户本地日期）。这是研究与选型笔记，未安装依赖、下载权重、运行模型或取得实测成绩。当前按用户补充理解为野外光伏电气设备及其底座、支撑结构和可见连接件；“光伏变电气”的具体设备类型仍待样图确认。目标暂定为可旋转查看、能选择和理解可见组成部分的近似 3D 场景，类似 Blender 中的浏览体验。

## 1. 哪些模型适合野外照片，输出能否代表真实零件？

### Takeaway

优先对比 **SAM 3D Objects 与 TRELLIS.2**，Hunyuan3D 2.1 作为可选第三条资产生成基线。三者的官方能力均不能直接等同于从照片恢复真实 BOM、内部结构或参数化 CAD；TRELLIS.2 论文更明确把零件分割及结构图列为未来方向。[SAM 官方仓库](https://github.com/facebookresearch/sam-3d-objects)、[TRELLIS.2 论文 Appendix F](https://arxiv.org/html/2512.14692v1)、[Hunyuan3D 2.1 官方仓库](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1)

### Cited Findings

| 候选及角色 | 官方输入、输出与范围 | 对本项目的直接意义 |
| --- | --- | --- |
| **SAM 3D Objects：野外场景主基线** | 图像 + 目标二值 mask，预测该对象的形状、纹理、旋转、平移和尺度；支持 mesh 或 3D Gaussian splats。使用目标裁剪与完整图像上下文，可选粗场景 pointmap。 | 与杂乱背景、部分遮挡、设备在原场景中的布局需求最相符。mask 是指定重建对象的条件，不能把 SAM 3D 本身描述成输入零件名称即可识别所有部件的系统。[论文 §2](https://arxiv.org/html/2511.16624v1#S2)、[公开调用接口](https://github.com/facebookresearch/sam-3d-objects/blob/main/notebook/inference.py) |
| **TRELLIS.2-4B：目标资产质量/速度基线** | 单张图像 → 带 PBR 材质的 mesh；O-Voxel 表示支持开放表面、非流形结构等，公开示例导出 GLB。材质包括颜色、金属度、粗糙度、透明度。 | 适合将设备主体或某个可见大部件单独抠出后生成可展示资产。不能仅凭其拓扑表示能力推断它能观测到照片背后的真实内部结构。[官方模型卡](https://huggingface.co/microsoft/TRELLIS.2-4B)、[官方示例](https://github.com/microsoft/TRELLIS.2/blob/main/example.py) |
| **Hunyuan3D 2.1：可选第三基线** | 图像到 Shape mesh，再由 Paint 为已有 mesh 合成 PBR；论文说明生成 albedo、metallic、roughness 贴图。 | 可用来确认“更复杂的纹理模型是否真的改善设备辨认”，而不是只比较漂亮渲染。官方单图形状/纹理流程没有提供制造零件清单接口。[官方使用说明](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1#code-usage)、[论文](https://arxiv.org/html/2506.15442v1) |

- SAM 的多对象 notebook 是对每个已有 mask 分别调用推理，再合成场景；示例保留 per-object outputs，并导出 posed Gaussian PLY。它提供“由指定对象组成的场景”，不是自动发现真实机械拆装边界的证据。[官方多对象 notebook](https://github.com/facebookresearch/sam-3d-objects/blob/main/notebook/demo_multi_object.ipynb)
- TRELLIS.2 的官方预处理优先使用已有 RGBA alpha，否则运行背景去除，再按 alpha 包围框裁成对象输入。对野外照片，设备周围的护栏、线缆、阴影、植被是否被错误保留或删除，必须先检查；代码支持复用人工确认的 alpha。[官方预处理实现](https://github.com/microsoft/TRELLIS.2/blob/main/trellis2/pipelines/trellis2_image_to_3d.py)
- SAM 3D 把 3D→2D 描述为有损映射，目标是拟合条件分布；其布局训练包含 normalized camera coordinates。可选 pointmap 能接入传感器或单目深度，但不能把无标尺的单张照片输出称为已校准的毫米尺寸。[SAM 论文 §2.1–§3.1](https://arxiv.org/html/2511.16624v1#S2.SS1)
- TRELLIS.2 明确说明当前表示不显式编码高层结构/语义信息，part-level segmentation 与 graph-based topology 是未来工作。[论文 Appendix F](https://arxiv.org/html/2512.14692v1)

### Inferences

以下是基于上述接口与表示做出的项目判断，不是厂商已验证的项目能力：

| 用户需要的结果 | 本项目应怎样定义与呈现 |
| --- | --- |
| **看起来合理的三维补全** | 单图生成模型可作候选；背面、被挡住的连接和内部都应标“推测”，旋转后看起来合理不等于真实。 |
| **可测量的几何重建** | 需要已知尺寸、尺度参照/相机信息，以及独立多视角或扫描真值验证；单一标尺只能提供尺度锚点，不能纠正所有形状错误。 |
| **能点选的语义部件场景** | 先对可见外部部件建立 mask/实例 ID 与名称，再将这些 ID 绑定到近似 3D 节点。可以先实现“箱体/底座/支架/可见附件”的粗层级，保留未知标签。 |
| **制造级零件分解/BOM** | 需要产品图纸、型号/零件库、装配规则和人工核对；连通网格、颜色分区或每个 mask 的生成结果都不是充分证据。 |
| **可编辑 CAD** | GLB/mesh 可在建模软件编辑顶点与材质，但不自动拥有草图、孔径、拉伸、约束、配合或特征树。若以后要求 CAD，应另立检索/参数拟合或逆向 CAD 路线。 |

- 对当前野外需求，推荐原图保留用于定位和语义解释，另保存设备主体与可见大部件的 mask/crop。比较时报告两条输入路径：SAM 的原图+mask，以及各资产模型的同一经确认目标裁剪。不要把不同背景处理带来的差异全归因于 3D 模型。
- 可立即展示二维识别结果与带名称的简单三维占位体，再异步替换为生成几何；部件 ID、名称和“推测/已确认”状态不应依赖模型生成的 mesh 拆分结果。这是交互设计建议，当前没有端到端时延测量。

### Gaps

- 尚无用户样图，不能确定需要重建设备主体、整组装配、整站场景，或需要哪些部件粒度；同一金属箱体的门板、散热件与内部设备不应混为一个“真实零件数量”指标。
- 本轮没有找到这三条官方基线在该用户的野外光伏设备照片上、针对真实部件数量/连接关系/尺寸误差的验证；不得引用通用视觉偏好排名替代领域验证。
- SAM 官方多对象示例主要展示 Gaussian 场景；“逐部件 mesh 导入 Blender 并保留准确布局/名称”的完整导出路径仍需后续原型检查，不能把 PLY 可视化示例当作已完成的 Blender 工作流。

## 2. 在什么环境运行，速度与商业许可应怎样表述？

### Takeaway

当前官方环境证据支持把 **Mac 用作交互前端、标注与结果查看，Linux + NVIDIA GPU 用作异步推理 worker**。这是一种减少移植偏差的架构建议，不能据此声称模型已经在本机可跑或达到秒级端到端响应。[SAM 安装文档](https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md)、[TRELLIS.2 环境说明](https://github.com/microsoft/TRELLIS.2#prerequisites)、[Hunyuan3D 2.1 环境说明](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1#get-started-with-hunyuan3d-21)

### Cited Findings

| 模型 | 官方运行证据 | 许可与权重获取 |
| --- | --- | --- |
| SAM 3D Objects | Linux 64 位，NVIDIA GPU **至少 32GB VRAM**；安装链含 CUDA/PyTorch3D 等。 | 代码和 checkpoint 均为 **SAM License**；HF 权重需申请访问/认证。许可证含再分发、研究致谢、贸易控制及特定用途限制，不能写成 Apache/MIT 或无条件商用。[setup](https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md)、[模型卡](https://huggingface.co/facebook/sam-3d-objects)、[LICENSE](https://github.com/facebookresearch/sam-3d-objects/blob/main/LICENSE) |
| TRELLIS.2 | 仅 Linux 被官方测试；NVIDIA **至少 24GB**，验证过 A100/H100；推荐 CUDA 12.4。 | 官方明确模型与代码为 **MIT**，模型卡亦标 MIT；仍应核对 nvdiffrast、nvdiffrec 等单独依赖许可。[README](https://github.com/microsoft/TRELLIS.2)、[权重卡](https://huggingface.co/microsoft/TRELLIS.2-4B)、[MIT 文本](https://github.com/microsoft/TRELLIS.2/blob/main/LICENSE) |
| Hunyuan3D 2.1 | README 报 **Shape 10GB、Texture 21GB、整套 29GB**；声称支持 macOS/Windows/Linux，但注明测试栈是 Python 3.10、PyTorch 2.5.1+cu124，默认形状设备为 CUDA，官方纹理 rasterizer 使用 CUDAExtension。 | **Tencent Hunyuan 3D 2.1 Community License**，代码/权重及衍生物受对应条款约束。许可 Territory 排除 EU/UK/韩国；第4条规定在版本发布日、前月全部产品/服务 MAU 超过100万者须另获许可。分发/AUP/依赖仍有条款。[README](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1)、[默认 pipeline](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/hy3dshape/hy3dshape/pipelines.py)、[CUDA rasterizer](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/hy3dpaint/custom_rasterizer/setup.py)、[LICENSE](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE) |

- TRELLIS.2 公布 H100 上 512³/1024³/1536³ 约 **3/17/60 秒**；这是特定硬件的形状+材质生成报告，不包含本项目网络传输、排队、分割、人机确认、冷启动和导出等完整响应链。[官方速度表](https://github.com/microsoft/TRELLIS.2#1-high-quality-resolution--efficiency)
- 低显存时不应同时扩展多个候选：原版 TRELLIS 官方门槛是16GB且仅 Linux 测试；Hunyuan3D 2.0 README 报 Shape6GB、形状+纹理16GB，可在预算不满足主基线时二选一作为替代，不能把2.0的显存数字套到2.1。[原版 TRELLIS](https://github.com/microsoft/TRELLIS#prerequisites)、[Hunyuan3D 2.0](https://github.com/Tencent-Hunyuan/Hunyuan3D-2#models-zoo)
- Hunyuan3D 2.1 的顶层 LICENSE/Notice 写 Community License，但部分代码文件头仍出现 NON-COMMERCIAL 字样；这是官方文本中的不一致，应记录而不是自行宣布哪一段失效。Notice 还列有独立第三方许可。[顶层 LICENSE](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE)、[Notice](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/Notice.txt)、[文件头示例](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/hy3dshape/hy3dshape/pipelines.py)

### Inferences

- 首轮若想在同一 worker 顺序比较主候选，可把 **48GB NVIDIA GPU** 作为资源申请候选，因其高于已公布32GB/29GB门槛；这不是48GB必然足够所有分辨率、并发与后处理的承诺，必须测峰值显存。只具备24GB时，应先缩小对比范围而非承诺SAM官方配置可跑。
- Mac 原生 MPS/MLX、Windows wrapper、量化/卸载等社区路径可能存在，但本轮不将其作为已验证官方基线。Hunyuan README 的跨平台声明应保留，同时说明“本项目尚未验证原生 Mac 的完整 Shape+PBR 路径”。
- 先返回轻量占位结果、后台排队生成、完成后缓存每个设备/部件资产，比把所有模型冷启动串入一次同步请求更符合“速度快”的目标；实际目标需分别设定首反馈与最终几何完成时间。
- 代码可读、权重可下载、许可证允许一定商业使用，属于不同问题。后续保存所用 commit、权重版本及所有依赖许可；若要提供跨地区服务或商业发布，先解决选中路线实际适用的条款，不在本研究中给出无限制商用结论。

### Gaps

- 尚无GPU型号、可用显存、预算、用户可接受等待时长及并发要求；不能选择具体云实例或报价。
- 尚未实际申请SAM权重、构建环境、做冷/热启动测试；当前没有本项目的p50/p95时延、吞吐、失败率或Mac运行证据。
- Hunyuan代码头与顶层许可的不一致尚未由维护者澄清。许可证观察只是选型事实记录，不构成对具体部署的法律结论。

## 3. 应如何小范围验证，哪些问题出现就停止单图路线？

### Takeaway

先验证“设备/可见组成部分是否被正确保留、生成的形状是否帮助理解”，再比较纹理观感。候选模型所用表示本身有分辨率与拓扑限制；没有依据承诺细杆、薄板间隙、孔洞及隐蔽连接在野外单图中可稳定恢复。[SAM 分辨率限制](https://arxiv.org/html/2511.16624v1)、[TRELLIS.2 Appendix F](https://arxiv.org/html/2512.14692v1)、[Hunyuan3D 2.1 形状预处理](https://arxiv.org/html/2506.15442v1#S2.SS2)

### Cited Findings

- SAM 官方指出粗形状分辨率64³等架构设置会对复杂形状造成细节丢失或扭曲；本项目因此还需检查目标很小时的有效输入分辨率。[SAM Appendix F](https://arxiv.org/html/2511.16624v1)
- TRELLIS.2 指出小于体素尺度的细节会混叠，距离很近的平行面可能被拟合到中间；还可能出现非预期小孔及局部拓扑断裂。[论文 Appendix F](https://arxiv.org/html/2512.14692v1)
- Hunyuan3D 2.1 训练预处理将物体归一化并由SDF/等值面生成闭合表面。其PBR材质能力描述的是生成外观贴图，不是通过照片实测真实金属表面参数或证明结构精度。[论文 §2–§3](https://arxiv.org/html/2506.15442v1)

### Inferences

**以下是拟议实验设计与项目门槛，不是已有结果或文献阈值：**

1. 只选12个有使用授权的真实野外设备/局部装配样本：4个主体清楚、背景干净；4个背景杂乱/部分遮挡；4个细长支撑、可见孔槽、强反光或重复对称结构明显。若同设备多张照片，按设备划分样本，避免把同件多个视角当独立成功案例。
2. 每个样本只给模型一张主照片；另留1–3个补充视角、可用产品图/清单或人工标注作核查依据，不输入单图模型。若没有这些依据，只能评“可见面/可见部件”和主观外观，不能评背面真实度或BOM准确度。
3. 人工先确认设备主体mask，以及粗粒度可见外部部件ID。各模型共享同一主图和经确认的alpha/crop；SAM额外使用完整图+mask作为其原生场景路径。分别记录裁剪错误和三维生成错误，不混成一个分数。
4. 主比较只跑SAM与TRELLIS.2；GPU预算允许才加Hunyuan2.1。先低/中分辨率、每例一个固定seed；只对成功和失败的代表案例追加两个seed检验结构稳定性，避免用无限重采样挑最好看的结果。
5. 每个输出必须同时看原图投影、无纹理灰模/法线、多视角旋转。分别记录：可见大部件是否遗漏/粘连/多生；细杆/孔槽/接头是否保留；对称/重复件数量是否稳定；背面是否只是推断；语义ID是否还能点选；与补充视角是否矛盾。生成纹理不能掩盖几何失败。
6. 时延记录上传/预处理、分割、排队、模型、导出、首次可交互、最终替换；冷启动与热启动分开，记录峰值显存与失败。H100官方速度只作为参考，不能代入目标worker。
7. 开始前由用户设定“第一反馈”和“最终近似3D”的等待预算，并确认仅可见粗部件还是每颗紧固件。若要尺寸，再指定允许误差及测量基准；这些门槛决定是否继续，而不是通用排行榜。

**停止或改路条件：**

- 若要求确定看不见的内部电气零件、完整真实BOM、隐藏连接或制造级CAD，立即把单图生成降级为可视化辅助，转向产品/部件库检索与型号匹配、图纸/装配数据或多视角采集；不通过追加prompt作真实保证。
- 首批6个样本即有2个以上在人工正确mask后仍把关键大部件漏掉、合并或凭空增加，则暂停扩张/微调，先复核分割粒度、拍摄方式与目标定义。该2/6是建议的探索止损阈值，可由用户调整。
- 若关键孔槽、导轨间隙或连接位置决定是否“看懂”，而三seed或留出视角核查仍不稳定，即判该类样本的几何生成不合格；保留二维部件解释或模板占位，不渲染成已确认结构。
- 若无法在约定GPU/时延预算内完成，停止升分辨率，保留即时识别+占位、异步缓存的交互路线；如仅粗几何即可满足需求，可直接采用经确认的参数化箱体/支撑模板。
- 反光金属、遮挡、近似对称背面应保留“未知/推测”状态。尤其禁止把补全出的机箱背面、孔洞或内部零件数量当作观测事实。
- 未通过上述结构与语义核查前，不推进领域微调、大规模数据标注或生产集成。只有失败模式明确且存在配对真值/实际收益时，才讨论训练。

**精简主源表（均于2026-10-30核查；main分支及模型卡以后可能变更）：**

| 主源 | 用途 |
| --- | --- |
| [SAM 3D repo](https://github.com/facebookresearch/sam-3d-objects) / [paper](https://arxiv.org/abs/2511.16624) | 场景/目标mask、输出与模型边界 |
| [SAM setup](https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md) / [license](https://github.com/facebookresearch/sam-3d-objects/blob/main/LICENSE) | 环境、权重门禁及许可 |
| [TRELLIS.2 repo](https://github.com/microsoft/TRELLIS.2) / [model card](https://huggingface.co/microsoft/TRELLIS.2-4B) / [paper](https://arxiv.org/abs/2512.14692) | 资产生成、硬件、速度、无语义结构的明确限制 |
| [TRELLIS.2 preprocess](https://github.com/microsoft/TRELLIS.2/blob/main/trellis2/pipelines/trellis2_image_to_3d.py) | 野外背景去除与目标裁剪 |
| [Hunyuan2.1 repo](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) / [paper](https://arxiv.org/abs/2506.15442) | Shape/Paint分工、PBR与环境 |
| [Hunyuan2.1 license](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE) / [Notice](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/Notice.txt) | 地域、商业条款及第三方依赖 |
| [TRELLIS原版](https://github.com/microsoft/TRELLIS) / [Hunyuan2.0](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) | 仅作为显存不足时的替代，不同时扩大比较 |

### Gaps

- 样图、具体设备类别、部件定义、交付格式、精度/时延目标尚未锁定；以上样本分层和阈值仍需据实际目标调整。
- 本轮没有声称某个模型胜出，没有给出本项目准确率、毫米误差或可承受并发；无模型实测，不得在后续摘要中把候选建议改写为已实现系统。
