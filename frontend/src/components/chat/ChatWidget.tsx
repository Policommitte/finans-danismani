"use client";

import Link from "next/link";
import { useState } from "react";
import { useChatStream } from "../../hooks/useChatStream";
import Button from "../ui/Button";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

export function ChatWidget({
  canSend = true,
  blockedMessage = "Soru sormadan önce giriş yapmalısınız.",
}: {
  canSend?: boolean;
  blockedMessage?: string;
}) {
  const [open, setOpen] = useState(false);
  const chat = useChatStream();
  const messages = canSend ? chat.messages : [];

  function sendMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed || !canSend) {
      return;
    }

    chat.sendMessage(trimmed);
  }

  return (
    <div className="fixed bottom-5 right-5 z-40">
      {open && (
        <section className="absolute bottom-16 right-0 flex h-[560px] w-[380px] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-lg border app-card shadow-2xl">
          <header className="flex items-center justify-between app-primary px-4 py-3">
            <div>
              <div className="font-semibold">Finans asistanı</div>
              <div className="text-xs opacity-80">{chat.status ?? "Hazır"}</div>
            </div>
            <button className="rounded px-2 py-1 text-xl leading-none hover:opacity-80" onClick={() => setOpen(false)}>
              ×
            </button>
          </header>
          {chat.error && <div className="app-danger-box px-4 py-2 text-xs">{chat.error}</div>}
          <MessageList
            messages={messages}
            emptyState={
              canSend ? undefined : (
                <Link href="/login" className="font-semibold text-[var(--color-primary)] underline-offset-4 hover:underline">
                  {blockedMessage}
                </Link>
              )
            }
          />
          <MessageInput
            disabled={!canSend || chat.isStreaming}
            onSend={sendMessage}
            placeholder={canSend ? "Mesajınızı yazın" : "Giriş yapmanız gerekir"}
            buttonLabel="Gönder"
          />
        </section>
      )}
      <Button className="h-14 rounded-full px-5 shadow-lg" onClick={() => setOpen((value) => !value)}>
        AI Chat
      </Button>
    </div>
  );
}
