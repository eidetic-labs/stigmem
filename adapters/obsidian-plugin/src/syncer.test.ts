import { beforeEach, describe, expect, it, vi } from "vitest";

import { VaultSyncer } from "./syncer";
import { DEFAULT_SETTINGS, type PluginSettings } from "./settings";

type FakeFile = { path: string };

class FakeVault {
  contents = new Map<string, string>();
  writes: Array<{ path: string; content: string }> = [];

  constructor(seed: Record<string, string>) {
    for (const [path, content] of Object.entries(seed)) {
      this.contents.set(path, content);
    }
  }

  async read(file: FakeFile): Promise<string> {
    return this.contents.get(file.path) ?? "";
  }

  async modify(file: FakeFile, content: string): Promise<void> {
    this.contents.set(file.path, content);
    this.writes.push({ path: file.path, content });
  }

  getMarkdownFiles(): FakeFile[] {
    return [...this.contents.keys()].map((path) => ({ path }));
  }
}

describe("VaultSyncer", () => {
  let settings: PluginSettings;

  beforeEach(() => {
    settings = {
      ...DEFAULT_SETTINGS,
      scope: "company",
      ignoredPaths: [],
      wikilinkRelation: "references",
      conflictPolicy: "comment",
    };
  });

  it("pushes note facts and pulls external facts into the managed section", async () => {
    const vault = new FakeVault({
      "notes/Alice.md": `---
title: Alice
---
Hello [[projects/loom]].
role:: engineer
`,
    });
    const syncer = new VaultSyncer(vault as never, settings);
    const assertFact = vi.fn().mockResolvedValue({});
    const queryAll = vi.fn().mockResolvedValue([
      {
        relation: "note:role",
        value: { type: "string", v: "CEO" },
        source: "agent:cto",
      },
    ]);
    (syncer as unknown as { client: { assertFact: typeof assertFact; queryAll: typeof queryAll } }).client = {
      assertFact,
      queryAll,
    };

    const result = await syncer.syncNote({ path: "notes/Alice.md" } as never);

    expect(result.errors).toEqual([]);
    expect(result.vaultToStigmem).toBeGreaterThanOrEqual(4);
    expect(result.stigmemToVault).toBe(1);
    expect(assertFact).toHaveBeenCalledWith(
      expect.objectContaining({
        entity: "obsidian://vault/notes/Alice",
        relation: "note:title",
        source: "obsidian://vault/notes/Alice.md",
        scope: "company",
      }),
    );
    expect(assertFact).toHaveBeenCalledWith(
      expect.objectContaining({
        relation: "references",
        value: { type: "ref", v: "obsidian://vault/projects/loom" },
      }),
    );
    expect(vault.contents.get("notes/Alice.md")).toContain("## Stigmem");
    expect(vault.contents.get("notes/Alice.md")).toContain("value: CEO");
  });

  it("adds a conflict comment when vault and stigmem disagree under comment policy", async () => {
    const vault = new FakeVault({
      "notes/Bob.md": `# Bob

## Stigmem
- relation: note:role
  value: engineer
  source: obsidian://vault/notes/Bob.md
`,
    });
    const syncer = new VaultSyncer(vault as never, settings);
    (syncer as unknown as { client: { assertFact: ReturnType<typeof vi.fn>; queryAll: ReturnType<typeof vi.fn> } }).client = {
      assertFact: vi.fn().mockResolvedValue({}),
      queryAll: vi.fn().mockResolvedValue([
        {
          relation: "note:role",
          value: { type: "string", v: "CTO" },
          source: "agent:cto",
        },
      ]),
    };

    const result = await syncer.syncNote({ path: "notes/Bob.md" } as never);

    expect(result.conflicts).toBe(1);
    expect(vault.contents.get("notes/Bob.md")).toContain("%%stigmem-conflict:");
    expect(vault.contents.get("notes/Bob.md")).toContain("vault=engineer stigmem=CTO");
  });
});
