"use client";

import { useCallback, useState } from "react";
import type { CallOutcomeInput } from "../models/leads";
import {
  getAutonomousQueue,
  getBsdQueue,
  getExcludedLeads,
  runLeadScan,
  setLeadOutcome,
} from "../services/leadsService";
import { useAsyncData } from "./useAsyncData";

export function useLeads() {
  const [scanning, setScanning] = useState(false);
  const [kaydedilenId, setKaydedilenId] = useState<number | null>(null);

  const loader = useCallback(async () => {
    const [bsd, autonomous, excluded] = await Promise.all([
      getBsdQueue(),
      getAutonomousQueue(),
      getExcludedLeads(),
    ]);
    return { bsd, autonomous, excluded };
  }, []);

  const state = useAsyncData(loader, [loader]);

  async function runScan() {
    setScanning(true);
    try {
      await runLeadScan(true);
      await state.refresh();
    } finally {
      setScanning(false);
    }
  }

  /**
   * Gorusme sonucunu isaretler ve listeyi tazeler.
   *
   * Iyimser guncelleme YAPILMAZ: bir tik sonra gelen `refresh` zaten
   * sunucunun gercek halini getiriyor ve satir sayisi/filtre sayaclari
   * da onunla tutarli kaliyor.
   */
  async function sonucKaydet(userId: number, outcome: CallOutcomeInput) {
    setKaydedilenId(userId);
    try {
      await setLeadOutcome(userId, outcome);
      await state.refresh();
    } finally {
      setKaydedilenId(null);
    }
  }

  return { ...state, scanning, runScan, sonucKaydet, kaydedilenId };
}