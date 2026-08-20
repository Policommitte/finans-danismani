"use client";

import { useAuth } from "../../hooks/useAuth";
import { MarketInsightList } from "../../components/dashboard/MarketInsightList";
import { SummaryCards } from "../../components/dashboard/SummaryCards";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { AssetAllocationChart } from "../../components/portfolio/AssetAllocationChart";
import { RiskScoreCard } from "../../components/risk/RiskScoreCard";
import { useDashboard } from "../../hooks/useDashboard";

const RISK_LEVEL_LABEL: Record<string, string> = {
  dusuk: "düşük",
  orta: "orta",
  yuksek: "yüksek",
  "cok yuksek": "çok yüksek",
  hesaplanamadi: "belirsiz",
};

export default function DashboardPage() {
  const auth = useAuth();
  const { data, loading, error, refetch } = useDashboard();

  if (loading) {
    return <LoadingState label="Dashboard yukleniyor" />;
  }

  if (error || !data) {
    return <ErrorState message={error ?? "Dashboard verisi bos dondu."} onRetry={refetch} />;
  }

  const levelKey = data.risk.risk_level.toLowerCase();
  const levelWord = RISK_LEVEL_LABEL[levelKey] ?? data.risk.risk_level;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold app-heading">
          Portföyün sağlıklı, <span className="text-[var(--color-cta)]">{auth.user?.first_name ?? "Yatırımcı"}</span> 👋
        </h1>
        <p className="mt-1 text-sm app-muted">
          Risk skorun <span className="font-medium">{levelWord}</span> bölgede · Danışman motoru portföyünü izliyor.
        </p>
      </div>
      <SummaryCards data={data} />
      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <AssetAllocationChart items={data.allocation} />
        <RiskScoreCard risk={data.risk} />
      </div>
      <MarketInsightList movers={data.movers} />
    </div>
  );
}
