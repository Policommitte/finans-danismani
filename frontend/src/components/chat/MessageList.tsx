import type { ReactNode } from "react";
import type { ChatMessage } from "../../models/chat";
import { AgentErrorNotice } from "./AgentErrorNotice";
import { SourceList } from "./SourceList";

export function MessageList({
  messages,
  emptyState = "Portföyün, piyasa verileri veya risk durumun hakkında soru sorabilirsin.",
}: {
  messages: ChatMessage[];
  emptyState?: ReactNode;
}) {
  return (
    <div className="flex-1 space-y-3 overflow-y-auto p-4">
      {messages.length === 0 && (
        <div className="rounded-lg app-card-muted p-4 text-sm app-muted">
          {emptyState}
        </div>
      )}
      {messages.map((message) => (
        <div
          key={message.id}
          className={`max-w-[86%] rounded-lg px-3 py-2 text-sm ${
            message.role === "user"
              ? "ml-auto app-primary"
              : "mr-auto app-card-muted app-heading"
          }`}
        >
          <div className="whitespace-pre-wrap">{message.content || "..."}</div>
          {message.role === "assistant" && <SourceList sources={message.sources ?? []} />}
          {message.role === "assistant" && <AgentErrorNotice errors={message.agent_errors ?? []} />}
        </div>
      ))}
    </div>
  );
}
