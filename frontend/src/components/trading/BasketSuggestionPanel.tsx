"use client";

import { useCallback, useEffect, useState } from "react";
import { IdleCashSuggestionModal } from "../chat/IdleCashSuggestionModal";
import { ErrorState } from "../feedback/ErrorState";
import { LoadingState } from "../feedback/LoadingState";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { IdleCashBasketOption, IdleCashSuggestion } from "../../models/chat";
import { getIdleCashBasketCatalog } from "../../services/recommendationService";

const GOALS: Array<{
  key: IdleCashSuggestion["goal"];
  label: string;
  description: string;
}> = [
  {
    key: "LONG_TERM",
    label: "Uzun Vadeli Birikim",
    description: "Uzun dönem performansını ve daha istikrarlı fiyat hareketlerini öne çıkarır.",
  },
  {
    key: "GROWTH",
    label: "Büyüme Odaklı",
    description: "Orta ve uzun vadede güçlü performans gösteren varlıklara ağırlık verir.",
  },
  {
    key: "MOMENTUM",
    label: "Momentum",
    description: "Günlük ve haftalık yükseliş eğilimi güçlü varlıkları öne çıkarır.",
  },
  {
    key: "LOW_VOLATILITY",
    label: "Düşük Oynaklık",
    description: "Fiyat hareketleri görece daha sınırlı varlıklarla dalgalanmayı azaltmayı hedefler.",
  },
];

export function BasketSuggestionPanel({ onReady }: { onReady?: () => void }) {
  const [goal, setGoal] = useState<IdleCashSuggestion["goal"]>("LONG_TERM");
  const [selectedBasket, setSelectedBasket] = useState<IdleCashBasketOption | null>(null);
  const loader = useCallback(() => getIdleCashBasketCatalog(goal), [goal]);
  const state = useAsyncData(loader, [loader]);

  useEffect(() => {
    if (!state.loading) onReady?.();
  }, [state.loading, onReady]);

  if (state.loading && !state.data) {
    return <LoadingState label="Sepet önerisi hazırlanıyor" />;
  }

  if (!state.data) {
    return (
      <ErrorState
        message={state.error ?? "Sepet önerisi oluşturulamadı."}
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
              Kişiselleştirilmiş yatırım sepeti
            </p>
            <h2 className="mt-1 text-xl font-bold app-heading">
              Atıl bakiye için yatırım sepeti alternatifleri
            </h2>
            <p className="mt-1 text-sm app-muted">
              Uygulamadaki tüm varlıklar taranır; bakiyen risk profilin, portföyün ve hedefinle uyumlu olanlara dağıtılır.
            </p>
          </div>
        </div>

        <div className="mb-5 flex flex-wrap gap-2" role="group" aria-label="Sepet hedefi">
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
              {item.label}
            </button>
          ))}
        </div>

        <p className="mb-5 text-sm app-muted">
          {GOALS.find((item) => item.key === goal)?.description}
        </p>

        {(state.data.stale_asset_count > 0 || state.data.insufficient_history_asset_count > 0) && (
          <p className="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Veri kalite kontrolü: {state.data.stale_asset_count} varlık güncel olmayan fiyat,
            {" "}{state.data.insufficient_history_asset_count} varlık yetersiz oynaklık geçmişi nedeniyle işaretlendi.
          </p>
        )}

        <div className="mb-5 grid gap-3 rounded-xl bg-[var(--color-soft)] p-4 text-sm md:grid-cols-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide app-muted">Değerlendirme düzeni</p>
            <p className="mt-1 font-semibold app-heading">{state.data.evaluation_frequency}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide app-muted">Son değerlendirme</p>
            <p className="mt-1 font-semibold app-heading">{dateTimeFormatter.format(new Date(state.data.evaluated_at))}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide app-muted">Son içerik değişimi</p>
            <p className="mt-1 font-semibold app-heading">{dateTimeFormatter.format(new Date(state.data.last_changed_at))}</p>
          </div>
          <p className="md:col-span-3 app-muted">{state.data.stability_note}</p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {state.data.options.map((option) => (
            <BasketCard key={option.id} option={option} onOpen={() => setSelectedBasket(option)} />
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
        title={selectedBasket?.title}
        subtitle={selectedBasket?.summary}
        strategyLabel={selectedBasket?.strategy_label}
        metrics={selectedBasket?.metrics}
        backtest={selectedBasket?.backtest}
        onClose={() => setSelectedBasket(null)}
      />
    </section>
  );
}

const moneyFormatter = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 0,
});

