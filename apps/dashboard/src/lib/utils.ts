import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function fmtConfidence(c: number): string {
  return `${Math.round(c * 100)}%`;
}

export function fmtValue(type: string, v: string | number | boolean | null): string {
  if (type === "null" || v === null) return "∅ null";
  if (type === "boolean") return v ? "true" : "false";
  return String(v);
}

export const SCOPES = ["local", "team", "public"] as const;
export type Scope = (typeof SCOPES)[number];

export const ROLES = ["reader", "writer", "admin"] as const;
export type Role = (typeof ROLES)[number];
