import type {
  AllocationResponse,
  HoldingsResponse,
  PortfolioPerformanceResponse,
  PortfolioSummary,
  TransactionsResponse,
} from "../models/portfolio";
import { apiRequest } from "./apiClient";

export function getPortfolioSummary(): Promise<PortfolioSummary> {
  return apiRequest<PortfolioSummary>("/api/portfolio/summary");
}

export function getPortfolioHoldings(): Promise<HoldingsResponse> {
  return apiRequest<HoldingsResponse>("/api/portfolio/holdings");
}

export function getPortfolioAllocation(): Promise<AllocationResponse> {
  return apiRequest<AllocationResponse>("/api/portfolio/allocation");
}

export function getPortfolioTransactions(limit = 20): Promise<TransactionsResponse> {
  return apiRequest<TransactionsResponse>(`/api/portfolio/transactions?limit=${limit}`);
}

export function getPortfolioPerformance(hours = 24): Promise<PortfolioPerformanceResponse> {
  return apiRequest<PortfolioPerformanceResponse>(`/api/portfolio/performance?hours=${hours}`);
}
