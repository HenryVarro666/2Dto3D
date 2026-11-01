import { useRef, useState } from "react";
import source from "../../../../docs/measurement/undistortion-results.json";
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
  condition: string;
  status: string;
  input_size: number;
  reference_lengths_mm: number[];
  job_id?: string;
  checks?: Check[];
  worker_wall_ms?: number;
  model?: { revision?: string; protocol_sha256?: string };
  preview_image_url?: string;
  preview_size?: number[];
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

function comparable(
  before: Run | undefined,
  after: Run | undefined,
  protocol: string,
) {
  if (
    !before ||
    !after ||
    [before, after].some(
      (r) =>
        r.status !== "succeeded" ||
        r.input_size !== 518 ||
        r.checks?.length !== 4 ||
        r.model?.protocol_sha256 !== protocol,
    )
  )
    return false;
  return (
    before.model?.revision === after.model?.revision &&
    before.reference_lengths_mm.length === 5 &&
    before.reference_lengths_mm.every(
      (v, i) => v === after.reference_lengths_mm[i],
    ) &&
    new Set(before.checks!.map((c) => c.segment_id)).size === 4 &&
    before.checks!.every((a) =>
      after.checks!.some(
        (b) =>
          a.segment_id === b.segment_id && a.reference_mm === b.reference_mm,
      ),
    )
  );
}

