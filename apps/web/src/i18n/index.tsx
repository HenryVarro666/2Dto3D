import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Category, EditableComponent } from "../api/types";
import { messages } from "./messages";
import type { MessageKey } from "./messages";

export type Locale = "zh" | "en" | "es";
const storageKey = "pv3d.locale";
type Params = Record<string, string | number>;

const serverMessages: Record<string, MessageKey> = {
  DERIVED_SUBPIXEL_ANCHORS_NOT_RAW_POINTS:
    "本审计包含按固定图像位置插值的端点；原始模型样本另存。",
  PUBLIC_SCAN_REFERENCE_NOT_FIELD_CERTIFICATION:
    "公开扫描参考验证，不代表现场尺寸精度。",
  WHOLE_SCENE_AUDIT_NOT_PV_COMPONENT_RECOGNITION:
    "此结果按照片视图分组，用于几何审计，不代表组件识别。",
  AUTHORED_ANALYTIC_DEMO_NOT_FIELD_ACCURACY:
    "解析测量演示未运行模型；组件细化和重建请使用真实多图结果。",
  MEASUREMENT_REFERENCE_REUSED:
    "标定线不能作为独立验证线。请选择另一条未参与标定的实测长度。",
  MEASUREMENT_GEOMETRY_CHANGED: "点云已变化，请重新载入结果并重新标定。",
  MEASUREMENT_POINT_INVALID: "所选点不存在于该点云，请重新选点。",
  MEASUREMENT_POINTS_TOO_CLOSE: "请选择两个不同位置的点。",
  MEASUREMENT_CALIBRATION_MISMATCH: "标定记录与当前任务或几何不匹配。",
  MEASUREMENT_SOURCE_REQUIRED: "请填写已知长度的来源。",
  MEASUREMENT_CALIBRATION_REQUIRED: "独立验证需要先选择有效标定。",
  MEASUREMENT_LOAD_FAILED: "测量记录未能载入，请重试。",
  MEASUREMENT_SAVE_FAILED: "测量记录保存失败，请重试。",
  MEASUREMENT_GEOMETRY_UNAVAILABLE: "当前任务没有可测量的点云。",
  MEASUREMENT_JOB_NOT_FOUND: "找不到可测量的多图任务。",
  "Multi-view processing failed. Check local model setup, retry, or return to single-photo mode.":
    "多图处理失败，请检查模型安装后重试，或使用单图模式。",
  "Use different views, not repeated copies of the same photo.":
    "请使用不同视角，不能重复上传同一张照片。",
  "Capture not found.": "照片组不存在，请重新上传。",
  "Multi-view job not found.": "多图任务不存在，请重新开始。",
  "Multi-view result is not ready.": "多图结果尚未就绪。",
  "Linked observations must use the same component name and category.":
    "关联标注的名称和类别必须一致。",
  MULTIVIEW_ASSOCIATIONS_REQUIRE_CONFIRMATION:
    "自动关联仅为候选，请核对并按需合并或拆开。",
  MULTIVIEW_TOO_FEW_VALID_VIEWS: "有效视角不足，请补拍清晰且有重叠的照片。",
  MULTIVIEW_LOW_PARALLAX: "拍摄位置变化太小，请向侧面移动后补拍。",
  MULTIVIEW_LOW_CROSS_VIEW_SUPPORT:
    "视角间的几何支持较弱，请检查是否为同一静止设备并增加重叠。",
  MULTIVIEW_NO_COMPONENTS_ADD_MANUALLY:
    "未识别到组件，请在照片中框选后应用校正。",
  MULTIVIEW_COMPONENT_WITHOUT_POINTS:
    "部分组件没有有效三维点，请细化边界或补拍近照。",
  "No usable region. Add points, redraw the box, or use the box without refinement.":
    "未得到有效区域，请补点、重新框选或仅用框保存。",
  "Boundary refinement failed. Retry or keep the box without refinement.":
    "边界细化失败，请重试或仅用框保存。",
  "Refinement must match the image and component box.":
    "区域记录与当前照片或组件框不匹配，请重新细化。",
  "Refinement not found.": "找不到边界细化记录，请重新细化。",
  "Some prompt points were not satisfied. Add points or redraw the box.":
    "部分修正点未被满足，请补点或重新框选。",
  "Model unavailable. Check local server logs.":
    "模型不可用，请检查本地服务日志。",
  "Model status unavailable.": "模型状态不可用。",
  "The server stopped before this task finished. Start a new task to try again.":
    "任务因服务重启而中断。可重新识别或手动框选。",
  "Use an actual JPEG, PNG, or WebP image.":
    "图片格式或内容无效，请选择 JPEG、PNG 或 WebP 图片。",
  "The file is not a valid supported image.":
    "图片格式或内容无效，请选择 JPEG、PNG 或 WebP 图片。",
  "The decoded image exceeds 25 million pixels.":
    "图片解码后尺寸过大，请选择较小图片。",
  "The decoded image is too large.": "图片解码后尺寸过大，请选择较小图片。",
  "The upload exceeds 20 MB.": "图片超过 20MB 上限",
  "The local processing queue is full. Retry after a task finishes.":
    "处理队列已满，请等当前任务完成后重试。",
  "The service is shutting down. Retry after it restarts.":
    "服务正在关闭，请在重启后重试。",
  "The access token is not valid.": "访问令牌无效，请检查后重试。",
  "Authentication required. Send the access token or sign in.":
    "需要访问令牌才能使用本地服务。",
  "The inference worker is busy with a long task. Retry the refinement later.":
    "推理服务正忙于较长任务，请稍后再试边界细化。",
  "The refinement mask is unavailable.": "边界细化文件不可用，请重新细化。",
  "Processing failed. Check local server logs, retry, or use manual components.":
    "处理失败，请检查本地服务日志，重试或手动框选组件。",
  "Asset not found.": "找不到照片。",
  "Job not found.": "找不到任务。",
  "The job has no completed result.": "任务尚无已完成的结果。",
  "The asset image is unavailable.": "照片文件不可用，请重新上传。",
  "The base job must belong to the same image asset.":
    "校正必须基于同一照片的任务。",
  "The result file is unavailable. Start a new task.":
    "结果文件不可用，请新建任务。",
  "There is no component scene. Add or correct components manually.":
    "没有组件场景，请手动添加或校正组件。",
  "API route not found.": "找不到 API 路由。",
  "Metric scale is unknown; all geometry uses relative display units.":
    "所有几何均采用相对显示单位，真实尺度未知。",
  "Depth and hidden surfaces use category priors, not recovered measurements.":
    "深度与隐藏面来自类别先验，并非恢复的实测数据。",
  "An exploded view explains visible component composition, not a verified disassembly procedure.":
    "分解视图用于解释可见组成，不代表经过验证的拆装流程。",
  "No usable components were recognized. Add or correct boxes manually.":
    "未识别到有效组件，请手动添加或校正候选框。",
  "An oversized or distant unknown detection was excluded from the cabinet schematic.":
    "已从柜体示意中排除过大或过远的未知候选。",
  "Manual edits were applied. Unchanged component evidence is retained from the base result.":
    "已应用人工校正，未修改组件保留原有识别依据。",
  MPS_FALLBACK_CPU: "MPS 推理已回退到 CPU。",
  SAM2_UNAVAILABLE_BBOX_ONLY: "SAM 2 不可用，保留真实检测框，不使用伪造区域。",
  SAM2_EMPTY_AUTOMATIC_REGION_BBOX_ONLY:
    "自动分割未得到框内区域，保留候选框供人工修正。",
};

