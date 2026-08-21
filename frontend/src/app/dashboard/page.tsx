"use client";

import { useState } from "react";
import { SummaryCards } from "../../components/dashboard/SummaryCards";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { AssetTable } from "../../components/portfolio/AssetTable";
import {
  PortfolioVisualization,
  type PortfolioViewMode,
} from "../../components/portfolio/PortfolioVisualization";
import { RecommendationList } from "../../components/risk/RecommendationList";
import { RiskScoreCard } from "../../components/risk/RiskScoreCard";
import { useAuth } from "../../hooks/useAuth";
import { useDashboard } from "../../hooks/useDashboard";
import { usePortfolioPerformance } from "../../hooks/usePortfolio";
import { useLanguage } from "../../contexts/LanguageContext";

const RISK_LEVEL_LABEL: Record<string, string> = {
  dusuk: "düşük",
  orta: "orta",
  yuksek: "yüksek",
  "cok yuksek": "çok yüksek",
  hesaplanamadi: "belirsiz",
};

export default function DashboardPage() {
  const { language } = useLanguage();
  const [portfolioViewMode, setPortfolioViewMode] = useState<PortfolioViewMode>("line");
  const auth = useAuth();
  const dashboard = useDashboard();
  const performance = usePortfolioPerformance(24);

  if (dashboard.loading) {
    return <LoadingState label={language === "tr" ? "Genel bakış yükleniyor" : "Loading overview"} />;
  }

  if (dashboard.error || !dashboard.data) {
    return (
      <ErrorState
        message={dashboard.error ?? (language === "tr" ? "Genel bakış verisi boş döndü." : "Overview data is empty.")}
        onRetry={dashboard.refetch}
      />
    );
  }

  const data = dashboard.data;
  const levelKey = data.risk.risk_level.toLowerCase();
  const levelWord = RISK_LEVEL_LABEL[levelKey] ?? data.risk.risk_level;
  const englishLevelLabels: Record<string, string> = {
    dusuk: "low",
    orta: "medium",
    yuksek: "high",
    "cok yuksek": "very high",
    hesaplanamadi: "unavailable",
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold app-heading">
          {language === "tr" ? "Portföyün ve genel görünümün," : "Your portfolio overview,"}{" "}
          <span className="text-[var(--color-cta)]">
            {auth.user?.first_name ?? (language === "tr" ? "Yatırımcı" : "Investor")}
          </span>
        </h1>
        <p className="mt-1 text-sm app-muted">
          {language === "tr" ? (
            <>Risk skorun <span className="font-medium">{levelWord}</span> bölgede. Varlıkların, dağılımın ve performansın tek ekranda izleniyor.</>
          ) : (
            <>Your risk score is in the <span className="font-medium">{englishLevelLabels[levelKey] ?? levelKey}</span> range. Your assets, allocation and performance are shown in one view.</>
          )}
        </p>
      </div>

      <SummaryCards data={data} />

      <div className="portfolio-view-layout" data-mode={portfolioViewMode}>
        <PortfolioVisualization
          holdings={data.holdings}
          performancePoints={performance.data?.points ?? []}
          performanceLoading={performance.loading}
          performanceError={performance.error}
          mode={portfolioViewMode}
          onModeChange={setPortfolioViewMode}
        />
        <div className="portfolio-assets-panel min-w-0">
          <AssetTable items={data.holdings} />
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[.8fr_1.2fr]">
        <RiskScoreCard risk={data.risk} />
        <RecommendationList risk={data.risk} />
      </div>
    </div>
  );
}
