"use client";

import { useCallback, useEffect, useState } from "react";
import { IdleCashSuggestionModal } from "../chat/IdleCashSuggestionModal";
import { ErrorState } from "../feedback/ErrorState";
import { LoadingState } from "../feedback/LoadingState";
import { useAsyncData } from "../../hooks/useAsyncData";
import { useLanguage } from "../../contexts/LanguageContext";
import type { IdleCashBasketOption, IdleCashSuggestion } from "../../models/chat";
import { getIdleCashBasketCatalog } from "../../services/recommendationService";

type Language = "tr" | "en";

const GOALS: Array<{
  key: IdleCashSuggestion["goal"];
  label: Record<Language, string>;
  description: Record<Language, string>;
}> = [
  {
    key: "LONG_TERM",
    label: { tr: "Uzun Vadeli Birikim", en: "Long-Term Investing" },
    description: {
      tr: "Uzun dönem performansını ve daha istikrarlı fiyat hareketlerini öne çıkarır.",
      en: "Prioritizes long-term performance and more stable price movements.",
    },
  },
  {
    key: "GROWTH",
    label: { tr: "Büyüme Odaklı", en: "Growth Focused" },
    description: {
      tr: "Orta ve uzun vadede güçlü performans gösteren varlıklara ağırlık verir.",
      en: "Emphasizes assets with strong medium- and long-term performance.",
    },
  },
  {
    key: "MOMENTUM",
    label: { tr: "Momentum", en: "Momentum" },
    description: {
      tr: "Günlük ve haftalık yükseliş eğilimi güçlü varlıkları öne çıkarır.",
      en: "Prioritizes assets with strong daily and weekly upward trends.",
    },
  },
  {
    key: "LOW_VOLATILITY",
    label: { tr: "Düşük Oynaklık", en: "Low Volatility" },
    description: {
      tr: "Fiyat hareketleri görece daha sınırlı varlıklarla dalgalanmayı azaltmayı hedefler.",
      en: "Aims to reduce fluctuations with assets that have relatively stable prices.",
    },
  },
];

const PANEL_COPY = {
  tr: {
    loading: "Sepet önerisi hazırlanıyor",
    error: "Sepet önerisi oluşturulamadı.",
    eyebrow: "Kişiselleştirilmiş yatırım sepeti",
    title: "Atıl bakiye için yatırım sepeti alternatifleri",
    intro: "Uygulamadaki tüm varlıklar taranır; bakiyen risk profilin, portföyün ve hedefinle uyumlu olanlara dağıtılır.",
    goalAria: "Sepet hedefi",
    reviewSchedule: "Değerlendirme düzeni",
    lastReview: "Son değerlendirme",
    lastChange: "Son içerik değişimi",
    riskFit: "risk profiline uygun",
    basketRisk: "Sepet riski",
    volatility: "20 günlük oynaklık",
    diversification: "Çeşitlendirme",
    allocation: "Dağılım",
    simulation: "Geçmiş simülasyon",
    netReturn: "Maliyet sonrası",
    days: "gün",
    total: "Önerilen toplam",
    assets: "varlık",
    details: "Detayları gör",
    openDetails: "sepetinin detaylarını aç",
    classes: "sınıf",
    sectors: "sektör",
  },
  en: {
    loading: "Preparing basket suggestions",
    error: "Basket suggestions could not be created.",
    eyebrow: "Personalized investment basket",
    title: "Investment basket alternatives for available cash",
    intro: "All tradable assets are screened and your available cash is allocated according to your risk profile, portfolio and goal.",
    goalAria: "Basket goal",
    reviewSchedule: "Review schedule",
    lastReview: "Last review",
    lastChange: "Last composition change",
    riskFit: "risk profile fit",
    basketRisk: "Basket risk",
    volatility: "20-day volatility",
    diversification: "Diversification",
    allocation: "Allocation",
    simulation: "Historical simulation",
    netReturn: "After costs",
    days: "days",
    total: "Suggested total",
    assets: "assets",
    details: "View details",
    openDetails: "open basket details",
    classes: "classes",
    sectors: "sectors",
  },
} as const;

