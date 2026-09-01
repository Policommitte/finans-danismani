"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useLanguage } from "../../contexts/LanguageContext";
import type { IdleCashBasketOption, IdleCashSuggestion } from "../../models/chat";
import { createBasketMarketOrders } from "../../services/tradingService";

type Language = "tr" | "en";

const RISK_LABELS = {
  tr: { LOW: "Düşük", MEDIUM: "Orta", HIGH: "Yüksek" },
  en: { LOW: "Low", MEDIUM: "Medium", HIGH: "High" },
} as const;

const GOAL_LABELS = {
  tr: { LONG_TERM: "Uzun vadeli birikim", GROWTH: "Büyüme odaklı", MOMENTUM: "Momentum", LOW_VOLATILITY: "Düşük oynaklık" },
  en: { LONG_TERM: "Long-term investing", GROWTH: "Growth focused", MOMENTUM: "Momentum", LOW_VOLATILITY: "Low volatility" },
} as const;

const ASSET_CLASS_LABELS: Record<Language, Record<string, string>> = {
  tr: { STOCK: "BIST hissesi", USA_STOCK: "ABD hissesi", EU_STOCK: "Avrupa hissesi", ETF: "ETF", GOLD: "Altın", COMMODITY: "Emtia", FOREX: "Döviz", CRYPTO: "Kripto varlık" },
  en: { STOCK: "BIST stock", USA_STOCK: "US stock", EU_STOCK: "European stock", ETF: "ETF", GOLD: "Gold", COMMODITY: "Commodity", FOREX: "FX", CRYPTO: "Crypto asset" },
};

const SCORE_COMPONENT_LABELS: Record<Language, Record<string, string>> = {
  tr: { yillik_performans: "Yıllık performans", haftalik_momentum: "Haftalık momentum", gunluk_momentum: "Günlük momentum", oynaklik: "Oynaklık", risk_profili: "Risk profili", profil_sinif_uyumu: "Profil-sınıf uyumu", hedef_sinif_uyumu: "Hedef-sınıf uyumu", mevcut_portfoy: "Mevcut portföy" },
  en: { yillik_performans: "Annual performance", haftalik_momentum: "Weekly momentum", gunluk_momentum: "Daily momentum", oynaklik: "Volatility", risk_profili: "Risk profile", profil_sinif_uyumu: "Profile-class fit", hedef_sinif_uyumu: "Goal-class fit", mevcut_portfoy: "Current portfolio" },
};

const SUITABILITY_LABELS = {
  tr: { HIGH: "Yüksek uygunluk", MEDIUM: "Orta uygunluk", LOW: "Düşük uygunluk" },
  en: { HIGH: "High suitability", MEDIUM: "Medium suitability", LOW: "Low suitability" },
} as const;

const suitabilityClasses = {
  HIGH: "bg-emerald-50 text-emerald-800",
  MEDIUM: "bg-amber-50 text-amber-800",
  LOW: "bg-slate-100 text-slate-700",
} as const;

