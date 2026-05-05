/**
 * Markdown note parser — frontmatter, wikilinks, Dataview inline fields, and the managed
 * ## Stigmem section. Mirrors the Python adapter's parser.py semantics exactly.
 */

// ---------------------------------------------------------------------------
// Regex patterns (mirrors Python adapter)
// ---------------------------------------------------------------------------

// [[wikilink]] or [[wikilink|alias]] or [[wikilink#heading]]
const WIKILINK_RE = /\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]/g;

// Dataview inline field: key:: value
const DATAVIEW_RE = /^([A-Za-z][A-Za-z0-9_ -]*)::[ \t]*(.+)$/gm;

// Fenced code blocks to strip before Dataview extraction
const CODE_BLOCK_RE = /```[\s\S]*?```/g;

export const STIGMEM_SECTION_HEADER = "## Stigmem";
const STIGMEM_SECTION_RE = /^## Stigmem\n([\s\S]*?)(?=^## |\Z)/m;

// ---------------------------------------------------------------------------
// Data shapes
// ---------------------------------------------------------------------------

export interface ParsedNote {
	relPath: string;
	title: string;
	frontmatter: Record<string, unknown>;
	wikilinks: string[];
	dataviewFields: Record<string, string>;
	body: string;
	contentHash: string;
	entityUri: string;
}

export interface StigmemFact {
	relation: string;
	value: string;
	source?: string;
}

// ---------------------------------------------------------------------------
// YAML frontmatter parsing (no external deps — inline minimal parser)
// ---------------------------------------------------------------------------

function parseFrontmatter(content: string): { meta: Record<string, unknown>; body: string } {
	if (!content.startsWith("---")) {
		return { meta: {}, body: content };
	}
	const end = content.indexOf("\n---", 4);
	if (end === -1) {
		return { meta: {}, body: content };
	}
	const yamlBlock = content.slice(4, end);
	const body = content.slice(end + 4).replace(/^\n/, "");
	const meta = parseYamlBlock(yamlBlock);
	return { meta, body };
}

/** Minimal YAML parser for simple scalar/list frontmatter (no nested maps). */
function parseYamlBlock(yaml: string): Record<string, unknown> {
	const result: Record<string, unknown> = {};
	const lines = yaml.split("\n");
	let i = 0;
	while (i < lines.length) {
		const line = lines[i];
		const colonIdx = line.indexOf(":");
		if (colonIdx === -1) { i++; continue; }
		const key = line.slice(0, colonIdx).trim();
		const rest = line.slice(colonIdx + 1).trim();
		if (!key) { i++; continue; }

		if (rest === "" || rest === "|" || rest === ">") {
			// Check if next lines are a YAML list
			const items: string[] = [];
			i++;
			while (i < lines.length && lines[i].match(/^[ \t]+-\s+/)) {
				items.push(lines[i].replace(/^[ \t]+-\s+/, "").trim());
				i++;
			}
			if (items.length > 0) {
				result[key] = items;
			} else {
				result[key] = null;
			}
			continue;
		}

		// Inline list: [a, b, c]
		if (rest.startsWith("[") && rest.endsWith("]")) {
			result[key] = rest.slice(1, -1).split(",").map(s => s.trim()).filter(Boolean);
			i++;
			continue;
		}

		// Quoted string
		if ((rest.startsWith('"') && rest.endsWith('"')) ||
			(rest.startsWith("'") && rest.endsWith("'"))) {
			result[key] = rest.slice(1, -1);
			i++;
			continue;
		}

		// Boolean
		if (rest === "true") { result[key] = true; i++; continue; }
		if (rest === "false") { result[key] = false; i++; continue; }

		// Number
		const num = Number(rest);
		if (!isNaN(num) && rest !== "") { result[key] = num; i++; continue; }

		result[key] = rest;
		i++;
	}
	return result;
}

