"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type SoundKind =
  | "register"
  | "tick"
  | "correct"
  | "wrong"
  | "timeout"
  | "win"
  | "powerup"
  | "purchase";

type Note = {
  freq: number;
  start: number;
  duration: number;
  type?: OscillatorType;
  gain?: number;
};

const PATTERNS: Record<SoundKind, Note[]> = {
  register: [{ freq: 660, start: 0, duration: 0.08, gain: 0.15 }],
  tick: [{ freq: 900, start: 0, duration: 0.04, gain: 0.08, type: "square" }],
  correct: [
    { freq: 523.25, start: 0, duration: 0.09, gain: 0.18 },
    { freq: 783.99, start: 0.09, duration: 0.14, gain: 0.18 },
  ],
  wrong: [{ freq: 160, start: 0, duration: 0.22, gain: 0.2, type: "sawtooth" }],
  timeout: [
    { freq: 300, start: 0, duration: 0.1, gain: 0.16, type: "triangle" },
    { freq: 180, start: 0.1, duration: 0.16, gain: 0.16, type: "triangle" },
  ],
  win: [
    { freq: 523.25, start: 0, duration: 0.1, gain: 0.2 },
    { freq: 659.25, start: 0.1, duration: 0.1, gain: 0.2 },
    { freq: 783.99, start: 0.2, duration: 0.22, gain: 0.22 },
  ],
  powerup: [
    { freq: 880, start: 0, duration: 0.06, gain: 0.14 },
    { freq: 1320, start: 0.06, duration: 0.08, gain: 0.14 },
  ],
  purchase: [
    { freq: 988, start: 0, duration: 0.06, gain: 0.16 },
    { freq: 1318.5, start: 0.05, duration: 0.1, gain: 0.16 },
  ],
};

const STORAGE_KEY = "sy-muted";

export function useSoundEffects() {
  const [muted, setMuted] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "1") setMuted(true);
  }, []);

  function ensureContext(): AudioContext | null {
    if (typeof window === "undefined") return null;
    if (!ctxRef.current) {
      const Ctor = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) return null;
      ctxRef.current = new Ctor();
    }
    if (ctxRef.current.state === "suspended") {
      ctxRef.current.resume().catch(() => {});
    }
    return ctxRef.current;
  }

  const play = useCallback(
    (kind: SoundKind) => {
      if (muted) return;
      const ctx = ensureContext();
      if (!ctx) return;

      for (const note of PATTERNS[kind]) {
        const osc = ctx.createOscillator();
        const gainNode = ctx.createGain();
        osc.type = note.type ?? "sine";
        osc.frequency.value = note.freq;

        const startTime = ctx.currentTime + note.start;
        const endTime = startTime + note.duration;
        const peakGain = note.gain ?? 0.15;

        gainNode.gain.setValueAtTime(0, startTime);
        gainNode.gain.linearRampToValueAtTime(peakGain, startTime + 0.01);
        gainNode.gain.exponentialRampToValueAtTime(0.001, endTime);

        osc.connect(gainNode);
        gainNode.connect(ctx.destination);

        osc.start(startTime);
        osc.stop(endTime + 0.02);
      }
    },
    [muted]
  );

  const toggleMute = useCallback(() => {
    setMuted((m) => {
      const next = !m;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      }
      return next;
    });
  }, []);

  return { play, muted, toggleMute };
}