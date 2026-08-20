"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../hooks/useAuth";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";

const allowedNextPaths = new Set(["/dashboard", "/portfolio", "/market", "/reports", "/profile", "/settings"]);

function getSafeNextPath() {
  if (typeof window === "undefined") {
    return "/dashboard";
  }

  const next = new URLSearchParams(window.location.search).get("next");
  return next && allowedNextPaths.has(next) ? next : "/dashboard";
}

export default function LoginPage() {
  const router = useRouter();
  const auth = useAuth();
  const [email, setEmail] = useState("mehmet@example.com");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.loading && auth.user) {
      router.replace(getSafeNextPath());
    }
  }, [auth.loading, auth.user, router]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await auth.login(email, password);
      router.replace(getSafeNextPath());
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Giris yapilamadi.");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center app-bg px-4">
      <Card className="w-full max-w-md" title="Giris">
        <form className="space-y-4" onSubmit={submit}>
          <label className="block text-sm">
            <span className="font-medium app-muted">E-posta</span>
            <input
              className="mt-1 w-full rounded-md border app-input px-3 py-2 outline-none"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium app-muted">Sifre</span>
            <input
              className="mt-1 w-full rounded-md border app-input px-3 py-2 outline-none"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
            />
          </label>
          {error && <div className="rounded-md app-danger-box p-3 text-sm">{error}</div>}
          <Button className="w-full" disabled={auth.loading}>
            {auth.loading ? "Kontrol ediliyor" : "Giris yap"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
