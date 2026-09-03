"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { BorsaIstanbulLogo, matchNewsLogo, matchSourceLogo } from "../../components/bulten/logos";
import { NewsCard } from "../../components/bulten/NewsCard";
import { NewsDetailModal, type NewsDetailArticle } from "../../components/bulten/NewsDetailModal";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { BULLETIN_PAGE_READY_EVENT } from "../../components/layout/transitionEvents";
import { EconomicCalendarTab } from "../../components/market/EconomicCalendarTab";
import { useAsyncData } from "../../hooks/useAsyncData";
import { useDashboard } from "../../hooks/useDashboard";
import { useLanguage } from "../../contexts/LanguageContext";
import type { NewsArticle } from "../../models/market";
import type { Holding } from "../../models/portfolio";
import { getNews } from "../../services/marketService";

type Section = "haberler" | "takvim";

const SECTIONS: { key: Section; label: { tr: string; en: string } }[] = [
  { key: "haberler", label: { tr: "Haberler", en: "News" } },
  { key: "takvim", label: { tr: "Ekonomik Takvim", en: "Economic Calendar" } },
];

function CalendarLoadingOverlay({ language }: { language: "tr" | "en" }) {
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
          {language === "tr" ? "Ekonomik takvim hazırlanıyor" : "Preparing economic calendar"}
        </span>
      </div>
    </div>,
    mainElement,
  );
}

type Category = "portfoy" | "bist" | "makro" | "bulten";

type Article = {
  id: string;
  category: Category;
  featured?: boolean;
  time: string;
  source: string;
  symbol?: string;
  title: string;
  summary: string;
  body: string[];
  image: string;
  tag?: "positive" | "negative" | "neutral";
  /** Haberin yayindaki adresi - `NewsDetailModal`'da "Kaynağa git" linkini besler. */
  sourceUrl?: string | null;
};

const tabs: { key: "tumu" | Category; label: { tr: string; en: string } }[] = [
  { key: "tumu", label: { tr: "Tümü", en: "All" } },
  { key: "portfoy", label: { tr: "Portföyüm", en: "My Portfolio" } },
  { key: "bist", label: { tr: "BIST / Hisse", en: "BIST / Stocks" } },
  { key: "makro", label: { tr: "Makro Ekonomi", en: "Macro Economy" } },
  { key: "bulten", label: { tr: "Günün Bülteni", en: "Daily Bulletin" } },
];

//: Backend `rag.documents.kategori` gercek degerleri (doviz | ekonomi | hisse
//: | altin | piyasa) sayfadaki mevcut sekme tasnifine (bist | makro | bulten)
//: esleniyor - sekme etiketleri/tasarimi degismiyor, yalnizca veri kaynagi.
function kategoriToTab(kategori: string | null): Category {
  if (kategori === "hisse") {
    return "bist";
  }
  if (kategori === "doviz" || kategori === "altin" || kategori === "ekonomi") {
    return "makro";
  }
  return "bulten";
}

function formatTarih(tarih: string | null, language: "tr" | "en"): string {
  if (!tarih) {
    return "";
  }
  const date = new Date(tarih);
  if (Number.isNaN(date.getTime())) {
    return tarih;
  }
  return date.toLocaleDateString(language === "tr" ? "tr-TR" : "en-US", { day: "2-digit", month: "2-digit" });
}

function toArticle(item: NewsArticle, index: number, language: "tr" | "en"): Article {
  return {
    id: item.id,
    category: kategoriToTab(item.kategori),
    featured: index === 0,
    time: formatTarih(item.tarih, language),
    source: item.sirket ?? (language === "tr" ? "Polifin Bülten" : "Polifin Bulletin"),
    symbol: item.symbol ?? undefined,
    title: item.baslik,
    summary: item.excerpt,
    body: item.body,
    image: item.image_url,
    sourceUrl: item.kaynak_url,
    // Backend, haberin ilgili oldugu varligin (altin, doviz, taninan bir
    // BIST sirketi vb.) CANLI gunluk degisimini cozebildiyse doldurur;
    // guvenilir bir eslesme yoksa null doner ve rozet hic gosterilmez.
    tag: item.related_change_pct == null ? undefined : item.related_change_pct < 0 ? "negative" : "positive",
  };
}

function FeaturedIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h13l3 3v13a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" />
      <path d="M8 9h8" />
      <path d="M8 13h8" />
      <path d="M8 17h5" />
    </svg>
  );
}

function HoldingIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M15 7h6v6" />
    </svg>
  );
}

function formatTry(value: number, language: "tr" | "en"): string {
  return new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatSignedTry(value: number, language: "tr" | "en"): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${formatTry(Math.abs(value), language)}`;
}

function buildHoldingArticle(
  holding: Holding,
  portfolioTotalTry: number,
  language: "tr" | "en",
): NewsDetailArticle {
  const changePct = holding.daily_change_pct ?? 0;
  const pct = Math.abs(changePct).toFixed(2);
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const priceText = holding.current_price.toLocaleString(locale, { maximumFractionDigits: 2 });
  const quantityText = holding.quantity.toLocaleString(locale, { maximumFractionDigits: 4 });
  const sharePct = portfolioTotalTry > 0 ? (holding.market_value_try / portfolioTotalTry) * 100 : 0;
  const shareText = sharePct.toFixed(2);
  const pnlPctText = holding.pnl_pct == null ? null : Math.abs(holding.pnl_pct).toFixed(2);

  if (language === "en") {
    const direction = changePct < 0 ? "fell" : "rose";
    const pnlDirection = holding.pnl_try < 0 ? "loss" : "profit";
    return {
      title: `${holding.asset_name} represents ${shareText}% of your portfolio`,
      source: "Portfolio Insight",
      time: "Current",
      symbol: holding.symbol,
      body: [
        holding.daily_change_pct == null
          ? `${holding.symbol} (${holding.asset_name}) is currently trading at ${priceText} ${holding.currency}; daily change data is not available yet.`
          : `${holding.symbol} (${holding.asset_name}) ${direction} ${pct}% today and is currently trading at ${priceText} ${holding.currency}.`,
        `Your ${quantityText} units are currently worth ${formatTry(holding.market_value_try, language)} and represent ${shareText}% of your total portfolio.`,
        `The position currently has a ${formatTry(Math.abs(holding.pnl_try), language)} ${pnlDirection}${
          pnlPctText == null ? "" : ` (${pnlPctText}%)`
        }. Today's impact on the portfolio value is ${formatSignedTry(holding.daily_change_try, language)}.`,
      ],
    };
  }

  const direction = changePct < 0 ? "geriledi" : "yükseldi";
  const pnlDirection = holding.pnl_try < 0 ? "zarar" : "kâr";

  return {
    title: `${holding.asset_name} portföyünün %${shareText}’ini oluşturuyor`,
    source: "Portföy İçgörüsü",
    time: "Güncel",
    symbol: holding.symbol,
    body: [
      holding.daily_change_pct == null
        ? `${holding.symbol} (${holding.asset_name}) güncel olarak ${priceText} ${holding.currency} seviyesinden işlem görüyor; günlük değişim verisi henüz bulunmuyor.`
        : `${holding.symbol} (${holding.asset_name}) bugün %${pct} ${direction} ve güncel olarak ${priceText} ${holding.currency} seviyesinden işlem görüyor.`,
      `Portföyündeki ${quantityText} adet varlığın güncel değeri ${formatTry(holding.market_value_try, language)}. Bu pozisyon toplam portföyünün %${shareText}’ini oluşturuyor.`,
      `Pozisyondaki toplam ${pnlDirection} ${formatTry(Math.abs(holding.pnl_try), language)}${
        pnlPctText == null ? "" : ` (%${pnlPctText})`
      }. Bugünkü fiyat hareketinin portföy değerine etkisi ${formatSignedTry(holding.daily_change_try, language)} oldu.`,
    ],
  };
}

