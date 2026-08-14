"use client";

import { getDashboardSummary } from "../services/dashboardService";
import { useAsyncData } from "./useAsyncData";

export function useDashboard() {
  return useAsyncData(getDashboardSummary, []);
}
