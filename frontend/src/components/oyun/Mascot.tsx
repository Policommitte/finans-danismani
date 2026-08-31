"use client";

import { Blobatar } from "blobatar/react";
import { thinking, happy, sad, mad } from "blobatar/expression";
import "blobatar/motion.css";

import type { MascotMood } from "../../hooks/useQuiz";
import { useLanguage } from "../../contexts/LanguageContext";

type Props = {
  mood: MascotMood;
  message: string;
};

/**
 * Maskot blobatar ile cizilir. `name` VE `hue` birlikte gorunumu belirler:
 * blobatar "ayni string HER ZAMAN ayni blobatar'i uretir" ilkesiyle
 * calisir - `hue` sadece rengin TONUNU kilitler, "tone" (acik/koyu) hala
 * isim hash'inden turetilir. Bu yuzden sitenin geneli (ChatWidget.tsx ->
 * ChatAvatar) ile AYNI ismi ("Aichatbot") kullanmak sart: sadece hue
 * esitlemek yeterli degildi, oyunun maskotu daha soluk/acik bir mavi
 * cikiyordu (bkz. gorsel tutarsizlik raporu). Ayni isim = piksel piksel
 * ayni renk/ton garantisi.
 */
const MASCOT_NAME = "Aichatbot";
const MASCOT_TRAITS = { shape: 0.933 }; // altıgen siluet
const MASCOT_HUE = 225; // chatbot ile ayni ton

/** Oyun durumu → blobatar ifadesi */
const EXPRESSION = {
  idle: thinking,
  hurry: mad,
  happy: happy,
  sad: sad,
} as const;

const BUBBLE_STYLE: Record<MascotMood, { bg: string; color: string }> = {
  idle: { bg: "var(--color-surface)", color: "var(--color-text)" },
  hurry: { bg: "var(--color-warning-bg)", color: "var(--color-warning-text)" },
  happy: { bg: "var(--color-primary-soft)", color: "var(--color-success)" },
  sad: { bg: "var(--color-danger-bg)", color: "var(--color-danger-text)" },
};

export function Mascot({ mood, message }: Props) {
  const { language } = useLanguage();
  const bubble = BUBBLE_STYLE[mood];

  return (
    <div className="flex items-center gap-3">
      <div className="grid h-[86px] w-[82px] shrink-0 place-items-center overflow-hidden rounded-full bg-[var(--color-panel-dark)]">
        <span className="block h-[118%] w-[118%] [&_svg]:h-full [&_svg]:w-full">
          <Blobatar
            name={MASCOT_NAME}
            traits={MASCOT_TRAITS}
            hue={MASCOT_HUE}
            expression={EXPRESSION[mood]}
            animate="always"
            title={language === "tr" ? "Yarışma danışmanı" : "Contest assistant"}
          />
        </span>
      </div>

      <div
        className="relative min-w-0 flex-1 rounded-xl px-4 py-2.5 text-[13.5px] font-semibold shadow-sm"
        style={{ background: bubble.bg, color: bubble.color }}
      >
        <span
          className="absolute -left-1.5 top-1/2 h-3 w-3 -translate-y-1/2 rotate-45"
          style={{ background: bubble.bg }}
        />
        <span className="relative">{message}</span>
      </div>
    </div>
  );
}
