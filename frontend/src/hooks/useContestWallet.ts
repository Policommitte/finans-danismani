"use client";

import { useCallback, useState } from "react";
import { apiHistoryRowToDisplay, type HistoryRow } from "../models/oyun";
import { buyDonationApi, buyPowerupApi, getWallet, getWalletHistory } from "../services/contestService";
import { useAsyncData } from "./useAsyncData";

export type WalletData = {
  pointsBalance: number;
  powerups: Record<string, number>;
  badges: string[];
  history: HistoryRow[];
};

async function loadWallet(): Promise<WalletData> {
  const [wallet, historyRows] = await Promise.all([getWallet(), getWalletHistory(20)]);
  return {
    pointsBalance: wallet.points_balance,
    powerups: wallet.powerups,
    badges: wallet.badges,
    history: historyRows.map(apiHistoryRowToDisplay),
  };
}

/** Cüzdan bakiyesi + puan geçmişi + mağaza satın alma eylemleri - TEK gerçek
 * kaynak backend'dir. Satın alma sonrası `refresh()` ile bakiye tazelenir. */
export function useContestWallet() {
  const { data, loading, error, refresh } = useAsyncData(loadWallet, []);
  const [actionError, setActionError] = useState<string | null>(null);

  const buyPowerup = useCallback(
    async (kind: string): Promise<boolean> => {
      setActionError(null);
      try {
        await buyPowerupApi(kind);
        await refresh();
        return true;
      } catch (exc) {
        setActionError(exc instanceof Error ? exc.message : "Satın alma başarısız oldu.");
        return false;
      }
    },
    [refresh]
  );

  const buyDonation = useCallback(
    async (donationKey: string): Promise<boolean> => {
      setActionError(null);
      try {
        await buyDonationApi(donationKey);
        await refresh();
        return true;
      } catch (exc) {
        setActionError(exc instanceof Error ? exc.message : "Bağış başarısız oldu.");
        return false;
      }
    },
    [refresh]
  );

  return {
    pointsBalance: data?.pointsBalance ?? 0,
    powerups: data?.powerups ?? {},
    badges: data?.badges ?? [],
    history: data?.history ?? [],
    loading,
    error,
    actionError,
    refresh,
    buyPowerup,
    buyDonation,
  };
}
