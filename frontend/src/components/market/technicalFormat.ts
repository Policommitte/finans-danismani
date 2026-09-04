import type { TechnicalLabel, TechnicalSignal } from "../../models/market";

/** Özet sınıfı → kullanıcıya gösterilen ad. */
export const SUMMARY_LABELS: Record<TechnicalLabel, string> = {
  GUCLU_AL: "Güçlü Al",
  AL: "Al",
  NOTR: "Nötr",
  SAT: "Sat",
  GUCLU_SAT: "Güçlü Sat",
};

export const SIGNAL_LABELS: Record<TechnicalSignal, string> = {
  AL: "Al",
  SAT: "Sat",
  NOTR: "Nötr",
  VERI_YOK: "Veri yok",
};

/** Sinyal → tema duyarlı renk değişkeni. */
export const SIGNAL_COLORS: Record<TechnicalSignal, string> = {
  AL: "var(--color-success)",
  SAT: "var(--color-danger)",
  NOTR: "var(--color-muted)",
  VERI_YOK: "var(--color-muted)",
};

export const SUMMARY_COLORS: Record<TechnicalLabel, string> = {
  GUCLU_AL: "var(--color-success)",
  AL: "var(--color-success)",
  NOTR: "var(--color-muted)",
  SAT: "var(--color-danger)",
  GUCLU_SAT: "var(--color-danger)",
};

/** Ölçek üzerindeki konum: skor -1..+1 → %0..%100. */
export function scorePosition(score: number): number {
  const clamped = Math.max(-1, Math.min(1, score));
  return ((clamped + 1) / 2) * 100;
}

const numberFormat = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 });

export function formatIndicatorValue(value: number | null): string {
  return value === null ? "—" : numberFormat.format(value);
}

/** "2026-09-03 00:00:00+00:00" → "3 Eyl 2026". */
export function formatDataTime(ts: string | null): string {
  if (!ts) {
    return "bilinmiyor";
  }
  const parsed = new Date(ts.replace(" ", "T"));
  if (Number.isNaN(parsed.getTime())) {
    return ts;
  }
  return parsed.toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric" });
}
