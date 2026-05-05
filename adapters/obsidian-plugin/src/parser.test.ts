import { describe, expect, it } from "vitest";

import {
  addConflictComment,
  buildStigmemSectionBody,
  extractStigmemSection,
  parseNote,
  parseStigmemSectionBody,
  replaceStigmemSection,
} from "./parser";

describe("parseNote", () => {
  it("extracts frontmatter, wikilinks, dataview fields, and entity URI", () => {
    const parsed = parseNote(
      "notes/Alice.md",
      `---
title: Alice Note
tags:
  - person
score: 7
---
Hello [[Project Loom|Loom]].
role:: engineer
\`\`\`
ignored:: field
\`\`\`
`,
    );

    expect(parsed.title).toBe("Alice Note");
    expect(parsed.frontmatter).toMatchObject({ title: "Alice Note", score: 7, tags: ["person"] });
    expect(parsed.wikilinks).toEqual(["Project Loom"]);
    expect(parsed.dataviewFields).toEqual({ role: "engineer" });
    expect(parsed.entityUri).toBe("obsidian://vault/notes/Alice");
    expect(parsed.contentHash).toMatch(/^[0-9a-f]{8}$/);
  });

  it("falls back to filename when frontmatter title is absent", () => {
    const parsed = parseNote("people/Bob.md", "# Bob\n");
    expect(parsed.title).toBe("Bob");
    expect(parsed.entityUri).toBe("obsidian://vault/people/Bob");
  });
});

describe("Stigmem section helpers", () => {
  it("round-trips managed section facts", () => {
    const body = buildStigmemSectionBody([
      { relation: "note:role", value: "CEO", source: "agent:cto" },
      { relation: "references", value: "obsidian://vault/projects/loom" },
    ]);

    expect(parseStigmemSectionBody(body)).toEqual([
      { relation: "note:role", value: "CEO", source: "agent:cto" },
      { relation: "references", value: "obsidian://vault/projects/loom" },
    ]);
  });

  it("replaces or appends the managed section and can add conflict comments", () => {
    const initial = "# Alice\n\nBody.\n";
    const withSection = replaceStigmemSection(initial, "- relation: note:role\n  value: CEO");
    expect(extractStigmemSection(withSection)).toContain("note:role");

    const updated = replaceStigmemSection(withSection, "- relation: note:role\n  value: CTO");
    expect(extractStigmemSection(updated)).toContain("CTO");

    const conflicted = addConflictComment(updated, "relation=note:role vault=CEO stigmem=CTO");
    expect(conflicted).toContain("%%stigmem-conflict:");
  });
});
