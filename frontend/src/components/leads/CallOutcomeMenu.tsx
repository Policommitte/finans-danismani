"use client";

import { useEffect, useRef, useState } from "react";
import type { CallOutcome, CallOutcomeInput } from "../../models/leads";
import { STATUS_LABELS, STATUS_CLASSES, type LeadStatus } from "./leadFields";

/**
 * DURUM sutunundaki rozet - ayni zamanda gorusme sonucunu isaretleme
 * menusu. Ayri bir "islem" sutunu ACMADIK: tablo zaten dokuz sutun, ve
 * danismanin zihninde "durum" ile "gorusme sonucu" ayni sey.
 *
 * Disari tiklayinca kapanma deseni `ScoreReasonsPopover` ile ayni
 * (projede popover bileseni / radix-floating-ui bagimliligi yok).
 */

const OPTIONS: Array<{ value: CallOutcome; label: string }> = [
  { value: "KABUL", label: STATUS_LABELS.accepted },
  { value: "ISTEMIYOR", label: STATUS_LABELS.declined },
  { value: "ULASILAMADI", label: STATUS_LABELS.unreachable },
];

//: Renk BILEREK burada verilmiyor: `app-heading` ile `app-muted` ayni
//: ozelligi (color) yazar, ikisini tek sinif dizesinde birlestirmek
//: kazananin index.css'teki TANIM SIRASINA baglanmasina yol acardi.
const ITEM_CLASS =
  "block w-full px-3 py-1.5 text-left text-xs font-medium transition app-subtle-hover";

export function CallOutcomeMenu({
  status,
  currentOutcome,
  saving,
  onSelect,
}: {
  status: LeadStatus;
  currentOutcome: CallOutcome | null;
  saving: boolean;
  onSelect: (outcome: CallOutcomeInput) => void;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;

    function handleOutsideClick(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("pointerdown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("pointerdown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  function select(outcome: CallOutcomeInput) {
    setOpen(false);
    onSelect(outcome);
  }

  return (
    <span ref={containerRef} className="relative inline-flex">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={saving}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Görüşme sonucunu güncelle (şu an: ${STATUS_LABELS[status]})`}
        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition hover:opacity-80 disabled:opacity-50 ${STATUS_CLASSES[status]}`}
      >
        {saving ? "Kaydediliyor…" : STATUS_LABELS[status]}
        {/* Metin oku (▾) yazi tipine gore inceliyor ve rozetin kucuk
            puntosunda zor secilir; ciziksel bir chevron her boyutta net. */}
        <svg
          width="11"
          height="11"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className="shrink-0"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {open && (
        <span
          role="menu"
          className="absolute left-0 top-full z-50 mt-1.5 w-40 overflow-hidden rounded-md border app-border app-card py-1 shadow-xl"
        >
          {OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              role="menuitem"
              onClick={() => select(option.value)}
              className={`${ITEM_CLASS} ${
                currentOutcome === option.value ? "app-primary-soft" : "app-heading"
              }`}
            >
              {option.label}
            </button>
          ))}

          {/* Yanlis isaretlemeyi geri almanin baska yolu yok; sonuc
              yalnizca isaretlenmisken gosterilir. */}
          {currentOutcome !== null && (
            <>
              <span className="my-1 block border-t app-border-soft" />
              <button
                type="button"
                role="menuitem"
                onClick={() => select("ACIK")}
                className={`${ITEM_CLASS} app-muted`}
              >
                Sonucu temizle
              </button>
            </>
          )}
        </span>
      )}
    </span>
  );
}
