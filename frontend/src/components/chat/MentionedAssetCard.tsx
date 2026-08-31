"use client";

import { useEffect, useState } from "react";
import type { Asset } from "../../models/market";
import { getMarketAssets } from "../../services/marketService";

const priceFormat = new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/**
 * Sohbet cevabinda bahsedilen varliklar icin kucuk bilgi karti.
 *
 * Sadece `symbols` (backend'in katalogla dogruladigi semboller) alir; ad/fiyat
 * bilgisini `AssetSummaryModal`'in kendisiyle AYNI cagriyla (`getMarketAssets`
 * + `symbol` ile filtre) ceker - iki ayri veri kaynagi olusmasin diye.
 */
export function MentionedAssetCard({
  symbols,
  onOpenAsset,
}: {
  symbols: string[];
  onOpenAsset: (symbol: string) => void;
}) {
  const [assets, setAssets] = useState<Record<string, Asset>>({});

  useEffect(() => {
    if (symbols.length === 0) {
      return;
    }
    let active = true;
    getMarketAssets()
      .then((response) => {
        if (!active) return;
        const bySymbol: Record<string, Asset> = {};
        for (const item of response.items) {
          if (symbols.includes(item.symbol)) {
            bySymbol[item.symbol] = item;
          }
        }
        setAssets(bySymbol);
      })
      .catch(() => {
        // Fiyat bilgisi cekilemezse kart yine de sembol+buton ile gosterilir.
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbols.join(",")]);

  if (symbols.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1.5">
      {symbols.map((symbol) => {
        const asset = assets[symbol];
        const changePositive = asset?.daily_change_pct != null ? asset.daily_change_pct >= 0 : null;
        return (
          <button
            key={symbol}
            type="button"
            onClick={() => onOpenAsset(symbol)}
            className="flex w-full items-center justify-between gap-3 rounded-lg border app-border bg-[var(--color-surface)] px-3 py-2 text-left transition hover:bg-[var(--color-surface-muted)]"
          >
            <div className="min-w-0">
              <div className="truncate text-xs font-semibold app-heading">{asset?.name ?? symbol}</div>
              <div className="text-[11px] app-muted">{symbol}</div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {asset && (
                <div className="text-right">
                  <div className="text-xs font-semibold app-heading">
                    {priceFormat.format(asset.current_price)} {asset.currency}
                  </div>
                  {asset.daily_change_pct != null && (
                    <div
                      className="text-[11px] font-medium"
                      style={{ color: changePositive ? "var(--color-success)" : "var(--color-danger)" }}
                    >
                      {changePositive ? "▲" : "▼"} %{priceFormat.format(Math.abs(asset.daily_change_pct))}
                    </div>
                  )}
                </div>
              )}
              <span
                aria-hidden="true"
                className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[var(--color-primary-soft)] text-[var(--color-primary)]"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
