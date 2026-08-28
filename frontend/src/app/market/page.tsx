"use client";

import { useEffect } from "react";

import { PriceHistoryChart } from "../../components/market/PriceHistoryChart";
import { OrderList } from "../../components/market/OrderList";
import { TradeTicket } from "../../components/market/TradeTicket";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { useMarket } from "../../hooks/useMarket";
import { useTrading } from "../../hooks/useTrading";
import { MARKET_PAGE_READY_EVENT } from "../../components/layout/transitionEvents";
import { useLanguage } from "../../contexts/LanguageContext";

export default function MarketPage() {
  const { language } = useLanguage();
  const market = useMarket();
  const trading = useTrading();

  useEffect(() => {
    if (market.loading) {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      document.documentElement.dataset.marketPageReady = "true";
      window.dispatchEvent(new Event(MARKET_PAGE_READY_EVENT));
    });

    return () => window.cancelAnimationFrame(frame);
  }, [market.loading]);

  if (market.loading && !market.data) {
    return <LoadingState label={language === "tr" ? "Piyasa verileri yükleniyor" : "Loading market data"} />;
  }

  if (!market.data) {
    return <ErrorState message={market.error ?? (language === "tr" ? "Piyasa verisi boş döndü." : "Market data returned empty.")} onRetry={market.refetch} />;
  }

  const selectedAsset =
    market.data.assets.items.find((asset) => asset.symbol === market.symbol) ??
    market.data.assets.items[0];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">{language === "tr" ? "Piyasa & İşlemler" : "Markets & Trading"}</h1>
        <p className="mt-1 text-sm app-muted">
          {language === "tr"
            ? "Varlık fiyatları, grafikler ve likit para destekli sanal işlemler."
            : "Asset prices, charts and virtual trades backed by liquid cash."}
        </p>
      </div>
      <PriceHistoryChart
        data={market.data.candles}
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
                onPreview={(symbol, side, quantity, orderType, limitPrice, validity, stopLossPrice) => void trading.requestPreview(symbol, side, quantity, orderType, limitPrice, validity, stopLossPrice)}
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
    </div>
  );
}
