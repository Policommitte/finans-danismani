"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChatWidget } from "../components/chat/ChatWidget";
import { useAuth } from "../hooks/useAuth";
import type { PublicMarketTickerItem } from "../models/market";
import { getPublicMarketTicker } from "../services/marketService";

type ThemeMode = "light" | "dark";
type Language = "tr" | "en";

const publicMenuTargets = [
  { key: "analysis", href: "/dashboard", icon: "/analiz.svg" },
  { key: "portfolio", href: "/portfolio", icon: "/portfoy.svg" },
  { key: "risk", href: "/risk", icon: "/risk.svg" },
  { key: "market", href: "/market", icon: "/piyasa.svg" },
];

const utilityMenuTargets = [
  { key: "profile", href: "/profile", icon: "/profil.svg" },
  { key: "settings", href: "/settings", icon: "/ayarlar.svg" },
];

const fallbackTickerItems: PublicMarketTickerItem[] = [
  { symbol: "USDTRY", label: "$/₺", value: 47.9128, currency: "TRY", change_percent: 0.02, source: "fallback" },
  { symbol: "EURTRY", label: "€/₺", value: 55.4919, currency: "TRY", change_percent: 0.07, source: "fallback" },
  { symbol: "GBPTRY", label: "£/₺", value: 64.8134, currency: "TRY", change_percent: -0.08, source: "fallback" },
  { symbol: "XAUUSD", label: "XAU/USD", value: 4458, currency: "USD", change_percent: 0.46, source: "fallback" },
  { symbol: "BTC", label: "BTC", value: 63583, currency: "USD", change_percent: 1.2, source: "fallback" },
  { symbol: "BIST100", label: "BIST 100", value: 14158, currency: "TRY", change_percent: 0.18, source: "fallback" },
];

