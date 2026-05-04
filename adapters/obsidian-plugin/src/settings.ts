import { App, Notice, PluginSettingTab, Setting } from "obsidian";
import type StigmemPlugin from "./main";
import { StigmemClient } from "./StigmemClient";

// ---------------------------------------------------------------------------
// Settings interface
// ---------------------------------------------------------------------------

export interface FolderScope {
	folder: string;
	scope: StigmemScope;
}

export type StigmemScope = "local" | "team" | "company" | "public";
export type ConflictPolicy = "comment" | "stigmem_wins" | "vault_wins";

export interface PluginSettings {
	/** URL of the stigmem node, e.g. http://localhost:8765 */
	nodeUrl: string;
	/** API key for auth-enabled nodes. Stored in plugin data (not synced across vaults). */
	apiKey: string;
	/** Default scope for asserted facts */
	scope: StigmemScope;
	/** Vault-relative folder where stigmem-only entities are materialised as notes */
	syncFolder: string;
	/** Glob patterns (vault-relative) to skip during sync */
	ignoredPaths: string[];
	/** Conflict resolution policy */
	conflictPolicy: ConflictPolicy;
	/** Relation used for [[wikilinks]] */
	wikilinkRelation: string;
	/** Per-folder scope overrides */
	folderScopes: FolderScope[];
	/** Debounce delay in ms after file modification before triggering sync */
	syncDebounceMs: number;
	/** Whether to auto-sync on file save */
	autoSync: boolean;
}

