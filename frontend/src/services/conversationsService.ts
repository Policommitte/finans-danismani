import type { ChatMessage, Conversation, StoredMessage } from "../models/chat";
import { apiRequest } from "./apiClient";

export function getConversations(limit = 50): Promise<Conversation[]> {
  return apiRequest<{ items: Conversation[] }>(`/api/conversations?limit=${limit}`).then(
    (response) => response.items,
  );
}

export function getConversationMessages(conversationId: number): Promise<StoredMessage[]> {
  return apiRequest<{ conversation_id: number; items: StoredMessage[] }>(
    `/api/conversations/${conversationId}/messages`,
  ).then((response) => response.items);
}

/**
 * Maps a persisted row back onto the widget's message shape. `meta.sources`,
 * `meta.agent_errors` and `meta.mentioned_assets` are written by the backend
 * on every assistant turn (see services/chat.py), so restored conversations
 * keep their source cards and asset chips.
 */
export function toChatMessage(row: StoredMessage): ChatMessage {
  const isAssistant = row.sender_role === "assistant";
  return {
    id: `stored-${row.id}`,
    role: isAssistant ? "assistant" : "user",
    content: row.message_content,
    message_id: row.id,
    sources: isAssistant ? row.meta?.sources ?? [] : undefined,
    agent_errors: isAssistant ? row.meta?.agent_errors ?? [] : undefined,
    mentioned_assets: isAssistant ? row.meta?.mentioned_assets ?? [] : undefined,
  };
}
