"use client";

import { useEffect, useRef, useState } from "react";
import type { CallOutcome, CallOutcomeInput } from "../../models/leads";
import { DURUM_ETIKETLERI, DURUM_SINIFLARI, type LeadDurum } from "./leadFields";

/**
 * DURUM sutunundaki rozet - ayni zamanda gorusme sonucunu isaretleme
 * menusu. Ayri bir "islem" sutunu ACMADIK: tablo zaten dokuz sutun, ve
 * danismanin zihninde "durum" ile "gorusme sonucu" ayni sey.
 *
 * Disari tiklayinca kapanma deseni `ScoreReasonsPopover` ile ayni
 * (projede popover bileseni / radix-floating-ui bagimliligi yok).
 */

const SECENEKLER: Array<{ deger: CallOutcome; etiket: string }> = [
  { deger: "KABUL", etiket: DURUM_ETIKETLERI.kabul },
  { deger: "ISTEMIYOR", etiket: DURUM_ETIKETLERI.istemiyor },
  { deger: "ULASILAMADI", etiket: DURUM_ETIKETLERI.ulasilamadi },
];

//: Renk BILEREK burada verilmiyor: `app-heading` ile `app-muted` ayni
//: ozelligi (color) yazar, ikisini tek sinif dizesinde birlestirmek
//: kazananin index.css'teki TANIM SIRASINA baglanmasina yol acardi.
const SATIR_SINIFI =
  "block w-full px-3 py-1.5 text-left text-xs font-medium transition app-subtle-hover";

export function CallOutcomeMenu({
  durum,
  mevcutSonuc,
  kaydediliyor,
  onSec,
}: {
  durum: LeadDurum;
  mevcutSonuc: CallOutcome | null;
  kaydediliyor: boolean;
  onSec: (outcome: CallOutcomeInput) => void;
}) {
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

  function sec(outcome: CallOutcomeInput) {
    setAcik(false);
    onSec(outcome);
  }

  return (
    <span ref={kapsayici} className="relative inline-flex">
      <button
        type="button"
        onClick={() => setAcik((v) => !v)}
        disabled={kaydediliyor}
        aria-haspopup="menu"
        aria-expanded={acik}
        aria-label={`Görüşme sonucunu güncelle (şu an: ${DURUM_ETIKETLERI[durum]})`}
        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition hover:opacity-80 disabled:opacity-50 ${DURUM_SINIFLARI[durum]}`}
      >
        {kaydediliyor ? "Kaydediliyor…" : DURUM_ETIKETLERI[durum]}
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

      {acik && (
        <span
          role="menu"
          className="absolute left-0 top-full z-50 mt-1.5 w-40 overflow-hidden rounded-md border app-border app-card py-1 shadow-xl"
        >
          {SECENEKLER.map((secenek) => (
            <button
              key={secenek.deger}
              type="button"
              role="menuitem"
              onClick={() => sec(secenek.deger)}
              className={`${SATIR_SINIFI} ${
                mevcutSonuc === secenek.deger ? "app-primary-soft" : "app-heading"
              }`}
            >
              {secenek.etiket}
            </button>
          ))}

          {/* Yanlis isaretlemeyi geri almanin baska yolu yok; sonuc
              yalnizca isaretlenmisken gosterilir. */}
          {mevcutSonuc !== null && (
            <>
              <span className="my-1 block border-t app-border-soft" />
              <button
                type="button"
                role="menuitem"
                onClick={() => sec("ACIK")}
                className={`${SATIR_SINIFI} app-muted`}
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
