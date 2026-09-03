"use client";

import { useState } from "react";
import Card from "../ui/Card";
import { useCountdown, nextContestTime } from "../../hooks/useCountdown";
import { CONFIG } from "../../models/oyun";
import { useLanguage } from "../../contexts/LanguageContext";

type Props = {
  onStart: () => void;
};

export function WaitingScreen({ onStart }: Props) {
  const { language } = useLanguage();
  const [target] = useState(() => nextContestTime());
  const { hours, minutes, seconds } = useCountdown(target);

  return (
    <Card>
      <div className="py-10 text-center">
        <span
          className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold"
          style={{ background: "var(--color-primary-soft)", color: "var(--color-success)" }}
        >
          {language === "tr" ? "✓ Kaydın alındı" : "✓ You're registered"}
        </span>

        <h2 className="app-heading mt-4 text-2xl font-semibold">
          {language === "tr" ? "Yarışma bekleniyor" : "Waiting for the contest"}
        </h2>

        <p className="app-muted mx-auto mt-2 max-w-md text-sm leading-relaxed">
          {language === "tr"
            ? "Yarışma saati geldiğinde çalışma notu açılacak. O ana kadar bu sayfada kalabilirsin, otomatik olarak yönlendirileceksin."
            : "The study notes will open once the contest time arrives. You can stay on this page until then — you'll be redirected automatically."}
        </p>

        <strong
          className="mt-6 block text-4xl font-bold tabular-nums"
          style={{ color: "var(--color-primary)" }}
        >
          {hours}:{minutes}:{seconds}
        </strong>

        <div className="mx-auto mt-8 max-w-md">
          <button
            onClick={onStart}
            className="group w-full rounded-full px-6 py-3.5 text-sm font-bold text-white transition hover:scale-[1.03] hover:shadow-xl active:scale-[0.98]"
            style={{
              background: "linear-gradient(135deg, var(--color-cta) 0%, var(--color-cta-hover) 100%)",
              boxShadow: "0 8px 24px color-mix(in srgb, var(--color-cta) 45%, transparent)",
            }}
          >
            <span className="inline-flex items-center justify-center gap-2">
              <span className="animate-pulse text-base" aria-hidden="true">
                ⚡
              </span>
              {language === "tr" ? "Çalışma notlarına geç" : "Go to the study notes"}
            </span>
          </button>
        </div>

        <p className="app-muted mt-6 text-xs">
          {language === "tr"
            ? `${CONFIG.questionCount} soru · her biri ${CONFIG.questionSeconds} saniye · ${CONFIG.prizePool.toLocaleString("tr-TR")} bonus puan havuzu`
            : `${CONFIG.questionCount} questions · ${CONFIG.questionSeconds} seconds each · ${CONFIG.prizePool.toLocaleString("en-US")} bonus point pool`}
        </p>
      </div>
    </Card>
  );
}
