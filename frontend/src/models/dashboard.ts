import type { Asset } from "./market";
import type { AllocationSlice, Holding, PortfolioSummary } from "./portfolio";
import type { RiskProfileResponse } from "./risk";

export type DashboardSummaryResponse = {
  summary: PortfolioSummary | null;
  holdings: Holding[];
  allocation: AllocationSlice[];
  risk: RiskProfileResponse;
  movers: Asset[];
};
