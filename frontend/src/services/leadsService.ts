import type { LeadQueueResponse, LeadScanSummary } from "../models/leads";
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