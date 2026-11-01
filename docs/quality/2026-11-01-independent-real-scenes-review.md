# E10-M 独立审查及修复处置

审查范围66fd7cca9b953adc7cc182a0ce9ea24239824f88..cc62f64244be8755de85eb20739f2c9e0803d5b0。新上下文独立Code Reviewer只读审查，没有改文件或再派代理，也没有重跑24次模型或声称独立重复浏览器/新克隆验收。其程序化检查重算30个扫描点和120组配置内映射、12个张量/支持mask/预览，核对24组raw/audit GLB、AB-only尺度与所有误差；现有归档数据正确，E07–E09和默认未变。没有Critical或Declined-to-judge项目。

| 发现 | 实际影响与处置 | RED→GREEN证据 |
|---|---|---|
| Important：结果重发布/网页可接受错标RGB分层；publisher也接受与长度不一致的误差 | METRIC-VERIFY-001。按scene/RGB/resize解析冻结case，核对model.image_condition、实际输入tensor SHA和layout；校准比例、校准长度、绝对/相对误差均复算。前端直接加载冻结协议，比对对应输入/映射与模型条件；不再只信结果自己的标签 | 后端8种变更（外标签、连模型标签、tensor、layout、相对/绝对误差、校准长度/比例），前端4种错配均先失败后通过；现有24组通过更强发布检查 |
| Important：仅核对存储XYZ与存储长度自洽，不足以证明来自实际扫描点 | METRIC-VERIFY-002。读取已验SHA的稀疏深度，按所选照片camera ID及requested_pixel重算参考点；逐字段比较sample pixel、Z、XYZ、支持数/跨度/位移/中位数偏差。保留原21×21/30mm/3px门槛 | 将XYZ与长度一起翻倍，或改Z/像素/支持数/跨度/位移/中位数偏差，7种变更先失败后通过。实际30点仍一致 |
| 原评级Minor：DATA-001重用、E09的16调用/144收据被插入新E10-M节下 | DOC-METRIC-001。因用户明确要求稳定问题ID与实验交接，按实际可追溯性影响升为Important并修复。原设备身份DATA-001保留；解包问题改为DATA-METRIC-001并更新本轮引用。恢复原E09/CI叙述，将本轮独立追加 | 文档审计先因重复ID失败；修正后验证新ID不与历史冲突，旧16调用叙述仍属于E09 |

无遗留Minor，也没有重派复审。修复由作者在一个RED/GREEN修复阶段完成；新增16个后端和4个前端案例，当前164后端通过/2可选ML跳过、82前端、build/Ruff/14SVG通过。正式ML环境与最终新克隆/远端状态在[主报告](2026-11-01-independent-real-scenes.md)继续追加。

这轮修复加强验证和文档谱系，未改变扫描点、任何图像/模型输入、既有预测或误差结果。independent-sources/selection/results/repeat四文件与cc62f64逐字节一致，协议SHA仍2bc561635a567544fc5a97e5e7022e5bb5984c34358b1355489366309bc5bcf6。24次正式对照不重命名、不覆盖；后续新克隆smoke另存。
