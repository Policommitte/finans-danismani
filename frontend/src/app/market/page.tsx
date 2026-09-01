"use client";

import { useState } from "react";

import { EconomicCalendarTab } from "../../components/market/EconomicCalendarTab";
import { TradingCenter } from "../../components/trading/TradingCenter";

type MarketTab = "islemler" | "takvim";

const TABS: { key: MarketTab; label: string }[] = [
  { key: "islemler", label: "İşlemler" },
  { key: "takvim", label: "Ekonomik Takvim" },
];

export default function MarketPage() {
  const [tab, setTab] = useState<MarketTab>("islemler");

  return (
    <div className="space-y-6">
      <nav className="flex flex-wrap gap-2">
        {TABS.map((item) => {
          const active = item.key === tab;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => setTab(item.key)}
              className={`rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${
                active ? "app-primary border-transparent" : "app-card app-border app-subtle-hover"
              }`}
            >
              {item.label}
            </button>
          );
        })}
      </nav>

      {tab === "takvim" ? <EconomicCalendarTab /> : <TradingCenter />}
    </div>
  );
}
