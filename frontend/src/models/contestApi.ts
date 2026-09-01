/**
 * `backend/app/schemas/contest.py` ile BIREBIR AYNI alan adları (snake_case) -
 * diğer API modelleri (bkz. `models/portfolio.ts`) de bu kuralı izliyor,
 * dönüştürme katmanı yok.
 *
 * Rakip oyuncu simülasyonu (isim/skor/yüzde) için hiçbir alan YOK - "kaç
 * kişi yarışta" gibi görünümler `models/oyun.ts`'teki frontend
 * simülasyonunda kalmaya devam eder. Bu dosya yalnızca kullanıcının KENDİ
 * katılımını/cüzdanını taşıyan gerçek API sözleşmesidir.
 */

import type { LocalizedText } from "./oyun";

export type ContestState = {
  contest_id: number;
  contest_date: string;
  starts_at: string;
  capacity_total: number;
  prize_pool_points: number;
  question_count: number;
  participant_count: number;
  has_agreement: boolean;
  already_participated_today: boolean;
};

export type ContestTopicApi = {
  id: number;
  title: LocalizedText;
  body: LocalizedText;
};

export type ContestQuestionApi = {
  contest_question_id: number;
  sort_order: number;
  text: LocalizedText;
  options: LocalizedText[];
  timer_seconds: number;
  difficulty: string;
};

export type ParticipationStart = {
  participation_id: number;
  questions: ContestQuestionApi[];
};

export type AnswerRequestPayload = {
  contest_question_id: number;
  selected_index: number | null;
  elapsed_seconds: number;
  double_points_active: boolean;
};

export type AnswerResult = {
  is_correct: boolean;
  points_earned: number;
  correct_index: number;
  education_note: LocalizedText;
};

export type FiftyFiftyResult = {
  removed_indices: number[];
};

export type FinishRequest = {
  /** Frontend'in simüle ettiği rakip/kazanan sayısı (100-500) - ödül
   * havuzunu BUNUNLA böleriz, gerçek katılımcı sayısıyla değil (bkz.
   * useQuiz.ts rivalsCurve). Backend 100-500 dışını reddeder. */
  rivals_at_end: number;
};

export type FinishResult = {
  won: boolean;
  final_score: number;
  correct_count: number;
  reached_question: number;
  eliminated_at_question: number | null;
  payout_points: number;
  /** Ödül hesabında bölen olarak KULLANILAN sayı - gönderdiğimiz simüle
   * değerin aynısı geri döner. */
  rivals_at_end: number;
};

export type WalletSummary = {
  points_balance: number;
  powerups: Record<string, number>;
  badges: string[];
};

export type ContestHistoryRowApi = {
  occurred_at: string;
  kind: "contest" | "powerup_purchase" | "donation_purchase";
  points: number;
  won: boolean | null;
  final_score: number | null;
  eliminated_at_question: number | null;
  powerup_kind: string | null;
  donation_key: string | null;
};

export type LeaderboardEntryApi = {
  rank: number;
  label: string;
  score: number;
};
