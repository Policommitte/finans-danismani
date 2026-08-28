"use client";

import { useEffect, useState } from "react";
import Card from "../ui/Card";
import { Mascot } from "./Mascot";
import { CONFIG, nextContestDate, type GameResult } from "../../models/oyun";

type Props = {
  result: GameResult;
  /** Çalışma notu sekmesine dön */
  onReview: () => void;
  /** Puanlar sekmesine git */
  onGoPoints: () => void;
};

/** 20.00'a kalan süre — sn cinsinden canlı sayaç */
function useNextContest() {
  const [left, setLeft] = useState(() => nextContestDate().getTime() - Date.now());

  useEffect(() => {
    const id = setInterval(() => {
      setLeft(nextContestDate().getTime() - Date.now());
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const total = Math.max(0, Math.floor(left / 1000));
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(Math.floor(total / 3600))}:${pad(Math.floor((total % 3600) / 60))}:${pad(total % 60)}`;
}

export function EliminatedScreen({ result, onReview, onGoPoints }: Props) {
  const countdown = useNextContest();

  const stats = [
    { label: "Ulaşılan soru", value: `${result.reached} / ${CONFIG.questionCount}` },
    { label: "Doğru cevap", value: String(result.correct) },
    { label: "Skor", value: result.score.toLocaleString("tr-TR") },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-col items-center gap-4 py-6 text-center">
                  <Mascot
            mood="sad"
            message={
              result.timedOut
                ? "Süre doldu, üzülme — yarın tekrar deneriz."
                : "Bu sefer olmadı, doğrusuna bakalım."
            }
          />
          <div>
            <p className="app-heading text-2xl font-semibold">Yarışman burada bitti</p>
            <p className="app-muted mt-1 text-sm">
              {result.timedOut
                ? `${result.reached}. soruda süre doldu.`
                : `${result.reached}. soruda yanlış cevap verdin.`}
            </p>
          </div>

          <dl className="grid w-full max-w-md grid-cols-3 gap-2">
            {stats.map((s) => (
              <div
                key={s.label}
                className="rounded-lg px-3 py-3"
                style={{ background: "var(--color-surface-muted)" }}
              >
                <dt className="app-muted text-[11px] uppercase tracking-wide">{s.label}</dt>
                <dd className="app-heading mt-1 text-lg font-semibold">{s.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Card>

      <Card title="Doğru cevap">
        <div className="space-y-3">
          <p className="app-muted text-sm">{result.questionText}</p>

          <div
            className="rounded-lg border px-4 py-3"
            style={{
              borderColor: "var(--color-success)",
              background: "var(--color-surface)",
            }}
          >
            <p className="text-sm font-semibold" style={{ color: "var(--color-success)" }}>
              {result.correctAnswer}
            </p>
          </div>

          <div
            className="rounded-lg px-4 py-3"
            style={{ background: "var(--color-surface-muted)" }}
          >
            <p className="app-muted text-[11px] uppercase tracking-wide">Neden</p>
            <p className="mt-1 text-sm leading-relaxed">{result.educationNote}</p>
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex flex-col items-center gap-3 py-4 text-center">
          <p className="app-muted text-xs uppercase tracking-wide">Sonraki yarışma</p>
          <p
            className="text-3xl font-semibold tabular-nums"
            style={{ color: "var(--color-primary)" }}
          >
            {countdown}
          </p>
          <p className="app-muted text-sm">Her akşam 20.00, tek seans. Yarın tekrar deneyebilirsin.</p>

          <div className="mt-2 flex flex-wrap justify-center gap-2">
            <button
              onClick={onReview}
              className="rounded-lg px-4 py-2 text-sm font-semibold transition"
              style={{
                background: "var(--color-primary)",
                color: "var(--color-on-primary)",
              }}
            >
              Çalışma notunu incele
            </button>
            <button
              onClick={onGoPoints}
              className="rounded-lg border px-4 py-2 text-sm font-semibold transition"
              style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
            >
              Puanlarım
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}
