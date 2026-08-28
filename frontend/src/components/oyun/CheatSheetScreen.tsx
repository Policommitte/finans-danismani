"use client";

import { useEffect, useState } from "react";
import Card from "../ui/Card";
import { FlipCard } from "./FlipCard";
import { CHEAT_SHEET, CONFIG } from "../../models/oyun";

type Props = {
  onFinish: () => void;
};

const TOPIC_ICONS = ["📈", "💸", "🧺", "⚖️", "🛟", "💳"];
const TOPIC_COLORS = [
  "var(--color-primary)",
  "var(--color-cta)",
  "var(--color-success)",
  "var(--color-chart-purple)",
  "var(--color-chart-cyan)",
  "var(--color-danger)",
];

export function CheatSheetScreen({ onFinish }: Props) {
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
            style={{ color: "var(--color-cta)" }}
          >
            Hazırlık
          </p>
          <h2 className="app-heading mt-1 text-xl font-semibold">Çalışma notu</h2>
        </div>

        <div className="text-right">
          <span className="app-muted block text-xs">Yarışma başlıyor</span>
          <strong
            className="block text-2xl font-bold tabular-nums"
            style={{ color: "var(--color-cta)" }}
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
          style={{ width: `${progress}%`, background: "var(--color-cta)" }}
        />
      </div>

      <p className="app-muted mt-4 max-w-3xl text-sm leading-relaxed">
        Kartlara tıklayıp çevir, konuyu oku. Sorular bu konulardan gelecek, ancak cevaplar
        burada doğrudan yazmıyor — konuyu anlaman gerekiyor.
      </p>

      {/* 6 flip kart */}
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {CHEAT_SHEET.map((t, i) => (
          <FlipCard            key={t.title}
            icon={TOPIC_ICONS[i] ?? "📌"}
            title={t.title}
            body={t.body}
            color={TOPIC_COLORS[i] ?? "var(--color-primary)"}
          />
         ))}
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
          {ready ? "Hazırsın, yarışma bekleniyor…" : "Hazırım"}
        </button>

        <p className="app-muted mt-2 text-xs">
          Yarışma tüm katılımcılar için aynı anda başlar.
        </p>

        <button
          onClick={onFinish}
          className="mt-4 text-xs font-semibold underline underline-offset-4"
          style={{ color: "var(--color-muted)" }}
        >
          Demo: yarışmaya geç
        </button>
      </div>
    </Card>
  );
}