export function IdleCashSuggestionModal({
  suggestion,
  onClose,
  title,
  subtitle,
  strategyLabel,
  metrics,
  backtest,
}: {
  suggestion: IdleCashSuggestion | null;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  strategyLabel?: string;
  metrics?: IdleCashBasketOption["metrics"];
  backtest?: IdleCashBasketOption["backtest"];
}) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const tryFormatter = new Intl.NumberFormat(locale, { style: "currency", currency: "TRY", maximumFractionDigits: 2 });
  const [mounted, setMounted] = useState(false);
  const [orderStep, setOrderStep] = useState<"idle" | "confirm" | "submitting" | "success">("idle");
  const [orderError, setOrderError] = useState<string | null>(null);
  const [createdOrderCount, setCreatedOrderCount] = useState(0);

  useEffect(() => setMounted(true), []);
  useEffect(() => {
    setOrderStep("idle");
    setOrderError(null);
    setCreatedOrderCount(0);
  }, [suggestion]);
  useEffect(() => {
    if (!suggestion) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [suggestion, onClose]);

  if (!mounted || !suggestion) return null;

  async function submitBasketOrders() {
    if (!suggestion) return;
    setOrderStep("submitting");
    setOrderError(null);
    try {
      const orders = await createBasketMarketOrders(
        suggestion.items.map((item) => ({ symbol: item.symbol, quantity: item.quantity })),
      );
      setCreatedOrderCount(orders.length);
      setOrderStep("success");
    } catch (error) {
      setOrderError(
        language === "tr" && error instanceof Error
          ? error.message
          : language === "tr"
            ? "Sepet emirleri oluşturulamadı."
            : "Basket orders could not be created.",
      );
      setOrderStep("confirm");
    }
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-[2px]"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="idle-cash-title"
        className="flex max-h-[calc(100vh-2rem)] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border app-card shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b px-6 py-5">
          <div>
            <p className="mb-1 text-sm font-semibold text-[var(--color-primary)]">
              {language === "tr" ? "Kişiselleştirilmiş öneri" : "Personalized suggestion"}
            </p>
            <h2 id="idle-cash-title" className="text-2xl font-bold">
              {title ?? (language === "tr"
                ? suggestion.mode === "basket" ? "Atıl bakiye için yatırım sepeti" : "Bakiyeye uygun tek varlık"
                : suggestion.mode === "basket" ? "Investment basket for available cash" : "Single asset for available cash")}
            </h2>
            {subtitle && <p className="mt-2 text-sm text-[var(--color-muted)]">{subtitle}</p>}
            {strategyLabel && (
              <span className="mt-2 inline-flex rounded-full bg-[var(--color-soft)] px-3 py-1 text-xs font-semibold">
                {strategyLabel}
              </span>
            )}
            <p className="mt-2 text-sm text-[var(--color-muted)]">
              {language === "tr"
                ? suggestion.preference_summary
                : `${suggestion.items[0]?.candidate_count ?? 0} eligible candidates were evaluated for the ${RISK_LABELS.en[suggestion.risk_profile].toLowerCase()} risk profile and ${GOAL_LABELS.en[suggestion.goal].toLowerCase()} goal; ${suggestion.items.length} assets were selected.`}
            </p>
          </div>
          <button
            type="button"
            aria-label={language === "tr" ? "Öneriyi kapat" : "Close suggestion"}
            className="rounded-lg px-3 py-1 text-2xl text-[var(--color-muted)] hover:bg-black/5"
            onClick={onClose}
          >
            ×
          </button>
        </header>

        <div className="overflow-y-auto px-6 py-5">
          <IdleCashSuggestionContent
            suggestion={suggestion}
            metrics={metrics}
            backtest={backtest}
          />
        </div>

        <footer className="border-t px-6 py-4">
          {orderStep === "confirm" && (
            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <p className="font-semibold">
                {language === "tr"
                  ? `Sepetteki ${suggestion.items.length} varlık için alış emri oluşturulsun mu?`
                  : `Create buy orders for the ${suggestion.items.length} assets in this basket?`}
              </p>
              <p className="mt-1 text-xs">
                {language === "tr"
                  ? `Emirler piyasa emri olarak beklemeye alınır ve bir sonraki doğrulanmış fiyat güncellemesinde değerlendirilir. Tahmini toplam ${tryFormatter.format(suggestion.estimated_total)}.`
                  : `Orders will be queued as market orders and evaluated at the next verified price update. Estimated total: ${tryFormatter.format(suggestion.estimated_total)}.`}
              </p>
            </div>
          )}
          {orderStep === "success" && (
            <p className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-900" role="status">
              {language === "tr"
                ? `${createdOrderCount} sepet emri başarıyla oluşturuldu. Emirleri Manuel Alım bölümünden takip edebilirsin.`
                : `${createdOrderCount} basket orders were created successfully. You can track them under Manual Trading.`}
            </p>
          )}
          {orderError && (
            <p className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
              {orderError}
            </p>
          )}
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              className="rounded-lg border px-5 py-3 font-semibold"
              onClick={orderStep === "confirm" ? () => setOrderStep("idle") : onClose}
              disabled={orderStep === "submitting"}
            >
              {orderStep === "confirm"
                ? language === "tr" ? "Vazgeç" : "Cancel"
                : language === "tr" ? "Kapat" : "Close"}
            </button>
            {orderStep === "idle" && (
              <button
                type="button"
                className="rounded-lg app-primary px-5 py-3 text-center font-semibold"
                onClick={() => setOrderStep("confirm")}
              >
                {language === "tr" ? "Sepet için emir ver" : "Place basket orders"}
              </button>
            )}
            {orderStep === "confirm" && (
              <button
                type="button"
                className="rounded-lg app-primary px-5 py-3 text-center font-semibold"
                onClick={() => void submitBasketOrders()}
              >
                {language === "tr" ? "Onayla ve emirleri oluştur" : "Confirm and create orders"}
              </button>
            )}
            {orderStep === "submitting" && (
              <button type="button" className="rounded-lg app-primary px-5 py-3 font-semibold opacity-70" disabled>
                {language === "tr" ? "Emirler oluşturuluyor…" : "Creating orders…"}
              </button>
            )}
          </div>
        </footer>
      </section>
    </div>,
    document.body,
  );
}

