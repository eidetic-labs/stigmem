"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, AlertTriangle, Trash2, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fmtDate, fmtConfidence, fmtValue } from "@/lib/utils";
import type { FactRecord, AuditLogEntry } from "@/lib/api";

async function fetchFact(id: string): Promise<FactRecord> {
  const res = await fetch(`/api/stigmem/v1/facts/${id}`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

async function fetchAudit(factId: string): Promise<AuditLogEntry[]> {
  const res = await fetch(`/api/stigmem/v1/audit/facts/${factId}`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

type MeResponse = { entityUri: string; permissions: string[] };

async function fetchMe(): Promise<MeResponse> {
  const res = await fetch("/api/auth/me");
  return res.json();
}

async function retractFact(
  fact: FactRecord,
  reason: string,
  entityUri: string
): Promise<void> {
  const body = {
    entity: fact.entity,
    relation: fact.relation,
    value: fact.value,
    source: entityUri,
    confidence: 0.0,
    scope: fact.scope,
  };
  const res = await fetch("/api/stigmem/v1/facts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Retraction failed");
  }

  if (reason.trim()) {
    const reasonBody = {
      entity: fact.id,
      relation: "stigmem:retract:reason",
      value: { type: "string", v: reason.trim() },
      source: entityUri,
      confidence: 1.0,
      scope: fact.scope,
    };
    await fetch("/api/stigmem/v1/facts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(reasonBody),
    });
  }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

export default function FactDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [retractOpen, setRetractOpen] = useState(false);
  const [retractReason, setRetractReason] = useState("");

  const { data: fact, isLoading, isError } = useQuery({
    queryKey: ["fact", id],
    queryFn: () => fetchFact(id),
  });

  const { data: audit } = useQuery({
    queryKey: ["audit", "fact", id],
    queryFn: () => fetchAudit(id),
    enabled: !!fact,
  });

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: fetchMe });
  const canWrite = me?.permissions?.includes("write");

  const retract = useMutation({
    mutationFn: () => retractFact(fact!, retractReason, me!.entityUri),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fact", id] });
      queryClient.invalidateQueries({ queryKey: ["facts"] });
      setRetractOpen(false);
      setRetractReason("");
    },
  });

  if (isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (isError || !fact) return <p className="text-destructive">Fact not found.</p>;

  const isRetracted = fact.confidence === 0;

  return (
    <div className="max-w-2xl space-y-6">
      <FactHeader isRetracted={isRetracted} fact={fact} />
      <FactDetailCard fact={fact} />

      {canWrite && !isRetracted && (
        <Button
          variant="destructive"
          size="sm"
          onClick={() => setRetractOpen(true)}
        >
          <Trash2 size={14} className="mr-1" />
          Retract fact
        </Button>
      )}

      <RetractDialog
        open={retractOpen}
        onOpenChange={setRetractOpen}
        fact={fact}
        reason={retractReason}
        setReason={setRetractReason}
        mutation={retract}
      />

      {audit && audit.length > 0 && <AuditTrailCard audit={audit} />}
    </div>
  );
}

function FactHeader({ isRetracted, fact }: { isRetracted: boolean; fact: FactRecord }) {
  return (
    <div className="flex items-center gap-3">
      <Button variant="ghost" size="sm" asChild>
        <Link href="/facts"><ArrowLeft size={14} /> Facts</Link>
      </Button>
      <h1 className="text-xl font-semibold">Fact detail</h1>
      {isRetracted && <Badge variant="red">retracted</Badge>}
      {fact.contradicted && !isRetracted && <Badge variant="yellow">contradicted</Badge>}
      {fact.attested_key_id && <Badge variant="green">attested</Badge>}
    </div>
  );
}

function FactDetailCard({ fact }: { fact: FactRecord }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-mono text-muted-foreground">{fact.id}</CardTitle>
          <Button
            variant="ghost"
            size="icon"
            title="Copy ID"
            onClick={() => navigator.clipboard.writeText(fact.id)}
          >
            <Copy size={14} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4">
          <Field label="Entity">
            <code className="font-mono text-xs break-all">{fact.entity}</code>
          </Field>
          <Field label="Relation">
            <code className="font-mono text-xs">{fact.relation}</code>
          </Field>
          <Field label="Value">
            <span>
              <Badge variant="gray" className="mr-1">{fact.value.type}</Badge>
              {fmtValue(fact.value.type, fact.value.v)}
            </span>
          </Field>
          <Field label="Source">
            <code className="font-mono text-xs break-all">{fact.source}</code>
          </Field>
          <Field label="Confidence">{fmtConfidence(fact.confidence)}</Field>
          <Field label="Scope"><Badge variant="gray">{fact.scope}</Badge></Field>
          <Field label="Asserted">{fmtDate(fact.timestamp)}</Field>
          {fact.valid_until && (
            <Field label="Valid until">{fmtDate(fact.valid_until)}</Field>
          )}
          {fact.received_from && (
            <Field label="Received from"><code className="font-mono text-xs">{fact.received_from}</code></Field>
          )}
          {fact.attested_key_id && (
            <Field label="Attested by"><code className="font-mono text-xs">{fact.attested_key_id}</code></Field>
          )}
        </dl>

        {fact.warnings.length > 0 && (
          <div className="mt-4 flex items-start gap-2 rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <ul className="list-disc ml-4 space-y-1">
              {fact.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface RetractDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  fact: FactRecord;
  reason: string;
  setReason: (s: string) => void;
  mutation: { isError: boolean; error: unknown; isPending: boolean; mutate: () => void };
}

function RetractDialog({
  open, onOpenChange, fact, reason, setReason, mutation,
}: RetractDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Retract fact?</DialogTitle>
          <DialogDescription>
            Sets confidence to 0.0 for entity <strong>{fact.entity}</strong> /
            relation <strong>{fact.relation}</strong> / scope <strong>{fact.scope}</strong>.
            This cannot be undone without re-asserting.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="retract-reason">Reason (optional)</Label>
          <Input
            id="retract-reason"
            placeholder="Why is this being retracted?"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
        {mutation.isError && (
          <p className="text-sm text-destructive">{String(mutation.error)}</p>
        )}
        <div className="flex justify-end gap-2 mt-2">
          <DialogClose asChild>
            <Button variant="outline" size="sm">Cancel</Button>
          </DialogClose>
          <Button
            variant="destructive"
            size="sm"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Retracting…" : "Confirm retract"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function AuditTrailCard({ audit }: { audit: AuditLogEntry[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Audit trail</CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full text-xs">
          <thead className="text-muted-foreground">
            <tr>
              <th className="text-left pb-2">Event</th>
              <th className="text-left pb-2">Principal</th>
              <th className="text-left pb-2">Attested key</th>
              <th className="text-left pb-2">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {audit.map((e) => (
              <tr key={e.id} className="align-top">
                <td className="py-1.5 pr-4"><Badge variant="gray">{e.event_type}</Badge></td>
                <td className="py-1.5 pr-4 font-mono max-w-[160px] truncate" title={e.entity_uri}>
                  {e.entity_uri}
                </td>
                <td className="py-1.5 pr-4 font-mono max-w-[140px] truncate" title={e.attested_key_id ?? ""}>
                  {e.attested_key_id ?? "—"}
                </td>
                <td className="py-1.5 text-muted-foreground">{fmtDate(e.ts)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
