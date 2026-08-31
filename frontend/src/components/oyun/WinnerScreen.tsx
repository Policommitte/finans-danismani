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
import { useLanguage } from "../../contexts/LanguageContext";

type Props = {
  result: GameResult;
  onGoPoints: () => void;
};

function useCountUp(target: number, ms = 1200) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const id = setInterval(() => {
      const t = Math.min(1, (Date.now() - start) / ms);
      setValue(Math.round(target * (1 - Math.pow(1 - t, 3))));
      if (t >= 1) clearInterval(id);
    }, 40);
    return () => clearInterval(id);
  }, [target, ms]);

  return value;
}

const CONFETTI_COLORS = ["#e21b3c", "#1368ce", "#d89e00", "#26890c", "#f5a524", "#8b5cf6"];

function Confetti() {
  const pieces = useMemo(
    () =>
      Array.from({ length: 40 }, (_, i) => ({
        left: Math.random() * 100,
        delay: Math.random() * 0.6,
        duration: 2.4 + Math.random() * 1.4,
        color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
        rotate: Math.random() * 360,
        size: 6 + Math.random() * 6,
      })),
    []
  );

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-xl" aria-hidden="true">
      {pieces.map((p, i) => (
        <span
          key={i}
          className="qz-confetti absolute top-0 block rounded-sm"
          style={{
            left: p.left + "%",
            width: p.size,
            height: p.size * 0.6,
            background: p.color,
            animationDelay: p.delay + "s",
            animationDuration: p.duration + "s",
            transform: "rotate(" + p.rotate + "deg)",
          }}
        />
      ))}
    </div>
  );
}

