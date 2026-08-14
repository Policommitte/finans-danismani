import type { ChatMessage } from "../../models/chat";
import { AgentErrorNotice } from "./AgentErrorNotice";
import { SourceList } from "./SourceList";

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  return (
    <div className="flex-1 space-y-3 overflow-y-auto p-4">
      {messages.length === 0 && (
        <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">
          Portfoyun, piyasa verileri veya risk durumun hakkinda soru sorabilirsin.
        </div>
      )}
      {messages.map((message) => (
        <div
          key={message.id}
          className={`max-w-[86%] rounded-lg px-3 py-2 text-sm ${
            message.role === "user"
              ? "ml-auto bg-blue-700 text-white"
              : "mr-auto bg-slate-100 text-slate-900"
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
