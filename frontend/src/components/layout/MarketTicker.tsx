"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../../contexts/LanguageContext";
import type { PublicMarketTickerItem } from "../../models/market";
import { getPublicMarketTicker } from "../../services/marketService";
import { ThemeToggle } from "../ui/ThemeToggle";
import { MARKET_TICKER_READY_EVENT } from "./transitionEvents";

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
  const tickerTrackRef = useRef<HTMLDivElement>(null);
  const { language, toggleLanguage } = useLanguage();
  const displayItems = items.length > 0 ? [...items, ...items] : [];

  function setTickerPlaybackRate(rate: number) {
    tickerTrackRef.current?.getAnimations().forEach((animation) => {
      animation.updatePlaybackRate(rate);
    });
  }

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await getPublicMarketTicker();
        if (active) {
          if (response.items.length > 0) {
            cachedTickerItems = response.items;
            setItems(response.items);
          }
        }
      } catch {
        if (active) {
          setItems((current) => current);
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

  useEffect(() => {
    if (items.length === 0) {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      document.documentElement.dataset.marketTickerReady = "true";
      window.dispatchEvent(new Event(MARKET_TICKER_READY_EVENT));
    });

    return () => window.cancelAnimationFrame(frame);
  }, [items.length]);

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

        <div className="relative min-w-0 flex-1 overflow-hidden py-3" data-tour="market-stream">
          <div ref={tickerTrackRef} className="ticker-track flex w-max gap-3">
            {displayItems.map((item, index) => {
              const positive = (item.change_percent ?? 0) >= 0;
              return (
                <button
                  key={`${item.symbol}-${index}`}
                  type="button"
                  onClick={() => onSelect(item.symbol)}
                  onPointerEnter={() => setTickerPlaybackRate(0.28)}
                  onPointerLeave={() => setTickerPlaybackRate(1)}
                  className="ticker-item flex min-w-48 shrink-0 items-center gap-3 border-l border-[var(--color-border)] pl-6 text-left"
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
            className="flex h-20 w-24 shrink-0 items-center justify-center rounded-none bg-[var(--color-cta)] text-sm font-bold text-[var(--color-market-text)] hover:bg-[var(--color-cta-hover)] md:w-28"
          >
            {language === "tr" ? "Çıkış" : "Logout"}
          </button>
        ) : (
          <Link
            href="/login"
            className="flex h-20 w-24 shrink-0 items-center justify-center rounded-none bg-[var(--color-cta)] text-sm font-bold text-[var(--color-market-text)] hover:bg-[var(--color-cta-hover)] md:w-28"
          >
            {language === "tr" ? "Giriş" : "Login"}
          </Link>
        )}
        <div className="flex shrink-0 items-center gap-3" data-tour="appearance-controls">
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
