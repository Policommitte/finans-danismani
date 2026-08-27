"use client";

import { useCallback, useState } from "react";
import type { Recommendation, RejectionReason } from "../models/recommendation";
import {
  approveRecommendation,
  getRecommendations,
  openRecommendation,
  rejectRecommendation,
} from "../services/recommendationService";
import { useAsyncData } from "./useAsyncData";

export function useRecommendations() {
  const loader = useCallback(() => getRecommendations(), []);
  const state = useAsyncData(loader, [loader]);
  const [selected, setSelected] = useState<Recommendation | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const open = useCallback(async (id: number) => {
    setActionError(null);
    setNotice(null);
    try {
      // Sunucu bu cagriyla durumu Goruntulendi'ye cevirir; liste de tazelenir.
      const detail = await openRecommendation(id);
      setSelected(detail);
      await state.refresh();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Öneri açılamadı.");
    }
  }, [state.refresh]);

  const reject = useCallback(async (id: number, reason: RejectionReason) => {
    setSubmitting(true);
    setActionError(null);
    try {
      await rejectRecommendation(id, reason);
      setNotice("Öneri reddedildi. Gerekçen sonraki önerilerde dikkate alınacak.");
      setSelected(null);
      await state.refresh();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Öneri reddedilemedi.");
    } finally {
      setSubmitting(false);
    }
  }, [state.refresh]);

  const approve = useCallback(async (id: number, quantity: number | null) => {
    setSubmitting(true);
    setActionError(null);
    try {
      await approveRecommendation(id, quantity);
      setNotice("Emir oluşturuldu; bir sonraki doğrulanmış fiyatta değerlendirilecek.");
      setSelected(null);
      await state.refresh();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Emir oluşturulamadı.");
    } finally {
      setSubmitting(false);
    }
  }, [state.refresh]);

  return {
    ...state,
    selected,
    setSelected,
    submitting,
    actionError,
    notice,
    open,
    reject,
    approve,
  };
}
