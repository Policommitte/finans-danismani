"use client";

import { getRiskProfile } from "../services/riskService";
import { useAsyncData } from "./useAsyncData";

export function useRisk() {
  return useAsyncData(getRiskProfile, []);
}
