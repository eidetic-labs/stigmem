import { describe, expect, it, vi } from "vitest";

describe("SESSION_OPTIONS", () => {
  it("uses the configured secret and secure production cookies", async () => {
    vi.resetModules();
    vi.stubEnv("SESSION_SECRET", "super-secret");
    vi.stubEnv("NODE_ENV", "production");

    const { SESSION_OPTIONS } = await import("./session");

    expect(SESSION_OPTIONS.password).toBe("super-secret");
    expect(SESSION_OPTIONS.cookieName).toBe("stigmem_session");
    expect(SESSION_OPTIONS.cookieOptions?.secure).toBe(true);
    expect(SESSION_OPTIONS.cookieOptions?.maxAge).toBe(60 * 60 * 8);
  });

  it("falls back to the development secret outside production", async () => {
    vi.resetModules();
    vi.unstubAllEnvs();
    vi.stubEnv("NODE_ENV", "test");

    const { SESSION_OPTIONS } = await import("./session");

    expect(SESSION_OPTIONS.password).toBe("changeme-set-SESSION_SECRET-in-env");
    expect(SESSION_OPTIONS.cookieOptions?.secure).toBe(false);
    expect(SESSION_OPTIONS.cookieOptions?.sameSite).toBe("lax");
  });
});
