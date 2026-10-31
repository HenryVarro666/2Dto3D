# 现有硬件与模型部署方案

核查日期：2026-10-30。用户已确认有 NVIDIA RTX 5080，备选为 M4 Pro MacBook Pro。一期实现阶段确认本机为 M4 Pro、24GB 内存，PyTorch 2.8.0 MPS 可用，已执行 Grounding DINO＋SAM 2.1 的真实调用。尚未连接或测试 5080 机器，其操作系统、驱动和实际可用显存未知。以下大型生成模型的资源分析仍是部署建议，未运行高精几何模型；当前启动方式见 [运行说明](running.md)。

## 优先使用现有 5080 验证首屏

按 NVIDIA 公布的标准 GeForce RTX 5080 **16GB GDDR7**规划；实施时以实际设备信息确认。先验证检测、分割和参数化结构示意，后台三维生成不放在 10 秒首屏关键路径。这是基于项目需求的工程选择，不是已证明 5080 能达到该时延。[NVIDIA 官方规格](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5080/)

| 运行端 | 建议承担的工作 | 需要验证 |
| --- | --- | --- |
| RTX 5080 机器，主运行端 | 检测／分割、基本体布局、网格导出；之后尝试低显存后台几何 | 操作系统、驱动、Blackwell 兼容、峰值显存、冷／暖时延与后台争用。 |
| M4 Pro MacBook Pro，备用端 | 开发、浏览器查看、组件纠正、CPU 基本体构建及 GLB 导出；识别可另试 MPS | 内存容量、所选模型／算子兼容性及本机首屏时延。 |
| 更高显存 GPU，条件性扩展 | 比较原计划的大型生成模型 | 并非首版前置条件；有相应资源后另行验证，不默认租用。 |

优先把 API、SQLite、文件和 worker 放在 5080 机器同一主机，Mac 通过浏览器访问，避免跨主机共享 SQLite 文件。Mac 独立备用模式使用自己的本地数据目录和数据库，通过显式导入／导出交换资产。

## 根据显存调整后台候选

| 候选 | 官方资源信息 | 本项目的选择 |
| --- | --- | --- |
| Hunyuan3D-2，仅形状 | 仓库报告形状约 6GB、形状＋纹理合计约 16GB。 | 先选一个 shape-only checkpoint 做 5080 小样本试验；不把这些数字当作所有版本、扩展及并发下的保证。 |
| 原版 TRELLIS | 官方要求至少 16GB，验证硬件为 A100／A6000。 | 必要时再作一个对照，5080 几乎没有额外显存余量，不能认定已验证兼容或可与前台常驻模型同时运行。 |
| TRELLIS.2 | 官方要求至少 24GB，Linux 下验证 A100／H100。 | 移为高显存候选，不以标准 16GB 5080 运行默认配置为前提。 |
| SAM 3D Objects | 官方要求 Linux 与至少 32GB NVIDIA 显存。 | 保留为几何／布局能力的高显存候选，首版不依赖其在 5080 上直接运行。 |

来源：[Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2#models-zoo)、[原版 TRELLIS](https://github.com/microsoft/TRELLIS#prerequisites)、[TRELLIS.2](https://github.com/microsoft/TRELLIS.2#prerequisites)、[SAM 3D 安装](https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md)。低显存卸载、量化或社区移植可以后续实验，当前没有项目内证据，不作为默认能力。

只先验证一个低显存候选，不同时建立所有环境。第一轮仅形状生成、无 PBR 纹理，以减少依赖并单独判断几何价值；这是试验范围，不改变最终细化方向。生成整物网格不证明组件分解，仍须检查每组件映射、共同坐标与 GLB 导出。代码与权重许可按实际 checkpoint 核对。

## Blackwell 与 MPS 的兼容边界

5080 环境需要支持 Blackwell 的 PyTorch／CUDA 组合。PyTorch 2.7 官方公告已加入 Blackwell 和 CUDA 12.8 wheel 支持；这是历史支持依据，不是强制锁定 2.7。最终版本要兼顾模型及自定义扩展，不能直接照搬旧 CUDA 11.8／12.1／12.4 安装脚本。PyTorch 张量运算可用也不证明稀疏卷积、光栅化和注意力扩展均可用，每个启用的扩展需要独立验证。[PyTorch 官方 2.7 公告](https://pytorch.org/blog/pytorch-2-7/)

M4 Pro 可评估 PyTorch MPS；MPS 是 Metal 路径，不提供 NVIDIA CUDA 扩展的直接替代。CPU／MPS 需要独立适配和计时，不能把系统的统一内存容量当作上述 NVIDIA 显存门槛已经满足。若自动识别不兼容，仍可支持人工组件输入后的示意构建与查看；这属于功能备用，不能宣称自动 10 秒流程达标。[PyTorch MPS 文档](https://docs.pytorch.org/docs/2.7/notes/mps.html)

## 实施时的最小验证顺序

1. 记录 5080 实际显存、操作系统、驱动、RAM，以及 Mac 内存；不预设 GPU 机器已经运行 Linux。
2. 为当前模型固定经过测试的 PyTorch／CUDA 和扩展组合，先完成基础计算与单样例导出检查。
3. 在 5080 上只运行快路径，测含上传和浏览器加载的完整 10 秒目标。
4. 后台单独加载一个低显存 shape-only 候选，记录峰值显存、耗时与输出对应关系。
5. 最后测试前后台同时有请求的情况；16GB 总量还需容纳常驻模型、工作区和系统占用。发生 OOM、首屏阻塞或不符合十秒目标时，关闭并发或安排独立细化时段，并明确该运行条件；队列优先级不代表可即时抢占正在运行的 GPU 推理。
6. 独立测试 M4 Pro 备用路径，分别记录自动识别是否可用、示意构建和查看能力，不沿用 5080 测速结果。

基本原则是先用已有硬件验证；更高显存资源、云实例和完整纹理模型均在证据需要时再选择。[返回计划书](plan.md) · [设备扩展路线](roadmap.md)
