"use client";

import { useEffect, useState } from "react";
import Button from "../ui/Button";

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
    <div className="rounded-xl border app-card p-5 shadow-sm">
      <h2 className="text-base font-semibold app-heading">🏷️ Yatırım Tercihlerim</h2>
      <p className="mt-1 text-sm app-muted">Takip etmek istediğin sektörleri ve varlık türlerini seç.</p>

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
