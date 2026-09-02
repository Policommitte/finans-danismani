"use client";

import type { Asset } from "../../models/market";
import { useLanguage } from "../../contexts/LanguageContext";

/**
 * Bir yatirim tipine ait TUM alinabilir varliklarin tam listesi - kart
 * gorunumunde, mumkun oldugunca coğu ayni anda gorunur (grid + kaydirma).
 * Market sayfasindaki eski kisitli acilir-liste (`<select>`) deseninin
 * yerini alir (bkz. TradeTicket.tsx - o dosyaya DOKUNULMADI, hala kendi
 * ic acilir listesini kullaniyor, bu bilesen yalnizca GOZ AT/SEC asamasi
 * icin).
 *
 * Bir karta tiklamak `onView`'i tetikler (AssetSummaryModal acilir - grafik
 * + Polifin AI analizi). Kartin ayri "Islem Yap" dugmesi `onTrade`'i
 * tetikler (dogrudan TradeTicket'a gecer) - "goruntule" ve "islem yap"
 * eylemleri kasitli olarak AYRI tutuldu.
 */
export function AssetList({
  items,
  onView,
  onTrade,
}: {
  items: Asset[];
  onView: (symbol: string) => void;
  onTrade: (symbol: string) => void;
}) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";

  if (items.length === 0) {
    return (
      <div className="grid min-h-[200px] place-items-center rounded-2xl border app-border app-card-muted text-sm app-muted">
        {language === "tr" ? "Bu kategoride varlık bulunamadı." : "No assets found in this category."}
      </div>
    );
  }

  return (
    <div className="grid max-h-[560px] grid-cols-1 gap-3 overflow-y-auto pr-1 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((asset) => {
        const changePositive = asset.daily_change_pct != null && asset.daily_change_pct >= 0;
        const changeClass =
          asset.daily_change_pct == null ? "app-muted" : changePositive ? "app-success" : "app-danger";
        const priceLabel = new Intl.NumberFormat(locale, {
          style: "currency",
          currency: asset.currency,
          minimumFractionDigits: asset.asset_class === "FOREX" ? 4 : 2,
          maximumFractionDigits: asset.asset_class === "FOREX" ? 4 : 2,
        }).format(asset.current_price);

        return (
          <div
            key={asset.symbol}
            className="flex flex-col justify-between gap-3 rounded-2xl border app-border app-card p-4 transition hover:border-[var(--color-primary)]/50"
          >
            <button
              type="button"
              onClick={() => onView(asset.symbol)}
              className="flex items-start justify-between gap-3 text-left"
            >
              <span className="min-w-0">
                <span className="block truncate font-semibold app-heading">{asset.symbol}</span>
                <span className="block truncate text-xs app-muted">{asset.name}</span>
              </span>
              <span className="shrink-0 text-right">
                <span className="block font-semibold app-heading">{priceLabel}</span>
                <span className={`block text-xs font-semibold ${changeClass}`}>
                  {asset.daily_change_pct == null
                    ? "—"
                    : `${changePositive ? "▲" : "▼"} %${Math.abs(asset.daily_change_pct).toFixed(2)}`}
                </span>
              </span>
            </button>

            <div className="flex gap-2 border-t app-border-soft pt-3">
              <button
                type="button"
                onClick={() => onView(asset.symbol)}
                className="flex-1 rounded-lg border app-border px-3 py-1.5 text-xs font-semibold app-muted transition hover:opacity-80"
              >
                {language === "tr" ? "Grafik ve AI" : "Chart & AI"}
              </button>
              <button
                type="button"
                onClick={() => onTrade(asset.symbol)}
                className="flex-1 rounded-lg bg-[var(--color-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--color-on-primary)] transition hover:opacity-90"
              >
                {language === "tr" ? "İşlem Yap" : "Trade"}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
