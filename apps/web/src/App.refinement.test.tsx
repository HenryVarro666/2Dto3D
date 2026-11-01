// Preload the real viewer before timed UI waits; cold transforms can exceed 1s on CI.
import "./components/SceneViewer";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
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

function drawNewBox(container: HTMLElement) {
  const surface = container.querySelector<HTMLElement>(".photo-fit")!;
  vi.spyOn(surface, "getBoundingClientRect").mockReturnValue({
    x: 0,
    y: 0,
    left: 0,
    top: 0,
    width: 1000,
    height: 1000,
    right: 1000,
    bottom: 1000,
    toJSON: () => ({}),
  });
  fireEvent.pointerDown(surface, { clientX: 600, clientY: 600 });
  fireEvent.pointerMove(surface, { clientX: 900, clientY: 900 });
  fireEvent.pointerUp(surface, { clientX: 900, clientY: 900 });
}

it.each(["exit", "other refinement"])(
  "creates a new component after abandoning a redraw via %s",
  async (abandonment) => {
    vi.stubGlobal("PointerEvent", MouseEvent);
    try {
      const user = userEvent.setup();
      let submitted: JobInput | undefined;
      const { container } = render(
        <App
          apiClient={fakeApi({
            createJob: async (input) => {
              submitted = input;
              return completed;
            },
            refine: async () => new Promise<Refinement>(() => {}),
          })}
        />,
      );
      await user.upload(screen.getByLabelText("选择设备照片"), photo);
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: "重新生成结构" }),
        ).toBeEnabled(),
      );
      await user.click(screen.getByRole("button", { name: "编辑 逆变器机柜" }));
      await user.click(screen.getByRole("button", { name: "细化边界" }));
      await user.click(screen.getByRole("button", { name: "重新框选" }));
      if (abandonment === "exit") {
        await user.click(screen.getByRole("button", { name: "退出框选" }));
      } else {
        await user.click(screen.getByRole("button", { name: "编辑 安装支架" }));
        await user.click(screen.getByRole("button", { name: "细化边界" }));
        await user.click(screen.getByRole("button", { name: "取消边界细化" }));
      }
      await user.click(
        screen.getAllByRole("button", { name: "添加组件框" })[0],
      );
      drawNewBox(container);
      await user.click(screen.getByRole("button", { name: "仅用框保存" }));
      await user.click(screen.getByRole("button", { name: "重新生成结构" }));
      expect(submitted?.components).toHaveLength(3);
      expect(submitted?.components?.[0]).toMatchObject({
        id: cabinet.id,
        bbox: cabinet.bbox,
      });
      expect(submitted?.components?.[2].id).not.toBe(cabinet.id);
    } finally {
      vi.unstubAllGlobals();
      vi.restoreAllMocks();
    }
  },
);

it("preserves the original component ID when redraw is completed without abandonment", async () => {
  vi.stubGlobal("PointerEvent", MouseEvent);
  try {
    const user = userEvent.setup();
    let submitted: JobInput | undefined;
    const { container } = render(
      <App
        apiClient={fakeApi({
          createJob: async (input) => {
            submitted = input;
            return completed;
          },
          refine: async () => new Promise<Refinement>(() => {}),
        })}
      />,
    );
    await user.upload(screen.getByLabelText("选择设备照片"), photo);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "重新生成结构" }),
      ).toBeEnabled(),
    );
    await user.click(screen.getByRole("button", { name: "编辑 逆变器机柜" }));
    await user.click(screen.getByRole("button", { name: "细化边界" }));
    await user.click(screen.getByRole("button", { name: "重新框选" }));
    drawNewBox(container);
    await user.click(screen.getByRole("button", { name: "仅用框保存" }));
    await user.click(screen.getByRole("button", { name: "重新生成结构" }));
    expect(submitted?.components).toHaveLength(2);
    expect(submitted?.components?.[0]).toMatchObject({
      id: cabinet.id,
      bbox: [0.6, 0.6, 0.9, 0.9],
    });
  } finally {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  }
});
