import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import App from "../App";
import { MultiviewWorkbench } from "./MultiviewWorkbench";
import {
  capture,
  fakeApi,
  multiCompleted,
  multiResult,
} from "../test/fixtures";
import type { MultiJobInput } from "../api/types";

const photos = ["front", "side"].map(
  (name) => new File([name], `${name}.png`, { type: "image/png" }),
);

it("keeps per-view edits, global association and language while preserving single mode", async () => {
  const user = userEvent.setup();
  const inputs: MultiJobInput[] = [];
  const create = vi.fn(async (input: MultiJobInput) => {
    inputs.push(input);
    return input.mode === "manual"
      ? {
          ...multiCompleted,
          id: "multi-2",
          result: {
            ...multiResult,
            job_id: "multi-2",
            scene_url: "/api/multiview/jobs/multi-2/cloud.glb",
            observations: input.observations!.map((o) => ({
              ...multiResult.observations.find((old) => old.id === o.id)!,
              ...o,
            })),
          },
        }
      : multiCompleted;
  });
  render(
    <App
      apiClient={fakeApi({
        createCapture: async () => capture,
        createMultiJob: create,
      })}
    />,
  );
  await user.click(screen.getByRole("button", { name: "多角度点云" }));
  await user.upload(screen.getByLabelText("选择多角度照片"), photos);
  expect(create).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "融合并识别组件" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "应用校正到点云" }),
    ).toBeEnabled(),
  );
  // jsdom intentionally has no WebGL: failed viewer loading must not mark all stages complete.
  expect(
    screen.getByRole("progressbar", { name: "多图阶段进度" }),
  ).toHaveAttribute("aria-valuenow", "5");
  await user.click(screen.getByRole("button", { name: "编辑 逆变器机柜" }));
  const name = screen.getByRole("textbox", { name: "组件名称" });
  await user.clear(name);
  await user.type(name, "Housing A");
  await user.click(screen.getByRole("button", { name: "照片 2：side.png" }));
  await user.click(screen.getByRole("button", { name: "编辑 Housing A" }));
  expect(screen.getByRole("textbox", { name: "组件名称" })).toHaveValue(
    "Housing A",
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "语言 / Language / Idioma" }),
    "es",
  );
  expect(
    screen.getByRole("textbox", { name: "Nombre del componente" }),
  ).toHaveValue("Housing A");
  await user.click(
    screen.getByRole("button", { name: "Separar como componente nuevo" }),
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Asociar a un componente global" }),
    "part-1",
  );
  expect(
    screen.getByRole("combobox", { name: "Asociar a un componente global" }),
  ).toHaveValue("part-1");
  await user.click(
    screen.getByRole("button", { name: "Separar como componente nuevo" }),
  );
  await user.click(
    screen.getByRole("button", { name: "Aplicar correcciones a la nube" }),
  );
  expect(inputs[1].observations).toHaveLength(2);
  expect(inputs[1].observations?.map((o) => o.label)).toEqual([
    "Housing A",
    "Housing A",
  ]);
  expect(inputs[1].observations?.[0].component_id).not.toBe(
    inputs[1].observations?.[1].component_id,
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Una foto" })).toBeEnabled(),
  );
  await user.click(screen.getByRole("button", { name: "Una foto" }));
  expect(
    screen.getByRole("heading", { name: "Mesa de trabajo de estructuras" }),
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Nube de múltiples vistas" }),
  );
  expect(
    screen.getByRole("button", { name: "Foto 2: side.png" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(create).toHaveBeenCalledTimes(2);
});

it("runs guided correction against the active photo and blocks changing views during a draft", async () => {
  const user = userEvent.setup();
  const refine = vi.fn(fakeApi().refine);
  render(
    <App
      apiClient={fakeApi({
        createCapture: async () => capture,
        createMultiJob: async () => multiCompleted,
        refine,
      })}
    />,
  );
  await user.click(screen.getByRole("button", { name: "多角度点云" }));
  await user.upload(screen.getByLabelText("选择多角度照片"), photos);
  await user.click(screen.getByRole("button", { name: "融合并识别组件" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "应用校正到点云" }),
    ).toBeEnabled(),
  );
  await user.click(screen.getByRole("button", { name: "照片 2：side.png" }));
  await user.click(screen.getByRole("button", { name: "编辑 逆变器机柜" }));
  await user.click(screen.getByRole("button", { name: "细化边界" }));
  expect(
    screen.getByRole("button", { name: "照片 1：front.png" }),
  ).toBeDisabled();
  await waitFor(() => expect(refine).toHaveBeenCalled());
  expect(refine.mock.calls[0][0].asset_id).toBe(multiResult.views[1].id);
  await user.click(screen.getByRole("button", { name: "确认区域" }));
  expect(
    screen.getByRole("button", { name: "照片 1：front.png" }),
  ).toBeEnabled();
});

it("reopening the same saved result releases the workspace lock", async () => {
  const id = "a".repeat(32);
  const defaults = fakeApi();
  const getMeasurements = vi.fn(defaults.getMeasurements);
  const api = fakeApi({
    getMeasurements,
    getMultiJob: vi.fn(async () => ({
      ...multiCompleted,
      id,
      result: {
        ...multiResult,
        job_id: id,
        scene_url: `/api/multiview/jobs/${id}/cloud.glb`,
      },
    })),
    getCapture: async () => capture,
  });
  const user = userEvent.setup();
  render(<MultiviewWorkbench apiClient={api} onBusyChange={vi.fn()} />);
  await user.type(screen.getByLabelText("多图任务 ID"), id);
  const open = screen.getByRole("button", { name: "打开已有结果" });
  await user.click(open);
  await waitFor(() => expect(open).toBeEnabled());
  await user.click(open);
  await waitFor(() => expect(api.getMultiJob).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(open).toBeEnabled(), { timeout: 600 });
  await waitFor(() => expect(getMeasurements).toHaveBeenCalledTimes(2));
});

it("keeps authored measurement demos viewable without offering unsupported reconstruction edits", async () => {
  const id = "b".repeat(32);
  const user = userEvent.setup();
  const api = fakeApi({
    getMultiJob: async () => ({
      ...multiCompleted,
      id,
      result: {
        ...multiResult,
        job_id: id,
        model: { ...multiResult.model, not_model_inference: true },
      },
    }),
  });
  render(<MultiviewWorkbench apiClient={api} onBusyChange={vi.fn()} />);
  await user.type(screen.getByLabelText("多图任务 ID"), id);
  await user.click(screen.getByRole("button", { name: "打开已有结果" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "打开已有结果" })).toBeEnabled(),
  );
  expect(screen.getByRole("button", { name: "应用校正到点云" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "添加组件框" })).toBeDisabled();
  expect(
    screen.getByRole("region", { name: "标定与测距" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "导出测量记录" }),
  ).toBeInTheDocument();
});
