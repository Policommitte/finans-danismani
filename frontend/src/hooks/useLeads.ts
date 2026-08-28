"use client";

import { useCallback, useState } from "react";
import { getAutonomousQueue, getBsdQueue, getExcludedLeads, runLeadScan } from "../services/leadsService";
import { useAsyncData } from "./useAsyncData";

export function useLeads() {
  const [scanning, setScanning] = useState(false);

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

  return { ...state, scanning, runScan };
}