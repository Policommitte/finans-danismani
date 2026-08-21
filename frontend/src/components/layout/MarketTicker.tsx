"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage } from "../../contexts/LanguageContext";
import type { PublicMarketTickerItem } from "../../models/market";
import { getPublicMarketTicker } from "../../services/marketService";
import { ThemeToggle } from "../ui/ThemeToggle";

const fallbackTickerItems: PublicMarketTickerItem[] = [
  { symbol: "BIST100", label: "BIST 100", value: 10842.36, currency: "TRY", change_percent: 0.84, source: "fallback" },
  { symbol: "USDTRY", label: "USD/TRY", value: 42.18, currency: "TRY", change_percent: 0.12, source: "fallback" },
  { symbol: "EURTRY", label: "EUR/TRY", value: 45.62, currency: "TRY", change_percent: -0.2, source: "fallback" },
  { symbol: "XAUTRY", label: "Gram Altın", value: 3918, currency: "TRY", change_percent: 1.24, source: "fallback" },
  { symbol: "BTC", label: "BTC", value: 2184306, currency: "TRY", change_percent: 2.1, source: "fallback" },
  { symbol: "THYAO", label: "THYAO", value: 312.5, currency: "TRY", change_percent: 1.16, source: "fallback" },
];

let cachedTickerItems: PublicMarketTickerItem[] = [];

function formatValue(item: PublicMarketTickerItem, language: "tr" | "en"): string {
  return new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    maximumFractionDigits: item.value > 1000 ? 0 : 4,
    minimumFractionDigits: item.value > 1000 ? 0 : 2,
  }).format(item.value);
}

export function MarketTicker({
  onSelect,
  onLogout,
  isAuthenticated,
}: {
  onSelect: (symbol: string) => void;
  onLogout: () => void;
  isAuthenticated: boolean;
}) {
  const [items, setItems] = useState<PublicMarketTickerItem[]>(() => cachedTickerItems);
  const { language, toggleLanguage } = useLanguage();
  const displayItems = items.length > 0 ? [...items, ...items] : [];

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await getPublicMarketTicker();
        if (active) {
          const nextItems = response.items.length > 0 ? response.items : fallbackTickerItems;
          cachedTickerItems = nextItems;
          setItems(nextItems);
        }
      } catch {
        if (active) {
          setItems((current) => {
            const nextItems = current.length > 0 ? current : fallbackTickerItems;
            cachedTickerItems = nextItems;
            return nextItems;
          });
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

  return (
    <section className="fixed left-24 right-0 top-0 z-[80] bg-[var(--color-market-bar)] text-[var(--color-market-text)]">
      <Link href="/" className="absolute left-2 top-1/2 hidden -translate-y-1/2 2xl:flex">
        <span
          aria-hidden="true"
          className="block h-12 w-48 bg-[var(--color-market-text)] [mask-image:url('/polifin-logo-clean.svg')] [mask-position:center] [mask-repeat:no-repeat] [mask-size:contain]"
        />
        <span className="sr-only">Polifin</span>
      </Link>

      <div className="flex min-h-20 w-full items-center gap-4 px-4 md:gap-6 2xl:pl-60 2xl:pr-14">
        <div className="hidden shrink-0 items-center gap-2 text-sm font-semibold text-[var(--color-market-muted)] md:flex">
          <span className="h-2 w-2 rotate-45 bg-[var(--color-accent)]" />
          {language === "tr" ? "PİYASA VERİLERİ" : "MARKET DATA"}
        </div>

        <div className="relative min-w-0 flex-1 overflow-hidden py-3">
          <div className="ticker-track flex w-max gap-3">
            {displayItems.map((item, index) => {
              const positive = (item.change_percent ?? 0) >= 0;
              return (
                <button
                  key={`${item.symbol}-${index}`}
                  type="button"
                  onClick={() => onSelect(item.symbol)}
                  className="flex min-w-48 shrink-0 items-center gap-3 border-l border-[var(--color-border)] pl-6 text-left"
                >
                  <span>
                    <span className="block text-xs font-semibold text-[var(--color-market-muted)]">
                      {item.label.toLocaleUpperCase(language === "tr" ? "tr-TR" : "en-US")}
                    </span>
                    <span className="mt-1 block text-lg font-semibold">{formatValue(item, language)}</span>
                  </span>
                  <span className={`text-xs font-semibold ${positive ? "app-success" : "app-danger"}`}>
                    {item.change_percent == null
                      ? "-"
                      : `${positive ? "+" : ""}${item.change_percent.toFixed(2)}%`}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {isAuthenticated ? (
          <button
            type="button"
            onClick={onLogout}
            className="shrink-0 rounded-none bg-[var(--color-cta)] px-6 py-7 text-sm font-bold text-[var(--color-market-text)] transition hover:bg-[var(--color-cta-hover)] md:px-8"
          >
            {language === "tr" ? "Çıkış" : "Logout"}
          </button>
        ) : (
          <Link
            href="/login"
            className="shrink-0 rounded-none bg-[var(--color-cta)] px-6 py-7 text-sm font-bold text-[var(--color-market-text)] transition hover:bg-[var(--color-cta-hover)] md:px-8"
          >
            {language === "tr" ? "Giriş" : "Login"}
          </Link>
        )}
        <div className="flex shrink-0 items-center gap-3">
          <ThemeToggle className="rounded-md" />
          <button
            type="button"
            aria-label={language === "tr" ? "Dili İngilizce yap" : "Switch language to Turkish"}
            onClick={toggleLanguage}
            className="flex h-10 w-12 items-center justify-center rounded-md border app-border app-surface text-sm font-black app-heading transition hover:opacity-80"
          >
            {language === "tr" ? "EN" : "TR"}
          </button>
        </div>
      </div>
    </section>
  );
}
