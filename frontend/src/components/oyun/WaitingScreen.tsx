"use client";

import { useState } from "react";
import Card from "../ui/Card";
import { useCountdown, nextContestTime } from "../../hooks/useCountdown";
import { CONFIG } from "../../models/oyun";

type Props = {
  onStart: () => void;
};

export function WaitingScreen({ onStart }: Props) {
  const [target] = useState(() => nextContestTime());
  const { hours, minutes, seconds } = useCountdown(target);

  return (
    <Card>
      <div className="py-10 text-center">
        <span
          className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold"
          style={{ background: "var(--color-primary-soft)", color: "var(--color-success)" }}
        >
          ✓ Kaydın alındı
        </span>

        <h2 className="app-heading mt-4 text-2xl font-semibold">Yarışma bekleniyor</h2>

        <p className="app-muted mx-auto mt-2 max-w-md text-sm leading-relaxed">
          Yarışma saati geldiğinde çalışma notu açılacak. O ana kadar bu sayfada
          kalabilirsin, otomatik olarak yönlendirileceksin.
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
            Test modunda başlat
          </button>
          <p className="app-muted mt-2 text-xs">
            Demo için saati beklemeden çalışma notuna geçer. Sunumda bu buton kaldırılacak.
          </p>
        </div>

        <p className="app-muted mt-6 text-xs">
          {CONFIG.questionCount} soru · her biri {CONFIG.questionSeconds} saniye ·{" "}
          {CONFIG.prizePool.toLocaleString("tr-TR")} bonus puan havuzu
        </p>
      </div>
    </Card>
  );
}
