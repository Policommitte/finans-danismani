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
            className="w-full rounded-lg px-6 py-3 text-sm font-semibold transition"
            style={{ background: "var(--color-panel-dark)", color: "#fff" }}
          >
            {language === "tr" ? "Test modunda başlat" : "Start in test mode"}
          </button>
          <p className="app-muted mt-2 text-xs">
            {language === "tr"
              ? "Demo için saati beklemeden çalışma notuna geçer. Sunumda bu buton kaldırılacak."
              : "For the demo, this skips ahead to the study notes without waiting for the time. This button will be removed for the presentation."}
          </p>
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
