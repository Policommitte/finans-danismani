"use client";

import { useState } from "react";
import { useChatStream } from "../../hooks/useChatStream";
import Button from "../ui/Button";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const chat = useChatStream();

  return (
    <div className="fixed bottom-5 right-5 z-40">
      {open && (
        <section className="mb-3 flex h-[560px] w-[380px] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-2xl">
          <header className="flex items-center justify-between bg-blue-700 px-4 py-3 text-white">
            <div>
              <div className="font-semibold">Finans asistani</div>
              <div className="text-xs text-blue-100">{chat.status ?? "Hazir"}</div>
            </div>
            <button className="rounded px-2 py-1 text-xl leading-none hover:bg-blue-800" onClick={() => setOpen(false)}>
              ×
            </button>
          </header>
          {chat.error && <div className="bg-red-50 px-4 py-2 text-xs text-red-700">{chat.error}</div>}
          <MessageList messages={chat.messages} />
          <MessageInput disabled={chat.isStreaming} onSend={chat.sendMessage} />
        </section>
      )}
      <Button className="h-14 rounded-full px-5 shadow-lg" onClick={() => setOpen((value) => !value)}>
        {open ? "Kapat" : "AI Chat"}
      </Button>
    </div>
  );
}
