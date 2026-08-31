import type { Holding } from "../../models/portfolio";
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

export function AssetTable({
  items,
  cashAccount,
  displayCurrency,
  conversionDivisor,
}: {
  items: Holding[];
  cashAccount?: TradingAccount | null;
  displayCurrency: DisplayCurrency;
  conversionDivisor: number;
}) {
  const { language } = useLanguage();
  const money = new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    style: "currency",
    currency: displayCurrency,
    maximumFractionDigits: 0,
  });
  return (
    <Card
      title={language === "tr" ? "Portföy varlıkları" : "Portfolio assets"}
      className="portfolio-assets-card h-full"
    >
      <div className="portfolio-assets-scroll">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b app-border text-xs uppercase app-muted">
            <tr>
              <th className="py-2 pr-4">{language === "tr" ? "Sembol" : "Symbol"}</th>
              <th className="py-2 pr-4">{language === "tr" ? "Tür" : "Type"}</th>
              <th className="py-2 pr-4">{language === "tr" ? "Adet" : "Quantity"}</th>
              <th className="py-2 pr-4">{language === "tr" ? "Değer" : "Value"}</th>
              <th className="py-2 pr-4">{language === "tr" ? "Kar/Zarar" : "P/L"}</th>
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
            {items.map((item) => (
              <tr key={item.symbol}>
                <td className="py-3 pr-4 font-medium app-heading">{item.symbol}</td>
                <td className="py-3 pr-4 app-muted">{getAssetClassLabel(item.asset_class, language)}</td>
                <td className="py-3 pr-4 app-muted">{item.quantity}</td>
                <td className="py-3 pr-4 app-heading">{money.format(item.market_value_try / conversionDivisor)}</td>
                <td className={`py-3 pr-4 ${item.pnl_try < 0 ? "app-danger" : "app-success"}`}>
                  {money.format(item.pnl_try / conversionDivisor)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