export const DEFAULT_SETTINGS: PluginSettings = {
	nodeUrl: "http://localhost:8765",
	apiKey: "",
	scope: "local",
	syncFolder: "Stigmem",
	ignoredPaths: [".obsidian/**", "templates/**", "*.tmp"],
	conflictPolicy: "comment",
	wikilinkRelation: "references",
	folderScopes: [],
	syncDebounceMs: 1500,
	autoSync: true,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function scopeForPath(relPath: string, settings: PluginSettings): StigmemScope {
	for (const fs of settings.folderScopes) {
		if (relPath.startsWith(fs.folder)) return fs.scope;
	}
	return settings.scope;
}

export function isIgnored(relPath: string, settings: PluginSettings): boolean {
	for (const pat of settings.ignoredPaths) {
		if (matchGlob(relPath, pat)) return true;
	}
	return false;
}

function matchGlob(path: string, pattern: string): boolean {
	const re = new RegExp(
		"^" +
		pattern
			.replace(/[.+^${}()|[\]\\]/g, "\\$&")
			.replace(/\*\*/g, "§DSTAR§")
			.replace(/\*/g, "[^/]*")
			.replace(/§DSTAR§/g, ".*") +
		"$"
	);
	return re.test(path);
}

// ---------------------------------------------------------------------------
// Settings tab
// ---------------------------------------------------------------------------

export class StigmemSettingTab extends PluginSettingTab {
	constructor(app: App, private plugin: StigmemPlugin) {
		super(app, plugin);
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();
		containerEl.createEl("h2", { text: "Stigmem settings" });

		// --- Connection ---
		containerEl.createEl("h3", { text: "Connection" });

		new Setting(containerEl)
			.setName("Node URL")
			.setDesc("URL of your stigmem node, e.g. http://localhost:8765")
			.addText(text =>
				text
					.setPlaceholder("http://localhost:8765")
					.setValue(this.plugin.settings.nodeUrl)
					.onChange(async v => {
						this.plugin.settings.nodeUrl = v.trim();
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("API key")
			.setDesc(
				"API key for auth-enabled nodes. Stored locally in .obsidian/plugins/stigmem/data.json — " +
				"exclude .obsidian/ from sync to keep it private."
			)
			.addText(text => {
				text
					.setPlaceholder("sk-...")
					.setValue(this.plugin.settings.apiKey)
					.onChange(async v => {
						this.plugin.settings.apiKey = v.trim();
						await this.plugin.saveSettings();
					});
				text.inputEl.type = "password";
			});

		new Setting(containerEl)
			.setName("Test connection")
			.setDesc("Ping the configured node to confirm connectivity.")
			.addButton(btn =>
				btn.setButtonText("Test").onClick(async () => {
					const client = new StigmemClient(
						this.plugin.settings.nodeUrl,
						this.plugin.settings.apiKey || null,
					);
					const ok = await client.ping();
					new Notice(ok ? "✓ Connected to stigmem node." : "✗ Could not reach stigmem node.");
				})
			);

		// --- Sync ---
		containerEl.createEl("h3", { text: "Sync" });

		new Setting(containerEl)
			.setName("Default scope")
			.setDesc("Scope for asserted facts when no per-folder override matches.")
			.addDropdown(dd =>
				dd
					.addOptions({ local: "local", team: "team", company: "company", public: "public" })
					.setValue(this.plugin.settings.scope)
					.onChange(async v => {
						this.plugin.settings.scope = v as StigmemScope;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("Sync folder")
			.setDesc(
				"Vault-relative folder where stigmem-only entities are created as new notes. Default: Stigmem"
			)
			.addText(text =>
				text
					.setPlaceholder("Stigmem")
					.setValue(this.plugin.settings.syncFolder)
					.onChange(async v => {
						this.plugin.settings.syncFolder = v.trim() || "Stigmem";
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("Auto-sync on save")
			.setDesc("Automatically sync a note to stigmem when you save it.")
			.addToggle(t =>
				t.setValue(this.plugin.settings.autoSync).onChange(async v => {
					this.plugin.settings.autoSync = v;
					await this.plugin.saveSettings();
				})
			);

		new Setting(containerEl)
			.setName("Sync debounce (ms)")
			.setDesc("Wait this many ms after the last file-change event before syncing.")
			.addText(text =>
				text
					.setPlaceholder("1500")
					.setValue(String(this.plugin.settings.syncDebounceMs))
					.onChange(async v => {
						const n = parseInt(v, 10);
						if (!isNaN(n) && n >= 0) {
							this.plugin.settings.syncDebounceMs = n;
							await this.plugin.saveSettings();
						}
					})
			);

		new Setting(containerEl)
			.setName("Ignored paths")
			.setDesc(
				"Glob patterns (vault-relative, one per line) to skip. E.g. .obsidian/**, templates/**"
			)
			.addTextArea(ta =>
				ta
					.setPlaceholder(".obsidian/**\ntemplates/**")
					.setValue(this.plugin.settings.ignoredPaths.join("\n"))
					.onChange(async v => {
						this.plugin.settings.ignoredPaths = v
							.split("\n")
							.map(s => s.trim())
							.filter(Boolean);
						await this.plugin.saveSettings();
					})
			);

		// --- Conflict ---
		containerEl.createEl("h3", { text: "Conflict policy" });

		new Setting(containerEl)
			.setName("Conflict policy")
			.setDesc(
				"What to do when the same fact has different values in the vault and in stigmem."
			)
			.addDropdown(dd =>
				dd
					.addOptions({
						comment: "comment — annotate note (default)",
						stigmem_wins: "stigmem_wins — overwrite vault",
						vault_wins: "vault_wins — ignore stigmem value",
					})
					.setValue(this.plugin.settings.conflictPolicy)
					.onChange(async v => {
						this.plugin.settings.conflictPolicy = v as ConflictPolicy;
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("Wikilink relation")
			.setDesc("Stigmem relation name used for [[wikilink]] edges. Default: references")
			.addText(text =>
				text
					.setPlaceholder("references")
					.setValue(this.plugin.settings.wikilinkRelation)
					.onChange(async v => {
						this.plugin.settings.wikilinkRelation = v.trim() || "references";
						await this.plugin.saveSettings();
					})
			);
	}
}
