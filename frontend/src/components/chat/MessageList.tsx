import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import type { ChatMessage, ChatQuickReply } from "../../models/chat";
import { downloadChatReport } from "../../services/chatService";
import { AgentErrorNotice } from "./AgentErrorNotice";
import { InvestmentPackageCard } from "./InvestmentPackageCard";
import { MentionedAssetCard } from "./MentionedAssetCard";
import { QuickReplies } from "./QuickReplies";
import { SourceList } from "./SourceList";

function ReportDownloadButton({ messageId, fileName }: { messageId: number; fileName: string }) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setDownloading(true);
    setError(null);
    try {
      await downloadChatReport(messageId, fileName);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Rapor indirilemedi.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={downloading}
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
        {downloading ? "İndiriliyor…" : `Raporu indir (${fileName})`}
      </button>
      {error && <div className="app-danger-box mt-1 rounded-md px-2 py-1 text-xs">{error}</div>}
    </div>
  );
}

/** Bot yanit hazirlarken gosterilen zipirti (typing) baloncugu - eskiden
 * ayri bir baslik satiri (`chat.status`) ile bu baloncuk AYRI yerlerde
 * gorunuyordu; artik durum metni bu baloncugun icinde, uc noktanin
 * yaninda gosteriliyor - tek bir "dusunuyor" gostergesi kaliyor. */
function TypingBubble({ statusText }: { statusText?: string | null }) {
  return (
    <div className="mr-auto flex max-w-[86%] items-center gap-2 rounded-lg app-card-muted px-3 py-2 text-sm app-heading">
      <span className="flex items-center gap-1" aria-hidden="true">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current opacity-60" />
      </span>
      <span className="text-xs app-muted">{statusText || "Düşünüyor…"}</span>
    </div>
  );
}

export function MessageList({
  messages,
  emptyState = "Portföyün, piyasa verileri veya risk durumun hakkında soru sorabilirsin.",
  onSelectAsset,
  leading,
  quickRepliesDisabled,
  onQuickReply,
  onPackagePurchased,
  statusText,
}: {
  messages: ChatMessage[];
  emptyState?: ReactNode;
  onSelectAsset?: (symbol: string) => void;
  /** Rendered above the messages (e.g. the suggestion bubble). */
  leading?: ReactNode;
  quickRepliesDisabled?: boolean;
  onQuickReply?: (reply: ChatQuickReply) => void;
  onPackagePurchased?: (orderCount: number) => void;
  /** Bot'un su an ne yaptigini anlatan kisa canli durum metni (bkz.
   * useChatStream.status) - AYRI bir baslik satirinda DEGIL, en son
   * bos icerikli asistan mesaji yerine gecen `TypingBubble` icinde
   * gosterilir. */
  statusText?: string | null;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const lastMessage = messages[messages.length - 1];
  const lastMessageKey = lastMessage
    ? `${lastMessage.id}:${lastMessage.content.length}:${lastMessage.quickReplies?.length ?? 0}:${lastMessage.investmentPackage ? 1 : 0}`
    : "";

  // Keep the newest message in view as answers stream in or the guided flow
  // appends its questions.
  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [lastMessageKey]);

  return (
    <div ref={containerRef} className="flex-1 space-y-3 overflow-y-auto p-4">
      {leading}
      {messages.length === 0 && emptyState && (
        <div className="rounded-lg app-card-muted p-4 text-sm app-muted">
          {emptyState}
        </div>
      )}
      {messages.map((message) => {
        if (message.role === "assistant" && !message.content) {
          return <TypingBubble key={message.id} statusText={statusText} />;
        }

        return (
        <div
          key={message.id}
          className={`${message.investmentPackage ? "max-w-[97%]" : "max-w-[86%]"} rounded-lg px-3 py-2 text-sm ${
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
          {message.role === "assistant" && message.investmentPackage && (
            <InvestmentPackageCard
              investmentPackage={message.investmentPackage}
              onPurchased={onPackagePurchased}
            />
          )}
          {message.role === "assistant" && message.quickReplies && onQuickReply && (
            <QuickReplies
              replies={message.quickReplies}
              disabled={quickRepliesDisabled}
              onSelect={onQuickReply}
            />
          )}
          {message.role === "assistant" && <SourceList sources={message.sources ?? []} />}
          {message.role === "assistant" && <AgentErrorNotice errors={message.agent_errors ?? []} />}
          {message.role === "assistant" && message.rapor && message.message_id && (
            <ReportDownloadButton
              messageId={message.message_id}
              fileName={message.rapor.dosya_adi}
            />
          )}
          {message.role === "assistant" && onSelectAsset && (
            <MentionedAssetCard symbols={message.mentioned_assets ?? []} onOpenAsset={onSelectAsset} />
          )}
        </div>
        );
      })}
    </div>
  );
}
