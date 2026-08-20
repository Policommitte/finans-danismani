"use client";

import Link from "next/link";
import { useState } from "react";
import { Blobatar } from "blobatar/react";
import { thinking } from "blobatar/expression";
import { useChatStream } from "../../hooks/useChatStream";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

function ChatBotAvatar({ size }: { size: number }) {
  return (
    <div style={{ width: size, height: size }}>
      <Blobatar
        name="Aichatbot"
        traits={{ shape: 0.933 }}
        hue={225}
        expression={thinking}
        animate="hover"
        className="h-full w-full"
      />
    </div>
  );
}

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
          <header className="flex items-center gap-3 border-b app-border px-4 py-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[var(--color-primary-soft)]">
              <ChatBotAvatar size={30} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="font-semibold app-heading">Yatırım Asistanı</div>
              <div className="text-xs app-muted">{chat.status ?? "Hazır"}</div>
            </div>
            <button className="rounded px-2 py-1 text-xl leading-none app-muted hover:opacity-80" onClick={() => setOpen(false)}>
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
      <button
        type="button"
        aria-label={open ? "Sohbeti kapat" : "Yatırım Asistanı'nı aç"}
        onClick={() => setOpen((value) => !value)}
        className="grid h-14 w-14 place-items-center rounded-full bg-[var(--color-panel-dark)] shadow-xl transition hover:-translate-y-0.5 hover:shadow-2xl"
      >
        <ChatBotAvatar size={40} />
      </button>
    </div>
  );
}
