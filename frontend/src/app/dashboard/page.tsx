"use client";

import { MarketInsightList } from "../../components/dashboard/MarketInsightList";
import { SummaryCards } from "../../components/dashboard/SummaryCards";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { AssetAllocationChart } from "../../components/portfolio/AssetAllocationChart";
import { RiskScoreCard } from "../../components/risk/RiskScoreCard";
import { useDashboard } from "../../hooks/useDashboard";

export default function DashboardPage() {
  const { data, loading, error, refetch } = useDashboard();

  if (loading) {
    return <LoadingState label="Dashboard yukleniyor" />;
  }

  if (error || !data) {
    return <ErrorState message={error ?? "Dashboard verisi bos dondu."} onRetry={refetch} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">Dashboard</h1>
        <p className="mt-1 text-sm app-muted">Portfoy, risk ve piyasa ozeti.</p>
      </div>
      <SummaryCards data={data} />
      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <AssetAllocationChart items={data.allocation} />
        <RiskScoreCard risk={data.risk} />
      </div>
      <MarketInsightList movers={data.movers} />
    </div>
  );
}
