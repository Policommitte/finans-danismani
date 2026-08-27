import type {
  AssetsResponse,
  CandlesResponse,
  ChartInterval,
  ChartRange,
  HistoryResponse,
  MarketSearchRequest,
  MarketSearchResponse,
  PublicLandingPreviewResponse,
  PublicMarketTickerResponse,
} from "../models/market";
import { apiRequest } from "./apiClient";

export function getMarketAssets(category?: string): Promise<AssetsResponse> {
  const query = category ? `?category=${encodeURIComponent(category)}` : "";
  return apiRequest<AssetsResponse>(`/api/market/assets${query}`);
}

export function getMarketHistory(symbol: string, days = 30): Promise<HistoryResponse> {
  const params = new URLSearchParams({ symbol, days: String(days) });
  return apiRequest<HistoryResponse>(`/api/market/history?${params.toString()}`);
}

export function searchMarket(payload: MarketSearchRequest): Promise<MarketSearchResponse> {
  return apiRequest<MarketSearchResponse>("/api/market/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getPublicMarketTicker(): Promise<PublicMarketTickerResponse> {
  return apiRequest<PublicMarketTickerResponse>("/api/public/market-ticker", { auth: false });
}

export function getMarketCandles(
  symbol: string,
  interval: ChartInterval,
  range: ChartRange,
): Promise<CandlesResponse> {
  const params = new URLSearchParams({ symbol, interval, range });
  return apiRequest<CandlesResponse>(`/api/market/candles?${params.toString()}`);
}

export function getPublicLandingPreview(): Promise<PublicLandingPreviewResponse> {
  return apiRequest<PublicLandingPreviewResponse>("/api/public/landing-preview", { auth: false });
}
