"use client";

import { thinking } from "blobatar/expression";
import "blobatar/motion.css";
import { Blobatar } from "blobatar/react";
import Link from "next/link";
import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { useChatStream } from "../../hooks/useChatStream";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

type ResizeDirection = "n" | "s" | "e" | "w" | "ne" | "nw" | "se" | "sw";
type PanelRect = { height: number; left: number; top: number; width: number };
type ResizeState = {
  direction: ResizeDirection;
  pointerX: number;
  pointerY: number;
  rect: PanelRect;
};

const PANEL_MIN_WIDTH = 320;
const PANEL_MIN_HEIGHT = 360;
const PANEL_VIEWPORT_MARGIN = 12;
const PANEL_TOP_BOUNDARY = 80;
const PANEL_DEFAULT_RIGHT = 20;
const PANEL_DEFAULT_BOTTOM = 116;
const PANEL_SIZE_STORAGE_KEY = "polifin-chat-panel-size-v1";

const resizeHandles: Array<{ direction: ResizeDirection; className: string }> = [
  { direction: "n", className: "left-3 right-3 top-0 h-2 cursor-ns-resize" },
  { direction: "s", className: "bottom-0 left-3 right-3 h-2 cursor-ns-resize" },
  { direction: "e", className: "bottom-3 right-0 top-3 w-2 cursor-ew-resize" },
  { direction: "w", className: "bottom-3 left-0 top-3 w-2 cursor-ew-resize" },
  { direction: "ne", className: "right-0 top-0 h-3 w-3 cursor-nesw-resize" },
  { direction: "nw", className: "left-0 top-0 h-3 w-3 cursor-nwse-resize" },
  { direction: "se", className: "bottom-0 right-0 h-3 w-3 cursor-nwse-resize" },
  { direction: "sw", className: "bottom-0 left-0 h-3 w-3 cursor-nesw-resize" },
];

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

export function ChatAvatar() {
  return (
    <span className="flex h-full w-full shrink-0 items-center justify-center overflow-hidden rounded-full bg-[var(--color-panel-dark)]">
      <span className="block h-[118%] w-[118%] [&_svg]:h-full [&_svg]:w-full">
        <Blobatar name="Aichatbot" traits={{ shape: 0.933 }} hue={225} expression={thinking} animate="hover" />
      </span>
    </span>
  );
}

