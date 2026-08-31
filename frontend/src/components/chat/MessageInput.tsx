"use client";

import { FormEvent, useState } from "react";
import Button from "../ui/Button";
import { AttachmentMenu, type PendingAttachment } from "./AttachmentMenu";
import { AttachmentPreview } from "./AttachmentPreview";

export function MessageInput({
  disabled,
  placeholder = "Mesajınızı yazın",
  buttonLabel = "Gönder",
  onSend,
}: {
  disabled: boolean;
  placeholder?: string;
  buttonLabel?: string;
  onSend: (message: string, attachment?: PendingAttachment) => void;
}) {
  const [message, setMessage] = useState("");
  const [attachment, setAttachment] = useState<PendingAttachment | null>(null);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!message.trim() && !attachment) return;
    onSend(message, attachment ?? undefined);
    setMessage("");
    setAttachment(null);
  }

  return (
    <div className="border-t app-border">
      {attachmentError && (
        <div className="app-danger-box mx-3 mt-2.5 rounded-md px-3 py-2 text-xs">{attachmentError}</div>
      )}
      {attachment && <AttachmentPreview attachment={attachment} onRemove={() => setAttachment(null)} />}
      <form className="flex gap-2 p-3" onSubmit={submit}>
        <AttachmentMenu
          disabled={disabled}
          onAttach={(a) => {
            setAttachmentError(null);
            setAttachment(a);
          }}
          onError={setAttachmentError}
        />
        <input
          className="min-w-0 flex-1 rounded-md border app-input px-3 py-2 text-sm outline-none"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder={placeholder}
          disabled={disabled}
        />
        <Button disabled={disabled || (!message.trim() && !attachment)}>{buttonLabel}</Button>
      </form>
    </div>
  );
}
