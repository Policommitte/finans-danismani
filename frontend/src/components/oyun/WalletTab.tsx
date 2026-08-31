"use client";

import Card from "../ui/Card";
import type { HistoryRow } from "../../models/oyun";
import { useLanguage } from "../../contexts/LanguageContext";

type Props = {
  pointsBalance: number;
  history: HistoryRow[];
  onGoShop: () => void;
};

//: Buyuk "hero" gosterim alani icin vektor tabanli ikon - fotograf DEGIL
//: (bir kez denendi: Pexels sonucu yesil/kahverengi bir stok fotografti,
//: sitenin koyu lacivert temasiyla cakisiyordu). SVG oldugu icin bu boyutta
//: da piksellesme olmaz. Govde/kapak icin --color-market-muted, cıtcıt
//: vurgusu icin --color-primary kullanilir - sayfanin geri kalanindaki
//: ikonlarla (chatbot, market ikonlari) ayni duz-cizgi/stroke dili.
function WalletIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-32 w-32 sm:h-40 sm:w-40"
      fill="none"
      aria-hidden="true"
      style={{ filter: "drop-shadow(0 0 16px rgba(255, 255, 255, 0.15))" }}
    >
      {/* govde + ust kapak kivrimi */}
      <path
        d="M21 12V7H5a2 2 0 0 1 0-4h14v4"
        stroke="var(--color-market-muted)"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M3 5v14a2 2 0 0 0 2 2h16v-5"
        stroke="var(--color-market-muted)"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* cıtcıt / kart yuvası */}
      <path d="M18 12a2 2 0 0 0 0 4h4v-4Z" fill="var(--color-primary)" />
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
              // Bu panel (govde arka plani) HER IKI temada da koyu; `--color-success`
              // aydinlik modda koyu yesile donup koyu zeminde silikleşiyordu.
              // `--color-market-*` ile ayni mantikla sabit acik yesil kullanildi.
              style={{ background: "var(--color-overlay-soft)", color: "#34d399" }}
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
                style={{ color: "var(--color-primary)" }}
              >
                {pointsBalance.toLocaleString(locale)}
              </span>
              <span className="text-sm" style={{ color: "var(--color-market-muted)" }}>
                {language === "tr" ? "bonus puan" : "bonus points"}
              </span>
            </div>

            <p className="mt-2 flex flex-wrap items-center gap-2 text-xs" style={{ color: "var(--color-market-muted)" }}>
              <span style={{ color: "#34d399" }}>▲ +{monthlyGain}</span>
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
