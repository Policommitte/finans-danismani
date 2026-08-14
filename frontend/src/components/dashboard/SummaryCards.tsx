import type { DashboardSummaryResponse } from "../../models/dashboard";
import Card from "../ui/Card";

const currency = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 0,
});

export function SummaryCards({ data }: { data: DashboardSummaryResponse }) {
  const summary = data.summary;
  const cards = [
    { label: "Toplam deger", value: summary ? currency.format(summary.total_value_try) : "-" },
    { label: "Kar / zarar", value: summary ? currency.format(summary.total_pnl_try) : "-" },
    { label: "Risk skoru", value: `${data.risk.risk_score}/100` },
    { label: "Varlik sayisi", value: String(summary?.holding_count ?? 0) },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <div className="text-xs font-medium uppercase text-slate-500">{card.label}</div>
          <div className="mt-2 text-2xl font-semibold text-slate-950">{card.value}</div>
        </Card>
      ))}
    </div>
  );
}
