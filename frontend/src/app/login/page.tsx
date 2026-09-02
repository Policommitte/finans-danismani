"use client";
import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { requestPageTransition } from "../../components/layout/transitionEvents";
import { useAuth } from "../../hooks/useAuth";

const allowedNextPaths = new Set([
  "/dashboard",
  "/market",
  "/risk",
  "/reports",
  "/bulten",
  "/islemler",
  "/yatirim-oyunu",
  "/destek",
  "/profile",
  "/settings",
]);

function getSafeNextPath() {
  if (typeof window === "undefined") {
    return "/dashboard";
  }
  const next = new URLSearchParams(window.location.search).get("next");
  return next && allowedNextPaths.has(next) ? next : "/dashboard";
}

const networkNodes = [
  { x: 40, y: 420 }, { x: 110, y: 470 }, { x: 60, y: 520 }, { x: 150, y: 400 },
  { x: 190, y: 500 }, { x: 20, y: 560 }, { x: 130, y: 560 }, { x: 230, y: 440 },
  { x: 660, y: 210 }, { x: 720, y: 160 }, { x: 780, y: 220 }, { x: 700, y: 270 },
  { x: 830, y: 180 }, { x: 760, y: 300 }, { x: 880, y: 260 }, { x: 820, y: 330 },
];
const networkLinks: [number, number][] = [
  [0, 1], [1, 2], [1, 3], [3, 4], [2, 5], [2, 6], [4, 6], [3, 7],
  [8, 9], [9, 10], [8, 11], [10, 11], [9, 12], [10, 13], [12, 14], [13, 14], [11, 13], [14, 15],
];

function EyeIcon({ off }: { off: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {off ? (
        <>
          <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-3.16 4.19M14.12 14.12a3 3 0 1 1-4.24-4.24" />
          <line x1="1" y1="1" x2="23" y2="23" />
        </>
      ) : (
        <>
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
        </>
      )}
    </svg>
  );
}

function LoginPageContent() {
  const auth = useAuth();
  const [email, setEmail] = useState("mehmet@example.com");
  const [password, setPassword] = useState("demo1234");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.loading && auth.user) {
      requestPageTransition(getSafeNextPath(), true);
    }
  }, [auth.loading, auth.user]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await auth.login(email, password);
      requestPageTransition(getSafeNextPath(), true);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Giris yapilamadi.");
    }
  }

  return (
    <main
      data-theme="dark"
      className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#0b1220] px-4 py-12"
    >
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.35]"
        viewBox="0 0 960 640"
        preserveAspectRatio="xMidYMid slice"
      >
        <g className="network-drift">
          {networkLinks.map(([a, b], i) => (
            <line
              key={i}
              className="network-line"
              x1={networkNodes[a].x}
              y1={networkNodes[a].y}
              x2={networkNodes[b].x}
              y2={networkNodes[b].y}
              stroke="#3b5578"
              strokeWidth="1"
              style={{ animationDelay: `${(i % 6) * 0.4}s`, animationDuration: `${5 + (i % 4)}s` }}
            />
          ))}
          {networkNodes.map((n, i) => (
            <circle
              key={i}
              className="network-node"
              cx={n.x}
              cy={n.y}
              r="3"
              fill="#5b7ba3"
              style={{ animationDelay: `${(i % 8) * 0.35}s` }}
            />
          ))}
        </g>
      </svg>

      <div className="relative z-10 flex w-full max-w-sm flex-col items-center gap-7">
        <span
          aria-hidden="true"
          className="block h-9 w-36 bg-white [mask-image:url('/polifin-logo-clean.svg')] [mask-position:center] [mask-repeat:no-repeat] [mask-size:contain]"
        />
        <span className="sr-only">POLIFIN</span>

        <div className="w-full rounded-2xl bg-[var(--color-surface-elevated)] p-7 shadow-2xl">
          <h1 className="text-center text-xl font-bold text-[var(--color-heading)]">Giriş Yap</h1>

          <form className="mt-6 space-y-4" onSubmit={submit}>
            <label className="block text-sm">
              <span className="font-medium text-[var(--color-text)]">E-mail</span>
              <input
                className="mt-1.5 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-input-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text)] outline-none transition placeholder:text-[var(--color-muted)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary-soft)]"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                placeholder="mehmet@example.com"
                autoComplete="username"
              />
            </label>

            <label className="block text-sm">
              <span className="font-medium text-[var(--color-text)]">Şifre</span>
              <div className="relative mt-1.5">
                <input
                  className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-input-bg)] px-3.5 py-2.5 pr-10 text-sm text-[var(--color-text)] outline-none transition placeholder:text-[var(--color-muted)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary-soft)]"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Şifreyi gizle" : "Şifreyi göster"}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-muted)] transition hover:text-[var(--color-text)]"
                >
                  <EyeIcon off={!showPassword} />
                </button>
              </div>
            </label>

            <div className="flex justify-end">
              <a href="#" className="text-xs font-medium text-blue-600 hover:text-blue-700">
                Şifremi unuttum?
              </a>
            </div>

            {error && (
              <div className="rounded-lg border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] p-3 text-sm text-[var(--color-danger-text)]">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={auth.loading}
              className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {auth.loading ? "Kontrol ediliyor…" : "Giriş yap"}
            </button>
          </form>

          <div className="mt-6 flex items-center justify-center gap-3 text-center">
            <Link
              href="/register"
              className="text-xs font-medium text-slate-500 transition hover:text-slate-700"
            >
              Hesabınız yok mu? Kayıt olun
            </Link>
            <span className="text-xs text-slate-700">·</span>
            <Link
              href="/danisman-giris"
              className="text-xs font-medium text-slate-500 transition hover:text-slate-700"
            >
              Danışman Girişi
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return <LoginPageContent />;
}
