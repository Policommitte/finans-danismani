"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ChatWidget } from "../components/chat/ChatWidget";
import { mainNavItems, utilityNavItems } from "../components/layout/navItems";
import { requestPageTransition } from "../components/layout/transitionEvents";
import { useLanguage } from "../contexts/LanguageContext";
import { useAuth } from "../hooks/useAuth";
import type { PublicLandingPreviewResponse } from "../models/market";
import { getPublicLandingPreview } from "../services/marketService";

type Language = "tr" | "en";
type PreviewKey = "dashboard" | "portfolio" | "market" | "newsletter";

//: Sidebar.tsx ile AYNI kaynaktan (navItems.ts) beslenir - giris yapilmis ve
//: yapilmamis durumda farkli menu ogeleri/etiketleri gorunmesin diye.
const publicMenuTargets = mainNavItems.filter((item) => item.key !== "home");
const utilityMenuTargets = utilityNavItems;

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
    brand: "Finans Danışmanı",
    themeToLight: "Aydınlık moda geç",
    themeToDark: "Karanlık moda geç",
    languageLabel: "Dili İngilizce yap",
    features: [
      {
        key: "dashboard",
        title: "Genel Bakış ve Portföy",
        metric: "1,64 Mn",
        description: "Varlıklar, dağılım, risk ve işlemler",
        badge: "Önizleme",
        icon: "/analiz.svg",
      },
      {
        key: "market",
        title: "Piyasa",
        metric: "5",
        description: "Canlı piyasa görünümü",
        badge: "Önizleme",
        icon: "/piyasa.svg",
      },
      {
        key: "newsletter",
        title: "Bülten",
        metric: "Güncel",
        description: "Piyasa haberleri ve şirket bültenlerini takip edin",
        badge: "Canlı",
        icon: "/bulten.svg",
      },
    ],
    slides: [
      {
        key: "analysis",
        tab: "Analiz",
        eyebrow: "Genel bakış ve risk görünümü",
        title: "Portföyünüzün anlık durumunu net görün.",
        body:
          "Toplam değer, kar-zarar, varlık dağılımı ve risk skoru genel bakış ekranında özetlenir. Kullanıcı portföyünün genel sağlığını hızlıca takip eder.",
        metrics: [
          ["Toplam değer", "1,64 Mn"],
          ["Risk skoru", "61/100"],
          ["Dağılım", "Kripto %67"],
        ],
      },
      {
        key: "market",
        tab: "Piyasalar",
        eyebrow: "Piyasa takibi, sanal işlemler ve otonom eylemler",
        title: "Piyasaları takip edin, işlemlerinizi tek yerden yönetin.",
        body:
          "Varlıkların fiyatlarını ve grafiklerini inceleyin, sanal emirlerinizi deneyin. Sistem portföyünüz ve risk profilinize göre eylem önerileri üretir; siz onaylamadan hiçbir emir iletilmez.",
        metrics: [
          ["Piyasalar", "Canlı takip"],
          ["Sanal işlemler", "Emirlerini dene"],
          ["Otonom eylemler", "Kontrol sende"],
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
          ["Haber takibi", "Gündemi yakala"],
          ["Sana özel", "Portföy etkisi"],
          ["Sonraki adım", "Net öneriler"],
        ],
      },
      {
        key: "chat",
        tab: "Chatbot",
        eyebrow: "AI finans asistanı",
        title: "Sorularınızı sayfadan ayrılmadan chatbot ile sorun.",
        body:
          "Sağ alttaki finans asistanına portföyünüz ve piyasa gelişmeleri hakkında sorular sorabilir, sayfadan ayrılmadan anlaşılır ve size özel yanıtlar alabilirsiniz.",
        metrics: [
          ["Her an yanında", "Hızlı yanıt"],
          ["Sana özel", "Portföy odaklı"],
          ["Kolay erişim", "Tek tıkla sor"],
        ],
      },
      {
        key: "game",
        tab: "Yatırım Oyunu",
        eyebrow: "Finansal farkındalık ve karar pratiği",
        title: "Yatırım kararlarınızı oyunla geliştirin.",
        body:
          "Gerçek para kullanmadan farklı piyasa senaryolarında seçimler yapın, sonuçlarını görün ve finansal bilginizi adım adım geliştirin.",
        metrics: [
          ["Senaryolar", "Kararını ver"],
          ["İlerleme", "Puanını artır"],
          ["Öğrenme", "Anında geri bildirim"],
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
    brand: "Finance Advisor",
    themeToLight: "Switch to light mode",
    themeToDark: "Switch to dark mode",
    languageLabel: "Switch language to Turkish",
    features: [
      {
        key: "dashboard",
        title: "Overview and Portfolio",
        metric: "1.64M TRY",
        description: "Assets, allocation, risk and transactions",
        badge: "Preview",
        icon: "/analiz.svg",
      },
      {
        key: "market",
        title: "Market",
        metric: "5",
        description: "Live market view",
        badge: "Preview",
        icon: "/piyasa.svg",
      },
      {
        key: "newsletter",
        title: "Newsletter",
        metric: "Live",
        description: "Follow market news and company bulletins",
        badge: "Live",
        icon: "/bulten.svg",
      },
    ],
    slides: [
      {
        key: "analysis",
        tab: "Overview",
        eyebrow: "Overview and risk view",
        title: "See your portfolio's current status clearly.",
        body:
          "Total value, profit/loss, asset allocation and risk score are summarized in the overview screen so users can quickly follow portfolio health.",
        metrics: [
          ["Total value", "1.64M TRY"],
          ["Risk score", "61/100"],
          ["Allocation", "Crypto 67%"],
        ],
      },
      {
        key: "market",
        tab: "Markets",
        eyebrow: "Market tracking, virtual trading and autonomous actions",
        title: "Follow the markets and manage your actions in one place.",
        body:
          "Explore asset prices and charts, then try virtual orders. The system generates action suggestions based on your portfolio and risk profile; no order is placed without your approval.",
        metrics: [
          ["Markets", "Live tracking"],
          ["Virtual trading", "Try your orders"],
          ["Autonomous actions", "You stay in control"],
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
          ["News tracking", "Stay up to date"],
          ["Personalized", "Portfolio impact"],
          ["Next step", "Clear suggestions"],
        ],
      },
      {
        key: "chat",
        tab: "Chatbot",
        eyebrow: "AI finance assistant",
        title: "Ask questions with the chatbot without leaving the page.",
        body:
          "Ask the financial assistant about your portfolio and market developments, and receive clear, personalized answers without leaving the page.",
        metrics: [
          ["Always available", "Quick answers"],
          ["Personalized", "Portfolio-aware"],
          ["Easy access", "Ask in one click"],
        ],
      },
      {
        key: "game",
        tab: "Investment Game",
        eyebrow: "Financial awareness and decision practice",
        title: "Improve your investment decisions through play.",
        body:
          "Make choices in different market scenarios without using real money, see the outcomes, and improve your financial knowledge step by step.",
        metrics: [
          ["Scenarios", "Make your choice"],
          ["Progress", "Build your score"],
          ["Learning", "Instant feedback"],
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

function displayUpper(value: string, language: Language): string {
  return value.toLocaleUpperCase(language === "tr" ? "tr-TR" : "en-US");
}

function MenuIcon({ src, className = "h-8 w-8" }: { src: string; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`block shrink-0 bg-current [mask-position:center] [mask-repeat:no-repeat] [mask-size:contain] ${className}`}
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

function LandingSideMenu({
  language,
  authRequiredPath,
  onNavigate,
  onAuthPopoverClose,
}: {
  language: Language;
  authRequiredPath: string | null;
  onNavigate: (href: string) => void;
  onAuthPopoverClose: () => void;
}) {
  const menuRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!authRequiredPath) {
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      if (!menuRef.current || !(event.target instanceof Node)) {
        return;
      }

      if (!menuRef.current.contains(event.target)) {
        onAuthPopoverClose();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [authRequiredPath, onAuthPopoverClose]);

  const iconButtonClass =
    "group relative flex h-16 w-full items-center justify-center overflow-visible rounded-md border border-white/10 bg-white/[0.06] px-0 text-white/70 transition hover:border-white/30 hover:bg-white/15 hover:text-white";
  const homeButtonClass =
    "group relative flex h-16 w-full items-center justify-center overflow-visible rounded-md border border-white/20 bg-white/10 px-0 text-white transition";
  const tooltipClass =
    "pointer-events-none absolute left-1/2 -top-3 z-[70] -translate-x-1/2 whitespace-nowrap px-1 text-[11px] font-bold leading-none text-white/70 transition-colors group-hover:text-white";
  const activeTooltipClass =
    "pointer-events-none absolute left-1/2 -top-3 z-[70] -translate-x-1/2 whitespace-nowrap px-1 text-[11px] font-bold leading-none text-white";

  return (
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
      className="fixed bottom-0 left-0 top-0 z-50 flex w-24 flex-col overflow-visible bg-[var(--color-market-bar)] px-6 py-6 shadow-2xl"
    >
      <div aria-hidden="true" className="h-20 shrink-0" />

      <nav className="mt-8 space-y-4">
        <Link
          href="/"
          data-tour="nav-home"
          onClick={onAuthPopoverClose}
          aria-current="page"
          className={homeButtonClass}
        >
          <span className="absolute bottom-2 left-0 top-2 w-1 rounded-r-full bg-[var(--color-primary)]" />
          <MenuIcon src="/ana-sayfa.svg" className="h-5 w-5" />
          <span className={activeTooltipClass}>{copy[language].home}</span>
        </Link>
        {publicMenuTargets.map((target) => (
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
              data-tour={target.tourId}
              onClick={() => onNavigate(target.href)}
              aria-label={target.label[language]}
              className={iconButtonClass}
            >
              <span className="absolute left-2 top-1/2 -translate-y-1/2">
                <MenuIcon src={target.icon} />
              </span>
            </button>
            <span className={tooltipClass}>{target.label[language]}</span>
          </div>
        ))}
      </nav>

      <div className="mt-auto space-y-4 pt-6">
        {utilityMenuTargets.map((target) => (
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
              data-tour={target.tourId}
              onClick={() => onNavigate(target.href)}
              aria-label={target.label[language]}
              className={iconButtonClass}
            >
              <span className="absolute left-2 top-1/2 -translate-y-1/2">
                <MenuIcon src={target.icon} />
              </span>
            </button>
            <span className={tooltipClass}>{target.label[language]}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}

function HeroVisual({ slideKey, language }: { slideKey: string; language: Language }) {
  const visual = copy[language].visual;

  if (slideKey === "game") {
    const gameCopy = language === "tr"
      ? {
          title: "Yatırım Oyunu",
          level: "Seviye 3",
          progress: "Senaryo 2 / 5",
          question: "Piyasa dalgalanırken ilk adımınız ne olur?",
          choices: ["Hemen alım yaparım", "Önce riskleri incelerim", "Tüm varlıkları satarım"],
          score: "+120 puan",
          feedback: "Dengeli karar",
        }
      : {
          title: "Investment Game",
          level: "Level 3",
          progress: "Scenario 2 / 5",
          question: "What is your first move when markets become volatile?",
          choices: ["Buy immediately", "Review the risks first", "Sell every asset"],
          score: "+120 points",
          feedback: "Balanced decision",
        };

    return (
      <div className="relative min-h-80 overflow-hidden rounded-md bg-[var(--color-panel-dark)] p-6 text-[var(--color-market-text)] shadow-xl">
        <div className="flex items-center justify-between gap-4 border-b border-white/15 pb-4">
          <div>
            <div className="text-lg font-black">{gameCopy.title}</div>
            <div className="mt-1 text-xs text-[var(--color-on-primary-muted)]">{gameCopy.level}</div>
          </div>
          <div className="rounded-full bg-[var(--color-primary)] px-3 py-1.5 text-xs font-black text-white">
            {gameCopy.score}
          </div>
        </div>

        <div className="mt-5 rounded-md bg-[var(--color-surface)] p-5 text-[var(--color-text)] shadow-sm">
          <div className="flex items-center justify-between gap-3 text-xs font-bold app-muted">
            <span>{displayUpper(gameCopy.progress, language)}</span>
            <span className="app-success">{gameCopy.feedback}</span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full app-card-muted">
            <div className="h-full w-2/5 rounded-full bg-[var(--color-primary)]" />
          </div>
          <div className="mt-5 text-lg font-black leading-6 app-heading">{gameCopy.question}</div>
          <div className="mt-4 space-y-2">
            {gameCopy.choices.map((choice, index) => (
              <div
                key={choice}
                className={`rounded-md border px-4 py-3 text-sm font-semibold ${
                  index === 1
                    ? "border-[var(--color-primary)] bg-[var(--color-primary-soft)] app-primary-text"
                    : "app-border app-muted"
                }`}
              >
                <span className="mr-3 font-black">{String.fromCharCode(65 + index)}</span>
                {choice}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

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
              <div className="text-xs font-bold text-[var(--color-on-primary-muted)]">{displayUpper(visual.newsFlow, language)}</div>
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
            <div className="text-xs font-bold app-muted">{displayUpper(visual.personalRecommendation, language)}</div>
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

  if (slideKey === "market") {
    const marketItems = [
      { symbol: "THYAO", value: "₺314,10", change: "+2,14%" },
      { symbol: "BTC", value: "₺3,21 Mn", change: "+0,84%" },
    ];

    return (
      <div className="relative min-h-80 overflow-hidden rounded-md bg-[var(--color-panel-dark)] p-6 text-[var(--color-market-text)] shadow-xl">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-xs font-bold text-[var(--color-on-primary-muted)]">
              {language === "tr" ? "SEÇİLİ VARLIK" : "SELECTED ASSET"}
            </div>
            <div className="mt-2 flex items-baseline gap-3">
              <span className="text-2xl font-black">THYAO</span>
              <span className="text-lg font-bold">₺314,10</span>
              <span className="text-sm font-bold app-success">+2,14%</span>
            </div>
          </div>
          <div className="flex gap-2 text-xs font-bold">
            {["1G", "1H", "1A", "1Y"].map((range, index) => (
              <span key={range} className={`rounded px-2 py-1 ${index === 2 ? "app-primary" : "bg-[var(--color-overlay-soft)]"}`}>
                {range}
              </span>
            ))}
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-[1fr_0.72fr]">
          <div className="rounded-md bg-[var(--color-overlay-soft)] p-4">
            <svg viewBox="0 0 420 180" className="h-44 w-full" role="img" aria-label={language === "tr" ? "Temsili fiyat grafiği" : "Representative price chart"}>
              {[30, 75, 120, 165].map((y) => (
                <line key={y} x1="0" y1={y} x2="420" y2={y} stroke="var(--color-border)" strokeOpacity="0.28" />
              ))}
              <path d="M0 151 C35 145 48 104 78 119 S128 137 150 91 S205 42 230 73 S278 130 302 85 S352 39 420 51 L420 180 L0 180 Z" fill="var(--color-primary)" fillOpacity="0.18" />
              <path d="M0 151 C35 145 48 104 78 119 S128 137 150 91 S205 42 230 73 S278 130 302 85 S352 39 420 51" fill="none" stroke="var(--color-accent)" strokeWidth="4" strokeLinecap="round" />
            </svg>
          </div>
          <div className="space-y-3 rounded-md bg-[var(--color-surface)] p-4 text-[var(--color-text)]">
            <div className="text-xs font-bold app-muted">
              {language === "tr" ? "TAKİP LİSTESİ" : "WATCHLIST"}
            </div>
            {marketItems.map((item) => (
              <div key={item.symbol} className="rounded-md border app-border p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-black app-heading">{item.symbol}</span>
                  <span className="text-xs font-bold app-success">{item.change}</span>
                </div>
                <div className="mt-1 text-sm font-semibold app-muted">{item.value}</div>
              </div>
            ))}
            <div className="rounded-md border border-[var(--color-primary)] bg-[var(--color-primary-soft)] p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-black app-primary-text">
                  {language === "tr" ? "OTONOM EYLEM" : "AUTONOMOUS ACTION"}
                </span>
                <span className="text-xs font-bold app-success">
                  {language === "tr" ? "%86 güven" : "86% confidence"}
                </span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-black app-heading">
                    {language === "tr" ? "THYAO için AL önerisi" : "BUY suggestion for THYAO"}
                  </div>
                  <div className="mt-1 text-xs app-muted">
                    {language === "tr" ? "Emir için onayınız bekleniyor" : "Waiting for your approval"}
                  </div>
                </div>
                <span className="shrink-0 rounded-md bg-[var(--color-primary)] px-3 py-2 text-xs font-black text-white">
                  {language === "tr" ? "İncele" : "Review"}
                </span>
              </div>
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
          <div className="text-xs font-bold app-muted">{displayUpper(visual.portfolioSummary, language)}</div>
          <div className="mt-4 text-3xl font-black app-heading">{language === "tr" ? "1,64 Mn" : "1.64M TRY"}</div>
          <div className="mt-2 text-sm font-semibold app-success">
            {language === "tr" ? "+5.27% kar/zarar" : "+5.27% P/L"}
          </div>
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
            <div className="text-xs font-bold text-[var(--color-on-primary-muted)]">{displayUpper(visual.riskScore, language)}</div>
            <div className="mt-3 text-4xl font-black">61</div>
            <div className="text-sm text-[var(--color-on-primary-muted)]">{visual.highRisk}</div>
          </div>
          <div className="rounded-md app-card p-5 shadow-sm">
            <div className="text-xs font-bold app-muted">{displayUpper(visual.marketSignal, language)}</div>
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
                    {displayUpper(slide.eyebrow, language)}
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
                      <div className="text-xs font-bold app-muted">{displayUpper(label, language)}</div>
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

function formatTry(value: number, language: Language): string {
  return new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    maximumFractionDigits: 0,
    style: "currency",
    currency: "TRY",
  }).format(value);
}

function formatCompactTry(value: number, language: Language): string {
  return new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    maximumFractionDigits: 2,
    notation: "compact",
    compactDisplay: "short",
  }).format(value);
}

function assetClassLabel(assetClass: string, language: Language): string {
  const labels: Record<string, { tr: string; en: string }> = {
    STOCK: { tr: "Hisse", en: "Stocks" },
    FOREX: { tr: "Döviz", en: "FX" },
    GOLD: { tr: "Altın", en: "Gold" },
    CRYPTO: { tr: "Kripto", en: "Crypto" },
    BOND: { tr: "Tahvil", en: "Bond" },
  };
  return labels[assetClass]?.[language] ?? assetClass;
}

function PreviewBody({
  preview,
  language,
  previewData,
}: {
  preview: PreviewKey;
  language: Language;
  previewData: PublicLandingPreviewResponse | null;
}) {
  if (preview === "portfolio") {
    const holdings = previewData?.holdings.length
      ? previewData.holdings
      : [
          {
            symbol: "THYAO",
            asset_name: "Turk Hava Yollari",
            asset_class: "STOCK",
            current_price: 315.5,
            daily_change_pct: 1.2,
            market_value_try: 315500,
            pnl_pct: 8.79,
          },
          {
            symbol: "SASA",
            asset_name: "Sasa Polyester",
            asset_class: "STOCK",
            current_price: 45.2,
            daily_change_pct: -1.8,
            market_value_try: 226000,
            pnl_pct: -13.08,
          },
          {
            symbol: "BTC",
            asset_name: "Bitcoin",
            asset_class: "CRYPTO",
            current_price: 65400,
            daily_change_pct: 4.5,
            market_value_try: 1097085,
            pnl_pct: 9,
          },
        ];
    const portfolioAllocation = previewData?.allocation.length
      ? previewData.allocation
      : [
          { asset_class: "CRYPTO", class_value_try: 1097085, class_pct: 66.95 },
          { asset_class: "STOCK", class_value_try: 541500, class_pct: 33.05 },
        ];

    return (
      <div className="grid gap-4 lg:grid-cols-[1fr_0.75fr]">
        <div className="rounded-md border app-card p-4">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-sm font-black app-heading">{language === "tr" ? "Varlıklar" : "Assets"}</div>
            <span className="rounded-full bg-[var(--color-surface-muted)] px-3 py-1 text-xs font-bold app-muted">
              {holdings.length} {language === "tr" ? "pozisyon" : "positions"}
            </span>
          </div>
          <div className="space-y-3">
            {holdings.map((holding) => {
              const change = holding.daily_change_pct ?? 0;
              return (
                <div key={holding.symbol} className="grid grid-cols-3 items-center rounded-md app-card-muted px-3 py-3 text-sm">
                  <span className="font-black app-heading">{holding.symbol}</span>
                  <span className="app-muted">{formatCompactTry(holding.market_value_try, language)}</span>
                  <span className={change >= 0 ? "app-success text-right font-bold" : "app-danger text-right font-bold"}>
                    {change >= 0 ? "+" : ""}{change.toFixed(2)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
        <div className="space-y-4">
          <div className="rounded-md border app-card p-4">
            <div className="text-sm font-black app-heading">{language === "tr" ? "Dağılım" : "Allocation"}</div>
            <div className="mt-4 space-y-3">
              {portfolioAllocation.map((item, index) => (
                <div key={item.asset_class}>
                  <div className="mb-1 flex items-center justify-between text-xs font-bold app-muted">
                    <span>{assetClassLabel(item.asset_class, language)}</span>
                    <span>%{item.class_pct.toFixed(2)}</span>
                  </div>
                  <div className="h-3 rounded-full app-card-muted">
                    <div
                      className="h-3 rounded-full"
                      style={{
                        width: `${item.class_pct}%`,
                        backgroundColor: ["var(--color-primary)", "var(--color-accent)", "var(--color-success)"][index % 3],
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-md border border-[var(--color-primary)] bg-[var(--color-surface)] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-black app-heading">{language === "tr" ? "Portföy özeti" : "Portfolio summary"}</div>
                <div className="mt-2 text-3xl font-black app-heading">{formatCompactTry(previewData?.total_value_try ?? 1638585, language)}</div>
                <p className="mt-2 text-sm app-muted">
                  {language === "tr"
                    ? `Toplam getiri: ${previewData?.total_pnl_pct == null ? "+5.27%" : `${previewData.total_pnl_pct > 0 ? "+" : ""}${previewData.total_pnl_pct.toFixed(2)}%`}`
                    : `Total return: ${previewData?.total_pnl_pct == null ? "+5.27%" : `${previewData.total_pnl_pct > 0 ? "+" : ""}${previewData.total_pnl_pct.toFixed(2)}%`}`}
                </p>
              </div>
              <div className="rounded-md border border-[var(--color-warning-border)] px-3 py-2 text-right">
                <div className="text-xs font-bold app-muted">{language === "tr" ? "Risk" : "Risk"}</div>
                <div className="mt-1 text-xl font-black text-[var(--color-warning-text)]">61/100</div>
                <div className="text-xs font-bold text-[var(--color-warning-text)]">{language === "tr" ? "orta" : "medium"}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (preview === "newsletter") {
    const newsItems = copy[language].visual.news.map((title, index) => ({
      title,
      category:
        language === "tr"
          ? ["Şirket", "Piyasalar", "Küresel"][index]
          : ["Company", "Markets", "Global"][index],
      time:
        language === "tr"
          ? ["12 dk önce", "28 dk önce", "45 dk önce"][index]
          : ["12 min ago", "28 min ago", "45 min ago"][index],
    }));
    const selectedNews = newsItems[0];

    return (
      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-md border app-card p-4">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="text-sm font-black app-heading">
              {language === "tr" ? "Güncel haberler" : "Latest news"}
            </div>
            <span className="rounded-full bg-[var(--color-surface-muted)] px-3 py-1 text-xs font-bold app-success">
              {language === "tr" ? "Canlı akış" : "Live feed"}
            </span>
          </div>
          <div className="space-y-3">
            {newsItems.map((item, index) => (
              <article
                key={item.title}
                className={`rounded-md border p-3 ${index === 0 ? "border-[var(--color-primary)] bg-[var(--color-primary-soft)]" : "app-border app-card-muted"}`}
              >
                <div className="flex items-center justify-between gap-3 text-xs font-bold app-muted">
                  <span>{item.category}</span>
                  <span>{item.time}</span>
                </div>
                <div className="mt-2 text-sm font-black leading-5 app-heading">{item.title}</div>
              </article>
            ))}
          </div>
        </div>

        <article className="rounded-md border app-card p-5">
          <div className="flex items-center justify-between gap-3 text-xs font-bold app-muted">
            <span>{selectedNews.category}</span>
            <span>{selectedNews.time}</span>
          </div>
          <h3 className="mt-4 text-2xl font-black leading-tight app-heading">{selectedNews.title}</h3>
          <p className="mt-4 text-sm leading-6 app-muted">
            {language === "tr"
              ? "Piyasaları ve şirketleri etkileyen güncel gelişmeleri tek akışta takip edin. Haber ayrıntılarını, ilgili varlıkları ve piyasa bağlamını bülten ekranında inceleyin."
              : "Follow current developments affecting markets and companies in one feed. Review story details, related assets and market context on the newsletter screen."}
          </p>
          <div className="mt-6 border-t app-border pt-4">
            <div className="text-xs font-bold app-muted">
              {language === "tr" ? "İLGİLİ VARLIKLAR" : "RELATED ASSETS"}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {["THYAO", "BIST 100", "USD/TRY"].map((symbol) => (
                <span key={symbol} className="rounded-full app-primary-soft px-3 py-1 text-xs font-bold">
                  {symbol}
                </span>
              ))}
            </div>
          </div>
        </article>
      </div>
    );
  }

  if (preview === "market") {
    const rows = [
      ["BIST 100", language === "tr" ? "14.241" : "14,241", "+0.80%"],
      ["USD/TRY", language === "tr" ? "47,93" : "47.93", "+0.02%"],
      ["BTC", language === "tr" ? "63.583" : "63,583", "+1.20%"],
      ["EUR/TRY", language === "tr" ? "55,49" : "55.49", "+0.07%"],
      ["XAU/USD", language === "tr" ? "4.458" : "4,458", "+0.46%"],
    ];
    const movers = [
      ["BTC", "+1.20%"],
      ["BIST 100", "+0.80%"],
      ["USD/TRY", "+0.02%"],
    ];

    return (
      <div className="grid gap-4 lg:grid-cols-[0.85fr_1fr]">
        <div className="rounded-md border app-card p-4">
          <div className="h-11 rounded-md border app-card-muted px-4 py-3 text-sm app-muted">
            {language === "tr" ? "Piyasada ara" : "Search market"}
          </div>
          <div className="mt-4 space-y-3">
            {rows.map(([symbol, value, change]) => (
              <div key={symbol} className="flex items-center justify-between rounded-md app-card-muted px-3 py-3">
                <div>
                  <div className="text-sm font-black app-heading">{symbol}</div>
                  <div className="text-xs app-muted">{value}</div>
                </div>
                <div className="text-sm font-bold app-success">{change}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-4">
          <div className="rounded-md border app-card p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-black app-heading">{language === "tr" ? "BIST 100 fiyat grafiği" : "BIST 100 price chart"}</div>
              <span className="rounded-full bg-[var(--color-primary)] px-3 py-1 text-xs font-bold text-[var(--color-on-primary)]">
                {language === "tr" ? "seçili endeks" : "selected index"}
              </span>
            </div>
            <div className="mt-6 flex h-40 items-end gap-2 rounded-md app-card-muted p-4">
              {[35, 52, 46, 70, 63, 88, 76, 96].map((height, index) => (
                <div
                  key={index}
                  className="flex-1 rounded-t bg-[var(--color-primary)]"
                  style={{ height: `${height}%`, opacity: 0.45 + index * 0.06 }}
                />
              ))}
            </div>
            <p className="mt-4 text-sm app-muted">
              {language === "tr"
                ? "Piyasa ekranı endeksleri, döviz kurlarını ve öne çıkan varlıkları tek görünümde takip etmenizi sağlar."
                : "The market screen helps you follow indices, FX rates and highlighted assets in one view."}
            </p>
          </div>
          <div className="rounded-md border border-[var(--color-primary)] bg-[var(--color-surface)] p-4">
            <div className="text-sm font-black app-heading">{language === "tr" ? "Piyasa özeti" : "Market summary"}</div>
            <div className="mt-3 text-2xl font-black app-heading">{language === "tr" ? "BIST yükselişte" : "BIST trending up"}</div>
            <div className="mt-3 grid gap-2 text-sm">
              {movers.map(([symbol, change]) => (
                <div key={symbol} className="flex items-center justify-between">
                  <span className="font-semibold app-muted">{symbol}</span>
                  <span className="font-bold app-success">{change}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const fallbackAllocation = [
    { asset_class: "CRYPTO", class_value_try: 1097085, class_pct: 66.95 },
    { asset_class: "STOCK", class_value_try: 541500, class_pct: 33.05 },
  ];
  const allocation = previewData?.allocation.length ? previewData.allocation : fallbackAllocation;
  const totalValue = previewData?.total_value_try ?? 1638585;
  const pnlPct = previewData?.total_pnl_pct ?? 5.27;
  const holdingCount = previewData?.holding_count ?? 3;
  const allocationColors = ["var(--color-primary)", "var(--color-accent)", "var(--color-success)", "var(--color-chart-yellow)"];
  let allocationCursor = 0;
  const allocationGradient = allocation
    .map((item, index) => {
      const start = allocationCursor;
      const end = allocationCursor + item.class_pct;
      allocationCursor = end;
      return `${allocationColors[index % allocationColors.length]} ${start}% ${end}%`;
    })
    .join(", ");
  const classCount = new Set(allocation.map((item) => item.asset_class)).size;

  const riskToneClass = "text-[var(--color-warning-text)]";
  const overviewMetrics = [
    {
      label: language === "tr" ? "Toplam değer" : "Total value",
      value: formatCompactTry(totalValue, language),
      badge: formatTry(totalValue, language),
      badgeClass: "app-success",
      valueClass: "app-heading",
    },
    {
      label: language === "tr" ? "Kar / zarar" : "Profit / loss",
      value: `${pnlPct > 0 ? "+" : ""}${pnlPct.toFixed(2)}%`,
      badge: language === "tr" ? "toplam getiri" : "total return",
      badgeClass: "app-muted",
      valueClass: pnlPct >= 0 ? "app-success" : "app-danger",
    },
    {
      label: language === "tr" ? "Risk skoru" : "Risk score",
      value: "61/100",
      badge: language === "tr" ? "orta" : "medium",
      badgeClass: riskToneClass,
      valueClass: riskToneClass,
    },
    {
      label: language === "tr" ? "Varlık sayısı" : "Asset count",
      value: String(holdingCount),
      badge: language === "tr" ? `${classCount} sınıf` : `${classCount} classes`,
      badgeClass: "app-success",
      valueClass: "app-heading",
    },
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-[0.8fr_1fr]">
      <div className="grid gap-3 sm:grid-cols-2">
        {overviewMetrics.map((metric) => (
          <div key={metric.label} className="rounded-md border app-card p-4">
            <div className="text-xs font-bold app-muted">{displayUpper(metric.label, language)}</div>
            <div className={`mt-3 text-2xl font-black ${metric.valueClass}`}>{metric.value}</div>
            <div className={`mt-2 text-xs font-bold ${metric.badgeClass}`}>{metric.badge}</div>
          </div>
        ))}
      </div>
      <div className="rounded-md border app-card p-4">
        <div className="text-sm font-black app-heading">{language === "tr" ? "Varlık dağılımı" : "Asset allocation"}</div>
        <div className="mt-5 grid items-center gap-5 sm:grid-cols-[180px_1fr]">
          <div
            aria-hidden="true"
            className="mx-auto h-40 w-40 rounded-full"
            style={{
              background: `conic-gradient(${allocationGradient})`,
            }}
          >
            <div className="flex h-full w-full items-center justify-center rounded-full p-6">
              <div className="flex h-full w-full flex-col items-center justify-center rounded-full bg-[var(--color-surface)] text-center">
                <div className="text-2xl font-black app-heading">{holdingCount}</div>
                <div className="text-xs font-bold app-muted">{language === "tr" ? "varlık" : "assets"}</div>
              </div>
            </div>
          </div>
          <div className="space-y-3 text-sm">
            {allocation.map((item, index) => (
              <div key={item.asset_class} className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: allocationColors[index % allocationColors.length] }}
                  />
                  <span className="font-semibold app-muted">{assetClassLabel(item.asset_class, language)}</span>
                </div>
                <span className="font-black app-heading">%{item.class_pct.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
        <p className="mt-5 text-sm leading-6 app-muted">
          {language === "tr" ? "Genel bakış ekranı portföy dağılımını ve temel metrikleri tek yerde toplar." : "The overview screen combines allocation and key metrics in one view."}
        </p>
      </div>
    </div>
  );
}

function PreviewModal({
  preview,
  language,
  previewData,
  isAuthenticated,
  onClose,
}: {
  preview: PreviewKey;
  language: Language;
  previewData: PublicLandingPreviewResponse | null;
  isAuthenticated: boolean;
  onClose: () => void;
}) {
  const selected = copy[language].features.find((card) => card.key === preview);

  if (!selected) {
    return null;
  }
  const previewFootnote =
    preview === "market"
      ? language === "tr"
        ? "Bu önizleme temsili piyasa verileriyle hazırlanmıştır."
        : "This preview is prepared with representative market data."
      : preview === "newsletter"
        ? language === "tr"
          ? "Bu önizleme temsili haber içerikleriyle hazırlanmıştır."
          : "This preview is prepared with representative news content."
      : language === "tr"
        ? "Bu önizleme temsili portföy verileriyle hazırlanmıştır."
        : "This preview is prepared with representative portfolio data.";

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <section className="max-h-[88vh] w-full max-w-5xl overflow-y-auto rounded-md border app-card p-6 shadow-2xl">
        <div className="mb-6 flex items-start justify-between gap-5">
          <div className="flex items-center gap-4">
            <span className="flex h-12 w-12 items-center justify-center rounded-md bg-[var(--color-surface-muted)] text-[var(--color-primary)]">
              <MenuIcon src={selected.icon} />
            </span>
            <div>
              <div className="text-xs font-bold app-primary-text">{selected.badge}</div>
              <h2 className="mt-1 text-2xl font-black app-heading">{selected.title}</h2>
              <p className="mt-1 text-sm app-muted">{selected.description}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={copy[language].close}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-[var(--color-border)] bg-transparent text-lg font-black app-muted transition hover:border-[var(--color-primary)] hover:text-[var(--color-heading)]"
          >
            x
          </button>
        </div>
        <PreviewBody preview={preview} language={language} previewData={previewData} />
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t app-border pt-5">
          <p className="text-sm app-muted">
            {previewFootnote}
          </p>
          {isAuthenticated ? (
            <span className="cursor-not-allowed rounded-md border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3 text-sm font-bold app-muted">
              {language === "tr" ? "Giriş yapıldı" : "Signed in"}
            </span>
          ) : (
            <Link href="/login" className="rounded-md app-primary px-4 py-3 text-sm font-bold">
              {copy[language].login}
            </Link>
          )}
        </div>
      </section>
    </div>
  );
}

function QuickAccessCards({
  language,
  previewData,
  onOpenPreview,
}: {
  language: Language;
  previewData: PublicLandingPreviewResponse | null;
  onOpenPreview: (preview: PreviewKey) => void;
}) {
  const cards = copy[language].features;

  function cardMetric(cardKey: string, fallback: string): { value: string; unit: string } {
    if (cardKey === "dashboard") {
      return {
        value: formatCompactTry(previewData?.total_value_try ?? 1638585, language),
        unit: language === "tr" ? "toplam değer" : "total value",
      };
    }

    if (cardKey === "newsletter") {
      return {
        value: fallback,
        unit: language === "tr" ? "haber akışı" : "news feed",
      };
    }

    return {
      value: fallback,
      unit: language === "tr" ? "öne çıkan" : "featured",
    };
  }

  return (
    <section id="ozellikler" className="border-t app-border app-card-muted py-14">
      <div className="mx-auto grid max-w-7xl gap-5 px-4 md:grid-cols-3">
        {cards.map((card) => {
          const metric = cardMetric(card.key, card.metric);

          return (
            <button
              key={card.key}
              type="button"
              onClick={() => onOpenPreview(card.key as PreviewKey)}
              className="group flex min-h-44 w-full flex-col justify-between rounded-md border app-card p-5 text-left shadow-sm transition hover:-translate-y-1 hover:border-[var(--color-primary)] hover:shadow-xl"
            >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-md bg-[var(--color-surface-muted)] text-[var(--color-primary)] transition group-hover:bg-[var(--color-primary)] group-hover:text-[var(--color-on-primary)]">
                  <MenuIcon src={card.icon} />
                </span>
                <div>
                  <div className="text-lg font-black app-heading">{card.title}</div>
                  <div className="mt-1 text-xs font-bold app-muted">{card.badge}</div>
                </div>
              </div>
              <span className="text-xl font-black app-muted transition group-hover:translate-x-1 group-hover:text-[var(--color-primary)]">
                &gt;
              </span>
            </div>

            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-black app-heading">{metric.value}</span>
                <span className="text-sm font-black app-muted">{metric.unit}</span>
              </div>
              <p className="mt-2 text-sm font-semibold leading-6 app-muted">{card.description}</p>
            </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

export default function HomePage() {
  const auth = useAuth();
  const { language } = useLanguage();
  const [authRequiredPath, setAuthRequiredPath] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [activePreview, setActivePreview] = useState<PreviewKey | null>(null);
  const [previewData, setPreviewData] = useState<PublicLandingPreviewResponse | null>(null);

  useEffect(() => {
    let active = true;

    async function loadPreviewData() {
      try {
        const response = await getPublicLandingPreview();
        if (active) {
          setPreviewData(response);
        }
      } catch {
        if (active) {
          setPreviewData(null);
        }
      }
    }

    void loadPreviewData();

    return () => {
      active = false;
    };
  }, []);

  function handleProtectedNavigate(href: string) {
    if (href === "/destek" || href.startsWith("/destek#")) {
      setAuthRequiredPath(null);
      requestPageTransition(href);
      return;
    }

    if (auth.loading) {
      return;
    }

    if (auth.user) {
      setAuthRequiredPath(null);
      requestPageTransition(href);
      return;
    }

    setAuthRequiredPath(href);
  }

  return (
    <main className="min-h-screen overflow-x-hidden app-bg transition-colors">
      <div className={activePreview ? "pointer-events-none blur-sm transition" : "transition"}>
        <LandingSideMenu
          language={language}
          authRequiredPath={authRequiredPath}
          onNavigate={handleProtectedNavigate}
          onAuthPopoverClose={() => setAuthRequiredPath(null)}
        />

        <div className="ml-24 w-[calc(100%-6rem)] pt-20">
          <HeroSlider language={language} />

          <QuickAccessCards
            language={language}
            previewData={previewData}
            onOpenPreview={setActivePreview}
          />
        </div>
      </div>

      {activePreview ? (
        <PreviewModal
          preview={activePreview}
          language={language}
          previewData={previewData}
          isAuthenticated={Boolean(auth.user)}
          onClose={() => setActivePreview(null)}
        />
      ) : null}

      <ChatWidget
        canSend={Boolean(auth.user)}
        blockedMessage={copy[language].chatLoginRequired}
        open={chatOpen}
        onOpenChange={setChatOpen}
      />
    </main>
  );
}
