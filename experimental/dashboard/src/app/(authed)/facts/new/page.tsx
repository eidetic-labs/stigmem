"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { SCOPES } from "@/lib/utils";

interface FormState {
  entity: string;
  relation: string;
  value_type: string;
  value_v: string;
  source: string;
  confidence: string;
  scope: string;
  valid_until: string;
}

const DEFAULTS: FormState = {
  entity: "",
  relation: "",
  value_type: "string",
  value_v: "",
  source: "",
  confidence: "1",
  scope: "local",
  valid_until: "",
};

const VALUE_TYPES = ["string", "text", "number", "boolean", "null"] as const;

interface ValueInputProps {
  valueType: string;
  value: string;
  onChange: (v: string) => void;
}

function ValueInput({ valueType, value, onChange }: ValueInputProps) {
  if (valueType === "boolean") {
    return (
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue placeholder="Select…" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="true">true</SelectItem>
          <SelectItem value="false">false</SelectItem>
        </SelectContent>
      </Select>
    );
  }
  if (valueType === "null") {
    return <Input id="value-v" disabled placeholder="null" />;
  }
  return (
    <Input
      id="value-v"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={valueType === "number" ? "0.0" : "value"}
    />
  );
}

async function assertFact(form: FormState) {
  let v: string | number | boolean | null;
  if (form.value_type === "null") v = null;
  else if (form.value_type === "boolean") v = form.value_v === "true";
  else if (form.value_type === "number") v = parseFloat(form.value_v);
  else v = form.value_v;

  const body = {
    entity: form.entity,
    relation: form.relation,
    value: { type: form.value_type, v },
    source: form.source,
    confidence: parseFloat(form.confidence),
    scope: form.scope,
    valid_until: form.valid_until || null,
  };

  const res = await fetch("/api/stigmem/v1/facts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Unknown error");
  }
  return res.json();
}

export default function AssertPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(DEFAULTS);
  const [successId, setSuccessId] = useState<string | null>(null);

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const r = await fetch("/api/auth/me");
      return r.json() as Promise<{ entityUri: string; permissions: string[] }>;
    },
  });

  const canWrite = me?.permissions?.includes("write");

  const mutation = useMutation({
    mutationFn: assertFact,
    onSuccess: (data) => {
      setSuccessId(data.id);
      setForm(DEFAULTS);
    },
  });

  const set = (k: keyof FormState, v: string) =>
    setForm((f) => ({ ...f, [k]: v }));

  const hasNamespaceWarning = form.relation && !form.relation.includes(":");

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-2xl font-semibold">Assert a Fact</h1>

      {!canWrite && me && (
        <div className="flex items-start gap-2 rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-800">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          Your account has read-only access. Assertions require write permission.
        </div>
      )}

      {successId && (
        <div className="flex items-center gap-2 rounded-md border border-green-300 bg-green-50 p-3 text-sm text-green-800">
          <CheckCircle2 size={16} />
          Fact asserted.{" "}
          <button
            className="underline"
            onClick={() => router.push(`/facts/${successId}`)}
          >
            View detail →
          </button>
        </div>
      )}

      {mutation.isError && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          {String(mutation.error)}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fact</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="entity">Entity URI</Label>
            <Input
              id="entity"
              placeholder="stigmem://authority/type/id"
              value={form.entity}
              onChange={(e) => set("entity", e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="relation">Relation</Label>
            <Input
              id="relation"
              placeholder="your-ns:relation-name"
              value={form.relation}
              onChange={(e) => set("relation", e.target.value)}
            />
            {hasNamespaceWarning && (
              <p className="text-xs text-yellow-700">
                ⚠ Relation has no namespace prefix — consider using <code>ns:relation</code> to
                avoid collisions (see relation-convention.md).
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Value type</Label>
              <Select value={form.value_type} onValueChange={(v) => set("value_type", v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {VALUE_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="value-v">Value</Label>
              <ValueInput
                valueType={form.value_type}
                value={form.value_v}
                onChange={(v) => set("value_v", v)}
              />
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="source">Source URI</Label>
            <Input
              id="source"
              placeholder="stigmem://authority/agent/id"
              value={form.source}
              onChange={(e) => set("source", e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="confidence">Confidence (0–1)</Label>
              <Input
                id="confidence"
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={form.confidence}
                onChange={(e) => set("confidence", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>Scope</Label>
              <Select value={form.scope} onValueChange={(v) => set("scope", v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SCOPES.map((s) => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="valid-until">Valid until (ISO 8601, optional)</Label>
            <Input
              id="valid-until"
              placeholder="2026-12-31T23:59:59Z"
              value={form.valid_until}
              onChange={(e) => set("valid_until", e.target.value)}
            />
          </div>

          <Button
            className="w-full"
            disabled={!canWrite || mutation.isPending || !form.entity || !form.relation || !form.source}
            onClick={() => mutation.mutate(form)}
          >
            {mutation.isPending ? "Asserting…" : "Assert fact"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
