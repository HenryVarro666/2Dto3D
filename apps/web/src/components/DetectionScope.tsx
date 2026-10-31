import type { SceneMode } from "../api/types";
import { useI18n } from "../i18n";

export function DetectionScope({
  value,
  onChange,
  disabled,
  canRetry,
  onRetry,
}: {
  value: SceneMode;
  onChange: (value: SceneMode) => void;
  disabled: boolean;
  canRetry: boolean;
  onRetry: () => void;
}) {
  const { t } = useI18n();
  return (
    <section className="detection-scope">
      <fieldset disabled={disabled}>
        <legend>{t("自动识别范围")}</legend>
        <label>
          <input
            type="radio"
            name="scene-mode"
            value="single"
            checked={value === "single"}
            onChange={() => onChange("single")}
          />
          {t("单设备")}
        </label>
        <label>
          <input
            type="radio"
            name="scene-mode"
            value="multiple"
            checked={value === "multiple"}
            onChange={() => onChange("multiple")}
          />
          {t("多设备")}
        </label>
      </fieldset>
      <p>{t("仅影响下一次自动识别；手工补录不受主柜数量限制。")}</p>
      {canRetry && (
        <button
          className="button small secondary"
          disabled={disabled}
          onClick={onRetry}
        >
          {t("按当前范围重新识别")}
        </button>
      )}
    </section>
  );
}
