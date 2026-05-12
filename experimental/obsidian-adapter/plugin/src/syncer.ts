/**
 * Vault ↔ stigmem sync engine.
 *
 * Mirrors the Python adapter's syncer.py semantics exactly:
 *   Pass 1: vault → stigmem (push facts from the current note)
 *   Pass 2: stigmem → vault (pull external facts back into ## Stigmem section)
 *
 * Source URI convention: obsidian://vault/<rel-path>
 * Entity URI convention: obsidian://vault/<rel-path-without-.md>
 */

import { TFile, Vault } from "obsidian";
import type { PluginSettings } from "./settings";
import { isIgnored, scopeForPath } from "./settings";
import { StigmemClient, stringValue, numberValue, booleanValue, refValue, type FactRecord } from "./StigmemClient";
import {
	parseNote,
	extractStigmemSection,
	parseStigmemSectionBody,
	buildStigmemSectionBody,
	replaceStigmemSection,
	addConflictComment,
	type StigmemFact,
} from "./parser";

// ---------------------------------------------------------------------------
// Result shape
// ---------------------------------------------------------------------------

export interface SyncResult {
	vaultToStigmem: number;
	stigmemToVault: number;
	conflicts: number;
	errors: string[];
}

const SOURCE_VAULT_PREFIX = "obsidian://vault";

// ---------------------------------------------------------------------------
// VaultSyncer
// ---------------------------------------------------------------------------

export class VaultSyncer {
	private client: StigmemClient;

	constructor(private vault: Vault, private settings: PluginSettings) {
		this.client = new StigmemClient(settings.nodeUrl, settings.apiKey || null);
	}

	/** Recreate the client after settings change. */
	updateClient(): void {
		this.client = new StigmemClient(this.settings.nodeUrl, this.settings.apiKey || null);
	}

	// -----------------------------------------------------------------------
	// Public: sync a single note file
	// -----------------------------------------------------------------------

	async syncNote(file: TFile): Promise<SyncResult> {
		const result: SyncResult = { vaultToStigmem: 0, stigmemToVault: 0, conflicts: 0, errors: [] };
		const relPath = file.path;

		if (isIgnored(relPath, this.settings)) return result;
		if (!relPath.endsWith(".md")) return result;

		let content: string;
		try {
			content = await this.vault.read(file);
		} catch (e) {
			result.errors.push(`read failed: ${relPath}: ${e}`);
			return result;
		}

		const note = parseNote(relPath, content);
		const scope = scopeForPath(relPath, this.settings);
		const source = `${SOURCE_VAULT_PREFIX}/${relPath}`;

		// Pass 1: vault → stigmem
		try {
			result.vaultToStigmem += await this.pushNote(note, scope, source);
		} catch (e) {
			result.errors.push(`push failed: ${relPath}: ${e}`);
		}

		// Pass 2: stigmem → vault
		try {
			const pulled = await this.pullEntity(file, note.entityUri, scope, source);
			result.stigmemToVault += pulled.written;
			result.conflicts += pulled.conflicts;
		} catch (e) {
			result.errors.push(`pull failed: ${relPath}: ${e}`);
		}

		return result;
	}

	// -----------------------------------------------------------------------
	// Public: full vault scan
	// -----------------------------------------------------------------------

	async syncAll(): Promise<SyncResult> {
		const result: SyncResult = { vaultToStigmem: 0, stigmemToVault: 0, conflicts: 0, errors: [] };
		const files = this.vault.getMarkdownFiles();
		for (const file of files) {
			const r = await this.syncNote(file);
			result.vaultToStigmem += r.vaultToStigmem;
			result.stigmemToVault += r.stigmemToVault;
			result.conflicts += r.conflicts;
			result.errors.push(...r.errors);
		}
		return result;
	}

	// -----------------------------------------------------------------------
	// Pass 1: vault → stigmem
	// -----------------------------------------------------------------------