// ---------------------------------------------------------------------------
// Content hash (FNV-32a — cheap, no crypto API needed in the browser)
// ---------------------------------------------------------------------------

function fnv32a(text: string): string {
	let hash = 0x811c9dc5;
	for (let i = 0; i < text.length; i++) {
		hash ^= text.charCodeAt(i);
		hash = (hash * 0x01000193) >>> 0;
	}
	return hash.toString(16).padStart(8, "0");
}

// ---------------------------------------------------------------------------
// Public parsers
// ---------------------------------------------------------------------------

export function parseNote(relPath: string, content: string): ParsedNote {
	const { meta, body } = parseFrontmatter(content);

	const title = (meta["title"] as string | undefined) ?? relPath.replace(/\.md$/, "").split("/").pop() ?? relPath;

	const wikilinks = extractWikilinks(body);
	const bodyNoCode = body.replace(CODE_BLOCK_RE, "");
	const dataviewFields = extractDataview(bodyNoCode);
	const contentHash = fnv32a(content);

	const stem = relPath.replace(/\.md$/, "");
	const entityUri = `obsidian://vault/${stem}`;

	return { relPath, title, frontmatter: meta, wikilinks, dataviewFields, body, contentHash, entityUri };
}

function extractWikilinks(text: string): string[] {
	const seen = new Set<string>();
	const result: string[] = [];
	let match: RegExpExecArray | null;
	const re = new RegExp(WIKILINK_RE.source, WIKILINK_RE.flags);
	while ((match = re.exec(text)) !== null) {
		const target = match[1].trim();
		if (target && !seen.has(target)) {
			seen.add(target);
			result.push(target);
		}
	}
	return result;
}

function extractDataview(text: string): Record<string, string> {
	const result: Record<string, string> = {};
	const re = new RegExp(DATAVIEW_RE.source, DATAVIEW_RE.flags);
	let match: RegExpExecArray | null;
	while ((match = re.exec(text)) !== null) {
		result[match[1].trim()] = match[2].trim();
	}
	return result;
}

// ---------------------------------------------------------------------------
// Stigmem section helpers (mirrors Python parser.py)
// ---------------------------------------------------------------------------

export function extractStigmemSection(content: string): string | null {
	const m = STIGMEM_SECTION_RE.exec(content);
	return m ? m[1].trim() : null;
}

export function replaceStigmemSection(content: string, newBody: string): string {
	const sectionText = `${STIGMEM_SECTION_HEADER}\n${newBody}\n`;
	if (STIGMEM_SECTION_RE.test(content)) {
		return content.replace(STIGMEM_SECTION_RE, sectionText);
	}
	const sep = content.endsWith("\n") ? "\n" : "\n\n";
	return content + sep + sectionText;
}

export function buildStigmemSectionBody(facts: StigmemFact[]): string {
	const lines: string[] = [];
	for (const fact of facts) {
		lines.push(`- relation: ${fact.relation}`);
		lines.push(`  value: ${fact.value}`);
		if (fact.source) lines.push(`  source: ${fact.source}`);
	}
	return lines.join("\n");
}

export function parseStigmemSectionBody(body: string): StigmemFact[] {
	const facts: StigmemFact[] = [];
	let current: Partial<StigmemFact> = {};
	for (const line of body.split("\n")) {
		const s = line.trim();
		if (s.startsWith("- relation:")) {
			if (current.relation) facts.push(current as StigmemFact);
			current = { relation: s.slice("- relation:".length).trim() };
		} else if (s.startsWith("value:") && current.relation) {
			current.value = s.slice("value:".length).trim();
		} else if (s.startsWith("source:") && current.relation) {
			current.source = s.slice("source:".length).trim();
		}
	}
	if (current.relation) facts.push(current as StigmemFact);
	return facts;
}

export function addConflictComment(content: string, conflictNote: string): string {
	return content + `\n%%stigmem-conflict: ${conflictNote}%%\n`;
}
