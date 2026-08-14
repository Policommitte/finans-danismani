"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../hooks/useAuth";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";

export default function LoginPage() {
  const router = useRouter();
  const auth = useAuth();
  const [email, setEmail] = useState("mehmet@example.com");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await auth.login(email, password);
      router.replace("/dashboard");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Giris yapilamadi.");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-md" title="Giris">
        <form className="space-y-4" onSubmit={submit}>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">E-posta</span>
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-blue-600"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Sifre</span>
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-blue-600"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
            />
          </label>
          {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          <Button className="w-full" disabled={auth.loading}>
            {auth.loading ? "Kontrol ediliyor" : "Giris yap"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
