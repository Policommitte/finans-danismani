"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  CONFIG,
  buildRivalsCurve,
  buildShares,
  pickTargetWinners,
  type GameResult,
  type LocalizedText,
} from "../models/oyun";
import type { ContestQuestionApi } from "../models/contestApi";
import {
  fiftyFiftyContest,
  finishParticipation,
  startParticipation,
  submitContestAnswer,
} from "../services/contestService";
import type { SoundKind } from "./useSoundEffects";
import { useLanguage } from "../contexts/LanguageContext";

export type Powerups = {
  doublePoints: number;
  fiftyFifty: number;
};

export type QuizPhase =
  | "loading" // katılım kaydı + soru listesi backend'den geliyor
  | "curtain" // "Soru N" + görünür geri sayım, HER soruda
  | "reading" // soru metni görünür, şıklar YOK
  | "asking" // şıklar görünür, cevap süresi işliyor
  | "locked" // cevap gönderildi (onaylanarak ya da süre dolarak) — sunucu
  //          sonucu VE süre bitişi ikisi de beklenir
  | "revealed"; // sonuç açıklandı

export type MascotMood = "idle" | "hurry" | "happy" | "sad";

const CURTAIN_SECONDS = 6;
const READING_SECONDS = 2;

/** Sunucudan gelen cevap sonucu — `correctIndex`/`educationNote` ancak
 * cevap gönderildikten SONRA bilinir, bu yüzden soru yüklenirken değil,
 * burada state'e girer. Ağ hatasında `correctIndex: null` ile devam edilir
 * (doğru şık vurgulanmaz, ama oyun akışı tıkanmaz). */
type LocalAnswerResult = {
  isCorrect: boolean;
  pointsEarned: number;
  correctIndex: number | null;
  educationNote: LocalizedText | null;
};

/** Backend'den gelen ham soruyu güncel dile göre görüntülenecek hale getirir.
 * BİLEREK doğru şık/eğitim notu YOK — hile önleme, bkz. backend
 * `ContestQuestion` şeması. */
type LiveQuestion = {
  contestQuestionId: number;
  text: string;
  options: string[];
  timerSeconds: number;
};

function toLiveQuestion(raw: ContestQuestionApi, lang: "tr" | "en"): LiveQuestion {
  return {
    contestQuestionId: raw.contest_question_id,
    text: raw.text[lang],
    options: raw.options.map((o) => o[lang]),
    timerSeconds: raw.timer_seconds,
  };
}

type Args = {
  registeredCount: number;
  powerups: Powerups;
  onUsePowerup: (kind: keyof Powerups) => void;
  onWin: (result: GameResult) => void;
  onLose: (result: GameResult) => void;
  /** Katılım başlatılamazsa (ör. bugünkü hak zaten kullanılmış, kontenjan
   * dolu) çağrılır — ekran "quiz" fazında asılı kalmasın diye. */
  onStartError: (message: string) => void;
  playSound?: (kind: SoundKind) => void;
};

