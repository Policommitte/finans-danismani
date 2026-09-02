import type { DashboardSummaryResponse } from "../models/dashboard";
import { apiRequest } from "./apiClient";
import { getPaperOrders } from "./tradingService";

export async function getDashboardSummary(): Promise<DashboardSummaryResponse> {
  const [summary, orders] = await Promise.all([
    apiRequest<Omit<DashboardSummaryResponse, "orders">>("/api/dashboard/summary"),
    getPaperOrders(100),
  ]);
  return {
    ...summary,
    orders: orders.items.filter((order) => order.status === "FILLED" || order.status === "PENDING"),
  };
}