	private async pushNote(
		note: ReturnType<typeof parseNote>,
		scope: string,
		source: string,
	): Promise<number> {
		const SKIP_FM_KEYS = new Set(["position", "cssclass", "publish"]);
		let count = 0;

		const assert = async (relation: string, value: ReturnType<typeof stringValue>) => {
			try {
				await this.client.assertFact({ entity: note.entityUri, relation, value, source, scope });
				count++;
			} catch (e) {
				console.warn(`[stigmem] assert failed ${note.entityUri}/${relation}: ${e}`);
			}
		};

		// Title
		await assert("note:title", stringValue(note.title));

		// Frontmatter
		for (const [key, val] of Object.entries(note.frontmatter)) {
			if (SKIP_FM_KEYS.has(key)) continue;
			const relation = `note:${key}`;
			if (Array.isArray(val)) {
				for (const item of val) await assert(relation, stringValue(String(item)));
			} else if (typeof val === "boolean") {
				await assert(relation, booleanValue(val) as ReturnType<typeof stringValue>);
			} else if (typeof val === "number") {
				await assert(relation, numberValue(val) as ReturnType<typeof stringValue>);
			} else if (val !== null && val !== undefined) {
				await assert(relation, stringValue(String(val)));
			}
		}

		// Wikilinks
		for (const target of note.wikilinks) {
			const targetUri = `obsidian://vault/${target}`;
			await assert(this.settings.wikilinkRelation, refValue(targetUri) as ReturnType<typeof stringValue>);
		}

		// Dataview inline fields
		for (const [key, val] of Object.entries(note.dataviewFields)) {
			await assert(`dataview:${key}`, stringValue(val));
		}

		// Content hash for rename tracking
		await assert("note:content_hash", stringValue(note.contentHash));

		return count;
	}

	// -----------------------------------------------------------------------
	// Pass 2: stigmem → vault
	// -----------------------------------------------------------------------

	private async pullEntity(
		file: TFile,
		entityUri: string,
		scope: string,
		vaultSource: string,
	): Promise<{ written: number; conflicts: number }> {
		// Fetch all facts for this entity that didn't originate from this vault file
		let allFacts: FactRecord[];
		try {
			const raw = await this.client.queryAll(entityUri, scope);
			allFacts = raw.filter(f => f.source !== vaultSource);
		} catch (e) {
			console.warn(`[stigmem] queryAll failed ${entityUri}: ${e}`);
			return { written: 0, conflicts: 0 };
		}

		if (allFacts.length === 0) return { written: 0, conflicts: 0 };

		const content = await this.vault.read(file);
		const existing = extractStigmemSection(content);
		const existingFacts = existing ? parseStigmemSectionBody(existing) : [];

		// Convert FactRecord[] to StigmemFact[]
		const incoming: StigmemFact[] = allFacts.map(f => ({
			relation: f.relation,
			value: String(f.value.v ?? ""),
			source: f.source,
		}));

		// Conflict detection
		const existingMap = new Map(existingFacts.map(f => [f.relation, f.value ?? ""]));
		const conflictMessages: string[] = [];
		let conflictCount = 0;
		const policy = this.settings.conflictPolicy;

		const filtered = incoming.filter(f => {
			const existingVal = existingMap.get(f.relation);
			if (existingVal === undefined || existingVal === f.value) return true;

			// Conflict
			conflictCount++;
			const msg = `relation=${f.relation} vault=${existingVal} stigmem=${f.value}`;
			if (policy === "vault_wins") {
				return false; // discard the incoming fact
			} else if (policy === "stigmem_wins") {
				return true; // overwrite vault
			} else {
				// comment policy: surface conflict, keep vault value
				conflictMessages.push(msg);
				return false;
			}
		});

		const newBody = buildStigmemSectionBody(filtered);
		let updated = replaceStigmemSection(content, newBody);

		for (const msg of conflictMessages) {
			updated = addConflictComment(updated, msg);
		}

		if (updated !== content) {
			await this.vault.modify(file, updated);
		}

		return { written: filtered.length, conflicts: conflictCount };
	}
}
