"use client";

import { useEffect, useMemo, useState } from "react";
import Card from "../ui/Card";
import { Mascot } from "./Mascot";
import {
  CONFIG,
  buildWinnerStats,
  makeReferralCode,
  type GameResult,
} from "../../models/oyun";

type Props = {
  result: GameResult;
  /** Puanlar sekmesine git */
  onGoPoints: () => void;
};

/** Ödül tutarını sayarak artırır */
function useCountUp(target: number, ms = 1200) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const id = setInterval(() => {
      const t = Math.min(1, (Date.now() - start) / ms);
      // ease-out
      setValue(Math.round(target * (1 - Math.pow(1 - t, 3))));
      if (t >= 1) clearInterval(id);
    }, 40);
    return () => clearInterval(id);
  }, [target, ms]);

  return value;
}

export function WinnerScreen({ result, onGoPoints }: Props) {
  // Tabloyu bir kez üret, her render'da değişmesin
  const stats = useMemo(() => buildWinnerStats(result.score), [result.score]);
  const code = useMemo(() => makeReferralCode(), []);
  const payout = useCountUp(stats.myPayout);
  const [copied, setCopied] = useState(false);

  const shareText = `Şans Yatırımda'da ${CONFIG.questionCount} sorunun hepsini bildim ve ${stats.myPayout.toLocaleString("tr-TR")} bonus puan kazandım. Davet kodum: ${code}`;
  const shareUrl = "https://polifin.local/yatirim-oyunu";

  const invites = [
    {
      label: "WhatsApp",
      href: `https://wa.me/?text=${encodeURIComponent(`${shareText} ${shareUrl}`)}`,
    },
    {
      label: "X",
      href: `https://x.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`,
    },
    {
      label: "E-posta",
      href: `mailto:?subject=${encodeURIComponent("Şans Yatırımda'ya davetlisin")}&body=${encodeURIComponent(`${shareText}\n\n${shareUrl}`)}`,
    },
  ];

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Paylaşım kartı — ekran görüntüsü alınmak üzere tasarlandı */}
      <Card>
        <div
          className="flex flex-col items-center gap-4 rounded-xl px-6 py-8 text-center"
          style={{ background: "var(--color-panel-dark)", color: "var(--color-on-primary)" }}
        >
                   <Mascot mood="happy" message="Tebrikler, hepsini bildin!" />
          <p className="text-xs uppercase tracking-[0.2em] opacity-80">Şans Yatırımda</p>
          <p className="text-2xl font-semibold">Tüm soruları bildin</p>

          <div>
            <p className="text-5xl font-semibold tabular-nums" style={{ color: "var(--color-cta)" }}>
              {payout.toLocaleString("tr-TR")}
            </p>
            <p className="mt-1 text-sm opacity-80">bonus puan kazandın</p>
          </div>

          <div className="grid w-full max-w-sm grid-cols-3 gap-2 text-sm">
            <div>
              <p className="text-lg font-semibold tabular-nums">
                {result.score.toLocaleString("tr-TR")}
              </p>
                        <p className="text-[11px] opacity-70">Skorun</p>
            </div>
            <div>
                    <p className="text-lg font-semibold tabular-nums">{stats.winners}</p>
              <p className="text-[11px] opacity-70">Kazanan</p>
            </div>
            <div>
              <p className="text-lg font-semibold tabular-nums">{stats.myRank}.</p>
              <p className="text-[11px] opacity-70">Sıran</p>
            </div>
          </div>
        </div>
      </Card>

      <Card title="Ödül dağılımı">
        <p className="app-muted mb-3 text-sm">
          {CONFIG.prizePool.toLocaleString("tr-TR")} puanlık havuz, kazananlar arasında skor payı
          oranında bölüşüldü. Sıralama anonimdir.
        </p>

        <ul className="space-y-2">
          {stats.board.map((row, i) => (
            <li
              key={`${row.label}-${i}`}
              className="flex items-center justify-between rounded-lg border px-4 py-3"
              style={{
                borderColor: row.isMe ? "var(--color-primary)" : "var(--color-border)",
                background: row.isMe ? "var(--color-primary-soft)" : "transparent",
              }}
            >
              <span className="flex items-center gap-3 text-sm font-semibold">
                <span className="app-muted tabular-nums">{i + 1}.</span>
                {row.label}
              </span>
              <span className="flex items-center gap-4 text-sm tabular-nums">
                <span className="app-muted">{row.score.toLocaleString("tr-TR")} skor</span>
                <span className="font-semibold" style={{ color: "var(--color-success)" }}>
                  +{row.payout.toLocaleString("tr-TR")}
                </span>
              </span>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="Arkadaşını davet et">
        <div className="space-y-3">
          <p className="app-muted text-sm">
            Davet ettiğin her arkadaşın ilk yarışmasına katıldığında hesabına 500 bonus puan yüklenir.
          </p>

          <div className="flex flex-wrap items-center gap-2">
            <code
              className="rounded-lg px-4 py-2 text-sm font-semibold tracking-widest"
              style={{ background: "var(--color-surface-muted)" }}
            >
              {code}
            </code>
                  <button
              onClick={copyCode}
              className="rounded-lg border px-3 py-2 text-xs font-semibold transition"
                    style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
            >
              {copied ? "Kopyalandı" : "Kodu kopyala"}
            </button>
          </div>

          <div className="flex flex-wrap gap-2">
            {invites.map((s) => (
              <a
                key={s.label}
                href={s.href}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg px-4 py-2 text-sm font-semibold transition"
                style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}
              >
                {s.label} ile paylaş
              </a>
            ))}
          </div>
        </div>
      </Card>

            <div className="flex justify-center">
        <button
           onClick={onGoPoints}
              className="rounded-lg px-5 py-2.5 text-sm font-semibold transition"
          style={{ background: "var(--color-cta)", color: "var(--color-on-primary)" }}
        >
          Puanlarımı gör
        </button>
      </div>
    </div>
  );
}
