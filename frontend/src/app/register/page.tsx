"use client";
import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { requestPageTransition } from "../../components/layout/transitionEvents";
import { useAuth } from "../../hooks/useAuth";

/**
 * Kayit akisi (TCKN/NVI dogrulamali eski akis KALDIRILDI):
 *
 *   1. Banka hesabi baglama - SIMULASYON. Gercek bir banka API'sine
 *      baglanilmaz; secilen banka rozeti ve girilen hesap numarasi
 *      dogrulanmadan bilgi amacli backend'e iletilir.
 *   2. E-posta + sifre - kaydi tamamlar, backend otomatik giris icin
 *      token doner (bkz. useAuth.register).
 *
 * Basarili kayittan sonra kullanici HER ZAMAN /portfolio'ya yonlendirilir -
 * /login'e asla geri donulmez.
 */

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

/** Jenerik banka ikonu (kolonlu bina) - hicbir markaya ait DEGIL, internetten
 * cekilmedi, elle cizildi. Tum banka rozetleri AYNI ikonu paylasir. */
function GenericBankIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 10l9-6 9 6" />
      <path d="M4 10v9M9 10v9M15 10v9M20 10v9" />
      <path d="M2 21h20" />
      <path d="M2 10h20" />
    </svg>
  );
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

const inputClassName =
  "mt-1.5 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-input-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text)] outline-none transition placeholder:text-[var(--color-muted)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary-soft)]";

/** Yalnizca gorsel secim icin banka adlari - gercek bir kuruma BAGLANMAZ. */
const BANK_NAMES = ["Ziraat Bankası", "İş Bankası", "Garanti BBVA", "Akbank", "Yapı Kredi", "Enpara"];

type Step = "bank" | "credentials";

function StepDots({ step }: { step: Step }) {
  return (
    <div className="flex items-center justify-center gap-2" aria-hidden="true">
      <span className={`h-1.5 w-6 rounded-full transition ${step === "bank" ? "bg-[var(--color-primary)]" : "bg-emerald-500"}`} />
      <span className={`h-1.5 w-6 rounded-full transition ${step === "credentials" ? "bg-[var(--color-primary)]" : "bg-white/15"}`} />
    </div>
  );
}

function RegisterPageContent() {
  const auth = useAuth();
  const [step, setStep] = useState<Step>("bank");

  // Adim 1: banka hesabi baglama (simulasyon)
  const [selectedBank, setSelectedBank] = useState<string | null>(null);
  const [accountNumber, setAccountNumber] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [bankError, setBankError] = useState<string | null>(null);

  // Adim 2: e-posta + sifre
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.loading && auth.user) {
      requestPageTransition("/portfolio", true);
    }
  }, [auth.loading, auth.user]);

  function submitBankStep(event: FormEvent) {
    event.preventDefault();
    setBankError(null);

    if (!selectedBank) {
      setBankError("Lütfen bir banka seçin.");
      return;
    }
    if (!/^\d{9}$/.test(accountNumber)) {
      setBankError("Hesap numarası 9 haneli olmalıdır.");
      return;
    }

    setConnecting(true);
    // Gercek bir banka API'sine baglanilmiyor - yalnizca akisin gerceklik
    // hissi vermesi icin kisa bir "getiriliyor" bekleme simulasyonu.
    window.setTimeout(() => {
      setConnecting(false);
      setStep("credentials");
    }, 1500);
  }

  async function submitCredentialsStep(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Şifreler eşleşmiyor.");
      return;
    }

    try {
      await auth.register({ email, password, account_number: accountNumber });
      requestPageTransition("/portfolio", true);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Kayıt oluşturulamadı.");
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

      <div className="relative z-10 flex w-full max-w-md flex-col items-center gap-7">
        <span
          aria-hidden="true"
          className="block h-9 w-36 bg-white [mask-image:url('/polifin-logo-clean.svg')] [mask-position:center] [mask-repeat:no-repeat] [mask-size:contain]"
        />
        <span className="sr-only">POLIFIN</span>

        <div className="w-full rounded-2xl bg-[var(--color-surface-elevated)] p-7 shadow-2xl">
          <h1 className="text-center text-xl font-bold text-[var(--color-heading)]">Kayıt Ol</h1>
          <div className="mt-4">
            <StepDots step={step} />
          </div>

          {step === "bank" ? (
            <>
              <p className="mt-5 text-center text-sm text-[var(--color-muted)]">
                Banka hesabını bağla{" "}
                <span className="text-[var(--color-muted)]/80">(simülasyon)</span>
              </p>

              <form className="mt-4 space-y-4" onSubmit={submitBankStep}>
                <div className="grid grid-cols-2 gap-2.5">
                  {BANK_NAMES.map((bank) => {
                    const active = selectedBank === bank;
                    return (
                      <button
                        key={bank}
                        type="button"
                        onClick={() => setSelectedBank(bank)}
                        aria-pressed={active}
                        className={`flex items-center gap-2 rounded-lg border px-3 py-2.5 text-left text-xs font-medium transition ${
                          active
                            ? "border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-primary-soft-text)]"
                            : "border-[var(--color-border)] bg-[var(--color-input-bg)] text-[var(--color-text)] hover:border-[var(--color-primary)]/60"
                        }`}
                      >
                        <GenericBankIcon />
                        <span className="truncate">{bank}</span>
                      </button>
                    );
                  })}
                </div>

                <label className="block text-sm">
                  <span className="font-medium text-[var(--color-text)]">Hesap Numarası</span>
                  <input
                    className={inputClassName}
                    value={accountNumber}
                    onChange={(event) => setAccountNumber(event.target.value.replace(/\D/g, "").slice(0, 9))}
                    type="text"
                    inputMode="numeric"
                    maxLength={9}
                    placeholder="9 haneli hesap numarası"
                    disabled={connecting}
                    required
                  />
                </label>

                {bankError && (
                  <div className="rounded-lg border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] p-3 text-sm text-[var(--color-danger-text)]">
                    {bankError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={connecting}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {connecting ? (
                    <>
                      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                      Hesap bilgileri getiriliyor…
                    </>
                  ) : (
                    "Hesabı Bağla"
                  )}
                </button>
              </form>
            </>
          ) : (
            <>
              <p className="mt-5 text-center text-sm text-[var(--color-muted)]">
                E-posta ve şifreni belirle
              </p>

              <form className="mt-4 space-y-4" onSubmit={submitCredentialsStep}>
                <label className="block text-sm">
                  <span className="font-medium text-[var(--color-text)]">E-mail</span>
                  <input
                    className={inputClassName}
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    type="email"
                    placeholder="mehmet@example.com"
                    autoComplete="username"
                    required
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
                      autoComplete="new-password"
                      minLength={8}
                      required
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

                <label className="block text-sm">
                  <span className="font-medium text-[var(--color-text)]">Şifre (Tekrar)</span>
                  <input
                    className={inputClassName}
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    minLength={8}
                    required
                  />
                </label>

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
                  {auth.loading ? "Kontrol ediliyor…" : "Kayıt ol"}
                </button>

                <button
                  type="button"
                  onClick={() => setStep("bank")}
                  className="w-full text-center text-xs font-medium text-[var(--color-muted)] transition hover:text-[var(--color-text)]"
                >
                  ← Banka hesabı adımına dön
                </button>
              </form>
            </>
          )}

          <div className="mt-6 text-center">
            <Link
              href="/login"
              className="text-xs font-medium text-slate-500 transition hover:text-slate-700"
            >
              Zaten hesabınız var mı? Giriş yapın
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function RegisterPage() {
  return <RegisterPageContent />;
}
