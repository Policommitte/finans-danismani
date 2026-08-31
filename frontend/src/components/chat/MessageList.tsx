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
          {message.attachment && (
            <div className="mb-1.5 flex items-center gap-1.5 text-xs opacity-90">
              {message.attachment.previewUrl ? (
                <img
                  src={message.attachment.previewUrl}
                  alt=""
                  className="h-8 w-8 rounded object-cover"
                />
              ) : (
                <svg
                  aria-hidden="true"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              )}
              <span className="truncate">{message.attachment.filename}</span>
            </div>
          )}
          <div className="whitespace-pre-wrap">{message.content || "..."}</div>
          {message.role === "assistant" && <SourceList sources={message.sources ?? []} />}
          {message.role === "assistant" && <AgentErrorNotice errors={message.agent_errors ?? []} />}
        </div>
      ))}
    </div>
  );
}
