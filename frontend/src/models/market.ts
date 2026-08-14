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
