import type { ChatQuickReply } from "../../models/chat";

/**
 * Compact, always-available prompt chips sitting right above the composer.
 * Unlike the old welcome bubble they do not scroll away with the history,
 * so the guided "I want to invest" entry point stays one tap away.
 */
export function SuggestionStrip({
  suggestions,
  disabled,
  onSelect,
}: {
  suggestions: ChatQuickReply[];
  disabled?: boolean;
  onSelect: (reply: ChatQuickReply) => void;
}) {
  if (suggestions.length === 0) return null;
  return (
    <div className="flex gap-1.5 overflow-x-auto px-3 pt-2.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {suggestions.map((reply) => (
        <button
          key={reply.id}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(reply)}
          title={reply.hint}
          className="shrink-0 rounded-full border border-[var(--color-primary)]/40 bg-[var(--color-surface)] px-3 py-1 text-xs font-medium text-[var(--color-primary)] transition hover:bg-[var(--color-primary-soft)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {reply.label}
        </button>
      ))}
    </div>
  );
}
