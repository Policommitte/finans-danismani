import type { EconomicCalendarResponse } from "../models/economicCalendar";
import { apiRequest } from "./apiClient";

export function getEconomicCalendar(): Promise<EconomicCalendarResponse> {
  return apiRequest<EconomicCalendarResponse>("/api/economic-calendar");
}
