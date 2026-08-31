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
  { tr: "Tam isabet, gayet iyi gidiyorsun.", en: "Bang on, you're on a roll." },
  { tr: "Bildin! Sıradaki soruya hazır ol.", en: "Got it! Get ready for the next one." },
];

const MASCOT_TIMEOUT = [
  { tr: "Süre doldu, cevap alınamadı.", en: "Time's up, no answer was submitted." },
  { tr: "Vakit yetmedi, bu sefer olmadı.", en: "Ran out of time this round." },
  { tr: "Süreyi kaçırdık, sıradaki soruda dikkatli ol.", en: "Missed the window — be quicker next time." },
];

const MASCOT_WRONG = [
  { tr: "Bu sefer olmadı. Doğru cevap işaretlendi.", en: "Not this time. The correct answer has been marked." },
  { tr: "Yanlış oldu, ama doğrusunu birlikte görelim.", en: "Wrong one, but let's see the right answer." },
  { tr: "Olsun, doğru cevabı not al.", en: "It's okay, take note of the right answer." },
];

const MASCOT_HURRY = [
  { tr: "Süre doluyor, kararınızı verin.", en: "Time's running out, make your decision." },
  { tr: "Son saniyeler, seç ve onayla.", en: "Final seconds, pick and confirm." },
  { tr: "Acele et, süre azalıyor.", en: "Hurry up, time is running low." },
];

const MASCOT_READING = [
  { tr: "Soruyu oku, şıklar birazdan gelecek.", en: "Read the question, options are coming up." },
  { tr: "Önce soruyu iyice oku.", en: "Take a moment to read the question first." },
  { tr: "Hazırlan, şıklar hemen açılıyor.", en: "Get ready, the options are about to open." },
];

const MASCOT_LOCKED = [
  { tr: "Cevabın kaydedildi. Süre bitince açıklanacak…", en: "Your answer is saved. It will be revealed when time's up…" },
  { tr: "Kararın alındı, şimdi süreyi bekliyoruz.", en: "Your choice is locked in, now we wait for time." },
  { tr: "Cevabın güvende, sonuç süre bitince belli olacak.", en: "Your answer is safe, the result shows when time runs out." },
];

const MASCOT_CURTAIN = [
  { tr: "Hazır ol, soru geliyor.", en: "Get ready, the question is coming." },
  { tr: "Yeni soru için hazırlan.", en: "Get set for the next question." },
  { tr: "Konsantre ol, başlıyoruz.", en: "Stay focused, here we go." },
];

