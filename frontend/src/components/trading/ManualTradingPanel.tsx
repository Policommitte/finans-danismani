"use client";

import { useEffect, useMemo, useState } from "react";
import { ErrorState } from "../feedback/ErrorState";
import { LoadingState } from "../feedback/LoadingState";
import { MARKET_PAGE_READY_EVENT } from "../layout/transitionEvents";
import { AssetList } from "../market/AssetList";
import { AssetSummaryModal } from "../market/AssetSummaryModal";
import { OrderList } from "../market/OrderList";
import { PriceHistoryChart } from "../market/PriceHistoryChart";
import { TradeTicket } from "../market/TradeTicket";
import { useAuth } from "../../hooks/useAuth";
import { useLanguage } from "../../contexts/LanguageContext";
import { useMarket } from "../../hooks/useMarket";
import { useTrading } from "../../hooks/useTrading";
import type { Forecast } from "../../models/market";
import { getForecast } from "../../services/marketService";

/**
 * Secili varligin tahminini ceker.
 *
 * `useMarket`'e EKLENMEDI: o hook fiyat/mum/emir akisini yonetiyor ve
 * tahmin OPSIYONEL bir sustur - basarisiz olursa panelin geri kalani
 * etkilenmemeli. Ayri tutmak, hatayi da ayri tutar.
 */
function useForecast(symbol: string | undefined): Forecast | null {
  const [forecast, setForecast] = useState<Forecast | null>(null);

  useEffect(() => {
    if (!symbol) {
      setForecast(null);
      return;
    }

    // Sembol degisince ESKI tahmin gorunmeye devam etmemeli: yeni istek
    // donene kadar temizlenir, aksi halde THYAO'nun tahmini bir an AAPL
    // grafiginin uzerinde durur.
    setForecast(null);
    let iptal = false;

    getForecast(symbol)
      .then((sonuc) => {
        if (!iptal) setForecast(sonuc);
      })
      .catch(() => {
        // Tahmin ozelligi kapali ya da uc hata verdi - SESSIZ gecilir,
        // grafik tahminsiz cizilir. Kullaniciya hata gostermek gereksiz:
        // istemedigi bir sus icin uyari almamali.
        if (!iptal) setForecast(null);
      });

    return () => {
      iptal = true;
    };
  }, [symbol]);

  return forecast;
}

//: Sekme sirasi bilerek sabit: kullanicinin en cok ilgilendigi tipler
//: (hisse/kripto/doviz/altin) once gelsin. Projede tanimli OLMAYAN bir tip
//: (orn. "FUND") burada yoksa listede hic gorunmez - yalnizca `market.data`
//: icinde GERCEKTEN var olan siniflar sekme olarak cikar.
const CLASS_ORDER = [
  "STOCK", "USA_STOCK", "EU_STOCK", "CRYPTO", "FOREX", "GOLD",
  "COMMODITY", "BOND", "ETF", "INDEX",
];
const CLASS_LABELS: Record<string, { tr: string; en: string }> = {
  STOCK: { tr: "Hisse", en: "Stocks" },
  USA_STOCK: { tr: "ABD Hissesi", en: "US Stocks" },
  EU_STOCK: { tr: "Avrupa Hissesi", en: "EU Stocks" },
  CRYPTO: { tr: "Kripto", en: "Crypto" },
  FOREX: { tr: "Döviz", en: "Forex" },
  GOLD: { tr: "Altın", en: "Gold" },
  COMMODITY: { tr: "Emtia", en: "Commodities" },
  BOND: { tr: "Tahvil", en: "Bonds" },
  ETF: { tr: "Fon (ETF)", en: "ETF" },
  INDEX: { tr: "Endeks", en: "Index" },
};

