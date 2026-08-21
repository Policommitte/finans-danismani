import type { Asset } from "../../models/market";
import Card from "../ui/Card";
import { useLanguage } from "../../contexts/LanguageContext";

export function MarketInsightList({ movers }: { movers: Asset[] }) {
  const { language } = useLanguage();
  return (
    <Card title={language === "tr" ? "Piyasa hareketleri" : "Market movers"}>
      <div className="divide-y app-border-soft">
        {movers.slice(0, 6).map((asset) => (
          <div key={asset.symbol} className="flex items-center justify-between py-3 text-sm">
            <div>
              <div className="font-medium app-heading">{asset.symbol}</div>
              <div className="app-muted">{asset.name}</div>
            </div>
            <div className={asset.daily_change_pct && asset.daily_change_pct < 0 ? "app-danger" : "app-success"}>
              {asset.daily_change_pct == null ? "-" : `%${asset.daily_change_pct.toFixed(2)}`}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
