import type { Asset } from "./market";
import type { AllocationSlice, Holding, PortfolioSummary } from "./portfolio";
import type { RiskProfileResponse } from "./risk";
import type { PaperOrder, TradingAccount } from "./trading";

export type DashboardSummaryResponse = {
  summary: PortfolioSummary | null;
  holdings: Holding[];
  allocation: AllocationSlice[];
  cash_account: TradingAccount | null;
  risk: RiskProfileResponse;
  movers: Asset[];
  filled_orders: PaperOrder[];
};
