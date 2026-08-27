import type {
  AssetsResponse,
  HistoryResponse,
  MarketSearchRequest,
  MarketSearchResponse,
  NewsListResponse,
  OhlcResponse,
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

export function getMarketOhlc(symbol: string, days = 30): Promise<OhlcResponse> {
  const params = new URLSearchParams({ symbol, days: String(days) });
  return apiRequest<OhlcResponse>(`/api/market/ohlc?${params.toString()}`);
}

export function searchMarket(payload: MarketSearchRequest): Promise<MarketSearchResponse> {
  return apiRequest<MarketSearchResponse>("/api/market/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getNews(limit = 20, kategori?: string): Promise<NewsListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (kategori) {
    params.set("kategori", kategori);
  }
  return apiRequest<NewsListResponse>(`/api/market/news?${params.toString()}`);
}

export function getPublicMarketTicker(): Promise<PublicMarketTickerResponse> {
  return apiRequest<PublicMarketTickerResponse>("/api/public/market-ticker", { auth: false });
}

export function getPublicLandingPreview(): Promise<PublicLandingPreviewResponse> {
  return apiRequest<PublicLandingPreviewResponse>("/api/public/landing-preview", { auth: false });
}
