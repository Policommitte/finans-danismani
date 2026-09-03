"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PendingAttachment } from "../components/chat/AttachmentMenu";
import type { AgentError, ChatAttachment, ChatMessage, Source } from "../models/chat";
import { streamChat } from "../services/chatService";
import { getConversationMessages, toChatMessage } from "../services/conversationsService";

//: Ek varsa ama mesaj kutusu bosbiraktilarsa, dosya turune gore makul bir
//: varsayilan soru - backend `ChatRequest.message` bos gecemez (min_length=1).
const DEFAULT_ATTACHMENT_PROMPTS: Record<PendingAttachment["kind"], string> = {
  image: "Bu görseli analiz et.",
  file: "Bu dosyayı analiz et.",
};

export type SendMessageOptions = {
  /**
   * Kullanici balonunda GORUNECEK metin; verilmezse gonderilen mesajin
   * kendisi gosterilir.
   *
   * Gomulu istemler icin var (bkz. `useDailyBrief` - gunluk ozet daveti):
   * modele giden yonerge uzundur ve kullaniciya oldugu gibi gosterilmesi
   * anlamsizdir, ama istemin KENDISI degismeden gider - backend'e ayri bir
   * "gizli mesaj" yolu acilmaz, sohbet gecmisine de tam metin yazilir.
   */
  displayText?: string;
};

export function useChatStream() {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  //: Aktif akisin iptal kolu. `stopStreaming()` ve provider unmount'u
  //: bunu tetikler; boylece kapatilan panel/sayfa arkasinda fetch surmez.
  const abortRef = useRef<AbortController | null>(null);
  const isStreamingRef = useRef(false);

  useEffect(() => () => abortRef.current?.abort(), []);

  /**
   * Sends one turn. Returns the id of the assistant message that will be
   * filled by the stream (or null when nothing was sent) so a caller such as
   * the asset modal can follow exactly its own answer in the shared history.
   */
  function sendMessage(
    content: string,
    pendingAttachment?: PendingAttachment,
    options?: SendMessageOptions,
  ): string | null {
    const trimmed = content.trim();
    if ((!trimmed && !pendingAttachment) || isStreamingRef.current) {
      return null;
    }

    const effectiveMessage = trimmed || (pendingAttachment ? DEFAULT_ATTACHMENT_PROMPTS[pendingAttachment.kind] : "");
    const attachment: ChatAttachment | undefined = pendingAttachment
      ? {
          kind: pendingAttachment.kind,
          filename: pendingAttachment.filename,
          mime_type: pendingAttachment.mimeType,
          data_base64: pendingAttachment.dataUrl.split(",")[1] ?? "",
        }
      : undefined;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: options?.displayText ?? effectiveMessage,
      attachment: pendingAttachment
        ? {
            kind: pendingAttachment.kind,
            filename: pendingAttachment.filename,
            previewUrl: pendingAttachment.kind === "image" ? pendingAttachment.dataUrl : undefined,
          }
        : undefined,
    };
    const assistantId = crypto.randomUUID();
    let assistantText = "";
    let sources: Source[] = [];
    let agentErrors: AgentError[] = [];
    let mentionedAssets: string[] = [];

    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, role: "assistant", content: "" },
    ]);
    isStreamingRef.current = true;
    setIsStreaming(true);
    setError(null);
    setStatus("Gonderiliyor");
    const controller = new AbortController();
    abortRef.current = controller;

    void (async () => {
    try {
      await streamChat({ message: effectiveMessage, conversation_id: conversationId, attachment }, (event) => {
        if (event.type === "meta") {
          setConversationId(event.conversation_id);
          setStatus("Baglandi");
        }

        if (event.type === "status") {
          setStatus(event.message);
        }

        if (event.type === "sources") {
          sources = event.items;
        }

        if (event.type === "agent_error") {
          agentErrors = [
            ...agentErrors,
            { agent: event.agent, error_type: event.error_type, message: event.message },
          ];
        }

        if (event.type === "token") {
          assistantText += event.content;
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, content: assistantText, sources, agent_errors: agentErrors }
                : message,
            ),
          );
        }

        if (event.type === "error") {
          setError(event.message);
        }

        if (event.type === "done") {
          mentionedAssets = event.mentioned_assets ?? [];
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content: assistantText,
                    sources,
                    agent_errors: agentErrors,
                    message_id: event.message_id,
                    // Belge analiz ajani PDF urettiyse (bkz.
                    // DocumentAnalysisAgent) indirme baglantisi icin gerekli
                    // meta veri - gercek dosya SSE'den GECMEZ, ayri bir
                    // uctan (`/api/chat/reports/{message_id}`) cekilir.
                    rapor: event.rapor,
                    mentioned_assets: mentionedAssets,
                  }
                : message,
            ),
          );
          setStatus(null);
              }
      }, controller.signal);
    } catch (exc) {
      if (controller.signal.aborted) {
        // Kullanici durdurdu: o ana kadar gelen metin kalir, hata gosterilmez;
        // hic metin gelmediyse bos asistan balonu kaldirilir.
        setMessages((current) =>
          current.filter((message) => !(message.id === assistantId && !message.content)),
        );
        setStatus(null);
          } else {
        setError(exc instanceof Error ? exc.message : "Sohbet akisi kesildi.");
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      isStreamingRef.current = false;
      setIsStreaming(false);
    }
    })();

    return assistantId;
  }

  /** Aborts the in-flight answer; already-streamed text is kept. */
  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  /** Starts a fresh thread: the next message opens a new conversation. */
  const startNewConversation = useCallback(() => {
    abortRef.current?.abort();
    setConversationId(null);
    setMessages([]);
    setError(null);
    setStatus(null);
  }, []);

  /** Restores a persisted conversation (FR-CHAT-03) into the widget. */
  const loadConversation = useCallback(async (id: number) => {
    abortRef.current?.abort();
    setIsLoadingHistory(true);
    setError(null);
    try {
      const rows = await getConversationMessages(id);
      setConversationId(id);
      setMessages(rows.map(toChatMessage));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Sohbet geçmişi yüklenemedi.");
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  /**
   * Adds a message that lives only in the widget (guided flows, local
   * confirmations). Returns the generated id so the caller can patch it later.
   */
  function appendLocalMessage(message: Omit<ChatMessage, "id" | "local">): string {
    const id = crypto.randomUUID();
    setMessages((current) => [...current, { ...message, id, local: true }]);
    return id;
  }

  function updateMessage(id: string, patch: Partial<ChatMessage>) {
    setMessages((current) =>
      current.map((message) => (message.id === id ? { ...message, ...patch } : message)),
    );
  }

  return {
    conversationId,
    messages,
    status,
    isStreaming,
    isLoadingHistory,
    error,
    sendMessage,
    stopStreaming,
    startNewConversation,
    loadConversation,
    appendLocalMessage,
    updateMessage,
  };
}
