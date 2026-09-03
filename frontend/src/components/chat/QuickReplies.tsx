import type { ChatQuickReply } from "../../models/chat";

/** Tappable answer chips rendered under an assistant message. */
export function QuickReplies({
  replies,
  disabled,
  onSelect,
}: {
  replies: ChatQuickReply[];
  disabled?: boolean;
  onSelect: (reply: ChatQuickReply) => void;
}) {
  if (replies.length === 0) return null;
  return (
    <div className="mt-2.5 flex flex-wrap gap-1.5">
      {replies.map((reply) => (
        <button
          key={reply.id}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(reply)}
          className="group flex flex-col items-start rounded-lg border border-[var(--color-primary)]/40 bg-[var(--color-surface)] px-3 py-1.5 text-left text-xs font-medium text-[var(--color-primary)] transition hover:bg-[var(--color-primary-soft)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span>{reply.label}</span>
          {reply.hint && (
            <span className="text-[11px] font-normal app-muted">{reply.hint}</span>
          )}
        </button>
      ))}
    </div>
  );
}
