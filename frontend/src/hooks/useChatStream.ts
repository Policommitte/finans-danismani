"use client";

import { useState } from "react";
import type { AgentError, ChatMessage, Source } from "../models/chat";
import { streamChat } from "../services/chatService";

export function useChatStream() {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendMessage(content: string) {
    const trimmed = content.trim();
    if (!trimmed || isStreaming) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };
    const assistantId = crypto.randomUUID();
    let assistantText = "";
    let sources: Source[] = [];
    let agentErrors: AgentError[] = [];

    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setIsStreaming(true);
    setError(null);
    setStatus("Gonderiliyor");

    try {
      await streamChat({ message: trimmed, conversation_id: conversationId }, (event) => {
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
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content: assistantText,
                    sources,
                    agent_errors: agentErrors,
                    message_id: event.message_id,
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

  return { messages, status, isStreaming, error, sendMessage };
}
