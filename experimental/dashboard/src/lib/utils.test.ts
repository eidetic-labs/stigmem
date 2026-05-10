import { describe, expect, it } from "vitest";

import { SCOPES, cn, fmtConfidence, fmtValue, ROLES } from "./utils";

describe("utils", () => {
  it("merges tailwind classes predictably", () => {
    expect(cn("px-2", false && "hidden", "px-4", "text-sm")).toBe("px-4 text-sm");
  });

  it("formats confidence and typed values", () => {
    expect(fmtConfidence(0.834)).toBe("83%");
    expect(fmtValue("null", null)).toBe("∅ null");
    expect(fmtValue("boolean", false)).toBe("false");
    expect(fmtValue("string", "CEO")).toBe("CEO");
  });

  it("exposes the full supported scope and role sets", () => {
    expect(SCOPES).toEqual(["local", "team", "company", "public"]);
    expect(ROLES).toEqual(["reader", "writer", "admin"]);
  });
});
