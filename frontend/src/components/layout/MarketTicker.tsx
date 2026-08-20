"use client";

import { useEffect, useState } from "react";
import type { PublicMarketTickerItem } from "../../models/market";
import { getPublicMarketTicker } from "../../services/marketService";

const fallbackTickerItems: PublicMarketTickerItem[] = [
  { symbol: "BIST100", label: "BIST 100", value: 10842.36, currency: "TRY", change_percent: 0.84, source: "fallback" },
  { symbol: "USDTRY", label: "USD/TRY", value: 42.18, currency: "TRY", change_percent: 0.12, source: "fallback" },
  { symbol: "EURTRY", label: "EUR/TRY", value: 45.62, currency: "TRY", change_percent: -0.2, source: "fallback" },
  { symbol: "XAUTRY", label: "Gram Altın", value: 3918, currency: "TRY", change_percent: 1.24, source: "fallback" },
  { symbol: "BTC", label: "BTC", value: 2184306, currency: "TRY", change_percent: 2.1, source: "fallback" },
  { symbol: "THYAO", label: "THYAO", value: 312.5, currency: "TRY", change_percent: 1.16, source: "fallback" },
];

function formatValue(item: PublicMarketTickerItem): string {
  const formatted = new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: item.value >= 1000 ? 0 : 2,
    maximumFractionDigits: item.value >= 1000 ? 0 : 2,
  }).format(item.value);

  if (item.currency === "TRY") {
    return `${formatted} ₺`;
  }

  return `${formatted} ${item.currency}`;
}

export function MarketTicker({ onSelect }: { onSelect: (symbol: string) => void }) {
  const [items, setItems] = useState<PublicMarketTickerItem[]>([]);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await getPublicMarketTicker();
        if (active && response.items.length > 0) {
          setItems(response.items);
        } else if (active) {
          setItems((current) => (current.length > 0 ? current : fallbackTickerItems));
        }
      } catch {
        if (active) {
          setItems((current) => (current.length > 0 ? current : fallbackTickerItems));
        }
      }
    }

    void load();
    const timer = window.setInterval(load, 60000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const displayItems = items.length > 0 ? [...items, ...items] : [];

  return (
    <div className="group overflow-hidden border-b border-black/10 bg-[var(--color-market-bar)]">
      <div className="ticker-track flex w-max gap-3 px-4 py-3 group-hover:[animation-play-state:paused]">
        {displayItems.map((item, index) => {
          const positive = (item.change_percent ?? 0) >= 0;
          return (
            <button
              key={`${item.symbol}-${index}`}
              type="button"
              onClick={() => onSelect(item.symbol)}
              className="flex shrink-0 items-center gap-2 rounded-lg px-3 py-1 text-sm whitespace-nowrap transition hover:bg-white/10"
            >
              <b className="font-semibold text-[var(--color-market-text)]">{item.label}</b>
              <span className="text-[var(--color-market-muted)]">{formatValue(item)}</span>
              {item.change_percent != null && (
                <span className={`text-xs font-semibold ${positive ? "app-success" : "app-danger"}`}>
                  {positive ? "▲" : "▼"} {Math.abs(item.change_percent).toFixed(2)}%
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
