"use client";

import type { DailyBriefTone } from "../../hooks/useDailyBrief";

const TONE_COLOR: Record<DailyBriefTone, string> = {
  positive: "text-[var(--color-success)]",
  negative: "text-[var(--color-danger)]",
  flat: "text-[var(--color-muted)]",
};

function ToneIcon({ tone }: { tone: DailyBriefTone }) {
  return (
    <svg
      aria-hidden="true"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`mt-0.5 shrink-0 ${TONE_COLOR[tone]}`}
    >
      {tone === "flat" ? (
        <path d="M4 12h16" />
      ) : tone === "positive" ? (
        <>
          <path d="M3 17l6-6 4 4 8-8" />
          <path d="M15 7h6v6" />
        </>
      ) : (
        <>
          <path d="M3 7l6 6 4-4 8 8" />
          <path d="M15 17h6v-6" />
        </>
      )}
    </svg>
  );
}

/**
 * Sohbet dugmesinin ustunde beliren gunluk ozet daveti.
 *
 * Iki ayri eylem tasir ve bu yuzden IC ICE DUGME KULLANILMAZ (gecersiz HTML,
 * tiklama hedefleri de birbirine karisir): govde tam genisligi kaplayan bir
 * dugme, kapatma ise onun KARDESI olan mutlak konumlu ikinci bir dugmedir.
 */
export function DailyBriefBubble({
  tone,
  teaser,
  actionLabel,
  closeLabel,
  onOpen,
  onDismiss,
}: {
  tone: DailyBriefTone;
  teaser: string;
  actionLabel: string;
  closeLabel: string;
  onOpen: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className="chat-pop-in absolute bottom-[4.75rem] right-0 z-30 w-[16rem] max-w-[calc(100vw-2.5rem)]">
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-start gap-2 rounded-2xl rounded-br-md border app-card px-3.5 py-3 text-left shadow-xl transition hover:-translate-y-0.5 hover:border-[var(--color-primary)]"
      >
        <ToneIcon tone={tone} />
        <span className="min-w-0">
          <span className="block text-sm font-semibold app-heading">{teaser}</span>
          <span className="mt-1 block text-xs font-semibold text-[var(--color-primary)]">
            {actionLabel}
          </span>
        </span>
      </button>
      {/* Baloncugun sohbet dugmesine bakan kuyrugu - kart zemini ve kenarligi
          ayni degiskenlerden gelsin diye dondurulmus bir kare. */}
      <span
        aria-hidden="true"
        className="absolute -bottom-[5px] right-7 h-2.5 w-2.5 rotate-45 border-b border-r app-card"
      />
      <button
        type="button"
        aria-label={closeLabel}
        onClick={onDismiss}
        className="absolute -right-1.5 -top-1.5 grid h-6 w-6 place-items-center rounded-full border app-card text-sm leading-none shadow-md transition hover:opacity-80"
      >
        ×
      </button>
    </div>
  );
}
