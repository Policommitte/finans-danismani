"use client";

import { useEffect, useState } from "react";
import { SummaryCards } from "../../components/dashboard/SummaryCards";
import { CompletedTrades } from "../../components/dashboard/CompletedTrades";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { AssetTable } from "../../components/portfolio/AssetTable";
import {
  PortfolioVisualization,
  type DisplayCurrency,
  type PortfolioFxRates,
  type PortfolioViewMode,
} from "../../components/portfolio/PortfolioVisualization";
import { PeriodSelector } from "../../components/dashboard/PeriodSelector";
import type { PerformanceRange } from "../../models/portfolio";
import { RecommendationList } from "../../components/risk/RecommendationList";
import { RiskScoreCard } from "../../components/risk/RiskScoreCard";
import { useAuth } from "../../hooks/useAuth";
import { useDashboard } from "../../hooks/useDashboard";
import { usePortfolioPerformance, usePortfolioSnapshots } from "../../hooks/usePortfolio";
import { useLanguage } from "../../contexts/LanguageContext";
import { DASHBOARD_READY_EVENT } from "../../components/layout/transitionEvents";
import { getPublicMarketTicker } from "../../services/marketService";

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
  const [displayCurrency, setDisplayCurrency] = useState<DisplayCurrency>("TRY");
  const [fxRates, setFxRates] = useState<PortfolioFxRates>({ USD: null, EUR: null });
  const auth = useAuth();
  const dashboard = useDashboard();
  //: Donem TEK yerde tutulur: grafik, "Donem Degisimi" karti ve varlik
  //: tablosunun kar/zarar sutunu ayni istekten beslenir, boylece uc yerde
  //: farkli donemlere ait rakam gorunmesi mumkun degil.
  const [range, setRange] = useState<PerformanceRange>("1G");
  const performance = usePortfolioPerformance(range);
  //: 1G'de grafik scheduler'in OLCTUGU snapshot'lari cizer: nakit dahil,
  //: emirler islendikten sonra alindigi icin yeniden hesaplanan seriden
  //: dogru. Ama snapshot 30 gun saklanip 720 saatle sinirli oldugundan
  //: 1H/1A/1Y'yi besleyemez - orada yeniden kurulan seriye duseriz.
  const gunIci = range === "1G";
  const snapshots = usePortfolioSnapshots(gunIci);

  //: Grafik tek bir bicim bekler; uzun aralik serisi snapshot bicimine
  //: cevrilir. Nakit ayrimi yalnizca snapshot'ta var, digerinde toplam
  //: dogrudan varlik degeridir.
  const grafikNoktalari = gunIci
    ? (snapshots.data?.points ?? [])
    : (performance.data?.points ?? []).map((nokta) => ({
        ts: nokta.ts,
        holdings_value_try: nokta.total_value_try,
        cash_value_try: 0,
        total_value_try: nokta.total_value_try,
      }));
  const grafikYukleniyor = gunIci ? snapshots.loading : performance.loading;
  const grafikHatasi = gunIci ? snapshots.error : performance.error;
  const conversionDivisor = displayCurrency === "TRY" ? 1 : (fxRates[displayCurrency] ?? 1);

  useEffect(() => {
    let active = true;

    async function loadFxRates() {
      try {
        const response = await getPublicMarketTicker();
        const findRate = (symbol: string) => response.items.find(
          (item) => item.symbol.replace(/[^A-Z]/gi, "").toUpperCase() === symbol,
        )?.value;
        const usdTry = findRate("USDTRY");
        const eurTry = findRate("EURTRY");

        if (active && usdTry && eurTry) {
          setFxRates({ USD: usdTry, EUR: eurTry });
        }
      } catch {
        // TRY remains available when current FX rates cannot be loaded.
      }
    }

    void loadFxRates();
    const timer = window.setInterval(loadFxRates, 60_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (dashboard.loading || performance.loading || snapshots.loading) {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      document.documentElement.dataset.dashboardReady = "true";
      window.dispatchEvent(new Event(DASHBOARD_READY_EVENT));
    });

    return () => window.cancelAnimationFrame(frame);
  }, [dashboard.loading, performance.loading, snapshots.loading]);

  if (dashboard.loading && !dashboard.data) {
    return <LoadingState label={language === "tr" ? "Genel bakış yükleniyor" : "Loading overview"} />;
  }

  if (!dashboard.data) {
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
      {dashboard.error ? (
        <div role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-lg border app-warning-box px-4 py-3 text-sm">
          <span>
            {language === "tr"
              ? "Veriler geçici olarak güncellenemedi. Son başarılı veriler gösteriliyor."
              : "Data could not be refreshed temporarily. The last successful data is shown."}
          </span>
          <button
            type="button"
            className="font-semibold underline underline-offset-4"
            onClick={() => void dashboard.refetch()}
          >
            {language === "tr" ? "Tekrar dene" : "Retry"}
          </button>
        </div>
      ) : null}
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

      {/* Donem secici kartlarin USTUNDE ve saga yasli: sag ustteki Risk
          Skoru kartinin hemen ustune denk gelir, dort kartin da ustunde
          durdugu icin "bu ekran su donemi gosteriyor" mesajini verir. */}
      <div className="flex justify-end">
        <PeriodSelector
          deger={range}
          onDegis={setRange}
          yukleniyor={performance.loading}
          language={language}
        />
      </div>

      <SummaryCards
        data={data}
        displayCurrency={displayCurrency}
        conversionDivisor={conversionDivisor}
        range={range}
        periodChangeTry={performance.data?.change_try ?? null}
        periodChangePct={performance.data?.change_pct ?? null}
        periodLoading={performance.loading}
      />

      <div className="portfolio-view-layout" data-mode={portfolioViewMode}>
        <PortfolioVisualization
          holdings={data.holdings}
          cashTotalTry={(data.cash_account?.available_balance ?? 0) + (data.cash_account?.reserved_balance ?? 0)}
          range={range}
          periodChangeTry={performance.data?.change_try ?? null}
          periodChangePct={performance.data?.change_pct ?? null}
          performancePoints={grafikNoktalari}
          performanceLoading={grafikYukleniyor}
          performanceError={grafikHatasi}
          mode={portfolioViewMode}
          onModeChange={setPortfolioViewMode}
          displayCurrency={displayCurrency}
          onDisplayCurrencyChange={setDisplayCurrency}
          fxRates={fxRates}
        />
        <div className="portfolio-assets-panel min-w-0" data-tour="portfolio-section">
          <AssetTable
            items={data.holdings}
            cashAccount={data.cash_account}
            displayCurrency={displayCurrency}
            conversionDivisor={conversionDivisor}
            range={range}
            symbolPnl={performance.data?.symbol_pnl ?? []}
            periodLoading={performance.loading}
          />
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[.8fr_1.2fr]">
        <RiskScoreCard risk={data.risk} />
        <RecommendationList risk={data.risk} />
      </div>

      <CompletedTrades items={data.orders} />
    </div>
  );
}
