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
