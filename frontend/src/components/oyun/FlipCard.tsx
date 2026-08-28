"use client";

import { useState } from "react";

type Props = {
  icon: string;
  title: string;
  body: string;
  color?: string;
};

export function FlipCard({ icon, title, body, color = "var(--color-primary)" }: Props) {
  const [flipped, setFlipped] = useState(false);

  return (
    <button
      type="button"
      onClick={() => setFlipped((f) => !f)}
      aria-pressed={flipped}
      aria-label={`${title} — ${flipped ? "kartı kapat" : "kartı çevir"}`}
      className={`flip-card h-40 w-full text-left ${flipped ? "flipped" : ""}`}
    >
      <div className="flip-card-inner">
        <div
          className="flip-card-face flex flex-col items-center justify-center gap-2 rounded-xl border-2 px-4 text-center"
          style={{
            background: `color-mix(in srgb, ${color} 10%, var(--color-surface))`,
            borderColor: `color-mix(in srgb, ${color} 35%, transparent)`,
          }}
        >
          <span className="text-2xl" aria-hidden="true">
            {icon}
          </span>
          <span className="app-heading text-sm font-semibold leading-snug">{title}</span>
          <span className="app-muted text-[11px]">Çevirmek için tıkla</span>
        </div>

        <div
          className="flip-card-face flip-card-back flex flex-col justify-center rounded-xl border-2 px-4 py-3"
          style={{
            background: `color-mix(in srgb, ${color} 16%, var(--color-surface))`,
            borderColor: color,
          }}
        >
          <span className="text-[11px] font-bold uppercase tracking-wide" style={{ color }}>
            {title}
          </span>
          <p className="app-heading mt-1.5 text-[13px] leading-relaxed">{body}</p>
        </div>
      </div>
    </button>
  );
}