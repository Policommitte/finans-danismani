"use client";

import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { EconomicCalendarTab } from "../../components/market/EconomicCalendarTab";
import { TradingCenter } from "../../components/trading/TradingCenter";
import { useLanguage } from "../../contexts/LanguageContext";

type MarketTab = "islemler" | "takvim";

const TABS: { key: MarketTab; label: string }[] = [
  { key: "islemler", label: "İşlemler" },
  { key: "takvim", label: "Ekonomik Takvim" },
];

export default function MarketPage() {
  const { language } = useLanguage();
  const [tab, setTab] = useState<MarketTab>("islemler");
  const [calendarReady, setCalendarReady] = useState(false);

  const markCalendarReady = useCallback(() => setCalendarReady(true), []);

  function selectTab(nextTab: MarketTab) {
    if (nextTab === tab) return;
    if (nextTab === "takvim") setCalendarReady(false);
    setTab(nextTab);
  }

  return (
    <div className="space-y-6">
      <nav className="flex flex-wrap gap-2">
        {TABS.map((item) => {
          const active = item.key === tab;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => selectTab(item.key)}
              className={`rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${
                active ? "app-primary border-transparent" : "app-card app-border app-subtle-hover"
              }`}
            >
              {item.label}
            </button>
          );
        })}
      </nav>

      {tab === "takvim" ? <EconomicCalendarTab onReady={markCalendarReady} /> : <TradingCenter />}
      {tab === "takvim" && !calendarReady ? (
        <CalendarLoadingOverlay language={language} />
      ) : null}
    </div>
  );
}

function CalendarLoadingOverlay({ language }: { language: "tr" | "en" }) {
  const [mainElement, setMainElement] = useState<HTMLElement | null>(null);

  useEffect(() => {
    setMainElement(document.querySelector("main"));
  }, []);

  if (!mainElement) return null;

  return createPortal(
    <div className="absolute inset-0 z-[80] grid place-items-center bg-slate-950/10 backdrop-blur-md">
      <div
        role="status"
        aria-live="polite"
        className="relative flex h-24 w-44 items-start justify-center"
      >
        <span className="page-transition__logo" />
        <span className="page-transition__spinner" />
        <span className="sr-only">
          {language === "tr" ? "Ekonomik takvim hazırlanıyor" : "Preparing economic calendar"}
        </span>
      </div>
    </div>,
    mainElement,
  );
}
