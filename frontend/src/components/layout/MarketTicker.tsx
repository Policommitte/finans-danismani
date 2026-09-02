"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { useLanguage } from "../../contexts/LanguageContext";
import type { PublicMarketTickerItem } from "../../models/market";
import { getPublicMarketTicker } from "../../services/marketService";
import { ThemeToggle } from "../ui/ThemeToggle";
import { GlobalSearch } from "./GlobalSearch";
import { MARKET_TICKER_READY_EVENT } from "./transitionEvents";

let cachedTickerItems: PublicMarketTickerItem[] = [];

const fallbackTickerItems: PublicMarketTickerItem[] = [
  { symbol: "BIST100", label: "BIST 100", value: 10842.36, currency: "TRY", change_percent: 0.84, source: "fallback" },
  { symbol: "USDTRY", label: "USD/TRY", value: 42.18, currency: "TRY", change_percent: 0.12, source: "fallback" },
  { symbol: "EURTRY", label: "EUR/TRY", value: 45.62, currency: "TRY", change_percent: -0.2, source: "fallback" },
  { symbol: "XAUTRY", label: "Gram Altın", value: 3918, currency: "TRY", change_percent: 1.24, source: "fallback" },
  { symbol: "BTC", label: "BTC", value: 2184306, currency: "TRY", change_percent: 2.1, source: "fallback" },
  { symbol: "THYAO", label: "THYAO", value: 312.5, currency: "TRY", change_percent: 1.16, source: "fallback" },
];

// Onceki CSS `@keyframes ticker-marquee` ile ayni his: yarim tur (bir set
// oge) 28 saniyede tamamlaniyordu. Suruklemeyle rF-tabanli bir konuma
// gecince de ayni hizi korumak icin ayni sureyi kullaniyoruz.
const LOOP_DURATION_SECONDS = 28;
const HOVER_SPEED_MULTIPLIER = 0.25;
const DRAG_CLICK_THRESHOLD_PX = 4;

function formatValue(item: PublicMarketTickerItem, language: "tr" | "en"): string {
  return new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    maximumFractionDigits: item.value > 1000 ? 0 : 4,
    minimumFractionDigits: item.value > 1000 ? 0 : 2,
  }).format(item.value);
}

