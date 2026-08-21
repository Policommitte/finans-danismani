import type { Asset } from "../../models/market";
import Card from "../ui/Card";

export function AssetList({ items, onSelect }: { items: Asset[]; onSelect: (symbol: string) => void }) {
  return (
    <Card title="Piyasa varliklari">
      <div className="divide-y app-border-soft">
        {items.map((asset) => (
          <button
            key={asset.symbol}
            className="flex w-full items-center justify-between py-3 text-left text-sm app-subtle-hover"
            onClick={() => onSelect(asset.symbol)}
          >
            <span>
              <span className="block font-medium app-heading">{asset.symbol}</span>
              <span className="app-muted">{asset.name}</span>
            </span>
            <span className="text-right">
              <span className="block font-medium">{asset.current_price}</span>
              <span className={asset.daily_change_pct && asset.daily_change_pct < 0 ? "app-danger" : "app-success"}>
                {asset.daily_change_pct == null ? "-" : `%${asset.daily_change_pct.toFixed(2)}`}
              </span>
            </span>
          </button>
        ))}
      </div>
    </Card>
  );
}
