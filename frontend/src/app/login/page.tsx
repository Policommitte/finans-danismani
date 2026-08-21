"use client";
import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 48 48">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.1 8.1 3l5.7-5.7C34.5 6.1 29.6 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.7-.4-3.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.5 15.1 18.9 12 24 12c3.1 0 5.9 1.1 8.1 3l5.7-5.7C34.5 6.1 29.6 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-1.9 13.5-5.2l-6.2-5.2C29.3 35.4 26.8 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.6 39.6 16.3 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.2 5.6l6.2 5.2C39.9 36.6 44 30.9 44 24c0-1.3-.1-2.7-.4-3.5z" />
    </svg>
  );
}

function LinkedInIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24">
      <rect width="24" height="24" rx="4.5" fill="#0A66C2" />
      <path
        fill="#fff"
        d="M7.35 9.6H4.7v9.6h2.65V9.6Zm-1.32-1.2a1.53 1.53 0 1 0 0-3.06 1.53 1.53 0 0 0 0 3.06ZM9.15 9.6h2.54v1.31h.04c.35-.66 1.22-1.36 2.51-1.36 2.68 0 3.18 1.77 3.18 4.06v5.59h-2.65v-4.95c0-1.18-.02-2.7-1.64-2.7-1.65 0-1.9 1.29-1.9 2.62v5.03H9.15V9.6Z"
      />
    </svg>
  );
}

function AppleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="#000">
      <path d="M16.365 1.43c0 1.14-.415 2.1-1.246 2.87-.878.83-1.9 1.31-2.985 1.22-.13-1.1.42-2.27 1.24-3.02.85-.78 2.14-1.28 2.99-1.07zM20.94 17.28c-.55 1.27-.81 1.84-1.52 2.96-.99 1.56-2.38 3.5-4.1 3.52-1.53.02-1.93-.99-4-1-2.08-.01-2.5 1.01-4.03 1-1.72-.02-3.03-1.77-4.02-3.32-2.76-4.31-3.05-9.37-1.35-12.06 1.21-1.9 3.11-3.02 4.9-3.02 1.82 0 2.96 1 4.46 1 1.45 0 2.34-1 4.46-1 1.6 0 3.29.87 4.5 2.38-3.95 2.17-3.31 7.83.7 9.56z" />
    </svg>
  );
}

function SocialButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex flex-col items-center gap-2 text-xs text-slate-500 transition hover:text-slate-700"
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 bg-white shadow-sm transition hover:shadow-md">
        {children}
      </span>
      {label}
    </button>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const auth = useAuth();
  const [email, setEmail] = useState("mehmet@example.com");
  const [password, setPassword] = useState("demo1234");
  const [showPassword, setShowPassword] = useState(false);
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

  function noopSocialLogin() {
    setError("Bu giris yontemi henuz aktif degil. E-posta ve sifre ile devam et.");
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
          <h1 className="text-xl font-bold text-[var(--color-heading)]">Giriş Yap</h1>
          <p className="mt-1 text-sm text-[var(--color-muted)]">Hesabınıza güvenle erişin</p>

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

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-[var(--color-border)]" />
            <span className="text-xs text-[var(--color-muted)]">veya</span>
            <div className="h-px flex-1 bg-[var(--color-border)]" />
          </div>

          <div className="flex justify-center gap-6">
            <SocialButton label="Google ile devam et" onClick={noopSocialLogin}>
              <GoogleIcon />
            </SocialButton>
            <SocialButton label="LinkedIn ile devam et" onClick={noopSocialLogin}>
              <LinkedInIcon />
            </SocialButton>
            <SocialButton label="Apple ile devam et" onClick={noopSocialLogin}>
              <AppleIcon />
            </SocialButton>
          </div>
        </div>
      </div>
    </main>
  );
}
