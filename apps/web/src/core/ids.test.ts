import { afterEach, describe, expect, it, vi } from "vitest";
import { newId } from "./ids";

const UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe("newId", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("produces unique RFC 4122 identifiers", () => {
    const ids = new Set(Array.from({ length: 200 }, () => newId()));
    expect(ids.size).toBe(200);
    for (const id of ids) expect(id).toMatch(UUID);
  });

  it("works without randomUUID, as in insecure HTTP contexts", () => {
    const getRandomValues = (array: Uint8Array) => {
      for (let i = 0; i < array.length; i += 1) array[i] = (i * 37 + 11) & 0xff;
      return array;
    };
    vi.stubGlobal("crypto", { getRandomValues });
    const id = newId();
    expect(id).toMatch(UUID);
    expect(newId()).toBe(id);
  });

  it("still produces a well-formed id with no crypto object at all", () => {
    vi.stubGlobal("crypto", undefined);
    expect(newId()).toMatch(UUID);
  });
});
