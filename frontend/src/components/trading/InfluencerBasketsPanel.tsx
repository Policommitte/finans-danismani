"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useLanguage } from "../../contexts/LanguageContext";
import { useAsyncData } from "../../hooks/useAsyncData";
import { createBasketMarketOrders, previewPercentageBasket } from "../../services/tradingService";
import {
  buildInfluencerBasketPlan,
  INFLUENCER_BASKETS,
  type InfluencerBasketPlan,
} from "./influencerBaskets";

type Language = "tr" | "en";

const COPY = {
  tr: {
    loading: "Fenomen sepetleri hazırlanıyor",
    error: "Fenomen sepetleri yüklenemedi.",
    title: "Fenomen Sepetleri",
    intro: "Sepetlerdeki hedef yüzdeler, kullanılabilir likit bakiyenize göre tutarlara dönüştürülerek sanal alım işlemleri oluşturulur.",
    disclaimer: "Kurgusal demo: Bu dağılımlar platform tarafından oluşturulmuştur. İsmi geçen kişinin gerçek görüşü veya önerisi değildir; kişiyle herhangi bir bağlantı ya da onay ilişkisi yoktur. Yatırım tavsiyesi değildir.",
    balance: "Kullanılabilir likit bakiye",
    fictional: "Kurgusal demo",
    targetAllocation: "Hedef dağılım",
    review: "Sepeti incele",
    estimatedOrders: "Tahmini emir toplamı",
    remaining: "Tahmini kalan",
    unavailable: "Fiyatı bulunamayan varlıklar",
    unaffordable: "Ayrılan tutarla en az bir adet alınamayan varlıklar",
    close: "Kapat",
    use: "Likit bakiyeyle uygula",
    confirmTitle: "Sanal alım emirleri oluşturulsun mu?",
    confirmBody: "Hedef yüzdeler tam adet, komisyon ve piyasa fiyat tamponu dikkate alınarak sanal emir adedine çevrildi.",
    cancel: "Vazgeç",
    confirm: "Onayla ve emirleri oluştur",
    submitting: "Emirler oluşturuluyor…",
    success: (count: number) => `${count} sanal alım emri başarıyla oluşturuldu.`,
    failed: "Sepet emirleri oluşturulamadı.",
    quantity: "adet",
    bufferNote: "%2 fiyat tamponu ve %0,15 tahmini komisyon ayrıldığı için tam adet yuvarlamasından sonra bir miktar nakit kalabilir.",
  },
  en: {
    loading: "Preparing public-figure baskets",
    error: "Public-figure baskets could not be loaded.",
    title: "Public-Figure Baskets",
    intro: "Each basket's target weights are converted into virtual purchase amounts based on your available cash balance.",
    disclaimer: "Fictional demo: These allocations were created by the platform. They are not the named person's real views or recommendations, and there is no affiliation or endorsement. This is not investment advice.",
    balance: "Available cash balance",
    fictional: "Fictional demo",
    targetAllocation: "Target allocation",
    review: "Review basket",
    estimatedOrders: "Estimated order total",
    remaining: "Estimated remaining",
    unavailable: "Assets without a usable price",
    unaffordable: "Assets whose allocation cannot buy one unit",
    close: "Close",
    use: "Apply to available cash",
    confirmTitle: "Create virtual buy orders?",
    confirmBody: "Target weights were converted into virtual order quantities after whole-unit, commission and market-price buffer rules.",
    cancel: "Cancel",
    confirm: "Confirm and create orders",
    submitting: "Creating orders…",
    success: (count: number) => `${count} virtual buy orders were created successfully.`,
    failed: "Basket orders could not be created.",
    quantity: "units",
    bufferNote: "A small cash remainder may remain after whole-unit rounding because a 2% price buffer and 0.15% estimated commission are reserved.",
  },
} as const;