function PointPreview({ run }: { run: Run }) {
  const { t } = useI18n();
  const [missing, setMissing] = useState(false);
  if (
    missing ||
    !run.preview_image_url ||
    !run.preview_points ||
    !run.preview_size
  )
    return (
      <p className="metric-scope-note">
        {t("本机尚无该归档照片；可先准备数据，或载入新运行的任务 ID。")}
      </p>
    );
  const height = (1000 * run.preview_size[1]) / run.preview_size[0];
  return (
    <figure className="fixed-point-preview">
      <div
        style={{ aspectRatio: `${run.preview_size[0]}/${run.preview_size[1]}` }}
      >
        <img
          src={run.preview_image_url}
          alt={`${run.scene} · ${t(run.condition === "original" ? "原图输入" : "去畸变输入")}`}
          onError={() => setMissing(true)}
        />
        <svg viewBox={`0 0 1000 ${height}`} aria-label={t("固定实际取点标记")}>
          {[0, 2, 4, 6, 8].map((i) => {
            const a = run.preview_points![i].uv,
              b = run.preview_points![i + 1].uv;
            return (
              <line
                key={i}
                x1={a[0] * 1000}
                y1={a[1] * height}
                x2={b[0] * 1000}
                y2={b[1] * height}
                stroke={i === 0 ? "#ffb547" : "#36f2c9"}
                strokeWidth="3"
              />
            );
          })}
          {run.preview_points.map((p, i) => (
            <g key={p.id}>
              <circle
                aria-label={t("固定点 {scene} {id}", {
                  scene: run.scene,
                  id: p.id,
                })}
                cx={p.uv[0] * 1000}
                cy={p.uv[1] * height}
                r="7"
                fill={i < 2 ? "#ffb547" : "#36f2c9"}
                stroke="#18382e"
                strokeWidth="2"
              />
              <text
                x={p.uv[0] * 1000 + 10}
                y={p.uv[1] * height - 10}
                fontSize="23"
                fontWeight="700"
                fill={i < 2 ? "#ffb547" : "#36f2c9"}
                stroke="#18382e"
                strokeWidth=".7"
                paintOrder="stroke"
              >
                {p.id}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <figcaption>
        {run.scene} ·{" "}
        {t(run.condition === "original" ? "原图输入" : "去畸变输入")}
      </figcaption>
    </figure>
  );
}

export function UndistortionComparison({
  onRestore,
  disabled,
  data = source,
}: {
  onRestore: (id: string) => void;
  disabled: boolean;
  data?: Summary;
}) {
  const { t } = useI18n();
  const details = useRef<HTMLDetailsElement>(null);
  const [photosOpen, setPhotosOpen] = useState(false);
  const pairs = [...new Set(data.runs.map((r) => r.scene))].map((scene) => ({
    scene,
    before: data.runs.find(
      (r) => r.scene === scene && r.condition === "original",
    ),
    after: data.runs.find(
      (r) => r.scene === scene && r.condition === "rectified",
    ),
  }));
  const complete =
    pairs.length === 2 &&
    pairs.every((p) => comparable(p.before, p.after, data.protocol_sha256));
  const errors = (condition: string) =>
    data.runs
      .filter((r) => r.condition === condition)
      .flatMap((r) => r.checks ?? [])
      .map((c) => c.relative_error_pct);
  const mean = (condition: string) => {
    const e = errors(condition);
    return (e.reduce((a, b) => a + b, 0) / e.length).toFixed(2);
  };
  const deltas = complete
    ? pairs.flatMap((p) =>
        p.before!.checks!.map(
          (c) =>
            p.after!.checks!.find((a) => a.segment_id === c.segment_id)!
              .relative_error_pct - c.relative_error_pct,
        ),
      )
    : [];
  const kicker = pairs.find((p) => p.scene === "kicker");
  const crossAux = kicker?.after?.diagnostics?.known_K_auxiliary?.checks.find(
    (c) => c.segment_id === "kicker-3",
  );
  function restore(run: Run | undefined) {
    if (!run?.job_id || run.status !== "succeeded") return;
    if (details.current) details.current.open = false;
    onRestore(run.job_id);
  }
  return (
    <details
      className="public-metric-benchmark undistortion-comparison"
      ref={details}
      id="undistortion-comparison"
    >
      <summary>
        <strong>{t("同点去畸变对照")}</strong>
        <span>E08 · VGGT · 518 px · {t("固定20个扫描参考点")}</span>
      </summary>
      <section aria-label={t("同点去畸变对照")}>
        <p className="metric-reference-kind">
          {t(
            "模型、分辨率和实际参考点固定；每场景只用 A–B 标定，四条检查线不参与拟合。",
          )}
        </p>
        {complete ? (
          <div className="metric-overview">
            {(["original", "rectified"] as const).map((c) => (
              <div key={c}>
                <span>{t(c === "original" ? "原图输入" : "去畸变输入")}</span>
                <strong>{mean(c)}%</strong>
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
        ) : (
          <p role="status">{t("对照条件不一致或运行未完成，暂不汇总误差。")}</p>
        )}
        <p className="metric-scope-note">
          {t(
            "E08 使用固定扫描坐标和亚像素深度取样，已重算原图基线；请与 E07 的最近顶点结果分开阅读。",
          )}
        </p>
        <p>
          {t(
            "去畸变使用数据集已知相机标定，保留源视场边界；无效白边约1.24%。相机标定是额外信息，普通现场照片未必具备。",
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
                    {t("原图点云")}
                  </button>
                  <button
                    className="button secondary"
                    disabled={disabled || p.after?.status !== "succeeded"}
                    onClick={() => restore(p.after)}
                  >
                    {t("去畸变点云")}
                  </button>
                </div>
              </header>
              {comparable(p.before, p.after, data.protocol_sha256) ? (
                <div className="metric-table-scroll">
                  <table>
                    <caption className="visually-hidden">
                      {p.scene} · {t("同一实际位置，前后参考长度一致")}
                    </caption>
                    <thead>
                      <tr>
                        <th>{t("独立检查线")}</th>
                        <th>{t("共同扫描参考")}</th>
                        <th>{t("原图：校准长度 / 误差")}</th>
                        <th>{t("去畸变：校准长度 / 误差")}</th>
                        <th>{t("误差变化（百分点）")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.before!.checks!.map((c) => {
                        const a = p.after!.checks!.find(
                          (a) => a.segment_id === c.segment_id,
                        )!;
                        const delta =
                          a.relative_error_pct - c.relative_error_pct;
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
            if (e.target === e.currentTarget)
              setPhotosOpen(e.currentTarget.open);
          }}
        >
          <summary>{t("同一物理点的照片对照")}</summary>
          <p>
            {t(
              "橙色 A–B 只用于标定，绿色 C–J 用于检查；同名标记对应同一扫描点，像素位置随去畸变映射变化。",
            )}
          </p>
          {photosOpen && (
            <div className="fixed-point-photo-grid">
              {pairs
                .flatMap((p) => [p.before, p.after])
                .filter((r): r is Run => Boolean(r))
                .map((r) => (
                  <PointPreview key={`${r.scene}-${r.condition}`} run={r} />
                ))}
            </div>
          )}
        </details>
        {complete &&
          kicker?.before?.diagnostics &&
          kicker.after?.diagnostics && (
            <details className="fixed-point-diagnostics">
              <summary>{t("518 难例的深度诊断")}</summary>
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
                      <th>{t("原图 Z（校准后）")}</th>
                      <th>{t("去畸变 Z（校准后）")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[2, 3, 6, 7].map((i) => {
                      const a = kicker.before!.diagnostics!.points[i],
                        b = kicker.after!.diagnostics!.points[i];
                      return (
                        <tr key={i}>
                          <th scope="row">{String.fromCharCode(65 + i)}</th>
                          <td>{a.true_camera_z_mm.toFixed(1)} mm</td>
                          <td>{a.primary_scale_camera_z_mm.toFixed(1)} mm</td>
                          <td>{b.primary_scale_camera_z_mm.toFixed(1)} mm</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {crossAux && (
                <p>
                  {t(
                    "同一预测深度使用已知内参并另用 A–B 标定后，跨墙误差仍为 {error}%；此辅助结果不计入主对照。",
                    { error: crossAux.relative_error_pct.toFixed(2) },
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
            href="https://github.com/HenryVarro666/2Dto3D/blob/main/docs/quality/2026-11-01-undistortion-fixed-points.md"
            target="_blank"
            rel="noreferrer"
          >
            {t("完整结果与复现步骤")} ↗
          </a>
          <span>ETH3D · CC BY-NC-SA 4.0 · E08</span>
        </p>
      </section>
    </details>
  );
}
