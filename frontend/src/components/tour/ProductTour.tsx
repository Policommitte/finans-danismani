"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useLanguage, type AppLanguage } from "../../contexts/LanguageContext";

type TourCopy = Record<AppLanguage, string>;
type TourStep = {
  id: string;
  target: string | null;
  targetPadding?: { top?: number; x?: number };
  placement?: Exclude<DialogSide, "center">;
  title: TourCopy;
  description: TourCopy;
};

const SIDEBAR_TARGET_PADDING = { top: 28, x: 18 };

const STEPS: TourStep[] = [
  {
    id: "welcome",
    target: null,
    title: { tr: "Polifin'e hoş geldin!", en: "Welcome to Polifin!" },
    description: {
      tr: "Finansal görünümünü daha kolay takip edebilmen için buradayız. Bu kısa turda uygulamanın temel bölümlerini birlikte keşfedelim.",
      en: "We're here to make your financial picture easier to follow. Let's explore the main parts of the application together in this short tour.",
    },
  },
  {
    id: "home",
    target: '[data-tour="nav-home"]',
    targetPadding: SIDEBAR_TARGET_PADDING,
    title: { tr: "Ana Sayfa", en: "Home" },
    description: {
      tr: "Polifin'in sunduğu özelliklerin genel tanıtımına ve herkese açık bilgilere buradan ulaşabilirsin.",
      en: "Open the public introduction to Polifin and its main features here.",
    },
  },
  {
    id: "overview",
    target: '[data-tour="nav-dashboard"]',
    targetPadding: SIDEBAR_TARGET_PADDING,
    title: { tr: "Genel Bakış", en: "Overview" },
    description: {
      tr: "Portföy değerini, kâr-zarar durumunu, varlık dağılımını ve risk görünümünü tek ekranda takip edebilirsin.",
      en: "Track portfolio value, profit and loss, asset allocation, and risk in one place.",
    },
  },
  {
    id: "newsletter",
    target: '[data-tour="nav-bulten"]',
    targetPadding: SIDEBAR_TARGET_PADDING,
    title: { tr: "Bülten", en: "Newsletter" },
    description: {
      tr: "Piyasa gelişmelerini ve öne çıkan finansal başlıkları Bülten ekranından inceleyebilirsin.",
      en: "Review market developments and highlighted financial topics on the Newsletter page.",
    },
  },
  {
    id: "markets",
    target: '[data-tour="nav-market"]',
    targetPadding: SIDEBAR_TARGET_PADDING,
    title: { tr: "Piyasalar", en: "Markets" },
    description: {
      tr: "Varlık fiyatlarını ve grafiklerini incelemek, sanal emirlerini yönetmek için Piyasalar ekranını kullanabilirsin.",
      en: "Use Markets to inspect asset prices and charts and manage virtual orders.",
    },
  },
  {
    id: "tour-button",
    target: '[data-tour="start-tour"]',
    targetPadding: SIDEBAR_TARGET_PADDING,
    title: { tr: "Platform turu", en: "Platform tour" },
    description: {
      tr: "Uygulamanın bölümlerini yeniden hatırlamak istediğinde bu düğmeyle platform turunu istediğin zaman başlatabilirsin.",
      en: "Use this button whenever you want to restart the platform tour and revisit the application's main sections.",
    },
  },
  {
    id: "profile",
    target: '[data-tour="nav-profile"]',
    targetPadding: SIDEBAR_TARGET_PADDING,
    title: { tr: "Profil", en: "Profile" },
    description: {
      tr: "Kişisel bilgilerini ve yatırımcı profilini bu bölümden görüntüleyip yönetebilirsin.",
      en: "View and manage your personal details and investor profile here.",
    },
  },
  {
    id: "settings",
    target: '[data-tour="nav-settings"]',
    targetPadding: SIDEBAR_TARGET_PADDING,
    title: { tr: "Ayarlar", en: "Settings" },
    description: {
      tr: "Uygulama tercihlerini ve hesap ayarlarını bu sayfadan düzenleyebilirsin.",
      en: "Manage application preferences and account settings on this page.",
    },
  },
  {
    id: "market-stream",
    target: '[data-tour="market-stream"]',
    placement: "below",
    title: { tr: "Canlı piyasa akışı", en: "Live market stream" },
    description: {
      tr: "Takip edilen varlıkların son değerlerini ve yüzdesel değişimlerini sayfa değiştirmeden üst bardan izleyebilirsin.",
      en: "Follow the latest values and percentage changes of tracked assets from the top bar.",
    },
  },
  {
    id: "appearance",
    target: '[data-tour="appearance-controls"]',
    placement: "below",
    title: { tr: "Dil ve tema", en: "Language and theme" },
    description: {
      tr: "Açık veya koyu temayı seçebilir, uygulama dilini Türkçe ve İngilizce arasında değiştirebilirsin.",
      en: "Choose light or dark mode and switch the application between Turkish and English.",
    },
  },
  {
    id: "assistant",
    target: '[data-tour="chat-assistant"]',
    title: { tr: "Finansal asistan", en: "Financial assistant" },
    description: {
      tr: "Chatbot görseline tıklayarak portföyün veya piyasalar hakkında finansal asistana soru sorabilirsin.",
      en: "Click the chatbot image to ask the financial assistant about your portfolio or the markets.",
    },
  },
];

