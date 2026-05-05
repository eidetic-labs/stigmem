/**
 * Sidebar pane showing graph neighbors of the active note from stigmem recall API.
 *
 * Opens via command palette "Open Stigmem recall sidebar" or the ribbon icon.
 * Auto-refreshes when the active leaf changes to a different markdown file.
 */

import { ItemView, MarkdownView, WorkspaceLeaf } from "obsidian";
import type StigmemPlugin from "./main";
import { StigmemClient, type ScoredFact } from "./StigmemClient";

export const VIEW_TYPE_RECALL = "stigmem-recall";

export class RecallView extends ItemView {
	private plugin: StigmemPlugin;
	private currentEntityUri: string | null = null;
	private loadingEl: HTMLElement | null = null;
	private resultsEl: HTMLElement | null = null;

	constructor(leaf: WorkspaceLeaf, plugin: StigmemPlugin) {
		super(leaf);
		this.plugin = plugin;
	}

	getViewType(): string {
		return VIEW_TYPE_RECALL;
	}

	getDisplayText(): string {
		return "Stigmem recall";
	}

	getIcon(): string {
		return "brain-circuit";
	}

	async onOpen(): Promise<void> {
		const container = this.containerEl.children[1] as HTMLElement;
		container.empty();

		container.createEl("div", {
			cls: "stigmem-recall-header",
			text: "Stigmem",
		}).style.cssText = "font-weight:600;font-size:1.1em;padding:8px 12px 4px;border-bottom:1px solid var(--background-modifier-border)";

		this.loadingEl = container.createEl("div", {
			cls: "stigmem-loading",
			text: "Switch to a note to load recall results.",
		});
		this.loadingEl.style.cssText = "padding:12px;color:var(--text-muted);font-size:0.9em";

		this.resultsEl = container.createEl("div", { cls: "stigmem-results" });

		// Trigger initial load for whatever is currently active
		this.refresh();
	}

	async onClose(): Promise<void> {
		// Nothing to clean up
	}

	/** Called by the plugin when the active leaf changes or a sync completes. */
	async refresh(): Promise<void> {
		const mdView = this.app.workspace.getActiveViewOfType(MarkdownView);
		if (!mdView?.file) {
			this.showPlaceholder("Switch to a note to load recall results.");
			return;
		}

		const relPath = mdView.file.path;
		const stem = relPath.replace(/\.md$/, "");
		const entityUri = `obsidian://vault/${stem}`;

		// Use the note title as the recall query; entity URI is the scope seed
		const query = mdView.file.basename;
		await this.loadRecall(query, entityUri);
	}

	private showPlaceholder(text: string): void {
		if (this.loadingEl) {
			this.loadingEl.textContent = text;
			this.loadingEl.style.display = "";
		}
		if (this.resultsEl) this.resultsEl.empty();
	}

	private async loadRecall(query: string, entityUri: string): Promise<void> {
		if (this.loadingEl) {
			this.loadingEl.textContent = "Loading…";
			this.loadingEl.style.display = "";
		}
		if (this.resultsEl) this.resultsEl.empty();

		const { nodeUrl, apiKey, scope } = this.plugin.settings;
		if (!nodeUrl) {
			this.showPlaceholder("Configure the stigmem node URL in settings.");
			return;
		}

		try {
			const client = new StigmemClient(nodeUrl, apiKey || null);
			const resp = await client.recall({
				query,
				scope,
				token_budget: 2000,
				depth: 2,
				include_neighbors: true,
				limit: 50,
			});

			if (this.loadingEl) this.loadingEl.style.display = "none";
			this.renderResults(resp.facts, query, resp.truncated);
		} catch (e) {
			this.showPlaceholder(`Recall failed: ${e}`);
		}
	}

	private renderResults(facts: ScoredFact[], query: string, truncated: boolean): void {
		if (!this.resultsEl) return;
		this.resultsEl.empty();

		if (facts.length === 0) {
			const empty = this.resultsEl.createEl("div", {
				text: "No related memories found.",
			});
			empty.style.cssText = "padding:12px;color:var(--text-muted);font-size:0.9em";
			return;
		}

		// Group by entity
		const byEntity = new Map<string, ScoredFact[]>();
		for (const sf of facts) {
			const key = sf.fact.entity;
			if (!byEntity.has(key)) byEntity.set(key, []);
			byEntity.get(key)!.push(sf);
		}

		const queryLabel = this.resultsEl.createEl("div");
		queryLabel.style.cssText = "padding:6px 12px;font-size:0.8em;color:var(--text-muted)";
		queryLabel.textContent = `Query: "${query}" · ${facts.length} facts${truncated ? " (truncated)" : ""}`;

		for (const [entity, entityFacts] of byEntity) {
			const section = this.resultsEl.createEl("div", { cls: "stigmem-entity-section" });
			section.style.cssText = "margin:8px 0;border-left:2px solid var(--interactive-accent);padding-left:8px;margin-left:8px";

			// Entity header
			const entityLabel = section.createEl("div", { cls: "stigmem-entity-label" });
			entityLabel.style.cssText = "font-size:0.8em;font-weight:600;color:var(--text-accent);padding:4px 4px 2px;word-break:break-all";
			entityLabel.textContent = this.formatEntityUri(entity);

			// Facts list
			const factList = section.createEl("ul");
			factList.style.cssText = "margin:0;padding-left:16px;list-style:disc";

			// Show top-5 per entity to keep the sidebar scannable
			const topFacts = entityFacts.slice(0, 5);
			for (const sf of topFacts) {
				const li = factList.createEl("li");
				li.style.cssText = "font-size:0.85em;padding:2px 0";
				const rel = sf.fact.relation;
				const val = sf.fact.value.v;
				const score = (sf.score * 100).toFixed(0);
				li.createEl("span", { text: `${rel}: ` }).style.cssText = "color:var(--text-muted)";
				li.createEl("span", { text: String(val ?? "") });
				li.createEl("span", { text: ` [${score}%]` }).style.cssText =
					"color:var(--text-faint);font-size:0.8em";
			}

			if (entityFacts.length > 5) {
				const more = section.createEl("div", { text: `+${entityFacts.length - 5} more…` });
				more.style.cssText = "font-size:0.8em;color:var(--text-muted);padding:2px 4px";
			}
		}
	}

	private formatEntityUri(uri: string): string {
		// obsidian://vault/path/to/Note → path/to/Note
		return uri.replace(/^obsidian:\/\/vault\//, "").replace(/^.*:\/\//, "");
	}
}
