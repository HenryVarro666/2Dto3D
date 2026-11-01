# E07：公开照片的尺度标定与独立测距验证

状态：数据准备中；此阶段尚未产生真实模型尺寸误差结果。

本轮继续主线 `517d04c` 的 E05 标定/测距工具，独立于另一个会话的 E06 组件识别回归。用户没有现场实测长度，授权寻找公开多角度与尺度依据；不将解析 fixture 当作实测。

## 评测协议与研究选择

- [执行计划](../superpowers/plans/2026-11-01-public-metric-measurement.md)。候选为 [ETH3D high-res multi-view training](https://eth3d.ethz.ch/datasets) 的 pipes 与 kicker：真实同场景照片，另附激光扫描渲染参考深度。不是照片中可见的实体尺，也不是逆变器现场验证。
- [官方格式说明](https://eth3d.ethz.ch/documentation)：`*_depth.7z` 是原始畸变照片对应的 float32 深度，并非同名 JPEG 图片；无效值为 infinity。COLMAP `points3D.txt` 是图像三角化结果，**不能当成激光真值**。
- 原图、参考深度及相机文件在模型外单独读取；THIN_PRISM_FISHEYE 反投影要按 [COLMAP 3.11.1 源码](https://github.com/colmap/colmap/blob/3.11.1/src/colmap/sensor/models.h)核对。不得直接把畸变深度套到预去畸变照片。
- 先检查照片/参考深度、冻结三图与端点，再运行模型。同一场景只用一条长度拟合尺度，其余长度只评分。无深度/遮挡边界点先按统一规则拒绝；模型误差大不能成为事后排除理由。
- 原始数据、数组、GLB/PLY、数据库、日志保存在 ignored `data/measurement-public/`。Git 保存下载/运行脚本、冻结选择、汇总结果、测试与文档；新克隆不会自带这些原始数据。
- ETH3D 数据许可见 [官方网站](https://eth3d.ethz.ch/)：CC BY-NC-SA 4.0；VGGT 仍用既有非商业权重。此轮不变更模型授权。

## 已发生的问题与决定

- SCALE-003（新）：有公开标靶照片不等于附有已知实测长度。[Agisoft 官方样例](https://www.agisoft.com/downloads/sample-data/)列出 6 图/3 标靶，但 `https://download.agisoft.com/datasets/coded.zip` 在本机 60 秒连接超时，未取得文件，不能确认其长度记录。保留来源作为后续候选，不编造尺寸，也不把教程推荐打印半径当成该样例实物长度。
- SCALE-004（新）：参考坐标错误可能比模型误差更大。匹配原始畸变照片、相机与深度，检查边界/空值，保存参考采样偏差和每点诊断；实施与测试待补。
- Ruling：使用扫描参考长度作本轮可执行验证，网页明确标明来源；代价是不能回答“现场放尺子后能达到多少毫米精度”。

后续按运行证据追加结果与问题，不覆盖本段准备历史。
