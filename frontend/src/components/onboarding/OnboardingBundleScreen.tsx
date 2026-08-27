"use client";

import { useEffect, useState } from "react";
import type { Asset } from "../../models/market";
import type { RiskTier } from "../../models/auth";
import { getMarketAssets } from "../../services/marketService";
import { BUNDLE_DEFINITIONS } from "./bundleDefinitions";

const priceFormat = new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function OnboardingBundleScreen({
  tier,
  onContinue,
}: {
  tier: RiskTier;
  onContinue: () => void;
}) {
  const [assets, setAssets] = useState<Asset[] | null>(null);
  const bundle = BUNDLE_DEFINITIONS[tier];

  useEffect(() => {
    let active = true;
    getMarketAssets()
      .then((response) => {
        if (active) setAssets(response.items);
      })
      .catch(() => {
        if (active) setAssets([]);
      });
    return () => {
      active = false;
    };
  }, []);

  const bundleAssets = bundle.symbols
    .map((symbol) => assets?.find((item) => item.symbol === symbol))
    .filter((item): item is Asset => Boolean(item));

  return (
    <div className="w-full max-w-lg rounded-2xl border app-card p-6 shadow-2xl">
      <div className="text-xs font-semibold uppercase tracking-wide app-muted">Sana özel sepet önerisi</div>
      <h2 className="mt-1 text-xl font-bold app-heading">{bundle.title}</h2>
      <p className="mt-1 text-sm app-muted">{bundle.description}</p>

      <div className="mt-5 space-y-2">
        {assets === null ? (
          <div className="rounded-lg app-card-muted p-4 text-sm app-muted">Fiyatlar yükleniyor…</div>
        ) : bundleAssets.length === 0 ? (
          <div className="rounded-lg app-card-muted p-4 text-sm app-muted">
            Şu an bu sepet için fiyat verisi alınamadı.
          </div>
        ) : (
          bundleAssets.map((asset) => {
            const positive = (asset.daily_change_pct ?? 0) >= 0;
            return (
              <div
                key={asset.symbol}
                className="flex items-center justify-between rounded-lg app-card-muted px-4 py-3"
              >
                <div>
                  <div className="text-sm font-semibold app-heading">{asset.symbol}</div>
                  <div className="text-xs app-muted">{asset.name}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold app-heading">
                    {priceFormat.format(asset.current_price)} {asset.currency}
                  </div>
                  {asset.daily_change_pct != null && (
                    <div className={`text-xs font-semibold ${positive ? "app-success" : "app-danger"}`}>
                      {positive ? "▲" : "▼"} %{priceFormat.format(Math.abs(asset.daily_change_pct))}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      <button
        type="button"
        onClick={onContinue}
        className="mt-6 w-full rounded-xl app-primary px-4 py-3 text-center text-sm font-semibold transition hover:opacity-90"
      >
        Devam Et
      </button>
    </div>
  );
}
