# 实验与改进索引

本机产物在ignored `data/`和`artifacts/`；Git只跟踪文字与实现。输入、模型、代码与结果缺一项时，不称可复现实验。状态与[问题台账](issues.md)同步。

| 实验 | 版本／输入 | 状态 | 结论和证据 |
|---|---|---|---|
| CI-001 | main8253f36与测量分支失败日志 | 7172cb9 GitHub全部通过：131后端/70前端 | [CI记录](2026-11-01-ci-viewer-preload.md)；独立工作区；真实查看器预载入与单条长流程15秒预算，保留两层超时失败，非模型实验 |
| E00 | V1/V2/V3功能与发布检查 | 历史完成，质量边界保留 | [验证记录](../verification.md)、[V3发布](../v3/release-notes.md)；包括失败回归、手工校正、浏览器和克隆检查；玩具链路不代表光伏精度 |
| E01 | ae4816c，新增13张×single/multiple | 已运行26次 | [本机报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v2_ae4816c_13photos/report.md)，发现映射、大框、主机选择、人物和几何问题 |
| E02 | ae4816c→00d0594，同13张 | 已运行26次＋主线0522a85补测26次 | [本机前后报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v2_perception_fix_13photos/report.md)，改善大框与主机；新增空槽假线束，保留中间版及审查反例 |
| E03 | 0522a85，4组9张同机候选 | 已运行4多图＋18单图 | [本机报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v3_multiview_real_4groups/report.md)，主机未跨图合并、细线丢点、插接件/槽体误分类；21 succeeded/1 needs_review不是质量准确率 |
| E04 | 0522a85→237f796，同E03输入＋原13图保护 | 最终42模型任务＋4受控回放；部分改善，有新错误 | [本机前后图](../../data/collections/sungrow/evaluation/runs/2026-10-31_v3_multiview_fix_4groups/index.html)、[报告](../../data/collections/sungrow/evaluation/runs/2026-10-31_v3_multiview_fix_4groups/report.md)、[计划](../superpowers/plans/2026-10-31-v3-real-regression-fixes.md)。4组主机均合并；固定旧mask线点保留改善；新推理Later线点略降、HC05丢细柱和新增语义误检。9c202d1的22任务另存，原747基线冻结 |
| E05 | 58e3e28 / e66a6d9 / 9c98a60；解析fixture + 4份E03旧GLB | 工具与解析/兼容性已验证，现场尺寸待测 | [本次记录](2026-10-31-scale-measurement.md)、[测量指南](../measurement/README.md)；200mm参照，独立高度10%误差反例；真实旧GLB仅相对单位；已完成整合、新克隆与生产浏览器验证，最终66前端/113正式后端；原始数据不入Git |

| E07 | 034ecb8；ETH3D pipes/kicker共6图；固定扫描参考 | 8次真实VGGT调用；网页与审查已验证 | [完整记录](2026-11-01-public-metric-measurement.md)、[主轮结果](../measurement/public-metric-results.json)、[复跑](../measurement/public-metric-repeat.json)。336/518各8条检查，MAPE19.36%/4.17%；518后墙退步，保留全部结果。原图无实体尺；不代表现场精度 |

| E08 | f148c36；同E07六图；VGGT518；固定20个实际点 | 8次真实调用与逆序复跑完成，部分改善有退步 | [完整记录](2026-11-01-undistortion-fixed-points.md)、[主轮](../measurement/undistortion-results.json)、[复跑](../measurement/undistortion-repeat.json)。MAPE4.24%→2.97%，4改善/4退步；kicker跨墙12.91%；深度顺序未修复，单独K射线仍12.65% |

| E09 | 959655a；同E08六图/20实际点/VGGT518；当前vs统一比例 | 16真实调用及逆序复跑完成，分层效果不同 | [完整记录](2026-11-01-aspect-ratio-fixed-points.md)、[主轮](../measurement/resize-results.json)、[复跑](../measurement/resize-repeat.json)。去畸变MAPE2.97→2.52、跨墙12.91→9.63；原图4.24→5.95、跨墙21.99%。保留默认与全部退步 |

| E10-M | eb2bd34预先冻结；3个新ETH3D场景/9图/30扫描点；VGGT518四方案 | 24真实调用与逆序复跑成功；数组/云/长度一致 | [完整报告](2026-11-01-independent-real-scenes.md)、[主轮](../measurement/independent-results.json)、[复跑](../measurement/independent-repeat.json)。去畸变MAPE2.860→2.407、跨墙2.338→1.072%；仍4条退步；原图3.100→2.349%。保留默认和kicker反例，公开训练排除不明 |

## 下一位接手者

读本轮计划、E04报告和issues最后事件；检查Git提交及工作区，不重复已完成的RED/GREEN或42次最终运行。优先PV-012/PV-013：隔离旧/新增词表与非目标物体上下文，先冻结E04再建新run；PV-011需要明确主机选择。没有after的实验保持待运行，不能用规划cases冒充执行。每轮明确新增错误和未改善项，不能只更新成功数字。

尺度与测距接手先读E09缩放分层结论、E08及其固定点协议，再读E05/E07；公开扫描参考已运行，现场仍需真正独立的实物长度。E07不验证桌球台或PV设备，且分辨率对照端点略有移动。识别保护项继续独立维护，不能以标定功能替代模型质量修复。

E10-M尺寸新接手入口在独立实景报告及来源/协议；新数据已经被本轮评估使用，后续调参须另留验证集。DATA-001/SCALE-013记录读取与相机匹配陷阱，SCALE-015和PERF-METRIC-001保持开放；不要把新均值掩盖掉旧kicker或新跨表面/短线退步。
