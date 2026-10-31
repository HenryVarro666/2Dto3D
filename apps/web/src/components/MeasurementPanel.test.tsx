import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { MeasurementPanel } from "./MeasurementPanel";
import { fakeApi } from "../test/fixtures";
import { I18nProvider } from "../i18n";
import { LanguageSwitcher } from "./LanguageSwitcher";
import type { MeasurementSession, PickedPoint } from "../api/types";

const sha = "a".repeat(64);
const points: PickedPoint[] = [
  { component_id: "part-a", point_index: 0, position: [0, 0, 0] },
  { component_id: "part-a", point_index: 1, position: [2, 0, 0] },
];
const session: MeasurementSession = {
  schema_version: 1,
  job_id: "job-a",
  geometry_job_id: "job-a",
  geometry_sha256: sha,
  raw_geometry_scale_status: "unknown",
  calibrations: [],
  measurements: [],
  stale_record_count: 0,
};

it("saves references and independent checks, keeps user notes during language changes and resets for a new job", async () => {
  const user = userEvent.setup();
  const save = vi.fn(async (_id, input) => ({
    ...input,
    id: "cal-a",
    job_id: "job-a",
    geometry_job_id: "job-a",
    created_at: "2026-10-31",
    points,
    distance_units: 2,
    mm_per_unit: 100,
    known_length_mm: 200,
    coordinate_frame: "GLB world, Y-up, un-exploded",
    scale_status: "reference_calibrated" as const,
    reference_kind: "user_supplied" as const,
  }));
  const check = vi.fn(async (_id, input) => ({
    ...input,
    id: "check-a",
    job_id: "job-a",
    geometry_job_id: "job-a",
    created_at: "2026-10-31",
    points,
    distance_units: 3.3,
    distance_mm: 330,
    scale_status: "reference_calibrated" as const,
    validation: {
      ...input.validation,
      known_length_mm: 300,
      signed_error_mm: 30,
      absolute_error_mm: 30,
      relative_error_pct: 10,
      used_for_calibration: false as const,
      reference_kind: "user_supplied" as const,
    },
  }));
  const api = fakeApi({
    getMeasurements: async (id) => ({ ...session, job_id: id }),
    calibrate: save,
    measure: check,
  });
  const props = {
    apiClient: api,
    jobId: "job-a",
    points,
    pickMode: true,
    disabled: false,
    onPickMode: vi.fn(),
    onClear: vi.fn(),
  };
  const view = render(
    <I18nProvider>
      <LanguageSwitcher />
      <MeasurementPanel {...props} />
    </I18nProvider>,
  );
  await screen.findByText("相对距离：2.0000 u");
  await user.type(screen.getByLabelText("已知长度"), "200");
  await user.type(screen.getByLabelText("长度来源 / 端点说明"), "Tape AB");
  await user.click(screen.getByRole("button", { name: "保存标定" }));
  await waitFor(() => expect(save).toHaveBeenCalledOnce());
  expect(save.mock.calls[0][1].points).toEqual(
    points.map(({ component_id, point_index }) => ({
      component_id,
      point_index,
    })),
  );
  expect(await screen.findByText("校准尺寸：200.00 mm")).toBeInTheDocument();
  // Different points are supplied by the actual viewer in production.
  view.rerender(
    <I18nProvider>
      <LanguageSwitcher />
      <MeasurementPanel
        {...props}
        points={
          points.map((p, i) => ({
            ...p,
            point_index: i + 2,
            position: [0, i * 3.3, 0],
          })) as PickedPoint[]
        }
      />
    </I18nProvider>,
  );
  await user.click(screen.getByLabelText("加入独立验证长度"));
  await user.type(screen.getByLabelText("独立实测长度"), "300");
  await user.type(screen.getByLabelText("验证长度来源"), "Tape CD, not AB");
  await user.click(screen.getByRole("button", { name: "保存测距 / 验证" }));
  expect(await screen.findByText(/10.00%/)).toBeInTheDocument();
  await user.selectOptions(
    screen.getByLabelText("语言 / Language / Idioma"),
    "en",
  );
  expect(screen.getByLabelText("Length source / endpoints")).toHaveValue(
    "Tape AB",
  );
  expect(screen.getByText("Held-out validation")).toBeInTheDocument();
  view.rerender(
    <I18nProvider>
      <LanguageSwitcher />
      <MeasurementPanel {...props} jobId="job-b" points={[]} />
    </I18nProvider>,
  );
  await waitFor(() =>
    expect(screen.queryByText(/10.00%/)).not.toBeInTheDocument(),
  );
  expect(screen.queryByText("cal-a")).not.toBeInTheDocument();
});

it("ignores old job loads and shows a retry without erasing points on failed saves", async () => {
  let resolveOld!: (value: MeasurementSession) => void;
  const api = fakeApi({
    getMeasurements: (id) =>
      id === "old"
        ? new Promise((resolve) => {
            resolveOld = resolve;
          })
        : Promise.resolve({ ...session, job_id: id }),
    calibrate: async () => {
      throw new Error("MEASUREMENT_REFERENCE_REUSED");
    },
  });
  const props = {
    apiClient: api,
    jobId: "old",
    points,
    pickMode: false,
    disabled: false,
    onPickMode: vi.fn(),
    onClear: vi.fn(),
  };
  const view = render(<MeasurementPanel {...props} />);
  view.rerender(<MeasurementPanel {...props} jobId="new" />);
  await screen.findByText("相对距离：2.0000 u");
  resolveOld({ ...session, geometry_sha256: "b".repeat(64) });
  await waitFor(() =>
    expect(screen.getByRole("link", { name: "导出测量记录" })).toHaveAttribute(
      "href",
      "/api/multiview/jobs/new/measurements/export.json",
    ),
  );
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("已知长度"), "200");
  await user.type(screen.getByLabelText("长度来源 / 端点说明"), "Tape AB");
  await user.click(screen.getByRole("button", { name: "保存标定" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "标定线不能作为独立验证线",
  );
  expect(screen.getByLabelText("已知长度")).toHaveValue(200);
});
