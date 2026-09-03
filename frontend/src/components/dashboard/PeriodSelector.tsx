"use client";

import type { PerformanceRange } from "../../models/portfolio";

/**
 * Genel bakis ekraninin donem secici seridi. Hem soldaki performans
 * grafigini hem de "Donem Degisimi" kartini ve varlik tablosundaki
 * KAR/ZARAR sutununu ayni anda yonetir - tek bir donem kavrami olsun diye
 * ekranda TEK yerde durur.
 */

const ARALIKLAR: Array<{ deger: PerformanceRange; etiket: string; ad: { tr: string; en: string } }> = [
  { deger: "1G", etiket: "1G", ad: { tr: "Bugün", en: "Today" } },
  { deger: "1H", etiket: "1H", ad: { tr: "Son 1 hafta", en: "Last week" } },
  { deger: "1A", etiket: "1A", ad: { tr: "Son 1 ay", en: "Last month" } },
  { deger: "1Y", etiket: "1Y", ad: { tr: "Son 1 yıl", en: "Last year" } },
];

export function PeriodSelector({
  deger,
  onDegis,
  yukleniyor,
  language,
}: {
  deger: PerformanceRange;
  onDegis: (aralik: PerformanceRange) => void;
  yukleniyor: boolean;
  language: "tr" | "en";
}) {
  return (
    <div
      role="group"
      aria-label={language === "tr" ? "Dönem seçimi" : "Period selection"}
      className="inline-flex gap-1 rounded-xl border app-border bg-[var(--color-surface-muted)] p-1"
    >
      {ARALIKLAR.map((aralik) => {
        const secili = deger === aralik.deger;
        return (
          <button
            key={aralik.deger}
            type="button"
            onClick={() => onDegis(aralik.deger)}
            // Yuklenirken yalnizca SECILI OLMAYAN dugmeler kilitlenir:
            // secili olani da kilitlemek butun seridi soluklastirirdi.
            disabled={yukleniyor && !secili}
            aria-pressed={secili}
            title={aralik.ad[language]}
            className={`rounded-lg px-3.5 py-1.5 text-sm font-semibold transition disabled:opacity-50 ${
              secili
                ? "bg-[var(--color-panel-dark)] text-white shadow-sm"
                : "app-muted hover:opacity-80"
            }`}
          >
            {aralik.etiket}
          </button>
        );
      })}
    </div>
  );
}
