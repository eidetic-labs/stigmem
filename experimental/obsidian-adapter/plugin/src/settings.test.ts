import { describe, expect, it } from "vitest";

import { DEFAULT_SETTINGS, isIgnored, scopeForPath, type PluginSettings } from "./settings";

describe("scopeForPath", () => {
  it("uses the first matching folder override before default scope", () => {
    const settings: PluginSettings = {
      ...DEFAULT_SETTINGS,
      scope: "local",
      folderScopes: [
        { folder: "team/", scope: "team" },
        { folder: "team/private/", scope: "company" },
      ],
    };

    expect(scopeForPath("team/roadmap.md", settings)).toBe("team");
    expect(scopeForPath("elsewhere/note.md", settings)).toBe("local");
  });
});

describe("isIgnored", () => {
  it("matches configured glob patterns", () => {
    const settings: PluginSettings = {
      ...DEFAULT_SETTINGS,
      ignoredPaths: [".obsidian/**", "templates/**", "*.tmp"],
    };

    expect(isIgnored(".obsidian/workspace.json", settings)).toBe(true);
    expect(isIgnored("templates/daily.md", settings)).toBe(true);
    expect(isIgnored("scratch.tmp", settings)).toBe(true);
    expect(isIgnored("notes/real-note.md", settings)).toBe(false);
  });
});
