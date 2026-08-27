import type { DashboardSummaryResponse } from "../../models/dashboard";
import { useLanguage } from "../../contexts/LanguageContext";
import { getRiskTone } from "../risk/riskTone";
import type { DisplayCurrency } from "../portfolio/PortfolioVisualization";

const RISK_LEVEL_LABEL: Record<string, string> = {
  dusuk: "Düşük risk bandında",
  orta: "Orta risk bandında",
  yuksek: "Yüksek risk bandında",
  "cok yuksek": "Çok yüksek risk bandında",
  hesaplanamadi: "Risk hesaplanamadı",
};

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
}

function RiskGauge({ score, color }: { score: number; color: string }) {
  const clamped = Math.max(0, Math.min(100, score));
  const angleEnd = 180 - (clamped / 100) * 180;
  const start = polar(50, 52, 42, 180);
  const end = polar(50, 52, 42, angleEnd);
  const needleEnd = polar(50, 52, 35, angleEnd);

  return (
    <svg viewBox="0 0 100 58" className="h-full w-full">
      <path d="M8 52 A42 42 0 0 1 92 52" fill="none" stroke="var(--color-chart-grid)" strokeWidth="9" strokeLinecap="round" />
      <path
        d={`M${start.x.toFixed(2)} ${start.y.toFixed(2)} A42 42 0 0 1 ${end.x.toFixed(2)} ${end.y.toFixed(2)}`}
        fill="none"
        stroke={color}
        strokeWidth="9"
        strokeLinecap="round"
      />
      <line x1="50" y1="52" x2={needleEnd.x.toFixed(2)} y2={needleEnd.y.toFixed(2)} stroke="var(--color-heading)" strokeWidth="3" strokeLinecap="round" />
      <circle cx="50" cy="52" r="4.5" fill="var(--color-heading)" />
    </svg>
  );
}

