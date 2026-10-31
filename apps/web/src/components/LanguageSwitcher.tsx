import { Languages } from "lucide-react";
import { useI18n } from "../i18n";
import type { Locale } from "../i18n";

export function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();
  return (
    <label className="language-switch">
      <Languages size={16} aria-hidden="true" />
      <select
        aria-label="语言 / Language / Idioma"
        value={locale}
        onChange={(event) => setLocale(event.target.value as Locale)}
      >
        <option value="zh" lang="zh-CN">
          中文
        </option>
        <option value="en" lang="en">
          English
        </option>
        <option value="es" lang="es">
          Español
        </option>
      </select>
    </label>
  );
}
