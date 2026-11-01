# 已知长度标定、两点测距与独立验证

[中文 README](../../README.md) · [English README](../../README.en.md) · [本次验证](../quality/2026-10-31-scale-measurement.md)

本功能测量已完成的**多图点云中的可见点**。单图结构示意的厚度来自类别先验，不进入本功能。照片上的端点可能没有可靠三维点；无法选中时，应补拍/改进几何，不能补造端点。

## 先分清数值依据

| 显示 | 数值依据 | 解释 |
|---|---|---|
| `估算几何 · 尺度未知`，`u` | 原始 GLB 相对坐标 | 相对直线距离，不是米 |
| `参照校准 · 几何仍为估算`，`mm` | 一条已知长度确定比例 | 相对于该参照的估算尺寸，其他位置/方向仍可能有误差 |
| `独立验证`，绝对/相对误差 | 另一条未用于标定的独立长度 | 该线段的误差观测，不是整台设备的精度 |

坐标为 GLB world / Y-up。glTF 的名义单位约定不能让未知尺度点云获得实际米制尺度。`mm_per_unit` 明确记录外部尺度依据。

## 公开实景参考验证（E07）

[完整结果与复现步骤](../quality/2026-11-01-public-metric-measurement.md)：ETH3D 两场景/六照片，独立激光深度参考，一条长度定比例、四条长度检查。336/518 各有8条未参与标定的长度，平均绝对百分比误差19.36%/4.17%；518仍有12.59%及退步，不提供现场毫米精度保证。照片中没有实体标定尺；kicker桌球台因缺参考深度未测量，不能把墙面结果当作桌球台尺寸验证。

主界面切“多角度点云”，展开“公开尺寸验证”。直接查看汇总不需要下载模型或原图；重放点云要先准备 `data/measurement-public/runtime/`，或运行E07脚本并手动输入新生成的job ID。真值来自模型外的扫描数据；raw GLB/PLY仍保持相对尺度。分辨率之间端点随输出像素略有移动，不能忽略这项比较限制。

## 同点去畸变对照（E08）

[完整记录与复现](../quality/2026-11-01-undistortion-fixed-points.md)：保持六张照片、VGGT、518及20个实际参考点不变，已重算亚像素原图基线。8条独立长度MAPE4.24%→2.97%，4条改善、4条退步；kicker后墙12.85%→4.18%，跨墙11.86%→12.91%。后墙深度顺序仍错；已知K辅助未解决跨墙误差。它与E07最近顶点评估方法不同，不直接混算。

网页“多角度点云 → 同点去畸变对照”可看同名A–J在两张照片中的映射、逐条误差与深度诊断，并恢复两条件的只读云和持久收据。测量端点是明确标记的亚像素派生层，原始模型数组/有效支持内原始样本云另存。去畸变需要已有镜头标定；数学映射残差不等于现场尺寸精度。原始图和DB不随Git迁移，缺图时有提示；新run需输入其新job ID。

## 当前与保比例缩放（E09）

[完整方法与复现](../quality/2026-11-01-aspect-ratio-fixed-points.md)：固定同批照片、VGGT518和20实际点，在同一RGB分层内比较缩放。去畸变MAPE2.97%→2.52%，kicker跨墙12.91%→9.63%但仍差515mm，后墙4.18%→5.99%退步；原图MAPE4.24%→5.95%，跨墙21.99%。16次主轮/逆序复跑数组/点云/长度一致，未增加独立场景。保留legacy14产品默认，不能从小样本推断全局改善。

“多角度点云 → 缩放方式同点对照”可切固定原图/固定去畸变图，查看全部误差、实际518准备输入及同名A–J投影、条件深度与known-K辅助，并恢复两种云/收据。统一scale的连续有效区高345.333，存储高346，取点不按整数高度重新拉伸。JPEG预览不参与模型；原始PNG、模型数组、有效区原始样本云和派生端点依据分别保存。

## 独立真实场景：E10-M