export function useQuiz({
  registeredCount,
  powerups,
  onUsePowerup,
  onWin,
  onLose,
  onStartError,
  playSound,
}: Args) {
  const { language } = useLanguage();

  const [participationId, setParticipationId] = useState<number | null>(null);
  const [rawQuestions, setRawQuestions] = useState<ContestQuestionApi[] | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);

  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<QuizPhase>("loading");
  const [selected, setSelected] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [gained, setGained] = useState<number | null>(null);
  const [correctCount, setCorrectCount] = useState(0);
  const [answerResult, setAnswerResult] = useState<LocalAnswerResult | null>(null);

  const [limit, setLimit] = useState<number>(CONFIG.questionSeconds);
  const [timeLeft, setTimeLeft] = useState<number>(CONFIG.questionSeconds);
  const [curtainLeft, setCurtainLeft] = useState<number>(CURTAIN_SECONDS);
  const [readLeft, setReadLeft] = useState<number>(READING_SECONDS);

  const [shares, setShares] = useState<number[]>([]);
  const [removed, setRemoved] = useState<number[]>([]);
  const [rivals, setRivals] = useState(registeredCount);
  const [mood, setMood] = useState<MascotMood>("idle");
  const [timedOut, setTimedOut] = useState(false);

  const [doublePointsUsed, setDoublePointsUsed] = useState(false);
  const [doublePointsActive, setDoublePointsActive] = useState(false);
  const [fiftyUsed, setFiftyUsed] = useState(false);

  const startedAt = useRef<number>(0);
  const startedRef = useRef(false);
  const totalSteps = CONFIG.questionCount;
  const question = rawQuestions ? toLiveQuestion(rawQuestions[index], language) : undefined;
  const isLast = index === totalSteps - 1;

  // Yarışma başında BİR KEZ hesaplanan hedef kazanan sayısı (100-500) ve bu
  // hedefe inen tam rakip eğrisi — "kaç kişi yarışta" ve şıkların "% doğru
  // bildi" değeri hep BU eğriden türer. BİLEREK simüle: gerçek rakip verisi
  // yok, bkz. backend `ContestRepository` docstring'i.
  const [targetWinners] = useState<number>(() => pickTargetWinners());
  const [rivalsCurve] = useState<number[]>(() =>
    buildRivalsCurve(registeredCount, targetWinners, totalSteps)
  );

  /* ── Katılımı başlat: soru listesini (doğru cevap OLMADAN) backend'den al ──
     `startParticipation` idempotent DEĞİL — günlük katılım hakkını TÜKETİR.
     React'ın geliştirme modunda efektleri iki kez çalıştırması (StrictMode)
     bu çağrıyı iki kez ateşlerse ikincisi haklı olarak 422 döner ve yanlışlıkla
     hataymış gibi görünür. `startedRef` ile TEK seferliğini garanti ediyoruz -
     cleanup'ta SIFIRLANMAZ, aksi halde ikinci StrictMode denemesi de gerçek
     bir çağrı sayılırdı. */
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    startParticipation()
      .then((data) => {
        setParticipationId(data.participation_id);
        setRawQuestions(data.questions);
        setPhase("curtain");
      })
      .catch((exc) => {
        onStartError(exc instanceof Error ? exc.message : "Yarışma başlatılamadı.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Soru hazırlığı: ortak state sıfırlaması (phase ayrı yerde ayarlanır) ── */
  useEffect(() => {
    if (!question) return;

    setSelected(null);
    setGained(null);
    setRemoved([]);
    setDoublePointsUsed(false);
    setDoublePointsActive(false);
    setFiftyUsed(false);
    setTimedOut(false);
    setAnswerResult(null);
    setShares([]);
    setMood("idle");
    setLimit(question.timerSeconds);
    setTimeLeft(question.timerSeconds);
    setCurtainLeft(CURTAIN_SECONDS);
    setReadLeft(READING_SECONDS);

    // Bu sorudan bir sonrakine geçerken rakip sayısının ne kadar azalacağı
    // ÖNCEDEN hesaplanmış rivalsCurve'den gelir; ekranda gösterilen "% doğru
    // bildi" (asıl hesap cevap açıklandığında yapılır, bkz. aşağıdaki
    // answerResult efekti) bu oranın YANSIMASIdır.
    setRivals(rivalsCurve[index]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, rawQuestions]);

  /* ── Cevap açıklandığında (sunucudan sonuç geldiğinde) şık yüzdelerini
     kur — doğru şık artık biliniyor, önceden kurulamazdı. ── */
  useEffect(() => {
    if (!answerResult || answerResult.correctIndex === null) return;
    const survivalPercent = Math.round((rivalsCurve[index + 1] / rivalsCurve[index]) * 100);
    setShares(buildShares(answerResult.correctIndex, survivalPercent));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answerResult]);

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

  /* ── Süre asking'de dolduysa: hiç onaylanmadan cevabı (boş) sunucuya
     bildir ve "locked"e geç — cevaplanmış/zaman aşımı ikisi de artık AYNI
     bekleme fazından geçer (sunucu sonucu gelene kadar açıklanmaz). ── */
  useEffect(() => {
    if (phase !== "asking" || timeLeft > 0) return;
    if (!question || participationId === null) return;

    setTimedOut(true);
    setMood("sad");
    playSound?.("timeout");
    setPhase("locked");

    const elapsed = (Date.now() - startedAt.current) / 1000;
    submitContestAnswer(participationId, {
      contest_question_id: question.contestQuestionId,
      selected_index: null,
      elapsed_seconds: elapsed,
      double_points_active: doublePointsActive,
    })
      .then((result) =>
        setAnswerResult({
          isCorrect: result.is_correct,
          pointsEarned: result.points_earned,
          correctIndex: result.correct_index,
          educationNote: result.education_note,
        })
      )
      .catch((exc) => {
        setNetworkError(exc instanceof Error ? exc.message : "Cevap gönderilemedi.");
        setAnswerResult({ isCorrect: false, pointsEarned: 0, correctIndex: null, educationNote: null });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, timeLeft]);

  /* ── "locked" fazında süre de doldu VE sunucu sonucu da geldiyse: sonucu
     AÇIĞA ÇIKAR. İki koşul birden — normal onaylamada süre zaten sunucudan
     çok önce bitmez, zaman aşımında ise sunucu cevabı hemen gelir. ── */
  useEffect(() => {
    if (phase !== "locked" || timeLeft > 0 || !answerResult) return;

    if (answerResult.isCorrect) {
      setScore((s) => s + answerResult.pointsEarned);
      setGained(answerResult.pointsEarned);
      setCorrectCount((c) => c + 1);
      setMood("happy");
      playSound?.("correct");
    } else {
      setMood("sad");
      playSound?.("wrong");
    }
    setPhase("revealed");
  }, [phase, timeLeft, answerResult, playSound]);

  /* ── Cevap sonrası: sonraki soru ya da bitiş ──
     KRİTİK: index ve phase burada AYNI ANDA (aynı batch içinde) değişir,
     böylece eski faz ile yeni soru metninin birlikte göründüğü "flash"
     karesi hiç oluşmaz. */
  useEffect(() => {
    if (phase !== "revealed" || !question || participationId === null) return;

    const wasCorrect = !timedOut && answerResult?.isCorrect === true;

    const id = setTimeout(() => {
      if (wasCorrect && !isLast) {
        setCurtainLeft(CURTAIN_SECONDS);
        setPhase("curtain");
        setIndex((i) => i + 1);
        return;
      }

      // Yarışma bitti — final skor/doğru sayısı SUNUCUDAN gelir, yereldeki
      // toplamlara güvenilmez. Ödül havuzunu bölen sayı ise BİLEREK gerçek
      // katılımcı sayısı değil, bu oturumun simüle rakip eğrisinin (bkz.
      // rivalsCurve) son değeri — "kaç kişi kazandı" zaten frontend'de
      // simüle edildiği için ödül de AYNI sayıyla hesaplanmalı, yoksa az
      // sayıda gerçek test kullanıcısıyla ödül gerçekçi olmayan şekilde şişer.
      finishParticipation(participationId, { rivals_at_end: targetWinners })
        .then((finishResult) => {
          const result: GameResult = {
            won: finishResult.won,
            score: finishResult.final_score,
            reached: finishResult.reached_question,
            correct: finishResult.correct_count,
            timedOut,
            questionText: question.text,
            correctAnswer:
              answerResult?.correctIndex != null ? question.options[answerResult.correctIndex] : "",
            educationNote: answerResult?.educationNote?.[language] ?? "",
            rivalsAtEnd: finishResult.rivals_at_end,
            payout: finishResult.payout_points,
          };
          if (result.won) onWin(result);
          else onLose(result);
        })
        .catch((exc) => {
          setNetworkError(exc instanceof Error ? exc.message : "Yarışma sonucu kaydedilemedi.");
        });
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
    if (phase !== "asking" || selected === null || !question || participationId === null) return;

    const elapsed = (Date.now() - startedAt.current) / 1000;
    setPhase("locked");

    submitContestAnswer(participationId, {
      contest_question_id: question.contestQuestionId,
      selected_index: selected,
      elapsed_seconds: elapsed,
      double_points_active: doublePointsActive,
    })
      .then((result) =>
        setAnswerResult({
          isCorrect: result.is_correct,
          pointsEarned: result.points_earned,
          correctIndex: result.correct_index,
          educationNote: result.education_note,
        })
      )
      .catch((exc) => {
        setNetworkError(exc instanceof Error ? exc.message : "Cevap gönderilemedi.");
        setAnswerResult({ isCorrect: false, pointsEarned: 0, correctIndex: null, educationNote: null });
      });
  }, [phase, selected, question, participationId, doublePointsActive]);

  const useDoublePoints = useCallback(() => {
    if (phase !== "asking" || doublePointsUsed || powerups.doublePoints <= 0) return;
    setDoublePointsUsed(true);
    setDoublePointsActive(true);
    onUsePowerup("doublePoints");
    playSound?.("powerup");
  }, [phase, doublePointsUsed, powerups.doublePoints, onUsePowerup, playSound]);

  const useFiftyFifty = useCallback(() => {
    if (phase !== "asking" || fiftyUsed || powerups.fiftyFifty <= 0 || !question || participationId === null) {
      return;
    }
    setFiftyUsed(true);
    onUsePowerup("fiftyFifty");
    playSound?.("powerup");

    fiftyFiftyContest(participationId, question.contestQuestionId)
      .then((result) => {
        setRemoved(result.removed_indices);
        setSelected((cur) => (cur !== null && result.removed_indices.includes(cur) ? null : cur));
      })
      .catch((exc) => {
        setNetworkError(exc instanceof Error ? exc.message : "Joker kullanılamadı.");
      });
  }, [phase, fiftyUsed, powerups.fiftyFifty, question, participationId, onUsePowerup, playSound]);

  return {
    question,
    index,
    total: totalSteps,
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
    doublePointsUsed,
    doublePointsActive,
    fiftyUsed,
    revealedCorrectIndex: answerResult?.correctIndex ?? null,
    networkError,
    pick,
    confirm,
    useDoublePoints,
    useFiftyFifty,
  };
}
