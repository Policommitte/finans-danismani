"use client";

import { useEffect, useState } from "react";
import Card from "../ui/Card";
import { Mascot } from "./Mascot";
import { CONFIG, nextContestDate, type GameResult } from "../../models/oyun";
import { useLanguage } from "../../contexts/LanguageContext";

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
  const { language } = useLanguage();
  const countdown = useNextContest();

  const stats = [
    {
      label: language === "tr" ? "Ulaşılan soru" : "Question reached",
      value: `${result.reached} / ${CONFIG.questionCount}`,
    },
    { label: language === "tr" ? "Doğru cevap" : "Correct answers", value: String(result.correct) },
    {
      label: language === "tr" ? "Skor" : "Score",
      value: result.score.toLocaleString(language === "tr" ? "tr-TR" : "en-US"),
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-col items-center gap-4 py-6 text-center">
                  <Mascot
            mood="sad"
            message={
              result.timedOut
                ? (language === "tr" ? "Süre doldu, üzülme — yarın tekrar deneriz." : "Time's up, don't worry — we'll try again tomorrow.")
                : (language === "tr" ? "Bu sefer olmadı, doğrusuna bakalım." : "Not this time, let's look at the correct answer.")
            }
          />
          <div>
            <p className="app-heading text-2xl font-semibold">
              {language === "tr" ? "Yarışman burada bitti" : "Your contest ended here"}
            </p>
            <p className="app-muted mt-1 text-sm">
              {language === "tr"
                ? (result.timedOut
                    ? `${result.reached}. soruda süre doldu.`
                    : `${result.reached}. soruda yanlış cevap verdin.`)
                : (result.timedOut
                    ? `Time ran out on question ${result.reached}.`
                    : `You answered question ${result.reached} incorrectly.`)}
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

      <Card title={language === "tr" ? "Doğru cevap" : "Correct answer"}>
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
            <p className="app-muted text-[11px] uppercase tracking-wide">
              {language === "tr" ? "Neden" : "Why"}
            </p>
            <p className="mt-1 text-sm leading-relaxed">{result.educationNote}</p>
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex flex-col items-center gap-3 py-4 text-center">
          <p className="app-muted text-xs uppercase tracking-wide">
            {language === "tr" ? "Sonraki yarışma" : "Next contest"}
          </p>
          <p
            className="text-3xl font-semibold tabular-nums"
            style={{ color: "var(--color-primary)" }}
          >
            {countdown}
          </p>
          <p className="app-muted text-sm">
            {language === "tr"
              ? "Her akşam 20.00, tek seans. Yarın tekrar deneyebilirsin."
              : "Every evening at 8:00 PM, one session. You can try again tomorrow."}
          </p>

          <div className="mt-2 flex flex-wrap justify-center gap-2">
            <button
              onClick={onReview}
              className="rounded-lg px-4 py-2 text-sm font-semibold transition"
              style={{
                background: "var(--color-primary)",
                color: "var(--color-on-primary)",
              }}
            >
              {language === "tr" ? "Çalışma notunu incele" : "Review the study notes"}
            </button>
            <button
              onClick={onGoPoints}
              className="rounded-lg border px-4 py-2 text-sm font-semibold transition"
              style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
            >
              {language === "tr" ? "Puanlarım" : "My points"}
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}
