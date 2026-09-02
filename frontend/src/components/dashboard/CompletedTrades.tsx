"use client";

import { useMemo, useState } from "react";
import type { PaperOrder } from "../../models/trading";
import { useLanguage } from "../../contexts/LanguageContext";
import Card from "../ui/Card";

type OrderFilter = "ALL" | "BUY" | "SELL" | "PENDING";

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
  const [filter, setFilter] = useState<OrderFilter>("ALL");
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "TRY",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const quantity = new Intl.NumberFormat(locale, { maximumFractionDigits: 6 });
  const filteredItems = useMemo(() => items.filter((order) => {
    if (filter === "PENDING") return order.status === "PENDING";
    if (filter === "BUY" || filter === "SELL") return order.side === filter;
    return true;
  }), [filter, items]);
  const filters: Array<{ value: OrderFilter; tr: string; en: string; count: number }> = [
    { value: "ALL", tr: "Tümü", en: "All", count: items.length },
    { value: "BUY", tr: "Al", en: "Buy", count: items.filter((order) => order.side === "BUY").length },
    { value: "SELL", tr: "Sat", en: "Sell", count: items.filter((order) => order.side === "SELL").length },
    { value: "PENDING", tr: "Bekleyen", en: "Pending", count: items.filter((order) => order.status === "PENDING").length },
  ];

  return (
    <Card className="overflow-hidden !p-0">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b app-border px-5 py-4">
        <div>
          <h2 className="text-base font-semibold app-heading">
            {language === "tr" ? "İşlemler" : "Trades"}
          </h2>
          <p className="mt-1 text-sm app-muted">
            {language === "tr"
              ? "Gerçekleşen ve bekleyen alım-satım emirlerini görüntüleyin."
              : "View completed and pending buy and sell orders."}
          </p>
        </div>
        <div
          className="flex flex-wrap gap-1 rounded-lg border app-border app-card-muted p-1"
          role="group"
          aria-label={language === "tr" ? "İşlem filtresi" : "Trade filter"}
        >
          {filters.map((item) => (
            <button
              key={item.value}
              type="button"
              aria-pressed={filter === item.value}
              onClick={() => setFilter(item.value)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                filter === item.value
                  ? "bg-[var(--color-panel-dark)] text-white shadow-sm"
                  : "app-muted hover:text-[var(--color-heading)]"
              }`}
            >
              {item[language]} <span className="opacity-70">{item.count}</span>
            </button>
          ))}
        </div>
      </div>

      {filteredItems.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm app-muted">
          {items.length === 0
            ? (language === "tr" ? "Henüz bir sanal işlem bulunmuyor." : "There are no virtual trades yet.")
            : (language === "tr" ? "Bu filtreye uygun işlem bulunmuyor." : "There are no trades matching this filter.")}
        </p>
      ) : (
        <div
          className={filteredItems.length > 5 ? "max-h-[28rem] overflow-auto" : "overflow-x-auto"}
          tabIndex={filteredItems.length > 5 ? 0 : undefined}
          aria-label={filteredItems.length > 5 ? (language === "tr" ? "İşlemler listesi" : "Trades list") : undefined}
        >
          <table className="min-w-full text-left text-sm">
            <thead className="sticky top-0 z-10 app-card-muted text-xs uppercase app-muted shadow-[0_1px_0_var(--color-border)]">
              <tr>
                <th className="px-5 py-3">{language === "tr" ? "Varlık" : "Asset"}</th>
                <th className="px-5 py-3">{language === "tr" ? "İşlem" : "Trade"}</th>
                <th className="px-5 py-3">{language === "tr" ? "Adet" : "Quantity"}</th>
                <th className="px-5 py-3">{language === "tr" ? "Fiyat" : "Price"}</th>
                <th className="px-5 py-3">{language === "tr" ? "Komisyon" : "Commission"}</th>
                <th className="px-5 py-3">{language === "tr" ? "Net / Toplam" : "Net / Total"}</th>
                <th className="px-5 py-3">{language === "tr" ? "Tarih" : "Date"}</th>
              </tr>
            </thead>
            <tbody className="divide-y app-border-soft">
              {filteredItems.map((order) => {
                const pending = order.status === "PENDING";
                const displayedQuantity = pending ? order.quantity : order.filled_quantity;
                const displayedPrice = pending
                  ? (order.order_type === "LIMIT" ? order.limit_price : order.stop_loss_price) ?? order.quoted_price
                  : order.average_fill_price ?? order.quoted_price;
                const gross = displayedPrice * displayedQuantity;
                const total = order.side === "BUY" ? gross + order.commission : gross - order.commission;
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
                      {pending ? (
                        <span className="mt-1 inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
                          {language === "tr" ? "BEKLİYOR" : "PENDING"}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-5 py-4 app-heading">{quantity.format(displayedQuantity)}</td>
                    <td className="px-5 py-4 app-heading">{money.format(displayedPrice)}</td>
                    <td className="px-5 py-4 app-muted">{pending ? "—" : money.format(order.commission)}</td>
                    <td className="px-5 py-4 font-semibold app-heading">{pending ? "—" : money.format(total)}</td>
                    <td className="whitespace-nowrap px-5 py-4 app-muted">
                      {new Date(pending ? order.created_at : order.filled_at ?? order.created_at).toLocaleString(locale)}
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
