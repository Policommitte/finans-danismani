import type {
  AutonomousSettings,
  Recommendation,
  RecommendationListResponse,
  RejectionReason,
} from "../models/recommendation";
import type { IdleCashBasketCatalog, IdleCashSuggestion } from "../models/chat";
import { apiRequest } from "./apiClient";

export function getRecommendations(status?: string): Promise<RecommendationListResponse> {
  const query = status ? `?durum=${encodeURIComponent(status)}` : "";
  return apiRequest<RecommendationListResponse>(`/api/oneriler${query}`);
}

/** Karti acmak sunucuda durumu Goruntulendi'ye gecirir (D-07). */
export function openRecommendation(id: number): Promise<Recommendation> {
  return apiRequest<Recommendation>(`/api/oneriler/${id}`);
}

export function rejectRecommendation(
  id: number,
  reason: RejectionReason,
): Promise<Recommendation> {
  return apiRequest<Recommendation>(`/api/oneriler/${id}/ret`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function approveRecommendation(id: number, quantity: number | null) {
  return apiRequest<{ recommendation: Recommendation; order: { id: number } }>(
    `/api/oneriler/${id}/onayla`,
    { method: "POST", body: JSON.stringify({ quantity }) },
  );
}

export function getAutonomousSettings(): Promise<AutonomousSettings> {
  return apiRequest<AutonomousSettings>("/api/oneriler/ayarlar");
}

export function updateAutonomousSettings(
  settings: AutonomousSettings,
): Promise<AutonomousSettings> {
  return apiRequest<AutonomousSettings>("/api/oneriler/ayarlar", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

export function getIdleCashSuggestion(
  goal: IdleCashSuggestion["goal"],
): Promise<IdleCashSuggestion> {
  return apiRequest<IdleCashSuggestion>("/api/oneriler/sepet", {
    method: "POST",
    body: JSON.stringify({ goal }),
  });
}

export function getIdleCashBasketCatalog(
  goal: IdleCashSuggestion["goal"],
): Promise<IdleCashBasketCatalog> {
  return apiRequest<IdleCashBasketCatalog>("/api/oneriler/sepetler", {
    method: "POST",
    body: JSON.stringify({ goal }),
  });
}
