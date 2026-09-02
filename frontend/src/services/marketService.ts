import type {
  AssetsResponse,
  CandlesResponse,
  ChartInterval,
  ChartRange,
  Forecast,
  HistoryResponse,
  MarketSearchRequest,
  MarketSearchResponse,
  NewsListResponse,
  OhlcResponse,
  PhotoResponse,
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

// Ticker yaniti kisa sureligine paylasilir: ust serit (MarketTicker) ve
// dashboard'daki doviz cevirimi AYNI ucu, AYNI 60 sn aralikla ayri ayri
// cekiyordu - her dashboard ziyareti backend'e iki ozdes istek atiyordu.
// Ayni anda gelen cagrilar tek istege katlanir (in-flight dedupe), sonuc
// TTL boyunca tekrar kullanilir. TTL, iki tuketicinin de kendi 60 sn
// tazeleme periyodundan kisa tutuldu ki hicbiri bayat veriyle kalmasin.
const TICKER_SHARE_TTL_MS = 30_000;
let tickerCache: { at: number; value: PublicMarketTickerResponse } | null = null;
let tickerInFlight: Promise<PublicMarketTickerResponse> | null = null;

export function getPublicMarketTicker(): Promise<PublicMarketTickerResponse> {
  const now = Date.now();
  if (tickerCache !== null && now - tickerCache.at < TICKER_SHARE_TTL_MS) {
    return Promise.resolve(tickerCache.value);
  }
  if (tickerInFlight !== null) {
    return tickerInFlight;
  }
  tickerInFlight = apiRequest<PublicMarketTickerResponse>("/api/public/market-ticker", {
    auth: false,
  })
    .then((value) => {
      tickerCache = { at: Date.now(), value };
      return value;
    })
    .finally(() => {
      tickerInFlight = null;
    });
  return tickerInFlight;
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

export function getMarketPhoto(query: string): Promise<PhotoResponse> {
  return apiRequest<PhotoResponse>(`/api/market/photo?query=${encodeURIComponent(query)}`);
}

/**
 * Bir varligin ~1 aylik tahmini. `null` donebilir - HATA DEGILDIR:
 * tahmin ozelligi opsiyoneldir (backend'de `FORECAST_MODEL` bos ya da
 * torch/timesfm kurulu degil). Cagiran taraf `null` gorunce kesikli
 * cizgiyi cizmez, grafigin geri kalani normal calisir.
 */
export function getForecast(symbol: string): Promise<Forecast | null> {
  return apiRequest<Forecast | null>(`/api/market/forecast/${encodeURIComponent(symbol)}`);
}

/** Portfoyun TUM varliklari + nakdi uzerinden TL bazli birlesik tahmin. */
export function getPortfolioForecast(): Promise<Forecast | null> {
  return apiRequest<Forecast | null>("/api/market/forecast-portfolio");
}
