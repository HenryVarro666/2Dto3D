import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { PhotoPanel } from "./PhotoPanel";
import { asset, bracket, cabinet } from "../test/fixtures";

it("keeps original component numbers on photo overlays when an earlier component is hidden", () => {
  render(
    <PhotoPanel
      imageUrl={asset.image_url}
      fileName="inverter.png"
      asset={asset}
      components={[cabinet, bracket]}
      selectedId={null}
      hiddenIds={new Set(["cabinet-1"])}
      drawing={false}
      canDraw
      onSelect={() => {}}
      onChoose={() => {}}
      onFile={() => {}}
      onDrawingChange={() => {}}
      onBox={() => {}}
    />,
  );

  expect(
    screen.queryByRole("button", { name: "照片中选择 逆变器机柜" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "照片中选择 安装支架" }),
  ).toHaveTextContent("02 安装支架");
});
