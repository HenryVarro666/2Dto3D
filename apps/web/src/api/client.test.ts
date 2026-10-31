import { afterEach, expect, it, vi } from "vitest";
import { createApi } from "./client";

afterEach(() => vi.unstubAllGlobals());

it("passes a real upload as multipart and renders a safe server validation error", async () => {
  let request: RequestInit | undefined;
  vi.stubGlobal("fetch", async (_url: string, init: RequestInit) => {
    request = init;
    return new Response(JSON.stringify({ detail: "图片超过 20MB 上限" }), {
      status: 413,
      headers: { "Content-Type": "application/json" },
    });
  });
  const api = createApi();
  await expect(
    api.uploadAsset(new File(["image"], "photo.png", { type: "image/png" })),
  ).rejects.toThrow("图片超过 20MB 上限");
  expect(request?.body).toBeInstanceOf(FormData);
  expect((request?.body as FormData).get("file")).toBeInstanceOf(File);
});

it("shows an actionable connection failure when the local API cannot be reached", async () => {
  vi.stubGlobal("fetch", async () => {
    throw new TypeError("Failed to fetch");
  });
  await expect(createApi().health()).rejects.toThrow("无法连接本地服务");
});
