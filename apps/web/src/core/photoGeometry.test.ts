import { describe, expect, it } from "vitest";
import {
  containedImageRect,
  normalizedPoint,
  boxFromPoints,
} from "./photoGeometry";

describe("photo coordinates", () => {
  it("excludes letterboxing when a wide photo is inside a square panel", () => {
    expect(containedImageRect(600, 600, 1200, 600)).toEqual({
      left: 0,
      top: 150,
      width: 600,
      height: 300,
    });
    expect(
      normalizedPoint(150, 225, { left: 0, top: 150, width: 600, height: 300 }),
    ).toEqual([0.25, 0.25]);
  });
  it("normalizes reverse drawing and rejects a click or negligible box", () => {
    expect(boxFromPoints([0.8, 0.9], [0.2, 0.3])).toEqual([0.2, 0.3, 0.8, 0.9]);
    expect(boxFromPoints([0.5, 0.5], [0.501, 0.501])).toBeNull();
  });
});
