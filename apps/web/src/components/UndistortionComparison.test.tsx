import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import source from "../../../../docs/measurement/undistortion-results.json";
import { I18nProvider } from "../i18n";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { UndistortionComparison } from "./UndistortionComparison";

it("shows same-reference518 results and preserves physical point markers across languages", async () => {
  const user = userEvent.setup();
  const restore = vi.fn();
  render(
    <I18nProvider>
      <LanguageSwitcher />
      <UndistortionComparison disabled={false} onRestore={restore} />
    </I18nProvider>,
  );
  await user.click(screen.getByText("同点去畸变对照"));
  const panel = screen.getByRole("region", { name: "同点去畸变对照" });
  expect(within(panel).getByText("4.24%")).toBeInTheDocument();
  expect(within(panel).getByText("2.97%")).toBeInTheDocument();
  expect(within(panel).getAllByText(/12.91%/)).toHaveLength(1);
  await user.click(within(panel).getByText("同一物理点的照片对照"));
  expect(within(panel).getAllByLabelText("固定点 pipes C")).toHaveLength(2);
  const marker = within(panel).getAllByLabelText("固定点 pipes C")[0];
  const position = [marker.getAttribute("cx"), marker.getAttribute("cy")];
  await user.selectOptions(
    screen.getByLabelText("语言 / Language / Idioma"),
    "en",
  );
  expect(
    screen.getByText("Fixed-point undistortion comparison"),
  ).toBeInTheDocument();
  expect(
    within(panel).getAllByLabelText("Fixed point pipes C")[0],
  ).toHaveAttribute("cx", position[0]);
  await user.selectOptions(
    screen.getByLabelText("语言 / Language / Idioma"),
    "es",
  );
  expect(
    screen.getByText(
      "Comparación de corrección de distorsión con puntos fijos",
    ),
  ).toBeInTheDocument();
  expect(within(panel).getByText("2.97%")).toBeInTheDocument();
  const images = within(panel)
    .getAllByRole("img")
    .filter((el) => el.tagName.toLowerCase() === "img");
  fireEvent.error(images[0]);
  expect(
    within(panel).getByText(/La foto archivada no está disponible/),
  ).toBeInTheDocument();
  await user.click(
    within(panel).getAllByRole("button", { name: "Nube rectificada" })[1],
  );
  expect(restore).toHaveBeenCalledWith(
    source.runs.find(
      (r) => r.scene === "kicker" && r.condition === "rectified",
    )!.job_id,
  );
});

it("withholds aggregate error when calibration references differ", async () => {
  const user = userEvent.setup();
  const altered = {
    ...source,
    runs: source.runs.map((r) =>
      r.scene === "kicker" && r.condition === "rectified"
        ? {
            ...r,
            reference_lengths_mm: [
              r.reference_lengths_mm[0] + 1,
              ...r.reference_lengths_mm.slice(1),
            ],
          }
        : r,
    ),
  };
  render(
    <I18nProvider>
      <UndistortionComparison
        disabled={false}
        onRestore={vi.fn()}
        data={altered}
      />
    </I18nProvider>,
  );
  await user.click(screen.getByText("同点去畸变对照"));
  expect(
    screen.getByText("对照条件不一致或运行未完成，暂不汇总误差。"),
  ).toBeInTheDocument();
  expect(screen.queryByText("2.97%")).not.toBeInTheDocument();
});
