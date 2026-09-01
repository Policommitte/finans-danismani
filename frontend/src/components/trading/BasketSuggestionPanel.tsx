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
        <div className="mb-5 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
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
          <button
            type="button"
            onClick={() => void state.refetch()}
            className="rounded-lg border px-4 py-2 text-sm font-semibold hover:bg-black/5"
          >
            Önerileri güncelle
          </button>
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
          <span className="ml-2 font-semibold text-[var(--color-primary)]">
            {state.data.universe_size} varlık analiz edildi · {state.data.eligible_asset_count} işlem yapılabilir aday
          </span>
        </p>

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

const riskLabels = { LOW: "Düşük", MEDIUM: "Orta", HIGH: "Yüksek" } as const;

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