export function SummaryCards({
  data,
  displayCurrency,
  conversionDivisor,
}: {
  data: DashboardSummaryResponse;
  displayCurrency: DisplayCurrency;
  conversionDivisor: number;
}) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const currency = new Intl.NumberFormat(locale, { style: "currency", currency: displayCurrency, maximumFractionDigits: 0 });
  const pct = new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const summary = data.summary;
  const isUp = (summary?.total_pnl_try ?? 0) >= 0;
  const availableCash = data.cash_account?.available_balance ?? 0;
  const reservedCash = data.cash_account?.reserved_balance ?? 0;
  const totalCash = availableCash + reservedCash;
  const investedValue = summary?.total_value_try ?? 0;
  const netWorth = investedValue + totalCash;

  const dailyChangeTry = summary?.daily_change_try ?? 0;
  const dailyChangePct = summary?.daily_change_pct ?? null;
  const dailyUp = dailyChangeTry >= 0;

  const levelKey = data.risk.risk_level.toLowerCase();
  const englishRiskLabels: Record<string, string> = {
    dusuk: "Low risk range",
    orta: "Medium risk range",
    yuksek: "High risk range",
    "cok yuksek": "Very high risk range",
    hesaplanamadi: "Risk unavailable",
  };
  const levelLabel = language === "tr"
    ? RISK_LEVEL_LABEL[levelKey] ?? data.risk.risk_level
    : englishRiskLabels[levelKey] ?? data.risk.risk_level;
  const levelColor = getRiskTone(levelKey);

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <div className="relative overflow-hidden rounded-xl bg-[var(--color-panel-dark)] p-5 text-white shadow-lg">
        <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10 blur-2xl" />
        <div className="relative flex items-center gap-2 text-xs font-medium text-white/70">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-white/10">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12A9 9 0 1 1 12 3" />
              <path d="M21 3v6h-6" />
              <path d="M12 8v4l3 2" />
            </svg>
          </span>
          {language === "tr" ? "Toplam Portföy Değeri" : "Total Portfolio Value"}
        </div>
        <div className="relative mt-3 text-2xl font-semibold">
          {summary || data.cash_account ? currency.format(netWorth / conversionDivisor) : "—"}
        </div>
        {(summary || data.cash_account) && (
          <p className="relative mt-1 text-xs text-white/65">
            {language === "tr" ? "Varlıklar" : "Assets"}: {currency.format(investedValue / conversionDivisor)} · {language === "tr" ? "Nakit" : "Cash"}: {currency.format(totalCash / conversionDivisor)}
          </p>
        )}
        {summary && (
          <span
            className={`relative mt-3 inline-flex items-center gap-1 rounded-full bg-white/10 px-2.5 py-1 text-xs font-semibold ${
              isUp ? "app-success" : "app-danger"
            }`}
          >
            {isUp ? "▲" : "▼"} {currency.format(Math.abs(summary.total_pnl_try) / conversionDivisor)}
            {summary.total_pnl_pct != null && ` · %${pct.format(Math.abs(summary.total_pnl_pct))}`}
          </span>
        )}
      </div>

      <div className="rounded-xl border app-card p-5 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-medium app-muted">
          <span className="grid h-8 w-8 place-items-center rounded-lg app-primary-soft">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 8V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h2" />
              <rect x="11" y="8" width="10" height="12" rx="2" />
              <path d="M15 13v2" />
            </svg>
          </span>
          {language === "tr" ? "Günlük Değişim" : "Daily Change"}
        </div>
        <div className="mt-3 text-2xl font-semibold app-heading">
          {summary ? `${dailyUp ? "+" : ""}${currency.format(dailyChangeTry / conversionDivisor)}` : "—"}
        </div>
        <span className={`mt-3 inline-flex items-center gap-1 text-sm font-semibold ${dailyUp ? "app-success" : "app-danger"}`}>
          {dailyChangePct == null
            ? language === "tr" ? "Veri yok" : "No data"
            : `${dailyUp ? "▲" : "▼"} %${pct.format(Math.abs(dailyChangePct))}`}
        </span>
      </div>

      <div className="rounded-xl border app-card p-5 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-medium app-muted">
          <span className="grid h-8 w-8 place-items-center rounded-lg app-primary-soft">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="6" width="18" height="13" rx="2" />
              <path d="M16 11h5v4h-5a2 2 0 0 1 0-4Z" />
              <path d="M7 6V4h10v2" />
            </svg>
          </span>
          {language === "tr" ? "Toplam Likit Para" : "Total Liquid Cash"}
        </div>
        <div className="mt-3 text-2xl font-semibold app-heading">
          {data.cash_account ? currency.format(totalCash / conversionDivisor) : "—"}
        </div>
        {data.cash_account && (
          <div className="mt-3 space-y-1 text-xs app-muted">
            <div className="flex justify-between gap-3">
              <span>{language === "tr" ? "Kullanılabilir" : "Available"}</span>
              <strong className="app-heading">{currency.format(availableCash / conversionDivisor)}</strong>
            </div>
            <div className="flex justify-between gap-3">
              <span>{language === "tr" ? "Emirlerde bloke" : "Reserved for orders"}</span>
              <strong className="app-heading">{currency.format(reservedCash / conversionDivisor)}</strong>
            </div>
          </div>
        )}
      </div>

      <div className="relative overflow-hidden rounded-xl border app-card p-5 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-medium app-muted">
          <span className="grid h-8 w-8 place-items-center rounded-lg app-warning-box">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2l8 3.5v5c0 5-3.4 9.3-8 11-4.6-1.7-8-6-8-11v-5z" />
              <path d="M12 8v4" />
              <path d="M12 16h.01" />
            </svg>
          </span>
          {language === "tr" ? "Risk Skoru" : "Risk Score"}
        </div>
        <div className="mt-3 text-2xl font-semibold app-heading">
          {data.risk.risk_score}
          <span className="text-sm font-normal app-muted">/100</span>
        </div>
        <span className={`mt-3 inline-flex items-center text-sm font-semibold ${levelColor.textClass}`}>{levelLabel}</span>
        <div className="absolute right-4 top-4 h-16 w-24">
          <RiskGauge score={data.risk.risk_score} color={levelColor.color} />
        </div>
      </div>
    </div>
  );
}