export default function BultenPage() {
  const { language } = useLanguage();
  const [section, setSection] = useState<Section>("haberler");
  const [calendarReady, setCalendarReady] = useState(false);
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]["key"]>("tumu");
  const [selectedArticle, setSelectedArticle] = useState<NewsDetailArticle | null>(null);
  const { data, loading, error, refetch } = useDashboard();
  const news = useAsyncData(() => getNews(50), [], "news:50");

  const markCalendarReady = useCallback(() => setCalendarReady(true), []);

  function selectSection(next: Section) {
    if (next === section) return;
    if (next === "takvim") setCalendarReady(false);
    setSection(next);
  }

  useEffect(() => {
    if (loading || news.loading) {
      return;
    }

    const frame = window.requestAnimationFrame(() => {
      document.documentElement.dataset.bulletinPageReady = "true";
      window.dispatchEvent(new Event(BULLETIN_PAGE_READY_EVENT));
    });

    return () => window.cancelAnimationFrame(frame);
  }, [loading, news.loading]);

  const articles = useMemo(
    () => (news.data?.items ?? []).map((item, index) => toArticle(item, index, language)),
    [language, news.data],
  );

  const filtered = useMemo(
    () => (
      activeTab === "tumu" || activeTab === "bulten"
        ? articles
        : articles.filter((article) => article.category === activeTab)
    ),
    [activeTab, articles],
  );
  const featured = activeTab === "tumu" ? filtered.find((article) => article.featured) : undefined;
  const featuredLogoMatch = featured ? matchNewsLogo(featured.symbol ?? featured.title) : null;
  const featuredSourceLogo = featured ? matchSourceLogo(featured.source) : null;
  const bulletinItems = filtered.filter((article) => article.id !== featured?.id);
  const showPortfolio = activeTab === "tumu" || activeTab === "portfoy";

  if (section === "haberler") {
    if ((loading && !data) || (news.loading && !news.data)) {
      return <LoadingState label={language === "tr" ? "Bülten yükleniyor" : "Loading newsletter"} />;
    }

    if (!data) {
      return (
        <ErrorState
          message={error ?? (language === "tr" ? "Bülten verisi boş döndü." : "Newsletter data returned empty.")}
          onRetry={refetch}
        />
      );
    }

    if (news.error) {
      return <ErrorState message={news.error} onRetry={news.refetch} />;
    }
  }

  const holdings = data?.holdings ?? [];
  const portfolioTotalTry = data?.summary?.total_value_try
    ?? holdings.reduce((total, holding) => total + holding.market_value_try, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">{language === "tr" ? "Bülten" : "Newsletter"}</h1>
        <p className="mt-1 text-sm app-muted">
          {language === "tr"
            ? "Portföyünle ve piyasayla ilgili güncel gelişmeler."
            : "The latest developments related to your portfolio and the markets."}
        </p>
      </div>

      <nav className="flex flex-wrap gap-2">
        {SECTIONS.map((item) => {
          const active = item.key === section;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => selectSection(item.key)}
              className={`rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${
                active ? "app-primary border-transparent" : "app-card app-border app-subtle-hover"
              }`}
            >
              {item.label[language]}
            </button>
          );
        })}
      </nav>

      {section === "takvim" ? (
        <>
          <EconomicCalendarTab onReady={markCalendarReady} />
          {!calendarReady && <CalendarLoadingOverlay language={language} />}
        </>
      ) : (
        <>
      <nav className="flex flex-wrap gap-2">
        {tabs.map((tab) => {
          const active = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${
                active ? "app-primary border-transparent" : "app-card app-border app-subtle-hover"
              }`}
            >
              {tab.key === "bist" && (
                <span className="h-4 w-4 shrink-0">
                  <BorsaIstanbulLogo />
                </span>
              )}
              {tab.label[language]}
            </button>
          );
        })}
      </nav>

      {featured && (
        <button
          type="button"
          onClick={() => setSelectedArticle(featured)}
          className="app-hover-card flex w-full flex-col gap-4 rounded-2xl border p-6 text-left shadow-sm sm:flex-row sm:items-start"
        >
          <span
            className="grid h-14 w-14 shrink-0 place-items-center overflow-hidden rounded-xl app-primary-soft"
            style={featuredLogoMatch ? { backgroundColor: featuredLogoMatch.background } : undefined}
          >
            {featuredLogoMatch ? (
              <span className={`h-full w-full ${featuredLogoMatch.fill ? "" : "p-2.5"}`}>
                <featuredLogoMatch.Logo />
              </span>
            ) : (
              <FeaturedIcon />
            )}
          </span>
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide app-muted">
              <span>{language === "tr" ? "Öne Çıkan Bülten" : "Featured Bulletin"} ·</span>
              {featuredSourceLogo && (
                <img src={featuredSourceLogo} alt="" aria-hidden="true" className="h-4 w-4 shrink-0 rounded-sm object-contain" />
              )}
              <span>
                {featured.source} · {featured.time}
              </span>
            </div>
            <h2 className="mt-1 text-lg font-bold app-heading">{featured.title}</h2>
            <p className="mt-2 text-sm app-muted">{featured.summary}</p>
          </div>
        </button>
      )}

      {showPortfolio && (
        <section>
          <h2 className="mb-3 text-base font-semibold app-heading">
            {language === "tr" ? "Portföyden" : "From Your Portfolio"}
          </h2>
          {holdings.length === 0 ? (
            <p className="text-sm app-muted">
              {language === "tr" ? "Portföyünde henüz bir varlık bulunmuyor." : "There are no assets in your portfolio yet."}
            </p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {holdings.map((holding) => {
                const holdingArticle = buildHoldingArticle(holding, portfolioTotalTry, language);
                const sharePct = portfolioTotalTry > 0
                  ? (holding.market_value_try / portfolioTotalTry) * 100
                  : 0;
                const changePct = Math.abs(holding.daily_change_pct ?? 0).toFixed(2);
                const summary = language === "tr"
                  ? holding.daily_change_pct == null
                    ? `${holding.symbol} pozisyonunun güncel değeri ${formatTry(holding.market_value_try, language)} ve portföy payı %${sharePct.toFixed(2)}.`
                    : `${holding.symbol} bugün %${changePct} ${holding.daily_change_pct < 0 ? "değer kaybetti" : "değer kazandı"}. Pozisyon değeri ${formatTry(holding.market_value_try, language)}, portföy payı %${sharePct.toFixed(2)}.`
                  : holding.daily_change_pct == null
                    ? `Your ${holding.symbol} position is worth ${formatTry(holding.market_value_try, language)} and represents ${sharePct.toFixed(2)}% of your portfolio.`
                    : `${holding.symbol} ${holding.daily_change_pct < 0 ? "fell" : "rose"} ${changePct}% today. The position is worth ${formatTry(holding.market_value_try, language)} and represents ${sharePct.toFixed(2)}% of your portfolio.`;
                return (
                  <NewsCard
                    key={holding.symbol}
                    icon={<HoldingIcon />}
                    photoQuery={holding.asset_name}
                    symbol={holding.symbol}
                    time={holdingArticle.time}
                    tag={
                      holding.daily_change_pct == null
                        ? "neutral"
                        : holding.daily_change_pct < 0
                          ? "negative"
                          : "positive"
                    }
                    title={holdingArticle.title}
                    summary={summary}
                    onOpen={() => setSelectedArticle(holdingArticle)}
                  />
                );
              })}
            </div>
          )}
        </section>
      )}

      {bulletinItems.length > 0 && (
        <section>
          <h2 className="mb-3 text-base font-semibold app-heading">
            {language === "tr" ? "Günün Bültenleri" : "Today's Bulletins"}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {bulletinItems.map((article) => (
              <NewsCard
                key={article.id}
                image={article.image}
                symbol={article.symbol}
                tag={article.tag}
                time={article.time}
                title={article.title}
                summary={article.summary}
                onOpen={() => setSelectedArticle(article)}
              />
            ))}
          </div>
        </section>
      )}

      {selectedArticle && <NewsDetailModal article={selectedArticle} onClose={() => setSelectedArticle(null)} />}
        </>
      )}
    </div>
  );
}
