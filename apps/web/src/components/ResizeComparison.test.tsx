import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { ResizeComparison } from "./ResizeComparison";

function fixture() {
  return {
    protocol_sha256: "authored-test",
    runs: ["pipes", "kicker"].flatMap((scene) =>
      ["original", "rectified"].flatMap((image_condition) =>
        ["legacy14", "isotropic"].map((resize_mode) => {
          const errors =
            image_condition === "original"
              ? resize_mode === "legacy14"
                ? [1, 2, 3, 4]
                : [2, 3, 4, 5]
              : (resize_mode === "legacy14" ? [5, 6, 7, 8] : [4, 8, 6, 7]).map(
                  (v) => v + (scene === "kicker" ? 10 : 0),
                );
          return {
            scene,
            image_condition,
            resize_mode,
            status: "succeeded",
            input_size: 518,
            reference_lengths_mm: [100, 200, 300, 400, 500],
            model: {
              revision: "fixed-model",
              code_revision: "fixed-code",
              protocol_sha256: "authored-test",
              resize_mode,
            },
            layout: {
              rect: [0, 84, 518, 434],
              mapping_rect: [0, 84, 518, 434],
              scale_xy: [1, 1],
            },
            checks: errors.map((error, i) => ({
              segment_id: `${scene}-${i + 1}`,
              reference_mm: (i + 2) * 100,
              calibrated_mm: (i + 2) * 100 * (1 + error / 100),
              relative_error_pct: error,
            })),
            job_id: `authored-${scene}-${image_condition}-${resize_mode}`,
            input_preview_url: `/authored-${scene}-${image_condition}-${resize_mode}.jpg`,
            preview_points: Array.from({ length: 10 }, (_, i) => ({
              id: String.fromCharCode(65 + i),
              uv: [0.2 + i / 25, 0.3 + i / 40],
            })),
          };
        }),
      ),
    ),
  };
}

it("compares resize modes within one RGB stratum and preserves points and replay across locales", async () => {
  const user = userEvent.setup(),
    restore = vi.fn();
  render(
    <I18nProvider>
      <LanguageSwitcher />
      <ResizeComparison data={fixture()} disabled={false} onRestore={restore} />
    </I18nProvider>,
  );
  await user.click(screen.getByText("缩放方式同点对照"));
  const panel = screen.getByRole("region", { name: "缩放方式同点对照" });
  expect(within(panel).getByText("11.50%")).toBeInTheDocument();
  expect(within(panel).getByText("11.25%")).toBeInTheDocument();
  await user.click(within(panel).getByRole("radio", { name: "固定原图" }));
  expect(within(panel).getByText("2.50%")).toBeInTheDocument();
  expect(within(panel).getByText("3.50%")).toBeInTheDocument();
  expect(within(panel).queryByText("11.25%")).not.toBeInTheDocument();
  await user.click(within(panel).getByText("实际518输入与同点标记"));
  const marker = within(panel).getAllByLabelText("固定点 kicker G")[0];
  const position = marker.getAttribute("cx");
  await user.selectOptions(
    screen.getByLabelText("语言 / Language / Idioma"),
    "en",
  );
  expect(within(panel).getByText("3.50%")).toBeInTheDocument();
  expect(
    within(panel).getAllByLabelText("Fixed point kicker G")[0],
  ).toHaveAttribute("cx", position);
  await user.selectOptions(
    screen.getByLabelText("语言 / Language / Idioma"),
    "es",
  );
  expect(
    within(panel).getByRole("radio", { name: "RGB original fijo" }),
  ).toBeChecked();
  const photos = within(panel)
    .getAllByRole("img")
    .filter((el) => el.tagName.toLowerCase() === "img");
  fireEvent.error(photos[0]);
  expect(
    within(panel).getByText(/La foto archivada no está disponible/),
  ).toBeInTheDocument();
  await user.click(
    within(panel).getAllByRole("button", {
      name: "Nube con escala isotrópica",
    })[1],
  );
  expect(restore).toHaveBeenCalledWith("authored-kicker-original-isotropic");
});

it("withholds aggregates when a reference or model code differs", async () => {
  const user = userEvent.setup(),
    data = fixture();
  const altered = data.runs.find(
    (r) =>
      r.scene === "kicker" &&
      r.image_condition === "rectified" &&
      r.resize_mode === "isotropic",
  )!;
  altered.reference_lengths_mm[0] += 1;
  altered.model.code_revision = "different-code";
  render(
    <I18nProvider>
      <ResizeComparison data={data} disabled={false} onRestore={vi.fn()} />
    </I18nProvider>,
  );
  await user.click(screen.getByText("缩放方式同点对照"));
  expect(
    screen.getByText("对照条件不一致或运行未完成，暂不汇总误差。"),
  ).toBeInTheDocument();
  expect(screen.queryByText("11.25%")).not.toBeInTheDocument();
});