export function MarketTicker({
  onSelect,
  onLogout,
  isAuthenticated,
}: {
  onSelect: (symbol: string) => void;
  onLogout: () => void;
  isAuthenticated: boolean;
}) {
  const [items, setItems] = useState<PublicMarketTickerItem[]>(() => cachedTickerItems);
  const [isDragging, setIsDragging] = useState(false);
  const { language, toggleLanguage } = useLanguage();

  const trackRef = useRef<HTMLDivElement | null>(null);
  const offsetRef = useRef(0);
  const halfWidthRef = useRef(0);
  const draggingRef = useRef(false);
  const hoveringRef = useRef(false);
  const draggedPastThresholdRef = useRef(false);
  const dragStartXRef = useRef(0);
  const dragStartOffsetRef = useRef(0);
  const lastFrameRef = useRef<number | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await getPublicMarketTicker();
        if (active && response.items.length > 0) {
          cachedTickerItems = response.items;
          setItems(response.items);
        }
      } catch {
        if (active) {
          setItems((current) => (current.length > 0 ? current : fallbackTickerItems));
        }
      }
    }

    void load();
    const timer = window.setInterval(load, 60000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const displayItems = items.length > 0 ? [...items, ...items] : [];

  // Bir set ogenin gercek genisligini olc (dizi ikiye katlanmis durumda,
  // dolayisiyla scrollWidth/2 = kesintisiz donguyu tamamlayan mesafe).
  useEffect(() => {
    function measure() {
      if (trackRef.current) {
        halfWidthRef.current = trackRef.current.scrollWidth / 2;
      }
    }
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [displayItems.length]);

  // Otomatik kayma: fare uzerindeyken tamamen durmak yerine yavaslar;
  // suruklerken kullanici pointermove'da offset'i dogrudan gunceller ve
  // otomatik hareket gecici olarak durur.
  useEffect(() => {
    let rafId: number;

    function frame(timestamp: number) {
      if (lastFrameRef.current === null) {
        lastFrameRef.current = timestamp;
      }
      const deltaSeconds = (timestamp - lastFrameRef.current) / 1000;
      lastFrameRef.current = timestamp;

      const halfWidth = halfWidthRef.current;
      if (!draggingRef.current && halfWidth > 0) {
        const speedMultiplier = hoveringRef.current ? HOVER_SPEED_MULTIPLIER : 1;
        const speed = (halfWidth / LOOP_DURATION_SECONDS) * speedMultiplier;
        offsetRef.current -= speed * deltaSeconds;
        if (offsetRef.current <= -halfWidth) {
          offsetRef.current += halfWidth;
        }
      }

      if (trackRef.current) {
        trackRef.current.style.transform = `translateX(${offsetRef.current}px)`;
      }

      rafId = requestAnimationFrame(frame);
    }

    rafId = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(rafId);
  }, []);

  function wrapOffset(value: number): number {
    const halfWidth = halfWidthRef.current;
    if (halfWidth <= 0) {
      return value;
    }
    let wrapped = value;
    while (wrapped <= -halfWidth) {
      wrapped += halfWidth;
    }
    while (wrapped > 0) {
      wrapped -= halfWidth;
    }
    return wrapped;
  }

  function handlePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (halfWidthRef.current <= 0) {
      return;
    }
    draggingRef.current = true;
    draggedPastThresholdRef.current = false;
    setIsDragging(true);
    dragStartXRef.current = event.clientX;
    dragStartOffsetRef.current = offsetRef.current;
  }

  function handlePointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (!draggingRef.current) {
      return;
    }
    const delta = event.clientX - dragStartXRef.current;
    if (!draggedPastThresholdRef.current && Math.abs(delta) > DRAG_CLICK_THRESHOLD_PX) {
      draggedPastThresholdRef.current = true;
      // Pointer capture'i ancak gercek bir surukleme baslayinca devreye
      // aliyoruz: pointerdown aninda capture edilirse, dokunmadan/hareket
      // etmeden yapilan duz bir tikin ureteceigi click olayi da bu
      // elemente yonlendiriliyor ve altindaki butona hic ulasamiyor.
      event.currentTarget.setPointerCapture(event.pointerId);
    }
    offsetRef.current = wrapOffset(dragStartOffsetRef.current + delta);
  }

  function endDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (!draggingRef.current) {
      return;
    }
    draggingRef.current = false;
    setIsDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function handlePointerEnter(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.pointerType === "mouse") {
      hoveringRef.current = true;
    }
  }

  function handlePointerLeave(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.pointerType === "mouse") {
      hoveringRef.current = false;
    }
    endDrag(event);
  }

  function handleClickCapture(event: React.MouseEvent) {
    // Suruklemenin sonunda tarayicinin otomatik urettigi click'i bastir,
    // boylece bir sembolu suruklerken yanlislikla secmis olmayalim.
    if (draggedPastThresholdRef.current) {
      event.preventDefault();
      event.stopPropagation();
      draggedPastThresholdRef.current = false;
    }
  }

  useEffect(() => {
    if (items.length === 0) {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      document.documentElement.dataset.marketTickerReady = "true";
      window.dispatchEvent(new Event(MARKET_TICKER_READY_EVENT));
    });

    return () => window.cancelAnimationFrame(frame);
  }, [items.length]);

  return (
    <section className="fixed left-24 right-0 top-0 z-[80] bg-[var(--color-market-bar)] text-[var(--color-market-text)]">
      <Link href="/" className="absolute left-0 top-1/2 hidden -translate-y-1/2 2xl:flex">
        <span
          aria-hidden="true"
          className="block h-12 w-28 bg-[var(--color-market-text)] [mask-image:url('/polifin-logo-clean.svg')] [mask-position:left_center] [mask-repeat:no-repeat] [mask-size:contain]"
        />
        <span className="sr-only">Polifin</span>
      </Link>

      <div className="flex min-h-20 w-full items-center gap-3 px-4 md:gap-4 2xl:pl-36 2xl:pr-6">
        <div className="relative min-w-0 flex-1 overflow-hidden py-3" data-tour="market-stream">
          <div
            ref={trackRef}
            className={`flex w-max touch-pan-y select-none ${isDragging ? "cursor-grabbing" : "cursor-grab"}`}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={endDrag}
            onPointerCancel={endDrag}
            onPointerEnter={handlePointerEnter}
            onPointerLeave={handlePointerLeave}
            onClickCapture={handleClickCapture}
          >
            {displayItems.map((item, index) => {
              const positive = (item.change_percent ?? 0) >= 0;
              return (
                <button
                  key={`${item.symbol}-${index}`}
                  type="button"
                  draggable={false}
                  onClick={() => onSelect(item.symbol)}
                  className="ticker-item flex min-w-48 shrink-0 items-center gap-3 border-l border-[var(--color-border)] px-6 text-left"
                >
                  <span>
                    <span className="block text-xs font-semibold text-[var(--color-market-muted)]">
                      {item.label.toLocaleUpperCase(language === "tr" ? "tr-TR" : "en-US")}
                    </span>
                    <span className="mt-1 block text-lg font-semibold">{formatValue(item, language)}</span>
                  </span>
                  <span className={`text-xs font-semibold ${positive ? "app-success" : "app-danger"}`}>
                    {item.change_percent == null
                      ? "-"
                      : `${positive ? "+" : ""}${item.change_percent.toFixed(2)}%`}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <GlobalSearch onSelectSymbol={onSelect} isAuthenticated={isAuthenticated} />

        <div className="flex shrink-0 items-center gap-3" data-tour="appearance-controls">
          <button
            type="button"
            aria-label={language === "tr" ? "Dili İngilizce yap" : "Switch language to Turkish"}
            onClick={toggleLanguage}
            className="flex h-10 w-12 items-center justify-center rounded-md border app-border app-surface text-sm font-black app-heading transition hover:opacity-80"
          >
            {language === "tr" ? "EN" : "TR"}
          </button>
          <ThemeToggle className="rounded-md" />
        </div>

        {isAuthenticated ? (
          <button
            type="button"
            onClick={onLogout}
            aria-label={language === "tr" ? "Çıkış" : "Logout"}
            title={language === "tr" ? "Çıkış" : "Logout"}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md border border-white/20 bg-white/[0.06] text-white/80 transition hover:border-white/35 hover:bg-white/10 hover:text-white"
          >
            <svg
              width="19"
              height="19"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.9"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3" />
              <path d="M15 17l5-5-5-5" />
              <path d="M20 12H9" />
            </svg>
          </button>
        ) : (
          <Link
            href="/login"
            className="flex h-11 w-20 shrink-0 items-center justify-center rounded-md border border-white/30 bg-white/[0.13] text-sm font-bold text-white shadow-sm transition hover:border-white/45 hover:bg-white/[0.18] md:w-24"
          >
            {language === "tr" ? "Giriş" : "Login"}
          </Link>
        )}
      </div>
    </section>
  );
}
