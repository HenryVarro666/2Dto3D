import { useEffect, useRef, useState } from "react";
import { Download, Ruler } from "lucide-react";
import type {
  LengthUnit,
  MeasurementSession,
  PickedPoint,
  WorkbenchApi,
} from "../api/types";
import { useI18n } from "../i18n";

export function MeasurementPanel({
  apiClient,
  jobId,
  points,
  pickMode,
  disabled,
  onPickMode,
  onClear,
  onShowPoints,
}: {
  apiClient: WorkbenchApi;
  jobId: string;
  points: PickedPoint[];
  pickMode: boolean;
  disabled: boolean;
  onPickMode: (enabled: boolean) => void;
  onClear: () => void;
  onShowPoints?: (points: PickedPoint[]) => void;
}) {
  const { t, localize } = useI18n();
  const [session, setSession] = useState<MeasurementSession | null>(null);
  const [calibrationId, setCalibrationId] = useState("");
  const [known, setKnown] = useState("");
  const [unit, setUnit] = useState<LengthUnit>("mm");
  const [note, setNote] = useState("");
  const [label, setLabel] = useState("");
  const [validate, setValidate] = useState(false);
  const [truth, setTruth] = useState("");
  const [truthUnit, setTruthUnit] = useState<LengthUnit>("mm");
  const [truthNote, setTruthNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    const token = ++generation.current;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setSession(null);
    setCalibrationId("");
    setError(null);
    setBusy(true);

    void apiClient
      .getMeasurements(jobId, abort.signal)
      .then((value) => {
        if (abort.signal.aborted || token !== generation.current) return;
        setSession(value);
        setCalibrationId(
          value.calibrations
            .filter((c) => c.geometry_sha256 === value.geometry_sha256)
            .at(-1)?.id ?? "",
        );
      })
      .catch((reason) => {
        if (!abort.signal.aborted && token === generation.current)
          setError(
            reason instanceof Error
              ? reason.message
              : "MEASUREMENT_LOAD_FAILED",
          );
      })
      .finally(() => {
        if (!abort.signal.aborted && token === generation.current)
          setBusy(false);
      });
    return () => {
      generation.current++;
      abort.abort();
    };
  }, [jobId, apiClient, retry]);

  useEffect(() => {
    setKnown("");
    setNote("");
    setLabel("");
    setValidate(false);
    setTruth("");
    setTruthNote("");
  }, [jobId]);

  const validSession = session?.job_id === jobId ? session : null;
  const calibration = validSession?.calibrations.find(
    (c) =>
      c.id === calibrationId &&
      c.geometry_sha256 === validSession.geometry_sha256,
  );
  const rawDistance =
    points.length === 2
      ? Math.hypot(
          ...points[0].position.map((n, i) => n - points[1].position[i]),
        )
      : null;
  const canSave =
    !disabled &&
    !busy &&
    Boolean(validSession) &&
    rawDistance !== null &&
    rawDistance > 1e-12;
  const validLength = (value: string) =>
    Number.isFinite(Number(value)) &&
    Number(value) >= 0.000001 &&
    Number(value) <= 1_000_000;
  const records = validSession?.measurements ?? [];

  async function save(kind: "calibration" | "measurement") {
    if (!canSave || !validSession) return;
    const token = generation.current;
    setBusy(true);
    setError(null);
    const input = {
      geometry_sha256: validSession.geometry_sha256,
      points: points.map(({ component_id, point_index }) => ({
        component_id,
        point_index,
      })),
      label,
    };
    try {
      if (kind === "calibration") {
        const value = await apiClient.calibrate(
          jobId,
          {
            ...input,
            known_length: Number(known),
            unit,
            source_note: note.trim(),
          },
          controller.current?.signal,
        );
        if (generation.current !== token) return;
        setSession((s) =>
          s ? { ...s, calibrations: [...s.calibrations, value] } : s,
        );
        setCalibrationId(value.id);
      } else {
        const value = await apiClient.measure(
          jobId,
          {
            ...input,
            ...(calibration ? { calibration_id: calibration.id } : {}),
            ...(validate
              ? {
                  validation: {
                    known_length: Number(truth),
                    unit: truthUnit,
                    source_note: truthNote.trim(),
                  },
                }
              : {}),
          },
          controller.current?.signal,
        );
        if (generation.current !== token) return;
        setSession((s) =>
          s ? { ...s, measurements: [...s.measurements, value] } : s,
        );
      }
    } catch (reason) {
      if (generation.current === token)
        setError(
          reason instanceof Error ? reason.message : "MEASUREMENT_SAVE_FAILED",
        );
    } finally {
      if (generation.current === token) setBusy(false);
    }
  }

  function unitSelect(
    value: LengthUnit,
    change: (u: LengthUnit) => void,
    name: string,
  ) {
    return (
      <select
        aria-label={name}
        value={value}
        onChange={(e) => change(e.target.value as LengthUnit)}
        disabled={busy || disabled}
      >
        <option value="mm">mm</option>
        <option value="cm">cm</option>
        <option value="m">m</option>
      </select>
    );
  }
  return (
    <section className="measurement-panel" aria-label={t("标定与测距")}>
      <header className="measurement-heading">
        <div>
          <Ruler size={20} />
          <h2>{t("标定与测距")}</h2>
        </div>
        <span
          className={`measurement-scale-badge ${calibration ? "calibrated" : ""}`}
        >
          {t(calibration ? "参照校准 · 几何仍为估算" : "估算几何 · 尺度未知")}
        </span>
      </header>
      <p className="measurement-limit">
        {t(
          "一个已知长度只校准比例，不修正形变。请用另一条独立实测长度验证；结果不作为工程验收尺寸。",
        )}
      </p>
      <div className="measurement-actions">
        <button
          className={
            pickMode ? "button primary small" : "button secondary small"
          }
          aria-pressed={pickMode}
          disabled={disabled || busy || !validSession}
          onClick={() => onPickMode(!pickMode)}
        >
          {t(pickMode ? "结束选点" : "在点云中选择 A / B")}
        </button>
        <button
          className="text-button"
          disabled={busy || points.length === 0}
          onClick={onClear}
        >
          {t("清除选点")}
        </button>
        <span>{t("已选 {count}/2 个点", { count: points.length })}</span>
      </div>
      <p className="measurement-instruction">
        {t(
          "点击可见表面的实际点。A、B 标记和连线使用原始坐标；选点时关闭组件分解。",
        )}
      </p>
      <ol className="measurement-points">
        {points.map((p, i) => (
          <li key={i}>
            <b>{i ? "B" : "A"}</b>
            <code>
              {p.component_id} · #{p.point_index}
            </code>
            <span>{p.position.map((n) => n.toFixed(4)).join(", ")}</span>
          </li>
        ))}
      </ol>
      {rawDistance !== null && (
        <div className="measurement-reading" aria-live="polite">
          <strong>
            {t("相对距离：{distance} u", { distance: rawDistance.toFixed(4) })}
          </strong>
          {calibration && (
            <strong className="metric-reading">
              {t("校准尺寸：{distance} mm", {
                distance: (rawDistance * calibration.mm_per_unit).toFixed(2),
              })}
            </strong>
          )}
        </div>
      )}
      <label className="measurement-label">
        {t("测量备注")}
        <input
          value={label}
          maxLength={160}
          disabled={busy || disabled}
          onChange={(e) => setLabel(e.target.value)}
        />
      </label>
      <div className="measurement-forms">
        <fieldset disabled={busy || disabled || !validSession}>
          <legend>1 · {t("已知尺寸标定")}</legend>
          <label>
            {t("已知长度")}
            <div className="length-input">
              <input
                aria-label={t("已知长度")}
                type="number"
                min="0.000001"
                max="1000000"
                step="any"
                value={known}
                onChange={(e) => setKnown(e.target.value)}
              />
              {unitSelect(unit, setUnit, t("标定单位"))}
            </div>
          </label>
          <label>
            {t("长度来源 / 端点说明")}
            <input
              value={note}
              maxLength={1000}
              onChange={(e) => setNote(e.target.value)}
              placeholder={t("例如：卷尺测得正面 A–B；记录拍摄或实测依据")}
            />
          </label>
          <button
            className="button secondary small"
            disabled={!canSave || !validLength(known) || !note.trim()}
            onClick={() => void save("calibration")}
          >
            {t("保存标定")}
          </button>
        </fieldset>
        <fieldset disabled={busy || disabled || !validSession}>
          <legend>2 · {t("两点直线距离")}</legend>
          <label>
            {t("尺度依据")}
            <select
              value={calibrationId}
              onChange={(e) => {
                setCalibrationId(e.target.value);
                if (!e.target.value) setValidate(false);
              }}
            >
              <option value="">{t("未标定：仅相对单位")}</option>
              {validSession?.calibrations
                .filter(
                  (c) => c.geometry_sha256 === validSession.geometry_sha256,
                )
                .map((c, i) => (
                  <option key={c.id} value={c.id}>
                    {i + 1} · {c.known_length} {c.unit} ·{" "}
                    {c.label || c.source_note.slice(0, 35)}
                  </option>
                ))}
            </select>
          </label>
          {calibration && (
            <p className="reference-evidence">
              <b>{t("当前参照")}</b> · {calibration.known_length}{" "}
              {calibration.unit} → {calibration.mm_per_unit.toFixed(4)} mm/u
              <br />
              {calibration.source_note}
              <br />
              <code>{calibration.id}</code>
              {onShowPoints && (
                <button
                  className="text-button"
                  onClick={() => onShowPoints(calibration.points)}
                >
                  {t("查看参照端点")}
                </button>
              )}
            </p>
          )}
          <label className="inline-label">
            <input
              type="checkbox"
              checked={validate}
              disabled={!calibration}
              onChange={(e) => setValidate(e.target.checked)}
            />
            {t("加入独立验证长度")}
          </label>
          {validate && (
            <>
              <label>
                {t("独立实测长度")}
                <div className="length-input">
                  <input
                    aria-label={t("独立实测长度")}
                    type="number"
                    min="0.000001"
                    max="1000000"
                    step="any"
                    value={truth}
                    onChange={(e) => setTruth(e.target.value)}
                  />
                  {unitSelect(truthUnit, setTruthUnit, t("验证单位"))}
                </div>
              </label>
              <label>
                {t("验证长度来源")}
                <input
                  value={truthNote}
                  maxLength={1000}
                  onChange={(e) => setTruthNote(e.target.value)}
                />
              </label>
              <p>
                {t(
                  "确认这条长度未用于标定。换点重画同一标定线仍不构成独立验证。",
                )}
              </p>
            </>
          )}
          <button
            className="button primary small"
            disabled={
              !canSave ||
              (validate &&
                (!calibration || !validLength(truth) || !truthNote.trim()))
            }
            onClick={() => void save("measurement")}
          >
            {t("保存测距 / 验证")}
          </button>
        </fieldset>
      </div>
      {busy && <p role="status">{t("正在读取或保存测量记录…")}</p>}
      {error && (
        <p role="alert">
          {localize(error)}{" "}
          <button
            className="text-button"
            disabled={busy}
            onClick={() => setRetry((n) => n + 1)}
          >
            {t("重新载入记录")}
          </button>
        </p>
      )}
      {Boolean(validSession?.stale_record_count) && (
        <p role="alert">
          {t("部分记录对应旧几何，已保留但不能用于当前点云。")}
        </p>
      )}
      {records.length > 0 && (
        <div className="measurement-history">
          <h3>{t("测距与验证记录")}</h3>
          <div className="measurement-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("测量备注")}</th>
                  <th>{t("尺度依据")}</th>
                  <th>{t("距离")}</th>
                  <th>{t("独立验证 / 误差")}</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr
                    key={r.id}
                    className={
                      r.geometry_sha256 !== validSession?.geometry_sha256
                        ? "stale-record"
                        : ""
                    }
                  >
                    <td>
                      {r.label || r.id.slice(0, 8)}
                      {onShowPoints &&
                        r.geometry_sha256 === validSession?.geometry_sha256 && (
                          <button
                            className="text-button"
                            disabled={busy || disabled}
                            onClick={() => onShowPoints(r.points)}
                          >
                            {t("查看端点")}
                          </button>
                        )}
                      <small>
                        {r.points
                          .map((p) => `${p.component_id} #${p.point_index}`)
                          .join(" → ")}
                      </small>
                    </td>
                    <td>
                      {t(
                        r.scale_status === "reference_calibrated"
                          ? "参照校准"
                          : "相对估算",
                      )}
                      <small>{r.calibration_id?.slice(0, 8)}</small>
                    </td>
                    <td>
                      {r.distance_mm === null
                        ? `${r.distance_units.toFixed(4)} u`
                        : `${r.distance_mm.toFixed(2)} mm`}
                    </td>
                    <td>
                      {r.validation ? (
                        <>
                          <b>{t("独立验证")}</b> · {r.validation.known_length}{" "}
                          {r.validation.unit}
                          <br />
                          {r.validation.absolute_error_mm.toFixed(2)} mm ·{" "}
                          {r.validation.relative_error_pct.toFixed(2)}%
                          <small>{r.validation.source_note}</small>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <footer className="measurement-footer">
        <span>
          {t("原始 GLB / PLY 保持相对尺度；校准与误差保存在独立记录中。")}
        </span>
        {validSession && (
          <a
            className="text-button"
            href={`/api/multiview/jobs/${encodeURIComponent(jobId)}/measurements/export.json`}
            download
          >
            <Download size={14} />
            {t("导出测量记录")}
          </a>
        )}
      </footer>
    </section>
  );
}
