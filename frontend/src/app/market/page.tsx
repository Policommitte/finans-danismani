"use client";

import { AssetList } from "../../components/market/AssetList";
import { MarketSearchBox } from "../../components/market/MarketSearchBox";
import { PriceHistoryChart } from "../../components/market/PriceHistoryChart";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { useMarket } from "../../hooks/useMarket";

export default function MarketPage() {
  const market = useMarket();

  if (market.loading) {
    return <LoadingState label="Piyasa verileri yukleniyor" />;
  }

  if (market.error || !market.data) {
    return <ErrorState message={market.error ?? "Piyasa verisi bos dondu."} onRetry={market.refetch} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Piyasa</h1>
        <p className="mt-1 text-sm text-slate-500">Varlik fiyatlari, grafikler ve RAG aramasi.</p>
      </div>
      <div className="grid gap-6 xl:grid-cols-[.8fr_1.2fr]">
        <AssetList items={market.data.assets.items} onSelect={market.setSymbol} />
        <PriceHistoryChart history={market.data.history} />
      </div>
      <MarketSearchBox result={market.searchResult} searching={market.searching} onSearch={market.runSearch} />
    </div>
  );
}
