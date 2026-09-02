import type { ReactNode } from "react";
import { useState } from "react";
import type { ChatMessage } from "../../models/chat";
import { downloadChatReport } from "../../services/chatService";
import { AgentErrorNotice } from "./AgentErrorNotice";
import { SourceList } from "./SourceList";

function ReportDownloadButton({ messageId, dosyaAdi }: { messageId: number; dosyaAdi: string }) {
  const [indiriliyor, setIndiriliyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  async function handleClick() {
    setIndiriliyor(true);
    setHata(null);
    try {
      await downloadChatReport(messageId, dosyaAdi);
    } catch (exc) {
      setHata(exc instanceof Error ? exc.message : "Rapor indirilemedi.");
    } finally {
      setIndiriliyor(false);
    }
  }

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={indiriliyor}
        className="flex items-center gap-1.5 rounded-md border app-border bg-[var(--color-surface)] px-2.5 py-1.5 text-xs font-medium text-[var(--color-text)] transition hover:bg-[var(--color-primary-soft)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        <svg
          aria-hidden="true"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        {indiriliyor ? "İndiriliyor…" : `Raporu indir (${dosyaAdi})`}
      </button>
      {hata && <div className="app-danger-box mt-1 rounded-md px-2 py-1 text-xs">{hata}</div>}
    </div>
  );
}

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
          {message.role === "assistant" && message.rapor && message.message_id && (
            <ReportDownloadButton
              messageId={message.message_id}
              dosyaAdi={message.rapor.dosya_adi}
            />
          )}
        </div>
      ))}
    </div>
  );
}
