# 户外光伏电气设备：可见组件分解、CAD 支线与装配表示

研究日期：2026-10-30。研究与方案讨论阶段，未安装软件、下载权重、运行模型或验证延迟。根据后续澄清，对象暂按户外光伏电气设备及其支撑结构理解，目标是较快生成类似 Blender 可浏览、能看出组成部分的三维结果。具体设备类别仍未知；下述组件类别是待样图确认的例子。首版不要求完整 CAD 库。

## 1. 应识别什么，以及如何从照片获得组件实例？

### Takeaway

首版输出应称为“可见组件分解”：以设备主体和可见附属箱体、底座、支架、外部连接组件等约 3–5 个粗粒度类别起步。标签、视觉组件实例、实际可拆装零件和工程 BOM 是不同层次，不能由一张外观照片互相替代。

### Cited Findings

- CAD 数据中，`components` 是可复用定义，`occurrences` 是具有独立位置、朝向、可见性的实例；`bodies`、`holes`、`contacts`、`joints` 则分别记录其他几何与装配信息。这为“零件类型、实例与几何特征分开存”提供了直接参考。[Fusion 360 Gallery 装配格式](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/assembly.md)
- SAM 2 支持图像/视频中的可提示分割，可用点、框等交互得到对象区域；其模型权重、训练和演示代码以 Apache 2.0 发布，演示字体和部分第三方代码另有许可。[SAM 2 官方仓库及许可说明](https://github.com/facebookresearch/sam2#license)
- GroundingDINO 提供文本驱动的开放集目标检测；可以先给候选框，再让 SAM 2 细分。官方仓库为 Apache 2.0，官方 `IDEA-Research/grounding-dino-tiny` 模型卡也标注 Apache 2.0。[GroundingDINO](https://github.com/IDEA-Research/GroundingDINO)；[模型卡](https://huggingface.co/IDEA-Research/grounding-dino-tiny)
- SAM 3 已支持通过短文本概念或图像示例寻找所有匹配实例，并支持点、框、掩码等提示；官方 README 还记载 2026-03-27 发布的 SAM 3.1，主要增加多对象视频跟踪能力。SAM 3 使用独立的 SAM License，不能沿用 SAM 2 的 Apache 结论。[SAM 3 官方仓库](https://github.com/facebookresearch/sam3)；[SAM License](https://github.com/facebookresearch/sam3/blob/main/LICENSE)

### Inferences

- **先区分两种输入。** 单个一体成型结构件：孔、槽、折弯、加强筋等先作为父零件的几何特征；设备或装配体：再判断哪些是外壳、支架、附属箱等独立组件。同样外观的筋板可能一体成型，也可能另行焊接，照片不足时不认定制造方式。遮挡可能把一个实物分成多个可见区域；相连的 mesh 也不证明是一件实物。
- **首个可比较分割基线：** 人工框/点 + SAM 2；自动模式再比较 GroundingDINO-tiny + SAM 2 与 SAM 3 文本/示例分割。先验证粗粒度实例是否完整，再决定是否值得加入更细的门板、散热构件、线缆或紧固件。不能预先承诺模型理解专用电气部件名称。
- VLM 可提供“可能的设备类别、候选组件词、可见属性、需要补拍的位置”，作为搜索和标注建议；逐条绑定裁剪区域。候选词不自动成为真值，不猜精确 SKU、电气参数或隐藏内部结构。
- 交互必须支持增删实例、合并/拆分掩码、修改类别及标记未知。用户确认的实例 ID 应持续保留，使三维对象能对应回照片。若使用多张照片，应跨图关联同一实例，不能按掩码总数累加件数。
- 外壳看起来是一个组件，不等于只有一件工程零件；外观上的螺栓头也不足以认定隐藏螺母、垫圈和螺纹规格。首版清单记录“可见实例数”，BOM 仅在另有图纸、目录、拆机或人工核对依据时建立。

### Gaps

- 尚无样图，无法确定设备是否为逆变器、变压器、开关设备或其他对象，不能预定一套固定拆分标签。
- 未找到这些模型在本项目户外设备照片、反光金属、细支架、遮挡线缆上的项目内精度与延迟证据。首版模型选择仍需小样本实测。

## 2. 生成式分块与 CAD 检索/拟合各适合什么？未知相机如何对齐？

### Takeaway

可浏览的粗三维可优先采用生成式模型并保留人工组件校正；CAD 检索/参数拟合是有目录、已知尺寸或标准部件时的增强支线。分块生成给出可分离 mesh，不代表已测量 CAD、真实工程零件数或正确装配约束。

### Cited Findings

| 候选 | 官方能力与输入 | 本项目相关边界及许可 |
| --- | --- | --- |
| PartCrafter | 从一张 RGB 联合生成多个 mesh，不要求预分割；项目展示包含对不可见部分的生成。当前脚本需确定目标 `num_parts`，可手填或让 VLM 建议。 | 代码和官方对象级权重标注 MIT。当前 README 明确训练图像来自 Objaverse 渲染，并提供实拍风格转换，说明实拍存在域差异。默认去背景会使用 RMBG-1.4，其权重只允许非商业使用，不能把整个默认链统称 MIT。[项目](https://wgsxm.github.io/projects/partcrafter/)；[输入及 VLM 选项](https://github.com/wgsxm/PartCrafter#vlm-based-part-suggestion)；[代码许可](https://github.com/wgsxm/PartCrafter/blob/main/LICENSE)；[权重许可](https://huggingface.co/wgsxm/PartCrafter)；[RMBG-1.4](https://huggingface.co/briaai/RMBG-1.4) |
| MIDI | 从全图及分割的实例图生成组合式三维场景；CLI 先准备实例分割图，再输出 GLB，官方建议交互确定适当分割粒度。 | 与“先确认可见组件再三维化”较接近，但主要证据不是户外电气设备。代码和官方 MIDI-3D 权重标注 Apache 2.0；纹理、分割等额外模型仍分别核查。[仓库](https://github.com/VAST-AI-Research/MIDI-3D)；[项目](https://huanngzh.github.io/MIDI-Page/)；[权重](https://huggingface.co/VAST-AI/MIDI-3D) |

- CadQuery 是基于 OpenCascade Python 绑定的参数化 CAD 库，可导入/导出 STEP；文档已有带孔板及型材装配示例，适合箱体、底座、板件、规则支架的受限模板。[CadQuery 简介](https://cadquery.readthedocs.io/en/latest/intro.html)；[型材装配示例](https://cadquery.readthedocs.io/en/latest/assy.html)
- CadQuery 为 Apache 2.0；底层 OCCT 使用 LGPL 2.1 并带 Open CASCADE exception，需要分别保留依赖许可。FreeCAD 则提供参数化建模与 Python API，可作为后续人工校核工具，不必成为首版服务依赖。[CadQuery 许可](https://github.com/CadQuery/cadquery/blob/master/LICENSE)；[OCCT LGPL](https://github.com/Open-Cascade-SAS/OCCT/blob/master/LICENSE_LGPL_21.txt)；[例外条款](https://github.com/Open-Cascade-SAS/OCCT/blob/master/OCCT_LGPL_EXCEPTION.txt)；[FreeCAD 官方说明](https://github.com/FreeCAD/FreeCAD)
- OpenCV 的 PnP 从已知三维点、对应二维投影、相机内参和畸变参数估计物体相对相机的旋转与平移；不要求事先知道相机外参。[OpenCV PnP](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html)

### Inferences

- **生成分支的验收对象是外观与组件对应关系。** PartCrafter 的块数即使由 VLM 建议，也不证明实物件数，给定数量也不保证每块与用户标签一一对应。应投影回原图对照、允许重命名和修正，标明背面/遮挡部分是生成补全。不要用风格转换后的几何细节作为孔位或尺寸证据。
- **首版没有 CAD 库仍可成立。** 先形成可点选、隐藏的独立对象和可见组件列表；无法稳定拆分时，让用户确认粗粒度划分。箱体等简单部分可使用允许用户调整的几何代理。把整物 mesh 的可见表面按二维掩码着色，并不等于得到了完整的独立三维零件。
- **CAD 增强支线：** 从用户授权目录/图纸或自己确认的少量模板入库，生成多视角缩略图，检索 Top-k 候选；结合外轮廓、孔型、型材截面及人工尺寸确认后拟合有限参数。标准紧固件仅在规格已知时选库；没有目录匹配就返回未知或近似族，不编造精确 SKU。厂商 CAD 可下载并不自动代表可公开再分发。
- 参数化模板应限制自由度，例如箱体长宽高、板厚、支架角度、孔间距；未观测参数保留未知/区间/目录值及来源。这样得到的 STEP 是模板重建结果，生成 mesh 转存 STEP 不会自动恢复参数化设计历史、真实公差或制造意图。
- **对齐能力分阶段：**
  1. 初版仅给候选三维与人工旋转/移动校正，可浏览的相对布局标作估计。
  2. 已知真实尺寸 CAD、内参和稳定二维—三维特征后，估计单个设备/组件的物体到相机变换，再以轮廓、边缘或关键点重投影优化。相机外参可以求解，不能误说必须预先掌握。
  3. 多组件共用同一相机坐标系后，可由各自变换求相对位姿，再加入用户确认的接触、同轴、共面等约束。
- 任意现场单图若焦距、尺寸和特征对应都未知，靠候选 CAD 外观不能保证唯一深度和相对布局。规则箱体、重复支架、平面板和对称件尤其可能多解；保留候选姿态与人工确认，多视角/标尺作为后续提高可信度的手段，不作为首版输入的强制前提。

### Gaps

- 未发现 PartCrafter/MIDI 在本项目设备上的尺寸、孔位、真实组件粒度或装配精度证据。这里只推荐可比较候选，未认证任何模型可直接满足目标。
- 用户的硬件、速度目标、能否补拍及 CAD 获取条件尚待明确；官方展示耗时不能当作本项目从上传、分割到可交互显示的延迟保证。

## 3. 如何表示组成关系、做爆炸图，并验证 MVP？

### Takeaway

用“几何资产—组件实例—关系—证据”四层表示，首版爆炸图只提供帮助观察的显示位移。评价先覆盖可见组件及外观，再逐步加入有真值的 CAD、尺寸和位姿，避免以“看起来像”代替零件正确性。

### Cited Findings

- Fusion 360 Gallery 的装配树描述父子层次，occurrence 引用共享 component；接触图、joint 图与层次图表达不同关系。Joint/mate 定义相对自由度、静止姿态参数和运动限制，而非仅在世界坐标中摆放 mesh。[装配数据](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/assembly.md)；[joint 数据](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/assembly_joint.md)
- CadQuery 的装配求解器通过位置与朝向上的约束代价求解，支持 Point、Axis、Plane 等约束；因此几何相邻不等同于已建立 CAD 约束。[CadQuery constraints](https://cadquery.readthedocs.io/en/latest/assy.html#constraints)
- OCCT XDE 可保存装配描述、名称、颜色和实例位置，并支持 STEP 读写，可作为后续工程数据交换依据。[OCCT XDE](https://occt3d.com/dev/doc/overview/html/occt_user_guides__xde.html)
- BOP 将二维检测/分割和三维位姿分别评价；位姿使用 VSD、MSSD、MSPD 处理可见表面、对称形状及投影歧义。可借鉴其任务拆分和对称性处理，但不能照搬室内/工业数据成绩到本项目。[BOP 2023 评价](https://bop.felk.cvut.cz/challenges/bop-challenge-2023/)
- Fusion 360 Gallery 数据集只允许非商业研究；可参考其数据结构，不能默认为商业组件库或直接随产品分发。[数据许可](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md)

### Inferences

- **最小记录建议：**
  - 几何资产：`asset_id`、mesh/CAD 文件、版本/哈希、单位、来源与许可、生成模型版本或模板参数。
  - 实例：`instance_id`、`asset_id`、类别候选、照片/掩码 ID、可见性、估计或已确认变换。同一型号多个实物用多个实例，不复制型号定义。
  - 特征：孔、槽、折弯等挂在所属资产/实例下，避免当作同级零件。
  - 关系：父子、可见邻接、推测接触、人工确认的装配约束分别记录；不要把“相邻”自动升级成“螺栓连接”。
  - 证据：`observed / generated / catalog / measured / user_confirmed / unknown`，连同原图区域、尺度来源、校正记录；置信度分标签、几何、尺寸和位姿记录，不用一个分数代表全部可靠性。
- 保存原始场景位姿；爆炸方向、距离、展示顺序另存为显示参数。手动爆炸只用于查看组成，不声称是可执行拆卸路径或装配顺序。后续若要这些能力，需补充碰撞、紧固关系、真实间隙和顺序约束。
- **建议的 MVP 切片：** 单图中人工选定一个设备主体 → 粗粒度可见实例与人工校正 → 生成可浏览三维 → 将标签对应独立对象 → 点选/隐藏/可选手动爆炸 → 显示未观测部分提示。目录 CAD、精确位姿、自动装配为后续阶段。
- **评价集与指标：**
  - 先采一批真实户外设备及组件，以人工确认的可见组件为真值，覆盖杂乱背景、反光、遮挡、细长连接组件和重复设备；组件边界存在歧义时保留标注规则与争议记录。
  - 按真实设备/装配体 ID 分训练与测试，同一设备的多张图不得跨分区。另分“已知型号的新拍摄”和“未见型号/结构变体”，明确是否允许测试 CAD 在检索库中。
  - 分开测组件类别、实例召回/计数、掩码 IoU，以及未知类别拒识；三维测可见轮廓/投影对应、丢失与多生组件、对象可选中率、人工修正时间。不能只报整物外观分数。
  - 有确切目录真值时再测 CAD Top-1/Top-3；有已知 CAD/尺寸时测参数绝对误差及相对误差；有姿态真值时使用对称性友好的位姿/重投影误差。隐藏内容单列，不能把生成补全当实测真值。
  - 同时比较“人工掩码输入”和“模型掩码输入”，区分错误来自分割还是三维模块；闭集与库外样本分别报告。
  - 速度分上传/预处理、首个可显示结果、全部组件生成、导出和人工修正记录 p50/p95，标注硬件、组件数和图像尺寸；先显示粗结果、后台逐步补全可改善体验，但不能把首屏时间当全流程完成时间。

### Gaps

- 工程 BOM、内部器件及可执行拆装路径需要项目外的图纸、目录或现场核验，当前外观目标无法单独验证。
- 目前没有项目样图和实测结果，不能设定有依据的精度阈值、证明实时能力或确认最佳组件粒度。
