export type RiskComponents = {
  concentration: number;
  asset_type: number;
  volatility: number;
  single_position: number;
};

export type RiskProfileResponse = {
  risk_score: number;
  risk_level: string;
  risk_tolerance: string | null;
  tolerance_alignment: string;
  holding_count: number;
  top_class: string | null;
  top_class_pct: number | null;
  avg_volatility_pct: number | null;
  components: RiskComponents;
  reasons: string[];
  suggestions: string[];
};
