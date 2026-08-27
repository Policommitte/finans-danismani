export type OrderSide = "BUY" | "SELL";
export type OrderStatus = "PENDING" | "FILLED" | "REJECTED" | "CANCELLED";
export type EntryOrderType = "MARKET" | "LIMIT";
export type OrderType = EntryOrderType | "STOP_MARKET";
export type OrderValidity = "DAY" | "GTC";

export type TradingAccount = {
  portfolio_id: number;
  portfolio_name: string;
  currency: string;
  available_balance: number;
  reserved_balance: number;
};

export type OrderPreview = {
  symbol: string;
  asset_name: string;
  side: OrderSide;
  quantity: number;
  order_type: EntryOrderType;
  limit_price: number | null;
  stop_loss_price: number | null;
  validity: OrderValidity;
  expires_at: string | null;
  quoted_price: number;
  gross_amount: number;
  estimated_commission: number;
  estimated_total: number;
  estimated_reserve: number;
  available_balance: number;
  holding_quantity: number;
  price_updated_at: string | null;
  execution_note: string;
};

export type PaperOrder = {
  id: number;
  symbol: string;
  asset_name: string;
  side: OrderSide;
  order_type: OrderType;
  limit_price: number | null;
  stop_loss_price: number | null;
  parent_order_id: number | null;
  validity: OrderValidity;
  expires_at: string | null;
  quantity: number;
  quoted_price: number;
  status: OrderStatus;
  filled_quantity: number;
  average_fill_price: number | null;
  commission: number;
  rejection_reason: string | null;
  created_at: string;
  filled_at: string | null;
};

export type OrdersResponse = { items: PaperOrder[]; limit: number };
