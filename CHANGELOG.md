# Changelog

## Unreleased — production hardening (HARDEN-001)

- Add validated environment settings (`pv3d.config.Settings`), a `python -m pv3d` entry point with `--check`, text/JSON logging, per-request IDs and access logs, security headers and opt-in CORS.
- Make shutdown deterministic: running work finishes, queued jobs are recorded as interrupted, new submissions get 503. Lock the data directory so two servers cannot interrupt each other's jobs.
- Bound long waits: configurable VGGT worker timeout with a distinct error, refinement wait timeout behind the single worker, configurable queue capacity exposed on `/api/health`.
- Reject oversized uploads before multipart parsing, move upload CPU work off the event loop, accept multi-picture JPEGs, return 404 for missing masks and 405 for wrong methods.
- Record the SQLite schema version and refuse newer ledgers; add indexes and per-connection pragmas.
- Frontend: secure-context-independent IDs for manual boxes, missing translations, stable test parallelism; prettier/tsc checks in CI.
- Add Dockerfile, `.env.example`, pre-commit hooks, mypy and a three-job CI; document deployment in `docs/operations.md`. Frozen benchmark scripts and the VGGT worker are unchanged.

## Unreleased — aspect-preserving resize evaluation (E09)

- Add an experimental isotropic preprocessing mode with continuous point mapping, fractional Pillow source boxes and separate integer storage bounds. Legacy14 remains the default and reproduces E08 arrays/clouds/measurements exactly.
- Compare all eight conditions twice at fixed VGGT/518 and physical points: rectified MAPE 2.97%→2.52%, but original 4.24%→5.95% and cross-wall 21.99%; retain all regressions and avoid a global default change.
- Add trilingual stratum selection, real 518-input point overlays, depth diagnostics and immutable cloud replay; update both READMEs, source-attributed figures/screenshots and durable issue/evidence records.

## Unreleased — fixed-point undistortion evaluation (E08)

- Freeze 20 physical scanner endpoints before evaluating the same six photos with VGGT/518, calibrated full-field rectification and subpixel camera-Z sampling. Preserve raw arrays, supported model samples and derived-anchor provenance.
- Run eight primary/repeat calls: length MAPE 4.24%→2.97%, four checks improve and four regress; cross-wall error 12.91% and reversed back-wall depth order remain. Known-K auxiliary does not resolve the difficult geometry.
- Add trilingual original/rectified tables, matching photo markers, depth diagnostics and immutable replay; update Chinese/English READMEs with reproducible charts and authentic screenshots.
- Prevent measurement evaluation from interrupting unrelated queued jobs (RUN-001); save all failed cases then exit nonzero (RUN-002). Field precision and aspect-preserving resize remain unverified.

## Unreleased — reference calibration and bilingual visual documentation

- Add immutable known-length calibrations and two-point measurements over actual multi-view GLB point indices/world coordinates, separating relative estimates and reference-calibrated lengths.
- Record held-out sources and absolute/relative errors; reject reference reuse, geometry changes and cross-job calibration. Keep raw GLB/PLY and single-photo schematic scale unchanged.
- Persist/export receipts; restore old jobs and reopen the same job without locking UI. Add A/B markers/lines and trilingual controls.
- Add model-free analytic demo and matching Chinese/English READMEs with authored diagrams and authentic screenshots. Analytic and compatibility checks do not establish field precision; existing geometry issues remain in the ledger.

## 未发布：真实光伏多视角回归修复

- 增加带深度/有效性/歧义检查的主机双向掩码重投影关联，保留同图互斥与人工ID。
- 线缆采用面积覆盖mask、局部置信保留和更细体素，记录补充点的依据；无真实尺度保证。
- 新增插接件/线槽独立类别与三语、API及导出支持，增加上下文/形状保护；已知边界见质量台账。
- 同4组9张完成4多图＋18单图，追加20任务覆盖原13图保护；4组主机均归为1个ID，固定旧mask回放的线缆点保留均改善。新推理Later线点略降、HC05细柱漏检及非目标插接件/槽体误分类仍开放，非质量全通过。
- 建立docs/quality历史问题、失败试验和后续文档交接要求；实际前后图与原始产物在本机ignored目录，未远程发布。


## 3.0.0 — 2026-10-31

- 同一设备 2–8 张不同视角照片，持久照片组与独立多图任务，保留全部单图 API。
- 固定 VGGT-1B 源码／权重版本，在隔离环境联合预测相机与深度，过滤并融合相对尺度彩色点云。
- 逐图 DINO／SAM 组件候选；跨视角空间关联、全局组件 ID、手动合并／拆开和同组几何复用。
- 多图网页、真实阶段与视角进度、中英西文案、逐图框选及正负点、点选择／隐藏／背景／分解和 GLB／PLY／JSON 导出。
- 原始 checkpoint 仅用于非商业研究；尚无光伏多视角准确率、真实尺寸、制造 CAD 或 RTX 5080 实机结论。

## 2.0.0 — 2026-10-31

- 框选后调用真实 SAM 2.1 细化；正负点修正、撤销、清空、重框、独立确认与仅框回退。
- 增加单／多设备自动识别范围；切换后由用户明确重跑，多设备移除单主柜筛选。
- 服务端不可变掩码／提示点／模型记录，与照片和框绑定；人工重建使用引用，保留组件 ID。
- 草稿保留、过期响应保护、合并加点请求、同图特征缓存，以及中英西三语控件。
- 支持启动时选择固定的 SAM 2.1 tiny／small／base-plus／large；仅 tiny 已实机检查。
- 继续提供相对尺度的组件示意，不生成真实尺寸、精确轮廓网格、设备归属树或完整 BOM。

## 1.0.0 — 2026-10-31

- 对升级前已运行代码创建不可变版本快照，commit `7ba23c8ca541713e696ba7de58d3b78c850af14c`。
- 照片上传、Grounding DINO tiny＋SAM 2.1 tiny、参数化结构、GLB／JSON、手动框与组件编辑。
- 实际阶段进度、已用时间及中文／English／Español 切换。
- V1 快照内部沿用早期 `0.1.0` 清单元数据，以保持快照代码不变；发布标签为 `v1.0.0`。
