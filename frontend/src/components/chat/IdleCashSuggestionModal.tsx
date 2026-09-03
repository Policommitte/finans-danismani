"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useLanguage } from "../../contexts/LanguageContext";
import type { IdleCashSuggestion } from "../../models/chat";
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

export function IdleCashSuggestionModal({
  suggestion,
  onClose,
  title,
  strategyLabel,
}: {
  suggestion: IdleCashSuggestion | null;
  onClose: () => void;
  title?: string;
  strategyLabel?: string;
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
            <h2 id="idle-cash-title" className="text-2xl font-bold">
              {title ?? (language === "tr"
                ? suggestion.mode === "basket" ? "Atıl bakiye için yatırım sepeti" : "Bakiyeye uygun tek varlık"
                : suggestion.mode === "basket" ? "Investment basket for available cash" : "Single asset for available cash")}
            </h2>
            {strategyLabel && (
              <span className="mt-2 inline-flex rounded-full bg-[var(--color-soft)] px-3 py-1 text-xs font-semibold">
                {strategyLabel}
              </span>
            )}
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
          <IdleCashSuggestionContent suggestion={suggestion} />
        </div>

        <footer className="border-t px-6 py-4">
          {orderStep === "confirm" && (
            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <p className="font-semibold">
                {language === "tr"
                  ? `Sepetteki ${suggestion.items.length} varlık için alış emri oluşturulsun mu? Tahmini toplam ${tryFormatter.format(suggestion.estimated_total)}.`
                  : `Create buy orders for the ${suggestion.items.length} assets in this basket? Estimated total: ${tryFormatter.format(suggestion.estimated_total)}.`}
              </p>
            </div>
          )}
          {orderStep === "success" && (
            <p className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-900" role="status">
              {language === "tr"
                ? `${createdOrderCount} sepet emri oluşturuldu.`
                : `${createdOrderCount} basket orders created.`}
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
}: {
  suggestion: IdleCashSuggestion;
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
              </div>
            </div>
          </article>
        ))}
      </div>

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

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-[var(--color-soft)] p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-muted)]">{label}</p>
      <p className="mt-1 text-lg font-bold">{value}</p>
    </div>
  );
}
