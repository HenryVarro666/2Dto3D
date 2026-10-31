# 实验与改进索引

本机产物在ignored `data/`和`artifacts/`；Git只跟踪文字与实现。输入、模型、代码与结果缺一项时，不称可复现实验。状态与[问题台账](issues.md)同步。

| 实验 | 版本／输入 | 状态 | 结论和证据 |
|---|---|---|---|
| E00 | V1/V2/V3功能与发布检查 | 历史完成，质量边界保留 | [验证记录](../verification.md)、[V3发布](../v3/release-notes.md)；包括失败回归、手工校正、浏览器和克隆检查；玩具链路不代表光伏精度 |
| E01 | ae4816c，新增13张×single/multiple | 已运行26次 | [本机报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v2_ae4816c_13photos/report.md)，发现映射、大框、主机选择、人物和几何问题 |
| E02 | ae4816c→00d0594，同13张 | 已运行26次＋主线0522a85补测26次 | [本机前后报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v2_perception_fix_13photos/report.md)，改善大框与主机；新增空槽假线束，保留中间版及审查反例 |
| E03 | 0522a85，4组9张同机候选 | 已运行4多图＋18单图 | [本机报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v3_multiview_real_4groups/report.md)，主机未跨图合并、细线丢点、插接件/槽体误分类；21 succeeded/1 needs_review不是质量准确率 |
| E04 | 0522a85→237f796，同E03输入＋原13图保护 | 最终42模型任务＋4受控回放；部分改善，有新错误 | [本机前后图](../../data/collections/sungrow/evaluation/runs/2026-10-31_v3_multiview_fix_4groups/index.html)、[报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v3_multiview_fix_4groups/report.md)、[计划](../superpowers/plans/2026-10-31-v3-real-regression-fixes.md)。4组主机均合并；固定旧mask线点保留改善；新推理Later线点略降、HC05丢细柱和新增语义误检。9c202d1的22任务另存，原747基线冻结 |

## 下一位接手者

读本轮计划、E04报告和issues最后事件；检查Git提交及工作区，不重复已完成的RED/GREEN或42次最终运行。优先PV-012/PV-013：隔离旧/新增词表与非目标物体上下文，先冻结E04再建新run；PV-011需要明确主机选择。没有after的实验保持待运行，不能用规划cases冒充执行。每轮明确新增错误和未改善项，不能只更新成功数字。
