import { useRef, useState } from "react";
import { useI18n } from "../i18n";
import { metricCheckLabels } from "./PublicMetricBenchmark";

type Check = {
  segment_id: string;
  reference_mm: number;
  calibrated_mm: number;
  relative_error_pct: number;
};
type Run = {
  scene: string;
  image_condition: string;
  resize_mode: string;
  status: string;
  input_size: number;
  reference_lengths_mm: number[];
  checks?: Check[];
  job_id?: string;
  model?: {
    revision?: string;
    code_revision?: string;
    protocol_sha256?: string;
    resize_mode?: string;
  };
  layout: { rect: number[]; mapping_rect: number[]; scale_xy: number[] };
  input_preview_url?: string;
  preview_points?: { id: string; uv: number[] }[];
  diagnostics?: {
    points: {
      point_index: number;
      true_camera_z_mm: number;
      primary_scale_camera_z_mm: number;
    }[];
    known_K_auxiliary?: {
      checks: { segment_id: string; relative_error_pct: number }[];
    };
  };
};
type Summary = { protocol_sha256: string; runs: Run[] };

function comparable(a: Run | undefined, b: Run | undefined, protocol: string) {
  if (
    !a ||
    !b ||
    a.resize_mode !== "legacy14" ||
    b.resize_mode !== "isotropic" ||
    a.image_condition !== b.image_condition
  )
    return false;
  if (
    [a, b].some(
      (r) =>
        r.status !== "succeeded" ||
        r.input_size !== 518 ||
        r.model?.protocol_sha256 !== protocol ||
        r.model?.resize_mode !== r.resize_mode ||
        r.checks?.length !== 4 ||
        r.reference_lengths_mm.length !== 5,
    )
  )
    return false;
  return (
    a.model?.revision === b.model?.revision &&
    a.model?.code_revision === b.model?.code_revision &&
    a.reference_lengths_mm.every(
      (v, i) => Number.isFinite(v) && v > 0 && v === b.reference_lengths_mm[i],
    ) &&
    new Set(a.checks!.map((c) => c.segment_id)).size === 4 &&
    new Set(b.checks!.map((c) => c.segment_id)).size === 4 &&
    a.checks!.every(
      (c) =>
        Object.hasOwn(metricCheckLabels, c.segment_id) &&
        b.checks!.some(
          (d) =>
            d.segment_id === c.segment_id && d.reference_mm === c.reference_mm,
        ),
    ) &&
    [...a.checks!, ...b.checks!].every(
      (c) =>
        Number.isFinite(c.calibrated_mm) &&
        c.calibrated_mm > 0 &&
        Number.isFinite(c.relative_error_pct) &&
        c.relative_error_pct >= 0,
    )
  );
}

