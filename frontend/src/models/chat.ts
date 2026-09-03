export type Source = {
  doc_id: string;
  baslik: string;
  sirket: string | null;
  tarih: string | null;
  tip: string | null;
  score: number | null;
  /**
   * Haberin yayindaki adresi (`rag.documents.kaynak_url`).
   *
   * Sohbete haberin tam metni BASILMAZ - uzun metin pencereyi bogar; kaynak
   * kartinda baslik/kaynak/tarih durur ve devamini okumak isteyen bu adrese
   * gider.
   *
   * `undefined` DE olabilir, `null` da: bu ozellikten ONCE kaydedilmis
   * mesajlar gecmisten `meta.sources` icinde bu alan HIC olmadan doner.
   */
  kaynak_url?: string | null;
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
  /**
   * Belge analiz ajaninin urettigi PDF rapor - varsa indirme baglantisi
   * gosterilir. SSE `done` olayindaki `rapor` alanindan gelir (bkz.
   * `Orchestrator.stream_request` - `app/engine/orchestrator.py`).
   */
  rapor?: ChatRaporMeta;
  /** Cevapta bahsedilen (katalogla dogrulanmis) varlik sembolleri - orn. ["TUPRS"]. */
  mentioned_assets?: string[];
  /**
   * Guided "I want to invest" flow (see useInvestmentPackageFlow.ts). These
   * messages are produced locally and never sent to the backend.
   */
  local?: boolean;
  /** Tappable answers shown under an assistant message; cleared once answered. */
  quickReplies?: ChatQuickReply[];
  /** Ready-made package rendered as a card with a one-tap purchase button. */
  investmentPackage?: InvestmentPackage;
};

export type ChatQuickReply = {
  id: string;
  label: string;
  /** Optional secondary line under the label. */
  hint?: string;
  /** Text echoed into the conversation as the user's message when tapped. */
  message: string;
};

export type InvestmentHorizon = "SHORT" | "MEDIUM" | "LONG";
export type InvestmentRiskProfile = "LOW" | "MEDIUM" | "HIGH";
export type InvestmentGoal = IdleCashSuggestion["goal"];

export type InvestmentPackageRequest = {
  amount: number;
  horizon: InvestmentHorizon;
  risk_profile: InvestmentRiskProfile;
  goal: InvestmentGoal;
};

/** Response of `POST /api/oneriler/paket` (backend/app/schemas/investment_package.py). */
export type InvestmentPackage = {
  title: string;
  summary: string;
  horizon: InvestmentHorizon;
  horizon_label: string;
  risk_profile: InvestmentRiskProfile;
  goal: InvestmentGoal;
  goal_label: string;
  requested_amount: number;
  available_balance: number;
  exceeds_balance: boolean;
  strategy_key: IdleCashBasketOption["strategy_key"];
  strategy_label: string;
  metrics: IdleCashBasketOption["metrics"];
  suggestion: IdleCashSuggestion;
  disclaimer: string;
};

/** PDF rapor teslimati meta verisi - baytlar SSE'den GECMEZ, yalnizca
 * dosya adi/boyutu. Gercek dosya ayri bir indirme ucundan alinir. */
export type ChatRaporMeta = {
  dosya_adi: string;
  boyut: number;
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
  | {
      type: "done";
      message_id?: number;
      latency_ms: number;
      rapor?: ChatRaporMeta;
      mentioned_assets?: string[];
    };

/** `GET /api/conversations` row (backend/app/schemas/chat.py `Conversation`). */
export type Conversation = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number | null;
};

/** `GET /api/conversations/{id}/messages` row - persisted message with its JSONB meta. */
export type StoredMessage = {
  id: number;
  sender_role: "user" | "assistant" | string;
  message_content: string;
  meta: {
    sources?: Source[];
    agent_errors?: AgentError[];
    mentioned_assets?: string[];
    [key: string]: unknown;
  };
  created_at: string;
};
