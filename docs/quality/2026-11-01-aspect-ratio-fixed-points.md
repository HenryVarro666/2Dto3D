# E09：当前缩放与保比例缩放，固定实际位置的518对照

状态：协议设计与实现中，尚无本轮模型效果结论。

用户已明确授权本轮受控执行、网页/中英文README/私有仓库同步。沿用[E08](2026-11-01-undistortion-fixed-points.md)的六张照片和20个实际扫描点，不因新输出像素移动端点。当前`SCALE-010`已观察到14对齐将6048×4032压为518×350，纵横比例相对拉伸1.35%；它是待验证的预处理假设，不是已证实的几何根因。

[完整设计与执行计划](../superpowers/plans/2026-11-01-aspect-ratio-fixed-points.md)。本轮在原图/去畸变RGB两个分层内分别比较缩放，主要观察去畸变kicker跨墙；同VGGT、同518方形输入、同物理位置、各自只用A–B拟合比例。16次真实调用计划包含主轮与逆序复跑，不增加独立场景数。

保比例方案采用相同PIL bicubic下采样滤波与单一scale，连续有效内容518×345.333像素，整数存储区域518×346；独立保存分数像素映射，不能将整数高度346或345当作精确保比例。GT深度和长度不用于图像准备或推理。比较包含有效像素覆盖、插值位置和白边变化，不能单独归因于深度头。

所有原始数组、模型输入、点云、日志和数据库保存在ignored `data/measurement-resize/`与既有重放runtime；旧E08协议/结果不改写。后续按实际运行追加改善、退步、失败与验证证据。

独立builder检查已完成，无重要未决问题；用纯Pillow解析fixture确认逆仿射位置相等、浮点box无裁剪/API拒绝，未运行模型。存储边界逐边floor/ceil，短轴白色源padding覆盖bicubic足迹。依据：[Pillow官方resize浮点box文档](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.resize)；实际使用项目锁定Pillow12.3.0，不升级依赖。
