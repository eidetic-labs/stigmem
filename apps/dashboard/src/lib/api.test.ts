import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, stigmemFetch, stigmemJson } from "./api";

describe("stigmemFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("forwards the api key and JSON headers to the backend", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );

    await stigmemFetch("/v1/facts", "sk-test", { method: "POST", body: "{}" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8765/v1/facts",
      expect.objectContaining({
        method: "POST",
        body: "{}",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          Authorization: "Bearer sk-test",
        }),
      }),
    );
  });
});

describe("stigmemJson", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns parsed JSON for successful responses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ facts: [], total: 0, cursor: null }), { status: 200 }),
    );

    await expect(stigmemJson("/v1/facts", "sk-test")).resolves.toEqual({
      facts: [],
      total: 0,
      cursor: null,
    });
  });

  it("raises ApiError with backend detail when present", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "forbidden" }), { status: 403, statusText: "Forbidden" }),
    );

    await expect(stigmemJson("/v1/facts", "sk-test")).rejects.toEqual(
      new ApiError(403, "forbidden"),
    );
  });

  it("falls back to status text when error JSON is unavailable", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("gateway timeout", { status: 504, statusText: "Gateway Timeout" }),
    );

    await expect(stigmemJson("/v1/facts", "sk-test")).rejects.toEqual(
      new ApiError(504, "Gateway Timeout"),
    );
  });
});
