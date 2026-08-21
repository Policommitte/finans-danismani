"use client";

import { FormEvent, useState } from "react";
import Button from "../ui/Button";

export function MessageInput({
  disabled,
  placeholder = "Mesajınızı yazın",
  buttonLabel = "Gönder",
  onSend,
}: {
  disabled: boolean;
  placeholder?: string;
  buttonLabel?: string;
  onSend: (message: string) => void;
}) {
  const [message, setMessage] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    onSend(message);
    setMessage("");
  }

  return (
    <form className="flex gap-2 border-t app-border p-3" onSubmit={submit}>
      <input
        className="min-w-0 flex-1 rounded-md border app-input px-3 py-2 text-sm outline-none"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        placeholder={placeholder}
        disabled={disabled}
      />
      <Button disabled={disabled || !message.trim()}>{buttonLabel}</Button>
    </form>
  );
}
