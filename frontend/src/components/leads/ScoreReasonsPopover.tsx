"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Skorun yanindaki "i" imleci: tiklayinca o skorun TURKCE gerekcelerini
 * gosterir. Projede tooltip/popover bileseni ve radix/floating-ui
 * bagimliligi yok; disari tiklayinca kapanma deseni landing sayfasindaki
 * `AuthRequiredPopover`'dan (app/page.tsx) alindi.
 */
export function ScoreReasonsPopover({ reasons }: { reasons: string[] }) {
  const [acik, setAcik] = useState(false);
  const kapsayici = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!acik) return;

    function disariTiklandi(event: PointerEvent) {
      if (!kapsayici.current?.contains(event.target as Node)) {
        setAcik(false);
      }
    }
    function escBasildi(event: KeyboardEvent) {
      if (event.key === "Escape") setAcik(false);
    }

    document.addEventListener("pointerdown", disariTiklandi);
    document.addEventListener("keydown", escBasildi);
    return () => {
      document.removeEventListener("pointerdown", disariTiklandi);
      document.removeEventListener("keydown", escBasildi);
    };
  }, [acik]);

  // Gerekce yoksa imleci hic gosterme - bos bir kutu acmanin anlami yok.
  if (reasons.length === 0) return null;

  return (
    <span ref={kapsayici} className="relative inline-flex">
      <button
        type="button"
        onClick={() => setAcik((v) => !v)}
        aria-expanded={acik}
        aria-label="Skorun gerekçesini göster"
        className="flex h-5 w-5 items-center justify-center rounded-full border app-border text-[10px] font-bold app-muted transition app-subtle-hover"
      >
        i
      </button>

      {acik && (
        <span
          role="status"
          className="absolute right-0 top-full z-50 mt-2 w-64 rounded-md border app-border app-card p-3 text-left shadow-xl"
        >
          <span className="mb-1.5 block text-xs font-semibold uppercase app-muted">
            Skorun gerekçesi
          </span>
          <ul className="space-y-1.5">
            {reasons.map((reason, i) => (
              <li key={i} className="text-xs leading-snug app-heading">
                • {reason}
              </li>
            ))}
          </ul>
        </span>
      )}
    </span>
  );
}
