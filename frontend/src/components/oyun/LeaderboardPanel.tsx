"use client";

import { useEffect, useState } from "react";
import Card from "../ui/Card";
import {
  buildLeaderboard,
  WEEKLY_PRIZES,
  type LeaderboardPeriod,
} from "../../models/oyun";
import { useLanguage } from "../../contexts/LanguageContext";

const PERIODS: { id: LeaderboardPeriod; label: { tr: string; en: string } }[] = [
  { id: "gunluk", label: { tr: "Günlük", en: "Daily" } },
  { id: "haftalik", label: { tr: "Haftalık", en: "Weekly" } },
  { id: "tumzamanlar", label: { tr: "Tüm Zamanlar", en: "All Time" } },
];

const PODIUM_ORDER = [2, 1, 3] as const; // görsel sıra: 2. sol, 1. orta, 3. sağ
const PODIUM_HEIGHT: Record<number, string> = { 1: "76px", 2: "56px", 3: "44px" };
const PODIUM_MEDAL: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };

type Props = {
  /** Kullanıcının kendi skoru — sıralamada değilse "katıl" mesajı gösterilir */
  myScore?: number | null;
};

 export function LeaderboardPanel({ myScore = null }: Props) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const [period, setPeriod] = useState<LeaderboardPeriod>("gunluk");
  const [entries, setEntries] = useState<ReturnType<typeof buildLeaderboard>>([]);

  useEffect(() => {
    setEntries(buildLeaderboard(period, language));
  }, [period, language]);

  const podium = entries.slice(0, 3);
  const rest = entries.slice(3);
  const myRank = myScore != null ? entries.findIndex((e) => myScore > e.score) + 1 : null;

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex gap-1.5" role="tablist">
          {PERIODS.map((p) => {
            const active = period === p.id;
            return (
              <button
                key={p.id}
                role="tab"
                aria-selected={active}
                onClick={() => setPeriod(p.id)}
                className="flex-1 rounded-lg px-2 py-1.5 text-[11px] font-semibold transition"
                style={
                  active
                    ? { background: "var(--color-primary)", color: "var(--color-on-primary)" }
                    : { background: "var(--color-surface-muted)", color: "var(--color-muted)" }
                }
              >
                {p.label[language]}
              </button>
            );
          })}
        </div>

        {/* podyum */}
        <div className="mt-4 flex items-end justify-center gap-2">
          {PODIUM_ORDER.map((place) => {
            const entry = podium[place - 1];
            if (!entry) return null;
            return (
              <div key={place} className="flex flex-1 flex-col items-center">
                <span className="text-lg">{PODIUM_MEDAL[place]}</span>
                <span
                  className="app-heading mt-1 max-w-full truncate text-[11px] font-semibold"
                  title={entry.label}
                >
                  {entry.label}
                </span>
                <span className="app-muted text-[10px] tabular-nums">
                  {entry.score.toLocaleString(locale)}
                </span>
                                <div
                  className="mt-1.5 w-full rounded-t-lg"
                  style={{
                    height: PODIUM_HEIGHT[place],
                    background:
                      place === 1
                        ? "var(--color-cta)"
                        : place === 2
                          ? "color-mix(in srgb, var(--color-muted) 55%, silver)"
                          : "color-mix(in srgb, var(--color-cta) 55%, #7c4a1e)",
                  }}
                />
              </div>
            );
          })}
        </div>

        {/* 4-6. sıralar */}
        {rest.length > 0 && (
          <div className="mt-4 space-y-1.5">
            {rest.map((entry) => (
              <div
                key={entry.rank}
                className="flex items-center justify-between rounded-lg px-3 py-2 text-xs"
                style={{ background: "var(--color-surface-muted)" }}
              >
                <span className="app-muted flex items-center gap-2">
                  <b className="app-heading tabular-nums">{entry.rank}.</b>
                  {entry.label}
                </span>
                <span className="app-heading font-semibold tabular-nums">
                  {entry.score.toLocaleString(locale)}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* kullanıcının kendi satırı */}
        <div
          className="mt-4 rounded-lg border px-3 py-2.5 text-center text-xs"
          style={{
            borderColor: "var(--color-primary)",
            background: "var(--color-primary-soft)",
            color: "var(--color-primary-soft-text)",
          }}
        >
          {myScore != null && myRank ? (
            <span className="font-semibold">
              {language === "tr" ? "Sıralaman" : "Your rank"}: <b className="tabular-nums">{myRank}.</b> ·{" "}
              <b className="tabular-nums">{myScore.toLocaleString(locale)}</b>{" "}
              {language === "tr" ? "puan" : "points"}
            </span>
          ) : (
            <span className="font-semibold">
              {language === "tr" ? "Sıralamaya girmek için oyuna katıl!" : "Join the game to enter the ranking!"}
            </span>
          )}
        </div>
      </Card>

      <Card title={language === "tr" ? "Haftanın büyük ödülleri" : "This week's big prizes"}>
        <div className="space-y-2.5">
          {WEEKLY_PRIZES.map((prize) => (
            <div
              key={prize.place}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5"
              style={{ background: "var(--color-surface-muted)" }}
            >
              <span className="text-lg">{prize.badge}</span>
              <div className="min-w-0 flex-1">
                <p className="app-heading truncate text-xs font-semibold">{prize.title[language]}</p>
                <p className="app-muted text-[11px] tabular-nums">
                  +{prize.points.toLocaleString(locale)} {language === "tr" ? "bonus puan" : "bonus points"}
                </p>
              </div>
            </div>
          ))}
        </div>
        <p className="app-muted mt-3 text-center text-[11px]">
          {language === "tr" ? "Sıralama pazar 23.59'da kapanır" : "Rankings close Sunday at 11:59 PM"}
        </p>
      </Card>
    </div>
  );
}
