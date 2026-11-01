# E10-M：独立真实场景，四方案固定实际点对照

状态：来源和协议准备中，尚未运行新场景模型。E10-M与另一个会话的E10组件识别分开编号。基线66fd7cc，独立工作树分支eval/independent-real-scenes；不改产品默认或E07–E09历史结果。

## 预注册设计与真实照片

[设计](../superpowers/specs/2026-11-01-independent-real-scenes-design.md) · [计划](../superpowers/plans/2026-11-01-independent-real-scenes.md) · [来源与实际扫描取点](../measurement/independent-sources.json)

数据来自[ETH3D官方高分辨率训练数据](https://eth3d.ethz.ch/datasets)和[官方数据说明](https://www.eth3d.net/documentation)。office办公室、delivery_area卸货区、terrains材料展示走廊，3场景9张真实照片，均不与本项目E07–E09场景及照片SHA重叠。此处“独立”仅针对本项目开发，不能确认VGGT预训练是否见过ETH3D。不是PV设备精度验证。

每场景3个有重叠的视角；首图冻结10个实际扫描像素/XYZ。AB单独确定比例；CD/EF/GH/IJ各有独立扫描长度，全部留作检查。每方案12条检查线，其中office与terrains各两条真正跨左右墙的线，共4条跨墙线。delivery_area两条为后墙至近侧柱面/拖车的跨表面线，不能称为跨墙。所有线均测端点欧氏距离，不是自动求墙的垂直净距。

原图/已标定全视场去畸变各比较legacy14/连续保比例，均VGGT518。模型checkpoint/code固定；RGB-only输入；扫描真值不参与图像变换、模型或几何预测。每组只用AB标定，known-K另有AB-only辅助比例，不混入主指标。12次主轮、逆序12次复跑；重复不扩充独立样本。worker耗时与预处理分开，缓存权重、同一M4 Pro24GB；未验证5080。

## 已发现的问题与取舍

| ID | 现象、根因及处理 | 验证与边界 |
|---|---|---|
| DATA-001 | bsdtar3.5.3/libarchive3.7.4选择性解delivery_area固实7z时报Truncated7-Zip body，并生成字节数正确的全零深度 | 改用7-Zip26.05；另一独立py7zr解包输出SHA一致。深度SHA baead6b314509ffd2e207a6979b0b598121c096f3297fbe35e06801d6cdd8c5c；不把全零读取失败算模型误差 |
| SCALE-013 | terrains有camera1/0两组标定，第一行并非所选照片相机 | 从images.txt的camera ID查cameras.txt，拒绝混用；先RED后GREEN回归。发现于协议冻结及推理前，旧E07–E09相机/结果不受影响 |
| SCALE-014 | 较远/倾斜/边界区域无法通过原21×21/30mm扫描支持门槛 | 卸货区排除4个候选，走廊0656排除7个并改选0658；原因完整保存在来源JSON，全部发生在推理前。未放宽阈值；选择偏向有扫描支持的可见表面，不能代表无真值区域 |

办公室AB/CD/EF/GH/IJ参考约1242.37/3043.17/1421.77/2727.24/909.47mm；卸货区约2033.05/4034.76/547.56/9626.24/6069.84mm；走廊约1073.45/2876.02/575.98/3257.64/137.18mm。完整精度以JSON为准。137mm短线用于暴露相对误差敏感性，不因模型结果删除。

原JPEG、激光深度、无损输入、数组、点云、DB与日志位于ignored `data/measurement-independent/` 和共享测量runtime。源JPEG预选时临时解出了同场景全套照片以制作contact sheet；冻结/跨机下载仅提取9张照片、标定和3张深度，节约磁盘。未入Git的完整来源选择过程可由来源JSON、照片与扫描支持重新检查。扫描配准/精度没有额外实测误差上界；照片中无实体标尺。

## 结果与验证

待完成真实主轮/复跑后填写，不能将单元测试或解析坐标一致性作为现场精度。
