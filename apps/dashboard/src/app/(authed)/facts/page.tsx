"use client";

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Plus, RefreshCw, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fmtDate, fmtConfidence, fmtValue, SCOPES } from "@/lib/utils";
import type { QueryResponse } from "@/lib/api";

interface Filters {
  entity: string;
  relation: string;
  scope: string;
  source: string;
  min_confidence: string;
  include_contradicted: boolean;
  cursor: string | null;
}

const DEFAULTS: Filters = {
  entity: "",
  relation: "",
  scope: "",
  source: "",
  min_confidence: "0",
  include_contradicted: false,
  cursor: null,
};

async function fetchFacts(f: Filters): Promise<QueryResponse> {
  const p = new URLSearchParams();
  if (f.entity) p.set("entity", f.entity);
  if (f.relation) p.set("relation", f.relation);
  if (f.scope) p.set("scope", f.scope);
  if (f.source) p.set("source", f.source);
  if (f.min_confidence && f.min_confidence !== "0") p.set("min_confidence", f.min_confidence);
  if (f.include_contradicted) p.set("include_contradicted", "true");
  if (f.cursor) p.set("cursor", f.cursor);
  p.set("limit", "50");

  const res = await fetch(`/api/stigmem/v1/facts?${p.toString()}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export default function FactsPage() {
  const [draft, setDraft] = useState<Filters>(DEFAULTS);
  const [applied, setApplied] = useState<Filters>(DEFAULTS);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["facts", applied],
    queryFn: () => fetchFacts(applied),
  });

  const apply = useCallback(() => setApplied({ ...draft, cursor: null }), [draft]);
  const reset = useCallback(() => {
    setDraft(DEFAULTS);
    setApplied(DEFAULTS);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Facts</h1>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw size={14} className="mr-1" />
            Refresh
          </Button>
          <Button size="sm" asChild>
            <Link href="/facts/new">
              <Plus size={14} className="mr-1" />
              Assert
            </Link>
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-lg border bg-card p-4 space-y-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="space-y-1">
            <Label htmlFor="f-entity">Entity</Label>
            <Input
              id="f-entity"
              placeholder="stigmem://…"
              value={draft.entity}
              onChange={(e) => setDraft((d) => ({ ...d, entity: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="f-relation">Relation</Label>
            <Input
              id="f-relation"
              placeholder="ns:relation"
              value={draft.relation}
              onChange={(e) => setDraft((d) => ({ ...d, relation: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="f-scope">Scope</Label>
            <Select
              value={draft.scope || "_all"}
              onValueChange={(v) => setDraft((d) => ({ ...d, scope: v === "_all" ? "" : v }))}
            >
              <SelectTrigger id="f-scope">
                <SelectValue placeholder="All scopes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_all">All scopes</SelectItem>
                {SCOPES.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="f-source">Source</Label>
            <Input
              id="f-source"
              placeholder="stigmem://…"
              value={draft.source}
              onChange={(e) => setDraft((d) => ({ ...d, source: e.target.value }))}
            />
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Label htmlFor="f-conf">Min confidence</Label>
            <Input
              id="f-conf"
              type="number"
              min={0}
              max={1}
              step={0.1}
              className="w-20"
              value={draft.min_confidence}
              onChange={(e) => setDraft((d) => ({ ...d, min_confidence: e.target.value }))}
            />
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input
              type="checkbox"
              checked={draft.include_contradicted}
              onChange={(e) => setDraft((d) => ({ ...d, include_contradicted: e.target.checked }))}
            />
            Include contradicted
          </label>
          <div className="flex gap-2 ml-auto">
            <Button variant="outline" size="sm" onClick={reset}>Reset</Button>
            <Button size="sm" onClick={apply}>Apply filters</Button>
          </div>
        </div>
      </div>

      {/* Results */}
      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      {isError && <p className="text-destructive">Failed to load facts.</p>}
      {data && (
        <>
          <p className="text-sm text-muted-foreground">
            Showing {data.facts.length} fact{data.facts.length !== 1 ? "s" : ""}
            {data.cursor ? " (more available)" : ""}
          </p>
          <div className="rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Entity</th>
                  <th className="px-4 py-3 text-left font-medium">Relation</th>
                  <th className="px-4 py-3 text-left font-medium">Value</th>
                  <th className="px-4 py-3 text-left font-medium">Scope</th>
                  <th className="px-4 py-3 text-left font-medium">Confidence</th>
                  <th className="px-4 py-3 text-left font-medium">Asserted</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.facts.map((f) => (
                  <tr
                    key={f.id}
                    className={
                      f.confidence === 0
                        ? "opacity-50 bg-muted/20"
                        : f.contradicted
                        ? "bg-yellow-50"
                        : "hover:bg-muted/30"
                    }
                  >
                    <td className="px-4 py-2 font-mono text-xs max-w-[180px] truncate" title={f.entity}>
                      {f.entity}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs max-w-[140px] truncate" title={f.relation}>
                      {f.relation}
                    </td>
                    <td className="px-4 py-2 max-w-[160px] truncate">
                      {fmtValue(f.value.type, f.value.v)}
                    </td>
                    <td className="px-4 py-2">
                      <Badge variant="gray">{f.scope}</Badge>
                    </td>
                    <td className="px-4 py-2">
                      {f.confidence === 0 ? (
                        <Badge variant="red">retracted</Badge>
                      ) : (
                        <span className={f.contradicted ? "text-yellow-700" : ""}>
                          {fmtConfidence(f.confidence)}
                          {f.contradicted && " ⚠"}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground text-xs">
                      {fmtDate(f.timestamp)}
                    </td>
                    <td className="px-4 py-2">
                      <Link
                        href={`/facts/${f.id}`}
                        className="inline-flex items-center text-primary hover:underline text-xs"
                      >
                        Detail <ChevronRight size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
                {data.facts.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                      No facts found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {data.cursor && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setApplied((a) => ({ ...a, cursor: data.cursor }))}
            >
              Load more
            </Button>
          )}
        </>
      )}
    </div>
  );
}
