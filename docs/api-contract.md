# V2 API 契约

所有路由以 `/api` 开头，坐标为 EXIF 归一化后的图片比例，bbox 为 `[x1,y1,x2,y2]` 且 `0≤x1<x2≤1`、`0≤y1<y2≤1`。每个设备配置独立，一期仅 `string_inverter`。

## 路由

- `GET /api/health` → `{status:"ok", model:{state, model_id, device, error?:string|null}}`。
- `POST /api/assets`，multipart `file` → `{id,width,height,image_url,sha256}`；真实校验 JPEG／PNG／WebP，最多 20MB、解码最多 25M 像素，归一化后最长边 2048。原图与模型路径不暴露。
- `POST /api/jobs` JSON `{asset_id, mode?:"automatic"|"manual", scene_mode?:"single"|"multiple", components?:ManualComponent[], base_job_id?:string}` → `Job`；默认 automatic／single。single 筛选一个主要柜体及附近结构，multiple 保留去重后的多个候选，最多 12 个；不允许客户端任意模型 ID。`base_job_id` 仅用于人工校正、须为同一照片已完成任务；未变更组件由服务端继承原来源／分数／区域，客户端不能伪造来源。
- `GET /api/jobs/{id}` → `Job`，前端约 700ms 轮询，终态停止。
- `GET /api/jobs/{id}/result` → `Result`；未完成返回 409。
- `GET /api/assets/{id}/image` 返回规范化图片。
- `GET /api/jobs/{id}/scene.glb` 和 `/result.json` 返回同版本文件。没有有效场景时返回明确错误。
- `POST /api/refinements` JSON `{asset_id,bbox,points?:[{x,y,label:0|1}]}` → HTTP 201 `Refinement`。最多 64 点，坐标有限且归一化；正点必须在框内，负点可在框外背景。请求进入与任务共用的有界单 worker，HTTP 等待结果，不返回虚构进度百分比。
- `GET /api/refinements/{id}/mask.png` → 与照片同尺寸的透明掩码预览。仅能获取已持久化记录，ID 为 32 位十六进制。完整二值 PNG 另存本地 `refinements/<id>/binary-mask.png`，不公开任意文件路径。

`Job={id,asset_id,status,stage,created_at,elapsed_ms,error:string|null,result:Result|null}`，status 为 `queued|running|succeeded|needs_review|failed|interrupted`。启动时将未结束的旧任务标 interrupted；初期单 worker。不存在资源 404，验证失败 400／413／422，内部模型失败不回传栈或主机路径。

`stage` 由实际执行位置写入 SQLite，自动流程依次可能出现 `queued → starting → loading_model → detecting → loading_segmentation → segmenting → geometry → exporting → complete`。已加载模型会直接进入推理阶段；可选分割关闭或不可用时不伪造区域完成，结果 `model.segmentation_state` 说明仅使用候选框。人工流程为 `queued → manual_components → geometry → exporting → complete`。失败保留失败前阶段；服务重启的中断阶段为 `interrupted`。

前端将这些状态映射为六阶段或人工三阶段进度，`complete` 仅表示服务产物就绪；GLB 在浏览器载入成功后才完成最后一段。进度是阶段完成数，不是模型内部百分比。客户端单独计入上传、排队与查看器载入的实际时间；超过十秒不会自动失败。短暂阶段可能在相邻轮询间完成，不人为延长等待。

## Result

```typescript
type Category = 'cabinet' | 'bracket' | 'pole' | 'cables' | 'unknown';
type ManualComponent = {
  id?:string; category:Category; label:string; bbox:[number,number,number,number];
  refinement_id?:string|null;
};
type Component = {
  id:string; category:Category; label:string; bbox:[number,number,number,number];
  score:number|null; source:'grounding_dino'|'manual';
  primitive:'box'|'cylinder'|'cable_bundle'; color:string;
  position:[number,number,number]; dimensions:[number,number,number];
  node_name:string;
  mask_polygon?:[number,number][]|null;
  mask_polygons?:[number,number][][]|null;
  mask_model?:Record<string,unknown>|null;
  refinement_id?:string|null;
};
type Result = {
  job_id:string; asset_id:string; equipment_type:'string_inverter';
  scene_mode:'single'|'multiple';
  representation:'structural_schematic'; metric_scale_status:'unknown';
  components:Component[]; scene_url:string|null; json_url:string;
  warnings:string[]; model:Record<string,unknown>;
  timings:Record<string,number>;
};
type Refinement = {
  id:string; asset_id:string;
  bbox:[number,number,number,number]; // 原始提示框
  geometry_bbox:[number,number,number,number]; // 裁到提示框内的真实掩码外接框
  points:{x:number;y:number;label:0|1}[];
  mask_polygons:[number,number][][]; // 简化轮廓，PNG 保留全部像素
  mask_url:string; model:Record<string,unknown>;
  timings:Record<string,number>; warnings:string[];
};
```

每个 GLB 组件节点 `name=component.id` 并写 `extras.component_id`，mesh 来源为结构示意，Y 向上、归一化显示，无毫米读数。背景／支架遮挡处的深度是显式先验。无组件时 `needs_review`，不能造任意整机模型算成功。人工纠正生成新任务／结果，不覆盖自动结果；保持已有组件 ID。

人工提交只允许 `ManualComponent` 字段。`refinement_id` 非空时，服务端在创建任务前核对同一 `asset_id` 和精确存储的 `geometry_bbox`，不符返回 400；轮廓和模型信息从服务端读取。省略此字段并保持原框，可兼容 V1 的区域继承；显式 `null` 清除已有掩码，表示仅框保存。重命名／改类别后来源标为 manual，名称、类别、框与引用全部未改时沿用原来源和分数。

细化记录只新增，不覆盖；多轮修正有不同 ID。掩码裁到提示框内，最多 64 条简化轮廓、每条最多 128 点，保留孔洞／不连通部分的完整 PNG。空掩码返回 422；模型失败返回 503，队列满返回 409；错误不暴露本机路径／栈。前端保留草稿可重试或选择仅框。取消等待不保证停止已排队计算。

## 模型适配器边界

`pv3d.perception.GroundingDetector` 构造为 `GroundingDetector(cache_dir:Path,device='auto',sam_size=None)`，提供同步 `detect(image,on_progress=None,scene_mode='single')->dict`、`refine(image,bbox,points,cache_key)->dict`、`status()->dict`。适配器在模型加载、检测、分割加载和分割执行前调用 `on_progress(stage)`；任务层负责持久化。细化可独立于检测器加载，使用两个图像特征的 LRU 缓存，键包含图像身份、尺寸、checkpoint 和设备。API 允许通过 `create_app(data_dir:Path, detector=...)` 注入慢模型替身用于边界测试，生产仅用真实模型。

`detect` 返回 `{detections:[{category,label,bbox,score,source:'grounding_dino',mask_polygon?:...}], model:{model_id,revision,device,...}, timings:{...}, warnings:[...]}`。全部框为上述比例坐标。`status()` 只报告状态，不在健康查询中下载权重。首次识别可以懒加载，前端显示模型加载状态；异常交给任务层转成可见失败。生产环境禁止固定样例检测结果替代任意上传图片。
