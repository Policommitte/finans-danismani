"use client";

import { useState, type ReactNode } from "react";
import { useLanguage } from "../../contexts/LanguageContext";

type Props = {
  icon: ReactNode;
  title: string;
  color: string;
  children: ReactNode;
  /** vertical: dikey, boy dolduran kart (sidebar) — horizontal: geniş, yatay kart */
  orientation?: "vertical" | "horizontal";
};

export function InfoFlipCard({ icon, title, color, children, orientation = "vertical" }: Props) {
  const { language } = useLanguage();
  const [flipped, setFlipped] = useState(false);
  const isHorizontal = orientation === "horizontal";

  return (
    <button
      type="button"
      onClick={() => setFlipped((f) => !f)}
      aria-pressed={flipped}
      className={`flip-card w-full text-left ${isHorizontal ? "h-40" : "h-full"} ${
        flipped ? "flipped" : ""
      }`}
    >
      <div className="flip-card-inner">
        <div
          className={`flip-card-face flex items-center justify-center gap-3 rounded-xl border-2 px-4 text-center ${
            isHorizontal ? "flex-row" : "flex-col"
          }`}
          style={{
            background: `color-mix(in srgb, ${color} 10%, var(--color-surface))`,
            borderColor: `color-mix(in srgb, ${color} 35%, transparent)`,
          }}
        >
          <span className="shrink-0" style={{ color }} aria-hidden="true">
            {icon}
          </span>
          <div className={isHorizontal ? "text-left" : ""}>
            <span className="app-heading block text-base font-semibold leading-snug">{title}</span>
            <span className="app-muted block text-[11px]">{language === "tr" ? "Çevirmek için tıkla" : "Tap to flip"}</span>
          </div>
        </div>

        <div
          className="flip-card-face flip-card-back overflow-y-auto rounded-xl border-2 px-4 py-3"
          style={{
            background: `color-mix(in srgb, ${color} 16%, var(--color-surface))`,
            borderColor: color,
          }}
        >
          <span className="text-[11px] font-bold uppercase tracking-wide" style={{ color }}>
            {title}
          </span>
          <div
            className={`app-heading mt-1.5 text-[12.5px] leading-relaxed ${
              isHorizontal ? "grid gap-x-6 gap-y-2 sm:grid-cols-2" : "space-y-2.5"
            }`}
          >
            {children}
          </div>
        </div>
      </div>
    </button>
  );
}