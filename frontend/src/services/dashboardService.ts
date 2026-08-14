import type { DashboardSummaryResponse } from "../models/dashboard";
import { apiRequest } from "./apiClient";

export function getDashboardSummary(): Promise<DashboardSummaryResponse> {
  return apiRequest<DashboardSummaryResponse>("/api/dashboard/summary");
}
