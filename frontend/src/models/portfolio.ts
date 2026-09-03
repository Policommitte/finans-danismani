export type PortfolioSummary = {
  portfolio_id: number | null;
  holding_count: number;
  total_value_try: number;
  total_cost_try: number;
  total_pnl_try: number;
  total_pnl_pct: number | null;
  daily_change_try: number;
  daily_change_pct: number | null;
};

/** Performans grafiginin donem secenekleri (backend ile AYNI anahtarlar). */
export type PerformanceRange = "1G" | "1H" | "1A" | "1Y";

/**
 * Tek bir varligin SECILEN DONEMDEKI kar/zarari.
 *
 * `Holding.pnl_try` ile karistirilmamali: o, alim gununden bugune TOPLAM
 * kar/zarardir ve donemden bagimsizdir.
 */
export type SymbolPeriodPnl = {
  symbol: string;
  pnl_try: number;
  pnl_pct: number | null;
};

export type Holding = {
  symbol: string;
  asset_name: string;
  asset_class: string;
  currency: string;
  quantity: number;
  average_buy_price: number;
  current_price: number;
  daily_change_pct: number | null;
  daily_change_try: number;
  daily_change_pct_try: number | null;
  market_value_try: number;
  cost_basis_try: number;
  pnl_try: number;
  pnl_pct: number | null;
};

export type HoldingsResponse = {
  items: Holding[];
  total_value_try: number;
};

export type AllocationSlice = {
  asset_class: string;
  class_value_try: number;
  class_pct: number;
};

export type AllocationResponse = {
  items: AllocationSlice[];
};

export type Transaction = {
  id: number;
  symbol: string;
  asset_name: string;
  transaction_type: string;
  quantity: number;
  unit_price: number;
  transaction_date: string;
};

export type TransactionsResponse = {
  items: Transaction[];
  limit: number;
};

export type PortfolioPerformancePoint = {
  ts: string;
  total_value_try: number;
  bist100_value_try: number | null;
};

export type PortfolioPerformanceResponse = {
  points: PortfolioPerformancePoint[];
  hours: number;
  range_key: PerformanceRange;
  /** Donem boyunca portfoyun kar/zarari (alim maliyeti dusulmus). */
  change_try: number;
  change_pct: number | null;
  symbol_pnl: SymbolPeriodPnl[];
};
