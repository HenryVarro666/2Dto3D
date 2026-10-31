import type { BBox, Point } from "../api/types";

export type ImageRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

export function containedImageRect(
  panelWidth: number,
  panelHeight: number,
  imageWidth: number,
  imageHeight: number,
): ImageRect {
  if (!panelWidth || !panelHeight || !imageWidth || !imageHeight)
    return { left: 0, top: 0, width: 0, height: 0 };
  const scale = Math.min(panelWidth / imageWidth, panelHeight / imageHeight);
  const width = imageWidth * scale;
  const height = imageHeight * scale;
  return {
    left: (panelWidth - width) / 2,
    top: (panelHeight - height) / 2,
    width,
    height,
  };
}

export function normalizedPoint(x: number, y: number, rect: ImageRect): Point {
  const clamp = (value: number) => Math.max(0, Math.min(1, value));
  return [
    clamp((x - rect.left) / rect.width),
    clamp((y - rect.top) / rect.height),
  ];
}

export function boxFromPoints(a: Point, b: Point): BBox | null {
  const bbox: BBox = [
    Math.min(a[0], b[0]),
    Math.min(a[1], b[1]),
    Math.max(a[0], b[0]),
    Math.max(a[1], b[1]),
  ];
  return bbox[2] - bbox[0] < 0.01 || bbox[3] - bbox[1] < 0.01 ? null : bbox;
}
