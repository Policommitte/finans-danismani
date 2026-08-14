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
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  agent_errors?: AgentError[];
  message_id?: number;
};

export type ChatRequest = {
  message: string;
  conversation_id?: number | null;
};

export type ChatEvent =
  | { type: "meta"; request_id: string; conversation_id: number }
  | { type: "status"; stage: string; message: string }
  | { type: "sources"; items: Source[] }
  | { type: "token"; content: string }
  | { type: "agent_error"; agent: string; error_type: AgentError["error_type"] }
  | { type: "error"; code: string; message: string }
  | { type: "done"; message_id?: number; latency_ms: number };
