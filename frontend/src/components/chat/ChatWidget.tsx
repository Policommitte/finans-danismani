"use client";

import { thinking } from "blobatar/expression";
import "blobatar/motion.css";
import { Blobatar } from "blobatar/react";
import Link from "next/link";
import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { useLanguage } from "../../contexts/LanguageContext";
import { useChat } from "../../contexts/ChatContext";
import { useAuth } from "../../hooks/useAuth";
import { useDailyBrief } from "../../hooks/useDailyBrief";
import { useInvestmentPackageFlow } from "../../hooks/useInvestmentPackageFlow";
import type { ChatQuickReply } from "../../models/chat";
import type { PendingAttachment } from "./AttachmentMenu";
import { ConversationHistory } from "./ConversationHistory";
import { DailyBriefBubble } from "./DailyBriefBubble";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";
import { SuggestionStrip } from "./SuggestionStrip";

const HEADER_COPY = {
  tr: {
    title: "Yatırım Asistanı",
    ready: "Hazır",
    history: "Sohbet geçmişi",
    newChat: "Yeni sohbet",
    close: "Sohbeti kapat",
    open: "Yatırım Asistanı'nı aç",
    send: "Gönder",
    stop: "Durdur",
    placeholder: "Mesajınızı yazın (Shift+Enter: yeni satır)",
    loginRequired: "Giriş yapmanız gerekir",
    loadingHistory: "Sohbet yükleniyor…",
    welcome: "Portföyün, piyasa verileri veya risk durumun hakkında soru sorabilirsin.",
  },
  en: {
    title: "Investment Assistant",
    ready: "Ready",
    history: "Conversation history",
    newChat: "New chat",
    close: "Close chat",
    open: "Open the Investment Assistant",
    send: "Send",
    stop: "Stop",
    placeholder: "Type your message (Shift+Enter for a new line)",
    loginRequired: "You need to sign in",
    loadingHistory: "Loading conversation…",
    welcome: "Ask about your portfolio, market data or your risk profile.",
  },
} as const;

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
const PANEL_SIDEBAR_WIDTH = 96;
const PANEL_LEFT_BOUNDARY = PANEL_SIDEBAR_WIDTH + PANEL_VIEWPORT_MARGIN;
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

