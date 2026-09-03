"use client";

import type { PerformanceRange } from "../../models/portfolio";

/**
 * Genel bakis ekraninin donem secici seridi. Hem soldaki performans
 * grafigini hem de "Donem Degisimi" kartini ve varlik tablosundaki
 * KAR/ZARAR sutununu ayni anda yonetir - tek bir donem kavrami olsun diye
 * ekranda TEK yerde durur.
 */

const RANGES: Array<{ value: PerformanceRange; label: string; title: { tr: string; en: string } }> = [
  { value: "1G", label: "1G", title: { tr: "Bugün", en: "Today" } },
  { value: "1H", label: "1H", title: { tr: "Son 1 hafta", en: "Last week" } },
  { value: "1A", label: "1A", title: { tr: "Son 1 ay", en: "Last month" } },
  { value: "1Y", label: "1Y", title: { tr: "Son 1 yıl", en: "Last year" } },
];

export function PeriodSelector({
  value,
  onChange,
  loading,
  language,
}: {
  value: PerformanceRange;
  onChange: (range: PerformanceRange) => void;
  loading: boolean;
  language: "tr" | "en";
}) {
  return (
    <div
      role="group"
      aria-label={language === "tr" ? "Dönem seçimi" : "Period selection"}
      className="inline-flex gap-1 rounded-xl border app-border bg-[var(--color-surface-muted)] p-1"
    >
      {RANGES.map((range) => {
        const isActive = value === range.value;
        return (
          <button
            key={range.value}
            type="button"
            onClick={() => onChange(range.value)}
            // Yuklenirken yalnizca SECILI OLMAYAN dugmeler kilitlenir:
            // secili olani da kilitlemek butun seridi soluklastirirdi.
            disabled={loading && !isActive}
            aria-pressed={isActive}
            title={range.title[language]}
            className={`rounded-lg px-3.5 py-1.5 text-sm font-semibold transition disabled:opacity-50 ${
              isActive
                ? "bg-[var(--color-panel-dark)] text-white shadow-sm"
                : "app-muted hover:opacity-80"
            }`}
          >
            {range.label}
          </button>
        );
      })}
    </div>
  );
}
