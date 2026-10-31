# 实验与改进索引

本机产物在ignored `data/`和`artifacts/`；Git只跟踪文字与实现。输入、模型、代码与结果缺一项时，不称可复现实验。状态与[问题台账](issues.md)同步。

| 实验 | 版本／输入 | 状态 | 结论和证据 |
|---|---|---|---|
| E00 | V1/V2/V3功能与发布检查 | 历史完成，质量边界保留 | [验证记录](../verification.md)、[V3发布](../v3/release-notes.md)；包括失败回归、手工校正、浏览器和克隆检查；玩具链路不代表光伏精度 |
| E01 | ae4816c，新增13张×single/multiple | 已运行26次 | [本机报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v2_ae4816c_13photos/report.md)，发现映射、大框、主机选择、人物和几何问题 |
| E02 | ae4816c→00d0594，同13张 | 已运行26次＋主线0522a85补测26次 | [本机前后报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v2_perception_fix_13photos/report.md)，改善大框与主机；新增空槽假线束，保留中间版及审查反例 |
| E03 | 0522a85，4组9张同机候选 | 已运行4多图＋18单图 | [本机报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v3_multiview_real_4groups/report.md)，主机未跨图合并、细线丢点、插接件/槽体误分类；21 succeeded/1 needs_review不是质量准确率 |
| E04 | 本轮三项修复，同E03输入＋原13图保护 | 诊断/修复中，真实after未运行 | [计划](../superpowers/plans/2026-10-31-v3-real-regression-fixes.md)；本机目录`data/collections/sungrow/evaluation/runs/2026-10-31_v3_multiview_fix_4groups/`，含747文件原基线、关联诊断与词表探针；不得提前报改善 |

| E05 | 9c202d1上的标定/测距扩展；解析fixture + 4份E03旧GLB | 工具与解析/兼容性已验证，现场尺寸待测 | [本次记录](2026-10-31-scale-measurement.md)、[测量指南](../measurement/README.md)；200mm参照，独立高度10%误差反例；真实旧GLB仅相对单位；新克隆/整合验证继续追加 |

## 下一位接手者

读本轮计划和issues最后事件；检查Git提交及工作区，不重复已完成的RED/GREEN或真实运行。没有after的实验保持待运行；修改后追加新提交/运行ID，不覆盖已有run目录。每轮明确新增错误和未改善项，不能只更新成功数字。