function getStoredTheme(): ThemeMode {
  if (typeof window === "undefined") {
    return "light";
  }

  const htmlTheme = document.documentElement.dataset.theme;
  if (htmlTheme === "light" || htmlTheme === "dark") {
    return htmlTheme;
  }

  const savedTheme = window.localStorage.getItem("app-theme") ?? window.localStorage.getItem("landing-theme");
  if (savedTheme === "light" || savedTheme === "dark") {
    return savedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

const copy = {
  tr: {
    marketData: "Piyasa Verileri",
    home: "Ana Sayfa",
    login: "Giriş",
    authRequiredTitle: "Giriş gerekli",
    authRequiredBody: "Bu sayfaya gidebilmeniz için önce giriş yapmanız gerekir.",
    authRequiredAction: "Giriş yap",
    chatLoginRequired: "Soru sormadan önce giriş yapmalısınız.",
    close: "Kapat",
    utilityNav: ["Profil", "Ayarlar"],
    nav: ["Genel Bakış", "Portföy", "Risk", "Piyasa"],
    brand: "Finans Danışmanı",
    themeToLight: "Aydınlık moda geç",
    themeToDark: "Karanlık moda geç",
    languageLabel: "Dili İngilizce yap",
    features: [
      ["Dashboard", "Portföy toplam değeri ve piyasa özeti."],
      ["Portföy", "Varlık dağılımı, pozisyonlar ve işlem geçmişi."],
      ["Risk", "Risk skoru, gerekçeler ve aksiyon önerileri."],
      ["AI Asistan", "Sağ altta açılan sohbet widget'ı."],
    ],
    slides: [
      {
        key: "analysis",
        tab: "Analiz",
        eyebrow: "Dashboard ve risk görünümü",
        title: "Portföyünüzün anlık durumunu net görün.",
        body:
          "Toplam değer, kar-zarar, varlık dağılımı ve risk skoru dashboard üzerinde özetlenir. Kullanıcı portföyünün genel sağlığını hızlıca takip eder.",
        metrics: [
          ["Toplam değer", "1.09M TL"],
          ["Risk skoru", "61/100"],
          ["Dağılım", "STOCK %67"],
        ],
      },
      {
        key: "recommendations",
        tab: "Öneriler",
        eyebrow: "Haber araştırması ve öneri motoru",
        title: "Piyasa haberlerinden kişisel öneriler üretin.",
        body:
          "Piyasa araştırma ajanı haberleri ve finansal dokümanları tarar. Sistem bu bilgileri portföyünüzle birleştirerek kişisel yorum ve aksiyon önerileri çıkarır.",
        metrics: [
          ["RAG kaynakları", "Haber + rapor"],
          ["Sinyal", "Piyasa etkisi"],
          ["Çıktı", "Aksiyon önerisi"],
        ],
      },
      {
        key: "chat",
        tab: "Chatbot",
        eyebrow: "AI finans asistanı",
        title: "Sorularınızı sayfadan ayrılmadan chatbot ile sorun.",
        body:
          "Sağ altta duran sohbet aracı, kullanıcının sorusunu backend orchestrator akışına iletir. Ajanlardan gelen yanıtlar tek bir asistan cevabına dönüşür.",
        metrics: [
          ["Kanal", "SSE stream"],
          ["Akış", "Orchestrator"],
          ["Yan panel", "Global widget"],
        ],
      },
    ],
    visual: {
      assistant: "Finans asistanı",
      ready: "Hazır",
      chatQuestion: "THYAO portföyümde risk yaratır mı?",
      chatAnswer:
        "THYAO portföyünüzdeki en büyük pozisyon. Risk etkisi orta-yüksek seviyede. Haber akışı ve mevcut dağılım birlikte değerlendirildiğinde kademeli dengeleme önerilir.",
      chatInput: "Mesajınızı yazın",
      newsFlow: "Haber akışı",
      news: [
        "THYAO yolcu trafiği beklentilerin üzerinde",
        "Bankacılık endeksinde gün içi oynaklık arttı",
        "Küresel risk iştahı sınırlı toparlandı",
      ],
      personalRecommendation: "Kişisel öneri",
      recommendationTitle: "Portföy etkisi izlenmeli",
      recommendationBody:
        "Haber sinyali olumlu, ancak mevcut portföy ağırlığı yüksek olduğu için kademeli dengeleme daha güvenli görünür.",
      portfolioSummary: "Portföy özeti",
      riskScore: "Risk skoru",
      highRisk: "Yüksek risk",
      marketSignal: "Piyasa sinyali",
      marketSignalBody: "Haber akışı portföy ağırlığı ile birlikte izleniyor.",
    },
  },
  en: {
    marketData: "Market Data",
    home: "Home",
    login: "Login",
    authRequiredTitle: "Login required",
    authRequiredBody: "You need to log in before opening this page.",
    authRequiredAction: "Log in",
    chatLoginRequired: "You need to log in before asking a question.",
    close: "Close",
    utilityNav: ["Profile", "Settings"],
    nav: ["Analysis", "Portfolio", "Risk", "Market"],
    brand: "Finance Advisor",
    themeToLight: "Switch to light mode",
    themeToDark: "Switch to dark mode",
    languageLabel: "Switch language to Turkish",
    features: [
      ["Dashboard", "Portfolio total value and market summary."],
      ["Portfolio", "Asset allocation, positions and transaction history."],
      ["Risk", "Risk score, explanations and action recommendations."],
      ["AI Assistant", "Chat widget that opens from the bottom right."],
    ],
    slides: [
      {
        key: "analysis",
        tab: "Analysis",
        eyebrow: "Dashboard and risk view",
        title: "See your portfolio's current status clearly.",
        body:
          "Total value, profit/loss, asset allocation and risk score are summarized on the dashboard so users can quickly follow portfolio health.",
        metrics: [
          ["Total value", "1.09M TRY"],
          ["Risk score", "61/100"],
          ["Weight", "STOCK 67%"],
        ],
      },
      {
        key: "recommendations",
        tab: "Recommendations",
        eyebrow: "News research and recommendation engine",
        title: "Turn market news into personal recommendations.",
        body:
          "The market research agent scans news and financial documents. The system combines that context with your portfolio to generate personalized comments and action ideas.",
        metrics: [
          ["RAG sources", "News + reports"],
          ["Signal", "Market impact"],
          ["Output", "Action idea"],
        ],
      },
      {
        key: "chat",
        tab: "Chatbot",
        eyebrow: "AI finance assistant",
        title: "Ask questions with the chatbot without leaving the page.",
        body:
          "The bottom-right chat widget sends the user's question to the backend orchestrator flow. Agent outputs are merged into one assistant response.",
        metrics: [
          ["Channel", "SSE stream"],
          ["Flow", "Orchestrator"],
          ["Panel", "Global widget"],
        ],
      },
    ],
    visual: {
      assistant: "Finance assistant",
      ready: "Ready",
      chatQuestion: "Does THYAO increase my portfolio risk?",
      chatAnswer:
        "THYAO is your largest position. Its risk impact is medium-high. Considering the news flow and current allocation together, gradual rebalancing is recommended.",
      chatInput: "Type your message",
      newsFlow: "News flow",
      news: [
        "THYAO passenger traffic beats expectations",
        "Intraday volatility increased in the banking index",
        "Global risk appetite recovered slightly",
      ],
      personalRecommendation: "Personal recommendation",
      recommendationTitle: "Portfolio impact should be monitored",
      recommendationBody:
        "The news signal is positive, but because the current portfolio weight is high, gradual rebalancing appears safer.",
      portfolioSummary: "Portfolio summary",
      riskScore: "Risk score",
      highRisk: "High risk",
      marketSignal: "Market signal",
      marketSignalBody: "News flow is monitored together with portfolio weight.",
    },
  },
};

function formatValue(item: PublicMarketTickerItem, language: Language): string {
  return new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    maximumFractionDigits: item.value > 1000 ? 0 : 4,
    minimumFractionDigits: item.value > 1000 ? 0 : 2,
  }).format(item.value);
}