export function ManualTradingPanel({ onReady }: { onReady?: () => void }) {
  const { language } = useLanguage();
  const auth = useAuth();
  const market = useMarket();
  const trading = useTrading();
  const forecast = useForecast(market.symbol);
  // Sayfa acilir acilmaz hicbir varligin grafigi/islem ekrani otomatik
  // gorunmesin diye baslangic durumu HER ZAMAN "liste" - `market.symbol`in
  // varsayilan degeri (bkz. useMarket.ts) yalnizca arka planda mum verisi
  // on-yuklemek icin var, ekranda GOSTERILMEZ.
  const [assetClass, setAssetClass] = useState<string | null>(null);
  const [tradeView, setTradeView] = useState(false);
  const [modalSymbol, setModalSymbol] = useState<string | null>(null);

  useEffect(() => {
    if (market.loading) return;
    const frame = window.requestAnimationFrame(() => {
      document.documentElement.dataset.marketPageReady = "true";
      window.dispatchEvent(new Event(MARKET_PAGE_READY_EVENT));
      onReady?.();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [market.loading, onReady]);

  const classes = useMemo(() => {
    if (!market.data) return [];
    const present = new Set(market.data.assets.items.map((item) => item.asset_class));
    const ordered = CLASS_ORDER.filter((code) => present.has(code));
    const extras = Array.from(present).filter((code) => !CLASS_ORDER.includes(code));
    return [...ordered, ...extras];
  }, [market.data]);

  const activeClass = assetClass && classes.includes(assetClass) ? assetClass : classes[0];

  function selectClass(nextClass: string) {
    setAssetClass(nextClass);
  }

  function openTradeView(symbol: string) {
    market.setSymbol(symbol);
    setTradeView(true);
  }

  if (market.loading && !market.data) {
    return (
      <LoadingState
        label={language === "tr" ? "Piyasa verileri yükleniyor" : "Loading market data"}
      />
    );
  }

  if (!market.data) {
    return (
      <ErrorState
        message={
          market.error ??
          (language === "tr" ? "Piyasa verisi boş döndü." : "Market data returned empty.")
        }
        onRetry={market.refetch}
      />
    );
  }

  const classItems = market.data.assets.items.filter((item) => item.asset_class === activeClass);
  const selectedAsset =
    market.data.assets.items.find((asset) => asset.symbol === market.symbol) ??
    market.data.assets.items[0];

  return (
    <div className="space-y-4">
      <div
        className="flex flex-wrap gap-2 rounded-2xl app-card-muted p-1.5"
        role="tablist"
        aria-label={language === "tr" ? "Yatırım tipi" : "Investment type"}
      >
        {classes.map((code) => {
          const active = code === activeClass;
          const label = CLASS_LABELS[code]?.[language] ?? code.replaceAll("_", " ");
          return (
            <button
              key={code}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => selectClass(code)}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                active ? "bg-[#454466] text-white shadow-lg" : "app-muted hover:bg-white/60 hover:text-[var(--color-text)]"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {tradeView && selectedAsset ? (
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => setTradeView(false)}
            className="text-sm font-semibold text-[var(--color-primary)] transition hover:opacity-80"
          >
            {language === "tr" ? "← Varlık listesine dön" : "← Back to asset list"}
          </button>

          <PriceHistoryChart
            data={market.data.candles}
            forecast={forecast}
            assetClass={selectedAsset.asset_class}
            currency={selectedAsset.currency}
            interval={market.chartInterval}
            range={market.chartRange}
            rangePresetActive={market.chartRangePresetActive}
            rangePresetRevision={market.chartRangePresetRevision}
            onIntervalChange={market.setChartInterval}
            onRangeChange={market.setChartRange}
            onRangePresetExit={market.clearChartRangePreset}
            loading={market.loading}
          >
            <p className="-mt-2 mb-4 text-xs app-muted">
              {language === "tr" ? "Grafikler " : "Charts are powered by "}
              <a
                href="https://www.tradingview.com/"
                target="_blank"
                rel="noreferrer"
                className="font-medium underline decoration-current/40 underline-offset-2 hover:decoration-current"
              >
                TradingView Lightweight Charts
              </a>
              {language === "tr" ? " ile oluşturulmuştur." : "."}
            </p>
            <div className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]">
              <TradeTicket
                asset={selectedAsset}
                assets={market.data.assets.items}
                holdings={trading.data?.holdings.items ?? []}
                orders={trading.data?.orders.items ?? []}
                account={trading.data?.account ?? null}
                preview={trading.preview}
                submitting={trading.submitting}
                error={trading.actionError ?? trading.error}
                notice={trading.notice}
                onSelectAsset={market.setSymbol}
                onPreview={(symbol, side, quantity, orderType, limitPrice, validity, stopLossPrice) =>
                  void trading.requestPreview(
                    symbol,
                    side,
                    quantity,
                    orderType,
                    limitPrice,
                    validity,
                    stopLossPrice,
                  )
                }
                onConfirm={() => void trading.confirmOrder()}
                onClearPreview={trading.clearPreview}
              />
              <div className="min-w-0 lg:relative lg:min-h-0">
                <div className="lg:absolute lg:inset-0">
                  <OrderList
                    items={trading.data?.orders.items ?? []}
                    submitting={trading.submitting}
                    onCancel={(orderId) => void trading.cancelOrder(orderId)}
                  />
                </div>
              </div>
            </div>
          </PriceHistoryChart>
        </div>
      ) : (
        <AssetList items={classItems} onView={setModalSymbol} onTrade={openTradeView} />
      )}

      {modalSymbol ? (
        <AssetSummaryModal
          symbol={modalSymbol}
          isAuthenticated={Boolean(auth.user)}
          onClose={() => setModalSymbol(null)}
        />
      ) : null}
    </div>
  );
}