type TargetRect = Pick<DOMRect, "bottom" | "height" | "left" | "right" | "top" | "width">;
type DialogSide = "above" | "below" | "center" | "left" | "right";
type DialogPosition = { left: number; side: DialogSide; top: number };

function readTargetRect(selector: string, padding?: TourStep["targetPadding"]): TargetRect | null {
  const element = document.querySelector<HTMLElement>(selector);
  if (!element) return null;
  const rect = element.getBoundingClientRect();
  const paddingTop = padding?.top ?? 0;
  const paddingX = padding?.x ?? 0;
  return {
    bottom: rect.bottom,
    height: rect.height + paddingTop,
    left: rect.left - paddingX,
    right: rect.right + paddingX,
    top: rect.top - paddingTop,
    width: rect.width + paddingX * 2,
  };
}

function placeDialog(
  rect: TargetRect,
  width: number,
  height: number,
  preferredSide?: Exclude<DialogSide, "center">,
): DialogPosition {
  const gap = 54;
  const padding = 16;
  const centeredTop = rect.top + rect.height / 2 - height / 2;
  const centeredLeft = rect.left + rect.width / 2 - width / 2;
  const clampedTop = Math.min(Math.max(centeredTop, padding), window.innerHeight - height - padding);
  const clampedLeft = Math.min(Math.max(centeredLeft, padding), window.innerWidth - width - padding);
  const naturalCandidates: DialogPosition[] = [
    { left: rect.right + gap, side: "right", top: clampedTop },
    { left: rect.left - width - gap, side: "left", top: clampedTop },
    { left: clampedLeft, side: "below", top: rect.bottom + gap },
    { left: clampedLeft, side: "above", top: rect.top - height - gap },
  ];
  const candidates = preferredSide
    ? [
        ...naturalCandidates.filter((candidate) => candidate.side === preferredSide),
        ...naturalCandidates.filter((candidate) => candidate.side !== preferredSide),
      ]
    : naturalCandidates;
  const fitting = candidates.find((candidate) =>
    candidate.left >= padding && candidate.top >= padding &&
    candidate.left + width <= window.innerWidth - padding &&
    candidate.top + height <= window.innerHeight - padding,
  );
  if (fitting) return fitting;
  return {
    left: clampedLeft,
    side: "center",
    top: clampedTop,
  };
}

