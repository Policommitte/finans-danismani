"use client";

import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { PublicMarketTickerItem } from "../../models/market";
import { getPublicMarketTicker } from "../../services/marketService";

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
const DRAG_CLICK_THRESHOLD_PX = 4;

function formatValue(item: PublicMarketTickerItem): string {
  const formatted = new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: item.value >= 1000 ? 0 : 2,
    maximumFractionDigits: item.value >= 1000 ? 0 : 2,
  }).format(item.value);

  if (item.currency === "TRY") {
    return `${formatted} ₺`;
  }

  return `${formatted} ${item.currency}`;
}

export function MarketTicker({ onSelect }: { onSelect: (symbol: string) => void }) {
  const [items, setItems] = useState<PublicMarketTickerItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);

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
          setItems(response.items);
        } else if (active) {
          setItems((current) => (current.length > 0 ? current : fallbackTickerItems));
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

  // Otomatik kayma: suruklenmiyor ve fare uzerinde degilken her karede
  // offset'i ilerletir; suruklerken kullanici pointermove'da offset'i
  // dogrudan gunceller, bu dongu sadece uygular.
  useEffect(() => {
    let rafId: number;

    function frame(timestamp: number) {
      if (lastFrameRef.current === null) {
        lastFrameRef.current = timestamp;
      }
      const deltaSeconds = (timestamp - lastFrameRef.current) / 1000;
      lastFrameRef.current = timestamp;

      const halfWidth = halfWidthRef.current;
      if (!draggingRef.current && !hoveringRef.current && halfWidth > 0) {
        const speed = halfWidth / LOOP_DURATION_SECONDS;
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

  return (
    <div className="overflow-hidden border-b border-black/10 bg-[var(--color-market-bar)]">
      <div
        ref={trackRef}
        className={`flex w-max touch-pan-y select-none gap-3 px-4 py-3 ${
          isDragging ? "cursor-grabbing" : "cursor-grab"
        }`}
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
              className="flex shrink-0 items-center gap-2 rounded-lg px-3 py-1 text-sm whitespace-nowrap transition hover:bg-white/10"
            >
              <b className="font-semibold text-[var(--color-market-text)]">{item.label}</b>
              <span className="text-[var(--color-market-muted)]">{formatValue(item)}</span>
              {item.change_percent != null && (
                <span className={`text-xs font-semibold ${positive ? "app-success" : "app-danger"}`}>
                  {positive ? "▲" : "▼"} {Math.abs(item.change_percent).toFixed(2)}%
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
