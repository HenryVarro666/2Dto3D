import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { SceneViewer } from "./SceneViewer";

it("shows an actionable WebGL fallback instead of a blank model panel", async () => {
  render(
    <SceneViewer
      sceneUrl="/api/jobs/test/scene.glb"
      componentIds={["cabinet-1"]}
      selectedId={null}
      hiddenIds={new Set()}
      explosion={0}
      wireframe={false}
      resetKey={0}
      onSelect={() => {}}
      onReady={() => {}}
    />,
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("WebGL");
  expect(screen.getByText(/硬件加速/)).toBeInTheDocument();
});
