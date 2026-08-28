"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../hooks/useAuth";
import { getMe } from "../../services/authService";

export default function DanismanGirisPage() {
  const router = useRouter();
  const auth = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await auth.login(email, password);
      const me = await getMe();
      if (me.role !== "advisor") {
        await auth.logout();
        setError("Bu hesap danışman yetkisine sahip değil.");
        return;
      }
      router.replace("/danisman");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Giriş yapılamadı.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      data-theme="dark"
      className="flex min-h-screen items-center justify-center bg-[#0b1220] px-4 py-12"
    >
      <div className="w-full max-w-sm rounded-2xl bg-[var(--color-surface-elevated)] p-7 shadow-2xl">
        <h1 className="text-xl font-bold text-[var(--color-heading)]">Danışman Girişi</h1>
        <p className="mt-1 text-sm text-[var(--color-muted)]">
          Bu ekran yalnızca danışman hesapları içindir.
        </p>

        <form className="mt-6 space-y-4" onSubmit={submit}>
          <label className="block text-sm">
            <span className="font-medium text-[var(--color-text)]">E-mail</span>
            <input
              className="mt-1.5 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-input-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text)] outline-none transition placeholder:text-[var(--color-muted)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary-soft)]"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              autoComplete="username"
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium text-[var(--color-text)]">Şifre</span>
            <input
              className="mt-1.5 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-input-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text)] outline-none transition placeholder:text-[var(--color-muted)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary-soft)]"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              autoComplete="current-password"
            />
          </label>

          {error && (
            <div className="rounded-lg border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] p-3 text-sm text-[var(--color-danger-text)]">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Kontrol ediliyor…" : "Danışman girişi yap"}
          </button>
        </form>
      </div>
    </main>
  );
}