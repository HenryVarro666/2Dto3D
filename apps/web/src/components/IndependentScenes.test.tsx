import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { IndependentScenes } from "./IndependentScenes";

const scenes = ["office", "delivery_area", "terrains"];
function fixture() {
  const sources = {
    scenes: scenes.map((id) => ({
      id,
      reference_lengths_mm: [100, 200, 300, 400, 500],
      segments: ["AB", "CD", "EF", "GH", "IJ"].map((s, i) => ({
        id: `${id}-${s}`,
        label: s,
        kind: i === 1 || i === 3 ? "cross_wall" : "same_wall",
      })),
    })),
  };
  const data = {
    protocol_sha256: "frozen",
    repeat_exact: true,
    source_gallery: scenes.map((scene) => ({
      scene,
      views: [0, 1, 2].map((i) => ({
        filename: `${scene}-${i}.JPG`,
        image_url: `/authored-${scene}-${i}.jpg`,
      })),
    })),
    runs: scenes.flatMap((scene) =>
      ["original", "rectified"].flatMap((image_condition) =>
        ["legacy14", "isotropic"].map((resize_mode) => {
          const errors =
            image_condition === "original"
              ? [10, 20, 30, 40]
              : resize_mode === "legacy14"
                ? [5, 6, 7, 8]
                : [4, 8, 6, 9];
          return {
            scene,
            image_condition,
            resize_mode,
            status: "succeeded",
            input_size: 518,
            view_count: 3,
            reference_lengths_mm: [100, 200, 300, 400, 500],
            worker_wall_ms: 20000,
            model: {
              revision: "860abec7937da0a4c03c41d3c269c366e82abdf9",
              code_revision: "a288dd0f14786c93483e45524328726ab7b1b4ce",
              protocol_sha256: "frozen",
              resize_mode,
            },
            job_id: `${scene}-${image_condition}-${resize_mode}`,
            input_preview_url: `/authored-${scene}-${image_condition}-${resize_mode}.jpg`,
            preview_points: Array.from({ length: 10 }, (_, i) => ({
              id: String.fromCharCode(65 + i),
              uv: [0.1 + i * 0.05, 0.4],
            })),
            checks: errors.map((e, i) => ({
              segment_id: `${scene}-${["CD", "EF", "GH", "IJ"][i]}`,
              reference_mm: (i + 2) * 100,
              calibrated_mm: (i + 2) * 100 * (1 + e / 100),
              relative_error_pct: e,
            })),
          };
        }),
      ),
    ),
  };
  return { sources, data };
}

it("shows every held-out line and real views, retains selection/numbers across languages and replays the selected policy", async () => {
  const user = userEvent.setup(),
    restore = vi.fn();
  render(
    <I18nProvider>
      <LanguageSwitcher />
      <IndependentScenes {...fixture()} disabled={false} onRestore={restore} />
    </I18nProvider>,
  );
  await user.click(screen.getByText("独立真实场景测试"));
  const panel = screen.getByRole("region", { name: "独立真实场景测试" });
  expect(
    within(panel)
      .getAllByRole("row")
      .filter((r) => r.hasAttribute("data-heldout")),
  ).toHaveLength(12);
  expect(
    within(panel).getByTestId("policy-rectified-legacy14"),
  ).toHaveTextContent("6.50%");
  expect(
    within(panel).getByTestId("policy-rectified-isotropic"),
  ).toHaveTextContent("6.75%");
  await user.selectOptions(
    within(panel).getByLabelText("真实场景"),
    "terrains",
  );
  await user.click(within(panel).getByText("实际518输入与同点标记"));
  await user.click(within(panel).getByRole("radio", { name: "固定原图" }));
  await user.selectOptions(
    screen.getByLabelText("语言 / Language / Idioma"),
    "en",
  );
  expect(within(panel).getByLabelText("Real scene")).toHaveValue("terrains");
  expect(
    within(panel).getByRole("radio", { name: "Fixed original RGB" }),
  ).toBeChecked();
  expect(
    within(panel).getByTestId("policy-rectified-isotropic"),
  ).toHaveTextContent("6.75%");
  expect(within(panel).getByText("terrains-0.JPG")).toBeInTheDocument();
  await user.click(
    within(panel).getByRole("button", {
      name: "Original RGB · Isotropic cloud",
    }),
  );
  expect(restore).toHaveBeenCalledWith("terrains-original-isotropic");
  await user.selectOptions(
    screen.getByLabelText("语言 / Language / Idioma"),
    "es",
  );
  expect(within(panel).getByLabelText("Escena real")).toHaveValue("terrains");
  fireEvent.error(
    within(panel)
      .getAllByRole("img")
      .find((i) => i.tagName.toLowerCase() === "img")!,
  );
  expect(
    within(panel).getByText(/La foto archivada no está disponible/),
  ).toBeInTheDocument();
});

it.each(["missing", "duplicate", "reference", "model"])(
  "withholds aggregates for %s cases rather than hiding invalid comparisons",
  async (invalid) => {
    const { data, sources } = fixture();
    if (invalid === "missing") data.runs.pop();
    if (invalid === "duplicate") data.runs[1] = data.runs[0];
    if (invalid === "reference") data.runs[0].checks[0].reference_mm += 1;
    if (invalid === "model") data.runs[0].model.code_revision = "different";
    render(
      <I18nProvider>
        <IndependentScenes
          data={data}
          sources={sources}
          disabled={false}
          onRestore={vi.fn()}
        />
      </I18nProvider>,
    );
    await userEvent.click(screen.getByText("独立真实场景测试"));
    expect(
      screen.queryByTestId("policy-rectified-isotropic"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("记录缺失、失败或协议不匹配，暂不计算汇总。"),
    ).toBeInTheDocument();
  },
);

it("hides prepared-point overlays when the archived model-input image is missing", async () => {
  render(
    <I18nProvider>
      <IndependentScenes {...fixture()} disabled={false} onRestore={vi.fn()} />
    </I18nProvider>,
  );
  await userEvent.click(screen.getByText("独立真实场景测试"));
  await userEvent.click(screen.getByText("实际518输入与同点标记"));
  const input = screen.getByAltText("office · legacy14 · 518");
  const figure = input.closest("figure")!;
  fireEvent.error(input);
  expect(figure.querySelector("svg")).not.toBeInTheDocument();
  expect(within(figure).getByText(/本机尚无该归档照片/)).toBeInTheDocument();
});
