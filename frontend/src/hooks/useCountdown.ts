"use client";

import { useEffect, useState } from "react";

export type Countdown = {
  /** Kalan toplam saniye */
  total: number;
  hours: string;
  minutes: string;
  seconds: string;
  /** Süre doldu mu */
  done: boolean;
};

/**
 * Verilen ana kadar geri sayar. Hedef geçmişteyse sıfırda kalır.
 * Yarışma günlük olduğu için hedef, `nextContestTime` ile hesaplanır.
 */
export function useCountdown(target: Date | null): Countdown {
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!target) return;

    const tick = () => {
      const diff = Math.floor((target.getTime() - Date.now()) / 1000);
      setTotal(Math.max(0, diff));
    };

    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [target]);

  const pad = (n: number) => String(n).padStart(2, "0");

  return {
    total,
    hours: pad(Math.floor(total / 3600)),
    minutes: pad(Math.floor((total % 3600) / 60)),
    seconds: pad(total % 60),
    done: total === 0,
  };
}

/**
 * Bir sonraki yarışma anı: bugün saat 20.00, geçtiyse yarın 20.00.
 * `playedToday` true ise (yarışma oynandıysa) doğrudan yarına gider —
 * demo modunda saat beklenmeden oynandığı için gerekli.
 */
export function nextContestTime(playedToday = false): Date {
  const t = new Date();
  t.setHours(20, 0, 0, 0);
  if (Date.now() > t.getTime() || playedToday) {
    t.setDate(t.getDate() + 1);
  }
  return t;
}
