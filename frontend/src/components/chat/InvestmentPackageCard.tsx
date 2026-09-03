"use client";

import { useState } from "react";
import { useLanguage } from "../../contexts/LanguageContext";
import type { InvestmentPackage } from "../../models/chat";
import { createBasketMarketOrders } from "../../services/tradingService";
import { formatBudget } from "../../utils/budgetInput";

const CARD_COPY = {
  tr: {
    budget: "Bütçe",
    invested: "Yatırılacak",
    remaining: "Kalan",
    risk: "Risk",
    volatility: "Beklenti oynaklık (20g)",
    diversification: "Çeşitlendirme",
    buy: "Paketi satın al",
    buying: "Emirler oluşturuluyor…",
    bought: "Paket satın alındı",
    insufficient: (balance: string) => `Nakit bakiyeniz (${balance}) bu bütçe için yetersiz.`,
    failed: "Paket satın alınamadı.",
    riskLevels: { LOW: "Düşük", MEDIUM: "Orta", HIGH: "Yüksek" },
    quantity: "adet",
  },
  en: {
    budget: "Budget",
    invested: "To invest",
    remaining: "Left over",
    risk: "Risk",
    volatility: "Expected volatility (20d)",
    diversification: "Diversification",
    buy: "Buy this package",
    buying: "Creating orders…",
    bought: "Package purchased",
    insufficient: (balance: string) => `Your cash balance (${balance}) is not enough for this budget.`,
    failed: "The package could not be purchased.",
    riskLevels: { LOW: "Low", MEDIUM: "Medium", HIGH: "High" },
    quantity: "units",
  },
} as const;

const riskBadgeClasses = {
  LOW: "bg-emerald-50 text-emerald-800",
  MEDIUM: "bg-amber-50 text-amber-800",
  HIGH: "bg-rose-50 text-rose-800",
} as const;

/** Compact package card rendered inside an assistant chat bubble. */
export function InvestmentPackageCard({
  investmentPackage,
  onPurchased,
}: {
  investmentPackage: InvestmentPackage;
  onPurchased?: (orderCount: number) => void;
}) {
  const { language } = useLanguage();
  const copy = CARD_COPY[language] ?? CARD_COPY.tr;
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const [purchaseState, setPurchaseState] = useState<"idle" | "submitting" | "done">("idle");
  const [purchaseError, setPurchaseError] = useState<string | null>(null);

  const { suggestion, metrics } = investmentPackage;
  const quantityFormatter = new Intl.NumberFormat(locale, { maximumFractionDigits: 6 });

  async function purchasePackage() {
    setPurchaseState("submitting");
    setPurchaseError(null);
    try {
      const orders = await createBasketMarketOrders(
        suggestion.items.map((item) => ({ symbol: item.symbol, quantity: item.quantity })),
      );
      setPurchaseState("done");
      onPurchased?.(orders.length);
    } catch (error) {
      setPurchaseError(error instanceof Error ? error.message : copy.failed);
      setPurchaseState("idle");
    }
  }

  const disabled = investmentPackage.exceeds_balance || purchaseState !== "idle";

  return (
    <div className="mt-2.5 overflow-hidden rounded-lg border app-border bg-[var(--color-surface)] text-[var(--color-text)]">
      <div className="flex items-start justify-between gap-2 px-3 py-2.5">
        <div>
          <div className="text-sm font-semibold">{investmentPackage.title}</div>
          <div className="text-[11px] app-muted">
            {investmentPackage.horizon_label} · {investmentPackage.goal_label} · {investmentPackage.strategy_label}
          </div>
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${riskBadgeClasses[metrics.risk_level]}`}>
          {copy.risk}: {copy.riskLevels[metrics.risk_level]}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-px border-y app-border bg-[var(--color-border)] text-center text-[11px]">
        <div className="bg-[var(--color-surface)] px-2 py-1.5">
          <div className="app-muted">{copy.budget}</div>
          <div className="font-semibold">{formatBudget(investmentPackage.requested_amount, locale)}</div>
        </div>
        <div className="bg-[var(--color-surface)] px-2 py-1.5">
          <div className="app-muted">{copy.invested}</div>
          <div className="font-semibold">{formatBudget(suggestion.estimated_total, locale)}</div>
        </div>
        <div className="bg-[var(--color-surface)] px-2 py-1.5">
          <div className="app-muted">{copy.remaining}</div>
          <div className="font-semibold">{formatBudget(suggestion.unallocated_balance, locale)}</div>
        </div>
      </div>

      <ul className="divide-y app-border-soft text-xs">
        {suggestion.items.map((item) => (
          <li key={item.asset_id} className="flex items-center gap-2 px-3 py-1.5">
            <div className="min-w-0 flex-1">
              <div className="truncate font-medium">
                {item.symbol} <span className="font-normal app-muted">· {item.name}</span>
              </div>
              <div className="text-[11px] app-muted">
                {quantityFormatter.format(item.quantity)} {copy.quantity} · {formatBudget(item.estimated_amount, locale)}
              </div>
            </div>
            <div className="w-14 text-right">
              <div className="font-semibold">%{item.weight_pct.toLocaleString(locale, { maximumFractionDigits: 1 })}</div>
              <div className="mt-0.5 h-1 overflow-hidden rounded-full bg-[var(--color-border)]">
                <div className="h-full bg-[var(--color-primary)]" style={{ width: `${Math.min(100, item.weight_pct)}%` }} />
              </div>
            </div>
          </li>
        ))}
      </ul>

      <div className="flex justify-between gap-2 border-t app-border px-3 py-1.5 text-[11px] app-muted">
        <span>{copy.volatility}: %{metrics.expected_volatility_20d_pct.toLocaleString(locale)}</span>
        <span>{copy.diversification}: {metrics.diversification_score.toLocaleString(locale)}/100</span>
      </div>

      <div className="border-t app-border px-3 py-2.5">
        {investmentPackage.exceeds_balance && (
          <div className="app-danger-box mb-2 rounded-md px-2 py-1 text-[11px]">
            {copy.insufficient(formatBudget(investmentPackage.available_balance, locale))}
          </div>
        )}
        {purchaseError && (
          <div className="app-danger-box mb-2 rounded-md px-2 py-1 text-[11px]">{purchaseError}</div>
        )}
        <button
          type="button"
          onClick={purchasePackage}
          disabled={disabled}
          className={`w-full rounded-md px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed ${
            purchaseState === "done"
              ? "bg-emerald-600 text-white disabled:opacity-100"
              : "app-primary disabled:opacity-60"
          }`}
        >
          {purchaseState === "done"
            ? `✓ ${copy.bought}`
            : purchaseState === "submitting"
              ? copy.buying
              : `${copy.buy} · ${formatBudget(suggestion.estimated_total, locale)}`}
        </button>
        <p className="mt-2 text-[10px] leading-snug app-muted">{investmentPackage.disclaimer}</p>
      </div>
    </div>
  );
}
