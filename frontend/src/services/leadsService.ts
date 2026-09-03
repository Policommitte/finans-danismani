import type { CallOutcomeInput, LeadQueueResponse, LeadScanSummary } from "../models/leads";
import { apiRequest } from "./apiClient";

export function getBsdQueue(): Promise<LeadQueueResponse> {
  return apiRequest<LeadQueueResponse>("/api/leads/bsd-queue");
}

export function getAutonomousQueue(): Promise<LeadQueueResponse> {
  return apiRequest<LeadQueueResponse>("/api/leads/autonomous-queue");
}

export function getExcludedLeads(): Promise<LeadQueueResponse> {
  return apiRequest<LeadQueueResponse>("/api/leads/excluded");
}

export function runLeadScan(force = true): Promise<LeadScanSummary> {
  return apiRequest<LeadScanSummary>("/api/leads/scan", {
    method: "POST",
    body: JSON.stringify({ force }),
  });
}

/**
 * Danismanin gorusme sonucunu isaretler. Uc 204 (govdesiz) doner;
 * `apiRequest` bunu `undefined` olarak gecer.
 *
 * `outcome: "ACIK"` isaretlemeyi temizler - kayit silinmez, ustune yeni
 * bir satir yazilir (backend tarafi ekleme-only).
 */
export function setLeadOutcome(
  userId: number,
  outcome: CallOutcomeInput,
  note: string | null = null,
): Promise<void> {
  return apiRequest<void>(`/api/leads/${userId}/outcome`, {
    method: "POST",
    body: JSON.stringify({ outcome, note }),
  });
}