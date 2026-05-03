"use client";

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { fmtDate } from "@/lib/utils";
import type { AuditLogResponse } from "@/lib/api";

interface Filters {
  entity_uri: string;
  source: string;
  fact_id: string;
  cursor: string | null;
}

const DEFAULTS: Filters = {
  entity_uri: "",
  source: "",
  fact_id: "",
  cursor: null,
};

async function fetchAudit(f: Filters): Promise<AuditLogResponse> {
  const p = new URLSearchParams();
  if (f.entity_uri) p.set("entity_uri", f.entity_uri);
  if (f.source) p.set("source", f.source);
  if (f.fact_id) p.set("fact_id", f.fact_id);
  if (f.cursor) p.set("cursor", f.cursor);
  p.set("limit", "50");
  const res = await fetch(`/api/stigmem/v1/audit?${p.toString()}`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

async function fetchMe(): Promise<{ entityUri: string; permissions: string[] }> {
  const res = await fetch("/api/auth/me");
  return res.json();
}

export default function AuditPage() {
  const [draft, setDraft] = useState<Filters>(DEFAULTS);
  const [applied, setApplied] = useState<Filters>(DEFAULTS);

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: fetchMe });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["audit", applied],
    queryFn: () => fetchAudit(applied),
  });

  const apply = useCallback(() => setApplied({ ...draft, cursor: null }), [draft]);
  const reset = useCallback(() => {
    setDraft(DEFAULTS);
    setApplied(DEFAULTS);
  }, []);

  const myAssertions = useCallback(() => {
    if (!me?.entityUri) return;
    const f = { ...DEFAULTS, entity_uri: me.entityUri };
    setDraft(f);
    setApplied(f);
  }, [me]);

  const exportUrl = (() => {
    const p = new URLSearchParams();
    if (applied.entity_uri) p.set("entity_uri", applied.entity_uri);
    if (applied.source) p.set("source", applied.source);
    if (applied.fact_id) p.set("fact_id", applied.fact_id);
    return `/api/stigmem/v1/audit/export?${p.toString()}`;
  })();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Audit Log</h1>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw size={14} className="mr-1" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href={exportUrl} download="stigmem-audit.csv">
              <Download size={14} className="mr-1" />
              Export CSV
            </a>
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-lg border bg-card p-4 space-y-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="space-y-1">
            <Label htmlFor="a-entity">Principal (entity URI)</Label>
            <Input
              id="a-entity"
              placeholder="oidc:sub or stigmem://…"
              value={draft.entity_uri}
              onChange={(e) => setDraft((d) => ({ ...d, entity_uri: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="a-source">Source</Label>
            <Input
              id="a-source"
              placeholder="stigmem://…"
              value={draft.source}
              onChange={(e) => setDraft((d) => ({ ...d, source: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="a-factid">Fact ID</Label>
            <Input
              id="a-factid"
              placeholder="uuid"
              value={draft.fact_id}
              onChange={(e) => setDraft((d) => ({ ...d, fact_id: e.target.value }))}
            />
          </div>
        </div>
        <div className="flex gap-2">
          {me?.entityUri && (
            <Button variant="secondary" size="sm" onClick={myAssertions}>
              My assertions
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={reset}>Reset</Button>
          <Button size="sm" onClick={apply}>Apply filters</Button>
        </div>
      </div>

      {/* Results */}
      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      {isError && <p className="text-destructive">Failed to load audit log.</p>}
      {data && (
        <>
          <p className="text-sm text-muted-foreground">
            Showing {data.entries.length} entr{data.entries.length !== 1 ? "ies" : "y"}
            {data.cursor ? " (more available)" : ""}
          </p>
          <div className="rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Event</th>
                  <th className="px-4 py-3 text-left font-medium">Principal</th>
                  <th className="px-4 py-3 text-left font-medium">Fact</th>
                  <th className="px-4 py-3 text-left font-medium">Source</th>
                  <th className="px-4 py-3 text-left font-medium">Attested key</th>
                  <th className="px-4 py-3 text-left font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.entries.map((e) => (
                  <tr key={e.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2">
                      <Badge variant={e.event_type === "assert" ? "default" : "gray"}>
                        {e.event_type}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs max-w-[160px] truncate" title={e.entity_uri}>
                      {e.entity_uri}
                    </td>
                    <td className="px-4 py-2">
                      {e.fact_id ? (
                        <a
                          href={`/facts/${e.fact_id}`}
                          className="font-mono text-xs text-primary hover:underline"
                        >
                          {e.fact_id.slice(0, 8)}…
                        </a>
                      ) : "—"}
                      {e.fact_entity && (
                        <p className="text-xs text-muted-foreground truncate max-w-[120px]" title={e.fact_entity}>
                          {e.fact_entity}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs max-w-[140px] truncate" title={e.source}>
                      {e.source}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs max-w-[120px] truncate" title={e.attested_key_id ?? ""}>
                      {e.attested_key_id ? (
                        <span className="text-green-700">{e.attested_key_id.slice(0, 8)}…</span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-2 text-xs text-muted-foreground">{fmtDate(e.ts)}</td>
                  </tr>
                ))}
                {data.entries.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                      No audit entries found.
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
