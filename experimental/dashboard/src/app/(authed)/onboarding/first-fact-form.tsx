"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowRight, CheckCircle2 } from "lucide-react";

interface Props {
  entityUri: string;
}

export function FirstFactForm({ entityUri }: Props) {
  const router = useRouter();
  const [form, setForm] = useState({
    entity: entityUri,
    relation: "knows",
    value: "stigmem",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch("/api/stigmem/v1/facts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          entity: form.entity,
          relation: form.relation,
          value: { type: "string", v: form.value },
          source: entityUri,
          scope: "private",
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? res.statusText);
      }

      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-10">
          <CheckCircle2 className="h-12 w-12 text-green-500" />
          <p className="text-lg font-medium">First fact written!</p>
          <p className="text-center text-sm text-muted-foreground">
            Your stigmem node is live. Head to your fact graph to explore or add more.
          </p>
          <Button onClick={() => router.push("/facts")} className="mt-2">
            Go to Facts <ArrowRight size={16} className="ml-1" />
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Write your first fact</CardTitle>
        <CardDescription>
          A fact is a triple: <em>entity → relation → value</em>. Edit the fields below or use the
          defaults to write your first one.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="entity">Entity</Label>
            <Input
              id="entity"
              value={form.entity}
              onChange={(e) => setForm({ ...form, entity: e.target.value })}
              placeholder="e.g. user:alice"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="relation">Relation</Label>
            <Input
              id="relation"
              value={form.relation}
              onChange={(e) => setForm({ ...form, relation: e.target.value })}
              placeholder="e.g. knows"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="value">Value</Label>
            <Input
              id="value"
              value={form.value}
              onChange={(e) => setForm({ ...form, value: e.target.value })}
              placeholder="e.g. stigmem"
              required
            />
          </div>

          {error && (
            <p className="rounded border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" disabled={submitting} className="mt-2">
            {submitting ? "Writing…" : "Write fact"}
            {!submitting && <ArrowRight size={16} className="ml-1" />}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
