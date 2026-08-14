"use client";

import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { AssetAllocationChart } from "../../components/portfolio/AssetAllocationChart";
import { AssetTable } from "../../components/portfolio/AssetTable";
import { TransactionList } from "../../components/portfolio/TransactionList";
import Card from "../../components/ui/Card";
import { usePortfolio } from "../../hooks/usePortfolio";

const money = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 0,
});

export default function PortfolioPage() {
  const { data, loading, error, refetch } = usePortfolio();

  if (loading) {
    return <LoadingState label="Portfoy yukleniyor" />;
  }

  if (error || !data) {
    return <ErrorState message={error ?? "Portfoy verisi bos dondu."} onRetry={refetch} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Portfoy</h1>
        <p className="mt-1 text-sm text-slate-500">Varliklar, dagilim ve son islemler.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <div className="text-xs uppercase text-slate-500">Toplam deger</div>
          <div className="mt-2 text-2xl font-semibold">{money.format(data.summary.total_value_try)}</div>
        </Card>
        <Card>
          <div className="text-xs uppercase text-slate-500">Toplam maliyet</div>
          <div className="mt-2 text-2xl font-semibold">{money.format(data.summary.total_cost_try)}</div>
        </Card>
        <Card>
          <div className="text-xs uppercase text-slate-500">Kar / zarar</div>
          <div className={`mt-2 text-2xl font-semibold ${data.summary.total_pnl_try < 0 ? "text-red-600" : "text-emerald-700"}`}>
            {money.format(data.summary.total_pnl_try)}
          </div>
        </Card>
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.4fr_.8fr]">
        <AssetTable items={data.holdings.items} />
        <AssetAllocationChart items={data.allocation.items} />
      </div>
      <TransactionList items={data.transactions.items} />
    </div>
  );
}
