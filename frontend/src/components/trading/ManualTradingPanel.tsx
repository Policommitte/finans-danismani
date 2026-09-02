"use client";

import { useEffect, useState } from "react";
import { ErrorState } from "../feedback/ErrorState";
import { LoadingState } from "../feedback/LoadingState";
import { MARKET_PAGE_READY_EVENT } from "../layout/transitionEvents";
import { OrderList } from "../market/OrderList";
import { PriceHistoryChart } from "../market/PriceHistoryChart";
import { TradeTicket } from "../market/TradeTicket";
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

export function ManualTradingPanel({ onReady }: { onReady?: () => void }) {
  const { language } = useLanguage();
  const market = useMarket();
  const trading = useTrading();
  const forecast = useForecast(market.symbol);

  useEffect(() => {
    if (market.loading) return;
    const frame = window.requestAnimationFrame(() => {
      document.documentElement.dataset.marketPageReady = "true";
      window.dispatchEvent(new Event(MARKET_PAGE_READY_EVENT));
      onReady?.();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [market.loading, onReady]);

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

  const selectedAsset =
    market.data.assets.items.find((asset) => asset.symbol === market.symbol) ??
    market.data.assets.items[0];

  return (
    <PriceHistoryChart
      data={market.data.candles}
      forecast={forecast}
      assetClass={selectedAsset?.asset_class}
      currency={selectedAsset?.currency}
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
      {selectedAsset && (
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
      )}
    </PriceHistoryChart>
  );
}
