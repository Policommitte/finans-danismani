"use client";

import { useCallback, useState } from "react";

/** Oyunun geçtiği ekranlar */
export type GameScreen =
  | "register" // kayıt / geri sayım
  | "waiting" // kayıt alındı, yarışma bekleniyor
  | "cheatsheet" // 5 dakikalık çalışma notu
  | "quiz" // soru akışı
  | "eliminated" // elendi
  | "victory" // kazandı
  | "closed"; // kontenjan dolu / kayıt kapalı

/** Sayfanın üst sekmeleri */
export type GameTab = "oyun" | "kampanyalar" | "puanlar";

export function useGameFlow() {
  const [tab, setTab] = useState<GameTab>("oyun");
  const [screen, setScreen] = useState<GameScreen>("register");

  /** Yarışma sırasında yan kolonlar gizlenir */
  const isFocused = screen === "quiz";

  const goTab = useCallback((next: GameTab) => {
    setTab(next);
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, []);

  const goScreen = useCallback((next: GameScreen) => {
    setScreen(next);
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, []);

  return { tab, goTab, screen, goScreen, isFocused };
}
