import type {
  OrderPreview,
  OrderSide,
  EntryOrderType,
  OrderValidity,
  OrdersResponse,
  PaperOrder,
  TradingAccount,
} from "../models/trading";
import { apiRequest } from "./apiClient";

export function getTradingAccount(): Promise<TradingAccount> {
  return apiRequest<TradingAccount>("/api/trading/account");
}

export function getPaperOrders(limit = 20): Promise<OrdersResponse> {
  return apiRequest<OrdersResponse>(`/api/trading/orders?limit=${limit}`);
}

export function previewPaperOrder(
  symbol: string,
  side: OrderSide,
  quantity: number,
  orderType: EntryOrderType,
  limitPrice: number | null,
  validity: OrderValidity,
  stopLossPrice: number | null,
): Promise<OrderPreview> {
  return apiRequest<OrderPreview>("/api/trading/orders/preview", {
    method: "POST",
    body: JSON.stringify({
      symbol, side, quantity, order_type: orderType,
      limit_price: orderType === "LIMIT" ? limitPrice : null,
      validity: orderType === "LIMIT" ? validity : "GTC",
      stop_loss_price: stopLossPrice,
    }),
  });
}

export function createPaperOrder(
  symbol: string,
  side: OrderSide,
  quantity: number,
  idempotencyKey: string,
  orderType: EntryOrderType,
  limitPrice: number | null,
  validity: OrderValidity,
  stopLossPrice: number | null,
): Promise<PaperOrder> {
  return apiRequest<PaperOrder>("/api/trading/orders", {
    method: "POST",
    body: JSON.stringify({
      symbol, side, quantity, idempotency_key: idempotencyKey,
      order_type: orderType,
      limit_price: orderType === "LIMIT" ? limitPrice : null,
      validity: orderType === "LIMIT" ? validity : "GTC",
      stop_loss_price: stopLossPrice,
    }),
  });
}

export async function createBasketMarketOrders(
  items: Array<{ symbol: string; quantity: number }>,
): Promise<PaperOrder[]> {
  if (items.length === 0) return [];

  const [account, previews] = await Promise.all([
    getTradingAccount(),
    Promise.all(
      items.map((item) =>
        previewPaperOrder(item.symbol, "BUY", item.quantity, "MARKET", null, "GTC", null),
      ),
    ),
  ]);
  const totalReserve = previews.reduce((total, preview) => total + preview.estimated_reserve, 0);
  if (totalReserve > account.available_balance) {
    throw new Error("Fiyat tamponu ve komisyon dahil sepet emirleri için kullanılabilir nakit yetersiz.");
  }

  const batchKey = crypto.randomUUID();
  const orders: PaperOrder[] = [];
  for (const [index, preview] of previews.entries()) {
    try {
      orders.push(
        await createPaperOrder(
          preview.symbol,
          "BUY",
          preview.quantity,
          `${batchKey}-${index}`,
          "MARKET",
          null,
          "GTC",
          null,
        ),
      );
    } catch (error) {
      const reason = error instanceof Error ? error.message : "Emir oluşturulamadı.";
      const rollbackResults = await Promise.allSettled(
        orders.map((order) => cancelPaperOrder(order.id)),
      );
      const rollbackFailures = rollbackResults.filter((result) => result.status === "rejected").length;
      throw new Error(
        rollbackFailures > 0
          ? `${orders.length - rollbackFailures} emir iptal edildi; ${rollbackFailures} emir iptal edilemedi. Emirler bölümünü kontrol et: ${reason}`
          : orders.length > 0
            ? `Sepet tamamlanamadığı için oluşturulan ${orders.length} emir otomatik iptal edildi: ${reason}`
            : reason,
      );
    }
  }
  return orders;
}

export function cancelPaperOrder(orderId: number): Promise<PaperOrder> {
  return apiRequest<PaperOrder>(`/api/trading/orders/${orderId}/cancel`, { method: "POST" });
}
