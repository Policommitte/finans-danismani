import type { RiskProfileResponse } from "../models/risk";
import { apiRequest } from "./apiClient";

export function getRiskProfile(): Promise<RiskProfileResponse> {
  return apiRequest<RiskProfileResponse>("/api/risk/profile");
}