export function InfluencerBasketsPanel({ onReady }: { onReady?: () => void }) {
  const { language } = useLanguage();
  const text = COPY[language];
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const money = useMemo(
    () => new Intl.NumberFormat(locale, { style: "currency", currency: "TRY", maximumFractionDigits: 0 }),
    [locale],
  );
  const loader = useCallback(async () => {
    const previews = await Promise.all(
      INFLUENCER_BASKETS.map((basket) =>
        previewPercentageBasket(
          basket.allocations.map((item) => ({
            symbol: item.symbol,
            weight_pct: item.weightPct,
          })),
        ),
      ),
    );
    return previews.map((preview, index) =>
      buildInfluencerBasketPlan(INFLUENCER_BASKETS[index], preview),
    );
  }, []);
  const state = useAsyncData(loader, [loader]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!state.loading) onReady?.();
  }, [state.loading, onReady]);

  const plans = state.data ?? [];
  const selectedPlan = plans.find((plan) => plan.basket.id === selectedId) ?? null;

  if (state.loading && !state.data) {
    return (
      <div className="grid min-h-72 place-items-center rounded-2xl border app-card" role="status">
        <span className="app-muted">{text.loading}</span>
      </div>
    );
  }

  if (!state.data) {
    return (
      <div className="rounded-2xl border app-card p-6">
        <p className="app-danger-box rounded-lg px-4 py-3 text-sm">{state.error ?? text.error}</p>
        <button type="button" className="mt-4 rounded-lg app-primary px-4 py-2 font-semibold" onClick={() => void state.refetch()}>
          {language === "tr" ? "Tekrar dene" : "Retry"}
        </button>
      </div>
    );
  }

  return (
    <section className="rounded-2xl border app-card p-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div className="max-w-3xl">
          <h2 className="text-xl font-bold app-heading">{text.title}</h2>
          <p className="mt-1 text-sm app-muted">{text.intro}</p>
        </div>
        <div className="shrink-0 rounded-xl bg-[var(--color-soft)] px-4 py-3 text-sm">
          <p className="app-muted">{text.balance}</p>
          <p className="mt-1 text-lg font-bold app-heading">{money.format(plans[0]?.availableBalance ?? 0)}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        {plans.map((plan) => (
          <InfluencerBasketCard
            key={plan.basket.id}
            plan={plan}
            language={language}
            onSelect={() => setSelectedId(plan.basket.id)}
          />
        ))}
      </div>

      <InfluencerBasketDialog
        plan={selectedPlan}
        language={language}
        onClose={() => setSelectedId(null)}
        onPurchased={() => state.refresh()}
      />
    </section>
  );
}

