"use client";

import type { ReactNode } from "react";

const CHAT_TOGGLE_SELECTOR =
  'button[aria-label="Yatırım Asistanı\'nı aç"], button[aria-label="Sohbeti kapat"]';

export function OpenChatButton({ className, children }: { className?: string; children: ReactNode }) {
  function handleClick() {
    const toggle = document.querySelector<HTMLButtonElement>(CHAT_TOGGLE_SELECTOR);
    toggle?.click();
  }

  return (
    <button type="button" onClick={handleClick} className={className}>
      {children}
    </button>
  );
}
