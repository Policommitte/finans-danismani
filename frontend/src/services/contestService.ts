import type {
  AnswerRequestPayload,
  AnswerResult,
  ContestHistoryRowApi,
  ContestQuestionApi,
  ContestState,
  ContestTopicApi,
  FiftyFiftyResult,
  FinishRequest,
  FinishResult,
  LeaderboardEntryApi,
  ParticipationStart,
  WalletSummary,
} from "../models/contestApi";
import { apiRequest } from "./apiClient";

export function getContestState(): Promise<ContestState> {
  return apiRequest<ContestState>("/api/contest/today");
}

export function acceptContestAgreement(): Promise<void> {
  return apiRequest<void>("/api/contest/agreement", { method: "POST" });
}

/** DEMO/GELİŞTİRME için: bugünkü katılımı siler, günlük hak yeniden
 * kullanılabilir olur. Backend üretimde bunu 422 ile reddeder. */
export function resetContestToday(): Promise<void> {
  return apiRequest<void>("/api/contest/reset", { method: "POST" });
}

export function getContestTopics(contestId: number): Promise<ContestTopicApi[]> {
  return apiRequest<ContestTopicApi[]>(`/api/contest/${contestId}/topics`);
}

export function startParticipation(): Promise<ParticipationStart> {
  return apiRequest<ParticipationStart>("/api/contest/participations", { method: "POST" });
}

export function submitContestAnswer(
  participationId: number,
  payload: AnswerRequestPayload
): Promise<AnswerResult> {
  return apiRequest<AnswerResult>(`/api/contest/participations/${participationId}/answers`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fiftyFiftyContest(
  participationId: number,
  contestQuestionId: number
): Promise<FiftyFiftyResult> {
  return apiRequest<FiftyFiftyResult>(
    `/api/contest/participations/${participationId}/questions/${contestQuestionId}/fifty-fifty`,
    { method: "POST" }
  );
}

export function finishParticipation(
  participationId: number,
  payload: FinishRequest
): Promise<FinishResult> {
  return apiRequest<FinishResult>(`/api/contest/participations/${participationId}/finish`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getWallet(): Promise<WalletSummary> {
  return apiRequest<WalletSummary>("/api/contest/wallet");
}

export function getWalletHistory(limit = 20): Promise<ContestHistoryRowApi[]> {
  return apiRequest<ContestHistoryRowApi[]>(`/api/contest/wallet/history?limit=${limit}`);
}

export function buyPowerupApi(kind: string): Promise<WalletSummary> {
  return apiRequest<WalletSummary>("/api/contest/shop/powerup", {
    method: "POST",
    body: JSON.stringify({ kind }),
  });
}

/** Bir joker yarışma İÇİNDE kullanıldığında çağrılır (satın alma değil) -
 * envanteri gerçekten düşürür ki sayfa yenilense kullanılan joker geri gelmesin. */
export function consumePowerupApi(kind: string): Promise<WalletSummary> {
  return apiRequest<WalletSummary>(`/api/contest/powerups/${kind}/consume`, {
    method: "POST",
  });
}

export function buyDonationApi(donationKey: string): Promise<WalletSummary> {
  return apiRequest<WalletSummary>("/api/contest/shop/donation", {
    method: "POST",
    body: JSON.stringify({ donation_key: donationKey }),
  });
}

export function getContestLeaderboard(
  period: "gunluk" | "haftalik" | "tumzamanlar" = "tumzamanlar"
): Promise<LeaderboardEntryApi[]> {
  return apiRequest<LeaderboardEntryApi[]>(`/api/contest/leaderboard?period=${period}`);
}
