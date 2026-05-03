"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Database,
  Plus,
  BookOpen,
  Users,
  ClipboardList,
  LogOut,
} from "lucide-react";

const links = [
  { href: "/facts", label: "Facts", icon: Database },
  { href: "/facts/new", label: "Assert", icon: Plus },
  { href: "/gardens", label: "Gardens", icon: BookOpen },
  { href: "/audit", label: "Audit Log", icon: ClipboardList },
];

export function Nav({ entityUri }: { entityUri?: string }) {
  const pathname = usePathname();
  return (
    <nav className="flex h-screen w-56 flex-col border-r bg-white px-4 py-6 shrink-0">
      <div className="mb-6">
        <span className="text-lg font-semibold tracking-tight text-primary">
          stigmem
        </span>
        {entityUri && (
          <p className="mt-1 truncate text-xs text-muted-foreground" title={entityUri}>
            {entityUri}
          </p>
        )}
      </div>

      <ul className="flex flex-col gap-1 flex-1">
        {links.map(({ href, label, icon: Icon }) => (
          <li key={href}>
            <Link
              href={href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                pathname === href || pathname.startsWith(href + "/")
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon size={16} />
              {label}
            </Link>
          </li>
        ))}
      </ul>

      <a
        href="/api/auth/logout"
        className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-destructive transition-colors"
      >
        <LogOut size={16} />
        Sign out
      </a>
    </nav>
  );
}
