import type { PaperOrder } from "../../models/trading";
import { useLanguage } from "../../contexts/LanguageContext";
import Card from "../ui/Card";

function orderKind(order: PaperOrder, language: "tr" | "en") {
  if (order.order_type === "STOP_MARKET") {
    return language === "tr" ? "Stop-loss satışı" : "Stop-loss sale";
  }
  if (order.order_type === "LIMIT") {
    return language === "tr" ? "Limit emri" : "Limit order";
  }
  return language === "tr" ? "Piyasa emri" : "Market order";
}

export function CompletedTrades({ items }: { items: PaperOrder[] }) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "TRY",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const quantity = new Intl.NumberFormat(locale, { maximumFractionDigits: 6 });

  return (
    <Card className="overflow-hidden !p-0">
      <div className="border-b app-border px-5 py-4">
        <h2 className="text-base font-semibold app-heading">
          {language === "tr" ? "Gerçekleşen İşlemler" : "Completed Trades"}
        </h2>
        <p className="mt-1 text-sm app-muted">
          {language === "tr"
            ? "Yalnızca gerçekleşmiş alım ve satım işlemleri gösterilir."
            : "Only completed buy and sell transactions are shown."}
        </p>
      </div>

      {items.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm app-muted">
          {language === "tr"
            ? "Henüz gerçekleşmiş bir sanal işlem bulunmuyor."
            : "There are no completed virtual trades yet."}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="app-card-muted text-xs uppercase app-muted">
              <tr>
                <th className="px-5 py-3">{language === "tr" ? "Varlık" : "Asset"}</th>
                <th className="px-5 py-3">{language === "tr" ? "İşlem" : "Trade"}</th>
                <th className="px-5 py-3">{language === "tr" ? "Adet" : "Quantity"}</th>
                <th className="px-5 py-3">{language === "tr" ? "Gerçekleşme fiyatı" : "Fill price"}</th>
                <th className="px-5 py-3">{language === "tr" ? "Komisyon" : "Commission"}</th>
                <th className="px-5 py-3">{language === "tr" ? "Net / Toplam" : "Net / Total"}</th>
                <th className="px-5 py-3">{language === "tr" ? "Tarih" : "Date"}</th>
              </tr>
            </thead>
            <tbody className="divide-y app-border-soft">
              {items.map((order) => {
                const fillPrice = order.average_fill_price ?? order.quoted_price;
                const gross = fillPrice * order.filled_quantity;
                const total = order.side === "BUY"
                  ? gross + order.commission
                  : gross - order.commission;
                return (
                  <tr key={order.id}>
                    <td className="px-5 py-4">
                      <p className="font-semibold app-heading">{order.symbol}</p>
                      <p className="mt-0.5 text-xs app-muted">{order.asset_name}</p>
                    </td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                        order.side === "BUY"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300"
                          : "bg-rose-100 text-rose-800 dark:bg-rose-950/50 dark:text-rose-300"
                      }`}>
                        {order.side === "BUY"
                          ? (language === "tr" ? "AL" : "BUY")
                          : (language === "tr" ? "SAT" : "SELL")}
                      </span>
                      <p className="mt-1 text-xs app-muted">{orderKind(order, language)}</p>
                    </td>
                    <td className="px-5 py-4 app-heading">{quantity.format(order.filled_quantity)}</td>
                    <td className="px-5 py-4 app-heading">{money.format(fillPrice)}</td>
                    <td className="px-5 py-4 app-muted">{money.format(order.commission)}</td>
                    <td className="px-5 py-4 font-semibold app-heading">{money.format(total)}</td>
                    <td className="whitespace-nowrap px-5 py-4 app-muted">
                      {new Date(order.filled_at ?? order.created_at).toLocaleString(locale)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
