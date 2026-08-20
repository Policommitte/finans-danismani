"use client";

import { thinking } from "blobatar/expression";
import "blobatar/motion.css";
import { Blobatar } from "blobatar/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useChatStream } from "../../hooks/useChatStream";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

function ChatAvatar() {
  return (
    <span className="flex h-full w-full shrink-0 items-center justify-center overflow-hidden rounded-full bg-[var(--color-panel-dark)]">
      <span className="block h-[118%] w-[118%] [&_svg]:h-full [&_svg]:w-full">
        <Blobatar name="Aichatbot" traits={{ shape: 0.933 }} hue={225} expression={thinking} animate="hover" />
      </span>
    </span>
  );
}

export function ChatWidget({
  canSend = true,
  blockedMessage = "Soru sormadan önce giriş yapmalısınız.",
  open: controlledOpen,
  onOpenChange,
}: {
  canSend?: boolean;
  blockedMessage?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen ?? internalOpen;
  const [renderPanel, setRenderPanel] = useState(open);
  const [closing, setClosing] = useState(false);
  const chat = useChatStream();
  const messages = canSend ? chat.messages : [];

  useEffect(() => {
    if (open) {
      setRenderPanel(true);
      setClosing(false);
      return;
    }

    if (!renderPanel) {
      return;
    }

    setClosing(true);
    const timer = window.setTimeout(() => {
      setRenderPanel(false);
      setClosing(false);
    }, 170);

    return () => window.clearTimeout(timer);
  }, [open, renderPanel]);

  function setOpen(nextOpen: boolean) {
    if (controlledOpen === undefined) {
      setInternalOpen(nextOpen);
    }
    onOpenChange?.(nextOpen);
  }

  function sendMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed || !canSend) {
      return;
    }

    chat.sendMessage(trimmed);
  }

  return (
    <div className="fixed bottom-5 right-5 z-40">
      {renderPanel && (
        <section
          className={`absolute bottom-24 right-0 z-20 flex h-[560px] w-[380px] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-lg border app-card shadow-2xl ${
            closing ? "chat-pop-out" : "chat-pop-in"
          }`}
        >
          <header className="flex items-center justify-between app-primary px-4 py-3">
            <div className="flex items-center gap-3">
              <span className="h-8 w-8">
                <ChatAvatar />
              </span>
              <div>
                <div className="font-semibold">Yatırım Asistanı</div>
                <div className="text-xs opacity-80">{chat.status ?? "Hazır"}</div>
              </div>
            </div>
            <button
              type="button"
              aria-label="Sohbeti kapat"
              className="rounded px-2 py-1 text-xl leading-none hover:opacity-80"
              onClick={() => setOpen(false)}
            >
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
        className="relative z-30 h-16 w-16 rounded-full bg-[var(--color-panel-dark)] p-0 shadow-lg transition hover:-translate-y-0.5 hover:brightness-110"
        aria-label={open ? "Sohbeti kapat" : "Yatırım Asistanı'nı aç"}
        onClick={() => setOpen(!open)}
      >
        <ChatAvatar />
      </button>
    </div>
  );
}
