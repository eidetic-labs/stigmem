/**
 * Stigmem Obsidian Plugin — main entry point.
 *
 * Registers:
 *   - Command: "Recall related memories" — runs recall for the active note
 *   - Command: "Sync vault now" — full bidirectional sync
 *   - Command: "Open stigmem garden" — opens the node's garden URL in the browser
 *   - Sidebar: RecallView (VIEW_TYPE_RECALL) — graph neighbors of the active note
 *   - Settings tab: StigmemSettingTab
 *   - File watcher: debounced sync on file-modify when autoSync is enabled
 */

import { MarkdownView, Notice, Plugin, TFile } from "obsidian";
import { DEFAULT_SETTINGS, PluginSettings, StigmemSettingTab } from "./settings";
import { VaultSyncer } from "./syncer";
import { RecallView, VIEW_TYPE_RECALL } from "./RecallView";

export default class StigmemPlugin extends Plugin {
	settings: PluginSettings = DEFAULT_SETTINGS;
	private syncer!: VaultSyncer;
	private debounceTimers = new Map<string, ReturnType<typeof setTimeout>>();

	async onload(): Promise<void> {
		await this.loadSettings();
		this.syncer = new VaultSyncer(this.app.vault, this.settings);

		// --- Register sidebar view ---
		this.registerView(VIEW_TYPE_RECALL, (leaf) => new RecallView(leaf, this));

		// --- Ribbon icon ---
		this.addRibbonIcon("brain-circuit", "Open Stigmem recall", () => {
			this.activateRecallView();
		});

		// --- Commands ---
		this.addCommand({
			id: "stigmem-recall",
			name: "Recall related memories",
			checkCallback: (checking) => {
				const view = this.app.workspace.getActiveViewOfType(MarkdownView);
				if (!view?.file) return false;
				if (checking) return true;
				this.activateRecallView();
				return true;
			},
		});

		this.addCommand({
			id: "stigmem-sync-vault",
			name: "Sync vault now",
			callback: async () => {
				new Notice("Stigmem: syncing vault…");
				try {
					const result = await this.syncer.syncAll();
					const msg =
						`Stigmem: sync done — ` +
						`↑${result.vaultToStigmem} facts pushed, ` +
						`↓${result.stigmemToVault} facts pulled` +
						(result.conflicts > 0 ? `, ${result.conflicts} conflicts` : "") +
						(result.errors.length > 0 ? ` (${result.errors.length} errors)` : "");
					new Notice(msg, 6000);
					if (result.errors.length > 0) {
						console.warn("[stigmem] sync errors:", result.errors);
					}
					this.refreshRecallView();
				} catch (e) {
					new Notice(`Stigmem sync failed: ${e}`);
					console.error("[stigmem] sync error:", e);
				}
			},
		});

		this.addCommand({
			id: "stigmem-open-garden",
			name: "Open stigmem garden",
			callback: () => {
				const url = this.settings.nodeUrl.replace(/\/$/, "") + "/garden";
				window.open(url, "_blank");
			},
		});

		// --- Settings tab ---
		this.addSettingTab(new StigmemSettingTab(this.app, this));

		// --- File watcher for auto-sync ---
		this.registerEvent(
			this.app.vault.on("modify", (file) => {
				if (!this.settings.autoSync) return;
				if (!(file instanceof TFile)) return;
				if (!file.path.endsWith(".md")) return;
				this.debouncedSyncNote(file);
			})
		);

		// --- Active-leaf change → refresh recall sidebar ---
		this.registerEvent(
			this.app.workspace.on("active-leaf-change", () => {
				this.refreshRecallView();
			})
		);

		console.log("[stigmem] plugin loaded — node:", this.settings.nodeUrl);
	}

	onunload(): void {
		for (const timer of this.debounceTimers.values()) clearTimeout(timer);
		this.debounceTimers.clear();
		console.log("[stigmem] plugin unloaded");
	}

	// -----------------------------------------------------------------------
	// Settings persistence
	// -----------------------------------------------------------------------

	async loadSettings(): Promise<void> {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings(): Promise<void> {
		await this.saveData(this.settings);
		this.syncer.updateClient();
	}

	// -----------------------------------------------------------------------
	// Debounced note sync
	// -----------------------------------------------------------------------

	private debouncedSyncNote(file: TFile): void {
		const key = file.path;
		const existing = this.debounceTimers.get(key);
		if (existing) clearTimeout(existing);

		const timer = setTimeout(async () => {
			this.debounceTimers.delete(key);
			try {
				const result = await this.syncer.syncNote(file);
				if (result.errors.length > 0) {
					console.warn(`[stigmem] sync errors for ${file.path}:`, result.errors);
				}
				this.refreshRecallView();
			} catch (e) {
				console.error(`[stigmem] sync failed for ${file.path}:`, e);
			}
		}, this.settings.syncDebounceMs);

		this.debounceTimers.set(key, timer);
	}

	// -----------------------------------------------------------------------
	// Recall sidebar helpers
	// -----------------------------------------------------------------------

	async activateRecallView(): Promise<void> {
		const { workspace } = this.app;
		let leaf = workspace.getLeavesOfType(VIEW_TYPE_RECALL)[0];
		if (!leaf) {
			leaf = workspace.getRightLeaf(false) ?? workspace.getLeaf(true);
			await leaf.setViewState({ type: VIEW_TYPE_RECALL, active: true });
		}
		workspace.revealLeaf(leaf);
		this.refreshRecallView();
	}

	private refreshRecallView(): void {
		const leaves = this.app.workspace.getLeavesOfType(VIEW_TYPE_RECALL);
		for (const leaf of leaves) {
			const view = leaf.view;
			if (view instanceof RecallView) {
				view.refresh();
			}
		}
	}
}