E10-M新增[独立真实场景](../quality/2026-11-01-independent-real-scenes.md)：office/delivery_area/terrains共9张新图；固定VGGT518、30个实际扫描端点。原图legacy14/保比例MAPE3.100/2.349%，去畸变legacy14/保比例2.860/2.407%；去畸变跨墙2.338→1.072%，仍有4条退步。24次含逆序复跑，数值/云完全一致，不扩充样本。网页“独立真实场景测试”展示四方案和实景画廊/重放；[来源](independent-sources.json)、[协议](independent-selection.json)、[结果](independent-results.json)。三张照片必须属于同一静止场景；这些室内场景不代表PV设备领域验证。

```bash
# 首次下载需要7zz或7z；例如macOS brew install sevenzip
.venv/bin/python scripts/independent_benchmark.py --download --prepare
.venv/bin/python scripts/independent_benchmark.py --run --runtime-root "$PWD"
.venv/bin/python scripts/independent_benchmark.py --run --run-name 2026-11-01-e10m-repeat --reverse-order --runtime-root "$PWD"
.venv/bin/python scripts/publish_independent.py --check
```

已有冻结run时换新run-name，不能覆盖。完整24次发布需要脚本默认命名的主轮/复跑；一次smoke可用`--scenes office --image-conditions rectified --resize-modes isotropic --run-name my-smoke`，不能把smoke当完整矩阵发布。新DB重跑会生成新job ID；Git内历史ID只在复制原runtime时可重放。

## 操作

1. 完成多图任务，或按 Job ID 打开已有点云。
2. 点击“在点云中选择 A / B”，旋转、放大到端点清晰的位置，点击实际点。第三次点击开始新的一对；可“清除选点”。
3. 核对 A/B、连线、组件 ID、点索引和原坐标。选点自动归零/禁用组件分解；隐藏点不能选择。测量是直线，不沿线缆曲线积分。
4. 输入**已知长度、mm/cm/m 和来源/端点说明**，保存标定。有效范围为所选单位的 `0.000001–1000000`，必须有限且为正。新标定追加版本，不覆盖旧记录。
5. 选择另一对端点，选用标定或“未标定：仅相对单位”，填写可选备注，保存测距。
6. 勾选“加入独立验证长度”，填写未用于求比例的实测值及来源，保存。表格显示独立依据、绝对和相对误差。“查看端点”重载线段，“查看参照端点”复核标定。
7. 下载测量 JSON。重启服务后按 Job ID 恢复；重复打开同一任务会重新读取最新记录。

放大选点可减少人工点击误差，但不会改善深度模型本身。点必须落在同一实物表面/边缘而非附近背景或另一层结构。小数位数不代表相同数量级的精度。用户备注、来源、组件名称和 ID 不因中英西界面切换而改写。

## 计算和独立性

```text
s_mm_per_unit = L_reference_mm / ||B − A||
L_predicted_mm = ||D − C|| × s_mm_per_unit
absolute_error_mm = |L_predicted_mm − L_heldout_mm|
relative_error_pct = absolute_error_mm / L_heldout_mm × 100
```

只有 A–B 参与求 s。服务端拒绝原标定段、反向段及不同索引但坐标相同的段作为验证。可以共享一个端点，但依据仍需人工确认：**在附近换点重画同一条实物标定线，不构成独立验证**。当前不能自动认定物理语义独立性。

如果多条验证线被用于挑选“最好”的标定，它们已经成为开发依据，还应保留未用于选择的长度。建议至少检查不同方向/深度的两条线并分别报告，避免均值掩盖大误差。

全局比例不能修复非均匀形变、深度错误、反光、细线丢点、错配或遮挡。现场加工/安装/验收仍需要经过验证的测量流程；本项目没有相应精度认证。

## 几何版本与记录

端点只提交 `(component_id, point_index)`，额外浏览器坐标会被拒绝。服务端从该任务真实 GLB 的 POSITION 顺序及节点原始变换解析坐标。SQLite 的 `measurement_records` 保存任务、源几何 ID、GLB SHA256、UTC 时间、点索引/原坐标、相对距离、比例与参照来源，以及独立依据、误差和 `used_for_calibration=false`。

