import type { Holding } from "../../models/portfolio";
import Card from "../ui/Card";

const money = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 0,
});

export function AssetTable({ items }: { items: Holding[] }) {
  return (
    <Card title="Portfoy varliklari">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b app-border text-xs uppercase app-muted">
            <tr>
              <th className="py-2 pr-4">Sembol</th>
              <th className="py-2 pr-4">Tur</th>
              <th className="py-2 pr-4">Adet</th>
              <th className="py-2 pr-4">Deger</th>
              <th className="py-2 pr-4">Kar/Zarar</th>
            </tr>
          </thead>
          <tbody className="divide-y app-border-soft">
            {items.map((item) => (
              <tr key={item.symbol}>
                <td className="py-3 pr-4 font-medium app-heading">{item.symbol}</td>
                <td className="py-3 pr-4 app-muted">{item.asset_class}</td>
                <td className="py-3 pr-4 app-muted">{item.quantity}</td>
                <td className="py-3 pr-4 app-heading">{money.format(item.market_value_try)}</td>
                <td className={`py-3 pr-4 ${item.pnl_try < 0 ? "app-danger" : "app-success"}`}>
                  {money.format(item.pnl_try)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