function InfluencerBasketCard({
  plan,
  language,
  onSelect,
}: {
  plan: InfluencerBasketPlan;
  language: Language;
  onSelect: () => void;
}) {
  const text = COPY[language];
  return (
    <article className="flex h-full flex-col rounded-2xl border p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold app-heading">{plan.basket.figureName}</h3>
          {plan.basket.role && (
            <p className="mt-1 text-sm font-medium app-muted">{plan.basket.role[language]}</p>
          )}
        </div>
        <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full border-2 border-white bg-[var(--color-soft)] shadow-sm">
          {plan.basket.photoScale ? (
            <div
              role="img"
              aria-label={`${plan.basket.figureName} portresi`}
              className="h-full w-full bg-no-repeat"
              style={{
                backgroundImage: `url("${plan.basket.photoSrc}")`,
                backgroundPosition: plan.basket.photoFocus,
                backgroundSize: `${plan.basket.photoScale * 100}%`,
              }}
            />
          ) : (
            <Image
              src={plan.basket.photoSrc}
              alt={`${plan.basket.figureName} portresi`}
              fill
              sizes="56px"
              className="object-cover object-center"
            />
          )}
        </div>
      </div>
      <div className="mt-5 space-y-3" aria-label={text.targetAllocation}>
        {plan.basket.allocations.map((allocation) => (
          <div key={allocation.symbol}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="font-semibold app-heading">{allocation.symbol}</span>
              <span className="font-bold text-[var(--color-primary)]">%{allocation.weightPct}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-[var(--color-border-soft)]">
              <div className="h-full rounded-full bg-[#454466]" style={{ width: `${allocation.weightPct}%` }} />
            </div>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={onSelect}
        className="mt-6 w-full rounded-xl app-primary px-4 py-3 font-semibold"
      >
        {text.review}
      </button>
    </article>
  );
}

function InfluencerBasketDialog({
  plan,
  language,
  onClose,
  onPurchased,
}: {
  plan: InfluencerBasketPlan | null;
  language: Language;
  onClose: () => void;
  onPurchased: () => Promise<void>;
}) {
  const text = COPY[language];
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const money = new Intl.NumberFormat(locale, { style: "currency", currency: "TRY", maximumFractionDigits: 2 });
  const quantity = new Intl.NumberFormat(locale, { maximumFractionDigits: 6 });
  const [mounted, setMounted] = useState(false);
  const [step, setStep] = useState<"idle" | "confirm" | "submitting" | "success">("idle");
  const [error, setError] = useState<string | null>(null);
  const [createdCount, setCreatedCount] = useState(0);

  useEffect(() => setMounted(true), []);
  useEffect(() => {
    setStep("idle");
    setError(null);
    setCreatedCount(0);
  }, [plan?.basket.id]);
  useEffect(() => {
    if (!plan) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && step !== "submitting") onClose();
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [plan, step, onClose]);

  if (!mounted || !plan) return null;

  async function submitOrders() {
    if (!plan || plan.items.length === 0) return;
    setStep("submitting");
    setError(null);
    try {
      const orders = await createBasketMarketOrders(
        plan.items.map((item) => ({ symbol: item.symbol, quantity: item.quantity })),
      );
      setCreatedCount(orders.length);
      setStep("success");
      await onPurchased();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : text.failed);
      setStep("confirm");
    }
  }

  const unavailable = [...plan.missingSymbols, ...plan.skippedSymbols];
  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-[2px]"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && step !== "submitting") onClose();
      }}
    >
      <section role="dialog" aria-modal="true" aria-labelledby="influencer-basket-title" className="flex max-h-[calc(100vh-2rem)] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border app-card shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b px-6 py-5">
          <div>
            <span className="inline-flex rounded-full bg-[var(--color-soft)] px-3 py-1 text-xs font-semibold text-[var(--color-primary)]">{text.fictional}</span>
            <h2 id="influencer-basket-title" className="mt-2 text-2xl font-bold app-heading">{plan.basket.figureName}</h2>
            <p className="font-semibold text-[var(--color-primary)]">{plan.basket.title[language]}</p>
          </div>
          <button type="button" className="rounded-lg px-3 py-1 text-2xl app-muted hover:bg-black/5" aria-label={text.close} onClick={onClose} disabled={step === "submitting"}>×</button>
        </header>

        <div className="overflow-y-auto px-6 py-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <Summary label={text.balance} value={money.format(plan.availableBalance)} />
            <Summary label={text.estimatedOrders} value={money.format(plan.estimatedReserve)} />
            <Summary label={text.remaining} value={money.format(plan.remainingBalance)} />
          </div>

          <div className="mt-5 overflow-hidden rounded-xl border">
            {plan.items.map((item) => (
              <div key={item.symbol} className="grid grid-cols-[1fr_auto] gap-4 border-b px-4 py-3 last:border-b-0 sm:grid-cols-[1fr_100px_160px] sm:items-center">
                <div>
                  <p className="font-bold app-heading">{item.symbol} <span className="font-normal app-muted">· {item.name}</span></p>
                  <p className="mt-1 text-xs app-muted">{quantity.format(item.quantity)} {text.quantity} · {money.format(item.quotedPriceTry)} / {text.quantity}</p>
                </div>
                <p className="text-right font-bold text-[var(--color-primary)]">%{item.weightPct}</p>
                <p className="col-span-2 text-right font-semibold app-heading sm:col-span-1">{money.format(item.estimatedGross)}</p>
              </div>
            ))}
          </div>

          {unavailable.length > 0 && (
            <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              {plan.missingSymbols.length > 0 && `${text.unavailable}: ${plan.missingSymbols.join(", ")}. `}
              {plan.skippedSymbols.length > 0 && `${text.unaffordable}: ${plan.skippedSymbols.join(", ")}.`}
            </p>
          )}
          <p className="mt-4 text-xs leading-relaxed app-muted">{text.bufferNote}</p>
          <p className="mt-3 rounded-lg bg-[var(--color-soft)] px-4 py-3 text-xs leading-relaxed app-muted">{text.disclaimer}</p>

          {step === "confirm" && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <p className="font-semibold">{text.confirmTitle}</p>
              <p className="mt-1 text-xs">{text.confirmBody}</p>
            </div>
          )}
          {step === "success" && (
            <p className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-900" role="status">{text.success(createdCount)}</p>
          )}
          {error && <p className="mt-4 rounded-xl app-danger-box p-4 text-sm" role="alert">{error}</p>}
        </div>

        <footer className="flex flex-col-reverse gap-3 border-t px-6 py-4 sm:flex-row sm:justify-end">
          <button type="button" className="rounded-lg border px-5 py-3 font-semibold" onClick={step === "confirm" ? () => setStep("idle") : onClose} disabled={step === "submitting"}>
            {step === "confirm" ? text.cancel : text.close}
          </button>
          {step === "idle" && (
            <button type="button" className="rounded-lg app-primary px-5 py-3 font-semibold disabled:opacity-50" onClick={() => setStep("confirm")} disabled={plan.items.length === 0}>
              {text.use}
            </button>
          )}
          {step === "confirm" && (
            <button type="button" className="rounded-lg app-primary px-5 py-3 font-semibold" onClick={() => void submitOrders()}>{text.confirm}</button>
          )}
          {step === "submitting" && <button type="button" className="rounded-lg app-primary px-5 py-3 font-semibold opacity-70" disabled>{text.submitting}</button>}
        </footer>
      </section>
    </div>,
    document.body,
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-[var(--color-soft)] p-4">
      <p className="text-xs app-muted">{label}</p>
      <p className="mt-1 font-bold app-heading">{value}</p>
    </div>
  );
}
