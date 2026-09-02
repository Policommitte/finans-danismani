"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { InvestmentPreferences } from "../../components/profile/InvestmentPreferences";
import { RiskProfileQuiz } from "../../components/profile/RiskProfileQuiz";
import Button from "../../components/ui/Button";
import { useAuth } from "../../hooks/useAuth";

type Goal = {
  id: string;
  name: string;
  target: number;
  saved: number;
  /** null = "Vade Yok". Basit bir yedek hesapla (kalan tutar / ay sayisi)
   * aylik biriktirme onerisi turetmek icin kullanilir - bkz. monthlySuggestion().
   * Mevcut oneri sistemi (Otonom Eylemler'in AL/SAT sinyal motoru,
   * backend/app/services/recommendation.py) bu tur bir hesap icin
   * TASARLANMAMIS (kural tabanli piyasa sinyali uretir, hedef/vade
   * planlamasi yapmaz) - kullaniciyla teyit edilip bilincli olarak bu
   * basit hesap tercih edildi. */
  termMonths: number | null;
};

//: `value` <select>'te string olarak tutulur - "" = Vade Yok (null).
const TERM_OPTIONS: { label: string; value: string; months: number | null }[] = [
  { label: "Vade Yok", value: "", months: null },
  { label: "1 Ay", value: "1", months: 1 },
  { label: "3 Ay", value: "3", months: 3 },
  { label: "6 Ay", value: "6", months: 6 },
  { label: "12 Ay", value: "12", months: 12 },
  { label: "24 Ay", value: "24", months: 24 },
  { label: "36 Ay", value: "36", months: 36 },
];

const initialGoals: Goal[] = [
  { id: "goal-1", name: "Ev peşinatı — Kadıköy 2+1", target: 500000, saved: 320000, termMonths: 24 },
  { id: "goal-2", name: "6 aylık acil durum fonu", target: 150000, saved: 142500, termMonths: null },
  { id: "goal-3", name: "Japonya tatili · 2027 yaz", target: 120000, saved: 45600, termMonths: 12 },
];

const currency = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0 });

/** Basit yedek hesap: kalan tutar / ay sayisi. Hedefe zaten ulasildiysa
 * (kalan <= 0) `0` doner - "ayda biriktir" onerisi anlamsiz hale gelir. */
function monthlySuggestion(goal: Goal): number | null {
  if (!goal.termMonths) {
    return null;
  }
  const remaining = goal.target - goal.saved;
  return remaining > 0 ? remaining / goal.termMonths : 0;
}

function progressPercent(goal: Goal): number {
  if (goal.target <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round((goal.saved / goal.target) * 100)));
}

function progressColor(percent: number): string {
  if (percent >= 80) {
    return "var(--color-success)";
  }
  if (percent >= 50) {
    return "var(--color-accent)";
  }
  return "var(--color-cta)";
}

function TrashIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6M14 11v6" />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z" />
    </svg>
  );
}

function TargetIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function SectionIcon({ accent, children }: { accent: string; children: ReactNode }) {
  return (
    <span
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
      style={{ background: `color-mix(in srgb, ${accent} 15%, var(--color-surface))`, color: accent }}
    >
      {children}
    </span>
  );
}

const RISK_TOLERANCE_LABELS: Record<string, string> = {
  LOW: "Düşük",
  MEDIUM: "Orta",
  HIGH: "Yüksek",
};

