import type { Holding, PerformanceRange, SymbolPeriodPnl } from "../../models/portfolio";
import Card from "../ui/Card";
import { useLanguage } from "../../contexts/LanguageContext";
import type { DisplayCurrency } from "./PortfolioVisualization";
import type { TradingAccount } from "../../models/trading";

const ASSET_CLASS_LABELS: Record<string, string> = {
  STOCK: "Hisse",
  USA_STOCK: "ABD hissesi",
  EU_STOCK: "Avrupa hissesi",
  CRYPTO: "Kripto",
  FOREX: "Döviz",
  GOLD: "Altın",
  BOND: "Tahvil",
  FUND: "Fon",
  ETF: "Borsa yatırım fonu",
  CASH: "Nakit",
  COMMODITY: "Emtia",
};

function getAssetClassLabel(assetClass: string, language: "tr" | "en"): string {
  return language === "tr" ? ASSET_CLASS_LABELS[assetClass.toUpperCase()] ?? assetClass : assetClass.replaceAll("_", " ");
}

const PERIOD_LABELS: Record<PerformanceRange, { tr: string; en: string }> = {
  "1G": { tr: "Günlük", en: "Daily" },
  "1H": { tr: "Haftalık", en: "Weekly" },
  "1A": { tr: "Aylık", en: "Monthly" },
  "1Y": { tr: "Yıllık", en: "Yearly" },
};

export function AssetTable({
  items,
  cashAccount,
  displayCurrency,
  conversionDivisor,
  range,
  symbolPnl,
  periodLoading,
}: {
  items: Holding[];
  cashAccount?: TradingAccount | null;
  displayCurrency: DisplayCurrency;
  conversionDivisor: number;
  range: PerformanceRange;
  /** Sembol -> donem kar/zarari. Bos gelirse sutun "—" gosterir. */
  symbolPnl: SymbolPeriodPnl[];
  periodLoading: boolean;
}) {
  const { language } = useLanguage();
  const periodPnlBySymbol = new Map(symbolPnl.map((s) => [s.symbol, s]));
  const money = new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    style: "currency",
    currency: displayCurrency,
    maximumFractionDigits: 0,
  });
  return (
    <Card
      title={language === "tr" ? "Portföy varlıkları" : "Portfolio assets"}
      className="portfolio-assets-card flex h-full min-h-0 flex-col"
    >
      <div className="portfolio-assets-scroll min-h-0 flex-1">
        <table className="min-w-full text-left text-sm">
          <thead className="sticky top-0 z-10 border-b bg-[var(--color-surface)] app-border text-xs uppercase app-muted">
            <tr>
              <th className="py-2 pr-4">{language === "tr" ? "Sembol" : "Symbol"}</th>
              <th className="py-2 pr-4">{language === "tr" ? "Tür" : "Type"}</th>
              <th className="py-2 pr-4">{language === "tr" ? "Adet" : "Quantity"}</th>
              <th className="py-2 pr-4">{language === "tr" ? "Değer" : "Value"}</th>
              <th className="py-2 pr-4">
                {language === "tr" ? "Kar/Zarar" : "P/L"}
                <span className="ml-1 normal-case app-muted">({PERIOD_LABELS[range][language]})</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y app-border-soft">
            {cashAccount && (
              <tr>
                <td className="py-3 pr-4 font-medium app-heading">{language === "tr" ? "NAKİT" : "CASH"}</td>
                <td className="py-3 pr-4 app-muted">{getAssetClassLabel("CASH", language)}</td>
                <td className="py-3 pr-4 app-muted">—</td>
                <td className="py-3 pr-4 app-heading">
                  {money.format((cashAccount.available_balance + cashAccount.reserved_balance) / conversionDivisor)}
                </td>
                <td className="py-3 pr-4 app-muted">—</td>
              </tr>
            )}
            {items.map((item) => {
              // Donem verisi gelmediyse (bellek ici yedek, ya da varlik
              // donem boyunca hic tutulmamis) uydurma rakam yerine "—".
              const pnl = periodPnlBySymbol.get(item.symbol);
              return (
                <tr key={item.symbol}>
                  <td className="py-3 pr-4 font-medium app-heading">{item.symbol}</td>
                  <td className="py-3 pr-4 app-muted">{getAssetClassLabel(item.asset_class, language)}</td>
                  <td className="py-3 pr-4 app-muted">{item.quantity}</td>
                  <td className="py-3 pr-4 app-heading">{money.format(item.market_value_try / conversionDivisor)}</td>
                  <td
                    className={`py-3 pr-4 transition-opacity ${periodLoading ? "opacity-50" : ""} ${
                      pnl == null ? "app-muted" : pnl.pnl_try < 0 ? "app-danger" : "app-success"
                    }`}
                  >
                    {pnl == null ? "—" : money.format(pnl.pnl_try / conversionDivisor)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
