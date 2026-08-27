"use client";

import { useState } from "react";
import Button from "../ui/Button";

function BarChartIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 20V10" />
      <path d="M12 20V4" />
      <path d="M20 20v-7" />
    </svg>
  );
}

type QuizOption = {
  label: string;
  points: 1 | 2 | 3;
};

type QuizQuestion = {
  id: string;
  question: string;
  options: QuizOption[];
};

const quizQuestions: QuizQuestion[] = [
  {
    id: "q1",
    question: "Portföyünde %20 değer kaybı yaşarsan ne yaparsın?",
    options: [
      { label: "Hemen satarım", points: 1 },
      { label: "Bekler, izlerim", points: 2 },
      { label: "Fırsat bilip artırırım", points: 3 },
    ],
  },
  {
    id: "q2",
    question: "Yatırım vadeni nasıl tanımlarsın?",
    options: [
      { label: "Kısa vadeli, 1 yıldan az", points: 1 },
      { label: "Orta vadeli, 1-3 yıl", points: 2 },
      { label: "Uzun vadeli, 3+ yıl", points: 3 },
    ],
  },
  {
    id: "q3",
    question: "Yüksek getiri için ne kadar risk almaya hazırsın?",
    options: [
      { label: "Düşük risk, düşük getiri yeterli", points: 1 },
      { label: "Dengeli bir risk-getiri isterim", points: 2 },
      { label: "Yüksek risk alıp yüksek getiri hedeflerim", points: 3 },
    ],
  },
  {
    id: "q4",
    question: "Yatırım deneyimin ne kadar?",
    options: [
      { label: "Yeni başladım", points: 1 },
      { label: "Birkaç yıldır yatırım yapıyorum", points: 2 },
      { label: "Deneyimliyim, aktif işlem yapıyorum", points: 3 },
    ],
  },
];

const MIN_SCORE = quizQuestions.length * 1;
const MAX_SCORE = quizQuestions.length * 3;

function tierFor(score: number): { label: string; color: string } {
  if (score <= 6) {
    return { label: "Düşük", color: "var(--color-cta)" };
  }
  if (score <= 9) {
    return { label: "Orta", color: "var(--color-chart-yellow)" };
  }
  return { label: "Yüksek", color: "var(--color-success)" };
}

//: tierFor()'un gosterim esikleriyle (<=6 / <=9 / uzeri) BIREBIR ayni -
//: kullanicinin ekranda gordugu "Dusuk/Orta/Yuksek" etiketiyle backend'e
//: yazilan enum her zaman uyusmali.
function tierEnumFor(score: number): "LOW" | "MEDIUM" | "HIGH" {
  if (score <= 6) {
    return "LOW";
  }
  if (score <= 9) {
    return "MEDIUM";
  }
  return "HIGH";
}

export function RiskProfileQuiz({
  onComplete,
}: {
  onComplete?: (tier: "LOW" | "MEDIUM" | "HIGH") => void;
} = {}) {
  const [answers, setAnswers] = useState<Record<string, 1 | 2 | 3>>({});
  const [score, setScore] = useState<number | null>(null);

  const allAnswered = quizQuestions.every((q) => answers[q.id] !== undefined);

  function selectOption(questionId: string, points: 1 | 2 | 3) {
    setAnswers((prev) => ({ ...prev, [questionId]: points }));
  }

  function handleSubmit() {
    if (!allAnswered) {
      return;
    }
    const total = quizQuestions.reduce((sum, q) => sum + (answers[q.id] ?? 0), 0);
    setScore(total);
    onComplete?.(tierEnumFor(total));
  }

  function handleRetake() {
    setAnswers({});
    setScore(null);
  }

  return (
    <div className="rounded-2xl border app-card p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <span
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
          style={{
            background: "color-mix(in srgb, var(--color-primary) 15%, var(--color-surface))",
            color: "var(--color-primary)",
          }}
        >
          <BarChartIcon />
        </span>
        <h2 className="text-base font-semibold app-heading">Risk Profilim</h2>
      </div>
      <p className="mt-2 text-sm app-muted">Birkaç soruyu yanıtla, yatırım risk toleransını görelim.</p>

      {score === null ? (
        <>
          <div className="mt-4 space-y-3">
            {quizQuestions.map((q, index) => (
              <div key={q.id} className="rounded-xl app-card-muted p-4">
                <p className="text-sm font-medium app-heading">
                  {index + 1}. {q.question}
                </p>
                <div className="mt-3 grid gap-2 sm:grid-cols-3">
                  {q.options.map((option) => {
                    const selected = answers[q.id] === option.points;
                    return (
                      <button
                        key={option.label}
                        type="button"
                        onClick={() => selectOption(q.id, option.points)}
                        aria-pressed={selected}
                        className={`w-full rounded-lg border p-3 text-left text-sm transition ${
                          selected
                            ? "border-[var(--color-primary)] app-primary-soft"
                            : "app-border app-surface hover:opacity-80"
                        }`}
                      >
                        {option.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          <Button type="button" onClick={handleSubmit} disabled={!allAnswered} className="mt-4">
            Testi Tamamla
          </Button>
        </>
      ) : (
        <div className="mt-4 rounded-xl app-card-muted p-4">
          <div className="relative mt-2">
            <div className="flex h-3 overflow-hidden rounded-full">
              <div className="flex-1" style={{ background: "var(--color-cta)" }} />
              <div className="flex-1" style={{ background: "var(--color-chart-yellow)" }} />
              <div className="flex-1" style={{ background: "var(--color-success)" }} />
            </div>
            <div
              className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 shadow"
              style={{
                left: `${((score - MIN_SCORE) / (MAX_SCORE - MIN_SCORE)) * 100}%`,
                background: tierFor(score).color,
                borderColor: "var(--color-surface)",
              }}
            />
          </div>
          <div className="mt-3 flex justify-between text-xs app-muted">
            <span>Düşük</span>
            <span>Orta</span>
            <span>Yüksek</span>
          </div>

          <p className="mt-4 text-sm app-heading">
            Risk Profilin: <span className="font-bold">{tierFor(score).label}</span>
          </p>

          <Button type="button" variant="secondary" onClick={handleRetake} className="mt-3 border app-border">
            Testi Yeniden Yap
          </Button>
        </div>
      )}
    </div>
  );
}
