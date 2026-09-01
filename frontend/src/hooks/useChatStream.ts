"use client";

import { useState } from "react";
import type { PendingAttachment } from "../components/chat/AttachmentMenu";
import type {
  AgentError,
  ChatAttachment,
  ChatMessage,
  Source,
} from "../models/chat";
import { streamChat } from "../services/chatService";

//: Ek varsa ama mesaj kutusu bosbiraktilarsa, dosya turune gore makul bir
//: varsayilan soru - backend `ChatRequest.message` bos gecemez (min_length=1).
const DEFAULT_ATTACHMENT_PROMPTS: Record<PendingAttachment["kind"], string> = {
  image: "Bu görseli analiz et.",
  file: "Bu dosyayı analiz et.",
};

export function useChatStream() {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendMessage(content: string, pendingAttachment?: PendingAttachment) {
    const trimmed = content.trim();
    if ((!trimmed && !pendingAttachment) || isStreaming) {
      return;
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
      content: effectiveMessage,
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
    setIsStreaming(true);
    setError(null);
    setStatus("Gonderiliyor");

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
                    mentioned_assets: mentionedAssets,
                  }
                : message,
            ),
          );
          setStatus(null);
        }
      });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Sohbet akisi kesildi.");
    } finally {
      setIsStreaming(false);
    }
  }

  return {
    messages,
    status,
    isStreaming,
    error,
    sendMessage,
  };
}
