import Link from "next/link";
import type { DashboardSummaryResponse } from "../../models/dashboard";
import type { PerformanceRange } from "../../models/portfolio";
import type { RecommendationListResponse } from "../../models/recommendation";
import { useLanguage } from "../../contexts/LanguageContext";
import type { DisplayCurrency } from "../portfolio/PortfolioVisualization";

function BoltIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 2 4 14h6l-1 8 9-12h-6z" />
    </svg>
  );
}

//: Kart basligi secilen doneme gore degisir - "Gunluk Degisim" yazip
//: yillik rakam gostermek en kotu secenek olurdu.
const DONEM_BASLIGI: Record<PerformanceRange, { tr: string; en: string }> = {
  "1G": { tr: "Günlük Değişim", en: "Daily Change" },
  "1H": { tr: "Haftalık Değişim", en: "Weekly Change" },
  "1A": { tr: "Aylık Değişim", en: "Monthly Change" },
  "1Y": { tr: "Yıllık Değişim", en: "Yearly Change" },
};

export function SummaryCards({
  data,
  displayCurrency,
  conversionDivisor,
  range,
  periodChangeTry,
  periodChangePct,
  periodLoading,
  currentTotalTry,
  recommendations,
}: {
  data: DashboardSummaryResponse;
  displayCurrency: DisplayCurrency;
  conversionDivisor: number;
  range: PerformanceRange;
  /** Donem kar/zarari; veri henuz gelmediyse null. */
  periodChangeTry: number | null;
  periodChangePct: number | null;
  periodLoading: boolean;
  /** Grafikle ortak, son basarili snapshot'taki nakit dahil toplam. */
  currentTotalTry: number | null;
  /** Bekleyen (PUBLISHED) otonom oneriler - null ise henuz yuklenmedi. */
  recommendations: RecommendationListResponse | null;
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
  const netWorth = currentTotalTry ?? investedValue + totalCash;
  const displayedInvestedValue = Math.max(0, netWorth - totalCash);

  // Donem verisi gelene kadar ozetteki gunluk rakama duseriz: kart bos
  // yanip sonmesin, secim degistiginde yalnizca solar.
  const changeTry = periodChangeTry ?? summary?.daily_change_try ?? 0;
  const changePct = periodChangePct ?? summary?.daily_change_pct ?? null;
  const changeUp = changeTry >= 0;

  const topRecommendation = recommendations?.items[0] ?? null;
  const pendingCount = recommendations?.counts?.PUBLISHED ?? 0;
  const isBuy = topRecommendation?.side === "BUY";

  //: Kar/zarar yonune gore hafif, ama musterinin RAHATCA fark edecegi bir
  //: renk vurgusu. `--color-panel-dark` KOYU MAVI oldugu icin kirmizi
  //: onun uzerine karisinca mor'a kayiyordu (kirmizi+mavi=mor) - bunun
  //: yerine notr, neredeyse siyah `--color-panel-dark-alt` uzerine
  //: karistiriliyor, boylece kirmizi kirmizi, yesil yesil kaliyor.
  //: Veri gelmeden notr lacivert kalir; `total_pnl_try` degistiginde
  //: (yeni fiyat/emir) gecis animasyonlu.
  const netWorthTintColor = summary
    ? isUp
      ? "color-mix(in srgb, var(--color-success) 32%, var(--color-panel-dark-alt))"
      : "color-mix(in srgb, var(--color-danger) 32%, var(--color-panel-dark-alt))"
    : "var(--color-panel-dark)";

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <div
        className="relative overflow-hidden rounded-xl p-5 text-white shadow-lg transition-colors duration-700"
        style={{ backgroundColor: netWorthTintColor }}
      >
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
            {language === "tr" ? "Varlıklar" : "Assets"}: {currency.format(displayedInvestedValue / conversionDivisor)} · {language === "tr" ? "Nakit" : "Cash"}: {currency.format(totalCash / conversionDivisor)}
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
          {DONEM_BASLIGI[range][language]}
        </div>
        <div
          className={`mt-3 text-2xl font-semibold app-heading transition-opacity ${
            periodLoading ? "opacity-50" : ""
          }`}
        >
          {summary ? `${changeUp ? "+" : ""}${currency.format(changeTry / conversionDivisor)}` : "—"}
        </div>
        <span className={`mt-3 inline-flex items-center gap-1 text-sm font-semibold ${changeUp ? "app-success" : "app-danger"}`}>
          {changePct == null
            ? language === "tr" ? "Veri yok" : "No data"
            : `${changeUp ? "▲" : "▼"} %${pct.format(Math.abs(changePct))}`}
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

      <Link
        href="/market?mode=otonom"
        className="group relative overflow-hidden rounded-xl border app-card p-5 shadow-sm transition hover:border-[var(--color-primary)]"
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-medium app-muted">
            <span className="grid h-8 w-8 place-items-center rounded-lg app-primary-soft">
              <BoltIcon />
            </span>
            {language === "tr" ? "Otonom Öneriler" : "Autonomous Recommendations"}
          </div>
          <span className="text-lg app-muted transition group-hover:translate-x-1" aria-hidden="true">→</span>
        </div>

        {recommendations === null ? (
          <div className="mt-3 text-2xl font-semibold app-heading">—</div>
        ) : topRecommendation ? (
          <>
            <div className="mt-3 flex items-center gap-2">
              <span
                className={`rounded-md px-2 py-0.5 text-xs font-bold text-white ${isBuy ? "bg-emerald-600" : "bg-rose-600"}`}
              >
                {isBuy ? (language === "tr" ? "AL" : "BUY") : language === "tr" ? "SAT" : "SELL"}
              </span>
              <span className="text-2xl font-semibold app-heading">{topRecommendation.asset_symbol}</span>
            </div>
            <p className="mt-3 text-sm app-muted">
              {currency.format(topRecommendation.estimated_amount / conversionDivisor)}
              {pendingCount > 1 && (
                <> · {language === "tr" ? `+${pendingCount - 1} öneri daha` : `+${pendingCount - 1} more`}</>
              )}
            </p>
          </>
        ) : (
          <p className="mt-3 text-sm app-muted">
            {language === "tr" ? "Şu an aktif bir öneri yok." : "No active recommendation right now."}
          </p>
        )}
      </Link>
    </div>
  );
}
