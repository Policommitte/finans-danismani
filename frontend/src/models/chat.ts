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
};

export type ChatRequest = {
  message: string;
  conversation_id?: number | null;
  attachment?: ChatAttachment;
};

export type ChatEvent =
  | { type: "meta"; request_id: string; conversation_id: number }
  | { type: "status"; stage: string; message: string }
  | { type: "sources"; items: Source[] }
  | { type: "token"; content: string }
  | { type: "agent_error"; agent: string; error_type: AgentError["error_type"]; message?: string }
  | { type: "error"; code: string; message: string }
  | { type: "done"; message_id?: number; latency_ms: number };
