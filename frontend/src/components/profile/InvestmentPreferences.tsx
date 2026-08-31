"use client";

import { useEffect, useState } from "react";
import Button from "../ui/Button";

function TagIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.59 2.59 20 10v.01L10.01 20H10L2 12V2h10z" />
      <circle cx="7" cy="7" r="1.2" fill="currentColor" stroke="none" />
    </svg>
  );
}

const sectors = ["Savunma", "Teknoloji", "Enerji", "Bankacılık", "Perakende", "Otomotiv", "Gıda", "İnşaat"];

const assetTypes = ["BIST Hisseleri", "Kripto Para", "Emtia", "Yatırım Fonları", "Döviz", "Tahvil/Bono"];

function TagGroup({
  title,
  items,
  selected,
  onToggle,
}: {
  title: string;
  items: string[];
  selected: Set<string>;
  onToggle: (item: string) => void;
}) {
  return (
    <div>
      <h3 className="text-sm font-semibold app-heading">{title}</h3>
      <div className="mt-2 flex flex-wrap gap-2">
        {items.map((item) => {
          const isSelected = selected.has(item);
          return (
            <button
              key={item}
              type="button"
              onClick={() => onToggle(item)}
              aria-pressed={isSelected}
              className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
                isSelected ? "text-white" : "app-card-muted app-heading hover:opacity-90"
              }`}
              style={isSelected ? { background: "var(--color-brand-teal)" } : undefined}
            >
              {item}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function InvestmentPreferences() {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showSavedNotice, setShowSavedNotice] = useState(false);

  useEffect(() => {
    if (!showSavedNotice) {
      return;
    }
    const timer = window.setTimeout(() => setShowSavedNotice(false), 2500);
    return () => window.clearTimeout(timer);
  }, [showSavedNotice]);

  function toggle(item: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(item)) {
        next.delete(item);
      } else {
        next.add(item);
      }
      return next;
    });
  }

  function handleSave() {
    setShowSavedNotice(true);
  }

  return (
    <div className="rounded-2xl border app-card p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <span
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
          style={{
            background: "color-mix(in srgb, var(--color-accent) 18%, var(--color-surface))",
            color: "var(--color-accent)",
          }}
        >
          <TagIcon />
        </span>
        <h2 className="text-base font-semibold app-heading">Yatırım Tercihlerim</h2>
      </div>
      <p className="mt-2 text-sm app-muted">Takip etmek istediğin sektörleri ve varlık türlerini seç.</p>

      <div className="mt-4 space-y-4">
        <TagGroup title="Sektörler" items={sectors} selected={selected} onToggle={toggle} />
        <TagGroup title="Varlık Türleri" items={assetTypes} selected={selected} onToggle={toggle} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button type="button" onClick={handleSave}>
          Tercihleri Kaydet
        </Button>
        {showSavedNotice && (
          <span className="text-sm font-medium" style={{ color: "var(--color-brand-teal)" }}>
            Tercihlerin kaydedildi ✓
          </span>
        )}
      </div>
    </div>
  );
}