export const categoryKeys: Record<Category, MessageKey> = {
  cabinet: "逆变器机柜",
  bracket: "安装支架",
  pole: "立柱 / 支撑",
  cables: "线缆束",
  connector: "接线插接件",
  cable_tray: "电缆线槽",
  unknown: "其他组件",
};
const defaultNames = new Set<string>([
  "主机外壳",
  "逆变器机柜",
  "安装支架",
  "支撑立柱",
  "线缆束",
  "接线插接件",
  "电缆线槽",
]);

function translator(locale: Locale) {
  const t = (source: MessageKey, params: Params = {}) => {
    const text =
      locale === "zh" ? source : messages[source][locale === "en" ? 0 : 1];
    return text.replace(/\{(\w+)\}/g, (placeholder, key: string) =>
      Object.hasOwn(params, key) ? String(params[key]) : placeholder,
    );
  };
  const localize = (message: string) => {
    if (Object.hasOwn(messages, message)) return t(message as MessageKey);
    if (Object.hasOwn(serverMessages, message))
      return t(serverMessages[message]);
    const status = /^请求未完成（(\d{3})），请重试。$/.exec(message);
    return status
      ? t("请求未完成（{status}），请重试。", { status: status[1] })
      : message;
  };
  const componentLabel = (component: EditableComponent) =>
    (component.labelEdited === false ||
      (component.labelEdited === undefined &&
        component.source === "grounding_dino")) &&
    defaultNames.has(component.label)
      ? t(component.label as MessageKey)
      : component.label;
  return { locale, t, localize, componentLabel };
}

const I18nContext = createContext({
  ...translator("zh"),
  setLocale: (_locale: Locale) => {},
});

function savedLocale(): Locale {
  try {
    const locale = localStorage.getItem(storageKey);
    return locale === "en" || locale === "es" ? locale : "zh";
  } catch {
    return "zh";
  }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(savedLocale);
  const value = useMemo(() => ({ ...translator(locale), setLocale }), [locale]);
  useEffect(() => {
    document.documentElement.lang = locale === "zh" ? "zh-CN" : locale;
    document.title = `${value.t("设备结构工作台")} · PV Structure`;
    try {
      localStorage.setItem(storageKey, locale);
    } catch {
      /* Switching still works if storage is blocked. */
    }
  }, [locale, value]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
