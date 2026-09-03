"use client";

import { thinking } from "blobatar/expression";
import "blobatar/motion.css";
import { Blobatar } from "blobatar/react";

/**
 * Sohbet asistaninin yuz ikonu - baslikta, kapali-durum kabarcik
 * butonunda VE (bkz. MessageList.tsx) yanit hazirlanirken gosterilen
 * "dusunuyor" balonunda kullanilir. Ayri bir dosyaya alindi ki
 * MessageList.tsx bunu ChatWidget.tsx'ten import ederken dongusel
 * import (ChatWidget -> MessageList -> ChatWidget) olusmasin.
 */
export function ChatAvatar() {
  return (
    <span className="flex h-full w-full shrink-0 items-center justify-center overflow-hidden rounded-full bg-[var(--color-panel-dark)]">
      <span className="block h-[118%] w-[118%] [&_svg]:h-full [&_svg]:w-full">
        <Blobatar name="Aichatbot" traits={{ shape: 0.933 }} hue={225} expression={thinking} animate="hover" />
      </span>
    </span>
  );
}
