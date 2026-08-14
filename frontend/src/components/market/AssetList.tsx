import type { Asset } from "../../models/market";
import Card from "../ui/Card";

export function AssetList({ items, onSelect }: { items: Asset[]; onSelect: (symbol: string) => void }) {
  return (
    <Card title="Piyasa varliklari">
      <div className="divide-y divide-slate-100">
        {items.map((asset) => (
          <button
            key={asset.symbol}
            className="flex w-full items-center justify-between py-3 text-left text-sm hover:bg-slate-50"
            onClick={() => onSelect(asset.symbol)}
          >
            <span>
              <span className="block font-medium text-slate-900">{asset.symbol}</span>
              <span className="text-slate-500">{asset.name}</span>
            </span>
            <span className="text-right">
              <span className="block font-medium">{asset.current_price}</span>
              <span className={asset.daily_change_pct && asset.daily_change_pct < 0 ? "text-red-600" : "text-emerald-700"}>
                {asset.daily_change_pct == null ? "-" : `%${asset.daily_change_pct.toFixed(2)}`}
              </span>
            </span>
          </button>
        ))}
      </div>
    </Card>
  );
}