const RISK_LABELS = {
  tr: { LOW: "Düşük", MEDIUM: "Orta", HIGH: "Yüksek" },
  en: { LOW: "Low", MEDIUM: "Medium", HIGH: "High" },
} as const;

const STATUS_LABELS = {
  tr: { SUFFICIENT: "Yeterli veri", LIMITED: "Sınırlı veri", INSUFFICIENT: "Yetersiz veri" },
  en: { SUFFICIENT: "Sufficient data", LIMITED: "Limited data", INSUFFICIENT: "Insufficient data" },
} as const;

const STRATEGY_COPY = {
  CORE: {
    tr: { label: "Dengeli Çekirdek", description: "Hedef puanı, risk ve çeşitlendirmeyi birlikte dengeler." },
    en: { label: "Balanced Core", description: "Balances goal score, risk and diversification." },
  },
  DEFENSIVE: {
    tr: { label: "Risk Kontrollü", description: "Daha düşük oynaklık ve korelasyona öncelik verir." },
    en: { label: "Risk Controlled", description: "Prioritizes lower volatility and correlation." },
  },
  OPPORTUNITY: {
    tr: { label: "Getiri Potansiyeli", description: "Hedefe uygun güçlü performansı öne çıkarırken risk sınırlarını korur." },
    en: { label: "Return Potential", description: "Highlights strong goal-aligned performance while preserving risk limits." },
  },
} as const;

const BASKET_TITLES: Record<IdleCashSuggestion["goal"], Record<Language, string[]>> = {
  LONG_TERM: { tr: ["İstikrarlı Birikim", "Birikim Alternatifi", "Geniş Perspektif"], en: ["Stable Accumulation", "Accumulation Alternative", "Broad Perspective"] },
  GROWTH: { tr: ["Güçlü Büyüme", "Büyüme Alternatifi", "Geniş Potansiyel"], en: ["Strong Growth", "Growth Alternative", "Broad Potential"] },
  MOMENTUM: { tr: ["Güçlü Momentum", "Trend Takibi", "Momentum Alternatifi"], en: ["Strong Momentum", "Trend Following", "Momentum Alternative"] },
  LOW_VOLATILITY: { tr: ["Sakin Seyir", "Dengeli Savunma", "Düşük Dalgalanma"], en: ["Calm Path", "Balanced Defense", "Low Volatility"] },
};

function optionTitle(option: IdleCashBasketOption, language: Language) {
  const index = option.strategy_key === "CORE" ? 0 : option.strategy_key === "DEFENSIVE" ? 1 : 2;
  return BASKET_TITLES[option.suggestion.goal][language][index];
}

function evaluationFrequency(goal: IdleCashSuggestion["goal"], language: Language) {
  const labels = {
    LONG_TERM: { tr: "Haftalık değerlendirme · en erken aylık üyelik değişimi", en: "Weekly review · composition changes no earlier than monthly" },
    GROWTH: { tr: "Haftalık değerlendirme · en az iki haftalık kalma süresi", en: "Weekly review · minimum two-week holding period" },
    MOMENTUM: { tr: "6 saatte bir değerlendirme · günlük üyelik değişimi", en: "Review every 6 hours · daily composition changes" },
    LOW_VOLATILITY: { tr: "Günlük değerlendirme · oynaklık artışı iki kontrolde doğrulanır", en: "Daily review · volatility increases require two confirmations" },
  };
  return labels[goal][language];
}

