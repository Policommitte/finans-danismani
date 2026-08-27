import type { PaperOrder } from "../../models/trading";
import Card from "../ui/Card";
import { useLanguage } from "../../contexts/LanguageContext";
import { localizeTradingMessage } from "../../utils/tradingMessages";

const statusLabel = {
  tr: { PENDING: "Bekliyor", FILLED: "Gerçekleşti", REJECTED: "Reddedildi", CANCELLED: "İptal edildi" },
  en: { PENDING: "Pending", FILLED: "Filled", REJECTED: "Rejected", CANCELLED: "Cancelled" },
} as const;

const statusClass = {
  PENDING: "bg-amber-100 text-amber-800",
  FILLED: "bg-emerald-100 text-emerald-800",
  REJECTED: "bg-rose-100 text-rose-800",
  CANCELLED: "bg-slate-100 text-slate-700",
};

type Props = {
  items: PaperOrder[];
  submitting: boolean;
  onCancel: (orderId: number) => void;
};

export function OrderList({ items, submitting, onCancel }: Props) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const money = new Intl.NumberFormat(locale, { style: "currency", currency: "TRY" });

  return (
    <Card title={language === "tr" ? "Sanal Emirler" : "Virtual Orders"} className="!border-0 !p-0 !shadow-none">
      {items.length === 0 ? (
        <p className="text-sm app-muted">{language === "tr" ? "Henüz bir sanal emir oluşturulmadı." : "No virtual orders have been created yet."}</p>
      ) : (
        <div className="max-h-80 divide-y overflow-y-auto app-border-soft">
          {items.map((order) => (
            <div key={order.id} className="py-3 first:pt-0 last:pb-0">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold app-heading">
                    {order.symbol} · {order.side === "BUY" ? (language === "tr" ? "AL" : "BUY") : (language === "tr" ? "SAT" : "SELL")}
                  </p>
                  <p className="mt-0.5 text-xs app-muted">
                    {order.quantity} {language === "tr" ? "adet" : "units"} · {order.average_fill_price == null
                      ? `${language === "tr" ? "referans" : "reference"} ${money.format(order.quoted_price)}`
                      : money.format(order.average_fill_price)}
                  </p>
                  <p className="mt-0.5 text-xs app-muted">
                    {order.order_type === "LIMIT"
                      ? `${language === "tr" ? "Limit" : "Limit"} ${money.format(order.limit_price ?? 0)} · ${order.validity === "DAY" ? (language === "tr" ? "Gün sonu" : "Day") : (language === "tr" ? "İptale kadar" : "Good till cancelled")}`
                      : order.order_type === "STOP_MARKET"
                        ? `${language === "tr" ? "Koruyucu stop" : "Protective stop"} ${money.format(order.stop_loss_price ?? 0)}`
                        : (language === "tr" ? "Piyasa emri" : "Market order")}
                  </p>
                  {order.order_type !== "STOP_MARKET" && order.stop_loss_price != null && (
                    <p className="mt-0.5 text-xs text-emerald-700 dark:text-emerald-400">
                      {language === "tr" ? "Bağlı stop-loss" : "Attached stop-loss"}: {money.format(order.stop_loss_price)}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {order.status === "PENDING" && (
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={() => onCancel(order.id)}
                      className="rounded-md border app-border px-2 py-1 text-xs font-semibold app-danger disabled:opacity-50"
                    >
                      {language === "tr" ? "İptal" : "Cancel"}
                    </button>
                  )}
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass[order.status]}`}>
                    {statusLabel[language][order.status]}
                  </span>
                </div>
              </div>
              {order.rejection_reason && (
                <p className="mt-2 text-xs app-danger">
                  {localizeTradingMessage(order.rejection_reason, language)}
                </p>
              )}
              <p className="mt-1 text-xs app-muted">
                {new Date(order.created_at).toLocaleString(locale)}
              </p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
