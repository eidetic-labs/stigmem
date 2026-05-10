import { getSession } from "@/lib/session";
import { redirect } from "next/navigation";
import { FirstFactForm } from "./first-fact-form";

export default async function OnboardingPage() {
  const session = await getSession();
  if (!session.apiKey) redirect("/login");

  return (
    <div className="mx-auto max-w-lg pt-16">
      <div className="mb-8 text-center">
        <div className="mb-2 text-4xl font-bold text-primary">stigmem</div>
        <h1 className="text-2xl font-semibold">Welcome!</h1>
        <p className="mt-2 text-muted-foreground">
          Your namespace <code className="rounded bg-muted px-1 font-mono text-sm">my-facts</code> is
          ready. Write your first fact to get started.
        </p>
      </div>
      <FirstFactForm entityUri={session.entityUri ?? ""} />
    </div>
  );
}