function placeArrow(rect: TargetRect, side: DialogSide) {
  const size = 34;
  if (side === "right") return { left: rect.right + 2, top: rect.top + rect.height / 2 - size / 2, transform: "rotate(180deg)" };
  if (side === "left") return { left: rect.left - size - 2, top: rect.top + rect.height / 2 - size / 2, transform: "rotate(0deg)" };
  if (side === "below") return { left: rect.left + rect.width / 2 - size / 2, top: rect.bottom + 2, transform: "rotate(-90deg)" };
  return { left: rect.left + rect.width / 2 - size / 2, top: rect.top - size - 2, transform: "rotate(90deg)" };
}

export function ProductTour({ open, onClose, storageKey }: { open: boolean; onClose: () => void; storageKey: string }) {
  const { language } = useLanguage();
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState<TargetRect | null>(null);
  const [dialogPosition, setDialogPosition] = useState<DialogPosition | null>(null);
  const [locating, setLocating] = useState(false);
  const [exiting, setExiting] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeTimerRef = useRef<number | null>(null);
  const step = STEPS[stepIndex];

  useEffect(() => {
    if (!open) {
      setStepIndex(0);
      setTargetRect(null);
      setDialogPosition(null);
      setLocating(false);
      setExiting(false);
      return;
    }
    setStepIndex(0);
    setExiting(false);
  }, [open]);

  useEffect(() => () => {
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current);
  }, []);

  function closeTour() {
    if (exiting) return;
    setExiting(true);
    closeTimerRef.current = window.setTimeout(onClose, 180);
  }

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") closeTour();
      else if (!locating && event.key === "ArrowRight") setStepIndex((current) => Math.min(current + 1, STEPS.length - 1));
      else if (!locating && event.key === "ArrowLeft") setStepIndex((current) => Math.max(current - 1, 0));
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [exiting, locating, open]);

  useEffect(() => {
    if (!open) return;
    if (!step.target) {
      setTargetRect(null);
      setLocating(false);
      return;
    }
    const target = step.target;
    const targetPadding = step.targetPadding;
    setLocating(true);
    let attempts = 0;
    let active = true;
    function locateTarget() {
      const nextRect = readTargetRect(target, targetPadding);
      if (nextRect) {
        if (active) {
          setTargetRect(nextRect);
          setLocating(false);
        }
        return;
      }
      attempts += 1;
      if (attempts >= 30) {
        if (active) setLocating(false);
        return;
      }
      window.setTimeout(locateTarget, 100);
    }
    const timer = window.setTimeout(locateTarget, 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [open, step]);

  useEffect(() => {
    if (!open || !targetRect || !step.target) return;
    const target = step.target;
    const targetPadding = step.targetPadding;
    function updateRect() {
      setTargetRect(readTargetRect(target, targetPadding));
    }
    window.addEventListener("resize", updateRect);
    window.addEventListener("scroll", updateRect, true);
    return () => {
      window.removeEventListener("resize", updateRect);
      window.removeEventListener("scroll", updateRect, true);
    };
  }, [open, step.target, Boolean(targetRect)]);

  useLayoutEffect(() => {
    const dialog = dialogRef.current;
    if (!open || !dialog) return;
    if (!step.target || !targetRect) {
      setDialogPosition({
        left: Math.max((window.innerWidth - dialog.offsetWidth) / 2, 16),
        side: "center",
        top: Math.max((window.innerHeight - dialog.offsetHeight) / 2, 16),
      });
      return;
    }
    setDialogPosition(placeDialog(targetRect, dialog.offsetWidth, dialog.offsetHeight, step.placement));
  }, [language, open, stepIndex, targetRect]);

  useEffect(() => {
    if (open && !locating && (dialogPosition || !step.target)) dialogRef.current?.focus();
  }, [dialogPosition, locating, open, step.target, stepIndex]);

  if (!open) return null;
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === STEPS.length - 1;
  const spotlightLeft = targetRect ? Math.max(targetRect.left - 6, 6) : 0;
  const spotlightTop = targetRect ? Math.max(targetRect.top - 6, 6) : 0;
  const arrowPosition = targetRect && dialogPosition && dialogPosition.side !== "center"
    ? placeArrow(targetRect, dialogPosition.side)
    : null;

  function finishTour() {
    window.localStorage.setItem(storageKey, "completed");
    closeTour();
  }
  function skipTour() {
    window.localStorage.setItem(storageKey, "skipped");
    closeTour();
  }

  return (
    <div className={`product-tour-overlay fixed inset-0 z-[9000] ${exiting ? "product-tour-overlay--exit" : ""}`} aria-live="polite">
      <div
        className="product-tour-spotlight pointer-events-none fixed rounded-xl transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:duration-0"
        style={{
          height: targetRect
            ? Math.max(Math.min(targetRect.bottom + 6, window.innerHeight - 6) - spotlightTop, 24)
            : 1,
          left: targetRect ? spotlightLeft : -24,
          top: targetRect ? spotlightTop : -24,
          width: targetRect
            ? Math.max(Math.min(targetRect.right + 6, window.innerWidth - 6) - spotlightLeft, 24)
            : 1,
        }}
        aria-hidden="true"
      />
      {arrowPosition ? (
        <span
          className="product-tour-arrow pointer-events-none fixed grid h-[34px] w-[34px] place-items-center rounded-full transition-[left,top,transform] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:duration-0"
          style={arrowPosition}
          aria-hidden="true"
        >
          <svg className="product-tour-arrow__icon h-5 w-5" viewBox="0 0 24 24" fill="none">
            <path d="M4 12h15M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      ) : null}

      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="product-tour-title"
        tabIndex={-1}
        className={`app-card fixed w-[min(25rem,calc(100vw-2rem))] rounded-2xl border p-5 shadow-2xl outline-none ${
          step.id === "welcome"
            ? "product-tour-dialog--welcome"
            : "transition-[left,top,opacity] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:duration-0"
        }`}
        style={dialogPosition
          ? { left: dialogPosition.left, top: dialogPosition.top, visibility: "visible" }
          : { left: 16, top: 16, visibility: "hidden" }}
      >
        <div className="mb-4 flex items-center justify-between gap-4">
          <span className="rounded-full bg-[var(--color-primary-soft)] px-3 py-1 text-xs font-bold text-[var(--color-primary-soft-text)]">
            {language === "tr" ? `Adım ${stepIndex + 1} / ${STEPS.length}` : `Step ${stepIndex + 1} / ${STEPS.length}`}
          </span>
          <button type="button" onClick={skipTour} className="text-sm font-medium app-muted hover:underline">
            {language === "tr" ? "Turu geç" : "Skip tour"}
          </button>
        </div>
        <h2 id="product-tour-title" className="text-xl font-bold app-heading">{step.title[language]}</h2>
        <p className="mt-2 text-sm leading-6 app-muted">
          {locating ? (language === "tr" ? "İlgili bölüm hazırlanıyor…" : "Preparing this section…") : step.description[language]}
        </p>
        <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-[var(--color-border-soft)]">
          <div className="h-full rounded-full bg-[var(--color-primary)] transition-[width] duration-300" style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }} />
        </div>
        <div className="mt-5 flex items-center justify-between gap-3">
          <button type="button" disabled={isFirst || locating} onClick={() => setStepIndex((current) => current - 1)} className="rounded-lg border app-border px-4 py-2 text-sm font-semibold app-heading transition hover:bg-[var(--color-surface-muted)] disabled:cursor-not-allowed disabled:opacity-40">
            {language === "tr" ? "Geri" : "Back"}
          </button>
          <button type="button" disabled={locating} onClick={() => isLast ? finishTour() : setStepIndex((current) => current + 1)} className="rounded-lg bg-[var(--color-primary)] px-5 py-2 text-sm font-bold text-[var(--color-on-primary)] transition hover:bg-[var(--color-primary-hover)] disabled:cursor-wait disabled:opacity-60">
            {isLast ? (language === "tr" ? "Turu tamamla" : "Finish tour") : (language === "tr" ? "İleri" : "Next")}
          </button>
        </div>
      </div>
    </div>
  );
}
