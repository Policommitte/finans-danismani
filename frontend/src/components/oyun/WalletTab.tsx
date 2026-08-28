"use client";

import Card from "../ui/Card";
import type { HistoryRow } from "../../models/oyun";
import { useLanguage } from "../../contexts/LanguageContext";

type Props = {
  pointsBalance: number;
  history: HistoryRow[];
  onGoShop: () => void;
};

function WalletIcon() {
  return (
    <svg
      viewBox="0 0 96 80"
      className="h-32 w-40 sm:h-40 sm:w-48"
      aria-hidden="true"
      style={{ filter: "drop-shadow(0 0 16px rgba(255, 255, 255, 0.15))" }}
    >
      <path
        d="M12 16V10a6 6 0 0 1 6-6h52a6 6 0 0 1 6 6v6"
        fill="none"
        stroke="var(--color-market-muted)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <rect
        x="4"
        y="16"
        width="88"
        height="56"
        rx="10"
        fill="none"
        stroke="var(--color-market-muted)"
        strokeWidth="4"
      />
      <circle cx="70" cy="48" r="4.5" fill="var(--color-cta)" />
    </svg>
  );
}

export function WalletTab({ pointsBalance, history, onGoShop }: Props) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const participation = history.length;
  const wins = history.filter((row) => row.result === "win").length;
  const successRate = participation > 0 ? Math.round((wins / participation) * 100) : 0;
  const bestScore = participation > 0 ? Math.max(...history.map((row) => row.score)) : 0;
  const monthlyGain = history.reduce((sum, row) => sum + row.points, 0);
  const lastActivity = history[0]?.date[language] ?? "—";

  const stats = [
    { label: language === "tr" ? "Katılım" : "Entries", value: String(participation) },
    { label: language === "tr" ? "Kazanma" : "Wins", value: String(wins) },
    { label: language === "tr" ? "Başarı" : "Success rate", value: `%${successRate}` },
    { label: language === "tr" ? "En yüksek skor" : "Best score", value: bestScore.toLocaleString(locale) },
  ];

  return (
    <div className="space-y-4">
            <div
        className="overflow-hidden rounded-2xl"
        style={{ background: "color-mix(in srgb, var(--color-panel-dark) 95%, white)" }}
      >
        <div className="flex flex-col items-center gap-8 p-6 sm:flex-row sm:items-center sm:gap-10 sm:p-10">
          {/* sol: dev cüzdan ikonu, alanın yarısını kaplıyor */}
          <div className="flex w-full flex-col items-center gap-3 sm:w-1/2">
            <WalletIcon />
            <p className="text-sm font-semibold" style={{ color: "var(--color-market-text)" }}>
              {language === "tr" ? "Bonus puan cüzdanı" : "Bonus points wallet"}
            </p>
          </div>

          {/* sağ: bakiye + istatistikler */}
          <div className="w-full sm:w-1/2">
            <span
              className="inline-block rounded-full px-3 py-1 text-[11px] font-semibold"
              style={{ background: "var(--color-overlay-soft)", color: "var(--color-success)" }}
            >
              {language === "tr" ? "Şans Yatırımda · Aktif" : "Şans Yatırımda · Active"}
            </span>

            <p
              className="mt-4 text-xs uppercase tracking-wide"
              style={{ color: "var(--color-market-muted)" }}
            >
              {language === "tr" ? "Kullanılabilir bakiye" : "Available balance"}
            </p>
            <div className="flex items-baseline gap-2">
              <span
                className="text-5xl font-bold tabular-nums"
                style={{ color: "var(--color-cta)" }}
              >
                {pointsBalance.toLocaleString(locale)}
              </span>
              <span className="text-sm" style={{ color: "var(--color-market-muted)" }}>
                {language === "tr" ? "bonus puan" : "bonus points"}
              </span>
            </div>

            <p className="mt-2 flex flex-wrap items-center gap-2 text-xs" style={{ color: "var(--color-market-muted)" }}>
              <span style={{ color: "var(--color-success)" }}>▲ +{monthlyGain}</span>
              <span>{language === "tr" ? "toplam kazanç" : "total earned"}</span>
              <span>·</span>
              <span>{language === "tr" ? "Son işlem" : "Last activity"} {lastActivity}</span>
            </p>

            <div
              className="mt-5 grid grid-cols-2 gap-4 border-t pt-5 sm:grid-cols-4"
              style={{ borderColor: "var(--color-overlay-soft)" }}
            >
              {stats.map((s) => (
                <div key={s.label}>
                  <p className="text-xs" style={{ color: "var(--color-market-muted)" }}>
                    {s.label}
                  </p>
                  <p
                    className="mt-1 text-xl font-bold tabular-nums"
                    style={{ color: "var(--color-market-text)" }}
                  >
                    {s.value}
                  </p>
                </div>
              ))}
            </div>

            <button
              onClick={onGoShop}
              className="mt-6 rounded-lg px-5 py-2.5 text-sm font-semibold transition"
              style={{ background: "var(--color-surface)", color: "var(--color-heading)" }}
            >
              {language === "tr" ? "Puan harca" : "Spend points"}
            </button>
          </div>
        </div>
      </div>

      <Card title={language === "tr" ? "Puan geçmişi" : "Points history"}>
        {history.length === 0 ? (
          <p className="app-muted text-sm">
            {language === "tr" ? "Henüz bir yarışmaya katılmadınız." : "You haven't joined a contest yet."}
          </p>
        ) : (
          <div className="space-y-2">
            {history.map((row, i) => (
              <div
                key={`${row.date.tr}-${i}`}
                className="flex items-center justify-between rounded-lg px-4 py-3"
                style={{ background: "var(--color-surface-muted)" }}
              >
                <div>
                  <p className="app-heading text-sm font-semibold">{row.date[language]}</p>
                  <p
                    className="text-xs"
                    style={{
                      color:
                        row.result === "win" ? "var(--color-success)" : "var(--color-muted)",
                    }}
                  >
                    {row.detail[language]}
                  </p>
                </div>
                <div className="text-right">
                  <p className="app-muted text-xs tabular-nums">
                    {language === "tr" ? "Skor" : "Score"} {row.score}
                  </p>
                  <p
                    className="text-sm font-bold tabular-nums"
                    style={{
                      color: row.points > 0 ? "var(--color-success)" : "var(--color-muted)",
                    }}
                  >
                    {row.points > 0 ? `+${row.points}` : "—"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
