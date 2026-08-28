"use client";

import Card from "../ui/Card";
import { Mascot } from "./Mascot";
import { useQuiz, type Powerups } from "../../hooks/useQuiz";
import { MASCOT_IDLE } from "../../models/oyun";
import type { GameResult } from "../../models/oyun";
import type { SoundKind } from "../../hooks/useSoundEffects";
import { useLanguage } from "../../contexts/LanguageContext";

type Props = {
  registeredCount: number;
  powerups: Powerups;
  onUsePowerup: (kind: keyof Powerups) => void;

  onWin: (result: GameResult) => void;
 onLose: (result: GameResult) => void;
 playSound?: (kind: SoundKind) => void;
};

const LETTERS = ["A", "B", "C", "D"];
const RING = 226; // 2πr, r = 36

const MASCOT_CORRECT = [
  { tr: "Doğru cevap, harika gidiyorsun.", en: "Correct answer, you're doing great." },
  { tr: "Aynen öyle, tuttun.", en: "Exactly right, nailed it." },
  { tr: "Doğru, bu bilgiyi biliyordun.", en: "Correct, you knew this one." },
  { tr: "İsabet, devam et.", en: "Spot on, keep going." },
];

export function QuizScreen(props: Props) {
  const { language } = useLanguage();
  const q = useQuiz(props);

  if (!q.question) return null;

  const ratio = q.timeLeft / q.limit;
  const urgent = q.timeLeft <= 5;
  const revealed = q.phase === "revealed";

  const message =
    q.mood === "happy"
      ? MASCOT_CORRECT[q.index % MASCOT_CORRECT.length][language]
      : q.mood === "sad"
        ? q.timedOut
          ? (language === "tr" ? "Süre doldu, cevap alınamadı." : "Time's up, no answer was submitted.")
          : (language === "tr" ? "Bu sefer olmadı. Doğru cevap işaretlendi." : "Not this time. The correct answer has been marked.")
        : q.mood === "hurry"
          ? (language === "tr" ? "Süre doluyor, kararınızı verin." : "Time's running out, make your decision.")
          : MASCOT_IDLE[q.index % MASCOT_IDLE.length][language];

  return (
    <div className="relative">
      {/* soru geçiş perdesi */}
      {q.phase === "curtain" && (
        <div
          className="qz-curtain absolute inset-0 z-20 grid place-items-center rounded-xl"
          style={{ background: "var(--color-panel-dark)" }}
        >
          <span className="text-4xl font-bold" style={{ color: "#fff" }}>
            {language === "tr" ? "Soru" : "Question"} {q.index + 1}
          </span>
        </div>
      )}

      <Card>
        {/* başlık: soru no · rakipler · sayaç · skor */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span
              className="rounded-full px-3 py-1.5 text-xs font-bold"
              style={{
                background: "var(--color-primary-soft)",
                color: "var(--color-primary-soft-text)",
              }}
            >
              {language === "tr" ? "Soru" : "Question"} {q.index + 1} / {q.total}
            </span>
            <span className="app-muted flex items-center gap-1.5 text-xs">
              <span
                className="rv-dot h-1.5 w-1.5 rounded-full"
                style={{ background: "var(--color-primary)" }}
              />
              <b className="app-heading font-bold tabular-nums">
                {q.rivals.toLocaleString(language === "tr" ? "tr-TR" : "en-US")}
              </b>{" "}
              {language === "tr" ? "yarışta" : "in the race"}
            </span>
          </div>

          <div className="flex items-center gap-4">
            {/* dairesel sayaç */}
            <div className="relative h-16 w-16 shrink-0">
              <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
                <circle cx="40" cy="40" r="36" fill="none" strokeWidth="6" stroke="var(--color-border)" />
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  fill="none"
                  strokeWidth="6"
                  strokeLinecap="round"
                  stroke={urgent ? "var(--color-danger)" : "var(--color-success)"}
                  strokeDasharray={RING}
                  strokeDashoffset={RING - ratio * RING}
                  style={{ transition: "stroke-dashoffset 1s linear, stroke .3s" }}
                />
              </svg>
              <span
                className="absolute inset-0 grid place-items-center text-xl font-bold tabular-nums"
                style={{ color: urgent ? "var(--color-danger)" : "var(--color-heading)" }}
              >
                {q.timeLeft}
              </span>
            </div>

            {/* skor */}
            <div className="relative min-w-[64px] text-right">
              <span
                className="block text-[10px] font-bold uppercase tracking-wider"
                style={{ color: "var(--color-muted)" }}
              >
                {language === "tr" ? "Skor" : "Score"}
              </span>
              <b className="app-heading text-xl font-bold tabular-nums">
                {q.score.toLocaleString(language === "tr" ? "tr-TR" : "en-US")}
              </b>
              {q.gained !== null && (
                <span
                  key={q.index}
                  className="qz-gain absolute right-0 top-full text-[13px] font-bold"
                  style={{ color: "var(--color-success)" }}
                >
                  +{q.gained}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* ilerleme */}
        <div
          className="mt-3 h-1 overflow-hidden rounded-full"
          style={{ background: "var(--color-border)" }}
        >
          <span
            className="block h-full rounded-full transition-[width] duration-500"
            style={{
              width: `${((q.index + 1) / q.total) * 100}%`,
              background: "var(--color-success)",
            }}
          />
        </div>

        {/* maskot */}
        <div className="mt-4">
          <Mascot mood={q.mood} message={message} />
        </div>

        {/* soru */}
        <h3 className="app-heading mt-4 text-lg font-semibold leading-snug">{q.question.text}</h3>

        {/* şıklar */}
        <div className="mt-4 space-y-2.5">
          {q.question.options.map((opt, i) => {
            const isRemoved = q.removed.includes(i);
            const isPicked = q.selected === i;
            const isCorrect = i === q.question!.correctIndex;
            const showCorrect = revealed && isCorrect;
            const showWrong = revealed && isPicked && !isCorrect;

            let bg = "var(--color-surface)";
            let border = "transparent";
            if (showCorrect) {
              bg = "var(--color-primary-soft)";
              border = "var(--color-success)";
            } else if (showWrong) {
              bg = "var(--color-danger-bg)";
              border = "var(--color-danger)";
            } else if (isPicked) {
              bg = "var(--color-primary-soft)";
              border = "var(--color-primary)";
            }

            return (
              <button
                key={i}
                onClick={() => q.pick(i)}
                disabled={q.phase !== "asking" || isRemoved}
                className="relative w-full overflow-hidden rounded-xl border-2 px-4 py-3 text-left transition disabled:cursor-default"
                style={{
                  background: bg,
                  borderColor: border,
                  opacity: isRemoved ? 0.35 : 1,
                  paddingBottom: revealed ? 22 : undefined,
                }}
              >
                <div className="flex items-start gap-3">
                  <span
                    className="w-5 shrink-0 text-base font-bold"
                    style={{ color: "var(--color-muted)" }}
                  >
                    {LETTERS[i]}
                  </span>
                  <span
                    className="text-[14.5px] font-semibold leading-snug"
                    style={{ color: "var(--color-text)" }}
                  >
                    {isRemoved ? "—" : opt}
                  </span>
                </div>

                {/* şık dağılımı */}
                {revealed && (
                  <span className="absolute inset-x-0 bottom-0 flex items-center">
                    <span
                      className="block h-1.5 rounded-br-none transition-[width] duration-500"
                      style={{
                        width: `${q.shares[i] ?? 0}%`,
                        background: showCorrect
                          ? "rgba(4,120,87,.5)"
                          : showWrong
                            ? "rgba(220,38,38,.45)"
                            : "rgba(100,116,139,.3)",
                      }}
                    />
                    <em
                      className="ml-2 text-[11.5px] font-bold not-italic"
                      style={{ color: "var(--color-muted)" }}
                    >
                      %{q.shares[i] ?? 0}
                    </em>
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* jokerler + onay */}
        {q.phase === "asking" && (
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <button
              onClick={q.useTimeShield}
              disabled={props.powerups.timeShield <= 0 || q.shieldUsed}
              className="rounded-lg border px-3 py-2 text-xs font-semibold transition disabled:opacity-40"
              style={{ borderColor: "var(--color-border)", color: "var(--color-text)" }}
              title={language === "tr" ? "Süreyi 10 saniye uzatır" : "Extends the timer by 10 seconds"}
            >
              {language === "tr" ? "Zaman kalkanı" : "Time shield"} ({props.powerups.timeShield})
            </button>

            <button
              onClick={q.useFiftyFifty}
              disabled={props.powerups.fiftyFifty <= 0 || q.fiftyUsed}
              className="rounded-lg border px-3 py-2 text-xs font-semibold transition disabled:opacity-40"
              style={{ borderColor: "var(--color-border)", color: "var(--color-text)" }}
              title={language === "tr" ? "İki yanlış şıkkı eler" : "Eliminates two wrong options"}
            >
              {language === "tr" ? "Çifte şans" : "Double chance"} ({props.powerups.fiftyFifty})
            </button>

            <button
              onClick={q.confirm}
              disabled={q.selected === null}
              className="ml-auto rounded-lg px-7 py-3 text-sm font-semibold transition disabled:cursor-not-allowed"
              style={{
                background: q.selected === null ? "var(--color-border)" : "var(--color-primary)",
                color: q.selected === null ? "var(--color-muted)" : "#fff",
              }}
            >
              {language === "tr" ? "Cevabı onayla" : "Confirm answer"}
            </button>
          </div>
        )}

      </Card>
    </div>
  );
}
