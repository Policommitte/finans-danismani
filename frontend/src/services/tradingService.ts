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

export function cancelPaperOrder(orderId: number): Promise<PaperOrder> {
  return apiRequest<PaperOrder>(`/api/trading/orders/${orderId}/cancel`, { method: "POST" });
}