export function BasketSuggestionPanel({ onReady }: { onReady?: () => void }) {
  const { language } = useLanguage();
  const text = PANEL_COPY[language];
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const [goal, setGoal] = useState<IdleCashSuggestion["goal"]>("LONG_TERM");
  const [selectedBasket, setSelectedBasket] = useState<IdleCashBasketOption | null>(null);
  const loader = useCallback(() => getIdleCashBasketCatalog(goal), [goal]);
  const state = useAsyncData(loader, [loader]);

  useEffect(() => {
    if (!state.loading) onReady?.();
  }, [state.loading, onReady]);

  if (state.loading && !state.data) {
    return <LoadingState label={text.loading} />;
  }

  if (!state.data) {
    return (
      <ErrorState
        message={language === "tr" ? state.error ?? text.error : text.error}
        onRetry={state.refetch}
      />
    );
  }

  return (
    <section className="relative overflow-hidden rounded-2xl border app-card p-5">
      <div className={state.loading ? "pointer-events-none blur-sm" : ""}>
        <div className="mb-5">
          <div>
            <p className="text-sm font-semibold text-[var(--color-primary)]">
              {text.eyebrow}
            </p>
            <h2 className="mt-1 text-xl font-bold app-heading">
              {text.title}
            </h2>
            <p className="mt-1 text-sm app-muted">
              {text.intro}
            </p>
          </div>
        </div>

        <div className="mb-5 flex flex-wrap gap-2" role="group" aria-label={text.goalAria}>
          {GOALS.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setGoal(item.key)}
              aria-pressed={goal === item.key}
              className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${
                goal === item.key ? "bg-[#454466] text-white" : "app-muted hover:bg-black/5"
              }`}
            >
              {item.label[language]}
            </button>
          ))}
        </div>

        <p className="mb-5 text-sm app-muted">
          {GOALS.find((item) => item.key === goal)?.description[language]}
        </p>

        {(state.data.stale_asset_count > 0 || state.data.insufficient_history_asset_count > 0) && (
          <p className="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {language === "tr"
              ? `Veri kalite kontrolü: ${state.data.stale_asset_count} varlık güncel olmayan fiyat, ${state.data.insufficient_history_asset_count} varlık yetersiz oynaklık geçmişi nedeniyle işaretlendi.`
              : `Data quality check: ${state.data.stale_asset_count} assets have stale prices and ${state.data.insufficient_history_asset_count} assets have insufficient volatility history.`}
          </p>
        )}

        <div className="mb-5 grid gap-3 rounded-xl bg-[var(--color-soft)] p-4 text-sm md:grid-cols-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide app-muted">{text.reviewSchedule}</p>
            <p className="mt-1 font-semibold app-heading">{evaluationFrequency(goal, language)}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide app-muted">{text.lastReview}</p>
            <p className="mt-1 font-semibold app-heading">{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(state.data.evaluated_at))}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide app-muted">{text.lastChange}</p>
            <p className="mt-1 font-semibold app-heading">{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(state.data.last_changed_at))}</p>
          </div>
          <p className="md:col-span-3 app-muted">
            {language === "tr"
              ? state.data.stability_note
              : state.data.membership_changed
                ? "The basket composition was updated after the change conditions were confirmed."
                : "Prices and quantities were updated; the composition was retained because the change threshold was not exceeded."}
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {state.data.options.map((option) => (
            <BasketCard key={option.id} option={option} language={language} onOpen={() => setSelectedBasket(option)} />
          ))}
        </div>
      </div>

      {state.loading && (
        <div className="absolute inset-0 grid place-items-center bg-white/20 backdrop-blur-sm">
          <span className="h-8 w-8 animate-spin rounded-full border-[3px] border-slate-300 border-t-[var(--color-primary)]" />
        </div>
      )}

      <IdleCashSuggestionModal
        suggestion={selectedBasket?.suggestion ?? null}
        title={selectedBasket ? optionTitle(selectedBasket, language) : undefined}
        subtitle={selectedBasket ? STRATEGY_COPY[selectedBasket.strategy_key][language].description : undefined}
        strategyLabel={selectedBasket ? STRATEGY_COPY[selectedBasket.strategy_key][language].label : undefined}
        metrics={selectedBasket?.metrics}
        backtest={selectedBasket?.backtest}
        onClose={() => setSelectedBasket(null)}
      />
    </section>
  );
}

function BasketCard({ option, language, onOpen }: { option: IdleCashBasketOption; language: Language; onOpen: () => void }) {
  const suggestion = option.suggestion;
  const text = PANEL_COPY[language];
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const moneyFormatter = new Intl.NumberFormat(locale, { style: "currency", currency: "TRY", maximumFractionDigits: 0 });
  const title = optionTitle(option, language);
  const strategy = STRATEGY_COPY[option.strategy_key][language];

  return (
    <button
      type="button"
      onClick={onOpen}
      className="group flex h-full flex-col rounded-2xl border p-5 text-left transition hover:-translate-y-0.5 hover:border-[var(--color-primary)] hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
      aria-label={`${title}: ${text.openDetails}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-primary)]">
            {RISK_LABELS[language][suggestion.risk_profile]} {text.riskFit}
          </p>
          <h3 className="mt-1 text-lg font-bold app-heading">{title}</h3>
          <span className="mt-2 inline-flex rounded-full bg-[var(--color-soft)] px-3 py-1 text-xs font-semibold app-heading">
            {strategy.label}
          </span>
        </div>
        <span className="text-xl app-muted transition group-hover:translate-x-1" aria-hidden="true">
          →
        </span>
      </div>

      <p className="mt-3 min-h-10 text-sm app-muted">{strategy.description}</p>

      <div className="mt-4 flex flex-wrap gap-2">
        {suggestion.items.map((item) => (
          <span key={item.asset_id} className="rounded-md bg-[var(--color-soft)] px-2 py-1 text-xs font-bold">
            {item.symbol}
          </span>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-[var(--color-soft)] p-2">
          <p className="app-muted">{text.basketRisk}</p>
          <p className="mt-1 font-semibold app-heading">{RISK_LABELS[language][option.metrics.risk_level]}</p>
        </div>
        <div className="rounded-lg bg-[var(--color-soft)] p-2">
          <p className="app-muted">{text.volatility}</p>
          <p className="mt-1 font-semibold app-heading">%{option.metrics.expected_volatility_20d_pct.toLocaleString(locale)}</p>
        </div>
        <div className="rounded-lg bg-[var(--color-soft)] p-2">
          <p className="app-muted">{text.diversification}</p>
          <p className="mt-1 font-semibold app-heading">{option.metrics.diversification_score.toLocaleString(locale)} / 100</p>
        </div>
        <div className="rounded-lg bg-[var(--color-soft)] p-2">
          <p className="app-muted">{text.allocation}</p>
          <p className="mt-1 font-semibold app-heading">{option.metrics.asset_class_count} {text.classes} · {option.metrics.sector_count} {text.sectors}</p>
        </div>
      </div>

      <div className="mt-3 rounded-lg border p-3 text-xs">
        <div className="flex items-center justify-between gap-2">
          <span className="app-muted">{text.simulation}</span>
          <span className="font-semibold app-heading">
            {STATUS_LABELS[language][option.backtest.status]}
          </span>
        </div>
        {option.backtest.net_return_pct != null && (
          <p className="mt-2 font-semibold app-heading">
            {text.netReturn} %{option.backtest.net_return_pct.toLocaleString(locale, { maximumFractionDigits: 2 })}
            <span className="ml-2 font-normal app-muted">
              · {option.backtest.observation_count} {text.days}
            </span>
          </p>
        )}
      </div>

      <div className="mt-auto flex items-end justify-between gap-3 border-t pt-4 text-sm">
        <div>
          <p className="app-muted">{text.total}</p>
          <p className="mt-1 font-bold app-heading">{moneyFormatter.format(suggestion.estimated_total)}</p>
        </div>
        <span className="font-semibold text-[var(--color-primary)]">
          {suggestion.items.length} {text.assets} · {text.details}
        </span>
      </div>
    </button>
  );
}
