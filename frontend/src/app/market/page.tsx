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
          <div
            role="note"
            className="mb-4 flex gap-3 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950 dark:border-sky-800/60 dark:bg-sky-950/30 dark:text-sky-100"
          >
            <span aria-hidden="true" className="mt-0.5 text-base">ⓘ</span>
            <div>
              <p className="font-semibold text-sky-950 dark:text-sky-50">
                {language === "tr" ? "Sanal işlem ve emir zamanlaması" : "Virtual trading and order timing"}
              </p>
              <p className="mt-1 leading-relaxed text-sky-900 dark:text-sky-200">
                {language === "tr"
                  ? "İşlemler sanaldır ve gerçek piyasaya iletilmez. Fiyatlar veri kaynağına göre gecikmeli olabilir (BIST yaklaşık 15 dakika). Piyasa emri sonraki doğrulanmış 5 dakikalık fiyatla; limit ve stop emirleri fiyat koşulları sağlandığında değerlendirilir. Stop fiyatı garanti edilen satış fiyatı değildir; gerçekleşme fiyatı ekrandaki son fiyattan ve stop seviyesinden farklı olabilir. Piyasa kapalıysa emir ilk uygun fiyat güncellemesini bekler."
                  : "Trades are virtual and are not sent to a real exchange. Prices may be delayed depending on the data source (BIST by approximately 15 minutes). Market orders are evaluated at the next verified 5-minute price; limit and stop orders are evaluated when their price conditions are met. A stop price is not a guaranteed execution price; the fill may differ from both the latest displayed price and the stop level. If the market is closed, the order waits for the next eligible price update."}
              </p>
            </div>
          </div>
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
              <OrderList
                items={trading.data?.orders.items ?? []}
                submitting={trading.submitting}
                onCancel={(orderId) => void trading.cancelOrder(orderId)}
              />
            </div>
          )}
      </PriceHistoryChart>
    </div>
  );
}
