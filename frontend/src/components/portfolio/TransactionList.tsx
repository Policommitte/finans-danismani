import type { Transaction } from "../../models/portfolio";
import Card from "../ui/Card";
import { useLanguage } from "../../contexts/LanguageContext";

export function TransactionList({ items }: { items: Transaction[] }) {
  const { language } = useLanguage();
  const transactionLabels: Record<string, { tr: string; en: string }> = {
    BUY: { tr: "Alış", en: "Buy" },
    SELL: { tr: "Satış", en: "Sell" },
  };
  return (
    <Card title={language === "tr" ? "Son işlemler" : "Recent transactions"}>
      <div className="space-y-3">
        {items.map((transaction) => (
          <div key={transaction.id} className="flex items-center justify-between rounded-md app-card-muted px-3 py-2 text-sm">
            <div>
              <div className="font-medium app-heading">{transaction.symbol}</div>
              <div className="app-muted">{transaction.transaction_date}</div>
            </div>
            <div className="text-right">
              <div className="font-medium">
                {transactionLabels[transaction.transaction_type.toUpperCase()]?.[language] ?? transaction.transaction_type}
              </div>
              <div className="app-muted">{transaction.quantity} {language === "tr" ? "adet" : "units"}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
