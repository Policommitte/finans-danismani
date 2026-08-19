import type { Transaction } from "../../models/portfolio";
import Card from "../ui/Card";

export function TransactionList({ items }: { items: Transaction[] }) {
  return (
    <Card title="Son islemler">
      <div className="space-y-3">
        {items.map((transaction) => (
          <div key={transaction.id} className="flex items-center justify-between rounded-md app-card-muted px-3 py-2 text-sm">
            <div>
              <div className="font-medium app-heading">{transaction.symbol}</div>
              <div className="app-muted">{transaction.transaction_date}</div>
            </div>
            <div className="text-right">
              <div className="font-medium">{transaction.transaction_type}</div>
              <div className="app-muted">{transaction.quantity} adet</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
