import type { ChatQuickReply } from "../../models/chat";
import { QuickReplies } from "./QuickReplies";

/**
 * The welcome bubble shown at the top of an empty conversation with a few
 * ready-made prompts. The first one starts the guided investment flow; the
 * others are ordinary questions sent to the assistant.
 */
export function SuggestionBubble({
  title,
  suggestions,
  disabled,
  onSelect,
}: {
  title: string;
  suggestions: ChatQuickReply[];
  disabled?: boolean;
  onSelect: (reply: ChatQuickReply) => void;
}) {
  return (
    <div className="mr-auto max-w-[92%] rounded-lg app-card-muted px-3 py-2.5 text-sm app-heading chat-pop-in">
      <div className="font-medium">{title}</div>
      <QuickReplies replies={suggestions} disabled={disabled} onSelect={onSelect} />
    </div>
  );
}
