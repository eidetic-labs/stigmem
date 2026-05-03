import { getSession } from "@/lib/session";
import { redirect } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LogIn, AlertCircle } from "lucide-react";

interface Props {
  searchParams: { error?: string; redirect?: string };
}

const ERROR_MESSAGES: Record<string, string> = {
  invalid_state: "Login session expired or tampered. Please try again.",
  token_exchange_failed: "Could not exchange authorization code for tokens.",
  stigmem_exchange_failed: "Could not obtain a stigmem API key from the identity provider.",
  access_denied: "Access was denied by the identity provider.",
};

export default async function LoginPage({ searchParams }: Props) {
  const session = await getSession();
  if (session.apiKey) redirect(searchParams.redirect ?? "/facts");

  const errorMsg = searchParams.error
    ? (ERROR_MESSAGES[searchParams.error] ?? `Login error: ${searchParams.error}`)
    : null;

  const oidcEnabled = !!process.env.OIDC_ISSUER_URL;

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mb-2 text-3xl font-bold text-primary">stigmem</div>
          <CardTitle className="text-base font-normal text-muted-foreground">
            Fact graph curator dashboard
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {errorMsg && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {oidcEnabled ? (
            <Button asChild className="w-full">
              <a href="/api/auth/login">
                <LogIn size={16} className="mr-2" />
                Sign in with your identity provider
              </a>
            </Button>
          ) : (
            <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
              OIDC is not configured on this node. Set{" "}
              <code className="font-mono text-xs">OIDC_ISSUER_URL</code>,{" "}
              <code className="font-mono text-xs">OIDC_CLIENT_ID</code>, and{" "}
              <code className="font-mono text-xs">OIDC_REDIRECT_URI</code> to enable login.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