原数据库启动时自动建新表，不修改旧结果。GLB/PLY 不重缩放，`MultiResult.metric_scale_status` 仍为 `unknown`；参照校准状态属于独立记录。第三方 GLB 查看器不会自动应用 JSON 比例。

人工重分配即使复用源几何，也可能改变导出点聚合/索引，因此**新 job 必须重新标定**。GLB 字节变化后，旧请求返回 409；旧记录保留但不用于当前几何。相机、居中和组件分解位置不会改变测量。

## 跨机器延续实验

GitHub 保存代码、锁文件、文档、测试、原创演示生成器和结果摘要。照片、权重、SQLite、点云与原始运行目录继续忽略。

- 复现软件：克隆后按 README 生成解析演示，不依赖旧电脑数据；生成的 Job ID 可能不同。
- 继续同一真实实验：停止该实验 API，确认无进程写入；通过自己的私有传输方式复制完整 `PV3D_DATA_DIR`，保留结构、SQLite 和存在的 WAL/SHM，而不是单独复制运行中的数据库。
- 目标机器指定复制后的目录，启动同版本服务，输入原 Job ID。GLB 字节不变时，记录可以继续使用。模型缓存按需另下，旧机器绝对模型路径不保证有效。
- 导出的测量 JSON 用于审计/外部分析；当前无独立 JSON 导入接口。它不包含 GLB/照片，不能独自恢复场景。

可运行 `make build`，再用 `PV3D_DATA_DIR="/absolute/path/to/copied-runtime" make serve`，在 8000 端口打开。无需为了迁移 force-add 原始数据。

## 解析复现与排错

```bash
uv sync --frozen --extra dev
npm --prefix apps/web ci
.venv/bin/python scripts/measurement_demo.py --evaluate
PV3D_DATA_DIR="$PWD/data/measurement-demo" make dev
```

脚本直接生成原创解析 GLB/图示，不调用模型。解析结果只用于查看/测量，没有VGGT原几何缓存，组件细化和重建入口关闭；真实结果的这些功能保留。200 mm 宽度标定；刻意拉长的高度由独立 300 mm 依据检出约 330 mm / 10% 误差；独立 120 mm 深度保持约 120 mm。原始 JSON 留在 ignored `data/measurement-demo/`，浮点残差不是现场精度。

| 现象 | 检查 |
|---|---|
| 没有 mm | 选择有效标定；未标定只显示 u 是预期行为 |
| 无法选端点 | 等待 GLB，归零分解，显示组件，放大并确认实际有点 |
| 几何变化/标定不匹配 | 打开当前 job，核对 SHA，重新选参照并保留旧记录 |
| 标定段被拒绝验证 | 换独立长度，不能反向复用 |
| 找不到旧任务 | 确认 `PV3D_DATA_DIR`；新克隆不自带旧数据库/GLB |
| `No module named fastapi` | 用项目 `.venv/bin/python` 或 `uv run`，不要用系统 Python |
| 开发中改 i18n 后切换无响应 | 本次热更新观察到此现象，整页重载恢复；生产构建另行验证，不能据此认定持久数据丢失 |

新增问题分配[台账 ID](../quality/issues.md)，按[实验模板](../quality/README.md)保存版本、失败尝试、修复、同输入对照、测试、剩余误差与下一步。


E08补充：[新GitHub克隆复现凭证](undistortion-clone-verification.json)记录独立安装、冻结预处理和两次真实模型smoke；复用了公开源数据与权重缓存，未复制原服务数据库。原始产物仍不随Git迁移。

E09补充：[新克隆实际推理凭证](resize-clone-verification.json)验证重新生成的输入和两次真实保比例smoke，明确复用源数据/权重缓存、未复用旧DB。它验证同机软件复现，不是5080实测或现场精度证明。

E10-M补充：[全新私有克隆凭证](independent-clone-verification.json)包括重新解包/生成冻结输入、重算30GT点、新DB两次实际推理与全部数组/云/长度一致；复用压缩源包和权重缓存，同机验证。
