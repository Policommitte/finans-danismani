"use client";

import { useState, type ReactNode } from "react";

type Props = {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
};

export function AccordionItem({ title, children, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      className="rounded-xl border"
      style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left"
      >
        <span className="app-heading text-sm font-semibold">{title}</span>
        <span
          className="shrink-0 text-lg font-bold transition-transform"
          style={{
            color: "var(--color-muted)",
            transform: open ? "rotate(45deg)" : "rotate(0deg)",
          }}
          aria-hidden="true"
        >
          +
        </span>
      </button>

      {open && (
        <div className="app-muted px-4 pb-4 text-[13.5px] leading-relaxed">{children}</div>
      )}
    </div>
  );
}