"use client";

import { useState, type Dispatch, type SetStateAction } from "react";
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

const fetchGarden = async (slug: string): Promise<GardenRecord> => {
  const res = await fetch(`/api/stigmem/v1/gardens/${slug}`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
};

const fetchMembers = async (slug: string): Promise<GardenMemberRecord[]> => {
  const res = await fetch(`/api/stigmem/v1/gardens/${slug}/members`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
};

type MeResponse = { entityUri: string; permissions: string[] };

const fetchMe = async (): Promise<MeResponse> => {
  const res = await fetch("/api/auth/me");
  return res.json();
};

interface MemberRowProps {
  member: { entity_uri: string; role: string; added_at: string };
  isAdmin: boolean;
  isSelf: boolean;
  onChangeRole: (role: string) => void;
  onRemove: () => void;
}

function MemberRow({ member, isAdmin, isSelf, onChangeRole, onRemove }: MemberRowProps) {
  const canEditRole = isAdmin && !isSelf;
  return (
    <tr className="hover:bg-muted/30">
      <td className="px-4 py-2 font-mono text-xs break-all max-w-[220px] truncate" title={member.entity_uri}>
        {member.entity_uri}
        {isSelf && <span className="ml-1 text-muted-foreground">(you)</span>}
      </td>
      <td className="px-4 py-2">
        {canEditRole ? (
          <Select value={member.role} onValueChange={onChangeRole}>
            <SelectTrigger className="h-7 w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
            </SelectContent>
          </Select>
        ) : (
          <Badge variant={ROLE_BADGE[member.role] ?? "gray"}>{member.role}</Badge>
        )}
      </td>
      <td className="px-4 py-2 text-xs text-muted-foreground">{fmtDate(member.added_at)}</td>
      {isAdmin && (
        <td className="px-4 py-2">
          {!isSelf && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-destructive"
              title="Remove member"
              onClick={onRemove}
            >
              <Trash2 size={12} />
            </Button>
          )}
        </td>
      )}
    </tr>
  );
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
                <MemberRow
                  key={m.entity_uri}
                  member={m}
                  isAdmin={isAdmin}
                  isSelf={m.entity_uri === me?.entityUri}
                  onChangeRole={(role) => changeRole.mutate({ entity_uri: m.entity_uri, role })}
                  onRemove={() => removeMember.mutate(m.entity_uri)}
                />
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

      <InviteDialog
        open={inviteOpen}
        onOpenChange={setInviteOpen}
        gardenName={garden?.name ?? slug}
        form={inviteForm}
        setForm={setInviteForm}
        mutation={addMember}
      />
    </div>
  );
}

interface InviteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  gardenName: string;
  form: { entity_uri: string; role: string };
  setForm: Dispatch<SetStateAction<{ entity_uri: string; role: string }>>;
  mutation: { isError: boolean; error: unknown; isPending: boolean; mutate: () => void };
}

function InviteDialog({
  open, onOpenChange, gardenName, form, setForm, mutation,
}: InviteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add member</DialogTitle>
          <DialogDescription>
            Add an entity URI as a member of <strong>{gardenName}</strong>.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="invite-uri">Entity URI</Label>
            <Input
              id="invite-uri"
              placeholder="oidc:sub | stigmem://authority/agent/id"
              value={form.entity_uri}
              onChange={(e) => setForm((f) => ({ ...f, entity_uri: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <Label>Role</Label>
            <Select value={form.role} onValueChange={(v) => setForm((f) => ({ ...f, role: v }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        {mutation.isError && (
          <p className="text-sm text-destructive">{String(mutation.error)}</p>
        )}
        <div className="flex justify-end gap-2 mt-2">
          <DialogClose asChild>
            <Button variant="outline" size="sm">Cancel</Button>
          </DialogClose>
          <Button
            size="sm"
            disabled={!form.entity_uri || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Adding…" : "Add member"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
