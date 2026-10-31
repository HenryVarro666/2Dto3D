# 一期 API 契约

所有路由以 `/api` 开头，坐标为 EXIF 归一化后的图片比例，bbox 为 `[x1,y1,x2,y2]` 且 `0≤x1<x2≤1`、`0≤y1<y2≤1`。每个设备配置独立，一期仅 `string_inverter`。

## 路由

- `GET /api/health` → `{status:"ok", model:{state, model_id, device, error?:string|null}}`。
- `POST /api/assets`，multipart `file` → `{id,width,height,image_url,sha256}`；真实校验 JPEG／PNG／WebP，最多 20MB、解码最多 25M 像素，归一化后最长边 2048。原图与模型路径不暴露。
- `POST /api/jobs` JSON `{asset_id, mode?:"automatic"|"manual", components?:ManualComponent[], base_job_id?:string}` → `Job`；自动模式默认，不允许客户端任意模型 ID。`base_job_id` 仅用于人工校正、须为同一照片已完成任务；未变更组件由服务端继承原来源／分数／区域，客户端不能伪造来源。
- `GET /api/jobs/{id}` → `Job`，前端约 700ms 轮询，终态停止。
- `GET /api/jobs/{id}/result` → `Result`；未完成返回 409。
- `GET /api/assets/{id}/image` 返回规范化图片。
- `GET /api/jobs/{id}/scene.glb` 和 `/result.json` 返回同版本文件。没有有效场景时返回明确错误。

`Job={id,asset_id,status,stage,created_at,elapsed_ms,error:string|null,result:Result|null}`，status 为 `queued|running|succeeded|needs_review|failed|interrupted`。启动时将未结束的旧任务标 interrupted；初期单 worker。不存在资源 404，验证失败 400／413／422，内部模型失败不回传栈或主机路径。

## Result

```typescript
type Category = 'cabinet' | 'bracket' | 'pole' | 'cables' | 'unknown';
type ManualComponent = {id?:string; category:Category; label:string; bbox:[number,number,number,number]};
type Component = {
  id:string; category:Category; label:string; bbox:[number,number,number,number];
  score:number|null; source:'grounding_dino'|'manual';
  primitive:'box'|'cylinder'|'cable_bundle'; color:string;
  position:[number,number,number]; dimensions:[number,number,number];
  node_name:string;
  mask_polygon?:[number,number][]|null;
};
type Result = {
  job_id:string; asset_id:string; equipment_type:'string_inverter';
  representation:'structural_schematic'; metric_scale_status:'unknown';
  components:Component[]; scene_url:string|null; json_url:string;
  warnings:string[]; model:Record<string,unknown>;
  timings:Record<string,number>;
};
```

每个 GLB 组件节点 `name=component.id` 并写 `extras.component_id`，mesh 来源为结构示意，Y 向上、归一化显示，无毫米读数。背景／支架遮挡处的深度是显式先验。无组件时 `needs_review`，不能造任意整机模型算成功。人工纠正生成新任务／结果，不覆盖自动结果；保持已有组件 ID。

## 模型适配器边界

root 维护 `pv3d.perception.GroundingDetector`，构造 `GroundingDetector(cache_dir:Path,device='auto')`，同步 `detect(image:PIL.Image.Image)->dict`、`status()->dict`。API 允许通过 `create_app(data_dir:Path, detector=...)` 注入慢模型替身用于边界测试，生产仅用真实模型。

`detect` 返回 `{detections:[{category,label,bbox,score,source:'grounding_dino',mask_polygon?:...}], model:{model_id,revision,device,...}, timings:{...}, warnings:[...]}`。全部框为上述比例坐标。`status()` 只报告状态，不在健康查询中下载权重。首次识别可以懒加载，前端显示模型加载状态；异常交给任务层转成可见失败。生产环境禁止固定样例检测结果替代任意上传图片。
