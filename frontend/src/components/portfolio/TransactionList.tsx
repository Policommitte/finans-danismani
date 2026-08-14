import type { Transaction } from "../../models/portfolio";
import Card from "../ui/Card";

export function TransactionList({ items }: { items: Transaction[] }) {
  return (
    <Card title="Son islemler">
      <div className="space-y-3">
        {items.map((transaction) => (
          <div key={transaction.id} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
            <div>
              <div className="font-medium text-slate-900">{transaction.symbol}</div>
              <div className="text-slate-500">{transaction.transaction_date}</div>
            </div>
            <div className="text-right">
              <div className="font-medium">{transaction.transaction_type}</div>
              <div className="text-slate-500">{transaction.quantity} adet</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
