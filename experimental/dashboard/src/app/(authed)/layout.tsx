import { getSession } from "@/lib/session";
import { redirect } from "next/navigation";
import { Nav } from "@/components/nav";

export default async function AuthedLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session.apiKey) redirect("/login");

  return (
    <div className="flex min-h-screen">
      <Nav entityUri={session.entityUri} />
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}
