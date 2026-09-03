"use client";

import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useLanguage } from "../../contexts/LanguageContext";
import { AutonomousTradingPanel } from "./AutonomousTradingPanel";
import { BasketSuggestionPanel } from "./BasketSuggestionPanel";
import { InfluencerBasketsPanel } from "./InfluencerBasketsPanel";
import { ManualTradingPanel } from "./ManualTradingPanel";

type TradingMode = "manual" | "autonomous" | "basket" | "influencer";

export function TradingCenter() {
  const { language } = useLanguage();
  const [mode, setMode] = useState<TradingMode>("manual");
  const [visited, setVisited] = useState<Set<TradingMode>>(() => new Set(["manual"]));
  const [readyModes, setReadyModes] = useState<Set<TradingMode>>(() => new Set());

  const markManualReady = useCallback(() => {
    setReadyModes((current) =>
      current.has("manual") ? current : new Set([...current, "manual"]),
    );
  }, []);
  const markAutonomousReady = useCallback(() => {
    setReadyModes((current) =>
      current.has("autonomous") ? current : new Set([...current, "autonomous"]),
    );
  }, []);
  const markBasketReady = useCallback(() => {
    setReadyModes((current) =>
      current.has("basket") ? current : new Set([...current, "basket"]),
    );
  }, []);
  const markInfluencerReady = useCallback(() => {
    setReadyModes((current) =>
      current.has("influencer") ? current : new Set([...current, "influencer"]),
    );
  }, []);

  useEffect(() => {
    if (window.location.search) {
      window.history.replaceState(window.history.state, "", "/market");
    }
  }, []);

  useEffect(() => {
    setVisited((current) => {
      if (current.has(mode)) return current;
      return new Set([...current, mode]);
    });
  }, [mode]);

  function selectMode(nextMode: TradingMode) {
    if (nextMode === mode) return;
    setVisited((current) =>
      current.has(nextMode) ? current : new Set([...current, nextMode]),
    );
    setMode(nextMode);
  }

  return (
    <div className="space-y-6" aria-busy={!readyModes.has(mode)}>
      <div>
        <h1 className="text-2xl font-semibold app-heading">
          {language === "tr" ? "İşlem Merkezi" : "Trading Center"}
        </h1>
        <p className="mt-1 text-sm app-muted">
          {language === "tr"
            ? "Manuel sanal işlemlerini ve kişiselleştirilmiş otonom önerileri aynı ekrandan yönet."
            : "Manage manual virtual trades and personalized autonomous suggestions in one place."}
        </p>
      </div>

      <div
        className="grid w-full max-w-3xl grid-cols-2 gap-1 rounded-2xl app-card-muted p-1.5 sm:grid-cols-4"
        role="tablist"
        aria-label={language === "tr" ? "İşlem türü" : "Trading mode"}
      >
        <ModeButton
          active={mode === "manual"}
          label={language === "tr" ? "Manuel Alım" : "Manual Trading"}
          onClick={() => selectMode("manual")}
        />
        <ModeButton
          active={mode === "autonomous"}
          label={language === "tr" ? "Otonom Alım" : "Autonomous Trading"}
          onClick={() => selectMode("autonomous")}
        />
        <ModeButton
          active={mode === "basket"}
          label={language === "tr" ? "Sepet Önerisi" : "Basket Suggestion"}
          onClick={() => selectMode("basket")}
        />
        <ModeButton
          active={mode === "influencer"}
          label={language === "tr" ? "Fenomen Sepetleri" : "Public-Figure Baskets"}
          onClick={() => selectMode("influencer")}
        />
      </div>

      {visited.has("manual") && (
        <div role="tabpanel" hidden={mode !== "manual"}>
          <ManualTradingPanel onReady={markManualReady} />
        </div>
      )}
      {visited.has("autonomous") && (
        <div role="tabpanel" hidden={mode !== "autonomous"}>
          <AutonomousTradingPanel onReady={markAutonomousReady} />
        </div>
      )}
      {visited.has("basket") && (
        <div role="tabpanel" hidden={mode !== "basket"}>
          <BasketSuggestionPanel onReady={markBasketReady} />
        </div>
      )}
      {visited.has("influencer") && (
        <div role="tabpanel" hidden={mode !== "influencer"}>
          <InfluencerBasketsPanel onReady={markInfluencerReady} />
        </div>
      )}
      {!readyModes.has(mode) && <ModeLoadingOverlay language={language} />}
    </div>
  );
}

function ModeLoadingOverlay({ language }: { language: "tr" | "en" }) {
  const [mainElement, setMainElement] = useState<HTMLElement | null>(null);

  useEffect(() => {
    setMainElement(document.querySelector("main"));
  }, []);

  if (!mainElement) return null;

  return createPortal(
    <div className="absolute inset-0 z-[80] grid place-items-center bg-slate-950/10 backdrop-blur-md">
      <div
        role="status"
        aria-live="polite"
        className="relative flex h-24 w-44 items-start justify-center"
      >
        <span className="page-transition__logo" />
        <span className="page-transition__spinner" />
        <span className="sr-only">
          {language === "tr" ? "İşlemler hazırlanıyor" : "Preparing trades"}
        </span>
      </div>
    </div>,
    mainElement,
  );
}

function ModeButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`rounded-xl px-4 py-3 text-sm font-semibold transition-all ${
        active
          ? "bg-[#454466] text-white shadow-lg"
          : "app-muted hover:bg-white/60 hover:text-[var(--color-text)]"
      }`}
    >
      {label}
    </button>
  );
}
