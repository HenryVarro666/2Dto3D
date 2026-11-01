import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { PublicMetricBenchmark } from "./PublicMetricBenchmark";
import { I18nProvider } from "../i18n";
import { LanguageSwitcher } from "./LanguageSwitcher";

it("shows independent measured errors and preserves the result when switching languages", async () => {
  const user = userEvent.setup();
  const open = vi.fn();
  render(
    <I18nProvider>
      <LanguageSwitcher />
      <PublicMetricBenchmark onRestore={open} disabled={false} />
    </I18nProvider>,
  );
  await user.click(screen.getByText("公开尺寸验证"));
  const panel = screen.getByRole("region", { name: "公开尺寸验证" });
  expect(within(panel).getByText(/激光扫描参考/)).toBeInTheDocument();
  expect(within(panel).getAllByText("45.03%")).toHaveLength(1);
  expect(within(panel).getAllByText("12.59%")).toHaveLength(1);
  expect(within(panel).getAllByRole("table")).toHaveLength(4);
  expect(
    within(panel).getAllByRole("button", { name: "查看点云与测量记录" }),
  ).toHaveLength(4);
  await user.click(
    within(panel).getAllByRole("button", { name: "查看点云与测量记录" })[0],
  );
  expect(open).toHaveBeenCalledOnce();
  expect(open.mock.calls[0][0]).toMatch(/^[a-f0-9]{32}$/);
  expect(panel.closest("details")).not.toHaveAttribute("open");
  await user.selectOptions(
    screen.getByLabelText("语言 / Language / Idioma"),
    "en",
  );
  expect(screen.getByText("Public metric validation")).toBeInTheDocument();
  expect(screen.getAllByText("Cabinet horizontal C–D")).toHaveLength(2);
  await user.selectOptions(
    screen.getByLabelText("语言 / Language / Idioma"),
    "es",
  );
  expect(screen.getByText("Validación métrica pública")).toBeInTheDocument();
  expect(screen.getAllByText("45.03%")).toHaveLength(1);
});
