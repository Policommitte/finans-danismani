"use client";

import { useEffect, useState } from "react";
import Card from "../ui/Card";
import { FlipCard } from "./FlipCard";
import { CHEAT_SHEET, CONFIG } from "../../models/oyun";
import { useLanguage } from "../../contexts/LanguageContext";

type Props = {
  onFinish: () => void;
};

//: Site genelinde kullanilan ayni ikon dili (24x24, stroke=currentColor,
//: strokeWidth 1.8, yuvarlak uc/kose) - bkz. destek/page.tsx CheckShieldIcon,
//: profile/page.tsx TargetIcon. Projede harici bir ikon paketi (lucide vb.)
//: YOK - tum ikonlar boyle yerel SVG fonksiyonlari olarak tanimli.
function TrendingUpIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 17 9 11 13 15 21 7" />
      <polyline points="14 7 21 7 21 14" />
    </svg>
  );
}

function TrendingDownIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 7 9 13 13 9 21 17" />
      <polyline points="14 17 21 17 21 10" />
    </svg>
  );
}

function PieChartIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
      <path d="M22 12A10 10 0 0 0 12 2v10z" />
    </svg>
  );
}

function ScaleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v13" />
      <path d="M5 8h14" />
      <path d="M9 21h6" />
      <path d="M2 15c0 1.7 1.3 3 3 3s3-1.3 3-3L5 8z" />
      <path d="M16 15c0 1.7 1.3 3 3 3s3-1.3 3-3l-3-7z" />
    </svg>
  );
}

function ShieldCheckIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l7 3v5c0 4.5-3 8.4-7 10-4-1.6-7-5.5-7-10V6z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function CreditCardIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="5" width="20" height="14" rx="2" />
      <path d="M2 10h20" />
      <path d="M6 15h4" />
    </svg>
  );
}

const TOPIC_ICONS = [TrendingUpIcon, TrendingDownIcon, PieChartIcon, ScaleIcon, ShieldCheckIcon, CreditCardIcon];
const TOPIC_COLORS = [
  "var(--color-primary)",
  "var(--color-chart-yellow)",
  "var(--color-success)",
  "var(--color-chart-purple)",
  "var(--color-chart-cyan)",
  "var(--color-danger)",
];

export function CheatSheetScreen({ onFinish }: Props) {
  const { language } = useLanguage();
  const [left, setLeft] = useState<number>(CONFIG.cheatSheetSeconds);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (left <= 0) {
      onFinish();
      return;
    }
    const id = setTimeout(() => setLeft((n) => n - 1), 1000);
    return () => clearTimeout(id);
  }, [left, onFinish]);

  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");
  const progress = ((CONFIG.cheatSheetSeconds - left) / CONFIG.cheatSheetSeconds) * 100;

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p
            className="text-[11px] font-bold uppercase tracking-[0.16em]"
            style={{ color: "var(--color-primary)" }}
          >
            {language === "tr" ? "Hazırlık" : "Preparation"}
          </p>
          <h2 className="app-heading mt-1 text-xl font-semibold">
            {language === "tr" ? "Çalışma notu" : "Study notes"}
          </h2>
        </div>

        <div className="text-right">
          <span className="app-muted block text-xs">
            {language === "tr" ? "Yarışma başlıyor" : "Contest starting in"}
          </span>
          <strong
            className="block text-2xl font-bold tabular-nums"
            style={{ color: "var(--color-primary)" }}
          >
            {mm}:{ss}
          </strong>
        </div>
      </div>

      <div
        className="mt-3 h-1 overflow-hidden rounded-full"
        style={{ background: "var(--color-border)" }}
      >
        <span
          className="block h-full rounded-full transition-[width] duration-1000 ease-linear"
          style={{ width: `${progress}%`, background: "var(--color-primary)" }}
        />
      </div>

      <p className="app-muted mt-4 max-w-3xl text-sm leading-relaxed">
        {language === "tr"
          ? "Kartlara tıklayıp çevir, konuyu oku. Sorular bu konulardan gelecek, ancak cevaplar burada doğrudan yazmıyor — konuyu anlaman gerekiyor."
          : "Click the cards to flip them and read the topic. Questions will come from these topics, but the answers aren't written here directly — you need to understand the topic."}
      </p>

      {/* 6 flip kart */}
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {CHEAT_SHEET.map((t, i) => {
          const TopicIcon = TOPIC_ICONS[i] ?? TrendingUpIcon;
          return (
            <FlipCard
              key={t.title.tr}
              icon={<TopicIcon />}
              title={t.title[language]}
              body={t.body[language]}
              color={TOPIC_COLORS[i] ?? "var(--color-primary)"}
            />
          );
        })}
      </div>

      <div className="mt-6 text-center">
        <button
          onClick={() => setReady(true)}
          disabled={ready}
          className="rounded-lg px-6 py-3 text-sm font-semibold transition disabled:cursor-default"
          style={{
            background: ready ? "var(--color-border)" : "var(--color-primary)",
            color: ready ? "var(--color-muted)" : "#fff",
          }}
        >
          {ready
            ? (language === "tr" ? "Hazırsın, yarışma bekleniyor…" : "You're ready, waiting for the contest…")
            : (language === "tr" ? "Hazırım" : "I'm ready")}
        </button>

        <p className="app-muted mt-2 text-xs">
          {language === "tr"
            ? "Yarışma tüm katılımcılar için aynı anda başlar."
            : "The contest starts at the same time for all participants."}
        </p>

        <button
          onClick={onFinish}
          className="mt-4 text-xs font-semibold underline underline-offset-4"
          style={{ color: "var(--color-muted)" }}
        >
          {language === "tr" ? "Demo: yarışmaya geç" : "Demo: skip to contest"}
        </button>
      </div>
    </Card>
  );
}