function getPanelLeftBoundary(viewportWidth: number): number {
  return Math.max(
    PANEL_VIEWPORT_MARGIN,
    Math.min(
      PANEL_LEFT_BOUNDARY,
      viewportWidth - PANEL_MIN_WIDTH - PANEL_VIEWPORT_MARGIN,
    ),
  );
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
  onSelectAsset,
}: {
  canSend?: boolean;
  blockedMessage?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** Cevapta bahsedilen varlik kartina tiklandiginda cagrilir - AppShell bunu
   * MarketTicker'in kullandigi AYNI `selectedSymbol` state'ine baglar, boylece
   * ayni AssetSummaryModal mekanizmasi calisir. */
  onSelectAsset?: (symbol: string) => void;
}) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen ?? internalOpen;
  const [renderPanel, setRenderPanel] = useState(open);
  const [closing, setClosing] = useState(false);
  const [panelRect, setPanelRect] = useState<PanelRect | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);
  const resizeStateRef = useRef<ResizeState | null>(null);
  const latestPanelRectRef = useRef<PanelRect | null>(null);
  const { language } = useLanguage();
  const copy = HEADER_COPY[language] ?? HEADER_COPY.tr;
  const chat = useChat();
  const [historyOpen, setHistoryOpen] = useState(false);
  const investmentFlow = useInvestmentPackageFlow({
    language,
    appendLocalMessage: chat.appendLocalMessage,
    updateMessage: chat.updateMessage,
  });
  const messages = canSend ? chat.messages : [];
  const auth = useAuth();
  const dailyBrief = useDailyBrief({
    enabled: canSend,
    userId: auth.user?.id ?? null,
    language,
  });
  //: Gunluk ozet OTURUM BASINA TEK KEZ istenir: davete tekrar tekrar
  //: tiklanamaz (baloncuk kapaniyor) ama panel kapanip acilirsa ayni
  //: istemin ikinci kez tum ajanlari kosturmasi da istenmez.
  const briefRequestedRef = useRef(false);

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

      const leftBoundary = getPanelLeftBoundary(window.innerWidth);
      const maximumWidth = window.innerWidth - leftBoundary - PANEL_VIEWPORT_MARGIN;
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
          leftBoundary,
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

        const leftBoundary = getPanelLeftBoundary(window.innerWidth);
        const width = Math.min(
          current.width,
          window.innerWidth - leftBoundary - PANEL_VIEWPORT_MARGIN,
        );
        const height = Math.min(
          current.height,
          window.innerHeight - PANEL_TOP_BOUNDARY - PANEL_VIEWPORT_MARGIN,
        );
        const nextRect = {
          width,
          height,
          left: clamp(
            current.left,
            leftBoundary,
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
    const leftBoundary = getPanelLeftBoundary(window.innerWidth);
    const minimumWidth = Math.min(
      PANEL_MIN_WIDTH,
      window.innerWidth - leftBoundary - PANEL_VIEWPORT_MARGIN,
    );
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
      left = clamp(left + deltaX, leftBoundary, right - minimumWidth);
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

  function sendMessage(message: string, attachment?: PendingAttachment) {
    const trimmed = message.trim();
    if ((!trimmed && !attachment) || !canSend) {
      return;
    }

    // While the guided investment flow is collecting answers, typed text is
    // an answer to its current question - it never reaches the chat backend.
    if (!attachment && investmentFlow.handleUserMessage(trimmed)) {
      return;
    }

    chat.sendMessage(trimmed, attachment);
  }

  function startNewConversation() {
    investmentFlow.reset();
    chat.startNewConversation();
    setHistoryOpen(false);
  }

  async function openConversation(conversationId: number) {
    investmentFlow.reset();
    setHistoryOpen(false);
    await chat.loadConversation(conversationId);
  }

  function selectQuickReply(reply: ChatQuickReply) {
    if (!canSend || chat.isStreaming) {
      return;
    }
    if (investmentFlow.handleQuickReply(reply)) {
      return;
    }
    chat.sendMessage(reply.message);
  }

  /** Davete tiklandi: panel acilir ve gunluk ozet istemi bir kez gonderilir. */
  function openDailyBrief() {
    const brief = dailyBrief.brief;
    dailyBrief.dismiss();
    setOpen(true);

    if (!brief || !canSend || briefRequestedRef.current) {
      return;
    }

    briefRequestedRef.current = true;
    chat.sendMessage(brief.prompt, undefined, { displayText: brief.displayText });
  }

  return (
    <>
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
                <div className="font-semibold">{copy.title}</div>
                <div className="text-xs opacity-80">
                  {chat.isLoadingHistory ? copy.loadingHistory : chat.status ?? copy.ready}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-0.5">
              {canSend && (
                <>
                  <button
                    type="button"
                    aria-label={copy.newChat}
                    title={copy.newChat}
                    className="rounded p-1.5 hover:bg-white/15 disabled:opacity-50"
                    onClick={startNewConversation}
                    disabled={chat.messages.length === 0 && !chat.conversationId}
                  >
                    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    aria-label={copy.history}
                    title={copy.history}
                    aria-pressed={historyOpen}
                    className={`rounded p-1.5 hover:bg-white/15 ${historyOpen ? "bg-white/20" : ""}`}
                    onClick={() => setHistoryOpen((current) => !current)}
                  >
                    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="9" />
                      <path d="M12 7v5l3 2" />
                    </svg>
                  </button>
                </>
              )}
              <button
                type="button"
                aria-label={copy.close}
                className="rounded px-2 py-1 text-xl leading-none hover:opacity-80"
                onClick={() => setOpen(false)}
              >
                ×
              </button>
            </div>
          </header>
          <ConversationHistory
            open={historyOpen && canSend}
            activeConversationId={chat.conversationId}
            language={language}
            onSelect={openConversation}
            onClose={() => setHistoryOpen(false)}
          />
          {chat.error && <div className="app-danger-box px-4 py-2 text-xs">{chat.error}</div>}
          <MessageList
            messages={messages}
            onSelectAsset={onSelectAsset}
            quickRepliesDisabled={chat.isStreaming}
            onQuickReply={selectQuickReply}
            onPackagePurchased={investmentFlow.notifyPurchased}
            emptyState={
              canSend ? (
                copy.welcome
              ) : (
                <Link href="/login" className="font-semibold text-[var(--color-primary)] underline-offset-4 hover:underline">
                  {blockedMessage}
                </Link>
              )
            }
          />
          <MessageInput
            disabled={!canSend || chat.isStreaming || chat.isLoadingHistory || investmentFlow.step === "building"}
            isStreaming={chat.isStreaming}
            onStop={chat.stopStreaming}
            onSend={sendMessage}
            placeholder={
              !canSend ? copy.loginRequired : investmentFlow.inputPlaceholder ?? copy.placeholder
            }
            buttonLabel={copy.send}
            stopLabel={copy.stop}
            leading={
              canSend && !investmentFlow.isActive ? (
                <SuggestionStrip
                  suggestions={investmentFlow.suggestions}
                  disabled={chat.isStreaming || chat.isLoadingHistory}
                  onSelect={selectQuickReply}
                />
              ) : undefined
            }
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
      {!open && dailyBrief.brief && (
        <DailyBriefBubble
          tone={dailyBrief.brief.tone}
          teaser={dailyBrief.brief.teaser}
          actionLabel={dailyBrief.brief.actionLabel}
          closeLabel={language === "tr" ? "Günün özetini kapat" : "Dismiss today's brief"}
          onOpen={openDailyBrief}
          onDismiss={dailyBrief.dismiss}
        />
      )}
      <button
        type="button"
        data-tour="chat-assistant"
        className="relative z-30 h-16 w-16 rounded-full bg-[var(--color-panel-dark)] p-0 shadow-lg transition hover:-translate-y-0.5 hover:brightness-110"
        aria-label={open ? copy.close : copy.open}
        onClick={() => setOpen(!open)}
      >
        <ChatAvatar />
      </button>
      </div>
    </>
  );
}
