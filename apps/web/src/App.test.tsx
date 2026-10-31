import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import App from "./App";
import { fakeApi } from "./test/fixtures";

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
