import { useState } from "react";
import { useI18n } from "../i18n";

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
  view_count: number;
  reference_lengths_mm: number[];
  model?: {
    revision?: string;
    code_revision?: string;
    protocol_sha256?: string;
    resize_mode?: string;
  };
  checks?: Check[];
  job_id?: string;
  worker_wall_ms?: number;
  input_preview_url?: string;
  preview_points?: { id: string; uv: number[] }[];
  diagnostics?: {
    known_K_auxiliary?: {
      checks: { segment_id: string; relative_error_pct: number }[];
    };
  };
};
type Sources = {
  scenes: {
    id: string;
    reference_lengths_mm: number[];
    segments: { id: string; label: string; kind: string }[];
  }[];
};
type Results = {
  protocol_sha256: string;
  repeat_exact: boolean;
  runs: Run[];
  source_gallery: {
    scene: string;
    views: { filename: string; image_url: string }[];
  }[];
};
const policies = [
  ["original", "legacy14"],
  ["original", "isotropic"],
  ["rectified", "legacy14"],
  ["rectified", "isotropic"],
] as const;
const scenes = {
  office: "办公室",
  delivery_area: "卸货区",
  terrains: "材料展示走廊",
} as const;

function complete(data: Results, sources: Sources) {
  if (!sources.scenes.length || data.runs.length !== sources.scenes.length * 4)
    return false;
  return sources.scenes.every((s) =>
    policies.every(([condition, mode]) => {
      const matches = data.runs.filter(
        (r) =>
          r.scene === s.id &&
          r.image_condition === condition &&
          r.resize_mode === mode,
      );
      if (matches.length !== 1) return false;
      const r = matches[0];
      return (
        r.status === "succeeded" &&
        r.input_size === 518 &&
        r.view_count === 3 &&
        r.model?.revision === "860abec7937da0a4c03c41d3c269c366e82abdf9" &&
        r.model?.code_revision === "a288dd0f14786c93483e45524328726ab7b1b4ce" &&
        r.model?.protocol_sha256 === data.protocol_sha256 &&
        r.model?.resize_mode === mode &&
        r.reference_lengths_mm.length === 5 &&
        s.reference_lengths_mm.length === 5 &&
        r.reference_lengths_mm.every(
          (v, i) =>
            Number.isFinite(v) && v > 0 && v === s.reference_lengths_mm[i],
        ) &&
        r.checks?.length === 4 &&
        s.segments.length === 5 &&
        new Set(r.checks.map((c) => c.segment_id)).size === 4 &&
        s.segments
          .slice(1)
          .every((segment, i) =>
            r.checks!.some(
              (c) =>
                c.segment_id === segment.id &&
                c.reference_mm === s.reference_lengths_mm[i + 1] &&
                Number.isFinite(c.calibrated_mm) &&
                c.calibrated_mm > 0 &&
                Number.isFinite(c.relative_error_pct) &&
                c.relative_error_pct >= 0 &&
                Math.abs(
                  c.relative_error_pct -
                    Math.abs(c.calibrated_mm / c.reference_mm - 1) * 100,
                ) < 1e-6,
            ),
          )
      );
    }),
  );
}

function Photo({ src, alt }: { src: string; alt: string }) {
  const { t } = useI18n(),
    [missing, setMissing] = useState(false);
  return missing ? (
    <p className="metric-scope-note">
      {t("本机尚无该归档照片；可先准备数据，或载入新运行的任务 ID。")}
    </p>
  ) : (
    <img src={src} alt={alt} loading="lazy" onError={() => setMissing(true)} />
  );
}

function PreparedPreview({ run }: { run: Run }) {
  const { t } = useI18n();
  const [missing, setMissing] = useState(false);
  return (
    <figure className="fixed-point-preview">
      <div style={{ aspectRatio: "1" }}>
        {missing || !run.input_preview_url ? (
          <p className="metric-scope-note">
            {t("本机尚无该归档照片；可先准备数据，或载入新运行的任务 ID。")}
          </p>
        ) : (
          <>
            <img
              src={run.input_preview_url}
              alt={`${run.scene} · ${run.resize_mode} · 518`}
              onError={() => setMissing(true)}
              loading="lazy"
            />
            <svg viewBox="0 0 518 518" aria-label={t("固定实际取点标记")}>
              {[0, 2, 4, 6, 8].map((i) => {
                const a = run.preview_points?.[i]?.uv,
                  b = run.preview_points?.[i + 1]?.uv;
                return a && b ? (
                  <line
                    key={i}
                    x1={a[0] * 518}
                    y1={a[1] * 518}
                    x2={b[0] * 518}
                    y2={b[1] * 518}
                    stroke={i ? "#25bfa4" : "#ffb547"}
                    strokeWidth="2"
                  />
                ) : null;
              })}
              {run.preview_points?.map((p) => (
                <g key={p.id}>
                  <circle
                    cx={p.uv[0] * 518}
                    cy={p.uv[1] * 518}
                    r="5"
                    fill={p.id < "C" ? "#ffb547" : "#25bfa4"}
                    stroke="#142f2e"
                  />
                  <text
                    x={p.uv[0] * 518 + 7}
                    y={p.uv[1] * 518 - 7}
                    fill="white"
                    stroke="#142f2e"
                    strokeWidth="3"
                    paintOrder="stroke"
                    fontSize="16"
                  >
                    {p.id}
                  </text>
                </g>
              ))}
            </svg>
          </>
        )}
      </div>
      <figcaption>
        {t(run.resize_mode === "legacy14" ? "当前14对齐" : "保比例缩放")}
      </figcaption>
    </figure>
  );
}

