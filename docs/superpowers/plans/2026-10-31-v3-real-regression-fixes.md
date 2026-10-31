# V3真实照片回归修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复真实同机跨视角关联、细线点保留和插接件/线槽误分类；重跑相同4组9张，并把历史、当前及未来改进连接到持久文档。

**Architecture:** 保留固定VGGT-1B/336和DINO/SAM tiny，以真实保存的相机、深度和掩码定位后处理错误。关联保留现有距离路径和同视角互斥，补充双向mask重投影/深度支持的保守匹配；细线使用局部mask置信选择和更细体素；分类增加两个明确类别及上下文约束。照片、原始基线和实验均在ignored data内，文档与测试入Git。

**Tech Stack:** 现有Python/FastAPI/NumPy/SciPy/PyTorch、React/TypeScript/Three.js；不新增外部推理服务。

**Spec:** 用户本轮明确的三项修复和持续文档要求；问题证据为本地`data/collections/sungrow/evaluation/runs/2026-10-31_v3_multiview_real_4groups/report.md`，领域范围沿用`docs/plan.md`及AGENTS.md。

## Global Constraints

- 保留同样4组9个原图SHA和安装阶段；不把跨阶段/无身份依据照片拼成一组。
- 保留二值mask孔洞/岛、同视角不合并、显式人工ID、Y-up及未知真实尺度。
- 既有V1/V2/V3标签不改；不上传原图、权重、SQLite和GLB；本轮无远程发布要求。
- 新类别是本次实现选择：`connector`/`cable_tray`。保持旧5类与历史JSON可读取。
- 不把点数增加、自动关联或任务succeeded当作准确率或CAD验收。

## Review Focus

- 相邻相似逆变器：新增投影路径不得把同图邻机或歧义候选强行合并。
- 低置信细线：只保留有mask及有限正深度/置信支持的点，不能补造点或引入留白。
- 插接件误检：限制到逆变器附近；线槽不得被电池/配电盒或整排端口替代。
- 旧类别和人工校正：新分类不能破坏来源、ID、mask继承和三语显示。
- 开发数据重复使用：相同4组已用于修复，报告定性回归和新增错误，不宣称独立精度。

## Task 1：台账和基线

Files: `docs/quality/{README,issues,experiments}.md`、`AGENTS.md`、`CONTRIBUTING.md`。

- [x] 冻结0522a85的747个实验文件，保存逐文件SHA及before副本。
- [x] 读取并记录基线投影、置信、体素和词表根因。
- [x] 建立稳定问题ID与历史证据索引，状态区分已修复/部分改善/待验证。
- [x] 写入后续变更的文档交接要求，保留原始验证文档而不改写历史。

## Task 2：三项修复，分别红绿验证

Files: `services/api/src/pv3d/{pointcloud,perception,profiles,schemas}.py`及对应tests；前端`api/types.ts`与`i18n/`。

- [x] 写失败回归：三维距离有偏差但双向相机投影正确的主机；相邻/歧义/深度不符的拒绝。
- [x] 实现投影补充匹配，保留同图互斥与人工分组；跑点云测试。
- [x] 写失败回归：细线mask缩小时消失、被背景置信截掉及被粗体素压缩；无效点仍拒绝。
- [x] 实现细线mask/局部置信/细体素策略并记录点保留诊断；跑点云测试。
- [x] 写失败回归：插接件/线槽分类、相邻箱体保护及新类别API/GLB/三语行为。
- [x] 实现新词表、分类保护、profiles/schema/三语兼容；跑针对测试。
- [x] 每次实验、失败、调整和剩余风险追加到台账，禁止只留聊天结论。

## Task 3：固定输入真实复跑与审查

- [x] 全套`make test`、`make build`、Ruff和diff检查。
- [x] 固定修复提交，运行同样4组VGGT及18次单图对照；追加旧13图的分类/主机负例回归。
- [x] 保存模型版本、源文件SHA、阶段、二值mask、geometry maps、JSON/GLB/PLY、前后二维/三维图、逐图新旧错误。
- [x] 独立整分支代码复核一次，修复重要问题后重复受影响的验证。
- [x] 更新问题状态和实验索引；验证基线未改动、输入同SHA、导出ID/点数及所有本地入口。

最终实现237f796，共42个最终真实模型任务、4个受控回放；9c202d1的22任务单独归档。16项证据校验通过，108后端＋60前端通过。质量结论为部分改善：四组主机归并、固定旧mask线点保留提高；新增PV-012细柱丢失、PV-013非目标物误分类，PV-005等未解决。详见[实验索引](../../quality/experiments.md)与本机E04报告；不把“任务计划完成”写成“所有光伏质量问题解决”。
