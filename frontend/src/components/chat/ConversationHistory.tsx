"use client";

import { useEffect, useState } from "react";
import type { Conversation } from "../../models/chat";
import { getConversations } from "../../services/conversationsService";

const COPY = {
  tr: {
    title: "Sohbet geçmişi",
    empty: "Henüz kayıtlı sohbet yok.",
    loading: "Yükleniyor…",
    failed: "Geçmiş yüklenemedi.",
    messages: (n: number) => `${n} mesaj`,
    close: "Kapat",
  },
  en: {
    title: "Conversation history",
    empty: "No saved conversations yet.",
    loading: "Loading…",
    failed: "History could not be loaded.",
    messages: (n: number) => `${n} messages`,
    close: "Close",
  },
} as const;

function formatDate(value: string, locale: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(date);
}

/**
 * Drawer listing the user's persisted conversations (`GET /api/conversations`).
 * Selecting one restores it into the widget; the list refreshes each time the
 * drawer opens so a thread started a minute ago is already there.
 */
export function ConversationHistory({
  open,
  activeConversationId,
  language,
  onSelect,
  onClose,
}: {
  open: boolean;
  activeConversationId: number | null;
  language: "tr" | "en";
  onSelect: (conversationId: number) => void;
  onClose: () => void;
}) {
  const copy = COPY[language] ?? COPY.tr;
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const [items, setItems] = useState<Conversation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setError(null);
    getConversations()
      .then((rows) => {
        if (active) setItems(rows);
      })
      .catch(() => {
        if (active) setError(copy.failed);
      });
    return () => {
      active = false;
    };
  }, [open, copy.failed]);

  if (!open) return null;

  return (
    <div className="absolute inset-x-0 top-[3.75rem] bottom-0 z-30 flex flex-col bg-[var(--color-surface)]">
      <div className="flex items-center justify-between border-b app-border px-4 py-2">
        <span className="text-sm font-semibold app-heading">{copy.title}</span>
        <button
          type="button"
          onClick={onClose}
          className="rounded px-2 py-0.5 text-xs app-muted app-subtle-hover"
        >
          {copy.close}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {error && <div className="app-danger-box rounded-md px-3 py-2 text-xs">{error}</div>}
        {!error && items === null && <div className="px-2 py-3 text-xs app-muted">{copy.loading}</div>}
        {items && items.length === 0 && <div className="px-2 py-3 text-xs app-muted">{copy.empty}</div>}
        {items && items.length > 0 && (
          <ul className="space-y-1">
            {items.map((conversation) => {
              const isActive = conversation.id === activeConversationId;
              return (
                <li key={conversation.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(conversation.id)}
                    className={`w-full rounded-md px-3 py-2 text-left transition ${
                      isActive ? "app-primary-soft" : "app-subtle-hover"
                    }`}
                  >
                    <div className="truncate text-sm font-medium app-heading">
                      {conversation.title || `#${conversation.id}`}
                    </div>
                    <div className="mt-0.5 flex justify-between text-[11px] app-muted">
                      <span>{formatDate(conversation.updated_at, locale)}</span>
                      {typeof conversation.message_count === "number" && (
                        <span>{copy.messages(conversation.message_count)}</span>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
