import type { Asset } from "../../models/market";
import Card from "../ui/Card";

export function MarketInsightList({ movers }: { movers: Asset[] }) {
  return (
    <Card title="Piyasa hareketleri">
      <div className="divide-y divide-slate-100">
        {movers.slice(0, 6).map((asset) => (
          <div key={asset.symbol} className="flex items-center justify-between py-3 text-sm">
            <div>
              <div className="font-medium text-slate-900">{asset.symbol}</div>
              <div className="text-slate-500">{asset.name}</div>
            </div>
            <div className={asset.daily_change_pct && asset.daily_change_pct < 0 ? "text-red-600" : "text-emerald-700"}>
              {asset.daily_change_pct == null ? "-" : `%${asset.daily_change_pct.toFixed(2)}`}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
