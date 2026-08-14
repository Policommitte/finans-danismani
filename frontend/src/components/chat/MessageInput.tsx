"use client";

import { FormEvent, useState } from "react";
import Button from "../ui/Button";

export function MessageInput({
  disabled,
  onSend,
}: {
  disabled: boolean;
  onSend: (message: string) => void;
}) {
  const [message, setMessage] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    onSend(message);
    setMessage("");
  }

  return (
    <form className="flex gap-2 border-t border-slate-200 p-3" onSubmit={submit}>
      <input
        className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-600"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        placeholder="Mesajinizi yazin"
        disabled={disabled}
      />
      <Button disabled={disabled || !message.trim()}>Gonder</Button>
    </form>
  );
}