function displayUpper(value: string): string {
  return value.toLocaleUpperCase("en-US");
}

function MenuIcon({ src }: { src: string }) {
  return (
    <span
      aria-hidden="true"
      className="block h-8 w-8 shrink-0 bg-current [mask-position:center] [mask-repeat:no-repeat] [mask-size:contain]"
      style={{ maskImage: `url('${src}')`, WebkitMaskImage: `url('${src}')` }}
    />
  );
}

function AuthRequiredPopover({
  language,
  nextPath,
  onClose,
}: {
  language: Language;
  nextPath: string;
  onClose: () => void;
}) {
  return (
    <div
      role="status"
      className="absolute left-0 right-0 top-full z-[65] mt-2 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-left shadow-xl md:left-full md:right-auto md:top-0 md:ml-3 md:mt-0 md:w-72"
    >
      <div className="text-sm font-black app-heading">{copy[language].authRequiredTitle}</div>
      <p className="mt-2 text-sm leading-5 app-muted">{copy[language].authRequiredBody}</p>
      <div className="mt-4 flex items-center gap-2">
        <Link
          href={`/login?next=${encodeURIComponent(nextPath)}`}
          className="rounded-md app-primary px-3 py-2 text-xs font-bold"
        >
          {copy[language].authRequiredAction}
        </Link>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md border border-[var(--color-border)] px-3 py-2 text-xs font-bold app-muted transition hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-heading)]"
        >
          {copy[language].close}
        </button>
      </div>
    </div>
  );
}

