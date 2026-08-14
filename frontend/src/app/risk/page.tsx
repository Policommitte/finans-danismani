"use client";

import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { RecommendationList } from "../../components/risk/RecommendationList";
import { RiskScoreCard } from "../../components/risk/RiskScoreCard";
import { useRisk } from "../../hooks/useRisk";

export default function RiskPage() {
  const { data, loading, error, refetch } = useRisk();

  if (loading) {
    return <LoadingState label="Risk profili yukleniyor" />;
  }

  if (error || !data) {
    return <ErrorState message={error ?? "Risk verisi bos dondu."} onRetry={refetch} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Risk</h1>
        <p className="mt-1 text-sm text-slate-500">Portfoy risk skoru ve strateji onerileri.</p>
      </div>
      <RiskScoreCard risk={data} />
      <RecommendationList risk={data} />
    </div>
  );
}
