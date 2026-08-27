"use client";

import { useMemo, useState } from "react";
import { BorsaIstanbulLogo, matchNewsLogo, matchSourceLogo } from "../../components/bulten/logos";
import { NewsCard } from "../../components/bulten/NewsCard";
import { NewsDetailModal, type NewsDetailArticle } from "../../components/bulten/NewsDetailModal";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { useAsyncData } from "../../hooks/useAsyncData";
import { useDashboard } from "../../hooks/useDashboard";
import type { NewsArticle } from "../../models/market";
import type { Holding } from "../../models/portfolio";
import { getNews } from "../../services/marketService";

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
};

const tabs: { key: "tumu" | Category; label: string }[] = [
  { key: "tumu", label: "Tümü" },
  { key: "portfoy", label: "Portföyüm" },
  { key: "bist", label: "BIST / Hisse" },
  { key: "makro", label: "Makro Ekonomi" },
  { key: "bulten", label: "Günün Bülteni" },
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

function formatTarih(tarih: string | null): string {
  if (!tarih) {
    return "";
  }
  const date = new Date(tarih);
  if (Number.isNaN(date.getTime())) {
    return tarih;
  }
  return date.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" });
}

function toArticle(item: NewsArticle, index: number): Article {
  return {
    id: item.id,
    category: kategoriToTab(item.kategori),
    featured: index === 0,
    time: formatTarih(item.tarih),
    source: item.sirket ?? "Polifin Bülten",
    symbol: item.symbol ?? undefined,
    title: item.baslik,
    summary: item.excerpt,
    body: item.body,
    image: item.image_url,
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

const holdingTimes = ["08:32", "10:47", "12:15", "14:03", "16:28", "17:41"];

function buildHoldingArticle(holding: Holding, index: number): NewsDetailArticle {
  const changePct = holding.daily_change_pct ?? 0;
  const direction = changePct < 0 ? "geriledi" : "yükseldi";
  const pct = Math.abs(changePct).toFixed(2);
  const priceText = holding.current_price.toLocaleString("tr-TR", { maximumFractionDigits: 2 });

  return {
    title: `${holding.asset_name} portföyünü etkiliyor`,
    source: "Polifin Piyasa Masası",
    time: holdingTimes[index % holdingTimes.length],
    symbol: holding.symbol,
    body: [
      `${holding.symbol} (${holding.asset_name}) bugünkü işlemlerde %${pct} ${direction} ve güncel fiyatı ${priceText} ${holding.currency} seviyesinden işlem görüyor.`,
      "Analistler, kısa vadeli fiyat hareketinin sektördeki genel eğilimle büyük ölçüde uyumlu olduğunu, pozisyon ağırlığı yüksek yatırımcıların portföy dengesini gözden geçirmesinde fayda olduğunu belirtiyor.",
      "Pozisyonun portföy içindeki payı ve toplam kâr/zarar etkisi Polifin risk motoru tarafından gün içinde güncellenmeye devam ediyor; önemli bir yön değişikliğinde bildirim gönderilecek.",
    ],
  };
}

export default function BultenPage() {
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]["key"]>("tumu");
  const [selectedArticle, setSelectedArticle] = useState<NewsDetailArticle | null>(null);
  const { data, loading, error, refetch } = useDashboard();
  const news = useAsyncData(() => getNews(50), []);

  const articles = useMemo(() => (news.data?.items ?? []).map(toArticle), [news.data]);

  const filtered = useMemo(
    () => (activeTab === "tumu" ? articles : articles.filter((article) => article.category === activeTab)),
    [activeTab, articles],
  );
  const featured = filtered.find((article) => article.featured);
  const featuredLogoMatch = featured ? matchNewsLogo(featured.symbol ?? featured.title) : null;
  const featuredSourceLogo = featured ? matchSourceLogo(featured.source) : null;
  const bulletinItems = filtered.filter((article) => !article.featured);
  const showPortfolio = activeTab === "tumu" || activeTab === "portfoy";

  if (loading || news.loading) {
    return <LoadingState label="Bülten yükleniyor" />;
  }

  if (error || !data) {
    return <ErrorState message={error ?? "Bülten verisi boş döndü."} onRetry={refetch} />;
  }

  if (news.error) {
    return <ErrorState message={news.error} onRetry={news.refetch} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">Bülten</h1>
        <p className="mt-1 text-sm app-muted">Portföyünle ve piyasayla ilgili güncel gelişmeler.</p>
      </div>

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
              {tab.label}
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
              <span>Öne Çıkan Bülten ·</span>
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
          <h2 className="mb-3 text-base font-semibold app-heading">Portföyden</h2>
          {data.holdings.length === 0 ? (
            <p className="text-sm app-muted">Portföyünde henüz bir varlık bulunmuyor.</p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {data.holdings.map((holding, index) => {
                const holdingArticle = buildHoldingArticle(holding, index);
                return (
                  <NewsCard
                    key={holding.symbol}
                    icon={<HoldingIcon />}
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
                    summary={`${holding.symbol} bugün %${Math.abs(holding.daily_change_pct ?? 0).toFixed(2)} ${
                      (holding.daily_change_pct ?? 0) < 0 ? "değer kaybetti" : "değer kazandı"
                    }. Pozisyonun güncel değeri portföy dağılımını etkileyebilir.`}
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
          <h2 className="mb-3 text-base font-semibold app-heading">Günün Bültenleri</h2>
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
    </div>
  );
}
