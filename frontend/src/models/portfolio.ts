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
};

export type PortfolioValueSnapshotPoint = {
  ts: string;
  holdings_value_try: number;
  cash_value_try: number;
  total_value_try: number;
};

export type PortfolioSnapshotPerformanceResponse = {
  points: PortfolioValueSnapshotPoint[];
  hours: number;
  interval_minutes: number;
};
