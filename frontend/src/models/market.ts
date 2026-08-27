export type Asset = {
  symbol: string;
  name: string;
  asset_class: string;
  currency: string;
  current_price: number;
  daily_change_pct: number | null;
  weekly_change_pct: number | null;
  yearly_change_pct: number | null;
};

export type AssetsResponse = {
  items: Asset[];
};

export type PricePoint = {
  ts: string;
  price: number;
};

export type HistoryResponse = {
  symbol: string;
  days: number;
  points: PricePoint[];
};

export type MarketSearchRequest = {
  query: string;
  top_k?: number;
  sirket?: string | null;
  tip?: string | null;
};

export type SearchHit = {
  doc_id: string | null;
  baslik: string | null;
  sirket: string | null;
  symbol: string | null;
  tarih: string | null;
  tip: string | null;
  excerpt: string;
  score: number | null;
};

export type MarketSearchResponse = {
  query: string;
  items: SearchHit[];
};

export type PublicMarketTickerItem = {
  symbol: string;
  label: string;
  value: number;
  currency: string;
  change_percent: number | null;
  source: string;
};

export type PublicMarketTickerResponse = {
  items: PublicMarketTickerItem[];
};

export type ChartInterval = "5m" | "15m" | "1h" | "4h" | "1d";
export type ChartRange = "1d" | "5d" | "1m" | "3m" | "1y";

export type Candle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
};

export type CandlesResponse = {
  symbol: string;
  interval: ChartInterval;
  range: ChartRange;
  candles: Candle[];
};

export type PublicLandingAllocationItem = {
  asset_class: string;
  class_value_try: number;
  class_pct: number;
};

export type PublicLandingHoldingItem = {
  symbol: string;
  asset_name: string;
  asset_class: string;
  current_price: number;
  daily_change_pct: number | null;
  market_value_try: number;
  pnl_pct: number | null;
};

export type PublicLandingPreviewResponse = {
  total_value_try: number;
  total_pnl_pct: number | null;
  holding_count: number;
  allocation: PublicLandingAllocationItem[];
  holdings: PublicLandingHoldingItem[];
};