function InputPreview({ run }: { run: Run }) {
  const { t } = useI18n(),
    [missing, setMissing] = useState(false);
  const mode = t(run.resize_mode === "legacy14" ? "当前14对齐" : "保比例缩放");
  if (missing || !run.input_preview_url || run.preview_points?.length !== 10)
    return (
      <p className="metric-scope-note">
        {t("本机尚无该归档照片；可先准备数据，或载入新运行的任务 ID。")}
      </p>
    );
  return (
    <figure className="fixed-point-preview">
      <div style={{ aspectRatio: "1" }}>
        <img
          src={run.input_preview_url}
          alt={`${run.scene} · ${mode}`}
          onError={() => setMissing(true)}
        />
        <svg viewBox="0 0 518 518" aria-label={t("固定实际取点标记")}>
          {[0, 2, 4, 6, 8].map((i) => (
            <line
              key={i}
              x1={run.preview_points![i].uv[0] * 518}
              y1={run.preview_points![i].uv[1] * 518}
              x2={run.preview_points![i + 1].uv[0] * 518}
              y2={run.preview_points![i + 1].uv[1] * 518}
              stroke={i === 0 ? "#ffb547" : "#36f2c9"}
              strokeWidth="1.5"
            />
          ))}
          {run.preview_points.map((p, i) => (
            <g key={p.id}>
              <circle
                aria-label={t("固定点 {scene} {id}", {
                  scene: run.scene,
                  id: p.id,
                })}
                cx={p.uv[0] * 518}
                cy={p.uv[1] * 518}
                r="3.5"
                fill={i < 2 ? "#ffb547" : "#36f2c9"}
                stroke="#18382e"
              />
              <text
                x={p.uv[0] * 518 + 5}
                y={p.uv[1] * 518 - 5}
                fontSize="12"
                fontWeight="700"
                fill={i < 2 ? "#ffb547" : "#36f2c9"}
                stroke="#18382e"
                strokeWidth=".4"
                paintOrder="stroke"
              >
                {p.id}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <figcaption>
        {run.scene} · {mode} · 518×518
      </figcaption>
    </figure>
  );
}

export function ResizeComparison({
  data,
  disabled,
  onRestore,
}: {
  data: Summary;
  disabled: boolean;
  onRestore: (id: string) => void;
}) {
  const { t } = useI18n();
  const details = useRef<HTMLDetailsElement>(null);
  const [condition, setCondition] = useState("rectified"),
    [photosOpen, setPhotosOpen] = useState(false);
  const rows = data.runs.filter((r) => r.image_condition === condition);
  const pairs = [...new Set(rows.map((r) => r.scene))].map((scene) => ({
    scene,
    before: rows.find((r) => r.scene === scene && r.resize_mode === "legacy14"),
    after: rows.find((r) => r.scene === scene && r.resize_mode === "isotropic"),
  }));
  const complete =
    rows.length === 4 &&
    pairs.length === 2 &&
    pairs.every((p) => comparable(p.before, p.after, data.protocol_sha256));
  const errors = (mode: string) =>
    rows
      .filter((r) => r.resize_mode === mode)
      .flatMap((r) => r.checks ?? [])
      .map((c) => c.relative_error_pct);
  const mean = (mode: string) => {
    const e = errors(mode);
    return (e.reduce((a, b) => a + b, 0) / e.length).toFixed(2);
  };
  const deltas = complete
    ? pairs.flatMap((p) =>
        p.before!.checks!.map(
          (c) =>
            p.after!.checks!.find((d) => c.segment_id === d.segment_id)!
              .relative_error_pct - c.relative_error_pct,
        ),
      )
    : [];
  const first = pairs[0],
    kicker = pairs.find((p) => p.scene === "kicker");
  const beforeAux = kicker?.before?.diagnostics?.known_K_auxiliary?.checks.find(
    (c) => c.segment_id === "kicker-3",
  );
  const afterAux = kicker?.after?.diagnostics?.known_K_auxiliary?.checks.find(
    (c) => c.segment_id === "kicker-3",
  );
  function restore(run: Run | undefined) {
    if (!run?.job_id || run.status !== "succeeded") return;
    if (details.current) details.current.open = false;
    onRestore(run.job_id);
  }
  return (
    <details
      className="public-metric-benchmark resize-comparison"
      ref={details}
      id="resize-comparison"
    >
      <summary>
        <strong>{t("缩放方式同点对照")}</strong>
        <span>E09 · VGGT · 518 px · {t("固定20个扫描参考点")}</span>
      </summary>
      <section aria-label={t("缩放方式同点对照")}>
        <p className="metric-reference-kind">
          {t("图像条件固定；只比较缩放方式。每场景 A–B 标定，四条长度仅验证。")}
        </p>
        <fieldset className="resize-condition">
          <legend>{t("图像条件（缩放对照）")}</legend>
          {(["rectified", "original"] as const).map((c) => (
            <label key={c}>
              <input
                type="radio"
                name="resize-image-condition"
                value={c}
                checked={condition === c}
                onChange={() => setCondition(c)}
              />
              {t(c === "rectified" ? "固定去畸变图" : "固定原图")}
            </label>
          ))}
        </fieldset>
        {complete ? (
          <>
            <div className="metric-overview">
              {(["legacy14", "isotropic"] as const).map((m) => (
                <div key={m}>
                  <span>
                    {t(m === "legacy14" ? "当前14对齐" : "保比例缩放")}
                  </span>
                  <strong>{mean(m)}%</strong>
                  <small>{t("平均绝对百分比误差")} · n=8</small>
                </div>
              ))}
              <p>
                {t("{better} 条改善，{worse} 条退步；复跑不增加独立样本数。", {
                  better: deltas.filter((v) => v < 0).length,
                  worse: deltas.filter((v) => v > 0).length,
                })}
              </p>
            </div>
            <p>
              {t("当前有效内容 {width}×{height}；纵横拉伸 {stretch}%。", {
                width: (
                  first.before!.layout.mapping_rect[2] -
                  first.before!.layout.mapping_rect[0]
                ).toFixed(0),
                height: (
                  first.before!.layout.mapping_rect[3] -
                  first.before!.layout.mapping_rect[1]
                ).toFixed(0),
                stretch: (
                  (first.before!.layout.scale_xy[1] /
                    first.before!.layout.scale_xy[0] -
                    1) *
                  100
                ).toFixed(2),
              })}
            </p>
            <p>
              {t(
                "保比例有效内容 {width}×{height}，存储高度 {stored}；实际取点使用连续映射。",
                {
                  width: (
                    first.after!.layout.mapping_rect[2] -
                    first.after!.layout.mapping_rect[0]
                  ).toFixed(0),
                  height: (
                    first.after!.layout.mapping_rect[3] -
                    first.after!.layout.mapping_rect[1]
                  ).toFixed(3),
                  stored:
                    first.after!.layout.rect[3] - first.after!.layout.rect[1],
                },
              )}
            </p>
          </>
        ) : (
          <p role="status">{t("对照条件不一致或运行未完成，暂不汇总误差。")}</p>
        )}
        <p className="metric-scope-note">
          {t(
            "原图与去畸变分层不混算；有效像素覆盖和白边也随缩放变化，不能单独确定深度模型的根因。",
          )}
        </p>
        <div className="undistortion-runs">
          {pairs.map((p) => (
            <article key={p.scene}>
              <header>
                <h3>{p.scene} · 518 px</h3>
                <div className="workspace-actions">
                  <button
                    className="button secondary"
                    disabled={disabled || p.before?.status !== "succeeded"}
                    onClick={() => restore(p.before)}
                  >
                    {t("查看当前点云")}
                  </button>
                  <button
                    className="button secondary"
                    disabled={disabled || p.after?.status !== "succeeded"}
                    onClick={() => restore(p.after)}
                  >
                    {t("查看保比例点云")}
                  </button>
                </div>
              </header>
              {comparable(p.before, p.after, data.protocol_sha256) ? (
                <div className="metric-table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>{t("独立检查线")}</th>
                        <th>{t("共同扫描参考")}</th>
                        <th>{t("当前：校准长度 / 误差")}</th>
                        <th>{t("保比例：校准长度 / 误差")}</th>
                        <th>{t("误差变化（百分点）")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.before!.checks!.map((c) => {
                        const a = p.after!.checks!.find(
                            (a) => a.segment_id === c.segment_id,
                          )!,
                          delta = a.relative_error_pct - c.relative_error_pct;
                        return (
                          <tr key={c.segment_id}>
                            <th scope="row">
                              {t(metricCheckLabels[c.segment_id])}
                            </th>
                            <td>{c.reference_mm.toFixed(1)} mm</td>
                            <td>
                              {c.calibrated_mm.toFixed(1)} mm ·{" "}
                              {c.relative_error_pct.toFixed(2)}%
                            </td>
                            <td>
                              {a.calibrated_mm.toFixed(1)} mm ·{" "}
                              {a.relative_error_pct.toFixed(2)}%
                            </td>
                            <td
                              className={
                                delta > 0
                                  ? "metric-large-error"
                                  : "metric-lower-error"
                              }
                            >
                              {delta > 0 ? "+" : ""}
                              {delta.toFixed(2)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p>{t("此场景对照暂不可用。")}</p>
              )}
            </article>
          ))}
        </div>
        <details
          className="fixed-point-photos"
          onToggle={(e) => {
            if (e.currentTarget === e.target)
              setPhotosOpen(e.currentTarget.open);
          }}
        >
          <summary>{t("实际518输入与同点标记")}</summary>
          <p>
            {t(
              "橙色 A–B 用于标定，绿色 C–J 仅验证；同名标记对应同一扫描点，按各自缩放映射取样。",
            )}
          </p>
          <p className="metric-scope-note">
            {t(
              "模型输入预览来自实际准备张量；JPEG仅供查看，原始PNG和哈希保留。",
            )}
          </p>
          {photosOpen && (
            <div className="fixed-point-photo-grid">
              {pairs
                .flatMap((p) => [p.before, p.after])
                .filter((r): r is Run => !!r)
                .map((r) => (
                  <InputPreview
                    key={`${r.scene}-${r.image_condition}-${r.resize_mode}`}
                    run={r}
                  />
                ))}
            </div>
          )}
        </details>
        {complete &&
          kicker?.before?.diagnostics &&
          kicker.after?.diagnostics && (
            <details className="fixed-point-diagnostics">
              <summary>{t("跨墙与后墙深度诊断")}</summary>
              <p>
                {t(
                  "下列深度使用各自 A–B 比例并依赖相机估计，用于定位问题，不能单独确定根因。",
                )}
              </p>
              <div className="metric-table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>{t("固定点")}</th>
                      <th>{t("扫描 Z")}</th>
                      <th>{t("当前 Z（校准后）")}</th>
                      <th>{t("保比例 Z（校准后）")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[2, 3, 6, 7].map((i) => {
                      const a = kicker.before!.diagnostics!.points.find(
                          (p) => p.point_index === i,
                        ),
                        b = kicker.after!.diagnostics!.points.find(
                          (p) => p.point_index === i,
                        );
                      return a && b ? (
                        <tr key={i}>
                          <th scope="row">{String.fromCharCode(65 + i)}</th>
                          <td>{a.true_camera_z_mm.toFixed(1)} mm</td>
                          <td>{a.primary_scale_camera_z_mm.toFixed(1)} mm</td>
                          <td>{b.primary_scale_camera_z_mm.toFixed(1)} mm</td>
                        </tr>
                      ) : null;
                    })}
                  </tbody>
                </table>
              </div>
              {beforeAux && afterAux && (
                <p>
                  {t(
                    "已知 K 辅助跨墙误差：当前 {before}%，保比例 {after}%；各自只用 A–B 拟合辅助比例，不计入主结果。",
                    {
                      before: beforeAux.relative_error_pct.toFixed(2),
                      after: afterAux.relative_error_pct.toFixed(2),
                    },
                  )}
                </p>
              )}
            </details>
          )}
        <p>
          {t(
            "点云另含明确标记的插值端点审计层，原始模型样本另存。原始 GLB / PLY 仍为相对尺度；这些结果不代表现场毫米精度。",
          )}
        </p>
        <p className="metric-source-links">
          <a
            href="https://github.com/HenryVarro666/2Dto3D/blob/main/docs/quality/2026-11-01-aspect-ratio-fixed-points.md"
            target="_blank"
            rel="noreferrer"
          >
            {t("完整结果与复现步骤")} ↗
          </a>
          <span>ETH3D · CC BY-NC-SA 4.0 · E09</span>
        </p>
      </section>
    </details>
  );
}
