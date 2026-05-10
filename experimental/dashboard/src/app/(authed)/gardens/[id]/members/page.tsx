"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, UserPlus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fmtDate, ROLES } from "@/lib/utils";
import type { GardenMemberRecord, GardenRecord } from "@/lib/api";

const ROLE_BADGE: Record<string, "green" | "default" | "gray"> = {
  admin: "green",
  writer: "default",
  reader: "gray",
};

async function fetchGarden(slug: string): Promise<GardenRecord> {
  const res = await fetch(`/api/stigmem/v1/gardens/${slug}`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

async function fetchMembers(slug: string): Promise<GardenMemberRecord[]> {
  const res = await fetch(`/api/stigmem/v1/gardens/${slug}/members`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

async function fetchMe(): Promise<{ entityUri: string; permissions: string[] }> {
  const res = await fetch("/api/auth/me");
  return res.json();
}

export default function GardenMembersPage() {
  const { id: slug } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteForm, setInviteForm] = useState({ entity_uri: "", role: "reader" });

  const { data: garden } = useQuery({ queryKey: ["garden", slug], queryFn: () => fetchGarden(slug) });
  const { data: members, isLoading } = useQuery({
    queryKey: ["garden-members", slug],
    queryFn: () => fetchMembers(slug),
  });
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: fetchMe });

  const myRole = members?.find((m) => m.entity_uri === me?.entityUri)?.role;
  const isAdmin = myRole === "admin";

  const addMember = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/stigmem/v1/gardens/${slug}/members`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(inviteForm),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Invite failed");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["garden-members", slug] });
      setInviteOpen(false);
      setInviteForm({ entity_uri: "", role: "reader" });
    },
  });

  const changeRole = useMutation({
    mutationFn: async ({ entity_uri, role }: { entity_uri: string; role: string }) => {
      const res = await fetch(
        `/api/stigmem/v1/gardens/${slug}/members/${encodeURIComponent(entity_uri)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role }),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail);
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["garden-members", slug] }),
  });

  const removeMember = useMutation({
    mutationFn: async (entity_uri: string) => {
      const res = await fetch(
        `/api/stigmem/v1/gardens/${slug}/members/${encodeURIComponent(entity_uri)}`,
        { method: "DELETE" }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail);
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["garden-members", slug] }),
  });

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/gardens"><ArrowLeft size={14} /> Gardens</Link>
        </Button>
        <div>
          <h1 className="text-xl font-semibold">{garden?.name ?? slug}</h1>
          <p className="text-xs text-muted-foreground font-mono">{garden?.garden_id}</p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-base font-medium">Members</h2>
        {isAdmin && (
          <Button size="sm" onClick={() => setInviteOpen(true)}>
            <UserPlus size={14} className="mr-1" />
            Add member
          </Button>
        )}
      </div>

      {isLoading && <p className="text-muted-foreground">Loading…</p>}

      {members && (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Entity</th>
                <th className="px-4 py-3 text-left font-medium">Role</th>
                <th className="px-4 py-3 text-left font-medium">Added</th>
                {isAdmin && <th className="px-4 py-3" />}
              </tr>
            </thead>
            <tbody className="divide-y">
              {members.map((m) => (
                <tr key={m.entity_uri} className="hover:bg-muted/30">
                  <td className="px-4 py-2 font-mono text-xs break-all max-w-[220px] truncate" title={m.entity_uri}>
                    {m.entity_uri}
                    {m.entity_uri === me?.entityUri && (
                      <span className="ml-1 text-muted-foreground">(you)</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    {isAdmin && m.entity_uri !== me?.entityUri ? (
                      <Select
                        value={m.role}
                        onValueChange={(r) => changeRole.mutate({ entity_uri: m.entity_uri, role: r })}
                      >
                        <SelectTrigger className="h-7 w-28">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Badge variant={ROLE_BADGE[m.role] ?? "gray"}>{m.role}</Badge>
                    )}
                  </td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">{fmtDate(m.added_at)}</td>
                  {isAdmin && (
                    <td className="px-4 py-2">
                      {m.entity_uri !== me?.entityUri && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted-foreground hover:text-destructive"
                          title="Remove member"
                          onClick={() => removeMember.mutate(m.entity_uri)}
                        >
                          <Trash2 size={12} />
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
              {members.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 4 : 3} className="px-4 py-8 text-center text-muted-foreground">
                    No members.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Invite dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add member</DialogTitle>
            <DialogDescription>
              Add an entity URI as a member of <strong>{garden?.name ?? slug}</strong>.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="invite-uri">Entity URI</Label>
              <Input
                id="invite-uri"
                placeholder="oidc:sub | stigmem://authority/agent/id"
                value={inviteForm.entity_uri}
                onChange={(e) => setInviteForm((f) => ({ ...f, entity_uri: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <Label>Role</Label>
              <Select value={inviteForm.role} onValueChange={(v) => setInviteForm((f) => ({ ...f, role: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          {addMember.isError && (
            <p className="text-sm text-destructive">{String(addMember.error)}</p>
          )}
          <div className="flex justify-end gap-2 mt-2">
            <DialogClose asChild>
              <Button variant="outline" size="sm">Cancel</Button>
            </DialogClose>
            <Button
              size="sm"
              disabled={!inviteForm.entity_uri || addMember.isPending}
              onClick={() => addMember.mutate()}
            >
              {addMember.isPending ? "Adding…" : "Add member"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
