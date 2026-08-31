"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  CONFIG,
  buildRivalsCurve,
  buildShares,
  computePayout,
  pickTargetWinners,
  prepareQuestions,
  scoreFor,
  type GameResult,
  type PreparedQuestion,
} from "../models/oyun";
import type { SoundKind } from "./useSoundEffects";
import { useLanguage } from "../contexts/LanguageContext";

export type Powerups = {
  timeShield: number; // "çift puan" jokeri olarak kullanılıyor
  fiftyFifty: number;
};

export type QuizPhase =
  | "curtain" // "Soru N" + görünür geri sayım, HER soruda
  | "reading" // soru metni görünür, şıklar YOK
  | "asking" // şıklar görünür, cevap süresi işliyor
  | "locked" // cevap kaydedildi ama SÜRE BİTENE KADAR açıklanmaz
  | "revealed"; // süre doldu, sonuç gösteriliyor

export type MascotMood = "idle" | "hurry" | "happy" | "sad";

const CURTAIN_SECONDS = 6;
const READING_SECONDS = 2;

type LockedResult = {
  correct: boolean;
  points: number;
};

type Args = {
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
  const { language } = useLanguage();
  const [questions] = useState<PreparedQuestion[]>(() => prepareQuestions(language));
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<QuizPhase>("curtain");
  const [selected, setSelected] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [gained, setGained] = useState<number | null>(null);
  const [correctCount, setCorrectCount] = useState(0);
  const [locked, setLocked] = useState<LockedResult | null>(null);

  const [limit, setLimit] = useState<number>(CONFIG.questionSeconds);
  const [timeLeft, setTimeLeft] = useState<number>(CONFIG.questionSeconds);
  const [curtainLeft, setCurtainLeft] = useState<number>(CURTAIN_SECONDS);
  const [readLeft, setReadLeft] = useState<number>(READING_SECONDS);

  const [shares, setShares] = useState<number[]>([]);
  const [removed, setRemoved] = useState<number[]>([]);
  const [rivals, setRivals] = useState(registeredCount);
  const [mood, setMood] = useState<MascotMood>("idle");
  const [timedOut, setTimedOut] = useState(false);

  const [shieldUsed, setShieldUsed] = useState(false);
  const [doublePointsActive, setDoublePointsActive] = useState(false);
  const [fiftyUsed, setFiftyUsed] = useState(false);

  const startedAt = useRef<number>(0);
  const question = questions[index];
  const isLast = index === questions.length - 1;
  // rivalsCurve[i] = soru i'ye GİRERKEN yarışta olan kişi sayısı;
  // rivalsCurve[questions.length] = SON sorunun kendi sonucu uygulandıktan
  // SONRA kalan sayı (= kazanan sayısı). Böylece son sorudaki "% doğru
  // bildi" de tıpkı diğerleri gibi gerçek bir azalmaya karşılık gelir —
  // ekranda donup kalan bir sayı olmaz.
  const totalSteps = questions.length;

  // Yarışma başında BİR KEZ hesaplanan hedef kazanan sayısı (100-500) ve bu
  // hedefe inen tam rakip eğrisi — "kaç kişi yarışta", şıkların "% doğru
  // bildi" değeri ve sonuçtaki kazanan sayısı hep BU eğriden türer.
  const [targetWinners] = useState<number>(() => pickTargetWinners());
  const [rivalsCurve] = useState<number[]>(() =>
    buildRivalsCurve(registeredCount, targetWinners, totalSteps)
  );

  /* ── Soru hazırlığı: ortak state sıfırlaması (phase ayrı yerde ayarlanır) ── */
  useEffect(() => {
    if (!question) return;

    setSelected(null);
    setGained(null);
    setRemoved([]);
    setShieldUsed(false);
    setDoublePointsActive(false);
    setFiftyUsed(false);
    setTimedOut(false);
    setLocked(null);
    setMood("idle");
    setLimit(question.timerSeconds);
    setTimeLeft(question.timerSeconds);
    setCurtainLeft(CURTAIN_SECONDS);
    setReadLeft(READING_SECONDS);

    // Bu sorunun KENDİSİ de dahil, her soru rakip sayısını rivalsCurve'de bir
    // adım aşağı indirir (son soru da farklı değil); ekranda gösterilen
    // "% doğru bildi" bu adımın YANSIMASIdır — bağımsız rastgele bir süreç
    // değil, tek kaynak.
    const survivalPercent = Math.round((rivalsCurve[index + 1] / rivalsCurve[index]) * 100);
    setShares(buildShares(question.correctIndex, survivalPercent));
    setRivals(rivalsCurve[index]);
  }, [index, question, rivalsCurve]);

  /* ── Perde: "Soru N" + görünür geri sayım, HER soruda ── */
  useEffect(() => {
    if (phase !== "curtain") return;
    if (curtainLeft <= 0) {
      setPhase("reading");
      return;
    }
    const id = setTimeout(() => setCurtainLeft((n) => n - 1), 1000);
    return () => clearTimeout(id);
  }, [phase, curtainLeft]);

  /* ── Okuma fazı: soru görünür, şıklar yok ── */
  useEffect(() => {
    if (phase !== "reading") return;
    if (readLeft <= 0) {
      setPhase("asking");
      startedAt.current = Date.now();
      return;
    }
    const id = setTimeout(() => setReadLeft((n) => n - 1), 1000);
    return () => clearTimeout(id);
  }, [phase, readLeft]);

  /* ── Geri sayım — "asking" ve "locked" fazlarında çalışmaya devam eder ── */
  useEffect(() => {
    if (phase !== "asking" && phase !== "locked") return;
    if (timeLeft <= 0) return;

    const id = setTimeout(() => setTimeLeft((n) => n - 1), 1000);
    return () => clearTimeout(id);
  }, [phase, timeLeft]);

  /* ── Son 5 saniye uyarısı ── */
  useEffect(() => {
    if (phase !== "asking" && phase !== "locked") return;
    if (timeLeft <= 5 && timeLeft > 0) {
      setMood("hurry");
      playSound?.("tick");
    }
  }, [phase, timeLeft, playSound]);

  /* ── Süre doldu: sonucu AÇIĞA ÇIKAR ── */
  useEffect(() => {
    if ((phase !== "asking" && phase !== "locked") || timeLeft > 0) return;

    if (phase === "asking") {
      setTimedOut(true);
      setMood("sad");
      playSound?.("timeout");
      setPhase("revealed");
      return;
    }

    if (locked) {
      if (locked.correct) {
        setScore((s) => s + locked.points);
        setGained(locked.points);
        setCorrectCount((c) => c + 1);
        setMood("happy");
        playSound?.("correct");
      } else {
        setMood("sad");
        playSound?.("wrong");
      }
    }
    setPhase("revealed");
  }, [phase, timeLeft, locked, playSound]);

  /* ── Cevap sonrası: sonraki soru ya da bitiş ──
     KRİTİK: index ve phase burada AYNI ANDA (aynı batch içinde) değişir,
     böylece eski faz ile yeni soru metninin birlikte göründüğü "flash"
     karesi hiç oluşmaz. */
  useEffect(() => {
    if (phase !== "revealed" || !question) return;

    const wasCorrect = !timedOut && locked?.correct === true;

    const id = setTimeout(() => {
      if (wasCorrect && !isLast) {
        setCurtainLeft(CURTAIN_SECONDS);
        setPhase("curtain");
        setIndex((i) => i + 1);
        return;
      }

      // Bu sorunun SONUCU uygulandıktan sonra kalan kişi sayısı — canlı
      // ekranda görülen `rivals` (soruya GİRERKEN gösterilen sayı) değil,
      // bir adım ilerisi. Kazanan sayısı ve payout TEK bu değerden gelir.
      const rivalsAfterThisQuestion = rivalsCurve[index + 1];

      const result: GameResult = {
        won: wasCorrect && isLast,
        score,
        reached: index + 1,
        correct: correctCount,
        timedOut,
        questionText: question.text,
        correctAnswer: question.options[question.correctIndex],
        educationNote: question.educationNote,
        rivalsAtEnd: rivalsAfterThisQuestion,
        payout: computePayout(rivalsAfterThisQuestion),
      };

      if (result.won) onWin(result);
      else onLose(result);
    }, CONFIG.answerRevealMs);

    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  /* ── Eylemler ── */

  const pick = useCallback(
    (i: number) => {
      if (phase !== "asking" || removed.includes(i)) return;
      setSelected(i);
      playSound?.("tick");
    },
    [phase, removed, playSound]
  );

  const confirm = useCallback(() => {
    if (phase !== "asking" || selected === null || !question) return;

    const elapsed = (Date.now() - startedAt.current) / 1000;
    const correct = selected === question.correctIndex;
    const basePoints = correct ? scoreFor(elapsed, limit) : 0;
    const points = doublePointsActive ? basePoints * 2 : basePoints;

    setLocked({ correct, points });
    setPhase("locked");
  }, [phase, selected, question, limit, doublePointsActive]);

  const useDoublePoints = useCallback(() => {
    if (phase !== "asking" || shieldUsed || powerups.timeShield <= 0) return;
    setShieldUsed(true);
    setDoublePointsActive(true);
    onUsePowerup("timeShield");
    playSound?.("powerup");
  }, [phase, shieldUsed, powerups.timeShield, onUsePowerup, playSound]);

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
    curtainLeft,
    readLeft,
    shares,
    removed,
    rivals,
    mood,
    timedOut,
    shieldUsed,
    doublePointsActive,
    fiftyUsed,
    pick,
    confirm,
    useDoublePoints,
    useFiftyFifty,
  };
}