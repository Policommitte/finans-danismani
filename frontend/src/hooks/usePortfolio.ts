"use client";

import { useCallback, useEffect } from "react";
import type {
  PerformanceRange,
  PortfolioSnapshotPerformanceResponse,
} from "../models/portfolio";
import {
  getPortfolioPerformance,
  getPortfolioSnapshotPerformance,
  getPortfolioTransactions,
} from "../services/portfolioService";
import { useAsyncData } from "./useAsyncData";

export function usePortfolioTransactions(limit = 20) {
  const loader = useCallback(() => getPortfolioTransactions(limit), [limit]);
  return useAsyncData(loader, [loader]);
}

/**
 * Secilen donemin deger serisi + donem kar/zarari.
 *
 * HER donemde cekilir, 1G dahil: "Donem Degisimi" karti ve varlik
 * tablosunun kar/zarar sutunu yalnizca buradan besleniyor - snapshot
 * ucunda varlik bazinda kar/zarar yok.
 */
export function usePortfolioPerformance(range: PerformanceRange = "1G") {
  const loader = useCallback(() => getPortfolioPerformance(range), [range]);
  const performance = useAsyncData(loader, [loader], `portfolio:performance:${range}`);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void performance.refresh();
    }, 60_000);

    return () => window.clearInterval(timer);
  }, [performance.refresh]);

  return performance;
}

//: `enabled=false` iken ag istegi atilmaz; bos yanit hook'un sozlesmesini
//: bozmadan "veri yok" demenin en sade yolu.
const EMPTY_SNAPSHOT: PortfolioSnapshotPerformanceResponse = {
  points: [],
  hours: 24,
  interval_minutes: 5,
};

/**
 * Scheduler'in 5 dakikada bir OLCTUGU portfoy toplamlari.
 *
 * Yeniden hesaplanan seriden daha dogrudur (nakit dahil, emirler
 * islendikten sonra alinir), ama YALNIZCA gun ici icin kullanilabilir:
 * tablo 30 gunluk kayan pencerede tutuluyor ve uc nokta 720 saatle sinirli.
 * Bu yuzden 1H/1A/1Y'de `enabled=false` gecilir ve grafik yeniden kurulan
 * seriye duser.
 */
export function usePortfolioSnapshots(enabled: boolean, hours = 24) {
  const loader = useCallback(
    () => (enabled ? getPortfolioSnapshotPerformance(hours) : Promise.resolve(EMPTY_SNAPSHOT)),
    [enabled, hours],
  );
  const snapshots = useAsyncData(
    loader,
    [loader],
    enabled ? `portfolio:snapshots:${hours}` : undefined,
  );

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const timer = window.setInterval(() => {
      void snapshots.refresh();
    }, 60_000);

    return () => window.clearInterval(timer);
  }, [enabled, snapshots.refresh]);

  return snapshots;
}
