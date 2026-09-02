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

function DropletIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3s7 7.5 7 12a7 7 0 0 1-14 0c0-4.5 7-12 7-12z" />
    </svg>
  );
}

function PercentIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="7" r="2.5" />
      <circle cx="17" cy="17" r="2.5" />
      <line x1="18" y1="6" x2="6" y2="18" />
    </svg>
  );
}

function SwapIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 8h13" />
      <path d="M13 4l4 4-4 4" />
      <path d="M20 16H7" />
      <path d="M11 20l-4-4 4-4" />
    </svg>
  );
}

export const TOPIC_ICONS = [
  TrendingUpIcon,
  TrendingDownIcon,
  PieChartIcon,
  ScaleIcon,
  ShieldCheckIcon,
  CreditCardIcon,
];
export const TOPIC_COLORS = [
  "var(--color-primary)",
  "var(--color-chart-yellow)",
  "var(--color-success)",
  "var(--color-chart-purple)",
  "var(--color-chart-cyan)",
  "var(--color-danger)",
];

function ForkIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v6" />
      <path d="M12 8l-6 6" />
      <path d="M12 8l6 6" />
      <circle cx="6" cy="18" r="2" />
      <circle cx="18" cy="18" r="2" />
    </svg>
  );
}

function ChecklistIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="3" width="16" height="18" rx="2" />
      <path d="M8 8h8" />
      <path d="M8 12h8" />
      <path d="M8 16h5" />
    </svg>
  );
}

function RepeatIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 2l4 4-4 4" />
      <path d="M3 11V9a4 4 0 0 1 4-4h14" />
      <path d="M7 22l-4-4 4-4" />
      <path d="M21 13v2a4 4 0 0 1-4 4H3" />
    </svg>
  );
}

function SlidersIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" y1="6" x2="20" y2="6" />
      <circle cx="9" cy="6" r="2" fill="currentColor" stroke="none" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <circle cx="15" cy="12" r="2" fill="currentColor" stroke="none" />
      <line x1="4" y1="18" x2="20" y2="18" />
      <circle cx="11" cy="18" r="2" fill="currentColor" stroke="none" />
    </svg>
  );
}

function UmbrellaIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a9 9 0 0 1 9 9H3a9 9 0 0 1 9-9z" />
      <path d="M12 11v8a2 2 0 0 1-4 0" />
      <path d="M12 2v2" />
    </svg>
  );
}

function TargetIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

// Sonraki yarışmayı beklerken gösterilen notlar (WAITING_NOTES, oyun.ts) için
// ÇALIŞMA NOTUNDAKİLERDEN farklı ikon/renk seti - iki ekranın karıştırılmaması icin.
export const WAITING_TOPIC_ICONS = [
  DropletIcon,
  PercentIcon,
  SwapIcon,
  ForkIcon,
  ChecklistIcon,
  RepeatIcon,
  SlidersIcon,
  UmbrellaIcon,
  TargetIcon,
];
export const WAITING_TOPIC_COLORS = [
  "var(--color-cta)",
  "color-mix(in srgb, var(--color-primary) 50%, var(--color-chart-cyan) 50%)",
  "color-mix(in srgb, var(--color-danger) 55%, var(--color-chart-yellow) 45%)",
  "color-mix(in srgb, var(--color-primary) 55%, var(--color-success) 45%)",
  "color-mix(in srgb, var(--color-chart-purple) 55%, var(--color-chart-cyan) 45%)",
  "color-mix(in srgb, var(--color-success) 55%, var(--color-chart-yellow) 45%)",
  "color-mix(in srgb, var(--color-danger) 55%, var(--color-chart-purple) 45%)",
  "color-mix(in srgb, var(--color-cta) 55%, var(--color-success) 45%)",
  "color-mix(in srgb, var(--color-primary) 55%, var(--color-chart-yellow) 45%)",
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
          className={`rounded-full px-7 py-3.5 text-sm font-bold text-white transition disabled:cursor-default ${
            ready ? "" : "hover:scale-[1.03] hover:shadow-xl active:scale-[0.98]"
          }`}
          style={
            ready
              ? { background: "var(--color-border)", color: "var(--color-muted)" }
              : {
                  background: "linear-gradient(135deg, var(--color-primary) 0%, color-mix(in srgb, var(--color-primary) 70%, #7c3aed) 100%)",
                  boxShadow: "0 8px 24px color-mix(in srgb, var(--color-primary) 45%, transparent)",
                }
          }
        >
          <span className="inline-flex items-center justify-center gap-2">
            {!ready && (
              <span className="animate-pulse text-base" aria-hidden="true">
                🚀
              </span>
            )}
            {ready
              ? (language === "tr" ? "Hazırsın, yarışma bekleniyor…" : "You're ready, waiting for the contest…")
              : (language === "tr" ? "Hazırım" : "I'm ready")}
          </span>
        </button>

        <p className="app-muted mt-2 text-xs">
          {language === "tr"
            ? "Yarışma tüm katılımcılar için aynı anda başlar."
            : "The contest starts at the same time for all participants."}
        </p>
      </div>
    </Card>
  );
}
