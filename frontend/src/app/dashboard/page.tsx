"use client";

import { MarketInsightList } from "../../components/dashboard/MarketInsightList";
import { SummaryCards } from "../../components/dashboard/SummaryCards";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { AssetTable } from "../../components/portfolio/AssetTable";
import { PortfolioVisualization } from "../../components/portfolio/PortfolioVisualization";
import { TransactionList } from "../../components/portfolio/TransactionList";
import { RecommendationList } from "../../components/risk/RecommendationList";
import { RiskScoreCard } from "../../components/risk/RiskScoreCard";
import { useAuth } from "../../hooks/useAuth";
import { useDashboard } from "../../hooks/useDashboard";
import { usePortfolioPerformance, usePortfolioTransactions } from "../../hooks/usePortfolio";
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
  const auth = useAuth();
  const dashboard = useDashboard();
  const performance = usePortfolioPerformance(24);
  const transactions = usePortfolioTransactions(20);

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
            <>Risk skorun <span className="font-medium">{levelWord}</span> bölgede. Varlıkların, dağılımın ve son işlemlerin tek ekranda izleniyor.</>
          ) : (
            <>Your risk score is in the <span className="font-medium">{englishLevelLabels[levelKey] ?? levelKey}</span> range. Your assets, allocation and recent transactions are shown in one view.</>
          )}
        </p>
      </div>

      <SummaryCards data={data} />

      <div className="grid items-stretch gap-6 xl:grid-cols-[1.25fr_.75fr]">
        <PortfolioVisualization
          holdings={data.holdings}
          performancePoints={performance.data?.points ?? []}
          performanceLoading={performance.loading}
          performanceError={performance.error}
        />
        <div data-tour="portfolio-section">
          <AssetTable items={data.holdings} />
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[.8fr_1.2fr]">
        <RiskScoreCard risk={data.risk} />
        <RecommendationList risk={data.risk} />
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-2">
        {transactions.loading ? (
          <LoadingState label={language === "tr" ? "İşlem geçmişi yükleniyor" : "Loading transaction history"} />
        ) : transactions.error || !transactions.data ? (
          <ErrorState
            message={transactions.error ?? (language === "tr" ? "İşlem geçmişi boş döndü." : "Transaction history is empty.")}
            onRetry={transactions.refetch}
          />
        ) : (
          <TransactionList items={transactions.data.items} />
        )}
        <MarketInsightList movers={data.movers} />
      </div>
    </div>
  );
}