function FinancialGoals() {
  const [goals, setGoals] = useState<Goal[]>(initialGoals);
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [saved, setSaved] = useState("");
  const [term, setTerm] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  function handleAdd(event: FormEvent) {
    event.preventDefault();
    const trimmedName = name.trim();
    const targetValue = Number(target);
    const savedValue = Number(saved) || 0;
    const termValue = term ? Number(term) : null;

    if (!trimmedName || !targetValue || targetValue <= 0) {
      return;
    }

    setGoals((prev) => [
      ...prev,
      { id: `goal-${Date.now()}`, name: trimmedName, target: targetValue, saved: savedValue, termMonths: termValue },
    ]);
    setName("");
    setTarget("");
    setSaved("");
    setTerm("");
  }

  function handleRemove(id: string) {
    setGoals((prev) => prev.filter((goal) => goal.id !== id));
    if (editingId === id) {
      setEditingId(null);
    }
  }

  function handleStartEdit(goal: Goal) {
    setEditingId(goal.id);
    setEditValue(String(goal.saved));
  }

  function handleCancelEdit() {
    setEditingId(null);
    setEditValue("");
  }

  function handleSaveEdit(id: string) {
    const newSaved = Math.max(0, Number(editValue) || 0);
    setGoals((prev) => prev.map((goal) => (goal.id === id ? { ...goal, saved: newSaved } : goal)));
    setEditingId(null);
    setEditValue("");
  }

  return (
    <div className="rounded-2xl border app-card p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <SectionIcon accent="var(--color-brand-teal)">
          <TargetIcon />
        </SectionIcon>
        <h2 className="text-base font-semibold app-heading">Finansal Hedeflerim</h2>
      </div>
      <p className="mt-2 text-sm app-muted">
        Sözel hedef + tutar gir, her hedef otomatik olarak bir ilerleme çubuğuna dönüşsün.
      </p>

      <form onSubmit={handleAdd} className="mt-4 rounded-xl app-card-muted p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm sm:col-span-2">
            <span className="font-medium app-heading">Hedef (sözel)</span>
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Örn: Ev peşinatı için birikim yap"
              className="mt-1.5 w-full rounded-lg border app-input px-3.5 py-2.5 text-sm outline-none"
            />
          </label>
          <label className="text-sm">
            <span className="font-medium app-heading">Hedef Tutarı (₺)</span>
            <input
              type="number"
              min="0"
              inputMode="decimal"
              value={target}
              onChange={(event) => setTarget(event.target.value)}
              placeholder="500000"
              className="mt-1.5 w-full rounded-lg border app-input px-3.5 py-2.5 text-sm outline-none"
            />
          </label>
          <label className="text-sm">
            <span className="font-medium app-heading">Şu Ana Kadar Birikilen (₺)</span>
            <input
              type="number"
              min="0"
              inputMode="decimal"
              value={saved}
              onChange={(event) => setSaved(event.target.value)}
              placeholder="0"
              className="mt-1.5 w-full rounded-lg border app-input px-3.5 py-2.5 text-sm outline-none"
            />
          </label>
          <label className="text-sm sm:col-span-2">
            <span className="font-medium app-heading">Vade</span>
            <select
              value={term}
              onChange={(event) => setTerm(event.target.value)}
              className="mt-1.5 w-full rounded-lg border app-input px-3.5 py-2.5 text-sm outline-none"
            >
              {TERM_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <Button type="submit" className="mt-3">
          + Hedef Ekle
        </Button>

        <p className="mt-3 text-xs app-muted">
          Hedefler, Portföyüm sayfasındaki 'Hedeflerim' kartında da ilerleme çubuğuyla gösterilecek.
        </p>
      </form>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {goals.map((goal) => {
          const percent = progressPercent(goal);
          const color = progressColor(percent);

          return (
            <div key={goal.id} className="rounded-xl app-card-muted p-4">
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-semibold app-heading">{goal.name}</h3>
                <div className="flex shrink-0 items-center gap-2.5">
                  <span
                    className="rounded-full px-2.5 py-1 text-xs font-bold tabular-nums"
                    style={{ background: `color-mix(in srgb, ${color} 16%, var(--color-surface))`, color }}
                  >
                    %{percent}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleStartEdit(goal)}
                    aria-label={`${goal.name} birikimini güncelle`}
                    className="app-muted transition hover:text-[var(--color-primary)]"
                  >
                    <PencilIcon />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRemove(goal.id)}
                    aria-label={`${goal.name} hedefini sil`}
                    className="app-muted transition hover:text-[var(--color-danger)]"
                  >
                    <TrashIcon />
                  </button>
                </div>
              </div>

              {editingId === goal.id ? (
                <div className="mt-3">
                  <label className="block text-xs">
                    <span className="font-medium app-heading">Yeni birikilen tutar (₺)</span>
                    <input
                      type="number"
                      min="0"
                      inputMode="decimal"
                      value={editValue}
                      onChange={(event) => setEditValue(event.target.value)}
                      autoFocus
                      className="mt-1.5 w-full rounded-lg border app-input px-3 py-2 text-sm outline-none"
                    />
                  </label>
                  <div className="mt-2 flex items-center gap-2">
                    <Button type="button" onClick={() => handleSaveEdit(goal.id)} className="px-3 py-1.5 text-xs">
                      Kaydet
                    </Button>
                    <Button type="button" variant="secondary" onClick={handleCancelEdit} className="px-3 py-1.5 text-xs">
                      İptal
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="mt-3 flex items-baseline gap-1.5">
                    <span className="text-xl font-bold tabular-nums app-heading">₺{currency.format(goal.saved)}</span>
                    <span className="text-xs app-muted">/ ₺{currency.format(goal.target)} hedef</span>
                  </div>
                  <div
                    className="mt-2.5 h-2.5 overflow-hidden rounded-full shadow-inner"
                    style={{ background: "var(--color-border-soft)" }}
                  >
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${percent}%`,
                        background: `linear-gradient(90deg, color-mix(in srgb, ${color} 60%, transparent), ${color})`,
                      }}
                    />
                  </div>
                  {goal.termMonths ? (
                    <p className="mt-2.5 text-xs app-muted">
                      Vade: <span className="font-semibold app-heading">{goal.termMonths} Ay</span>
                      {" · "}
                      {(() => {
                        const monthly = monthlySuggestion(goal);
                        return monthly && monthly > 0
                          ? <>Ayda <span className="font-semibold app-heading">₺{currency.format(Math.ceil(monthly))}</span> biriktirmelisin</>
                          : "Hedefe ulaşıldı";
                      })()}
                    </p>
                  ) : null}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const auth = useAuth();
  const user = auth.user;
  const fullName = user ? `${user.first_name} ${user.last_name}`.trim() : "Kullanıcı";
  const initials = user ? `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`.toUpperCase() : "?";

  const riskLabel = user?.risk_tolerance ? RISK_TOLERANCE_LABELS[user.risk_tolerance] : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">Profil</h1>
        <p className="mt-1 text-sm app-muted">Hesap bilgilerini, finansal hedeflerini ve yatırım tercihlerini yönet.</p>
      </div>

      <div className="rounded-2xl border app-card p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-5">
          <div
            className="grid h-20 w-20 shrink-0 place-items-center rounded-full app-primary-soft text-2xl font-bold"
            style={{ boxShadow: "0 0 0 4px color-mix(in srgb, var(--color-primary) 14%, transparent)" }}
          >
            {initials || "?"}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold app-heading">{fullName}</h2>
            {user?.email && <p className="mt-1 text-sm app-muted">{user.email}</p>}
          </div>
          {riskLabel && (
            <span
              className="shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold"
              style={{
                background: "color-mix(in srgb, var(--color-primary) 12%, var(--color-surface))",
                color: "var(--color-primary)",
              }}
            >
              Risk toleransı: {riskLabel}
            </span>
          )}
        </div>
      </div>

      <FinancialGoals />

      <RiskProfileQuiz />

      <InvestmentPreferences />
    </div>
  );
}