export function IdleCashSuggestionContent({
  suggestion,
  metrics,
  backtest,
}: {
  suggestion: IdleCashSuggestion;
  metrics?: IdleCashBasketOption["metrics"];
  backtest?: IdleCashBasketOption["backtest"];
}) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const tryFormatter = new Intl.NumberFormat(locale, { style: "currency", currency: "TRY", maximumFractionDigits: 2 });
  return (
    <>
      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Summary
          label={language === "tr" ? "Kullanılabilir nakit" : "Available cash"}
          value={tryFormatter.format(suggestion.available_balance)}
        />
        <Summary label={language === "tr" ? "Önerilen toplam" : "Suggested total"} value={tryFormatter.format(suggestion.estimated_total)} />
        <Summary label={language === "tr" ? "Risk profili" : "Risk profile"} value={RISK_LABELS[language][suggestion.risk_profile]} />
        <Summary label={language === "tr" ? "Hedef" : "Goal"} value={GOAL_LABELS[language][suggestion.goal]} />
      </div>

      {metrics && (
        <div className="mb-5 rounded-xl border p-4 text-sm">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Summary label={language === "tr" ? "Sepet riski" : "Basket risk"} value={RISK_LABELS[language][metrics.risk_level]} />
            <Summary label={language === "tr" ? "20 günlük oynaklık" : "20-day volatility"} value={`%${metrics.expected_volatility_20d_pct.toLocaleString(locale)}`} />
            <Summary label={language === "tr" ? "Çeşitlendirme" : "Diversification"} value={`${metrics.diversification_score.toLocaleString(locale)} / 100`} />
            <Summary label={language === "tr" ? "Dağılım" : "Allocation"} value={`${metrics.asset_class_count} ${language === "tr" ? "sınıf" : "classes"} · ${metrics.sector_count} ${language === "tr" ? "sektör" : "sectors"}`} />
          </div>
          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-[var(--color-muted)]">
            <span>{language === "tr" ? "Ortalama korelasyon" : "Average correlation"}: {metrics.average_correlation == null ? (language === "tr" ? "Yeterli veri yok" : "Insufficient data") : metrics.average_correlation.toLocaleString(locale)}</span>
            <span>{language === "tr" ? "Bölge sayısı" : "Regions"}: {metrics.region_count}</span>
            <span>{language === "tr" ? "En yüksek tek varlık ağırlığı" : "Largest single-asset weight"}: %{metrics.largest_weight_pct.toLocaleString(locale)}</span>
          </div>
        </div>
      )}

      {backtest && <BasketBacktestSummary backtest={backtest} language={language} />}

      <div className="space-y-3">
        {suggestion.items.map((item) => (
          <article key={item.asset_id} className="rounded-xl border p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded-md bg-[var(--color-primary)] px-2 py-1 text-sm font-bold text-white">
                    {item.symbol}
                  </span>
                  <h3 className="font-semibold">{item.name}</h3>
                </div>
                <p className="mt-2 text-sm text-[var(--color-muted)]">
                  {item.quantity.toLocaleString(locale, { maximumFractionDigits: 6 })} {language === "tr" ? "birim" : "units"} · {ASSET_CLASS_LABELS[language][item.asset_class] ?? item.asset_class} · {language === "tr" ? "referans" : "reference"} {tryFormatter.format(item.reference_price)}
                </p>
                <p className="mt-1 text-xs text-[var(--color-muted)]">
                  {item.sector.replaceAll("_", " ")} · {item.region} · {item.currency}
                </p>
              </div>
              <div className="text-right">
                <p className="font-bold">{tryFormatter.format(item.estimated_amount)}</p>
                <p className="text-sm text-[var(--color-muted)]">
                  {language === "tr" ? "Sepetin" : "Basket weight"} %{item.weight_pct.toLocaleString(locale)}
                </p>
                <span className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font-semibold ${suitabilityClasses[item.suitability_level]}`}>
                  {SUITABILITY_LABELS[language][item.suitability_level]}
                </span>
                <p className="mt-1 text-xs text-[var(--color-muted)]">
                  {language === "tr"
                    ? `Bu hedefte ${item.candidate_count} aday içinde ${item.goal_rank}. sırada`
                    : `Ranked ${item.goal_rank} of ${item.candidate_count} candidates for this goal`}
                </p>
              </div>
            </div>
            <details className="mt-3 rounded-lg bg-[var(--color-soft)] p-3 text-xs">
              <summary className="cursor-pointer font-semibold">{language === "tr" ? "Hesaplama ayrıntısı" : "Calculation details"}</summary>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {Object.entries(item.score_components).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3">
                    <span className="text-[var(--color-muted)]">{SCORE_COMPONENT_LABELS[language][key] ?? key}</span>
                    <strong className={value < 0 ? "text-red-600" : value > 0 ? "text-emerald-700" : ""}>
                      {value > 0 ? "+" : ""}{value.toLocaleString(locale, { maximumFractionDigits: 2 })}
                    </strong>
                  </div>
                ))}
              </div>
            </details>
            <ul className="mt-3 space-y-1 text-sm text-[var(--color-muted)]">
              {(language === "tr"
                ? item.rationale
                : [
                    `Scored for the ${RISK_LABELS.en[suggestion.risk_profile].toLowerCase()} risk profile, ${GOAL_LABELS.en[suggestion.goal].toLowerCase()} goal and ${ASSET_CLASS_LABELS.en[item.asset_class] ?? item.asset_class} characteristics.`,
                    item.score_components.mevcut_portfoy < 0
                      ? "The existing position was considered with a lower selection priority."
                      : "It may improve diversification because it is not currently held in the portfolio.",
                  ]).map((reason) => <li key={reason}>• {reason}</li>)}
            </ul>
          </article>
        ))}
      </div>

      <p className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
        {language === "tr"
          ? "Hedef içi uygunluk bir alım sinyali veya beklenen getiri değildir; varlıkları yalnızca seçilen hedefteki diğer adaylarla karşılaştırır."
          : "Goal suitability is not a buy signal or an expected return; it only compares assets with other candidates for the selected goal."}
      </p>

      <div className="mt-5 rounded-xl bg-[var(--color-soft)] p-4 text-sm">
        <div className="flex flex-wrap justify-between gap-2">
          <span>{language === "tr" ? "Dağıtım üst sınırı (%10 nakit tamponuyla)" : "Allocation limit (with a 10% cash buffer)"}</span>
          <strong>{tryFormatter.format(suggestion.investable_amount)}</strong>
        </div>
        <div className="flex flex-wrap justify-between gap-2">
          <span>{language === "tr" ? "Sepet sonrası ayrılmamış bakiye" : "Unallocated cash after basket"}</span>
          <strong>{tryFormatter.format(suggestion.unallocated_balance)}</strong>
        </div>
        <p className="mt-3 text-xs text-[var(--color-muted)]">
          {language === "tr" ? suggestion.disclaimer : "This rule-based basket is for informational and simulation purposes only; it is not investment advice."}
        </p>
      </div>
    </>
  );
}

function BasketBacktestSummary({ backtest, language }: { backtest: IdleCashBasketOption["backtest"]; language: Language }) {
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const statusLabels = {
    SUFFICIENT: language === "tr" ? "Yeterli veri" : "Sufficient data",
    LIMITED: language === "tr" ? "Sınırlı veri" : "Limited data",
    INSUFFICIENT: language === "tr" ? "Yetersiz veri" : "Insufficient data",
  } as const;
  const statusClasses = {
    SUFFICIENT: "bg-emerald-50 text-emerald-800",
    LIMITED: "bg-amber-50 text-amber-800",
    INSUFFICIENT: "bg-slate-100 text-slate-700",
  } as const;
  const pct = (value: number | null) => value == null
    ? "—"
    : `%${value.toLocaleString(locale, { maximumFractionDigits: 2 })}`;

  return (
    <section className="mb-5 rounded-xl border p-4 text-sm" aria-label={language === "tr" ? "Geçmiş performans simülasyonu" : "Historical performance simulation"}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-bold">{language === "tr" ? "Geçmiş performans simülasyonu" : "Historical performance simulation"}</h3>
          <p className="mt-1 text-xs text-[var(--color-muted)]">
            {backtest.observation_count} {language === "tr" ? "ortak işlem günü" : "common trading days"}
            {backtest.start_date && backtest.end_date
              ? ` · ${backtest.start_date} – ${backtest.end_date}`
              : ""}
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusClasses[backtest.status]}`}>
          {statusLabels[backtest.status]}
        </span>
      </div>

      {backtest.status !== "INSUFFICIENT" && (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Summary label={language === "tr" ? "Maliyet sonrası getiri" : "Return after costs"} value={pct(backtest.net_return_pct)} />
            <Summary label={language === "tr" ? "Evren karşılaştırması" : "Universe benchmark"} value={pct(backtest.benchmark_return_pct)} />
            <Summary label={language === "tr" ? "En büyük düşüş" : "Maximum drawdown"} value={pct(backtest.max_drawdown_pct)} />
            <Summary label={language === "tr" ? "Yıllıklandırılmış oynaklık" : "Annualized volatility"} value={pct(backtest.annualized_volatility_pct)} />
          </div>
          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-[var(--color-muted)]">
            <span>{language === "tr" ? "Fark" : "Difference"}: {pct(backtest.excess_return_pct)}</span>
            <span>{language === "tr" ? "Risk/getiri oranı" : "Risk/return ratio"}: {backtest.risk_adjusted_return?.toLocaleString(locale) ?? "—"}</span>
            <span>{language === "tr" ? "Tahmini maliyet etkisi" : "Estimated cost impact"}: {pct(backtest.transaction_cost_impact_pct)}</span>
            <span>{language === "tr" ? "Ağırlık dengeleme" : "Rebalancing"}: {backtest.rebalance_count} {language === "tr" ? "kez" : "times"}</span>
          </div>
          <p className="mt-2 text-xs text-[var(--color-muted)]">
            {language === "tr" ? `Karşılaştırma: ${backtest.benchmark_label}` : "Benchmark: eligible assets for the selected goal"}
          </p>
        </>
      )}

      <p className="mt-3 rounded-lg bg-[var(--color-soft)] p-3 text-xs">
        {language === "tr"
          ? backtest.note
          : backtest.status === "SUFFICIENT"
            ? "Current basket members and target weights were simulated using historical daily returns after estimated transaction costs. This is not a forecast."
            : "Historical coverage is limited, so the result has limited confidence. It is a simulation of the current basket, not a forecast."}
      </p>
    </section>
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-[var(--color-soft)] p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-muted)]">{label}</p>
      <p className="mt-1 text-lg font-bold">{value}</p>
    </div>
  );
}
