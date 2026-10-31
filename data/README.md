# 本地数据

项目根目录为 `/Users/caochao/Documents/2Dto3D/`。原始照片保留在 `photos/`，实际标注、派生数据和本地索引放在本目录。除本说明外，本目录内容默认不进入 Git。

## 当前资料

`photos/string_inverters/` 中有两张用户提供的候选图。它们可用于讨论外壳、安装支架和线缆等可见组成。照片来源和再分发许可尚未核实，未作为公开数据集发布；文件名也不证明精确型号。

`local-photo-index.json` 只在本地保存相对文件路径、哈希和图片尺寸。两张照片是否来自同一实物未知，`physical_object_id` 留空。索引不含三维结果或组件真值。

一期设备类别已确认是组串式逆变器及外部安装结构。后续扩展箱变、变压器等类别时，应分别记录 `equipment_type`、实物 ID 和类别标注规则，再建立该类留出数据；目录名不能替代人工核对。扩展顺序见 [路线图](../docs/roadmap.md)。

## 后续建议布局

```text
photos/                       原始照片，保留原件
data/local-photo-index.json   本地文件索引
data/annotations/             组件掩码、名称、修订版本
data/processed/               缩放图、裁剪图及中间数据
data/splits/                  按物理设备分组的数据分区
artifacts/                    导出场景、网格及结果清单
models/                       下载的权重及版本记录
```

只创建当前需要的目录。上述后续目录不表示已经有相应处理代码。

## 标注要求

- 每张照片关联独立的 `capture_id`；确认同一实物后再设置共同 `physical_object_id`。
- 来源、使用范围与未知项分别记录，避免从文件名推定许可或型号。
- 组件实例与孔、槽等几何特征分开记录。可见组件数不等于完整整机零件数。
- 保存原图到裁剪图的坐标转换，掩码须能映射回原图。
- 三维尺寸只有在存在可靠参照和验证依据时才填写。示意模型默认使用相对尺度。
- 用于单图方法评测的补充实拍视角只作核查，不混入单图推理输入。

相关文档：[项目计划](../docs/plan.md) · [开发约定](../CONTRIBUTING.md)


## V3 多视角数据

一组照片须对应同一物理设备的不同角度；按设备分组划分训练／测试，不能将同设备视角拆到不同分区。`data/runtime/`中SQLite新增captures／multiview_jobs，几何在`multiview/<job>/geometry.npz`，导出在同任务目录；人工版本保留原geometry_job_id。现有V2资产／任务／细化记录保留。

本机`data/samples/vggt-kitchen/`为官方VGGT固定commit的00／01／02公开玩具样图，source.json记录链接和哈希；仅验证链路，非光伏评测集，不随仓库发布。`data/v3-preview/`与`artifacts/v3-browser/`是本地验证数据／证据，不进Git。实际用户照片、权重和结果仍需各自来源与许可记录。

当前组件契约兼容原5类，并增加connector（接线插接件）和cable_tray（电缆线槽）。历史冻结记录保持原类别；新实验保存自己的prompt与版本，不能重写旧结果。所有问题和新旧实验应连接到[质量台账](../docs/quality/README.md)。