function ThemeToggle({ theme, onToggle, language }: { theme: ThemeMode; onToggle: () => void; language: Language }) {
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      aria-label={isDark ? copy[language].themeToLight : copy[language].themeToDark}
      onClick={onToggle}
      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-md border transition ${
        isDark
          ? "border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-chart-yellow)] hover:opacity-80"
          : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)] hover:opacity-80"
      }`}
    >
      <span className="text-lg leading-none">{isDark ? "☀" : "☾"}</span>
    </button>
  );
}

function LanguageToggle({ language, onToggle }: { language: Language; onToggle: () => void }) {
  return (
    <button
      type="button"
      aria-label={copy[language].languageLabel}
      onClick={onToggle}
      className="flex h-10 w-12 shrink-0 items-center justify-center rounded-md border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-sm font-black text-[var(--color-heading)] transition hover:opacity-80"
    >
      {language === "tr" ? "EN" : "TR"}
    </button>
  );
}

function LandingSideMenu({
  open,
  language,
  authRequiredPath,
  onOpen,
  onClose,
  onNavigate,
  onAuthPopoverClose,
}: {
  open: boolean;
  language: Language;
  authRequiredPath: string | null;
  onOpen: () => void;
  onClose: () => void;
  onNavigate: (href: string) => void;
  onAuthPopoverClose: () => void;
}) {
  const menuRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      if (!menuRef.current || !(event.target instanceof Node)) {
        return;
      }

      if (!menuRef.current.contains(event.target)) {
        if (event.target instanceof Element && event.target.closest("[data-keep-sidebar-open]")) {
          return;
        }

        onClose();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [onClose, open]);

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/45 backdrop-blur-sm transition-opacity md:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
      />

      <aside
        ref={menuRef}
        onPointerDown={(event) => {
          if (!authRequiredPath || !(event.target instanceof Element)) {
            return;
          }

          if (!event.target.closest("button,a,[role='status']")) {
            onAuthPopoverClose();
          }
        }}
        className={`fixed bottom-0 left-0 top-0 z-50 flex flex-col overflow-visible border-r border-[var(--color-border)] shadow-2xl transition-[width,padding] duration-500 ease-in-out ${
          open
            ? "w-80 max-w-[86vw] bg-[var(--color-market-bar)] px-6 py-6"
            : "w-24 bg-[var(--color-market-bar)] px-6 py-6"
        }`}
      >
        <button
          type="button"
          aria-label={open ? "Menuyu kapat" : "Menuyu ac"}
          aria-expanded={open}
          onClick={open ? onClose : onOpen}
          className="absolute right-0 top-1/2 flex h-14 w-9 translate-x-full -translate-y-1/2 items-center justify-center rounded-r-full border border-l-0 border-white/10 bg-gradient-to-br from-[#4f7cff] via-[#6366f1] to-[#7c5cff] text-lg font-medium leading-none text-white shadow-[0_10px_24px_rgba(79,124,255,0.35)] transition hover:brightness-110"
        >
          <span className="translate-y-[-1px]">{open ? "<" : ">"}</span>
        </button>

        <div aria-hidden="true" className="h-20" />

        <nav className="mt-10 space-y-3">
          <Link
            href="/"
            onClick={onClose}
            aria-current="page"
            className={`group relative flex h-16 items-center overflow-visible rounded-md border font-black tracking-wide transition-all duration-500 ease-in-out ${
              open
                ? "w-full gap-4 border-white/15 bg-white/10 px-4 pl-5 text-base text-white"
                : "w-full border-white/15 bg-white/10 px-0 text-white/80"
            }`}
          >
            {open ? <span className="absolute bottom-3 left-0 top-3 w-1 rounded-r-full bg-[var(--color-primary)]" /> : null}
            <span className="absolute left-2 top-1/2 -translate-y-1/2">
              <MenuIcon src="/ana-sayfa.svg" />
            </span>
            <span
              className={`ml-12 min-w-0 whitespace-nowrap transition-[max-width,opacity,transform] duration-300 ease-out ${
                open ? "max-w-44 translate-x-0 opacity-100" : "max-w-0 -translate-x-2 overflow-hidden opacity-0"
              }`}
            >
              {copy[language].home}
            </span>
            {!open ? (
              <span className="pointer-events-none absolute left-full top-1/2 z-[70] ml-3 -translate-y-1/2 rounded-md bg-[var(--color-surface)] px-3 py-2 text-xs font-bold text-[var(--color-heading)] opacity-0 shadow-lg transition-opacity delay-700 group-hover:opacity-100">
                {copy[language].home}
              </span>
            ) : null}
          </Link>
          {publicMenuTargets.map((target, index) => (
            <div key={target.key} className="group relative">
              {authRequiredPath === target.href ? (
                <AuthRequiredPopover
                  language={language}
                  nextPath={target.href}
                  onClose={onAuthPopoverClose}
                />
              ) : null}
              <button
                type="button"
                onClick={() => onNavigate(target.href)}
                className={`relative flex h-16 items-center overflow-visible rounded-md border font-black tracking-wide transition-all duration-500 ease-in-out hover:border-white/30 hover:bg-white/15 hover:text-white ${
                  open
                    ? "w-full gap-4 border-white/10 bg-white/[0.06] px-4 text-left text-base text-white/90"
                    : "w-full border-white/10 bg-white/[0.06] px-0 text-white/70"
                }`}
              >
                <span className="absolute left-2 top-1/2 -translate-y-1/2">
                  <MenuIcon src={target.icon} />
                </span>
                <span
                  className={`ml-12 min-w-0 whitespace-nowrap transition-[max-width,opacity,transform] duration-300 ease-out ${
                    open ? "max-w-44 translate-x-0 opacity-100" : "max-w-0 -translate-x-2 overflow-hidden opacity-0"
                  }`}
                >
                  {copy[language].nav[index]}
                </span>
              </button>
              {!open ? (
                <span className="pointer-events-none absolute left-full top-1/2 z-[70] ml-3 -translate-y-1/2 rounded-md bg-[var(--color-surface)] px-3 py-2 text-xs font-bold text-[var(--color-heading)] opacity-0 shadow-lg transition-opacity delay-700 group-hover:opacity-100">
                  {copy[language].nav[index]}
                </span>
              ) : null}
            </div>
          ))}
        </nav>

        <div className="mt-auto space-y-3 pt-6">
          {utilityMenuTargets.map((target, index) => (
            <div key={target.key} className="group relative">
              {authRequiredPath === target.href ? (
                <AuthRequiredPopover
                  language={language}
                  nextPath={target.href}
                  onClose={onAuthPopoverClose}
                />
              ) : null}
              <button
                type="button"
                onClick={() => onNavigate(target.href)}
                className={`relative flex h-16 items-center overflow-visible rounded-md border font-black tracking-wide transition-all duration-500 ease-in-out hover:border-white/30 hover:bg-white/15 hover:text-white ${
                  open
                    ? "w-full gap-4 border-white/10 bg-white/[0.06] px-4 text-left text-sm text-white/90"
                    : "w-full border-white/10 bg-white/[0.06] px-0 text-white/70"
                }`}
              >
                <span className="absolute left-2 top-1/2 -translate-y-1/2">
                  <MenuIcon src={target.icon} />
                </span>
                <span
                  className={`ml-12 min-w-0 whitespace-nowrap transition-[max-width,opacity,transform] duration-300 ease-out ${
                    open ? "max-w-44 translate-x-0 opacity-100" : "max-w-0 -translate-x-2 overflow-hidden opacity-0"
                  }`}
                >
                  {copy[language].utilityNav[index]}
                </span>
              </button>
              {!open ? (
                <span className="pointer-events-none absolute left-full top-1/2 z-[70] ml-3 -translate-y-1/2 rounded-md bg-[var(--color-surface)] px-3 py-2 text-xs font-bold text-[var(--color-heading)] opacity-0 shadow-lg transition-opacity delay-700 group-hover:opacity-100">
                  {copy[language].utilityNav[index]}
                </span>
              ) : null}
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}

function MarketTicker({
  theme,
  language,
  onThemeToggle,
  onLanguageToggle,
}: {
  theme: ThemeMode;
  language: Language;
  onThemeToggle: () => void;
  onLanguageToggle: () => void;
}) {
  const [items, setItems] = useState<PublicMarketTickerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const displayItems = items.length > 0 ? [...items, ...items] : [];

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await getPublicMarketTicker();
        if (active) {
          setItems(response.items);
        }
      } catch {
        if (active) {
          setItems((currentItems) => (currentItems.length > 0 ? currentItems : fallbackTickerItems));
        }
      } finally {
        if (active) {
          setLoading(false);
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

  return (
    <section className="relative bg-[var(--color-market-bar)] text-[var(--color-market-text)]">
      <Link href="/" className="absolute left-2 top-1/2 hidden -translate-y-1/2 2xl:flex">
        <span
          aria-hidden="true"
          className="block h-12 w-48 bg-[var(--color-market-text)] [mask-image:url('/polifin-logo-clean.svg')] [mask-position:center] [mask-repeat:no-repeat] [mask-size:contain]"
        />
        <span className="sr-only">{copy[language].brand}</span>
      </Link>
      <div className="flex min-h-20 w-full items-center gap-4 px-4 md:gap-6 2xl:pl-60 2xl:pr-14">
        <div className="hidden shrink-0 items-center gap-2 text-sm font-semibold tracking-wide text-[var(--color-market-muted)] md:flex">
          <span
            className="h-2 w-2 rotate-45 bg-[var(--color-accent)]"
          />
          {displayUpper(copy[language].marketData)}
        </div>
        <div className="relative min-w-0 flex-1 overflow-hidden py-3">
          {loading && items.length === 0 ? (
            <div className="flex gap-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="h-12 w-40 shrink-0 animate-pulse rounded-md bg-[var(--color-overlay-soft)]" />
              ))}
            </div>
          ) : (
            <div className="ticker-track flex w-max gap-3">
              {displayItems.map((item, index) => {
                const positive = (item.change_percent ?? 0) >= 0;
                return (
                  <div
                    key={`${item.symbol}-${index}`}
                    className="flex min-w-48 shrink-0 items-center gap-3 border-l border-[var(--color-border)] pl-6"
                  >
                    <div>
                      <div className="text-xs font-semibold text-[var(--color-market-muted)]">{displayUpper(item.label)}</div>
                      <div className="mt-1 text-lg font-semibold">{formatValue(item, language)}</div>
                    </div>
                    <div className={`text-xs font-semibold ${positive ? "app-success" : "app-danger"}`}>
                      {item.change_percent == null ? "-" : `${positive ? "+" : ""}${item.change_percent.toFixed(2)}%`}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        <Link
          href="/login"
          className="shrink-0 rounded-none bg-[var(--color-cta)] px-6 py-7 text-sm font-bold text-[var(--color-market-text)] transition hover:bg-[var(--color-cta-hover)] md:px-8"
        >
          {copy[language].login}
        </Link>
        <div data-keep-sidebar-open className="flex shrink-0 items-center gap-3">
          <ThemeToggle theme={theme} language={language} onToggle={onThemeToggle} />
          <LanguageToggle language={language} onToggle={onLanguageToggle} />
        </div>
      </div>
    </section>
  );
}

function HeroVisual({ slideKey, language }: { slideKey: string; language: Language }) {
  const visual = copy[language].visual;

  if (slideKey === "chat") {
    return (
      <div
        className="relative min-h-96 overflow-hidden rounded-md bg-[var(--color-panel-dark)] p-6 text-[var(--color-market-text)] shadow-xl"
      >
        <div className="mb-5 flex items-center justify-between border-b border-[var(--color-border)] pb-4">
          <div>
            <div className="text-sm font-bold">{visual.assistant}</div>
            <div className="text-xs app-success">{visual.ready}</div>
          </div>
          <div className="text-2xl leading-none">x</div>
        </div>
        <div className="ml-auto max-w-72 rounded-md app-primary px-4 py-3 text-sm font-semibold">
          {visual.chatQuestion}
        </div>
        <div className="mt-5 max-w-96 rounded-md bg-[var(--color-overlay-strong)] p-5 text-sm leading-6 text-[var(--color-market-text)] ring-1 ring-[var(--color-border)]">
          {visual.chatAnswer}
        </div>
        <div className="absolute bottom-6 left-6 right-6 flex h-11 items-center rounded-md border border-[var(--color-border)] bg-[var(--color-overlay-soft)] px-4 text-sm text-[var(--color-on-primary-muted)]">
          {visual.chatInput}
        </div>
      </div>
    );
  }

  if (slideKey === "recommendations") {
    return (
      <div className="relative min-h-80 overflow-hidden rounded-md bg-[var(--color-panel-dark)] p-6 text-[var(--color-market-text)] shadow-xl">
        <div className="grid gap-4 md:grid-cols-[0.9fr_1fr]">
          <div className="space-y-4">
            <div className="rounded-md bg-[var(--color-overlay-soft)] p-5">
              <div className="text-xs font-bold text-[var(--color-on-primary-muted)]">{displayUpper(visual.newsFlow)}</div>
              <div className="mt-4 space-y-3 text-sm text-[var(--color-market-text)]">
                {visual.news.map((newsItem) => (
                  <div key={newsItem} className="rounded-md bg-[var(--color-overlay-soft)] p-3">
                    {newsItem}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="rounded-md bg-[var(--color-surface)] p-5 text-[var(--color-text)]">
            <div className="text-xs font-bold app-muted">{displayUpper(visual.personalRecommendation)}</div>
            <div className="mt-4 text-xl font-black">{visual.recommendationTitle}</div>
            <p className="mt-3 text-sm leading-6 app-muted">
              {visual.recommendationBody}
            </p>
            <div className="mt-5 h-2 w-full rounded-full app-card-muted">
              <div className="h-2 w-3/4 rounded-full bg-[var(--color-success)]" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-80 overflow-hidden rounded-md app-card-muted p-6 shadow-xl">
      <div className="grid gap-4 md:grid-cols-[1fr_0.8fr]">
        <div className="rounded-md app-card p-5 shadow-sm">
          <div className="text-xs font-bold app-muted">{displayUpper(visual.portfolioSummary)}</div>
          <div className="mt-4 text-3xl font-black app-heading">1.09M TL</div>
          <div className="mt-2 text-sm font-semibold app-danger">-27.80% kar/zarar</div>
          <div className="mt-6 space-y-3">
            <div className="h-3 w-full rounded-full app-card-muted">
              <div className="h-3 w-2/3 rounded-full bg-[var(--color-primary)]" />
            </div>
            <div className="h-3 w-full rounded-full app-card-muted">
              <div className="h-3 w-1/3 rounded-full bg-[var(--color-accent)]" />
            </div>
            <div className="h-3 w-full rounded-full app-card-muted">
              <div className="h-3 w-1/2 rounded-full bg-[var(--color-success)]" />
            </div>
          </div>
        </div>
        <div className="space-y-4">
          <div className="rounded-md bg-[var(--color-panel-dark)] p-5 text-[var(--color-market-text)]">
            <div className="text-xs font-bold text-[var(--color-on-primary-muted)]">{displayUpper(visual.riskScore)}</div>
            <div className="mt-3 text-4xl font-black">61</div>
            <div className="text-sm text-[var(--color-on-primary-muted)]">{visual.highRisk}</div>
          </div>
          <div className="rounded-md app-card p-5 shadow-sm">
            <div className="text-xs font-bold app-muted">{displayUpper(visual.marketSignal)}</div>
            <div className="mt-3 text-sm font-semibold app-heading">
              {visual.marketSignalBody}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function HeroSlider({ language }: { language: Language }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const slides = copy[language].slides;

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % slides.length);
    }, 5000);

    return () => window.clearInterval(timer);
  }, [slides.length]);

  return (
    <section className="mx-auto max-w-7xl px-4 pb-20 pt-10">
      <div className="overflow-hidden">
        <div
          className="flex w-full transition-transform duration-700 ease-in-out"
          style={{ transform: `translate3d(-${activeIndex * 100}%, 0, 0)` }}
        >
          {slides.map((slide) => (
            <div
              key={slide.key}
              className="grid w-full max-w-full flex-none basis-full shrink-0 grow-0 items-start gap-10 overflow-hidden lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]"
            >
              <div className="min-w-0 flex min-h-[420px] flex-col justify-center">
                <div className="min-h-[270px]">
                  <p className="mb-4 text-sm font-bold tracking-wide app-primary-text">
                    {displayUpper(slide.eyebrow)}
                  </p>
                  <h1 className="max-w-4xl text-5xl font-black leading-tight app-heading md:text-6xl">
                    {slide.title}
                  </h1>
                  <p className="mt-6 max-w-2xl text-lg leading-8 app-muted">
                    {slide.body}
                  </p>
                </div>
                <div className="grid min-w-0 max-w-2xl gap-3 sm:grid-cols-3">
                  {slide.metrics.map(([label, value]) => (
                    <div
                      key={label}
                      className="rounded-md border app-card p-4"
                    >
                      <div className="text-xs font-bold app-muted">{displayUpper(label)}</div>
                      <div className="mt-2 text-lg font-black app-heading">{value}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="min-w-0">
                <HeroVisual slideKey={slide.key} language={language} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        {slides.map((slide, index) => (
          <button
            key={`${slide.key}-dot`}
            type="button"
            aria-label={`${slide.tab} ${language === "tr" ? "slaydına geç" : "slide"}`}
            onClick={() => setActiveIndex(index)}
            className={`h-3 w-3 rounded-full transition ${
              activeIndex === index ? "bg-[var(--color-heading)]" : "bg-[var(--color-border)]"
            }`}
          />
        ))}
      </div>
    </section>
  );
}

export default function HomePage() {
  const auth = useAuth();
  const router = useRouter();
  const [theme, setTheme] = useState<ThemeMode>("light");
  const [language, setLanguage] = useState<Language>("tr");
  const [menuOpen, setMenuOpen] = useState(false);
  const [authRequiredPath, setAuthRequiredPath] = useState<string | null>(null);

  useEffect(() => {
    const savedLanguage = window.localStorage.getItem("landing-language");
    setTheme(getStoredTheme());

    if (savedLanguage === "tr" || savedLanguage === "en") {
      setLanguage(savedLanguage);
    }
  }, []);

  function toggleTheme() {
    setTheme((current) => {
      const nextTheme = current === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = nextTheme;
      window.localStorage.setItem("app-theme", nextTheme);
      return nextTheme;
    });
  }

  function toggleLanguage() {
    setLanguage((current) => {
      const nextLanguage = current === "tr" ? "en" : "tr";
      window.localStorage.setItem("landing-language", nextLanguage);
      return nextLanguage;
    });
  }

  function handleProtectedNavigate(href: string) {
    if (auth.loading) {
      return;
    }

    if (auth.user) {
      setMenuOpen(false);
      setAuthRequiredPath(null);
      router.push(href);
      return;
    }

    setAuthRequiredPath(href);
  }

  function closeMenu() {
    setMenuOpen(false);
    setAuthRequiredPath(null);
  }

  return (
    <main className="min-h-screen overflow-x-hidden app-bg transition-colors">
      <LandingSideMenu
        open={menuOpen}
        language={language}
        authRequiredPath={authRequiredPath}
        onOpen={() => setMenuOpen(true)}
        onClose={closeMenu}
        onNavigate={handleProtectedNavigate}
        onAuthPopoverClose={() => setAuthRequiredPath(null)}
      />

      <div
        className={`transition-[margin,width] duration-500 ease-in-out ${
          menuOpen ? "ml-80 w-[calc(100%-20rem)]" : "ml-24 w-[calc(100%-6rem)]"
        }`}
      >
        <MarketTicker
          theme={theme}
          language={language}
          onThemeToggle={toggleTheme}
          onLanguageToggle={toggleLanguage}
        />

        <HeroSlider language={language} />

        <section
          id="ozellikler"
          className="border-t app-border app-card-muted py-14"
        >
          <div className="mx-auto grid max-w-7xl gap-4 px-4 md:grid-cols-4">
            {copy[language].features.map(([title, text]) => (
              <div
                key={title}
                className="rounded-md border app-card p-5"
              >
                <div className="text-lg font-bold app-heading">{title}</div>
                <p className="mt-2 text-sm leading-6 app-muted">{text}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <ChatWidget canSend={Boolean(auth.user)} blockedMessage={copy[language].chatLoginRequired} />
    </main>
  );
}
