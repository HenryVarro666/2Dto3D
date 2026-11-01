import { useRef } from "react";
import results from "../../../../docs/measurement/public-metric-results.json";
import { useI18n } from "../i18n";
import type { MessageKey } from "../i18n/messages";

type Run = {
  scene: string;
  input_size: number;
  status: string;
  job_id?: string;
  worker_wall_ms?: number;
  calibration?: { known_length_mm: number };
  checks?: {
    segment_id: string;
    reference_mm: number;
    calibrated_mm: number;
    absolute_error_mm: number;
    relative_error_pct: number;
  }[];
};

const labels: Record<string, MessageKey> = {
  "pipes-1": "柜体横向 C–D",
  "pipes-2": "橙色面板纵向 E–F",
  "pipes-3": "管道纵向 G–H",
  "pipes-4": "柜体至管道 I–J",
  "kicker-1": "后墙 C–D",
  "kicker-2": "侧墙 E–F",
  "kicker-3": "后墙至侧墙 G–H",
  "kicker-4": "柜体下段 I–J",
};
const runs: Run[] = results.runs;

export function PublicMetricBenchmark({
  onRestore,
  disabled,
}: {
  onRestore: (jobId: string) => void;
  disabled: boolean;
}) {
  const { t } = useI18n();
  const details = useRef<HTMLDetailsElement>(null);
  return (
    <details
      className="public-metric-benchmark"
      id="public-metric-validation"
      ref={details}
    >
      <summary>
        <strong>{t("公开尺寸验证")}</strong>
        <span>ETH3D · {t("2 个场景 · 6 张照片 · 8 条独立长度")}</span>
      </summary>
      <section aria-label={t("公开尺寸验证")}>
        <p className="metric-reference-kind">
          {t(
            "激光扫描参考；照片中没有实体标定尺。每个场景只用 A–B 标定，C–J 只用于独立检查。",
          )}
        </p>
        <div className="metric-overview">
          {[336, 518].map((size) => {
            const checks = runs
              .filter((r) => r.input_size === size)
              .flatMap((r) => r.checks ?? []);
            const mean =
              checks.reduce((sum, c) => sum + c.relative_error_pct, 0) /
              checks.length;
            return (
              <div key={size}>
                <span>VGGT · {size} px</span>
                <strong>{mean.toFixed(2)}%</strong>
                <small>
                  {t("平均绝对百分比误差")} · n={checks.length}
                </small>
              </div>
            );
          })}
          <p>
            {t(
              "提高分辨率改善了多数检查线，但 kicker 后墙误差从 10.36% 升至 12.59%。单条标定线不能消除整体形变。",
            )}
          </p>
        </div>
        <p className="metric-scope-note">
          {t(
            "这是两个公开场景的小样本诊断，不代表逆变器现场精度。两种分辨率取最近输出像素，端点略有移动；桌球台因缺少扫描参考而未测量。",
          )}
        </p>
        <div className="metric-runs">
          {runs.map((run) => (
            <article key={`${run.scene}-${run.input_size}`}>
              <header>
                <div>
                  <h3>
                    {run.scene} · {run.input_size} px
                  </h3>
                  {run.calibration && (
                    <p>
                      {t("标定 A–B")} ·{" "}
                      {run.calibration.known_length_mm.toFixed(1)} mm
                      {" · "}
                      {t("模型流程")} {(run.worker_wall_ms! / 1000).toFixed(2)}{" "}
                      s
                    </p>
                  )}
                </div>
                <button
                  className="button secondary"
                  disabled={disabled || !run.job_id}
                  onClick={() => {
                    if (run.job_id) {
                      if (details.current) details.current.open = false;
                      onRestore(run.job_id);
                    }
                  }}
                >
                  {t("查看点云与测量记录")}
                </button>
              </header>
              {run.status !== "succeeded" ? (
                <p>{t("运行失败")}</p>
              ) : (
                <div className="metric-table-scroll">
                  <table>
                    <caption className="visually-hidden">
                      {run.scene} {run.input_size} · {t("独立检查线")}
                    </caption>
                    <thead>
                      <tr>
                        <th>{t("独立检查线")}</th>
                        <th>{t("扫描参考")}</th>
                        <th>{t("校准后")}</th>
                        <th>{t("绝对误差")}</th>
                        <th>{t("相对误差")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {run.checks?.map((check) => (
                        <tr key={check.segment_id}>
                          <th scope="row">{t(labels[check.segment_id])}</th>
                          <td>{check.reference_mm.toFixed(1)} mm</td>
                          <td>{check.calibrated_mm.toFixed(1)} mm</td>
                          <td>{check.absolute_error_mm.toFixed(1)} mm</td>
                          <td
                            className={
                              check.relative_error_pct > 10
                                ? "metric-large-error"
                                : ""
                            }
                          >
                            {check.relative_error_pct.toFixed(2)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </article>
          ))}
        </div>
        <p>
          {t(
            "模型流程耗时包含每次进程加载、推理和几何写出，不含下载、上传和浏览器；不是端到端耗时。",
          )}
        </p>
        <p>
          {t(
            "新克隆可直接查看汇总；点云重放需先运行 E07 数据准备与评测脚本。视图分组只是几何审计，不代表自动组件分割。",
          )}
        </p>
        <p className="metric-source-links">
          <a
            href="https://eth3d.ethz.ch/datasets"
            target="_blank"
            rel="noreferrer"
          >
            {t("原始数据与来源")} ↗
          </a>
          <a
            href="https://github.com/HenryVarro666/2Dto3D/blob/main/docs/quality/2026-11-01-public-metric-measurement.md"
            target="_blank"
            rel="noreferrer"
          >
            {t("完整结果与复现步骤")} ↗
          </a>
          <span>ETH3D · CC BY-NC-SA 4.0 · E07</span>
        </p>
      </section>
    </details>
  );
}
