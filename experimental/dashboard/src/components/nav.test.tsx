import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

const usePathname = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => usePathname(),
}));

import { Nav } from "./nav";

describe("Nav", () => {
  beforeEach(() => {
    usePathname.mockReset();
  });

  it("renders the signed-in entity and highlights the active route", () => {
    usePathname.mockReturnValue("/facts/new");

    render(<Nav entityUri="oidc:user:alice" />);

    expect(screen.getByText("oidc:user:alice")).toBeInTheDocument();
    const assertLink = screen.getByRole("link", { name: /assert/i });
    expect(assertLink).toHaveClass("bg-primary/10");
    expect(screen.getByRole("link", { name: /sign out/i })).toHaveAttribute("href", "/api/auth/logout");
  });

  it("does not render the entity line when no identity is provided", () => {
    usePathname.mockReturnValue("/facts");

    render(<Nav />);

    expect(screen.queryByTitle(/oidc:/i)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /facts/i })).toHaveClass("bg-primary/10");
  });
});