export function ChatWidget({
  canSend = true,
  blockedMessage = "Soru sormadan önce giriş yapmalısınız.",
  open: controlledOpen,
  onOpenChange,
}: {
  canSend?: boolean;
  blockedMessage?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen ?? internalOpen;
  const [renderPanel, setRenderPanel] = useState(open);
  const [closing, setClosing] = useState(false);
  const [panelRect, setPanelRect] = useState<PanelRect | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);
  const resizeStateRef = useRef<ResizeState | null>(null);
  const latestPanelRectRef = useRef<PanelRect | null>(null);
  const chat = useChatStream();
  const messages = canSend ? chat.messages : [];

  useEffect(() => {
    if (open) {
      setRenderPanel(true);
      setClosing(false);
      return;
    }

    if (!renderPanel) {
      return;
    }

    setClosing(true);
    const timer = window.setTimeout(() => {
      setRenderPanel(false);
      setClosing(false);
    }, 170);

    return () => window.clearTimeout(timer);
  }, [open, renderPanel]);

  useEffect(() => {
    try {
      const savedValue = window.localStorage.getItem(PANEL_SIZE_STORAGE_KEY);
      if (!savedValue) {
        return;
      }

      const savedSize = JSON.parse(savedValue) as { height?: unknown; width?: unknown };
      if (
        typeof savedSize.width !== "number" ||
        typeof savedSize.height !== "number" ||
        !Number.isFinite(savedSize.width) ||
        !Number.isFinite(savedSize.height)
      ) {
        return;
      }

      const maximumWidth = window.innerWidth - PANEL_VIEWPORT_MARGIN * 2;
      const maximumHeight =
        window.innerHeight - PANEL_TOP_BOUNDARY - PANEL_VIEWPORT_MARGIN;
      const minimumWidth = Math.min(PANEL_MIN_WIDTH, maximumWidth);
      const minimumHeight = Math.min(PANEL_MIN_HEIGHT, maximumHeight);
      const width = clamp(savedSize.width, minimumWidth, maximumWidth);
      const height = clamp(savedSize.height, minimumHeight, maximumHeight);
      const restoredRect = {
        width,
        height,
        left: clamp(
          window.innerWidth - width - PANEL_DEFAULT_RIGHT,
          PANEL_VIEWPORT_MARGIN,
          window.innerWidth - width - PANEL_VIEWPORT_MARGIN,
        ),
        top: clamp(
          window.innerHeight - height - PANEL_DEFAULT_BOTTOM,
          PANEL_TOP_BOUNDARY,
          window.innerHeight - height - PANEL_VIEWPORT_MARGIN,
        ),
      };
      latestPanelRectRef.current = restoredRect;
      setPanelRect(restoredRect);
    } catch {
      // Bozuk veya tarayici tarafindan engellenmis kayit varsayilan boyutu bozmaz.
    }
  }, []);

  useEffect(() => {
    function keepPanelInsideViewport() {
      setPanelRect((current) => {
        if (!current) {
          return current;
        }

        const width = Math.min(current.width, window.innerWidth - PANEL_VIEWPORT_MARGIN * 2);
        const height = Math.min(
          current.height,
          window.innerHeight - PANEL_TOP_BOUNDARY - PANEL_VIEWPORT_MARGIN,
        );
        const nextRect = {
          width,
          height,
          left: clamp(
            current.left,
            PANEL_VIEWPORT_MARGIN,
            window.innerWidth - width - PANEL_VIEWPORT_MARGIN,
          ),
          top: clamp(
            current.top,
            PANEL_TOP_BOUNDARY,
            window.innerHeight - height - PANEL_VIEWPORT_MARGIN,
          ),
        };
        latestPanelRectRef.current = nextRect;
        return nextRect;
      });
    }

    keepPanelInsideViewport();
    window.addEventListener("resize", keepPanelInsideViewport);
    return () => window.removeEventListener("resize", keepPanelInsideViewport);
  }, []);

  function startResize(
    direction: ResizeDirection,
    event: ReactPointerEvent<HTMLDivElement>,
  ) {
    const panel = panelRef.current;
    if (!panel) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    const rect = panel.getBoundingClientRect();
    const nextRect = { height: rect.height, left: rect.left, top: rect.top, width: rect.width };
    latestPanelRectRef.current = nextRect;
    setPanelRect(nextRect);
    resizeStateRef.current = {
      direction,
      pointerX: event.clientX,
      pointerY: event.clientY,
      rect: nextRect,
    };
  }

  function resizePanel(event: ReactPointerEvent<HTMLDivElement>) {
    const resizeState = resizeStateRef.current;
    if (!resizeState) {
      return;
    }

    event.preventDefault();
    const deltaX = event.clientX - resizeState.pointerX;
    const deltaY = event.clientY - resizeState.pointerY;
    const minimumWidth = Math.min(PANEL_MIN_WIDTH, window.innerWidth - PANEL_VIEWPORT_MARGIN * 2);
    const minimumHeight = Math.min(
      PANEL_MIN_HEIGHT,
      window.innerHeight - PANEL_TOP_BOUNDARY - PANEL_VIEWPORT_MARGIN,
    );
    let left = resizeState.rect.left;
    let right = resizeState.rect.left + resizeState.rect.width;
    let top = resizeState.rect.top;
    let bottom = resizeState.rect.top + resizeState.rect.height;

    if (resizeState.direction.includes("e")) {
      right = clamp(
        right + deltaX,
        left + minimumWidth,
        window.innerWidth - PANEL_VIEWPORT_MARGIN,
      );
    }
    if (resizeState.direction.includes("w")) {
      left = clamp(left + deltaX, PANEL_VIEWPORT_MARGIN, right - minimumWidth);
    }
    if (resizeState.direction.includes("s")) {
      bottom = clamp(
        bottom + deltaY,
        top + minimumHeight,
        window.innerHeight - PANEL_VIEWPORT_MARGIN,
      );
    }
    if (resizeState.direction.includes("n")) {
      top = clamp(top + deltaY, PANEL_TOP_BOUNDARY, bottom - minimumHeight);
    }

    const nextRect = { height: bottom - top, left, top, width: right - left };
    latestPanelRectRef.current = nextRect;
    setPanelRect(nextRect);
  }

  function finishResize(event: ReactPointerEvent<HTMLDivElement>) {
    resizeStateRef.current = null;
    const latestRect = latestPanelRectRef.current;
    if (latestRect) {
      try {
        window.localStorage.setItem(
          PANEL_SIZE_STORAGE_KEY,
          JSON.stringify({ height: latestRect.height, width: latestRect.width }),
        );
      } catch {
        // Depolama kapaliysa panel mevcut oturumda yine boyutunu korur.
      }
    }
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function setOpen(nextOpen: boolean) {
    if (controlledOpen === undefined) {
      setInternalOpen(nextOpen);
    }
    onOpenChange?.(nextOpen);
  }

  function sendMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed || !canSend) {
      return;
    }

    chat.sendMessage(trimmed);
  }

  return (
    <div className="fixed bottom-5 right-5 z-40">
      {renderPanel && (
        <section
          ref={panelRef}
          style={panelRect ?? undefined}
          className={`${
            panelRect
              ? "fixed max-h-[calc(100vh-5.75rem)]"
              : "absolute bottom-24 right-0 h-[560px] max-h-[calc(100vh-12.25rem)] w-[380px]"
          } z-20 flex max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-lg border app-card shadow-2xl ${
            closing ? "chat-pop-out" : "chat-pop-in"
          }`}
        >
          <header className="flex items-center justify-between app-primary px-4 py-3">
            <div className="flex items-center gap-3">
              <span className="h-8 w-8">
                <ChatAvatar />
              </span>
              <div>
                <div className="font-semibold">Yatırım Asistanı</div>
                <div className="text-xs opacity-80">{chat.status ?? "Hazır"}</div>
              </div>
            </div>
            <button
              type="button"
              aria-label="Sohbeti kapat"
              className="rounded px-2 py-1 text-xl leading-none hover:opacity-80"
              onClick={() => setOpen(false)}
            >
              ×
            </button>
          </header>
          {chat.error && <div className="app-danger-box px-4 py-2 text-xs">{chat.error}</div>}
          <MessageList
            messages={messages}
            emptyState={
              canSend ? undefined : (
                <Link href="/login" className="font-semibold text-[var(--color-primary)] underline-offset-4 hover:underline">
                  {blockedMessage}
                </Link>
              )
            }
          />
          <MessageInput
            disabled={!canSend || chat.isStreaming}
            onSend={sendMessage}
            placeholder={canSend ? "Mesajınızı yazın" : "Giriş yapmanız gerekir"}
            buttonLabel="Gönder"
          />
          {resizeHandles.map((handle) => (
            <div
              key={handle.direction}
              aria-hidden="true"
              className={`absolute z-40 touch-none select-none ${handle.className}`}
              onPointerDown={(event) => startResize(handle.direction, event)}
              onPointerMove={resizePanel}
              onPointerUp={finishResize}
              onPointerCancel={finishResize}
            />
          ))}
          <span
            aria-hidden="true"
            className="pointer-events-none absolute bottom-1 right-1 z-30 h-2.5 w-2.5 border-b-2 border-r-2 border-[var(--color-muted)] opacity-40"
          />
        </section>
      )}
      <button
        type="button"
        data-tour="chat-assistant"
        className="relative z-30 h-16 w-16 rounded-full bg-[var(--color-panel-dark)] p-0 shadow-lg transition hover:-translate-y-0.5 hover:brightness-110"
        aria-label={open ? "Sohbeti kapat" : "Yatırım Asistanı'nı aç"}
        onClick={() => setOpen(!open)}
      >
        <ChatAvatar />
      </button>
    </div>
  );
}