const dateTimeFormatter = new Intl.DateTimeFormat("tr-TR", {
  dateStyle: "medium",
  timeStyle: "short",
});

const riskLabels = { LOW: "Düşük", MEDIUM: "Orta", HIGH: "Yüksek" } as const;
const basketRiskLabels = { LOW: "Düşük", MEDIUM: "Orta", HIGH: "Yüksek" } as const;

function BasketCard({ option, onOpen }: { option: IdleCashBasketOption; onOpen: () => void }) {
  const suggestion = option.suggestion;

  return (
    <button
      type="button"
      onClick={onOpen}
      className="group flex h-full flex-col rounded-2xl border p-5 text-left transition hover:-translate-y-0.5 hover:border-[var(--color-primary)] hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
      aria-label={`${option.title} sepetinin detaylarını aç`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-primary)]">
            {riskLabels[suggestion.risk_profile]} risk profiline uygun
          </p>
          <h3 className="mt-1 text-lg font-bold app-heading">{option.title}</h3>
          <span className="mt-2 inline-flex rounded-full bg-[var(--color-soft)] px-3 py-1 text-xs font-semibold app-heading">
            {option.strategy_label}
          </span>
        </div>
        <span className="text-xl app-muted transition group-hover:translate-x-1" aria-hidden="true">
          →
        </span>
      </div>

      <p className="mt-3 min-h-10 text-sm app-muted">{option.summary}</p>

      <div className="mt-4 flex flex-wrap gap-2">
        {suggestion.items.map((item) => (
          <span key={item.asset_id} className="rounded-md bg-[var(--color-soft)] px-2 py-1 text-xs font-bold">
            {item.symbol}
          </span>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-[var(--color-soft)] p-2">
          <p className="app-muted">Sepet riski</p>
          <p className="mt-1 font-semibold app-heading">{basketRiskLabels[option.metrics.risk_level]}</p>
        </div>
        <div className="rounded-lg bg-[var(--color-soft)] p-2">
          <p className="app-muted">20 günlük oynaklık</p>
          <p className="mt-1 font-semibold app-heading">%{option.metrics.expected_volatility_20d_pct.toLocaleString("tr-TR")}</p>
        </div>
        <div className="rounded-lg bg-[var(--color-soft)] p-2">
          <p className="app-muted">Çeşitlendirme</p>
          <p className="mt-1 font-semibold app-heading">{option.metrics.diversification_score.toLocaleString("tr-TR")} / 100</p>
        </div>
        <div className="rounded-lg bg-[var(--color-soft)] p-2">
          <p className="app-muted">Dağılım</p>
          <p className="mt-1 font-semibold app-heading">{option.metrics.asset_class_count} sınıf · {option.metrics.sector_count} sektör</p>
        </div>
      </div>

      <div className="mt-3 rounded-lg border p-3 text-xs">
        <div className="flex items-center justify-between gap-2">
          <span className="app-muted">Geçmiş simülasyon</span>
          <span className="font-semibold app-heading">
            {option.backtest.status === "INSUFFICIENT"
              ? "Yetersiz veri"
              : option.backtest.status === "LIMITED" ? "Sınırlı veri" : "Yeterli veri"}
          </span>
        </div>
        {option.backtest.net_return_pct != null && (
          <p className="mt-2 font-semibold app-heading">
            Maliyet sonrası %{option.backtest.net_return_pct.toLocaleString("tr-TR", { maximumFractionDigits: 2 })}
            <span className="ml-2 font-normal app-muted">
              · {option.backtest.observation_count} gün
            </span>
          </p>
        )}
      </div>

      <div className="mt-auto flex items-end justify-between gap-3 border-t pt-4 text-sm">
        <div>
          <p className="app-muted">Önerilen toplam</p>
          <p className="mt-1 font-bold app-heading">{moneyFormatter.format(suggestion.estimated_total)}</p>
        </div>
        <span className="font-semibold text-[var(--color-primary)]">
          {suggestion.items.length} varlık · Detayları gör
        </span>
      </div>
    </button>
  );
}
