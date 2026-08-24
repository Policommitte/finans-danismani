"use client";

import { useState } from "react";

export type FaqItem = {
  question: string;
  answer: string;
};

function PlusMinusIcon({ open }: { open: boolean }) {
  return (
    <span
      aria-hidden="true"
      className="relative grid h-7 w-7 shrink-0 place-items-center rounded-full text-white transition-transform duration-300"
      style={{ background: "var(--color-brand-teal)" }}
    >
      <span className="absolute h-0.5 w-3 rounded-full bg-current" />
      <span
        className={`absolute h-3 w-0.5 rounded-full bg-current transition-transform duration-300 ${
          open ? "scale-y-0" : "scale-y-100"
        }`}
      />
    </span>
  );
}

export function FaqAccordion({ items }: { items: FaqItem[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="space-y-3">
      {items.map((item, index) => {
        const open = openIndex === index;
        const panelId = `faq-panel-${index}`;

        return (
          <div key={item.question} className="overflow-hidden rounded-lg app-card-muted">
            <button
              type="button"
              onClick={() => setOpenIndex(open ? null : index)}
              aria-expanded={open}
              aria-controls={panelId}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-[var(--color-surface)]"
            >
              <span className="text-sm font-medium app-heading">{item.question}</span>
              <PlusMinusIcon open={open} />
            </button>
            <div
              id={panelId}
              role="region"
              className={`grid transition-[grid-template-rows] duration-300 ease-in-out ${
                open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
              }`}
            >
              <div className="overflow-hidden">
                <p className="px-5 pb-4 text-sm leading-relaxed app-muted">{item.answer}</p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
