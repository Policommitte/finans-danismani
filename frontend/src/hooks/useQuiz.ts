"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  CONFIG,
  buildShares,
  prepareQuestions,
  scoreFor,
  type GameResult,
  type PreparedQuestion,
} from "../models/oyun";
import type { SoundKind } from "./useSoundEffects";

/** Kullanıcının elindeki jokerler */
export type Powerups = {
  timeShield: number; // +10 saniye
  fiftyFifty: number; // iki yanlış şıkkı eler
};

/** Sorunun içinde bulunduğu aşama */
export type QuizPhase =
  | "curtain" // "Soru N" perdesi
  | "asking" // süre işliyor, cevap bekleniyor
  | "revealed"; // cevap verildi, doğru gösteriliyor

export type MascotMood = "idle" | "hurry" | "happy" | "sad";

const CURTAIN_MS = 900;

type Args = {
  /** Yarışmaya kayıt olan kişi sayısı — rakip sayacının başlangıcı */
  registeredCount: number;
  powerups: Powerups;
  onUsePowerup: (kind: keyof Powerups) => void;
  onWin: (result: GameResult) => void;
  onLose: (result: GameResult) => void;
  playSound?: (kind: SoundKind) => void;
};

export function useQuiz({
 registeredCount,
  powerups,
  onUsePowerup,
  onWin,
  onLose,
  playSound,
}: Args) {
  const [questions] = useState<PreparedQuestion[]>(() => prepareQuestions());
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<QuizPhase>("curtain");
  const [selected, setSelected] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [gained, setGained] = useState<number | null>(null);
  const [correctCount, setCorrectCount] = useState(0);

  const [limit, setLimit] = useState<number>(CONFIG.questionSeconds);
  const [timeLeft, setTimeLeft] = useState<number>(CONFIG.questionSeconds);
  const [shares, setShares] = useState<number[]>([]);
  const [removed, setRemoved] = useState<number[]>([]); // 50/50 ile elenen şıklar
  const [rivals, setRivals] = useState(registeredCount);
  const [mood, setMood] = useState<MascotMood>("idle");
  const [timedOut, setTimedOut] = useState(false);

  // Bu soruda joker kullanıldı mı
  const [shieldUsed, setShieldUsed] = useState(false);
  const [fiftyUsed, setFiftyUsed] = useState(false);

  const startedAt = useRef<number>(0);
  const prevShares = useRef<number>(100); // önceki sorunun doğru cevap oranı
  const question = questions[index];
  const isLast = index === questions.length - 1;

  /* ── Soru hazırlığı: perde → soru ── */
  useEffect(() => {
    if (!question) return;

    setPhase("curtain");
    setSelected(null);
    setGained(null);
    setRemoved([]);
    setShieldUsed(false);
    setFiftyUsed(false);
    setTimedOut(false);
    setMood("idle");
    setLimit(question.timerSeconds);
    setTimeLeft(question.timerSeconds);
    const nextShares = buildShares(question.correctIndex);
    setShares(nextShares);

    // Bir önceki soruda doğru cevabı seçen oran kadar katılımcı hayatta kalır.
    // Böylece gösterilen yüzde ile eleme sayısı tutarlı olur.
    if (index > 0) {
      const prevCorrectShare = prevShares.current;
      setRivals((n) => Math.max(1, Math.round((n * prevCorrectShare) / 100)));
    }
    prevShares.current = nextShares[question.correctIndex];

    const id = setTimeout(() => {
      setPhase("asking");
      startedAt.current = Date.now();
    }, CURTAIN_MS);

    return () => clearTimeout(id);
  }, [index, question]);

  /* ── Geri sayım ── */
  useEffect(() => {
    if (phase !== "asking") return;
    if (timeLeft <= 0) return;

    const id = setTimeout(() => setTimeLeft((n) => n - 1), 1000);
    return () => clearTimeout(id);
  }, [phase, timeLeft]);

  /* ── Son 5 saniye uyarısı ── */
  useEffect(() => {
    if (phase !== "asking") return;
    if (timeLeft <= 5 && timeLeft > 0) {
      setMood("hurry");
      playSound?.("tick");
    }
  }, [phase, timeLeft, playSound]);
  

  useEffect(() => {
    if (phase !== "asking" || timeLeft > 0) return;
    setTimedOut(true);
    setMood("sad");
    setPhase("revealed");
  playSound?.("timeout");
  }, [phase, timeLeft, playSound]);
  /* ── Cevap sonrası: sonraki soru ya da bitiş ── */
  useEffect(() => {
    if (phase !== "revealed" || !question) return;

    const wasCorrect = !timedOut && selected === question.correctIndex;

    const id = setTimeout(() => {
      if (wasCorrect && !isLast) {
        setIndex((i) => i + 1);
        return;
      }

      const result: GameResult = {
        won: wasCorrect && isLast,
        score,
        reached: index + 1,
        correct: correctCount,
        timedOut,
        questionText: question.text,
        correctAnswer: question.options[question.correctIndex],
        educationNote: question.educationNote,
      };

      if (result.won) onWin(result);
      else onLose(result);
    }, CONFIG.answerRevealMs);

    return () => clearTimeout(id);
    //: Bilincli olarak SADECE `phase` izleniyor: bu efekt "revealed" fazina
    //: GIRISTE bir kerelik bir zamanlayici kurar. question/selected/score/
    //: correctCount/timedOut/isLast/onWin/onLose degerleri o an icin zaten
    //: dogru (confirm() hepsini phase="revealed" ile AYNI batch'te set eder),
    //: ve phase "revealed" kaldigi surece bir daha degismezler - bu yuzden
    //: eksik-bagimlilik eslint uyarisi burada gecerli bir yeniden-calisma
    //: riski isaret etmiyor. Tum bagimliliklari eklemek, her soru sonrasi
    //: zamanlayiciyi gereksiz yere sifirlar/tekrar kurar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  /* ── Eylemler ── */

  const pick = useCallback(
    (i: number) => {
      if (phase !== "asking" || removed.includes(i)) return;
      setSelected(i);
    },
    [phase, removed]
  );

  const confirm = useCallback(() => {
    if (phase !== "asking" || selected === null || !question) return;

    const elapsed = (Date.now() - startedAt.current) / 1000;
    const correct = selected === question.correctIndex;

    if (correct) {
      const points = scoreFor(elapsed, limit);
      setScore((s) => s + points);
      setGained(points);
      setCorrectCount((c) => c + 1);
      setMood("happy");
      playSound?.("correct");
    } else {
      setMood("sad");
      playSound?.("wrong");
    }
    setPhase("revealed");
  
  }, [phase, selected, question, limit, playSound]);

  /** Zaman kalkanı: süreyi 10 saniye uzatır */
  const useTimeShield = useCallback(() => {
    if (phase !== "asking" || shieldUsed || powerups.timeShield <= 0) return;
    setShieldUsed(true);
    setLimit((l) => l + 10);
    setTimeLeft((t) => t + 10);
    onUsePowerup("timeShield");
  playSound?.("powerup");
  }, [phase, shieldUsed, powerups.timeShield, onUsePowerup, playSound]);

  /** Çifte şans: iki yanlış şıkkı eler */
  const useFiftyFifty = useCallback(() => {
    if (phase !== "asking" || fiftyUsed || powerups.fiftyFifty <= 0 || !question) return;

    const wrong = question.options
      .map((_, i) => i)
      .filter((i) => i !== question.correctIndex)
      .sort(() => Math.random() - 0.5)
      .slice(0, 2);

    setRemoved(wrong);
    if (selected !== null && wrong.includes(selected)) setSelected(null);
    setFiftyUsed(true);
    onUsePowerup("fiftyFifty");
playSound?.("powerup");
}, [phase, fiftyUsed, powerups.fiftyFifty, question, selected, onUsePowerup, playSound]);

  return {
    question,
    index,
    total: questions.length,
    phase,
    selected,
    score,
    gained,
    correctCount,
    timeLeft,
    limit,
    shares,
    removed,
    rivals,
    mood,
    timedOut,
    shieldUsed,
    fiftyUsed,
    pick,
    confirm,
    useTimeShield,
    useFiftyFifty,
  };
}