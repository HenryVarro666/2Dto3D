import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import App from "./App";
import { bracket, cabinet, completed, fakeApi, result } from "./test/fixtures";
import type { Job, JobInput } from "./api/types";

it("starts with a usable upload workspace and reports actual API model state", async () => {
  render(
    <App
      apiClient={fakeApi({
        health: async () => ({
          status: "ok",
          model: {
            state: "loading",
            model_id: "Grounding DINO",
            device: "mps",
          },
        }),
      })}
    />,
  );
  expect(
    screen.getByRole("heading", { name: "设备结构工作台" }),
  ).toBeInTheDocument();
  expect(screen.getByText("拖入一张设备照片")).toBeInTheDocument();
  expect(await screen.findByText("模型载入中")).toBeInTheDocument();
  expect(screen.getByText("尺寸未标定")).toBeInTheDocument();
});

it("keeps an upload failure visible without inventing recognized components", async () => {
  const user = userEvent.setup();
  render(
    <App
      apiClient={fakeApi({
        uploadAsset: async () => {
          throw new Error("图片解码失败，请换一张照片。");
        },
      })}
    />,
  );
  await user.upload(
    screen.getByLabelText("选择设备照片"),
    new File(["bad image"], "broken.png", { type: "image/png" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("图片解码失败");
  expect(screen.getByText("还没有组件候选")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /选择 逆变器/ }),
  ).not.toBeInTheDocument();
});

it("locks component mutations while a submitted manual rebuild is pending", async () => {
  const user = userEvent.setup();
  let resolveManual!: (job: Job) => void;
  let submitted: JobInput | undefined;
  const pendingJob = new Promise<Job>((resolve) => {
    resolveManual = resolve;
  });
  render(
    <App
      apiClient={fakeApi({
        createJob: async (input) => {
          if (input.mode === "manual") {
            submitted = input;
            return pendingJob;
          }
          return completed;
        },
      })}
    />,
  );
  await user.upload(
    screen.getByLabelText("选择设备照片"),
    new File(["image"], "inverter.png", { type: "image/png" }),
  );
  const rebuildButton = screen.getByRole("button", { name: "重新生成结构" });
  await waitFor(() => expect(rebuildButton).toBeEnabled());
  await user.click(screen.getByRole("button", { name: "编辑 逆变器机柜" }));
  const nameInput = screen.getByRole("textbox", { name: "组件名称" });
  await user.clear(nameInput);
  await user.type(nameInput, "已提交机柜");
  await user.click(rebuildButton);

  expect(nameInput).toBeDisabled();
  expect(screen.getByRole("combobox", { name: "组件类别" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "移除组件" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "编辑 安装支架" })).toBeDisabled();
  for (const button of screen.getAllByRole("button", { name: "添加组件框" })) {
    expect(button).toBeDisabled();
  }
  expect(screen.getByRole("checkbox", { name: "显示 安装支架" })).toBeEnabled();
  await user.type(nameInput, "不会被提交的修改");
  await user.click(screen.getByRole("button", { name: "移除组件" }));
  expect(nameInput).toHaveValue("已提交机柜");
  expect(submitted?.components?.[0].label).toBe("已提交机柜");

  await act(async () => {
    resolveManual({
      ...completed,
      id: "manual-job",
      result: {
        ...result,
        job_id: "manual-job",
        scene_url: "/api/jobs/manual-job/scene.glb",
        components: [{ ...cabinet, label: "已提交机柜" }, bracket],
      },
    });
  });
  await waitFor(() => expect(nameInput).toBeEnabled());
  expect(nameInput).toHaveValue("已提交机柜");
  expect(
    screen.getByRole("button", { name: "选择 安装支架" }),
  ).toBeInTheDocument();
});

it("keeps progress incomplete when the viewer fails again after a manual rebuild", async () => {
  // JSDOM has no WebGL. Use the actual viewer failure path, not a success stub.
  const user = userEvent.setup();
  render(
    <App
      apiClient={fakeApi({
        createJob: async (input) =>
          input.mode === "manual"
            ? {
                ...completed,
                id: "manual-viewer-failure",
                result: {
                  ...result,
                  job_id: "manual-viewer-failure",
                  scene_url: "/api/jobs/manual-viewer-failure/scene.glb",
                },
              }
            : completed,
      })}
    />,
  );
  await user.upload(
    screen.getByLabelText("选择设备照片"),
    new File(["image"], "inverter.png", { type: "image/png" }),
  );
  await screen.findByText(/此浏览器无法使用 WebGL/);
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "5");
  await user.click(screen.getByRole("button", { name: "重新生成结构" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "重新生成结构" })).toBeEnabled(),
  );
  expect(screen.getByText(/此浏览器无法使用 WebGL/)).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "3");
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "2");
  expect(
    screen.getByText("结构文件已生成，查看器暂不可用"),
  ).toBeInTheDocument();
});
