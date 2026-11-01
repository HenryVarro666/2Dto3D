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

变更/处理：原始照片进入VGGT联合几何；未对照片做生成式修补。查看器把相对坐标转为显示坐标，叠加实际GLB选点的A/B标记；截图保持浏览器原生像素，没有重写数值或修图。参考长度来自模型外激光深度，不是照片中已有标尺。二维图表是作者根据E07数值重画，SVG无脚本/外部资源，`scripts/readme_figures.py --check`现在验证8张SVG。

屏幕正常视口1280×720（滚动条占部分宽度）；中文/英文各截一次。浏览器还核对了西语的参考类别、范围说明与同一数字。完整来源、原图/模型/协议哈希见[E07](../quality/2026-11-01-public-metric-measurement.md)。