export function IndependentScenes({
  data,
  sources,
  disabled,
  onRestore,
}: {
  data: Results;
  sources: Sources;
  disabled: boolean;
  onRestore: (id: string) => void;
}) {
  const { t, localize } = useI18n();
  const [scene, setScene] = useState(sources.scenes[0]?.id ?? "office"),
    [condition, setCondition] = useState("rectified");
  const ready = complete(data, sources);
  const sceneName = (id: string) =>
    Object.hasOwn(scenes, id) ? t(scenes[id as keyof typeof scenes]) : id;
  const title = (condition: string, mode: string) =>
    `${t(condition === "original" ? "原图 RGB" : "去畸变 RGB")} · ${t(mode === "legacy14" ? "当前14对齐" : "保比例缩放")}`;
  const row = (id: string, condition: string, mode: string) =>
    data.runs.find(
      (r) =>
        r.scene === id &&
        r.image_condition === condition &&
        r.resize_mode === mode,
    );
  const crossIds = new Set(
    sources.scenes.flatMap((s) =>
      s.segments.filter((v) => v.kind === "cross_wall").map((v) => v.id),
    ),
  );
  const errors = (condition: string, mode: string, cross = false) =>
    data.runs
      .filter((r) => r.image_condition === condition && r.resize_mode === mode)
      .flatMap((r) =>
        (r.checks ?? [])
          .filter((c) => !cross || crossIds.has(c.segment_id))
          .map((c) => c.relative_error_pct),
      );
  const mean = (values: number[]) =>
    values.length
      ? (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2)
      : "—";
  const gallery = data.source_gallery.find((g) => g.scene === scene);
  const selected = sources.scenes.find((s) => s.id === scene);
  return (
    <details
      className="public-metric-benchmark independent-scenes"
      id="independent-scenes"
    >
      <summary>
        <strong>{t("独立真实场景测试")}</strong>
        <span>E10-M · VGGT · 518 px · {t("3个新场景 · 9张真实照片")}</span>
      </summary>
      <section aria-label={t("独立真实场景测试")}>
        <p className="metric-reference-kind">
          {t(
            "未用于本项目前轮调试；不保证未进入VGGT训练。每方案12条检查线，4条跨墙线。",
          )}
        </p>
        <p className="metric-scope-note">
          {t(
            "激光扫描提供独立参考；每场景仅A–B标定。跨墙是两端点直线，非垂直净距；不是PV设备精度验证。",
          )}
        </p>
        {!ready ? (
          <p role="status">{t("记录缺失、失败或协议不匹配，暂不计算汇总。")}</p>
        ) : (
          <>
            <div className="independent-policy-grid">
              {policies.map(([c, m]) => (
                <article key={`${c}-${m}`} data-testid={`policy-${c}-${m}`}>
                  <h4>{title(c, m)}</h4>
                  <strong>{mean(errors(c, m))}%</strong>
                  <small>{t("检查线平均误差（MAPE）")}</small>
                  <p>
                    {t("跨墙平均误差")} {mean(errors(c, m, true))}% · n=
                    {crossIds.size}
                  </p>
                  <small>
                    {t("最大单线误差")} {Math.max(...errors(c, m)).toFixed(2)}%
                  </small>
                </article>
              ))}
            </div>
            <div className="metric-table-wrap">
              <table aria-label={t("全部12条独立检查线")}>
                <thead>
                  <tr>
                    <th>{t("真实场景")}</th>
                    <th>{t("检查线 / 参考 mm")}</th>
                    {policies.map(([c, m]) => (
                      <th key={`${c}-${m}`}>
                        {title(c, m)}
                        <small>{t("校准 mm / 误差")}</small>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sources.scenes.flatMap((s) =>
                    s.segments.slice(1).map((segment, i) => (
                      <tr key={segment.id} data-heldout={segment.id}>
                        <th>
                          {sceneName(s.id)}
                          <small>{segment.id}</small>
                        </th>
                        <td>
                          {localize(segment.label)}
                          <small>
                            {s.reference_lengths_mm[i + 1].toFixed(1)} mm ·{" "}
                            {t(
                              segment.kind === "cross_wall"
                                ? "跨墙"
                                : segment.kind === "cross_surface"
                                  ? "跨表面"
                                  : "同一表面",
                            )}
                          </small>
                        </td>
                        {policies.map(([c, m]) => {
                          const check = row(s.id, c, m)!.checks!.find(
                            (v) => v.segment_id === segment.id,
                          )!;
                          const previous = row(
                            s.id,
                            c,
                            "legacy14",
                          )!.checks!.find((v) => v.segment_id === segment.id)!;
                          const worse =
                            m === "isotropic" &&
                            check.relative_error_pct >
                              previous.relative_error_pct + 1e-9;
                          return (
                            <td
                              key={`${c}-${m}`}
                              className={worse ? "independent-regression" : ""}
                            >
                              {check.calibrated_mm.toFixed(1)} mm
                              <small>
                                {check.relative_error_pct.toFixed(2)}%{" "}
                                {worse ? t("退步") : ""}
                              </small>
                            </td>
                          );
                        })}
                      </tr>
                    )),
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
        <label className="independent-scene-select">
          {t("真实场景")}
          <select value={scene} onChange={(e) => setScene(e.target.value)}>
            {sources.scenes.map((s) => (
              <option key={s.id} value={s.id}>
                {sceneName(s.id)} · {s.id}
              </option>
            ))}
          </select>
        </label>
        <h4>{t("真实照片与扫描依据")}</h4>
        <div className="independent-gallery">
          {gallery?.views.map((v) => (
            <figure key={v.image_url}>
              <Photo src={v.image_url} alt={v.filename} />
              <figcaption>{v.filename}</figcaption>
            </figure>
          ))}
        </div>
        <p className="metric-scope-note">
          <a
            href="https://eth3d.ethz.ch/datasets"
            target="_blank"
            rel="noreferrer"
          >
            ETH3D · Schöps et al.
          </a>{" "}
          ·{" "}
          <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">
            CC BY-NC-SA 4.0
          </a>{" "}
          · {t("原始照片无实体标尺；参考来自另行获取的激光扫描。")}
        </p>
        <details>
          <summary>{t("实际518输入与同点标记")}</summary>
          <fieldset className="resize-condition">
            <legend>{t("图像条件（缩放对照）")}</legend>
            {["rectified", "original"].map((c) => (
              <label key={c}>
                <input
                  type="radio"
                  name="independent-condition"
                  checked={condition === c}
                  onChange={() => setCondition(c)}
                />
                {t(c === "rectified" ? "固定去畸变图" : "固定原图")}
              </label>
            ))}
          </fieldset>
          <div className="fixed-point-photo-grid">
            {["legacy14", "isotropic"].map((m) => {
              const r = row(scene, condition, m);
              return r ? <PreparedPreview key={r.job_id ?? m} run={r} /> : null;
            })}
          </div>
          <p className="metric-scope-note">
            {t(
              "橙色 A–B 用于标定，绿色 C–J 仅验证；同名标记对应同一扫描点，按各自缩放映射取样。",
            )}
          </p>
        </details>
        <div className="independent-replay">
          {policies.map(([c, m]) => {
            const r = row(scene, c, m);
            return (
              <button
                key={`${c}-${m}`}
                className="button secondary"
                disabled={disabled || !r?.job_id || r.status !== "succeeded"}
                onClick={() => r?.job_id && onRestore(r.job_id)}
              >
                {t(c === "original" ? "原图 RGB" : "去畸变 RGB")} ·{" "}
                {t(m === "legacy14" ? "查看当前点云" : "查看保比例点云")}
              </button>
            );
          })}
        </div>
        {ready && (
          <details>
            <summary>{t("耗时与已知相机辅助检查")}</summary>
            <p className="metric-scope-note">
              {t(
                "缓存权重，M4 Pro；耗时仅含独立worker，不含上传和查看器。已知K另用A–B求比例，不混入主指标。",
              )}
            </p>
            {policies.map(([c, m]) => {
              const r = row(scene, c, m)!;
              return (
                <p key={`${c}-${m}`}>
                  {title(c, m)} · {((r.worker_wall_ms ?? 0) / 1000).toFixed(1)}{" "}
                  s
                  {c === "rectified" && r.diagnostics?.known_K_auxiliary
                    ? ` · known-K: ${selected?.segments
                        .slice(1)
                        .map(
                          (s) =>
                            `${s.id.split("-").at(-1)} ${r.diagnostics!.known_K_auxiliary!.checks.find((v) => v.segment_id === s.id)?.relative_error_pct.toFixed(2)}%`,
                        )
                        .join(" / ")}`
                    : ""}
                </p>
              );
            })}
          </details>
        )}
        <p className="metric-scope-note">
          {t(
            data.repeat_exact
              ? "逆序复跑数组、点云和长度一致；重复不增加独立样本。"
              : "复跑存在差异或未完成，请查看完整实验报告。",
          )}
        </p>
        <p>
          <a href="https://github.com/HenryVarro666/2Dto3D/blob/main/docs/quality/2026-11-01-independent-real-scenes.md">
            {t("完整实验报告")}
          </a>
        </p>
      </section>
    </details>
  );
}
