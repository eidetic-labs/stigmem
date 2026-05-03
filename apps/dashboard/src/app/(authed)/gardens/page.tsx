"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Plus, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fmtDate, SCOPES } from "@/lib/utils";
import type { GardenRecord } from "@/lib/api";

async function fetchGardens(): Promise<GardenRecord[]> {
  const res = await fetch("/api/stigmem/v1/gardens");
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

async function fetchMe(): Promise<{ entityUri: string; permissions: string[] }> {
  const res = await fetch("/api/auth/me");
  return res.json();
}

async function createGarden(body: { slug: string; name: string; scope: string; description: string }) {
  const res = await fetch("/api/stigmem/v1/gardens", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Create failed");
  }
  return res.json();
}

export default function GardensPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ slug: "", name: "", scope: "local", description: "" });

  const { data: gardens, isLoading, isError } = useQuery({
    queryKey: ["gardens"],
    queryFn: fetchGardens,
  });

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: fetchMe });
  const canWrite = me?.permissions?.includes("write");

  const create = useMutation({
    mutationFn: () => createGarden(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gardens"] });
      setOpen(false);
      setForm({ slug: "", name: "", scope: "local", description: "" });
    },
  });

  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Gardens</h1>
        {canWrite && (
          <Button size="sm" onClick={() => setOpen(true)}>
            <Plus size={14} className="mr-1" />
            New garden
          </Button>
        )}
      </div>

      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      {isError && <p className="text-destructive">Failed to load gardens.</p>}

      {gardens && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {gardens.map((g) => (
            <Card key={g.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-base">{g.name}</CardTitle>
                  <Badge variant="gray">{g.scope}</Badge>
                </div>
                <p className="font-mono text-xs text-muted-foreground">{g.slug}</p>
              </CardHeader>
              <CardContent className="space-y-3">
                {g.description && (
                  <p className="text-sm text-muted-foreground">{g.description}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Created {fmtDate(g.created_at)}
                </p>
                <Button variant="outline" size="sm" className="w-full" asChild>
                  <Link href={`/gardens/${g.slug}/members`}>
                    <Users size={14} className="mr-1" />
                    View roster
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
          {gardens.length === 0 && (
            <p className="col-span-full text-muted-foreground text-sm">
              No gardens yet. Create one to start organizing facts.
            </p>
          )}
        </div>
      )}

      {/* Create garden dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create garden</DialogTitle>
            <DialogDescription>
              Gardens group facts by team, scope, and access control.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="g-name">Name</Label>
              <Input id="g-name" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="My garden" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="g-slug">Slug</Label>
              <Input
                id="g-slug"
                value={form.slug}
                onChange={(e) => set("slug", e.target.value.toLowerCase())}
                placeholder="my-garden"
              />
              <p className="text-xs text-muted-foreground">Lowercase, hyphens allowed, max 63 chars.</p>
            </div>
            <div className="space-y-1">
              <Label>Scope</Label>
              <Select value={form.scope} onValueChange={(v) => set("scope", v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SCOPES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="g-desc">Description (optional)</Label>
              <Input id="g-desc" value={form.description} onChange={(e) => set("description", e.target.value)} />
            </div>
          </div>
          {create.isError && (
            <p className="text-sm text-destructive">{String(create.error)}</p>
          )}
          <div className="flex justify-end gap-2 mt-2">
            <DialogClose asChild>
              <Button variant="outline" size="sm">Cancel</Button>
            </DialogClose>
            <Button
              size="sm"
              disabled={!form.slug || !form.name || create.isPending}
              onClick={() => create.mutate()}
            >
              {create.isPending ? "Creating…" : "Create garden"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
