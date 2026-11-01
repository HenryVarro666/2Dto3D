# README 图像与来源

[中文](../../README.md) / [English](../../README.en.md) 使用以下版本化素材；原始实验照片仍按 data/artifacts 规则忽略。

| 文件 | 目的 | 来源与范围 |
|---|---|---|
| `workbench.zh.jpg` / `workbench.en.jpg` | 工作台、场景、点云与 A/B | 本地真实网页截图，场景为 `scripts/measurement_demo.py` 原创解析 fixture；没有现场照片，没有 ML 调用 |
| `validation.zh.jpg` / `validation.en.jpg` | 相对估算、参照校准与独立误差 | 同一真实网页持久记录；330/300 mm 是刻意形变，不是现场精度 |
| `workflow.zh.svg` / `workflow.en.svg` | 多图输入到标定的流程 | 作者绘制，展示当前实现，不充当实验结果 |
| `architecture.zh.svg` / `architecture.en.svg` | 网页/API/存储/模型环境 | 作者绘制；测量读 GLB，不进推理队列 |
| `scale-validation.zh.svg` / `scale-validation.en.svg` | 比例不能消除形变 | 解析算例，A–B/C–D/E–F 是解释标签；网页保留真实点索引 |

SVG 由标准库生成，无脚本、外部资源或嵌入照片：

```bash
.venv/bin/python scripts/readme_figures.py
.venv/bin/python scripts/readme_figures.py --check
```

重拍：按 README 启动解析演示，恢复 Job ID，“查看端点”显示高度线。核对 A/B、尺度标签和误差，分别切中/英文后用浏览器原生截图保存 JPEG。不要生成/修改数值来伪造 UI。增加真实设备图片前记录来源与使用依据，不能直接将 ignored 原照片入库。

本次视口约 1280×720；像素比/滚动条可能造成细微差异。备注与组件名保留原文。截图没有账号资料、私有路径、现场原图或 EXIF；校验和见[本次验证](../quality/2026-10-31-scale-measurement.md)。


## E07 公开实景结果与真实截图（2026-11-01）

| 文件 | 用途 | 来源与边界 |
|---|---|---|
| `public-metric-errors.zh.svg` / `.en.svg` | 8条独立长度的逐线对比 | 从Git内`docs/measurement/public-metric-results.json`确定性生成；百分比误差，不是识别准确率；含kicker退步 |
| `public-metric.zh.jpg` / `.en.jpg` | 真实三语网页的结果汇总入口 | 本地生产页面原生截图；可见336/518统计和前两张结果表，无模型/数值合成 |
| `public-cloud.zh.jpg` / `.en.jpg` | 原图、真实VGGT点云、检查端点显示 | 本地生产页面，pipes/518主轮`a64f1f644b4944a19ea1c174f4ee860a`，重放柜体横向C–D收据。通用查看器将该检查线两端显示为A/B；它们不是该任务的标定A–B，原始收据/表仍标C–D |

