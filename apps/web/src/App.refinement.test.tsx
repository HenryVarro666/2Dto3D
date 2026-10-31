import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import App from "./App";
import { cabinet, completed, fakeApi, result, running } from "./test/fixtures";
import type { JobInput, Refinement } from "./api/types";

const photo = new File(["image"], "inverter.png", { type: "image/png" });

it("changing scope keeps the current workspace until an explicit re-recognition", async () => {
  const user = userEvent.setup();
  const jobs: JobInput[] = [];
  render(
    <App
      apiClient={fakeApi({
        createJob: async (input) => {
          jobs.push(input);
          return completed;
        },
      })}
    />,
  );
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "重新生成结构" })).toBeEnabled(),
  );
  await user.click(screen.getByRole("radio", { name: "多设备" }));
  expect(jobs).toHaveLength(1);
  expect(
    screen.getByRole("button", { name: "选择 逆变器机柜" }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "按当前范围重新识别" }));
  await waitFor(() => expect(jobs).toHaveLength(2));
  expect(jobs[1].scene_mode).toBe("multiple");
});

it("keeps a guided draft through language changes and applies only its server refinement reference", async () => {
  const user = userEvent.setup();
  let resolveMask!: (value: Refinement) => void;
  let submitted: JobInput | undefined;
  let calls = 0;
  render(
    <App
      apiClient={fakeApi({
        createJob: async (input) => {
          submitted = input;
          return completed;
        },
        refine: async () => {
          calls += 1;
          return new Promise((resolve) => {
            resolveMask = resolve;
          });
        },
      })}
    />,
  );
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "重新生成结构" })).toBeEnabled(),
  );
  await user.click(screen.getByRole("button", { name: "编辑 逆变器机柜" }));
  await user.click(screen.getByRole("button", { name: "细化边界" }));
  await waitFor(() => expect(calls).toBe(1));
  await user.selectOptions(
    screen.getByRole("combobox", { name: "语言 / Language / Idioma" }),
    "en",
  );
  expect(
    screen.getByRole("region", { name: "Boundary refinement draft" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Confirm region" })).toBeDisabled();
  expect(calls).toBe(1);
  await act(async () =>
    resolveMask({
      id: "guided-mask",
      asset_id: "asset-1",
      bbox: [0.1, 0.1, 0.5, 0.9],
      points: [],
      geometry_bbox: [0.12, 0.12, 0.48, 0.88],
      mask_polygons: [
        [
          [0.12, 0.12],
          [0.48, 0.12],
          [0.48, 0.88],
        ],
      ],
      mask_url: "/api/refinements/guided-mask/mask.png",
      model: { model_id: "sam2" },
      timings: {},
      warnings: [],
    }),
  );
  await user.click(screen.getByRole("button", { name: "Confirm region" }));
  expect(
    screen.queryByRole("region", { name: "Boundary refinement draft" }),
  ).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Regenerate structure" }),
  );
  expect(submitted?.components?.[0]).toMatchObject({
    id: "cabinet-1",
    bbox: [0.12, 0.12, 0.48, 0.88],
    refinement_id: "guided-mask",
  });
  expect(submitted?.components?.[0]).not.toHaveProperty("mask_polygons");
});

it("does not allow an automatic retry to overwrite a guided draft after detection failure", async () => {
  const user = userEvent.setup();
  let jobs = 0;
  render(
    <App
      apiClient={fakeApi({
        createJob: async () =>
          ++jobs === 1
            ? completed
            : {
                ...running,
                status: "failed",
                stage: "detecting",
                error: "Detection unavailable",
              },
        refine: async () => new Promise<Refinement>(() => {}),
      })}
    />,
  );
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "重新生成结构" })).toBeEnabled(),
  );
  await user.click(screen.getByRole("button", { name: "按当前范围重新识别" }));
  const retry = await screen.findByRole("button", { name: "重新识别" });
  await user.click(screen.getByRole("button", { name: "编辑 逆变器机柜" }));
  await user.click(screen.getByRole("button", { name: "细化边界" }));
  expect(retry).toBeDisabled();
  expect(jobs).toBe(2);
});

it("does not send a server null refinement as an intentional mask-clear edit", async () => {
  const user = userEvent.setup();
  const serverResult = {
    ...result,
    components: [{ ...cabinet, refinement_id: null }],
  };
  let submitted: JobInput | undefined;
  render(
    <App
      apiClient={fakeApi({
        createJob: async (input) => {
          submitted = input;
          return { ...completed, result: serverResult };
        },
      })}
    />,
  );
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  const rebuild = screen.getByRole("button", { name: "重新生成结构" });
  await waitFor(() => expect(rebuild).toBeEnabled());
  await user.click(rebuild);
  expect(submitted?.components?.[0]).not.toHaveProperty("refinement_id");
  expect(submitted?.base_job_id).toBe("job-1");
});

it("still sends explicit null when a user chooses box-only for a refined component", async () => {
  const user = userEvent.setup();
  const serverResult = {
    ...result,
    components: [{ ...cabinet, refinement_id: "prior-mask" }],
  };
  let submitted: JobInput | undefined;
  render(
    <App
      apiClient={fakeApi({
        createJob: async (input) => {
          submitted = input;
          return { ...completed, result: serverResult };
        },
        refine: async () => new Promise<Refinement>(() => {}),
      })}
    />,
  );
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "重新生成结构" })).toBeEnabled(),
  );
  await user.click(screen.getByRole("button", { name: "编辑 逆变器机柜" }));
  await user.click(screen.getByRole("button", { name: "细化边界" }));
  await user.click(screen.getByRole("button", { name: "仅用框保存" }));
  await user.click(screen.getByRole("button", { name: "重新生成结构" }));
  expect(submitted?.components?.[0].refinement_id).toBeNull();
});
