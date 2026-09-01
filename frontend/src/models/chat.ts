export type Source = {
  doc_id: string;
  baslik: string;
  sirket: string | null;
  tarih: string | null;
  tip: string | null;
  score: number | null;
};

export type AgentError = {
  agent: string;
  error_type: "timeout" | "tool_error" | "llm_error" | "unknown";
  /**
   * Hatanin ham metni. YALNIZCA gelistirme ortaminda gelir - backend uretimde
   * bu alani hic gondermez (istisna metni tool adi, baglanti dizesi, dosya
   * yolu tasiyabilir; bkz. Orchestrator._hata_ayrintisi_gonderilsin).
   *
   * Gelistirirken kritik: "llm_error" tek basina 400 mu 404 mu kota mi
   * soylemiyor ve hatayi arayan kisi arayuze bakiyor, sunucu loglarina degil.
   */
  message?: string;
};

export type ChatAttachmentKind = "image" | "file";

/** Gonderilecek ek - `data_base64` sunucuya gonderilen govde. */
export type ChatAttachment = {
  kind: ChatAttachmentKind;
  filename: string;
  mime_type: string;
  data_base64: string;
};

/**
 * Kullanicinin kendi mesajinda YEREL gosterim icin - `previewUrl`
 * `URL.createObjectURL` ile uretilir, KALICI DEGILDIR (sayfa yenilenince
 * kaybolur, backend'e hicbir zaman gonderilmez, bkz. useChatStream.ts).
 */
export type ChatMessageAttachment = {
  kind: ChatAttachmentKind;
  filename: string;
  previewUrl?: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  agent_errors?: AgentError[];
  message_id?: number;
  attachment?: ChatMessageAttachment;
  /** Cevapta bahsedilen (katalogla dogrulanmis) varlik sembolleri - orn. ["TUPRS"]. */
  mentioned_assets?: string[];
};

export type ChatRequest = {
  message: string;
  conversation_id?: number | null;
  attachment?: ChatAttachment;
};

export type IdleCashSuggestionItem = {
  asset_id: number;
  symbol: string;
  name: string;
  asset_class: string;
  currency: string;
  sector: string;
  region: string;
  quantity: number;
  reference_price: number;
  estimated_amount: number;
  weight_pct: number;
  goal_rank: number;
  candidate_count: number;
  suitability_level: "HIGH" | "MEDIUM" | "LOW";
  score_components: Record<string, number>;
  rationale: string[];
};

export type IdleCashSuggestion = {
  mode: "basket" | "single";
  balance_source: "cash_account";
  available_balance: number;
  investable_amount: number;
  estimated_total: number;
  unallocated_balance: number;
  risk_profile: "LOW" | "MEDIUM" | "HIGH";
  goal: "LONG_TERM" | "GROWTH" | "MOMENTUM" | "LOW_VOLATILITY";
  preference_summary: string;
  items: IdleCashSuggestionItem[];
  disclaimer: string;
  generated_at: string;
};

export type IdleCashBasketOption = {
  id: string;
  title: string;
  summary: string;
  strategy_key: "CORE" | "DEFENSIVE" | "OPPORTUNITY";
  strategy_label: string;
  strategy_description: string;
  metrics: {
    expected_volatility_20d_pct: number;
    average_correlation: number | null;
    diversification_score: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH";
    asset_class_count: number;
    sector_count: number;
    region_count: number;
    largest_weight_pct: number;
  };
  backtest: {
    status: "SUFFICIENT" | "LIMITED" | "INSUFFICIENT";
    methodology_version: string;
    observation_count: number;
    start_date: string | null;
    end_date: string | null;
    gross_return_pct: number | null;
    net_return_pct: number | null;
    benchmark_return_pct: number | null;
    excess_return_pct: number | null;
    annualized_volatility_pct: number | null;
    max_drawdown_pct: number | null;
    risk_adjusted_return: number | null;
    transaction_cost_impact_pct: number | null;
    rebalance_count: number;
    benchmark_label: string;
    note: string;
  };
  suggestion: IdleCashSuggestion;
};

export type IdleCashBasketCatalog = {
  goal: IdleCashSuggestion["goal"];
  universe_size: number;
  eligible_asset_count: number;
  stale_asset_count: number;
  insufficient_history_asset_count: number;
  evaluation_frequency: string;
  evaluated_at: string;
  last_changed_at: string;
  next_evaluation_at: string;
  membership_changed: boolean;
  stability_note: string;
  options: IdleCashBasketOption[];
};

export type ChatEvent =
  | { type: "meta"; request_id: string; conversation_id: number }
  | { type: "status"; stage: string; message: string }
  | { type: "sources"; items: Source[] }
  | { type: "token"; content: string }
  | { type: "agent_error"; agent: string; error_type: AgentError["error_type"]; message?: string }
  | { type: "error"; code: string; message: string }
  | { type: "done"; message_id?: number; latency_ms: number; mentioned_assets?: string[] };