照片来源：ETH3D high-resolution multi-view training，pipes，原始`DSC_0635.JPG`（另两视图`DSC_0634.JPG`/`DSC_0636.JPG`）。作者/项目：Thomas Schöps、Johannes L. Schönberger、Silvano Galliani、Torsten Sattler、Konrad Schindler、Marc Pollefeys、Andreas Geiger，见[官方项目与论文](https://eth3d.ethz.ch/)、[数据](https://eth3d.ethz.ch/datasets)。ETH3D数据及这些包含照片/其点云衍生内容的截图按[CC BY-NC-SA4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)保留归属与许可。截图不是把原始输入照片直接入Git；原JPEG/EXIF、深度和网格仍为ignored本机产物。

变更/处理：原始照片进入VGGT联合几何；未对照片做生成式修补。查看器把相对坐标转为显示坐标，叠加实际GLB选点的A/B标记；截图保持浏览器原生像素，没有重写数值或修图。参考长度来自模型外激光深度，不是照片中已有标尺。二维图表是作者根据E07数值重画，SVG无脚本/外部资源，E07当轮由`--check`验证8张SVG；新增E08后为10张。

屏幕正常视口1280×720（滚动条占部分宽度）；中文/英文各截一次。浏览器还核对了西语的参考类别、范围说明与同一数字。完整来源、原图/模型/协议哈希见[E07](../quality/2026-11-01-public-metric-measurement.md)。


## E08 同点去畸变结果与照片对照（2026-11-01）

| 文件 | 用途与来源 |
|---|---|
| `undistortion-errors.zh.svg` / `.en.svg` | 从冻结`undistortion-results.json`生成8条固定实际点误差；包含全部退步，10张SVG通过确定性检查 |
| `undistortion.zh.jpg` / `.en.jpg` | 8004生产网页实际截图：4.24%/2.97%均值与逐条原图/去畸变结果，无合成数值 |
| `undistortion-points.zh.jpg` | 原生网页截图：ETH3D pipes/kicker原图与去畸变照片及同一20个扫描点投影。橙色A–B标定，绿色C–J未参与比例拟合；标记位于照片投影位置，没有把取点挪到最近模型像素 |

照片来源仍为[ETH3D官方数据](https://eth3d.ethz.ch/datasets)：pipes `DSC_0635.JPG`及kicker `DSC_6503.JPG`（输入顺序、路径、哈希见E08冻结协议）。归属与CC BY-NC-SA4.0沿用上节列出的ETH3D作者及许可。含照片的对照截图按相同许可保留，处理为已知镜头标定的OpenCV双线性去畸变、JPEG查看预览、SVG端点叠加和原生屏幕捕获，无生成式修补。模型输入独立使用无损PNG，预览JPEG不参与推理。原照片/EXIF/扫描数据仍ignored，不直接入Git。

[E08报告](../quality/2026-11-01-undistortion-fixed-points.md)保存方法、结果、问题与验证，屏幕正常视口1280×720。图表为作者重画，不代表现场PV精度；数学投影残差也不是物理误差上界。

`undistortion-cloud.zh.jpg`：8004真实生产网页，去畸变kicker任务`af0aa4da3b15428aa901a81a4c8ccb34`，显示G–H派生索引6/7（通用查看器显示A/B）与实际VGGT点云。照片和点云衍生内容沿用本节ETH3D归属及CC BY-NC-SA4.0；截图未修图，不能以可视化外观证明深度或长度正确。

## E10-M 独立真实场景（2026-11-01）

| 文件 | 用途、真实来源和范围 |
|---|---|
| `independent-errors.zh.svg` / `.en.svg` | 根据冻结independent-results.json确定性绘制4方案的12条检查/4条跨墙均值；写明退步，14张SVG一起校验 |
| `independent.zh.jpg` / `.en.jpg` | 8004真实生产页面四方案、范围提示和逐条误差表，无合成数值 |
| `independent-gallery.zh.jpg` / `.en.jpg` | terrains真实三视角DSC_0658/0657/0659及走廊退步行、参考范围/许可；图片未做生成式修补 |
| `independent-inputs.zh.jpg` | terrains两种缩放的实际518张量查看预览和同名扫描点投影，橙AB标定/绿C–J验证；JPEG查看预览不参与模型 |
| `independent-cloud.zh.jpg` / `.en.jpg` | office/rectified/isotropic主轮929bb59aad974fb6a525c88ac7aed98d，真实VGGT云及G–H派生索引6/7；通用查看器显示A/B，与标定AB不同 |
| `independent-corridor.zh.jpg` | terrains/rectified/isotropic主轮5b628234cf7c4d7faa20dff1becacab8，长走廊完整云默认适配后较小；保留视图局限，不用外观代替精度 |

照片来源仍为[ETH3D high-resolution training](https://eth3d.ethz.ch/datasets)，office原始DSC_0219/0220/0253，delivery_area原始DSC_0683/0682/0684，terrains原始DSC_0658/0657/0659；作者、[CC BY-NC-SA4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)归属沿用上列Schöps等完整作者信息。含照片或扫描/点云衍生内容的截图按该许可提供，原始JPEG/EXIF、激光深度、无损PNG和完整点云仍ignored。原图画廊为解码RGB的JPEG网页查看派生，去畸变由已知镜头参数OpenCV双线性重映射；518查看预览来自真正冻结的输入张量。截图为浏览器原生1280×720捕获，没有修图、移动标记或改写数值。[校验和清单](../measurement/independent-screenshots.json)、[完整实验和局限](../quality/2026-11-01-independent-real-scenes.md)。

办公室云只覆盖可见表面，桌面/显示器等有孔洞和缺点；按照片视图分组不等于真实组件分割。点云默认全景适配对长走廊会压缩局部细节，用户可旋转和缩放，未来可增加按照片相机查看的入口。所有这些截图均不是PV设备或现场毫米精度证明。


## E09 缩放方式同点对照（2026-11-01）

| 文件 | 用途与来源 |
|---|---|
| `resize-errors.zh.svg` / `.en.svg` | 作者按冻结resize-results.json重画两RGB分层、同横轴的全部长度误差；包含原图显著退步，12 SVG由脚本验证 |
| `resize.zh.jpg` / `.en.jpg` | 8004真实生产页面；固定去畸变RGB，2.97/2.52与逐线误差，分别原生中/英截图 |
| `resize-original.zh.jpg` | 原图保护分层真实截图：4.24/5.95，不混入去畸变结果 |
| `resize-inputs.zh.jpg` | 从真实准备张量导出的518输入查看预览及同一实际A–J；含白色letterbox。橙色标定、绿色未参与比例拟合，同名点对应同一扫描位置 |

含照片的截图来源ETH3D pipes/DSC_0635、kicker/DSC_6503（完整三视图顺序和SHA见E08/E09协议）；归属与CC BY-NC-SA4.0沿用E07/E08所列ETH3D作者、项目及许可。处理包括已知标定去畸变、PIL bicubic当前/统一比例缩放、JPEG查看预览、SVG端点叠加和原生1280×720捕获，无生成式修图。真实推理读取独立无损RGB并在worker准备张量，JPEG只展示。截图/图表不证明现场尺寸精度；原始照片/PNG/数组/DB/权重继续ignored。

`resize-cloud.zh.jpg`：真实8004工作台，kicker/rectified/isotropic任务6558249e023c47d3afa05a1c97d9fe1a；查看G–H派生索引6/7时通用查看器显示A/B。实际选点读原始GLB坐标，保留“原始几何·相对尺度”和“参照校准·几何仍为估算”。照片/点云衍生内容仍按上述ETH3D归属与CC BY-NC-SA4.0保存；不以点云外观看作尺寸正确证明。
