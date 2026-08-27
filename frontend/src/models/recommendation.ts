export type RecommendationStatus =
  | "PUBLISHED"
  | "VIEWED"
  | "APPROVED"
  | "CONVERTED"
  | "REJECTED"
  | "EXPIRED"
  | "HALTED";

/** FR-AUT-023: ret gerekcesi sabit kume — serbest metin alinmaz. */
export type RejectionReason =
  | "NOT_INTERESTED"
  | "TOO_RISKY"
  | "NO_CASH"
  | "BAD_TIMING"
  | "NOT_UNDERSTOOD";

export type RecommendationSource = {
  label: string;
  kind: string;
  url: string | null;
};

export type Recommendation = {
  id: number;
  asset_symbol: string;
  asset_name: string;
  asset_class: string;
  side: "BUY" | "SELL";
  quantity: number;
  reference_price: number;
  estimated_amount: number;
  confidence: number;
  rationale: string[];
  risk_note: string;
  sources: RecommendationSource[];
  personalization: Record<string, unknown>;
  status: RecommendationStatus;
  rejection_reason: RejectionReason | null;
  order_id: number | null;
  expires_at: string;
  created_at: string;
  viewed_at: string | null;
  decided_at: string | null;
  /** BR-AUT-01: SPK uyarisi sunucudan gelir, istemci kendi metnini uydurmaz. */
  disclaimer: string;
};

export type RecommendationListResponse = {
  items: Recommendation[];
  counts: Partial<Record<RecommendationStatus, number>>;
};

export type AutonomousSettings = {
  autonomous_enabled: boolean;
  per_order_limit_try: number;
  daily_limit_try: number;
  allowed_asset_classes: string[];
  max_daily_recommendations: number;
};