export function QuizScreen(props: Props) {
  const { language } = useLanguage();
  const q = useQuiz(props);

  if (!q.question) return null;

  const ratio = q.timeLeft / q.limit;
  const urgent = q.timeLeft <= 5;
  const revealed = q.phase === "revealed";
  // Şıklar SADECE bu iki fazda kesinlikle gizli — curtain VE reading.
  const hideOptions = q.phase === "curtain" || q.phase === "reading";

  const message =
    q.phase === "curtain"
      ? MASCOT_CURTAIN[q.index % MASCOT_CURTAIN.length][language]
      : q.phase === "locked"
        ? MASCOT_LOCKED[q.index % MASCOT_LOCKED.length][language]
        : q.mood === "happy"
          ? MASCOT_CORRECT[q.index % MASCOT_CORRECT.length][language]
          : q.mood === "sad"
            ? q.timedOut
              ? MASCOT_TIMEOUT[q.index % MASCOT_TIMEOUT.length][language]
              : MASCOT_WRONG[q.index % MASCOT_WRONG.length][language]
            : q.mood === "hurry"
              ? MASCOT_HURRY[q.index % MASCOT_HURRY.length][language]
              : q.phase === "reading"
                ? MASCOT_READING[q.index % MASCOT_READING.length][language]
                : MASCOT_IDLE[q.index % MASCOT_IDLE.length][language];

  return (
    <div className="relative">
      {/* "Soru N" + görünür geri sayım — HER soruda */}
      {q.phase === "curtain" && (
        <div
          className="qz-curtain absolute inset-0 z-20 grid place-items-center rounded-xl"
          style={{ background: "var(--color-panel-dark)" }}
        >
          <span className="text-6xl font-bold" style={{ color: "#fff" }}>
            {language === "tr" ? "Soru" : "Question"} {q.index + 1}
          </span>
        </div>
      )}

      <Card>
        

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
            {/* Sayaç HER fazda görünür — reading/curtain sırasında dolu (limit)
                durur, ancak "asking"e geçince gerçekten azalmaya başlar. */}
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

        <div className="mt-4">
          <Mascot mood={q.mood} message={message} showHand={q.mood === "happy"} />
        </div>

        <h3 className="app-heading mt-4 text-lg font-semibold leading-snug">{q.question.text}</h3>

        {!hideOptions && (
          <div className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {q.question.options.map((opt, i) => {
              const isRemoved = q.removed.includes(i);
              const isPicked = q.selected === i;
              const isCorrect = i === q.question!.correctIndex;
              const showCorrect = revealed && isCorrect;
              const showWrong = revealed && isPicked && !isCorrect;
              const showFaded = revealed && !isCorrect && !isPicked;

              const animClass = showCorrect || showWrong
                ? " qz-reveal-pop"
                : isPicked
                  ? " qz-pick-bump"
                  : "";

              // Dolu renkli kutular yerine nötr kart: doğru/yanlış geri
              // bildirimi (yeşil/kırmızı) fonksiyonel olduğu için solid
              // dolgu olarak kalıyor, ama şıklar arasında ARTIK sabit
              // renk ayrımı yok — tek accent (--color-primary) kullanılıyor.
              const isRevealedHighlight = showCorrect || showWrong;
              const background = showCorrect
                ? "var(--color-success)"
                : showWrong
                  ? "var(--color-danger)"
                  : isPicked && !revealed
                    ? "var(--color-primary-soft)"
                    : "var(--color-surface-muted)";
              const borderColor = showCorrect
                ? "var(--color-success)"
                : showWrong
                  ? "var(--color-danger)"
                  : isPicked && !revealed
                    ? "var(--color-primary)"
                    : "var(--color-border)";
              const textColor = isRevealedHighlight ? "#ffffff" : "var(--color-text)";
              const badgeBg = isRevealedHighlight ? "rgba(255,255,255,.25)" : "var(--color-primary-soft)";
              const badgeColor = isRevealedHighlight ? "#ffffff" : "var(--color-primary)";

              return (
                <button
                  key={i}
                  onClick={() => q.pick(i)}
                  disabled={q.phase !== "asking" || isRemoved}
                  className={"relative w-full overflow-hidden rounded-xl border-2 px-4 py-4 text-left transition disabled:cursor-default" + animClass}
                  style={{
                    background,
                    borderColor,
                    opacity: isRemoved ? 0.25 : showFaded ? 0.35 : 1,
                    boxShadow: isPicked && !revealed ? "0 8px 20px rgba(0,0,0,.12)" : undefined,
                    transform: isPicked && !revealed ? "scale(1.03)" : undefined,
                    zIndex: isPicked && !revealed ? 1 : undefined,
                  }}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className="grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-bold"
                      style={{ background: badgeBg, color: badgeColor }}
                    >
                      {LETTERS[i]}
                    </span>
                    <span
                      className="text-[14.5px] font-bold leading-snug"
                      style={{ color: textColor }}
                    >
                      {isRemoved ? "—" : opt}
                    </span>

                    {showCorrect && (
                      <span className="ml-auto shrink-0 text-lg font-bold" style={{ color: "#fff" }}>
                        ✓
                      </span>
                    )}
                    {showWrong && (
                      <span className="ml-auto shrink-0 text-lg font-bold" style={{ color: "#fff" }}>
                        ✕
                      </span>
                    )}
                    {isPicked && (q.phase === "asking" || q.phase === "locked") && (
                      <span
                        className="ml-auto grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-black"
                        style={{ background: "var(--color-primary)", color: "#fff" }}
                      >
                        ✓
                      </span>
                    )}
                  </div>

                  {revealed && (
                    <span
                      className="mt-1.5 block text-[11px] font-bold"
                      style={{ color: isRevealedHighlight ? "rgba(255,255,255,.85)" : "var(--color-muted)" }}
                    >
                      %{q.shares[i] ?? 0}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {q.phase === "asking" && (
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <button
              onClick={q.useDoublePoints}
              disabled={props.powerups.timeShield <= 0 || q.shieldUsed}
              className="flex items-center gap-2 rounded-lg border-2 px-3 py-2 text-xs font-semibold transition disabled:opacity-40"
              style={{
                borderColor: "#f5a524",
                background: "rgba(245, 165, 36, 0.12)",
                color: "#8a5a10",
              }}
              title={language === "tr" ? "Bu soruyu dogru bilirsen puanini ikiye katlar" : "Doubles your points if you get this question right"}
            >
              <span
                className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px] font-black"
                style={{ background: "#f5a524", color: "#3d2400" }}
              >
                2×
              </span>
              {language === "tr" ? "Çift puan" : "Double points"} ({props.powerups.timeShield})
            </button>

            <button
              onClick={q.useFiftyFifty}
              disabled={props.powerups.fiftyFifty <= 0 || q.fiftyUsed}
              className="flex items-center gap-2 rounded-lg border-2 px-3 py-2 text-xs font-semibold transition disabled:opacity-40"
              style={{
                borderColor: "#8b5cf6",
                background: "rgba(139, 92, 246, 0.12)",
                color: "#5b21b6",
              }}
              title={language === "tr" ? "İki yanlış şıkkı eler" : "Eliminates two wrong options"}
            >
              <span
                className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px] font-black leading-none"
                style={{ background: "#8b5cf6", color: "#fff" }}
              >
                50
              </span>
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