export function WinnerScreen({ result, onGoPoints }: Props) {
  const { language } = useLanguage();
  const stats = useMemo(() => buildWinnerStats(result.score, language), [result.score, language]);
  const code = useMemo(() => makeReferralCode(), []);
  const payout = useCountUp(stats.myPayout);
  const [copied, setCopied] = useState(false);

  const locale = language === "tr" ? "tr-TR" : "en-US";
  const shareText =
    language === "tr"
      ? "Şans Yatırımda'da " + CONFIG.questionCount + " sorunun hepsini bildim ve " + stats.myPayout.toLocaleString(locale) + " bonus puan kazandım. Davet kodum: " + code
      : "I got all " + CONFIG.questionCount + " questions right on Şans Yatırımda and won " + stats.myPayout.toLocaleString(locale) + " bonus points. My invite code: " + code;
  const shareUrl = "https://polifin.local/yatirim-oyunu";

  const waLink = "https://wa.me/?text=" + encodeURIComponent(shareText + " " + shareUrl);
  const xLink = "https://x.com/intent/tweet?text=" + encodeURIComponent(shareText) + "&url=" + encodeURIComponent(shareUrl);
  const mailSubject = language === "tr" ? "Şans Yatırımda'ya davetlisin" : "You're invited to Şans Yatırımda";
  const mailLink = "mailto:?subject=" + encodeURIComponent(mailSubject) + "&body=" + encodeURIComponent(shareText + "\n\n" + shareUrl);

  const invites = [
    { label: "WhatsApp", href: waLink },
    { label: "X", href: xLink },
    { label: language === "tr" ? "E-posta" : "Email", href: mailLink },
  ];

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(function () {
        setCopied(false);
      }, 2000);
    } catch (e) {
      setCopied(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Card>
        <div
          className="relative flex flex-col items-center gap-3 overflow-hidden rounded-xl px-6 py-9 text-center"
          style={{
            background: "linear-gradient(160deg, var(--color-panel-dark) 0%, color-mix(in srgb, var(--color-panel-dark) 75%, var(--color-primary)) 100%)",
            color: "var(--color-on-primary)",
          }}
        >
          <Confetti />

          <div className="relative">
            <Mascot
              mood="happy"
              message={language === "tr" ? "Tebrikler, hepsini bildin!" : "Congratulations, you got them all!"}
            />
          </div>

          <p className="relative mt-2 text-xs font-bold uppercase tracking-[0.25em] opacity-80">
            Şans Yatırımda
          </p>
          <p className="relative text-2xl font-bold">
            {language === "tr" ? "Tüm soruları bildin" : "You got every question right"}
          </p>

          <div className="relative">
            <p className="qz-payout-pop text-6xl font-black tabular-nums" style={{ color: "var(--color-cta)" }}>
              {payout.toLocaleString(locale)}
            </p>
            <p className="mt-1 text-sm opacity-80">
              {language === "tr" ? "bonus puan kazandın" : "bonus points earned"}
            </p>
          </div>

          <div className="relative grid w-full max-w-sm grid-cols-3 gap-2 text-sm">
            <div className="rounded-lg py-2" style={{ background: "rgba(255,255,255,.08)" }}>
              <p className="text-lg font-bold tabular-nums">{result.score.toLocaleString(locale)}</p>
              <p className="text-[11px] opacity-70">{language === "tr" ? "Skorun" : "Your score"}</p>
            </div>
            <div className="rounded-lg py-2" style={{ background: "rgba(255,255,255,.08)" }}>
              <p className="text-lg font-bold tabular-nums">{stats.winners}</p>
              <p className="text-[11px] opacity-70">{language === "tr" ? "Kazanan" : "Winners"}</p>
            </div>
            <div className="rounded-lg py-2" style={{ background: "rgba(255,255,255,.08)" }}>
              <p className="text-lg font-bold tabular-nums">{stats.myRank}.</p>
              <p className="text-[11px] opacity-70">{language === "tr" ? "Sıran" : "Your rank"}</p>
            </div>
          </div>
        </div>
      </Card>

      <Card title={language === "tr" ? "Ödül dağılımı" : "Prize distribution"}>
        <p className="app-muted mb-3 text-sm">
          {language === "tr"
            ? CONFIG.prizePool.toLocaleString("tr-TR") + " puanlık havuz, kazananlar arasında skor payı oranında bölüşüldü. Sıralama anonimdir."
            : "The " + CONFIG.prizePool.toLocaleString("en-US") + "-point pool was split among winners in proportion to their score share. The ranking is anonymous."}
        </p>

        <ul className="space-y-2">
          {stats.board.map(function (row, i) {
            return (
              <li
                key={row.label + "-" + i}
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
                  <span className="app-muted">
                    {row.score.toLocaleString(locale)} {language === "tr" ? "skor" : "score"}
                  </span>
                  <span className="font-semibold" style={{ color: "var(--color-success)" }}>
                    +{row.payout.toLocaleString(locale)}
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      </Card>

      <Card title={language === "tr" ? "Arkadaşını davet et" : "Invite a friend"}>
        <div className="space-y-3">
          <p className="app-muted text-sm">
            {language === "tr"
              ? "Davet ettiğin her arkadaşın ilk yarışmasına katıldığında hesabına 500 bonus puan yüklenir."
              : "500 bonus points are added to your account every time a friend you invite joins their first contest."}
          </p>

          <div className="flex flex-wrap items-center gap-2">
            <code className="rounded-lg px-4 py-2 text-sm font-semibold tracking-widest" style={{ background: "var(--color-surface-muted)" }}>
              {code}
            </code>
            <button
              onClick={copyCode}
              className="rounded-lg border px-3 py-2 text-xs font-semibold transition"
              style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
            >
              {copied ? (language === "tr" ? "Kopyalandı" : "Copied") : (language === "tr" ? "Kodu kopyala" : "Copy code")}
            </button>
          </div>

          <div className="flex flex-wrap gap-2">
            {invites.map(function (item) {
              return (
                <a
                  key={item.label}
                  href={item.href}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg px-4 py-2 text-sm font-semibold transition"
                  style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}
                >
                  {language === "tr" ? item.label + " ile paylaş" : "Share via " + item.label}
                </a>
              );
            })}
          </div>
        </div>
      </Card>

      <div className="flex justify-center">
        <button
          onClick={onGoPoints}
          className="rounded-lg px-5 py-2.5 text-sm font-semibold transition"
          style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}
        >
          {language === "tr" ? "Puanlarımı gör" : "View my points"}
        </button>
      </div>
    </div>
  );
}