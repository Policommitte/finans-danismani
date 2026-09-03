"use client";

import { FormEvent, KeyboardEvent, ReactNode, useEffect, useRef, useState } from "react";
import Button from "../ui/Button";
import { AttachmentMenu, type PendingAttachment } from "./AttachmentMenu";
import { AttachmentPreview } from "./AttachmentPreview";

/** Backend `ChatRequest.message` sinirini (max_length=4000) arayuzde de uygular. */
export const MAX_MESSAGE_LENGTH = 4000;
const COUNTER_VISIBLE_FROM = MAX_MESSAGE_LENGTH - 500;
const MAX_TEXTAREA_HEIGHT = 160;

export function MessageInput({
  disabled,
  placeholder = "Mesajınızı yazın",
  buttonLabel = "Gönder",
  stopLabel = "Durdur",
  isStreaming = false,
  onStop,
  onSend,
  leading,
}: {
  disabled: boolean;
  placeholder?: string;
  buttonLabel?: string;
  stopLabel?: string;
  /** Akis surerken Gonder yerine Durdur gosterilir. */
  isStreaming?: boolean;
  onStop?: () => void;
  onSend: (message: string, attachment?: PendingAttachment) => void;
  /** Rendered above the form, inside the input area (e.g. suggestion chips). */
  leading?: ReactNode;
}) {
  const [message, setMessage] = useState("");
  const [attachment, setAttachment] = useState<PendingAttachment | null>(null);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const tooLong = message.length > MAX_MESSAGE_LENGTH;
  const canSubmit = !disabled && !tooLong && (Boolean(message.trim()) || Boolean(attachment));

  // Auto-grow up to a few lines, then scroll inside the box.
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
  }, [message]);

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!canSubmit) return;
    onSend(message, attachment ?? undefined);
    setMessage("");
    setAttachment(null);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter gonderir, Shift+Enter yeni satir acar (IME birlestirme sirasinda dokunma).
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className="border-t app-border">
      {attachmentError && (
        <div className="app-danger-box mx-3 mt-2.5 rounded-md px-3 py-2 text-xs">{attachmentError}</div>
      )}
      {attachment && <AttachmentPreview attachment={attachment} onRemove={() => setAttachment(null)} />}
      {leading}
      <form className="flex items-end gap-2 p-3" onSubmit={submit}>
        <AttachmentMenu
          disabled={disabled}
          onAttach={(a) => {
            setAttachmentError(null);
            setAttachment(a);
          }}
          onError={setAttachmentError}
        />
        <div className="relative min-w-0 flex-1">
          <textarea
            ref={textareaRef}
            rows={1}
            className={`block w-full resize-none rounded-md border app-input px-3 py-2 text-sm leading-5 outline-none ${
              tooLong ? "border-[var(--color-danger)]" : ""
            }`}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            aria-invalid={tooLong}
          />
          {(message.length >= COUNTER_VISIBLE_FROM || tooLong) && (
            <span
              className={`pointer-events-none absolute -top-4 right-1 text-[10px] ${
                tooLong ? "app-danger font-semibold" : "app-muted"
              }`}
            >
              {message.length} / {MAX_MESSAGE_LENGTH}
            </span>
          )}
        </div>
        {isStreaming && onStop ? (
          <Button type="button" variant="secondary" onClick={onStop} aria-label={stopLabel}>
            <span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-current" aria-hidden="true" />
            {stopLabel}
          </Button>
        ) : (
          <Button disabled={!canSubmit}>{buttonLabel}</Button>
        )}
      </form>
    </div>
  );
}
