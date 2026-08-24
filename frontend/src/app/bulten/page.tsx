"use client";

import { useMemo, useState } from "react";
import { BorsaIstanbulLogo, matchNewsLogo, matchSourceLogo } from "../../components/bulten/logos";
import { NewsCard } from "../../components/bulten/NewsCard";
import { NewsDetailModal, type NewsDetailArticle } from "../../components/bulten/NewsDetailModal";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { useDashboard } from "../../hooks/useDashboard";
import type { Holding } from "../../models/portfolio";

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
};

const tabs: { key: "tumu" | Category; label: string }[] = [
  { key: "tumu", label: "Tümü" },
  { key: "portfoy", label: "Portföyüm" },
  { key: "bist", label: "BIST / Hisse" },
  { key: "makro", label: "Makro Ekonomi" },
  { key: "bulten", label: "Günün Bülteni" },
];

const articles: Article[] = [
  {
    id: "featured-1",
    category: "bulten",
    featured: true,
    time: "09:14",
    source: "Bloomberg HT",
    symbol: "BIST",
    title: "BIST 100 güne yatay başladı, bankacılık hisseleri öne çıktı",
    summary:
      "Yurt içi piyasalarda güne yatay bir seyirle başlandı. Bankacılık endeksi %1,2 primli açılırken, yurt dışı faiz beklentileri gün içinde takip edilecek. Analistler öğleden sonra açıklanacak enflasyon verisinin oynaklığı artırabileceğini belirtiyor.",
    body: [
      "Borsa İstanbul'da BIST 100 endeksi güne önceki kapanışa yakın, yatay bir seyirle başladı. Açılışın ardından bankacılık endeksi %1,2 primli seyrederek genel endeksin üzerinde bir performans sergiledi.",
      "Piyasa yapıcılar, yurt dışında beklenen faiz kararlarının ve öğleden sonra açıklanacak yurt içi enflasyon verisinin gün içi oynaklığı artırabileceği uyarısında bulundu. Yabancı yatırımcı işlemlerinde net bir yön henüz gözlenmiyor.",
      "Teknik analistler, endeksin kısa vadeli direnç seviyesinin üzerinde kalıcı olması durumunda yükseliş eğiliminin güçlenebileceğini, aksi halde kâr satışlarının gündeme gelebileceğini belirtiyor.",
    ],
  },
  {
    id: "bist-1",
    category: "bist",
    time: "13:07",
    source: "Reuters",
    title: "Sanayi üretiminde beklenti üstü artış",
    summary:
      "Sanayi üretim endeksi yıllık bazda %4,8 artarak piyasa beklentisinin üzerinde geldi. İhracata dayalı sektörlerde ivmelenme dikkat çekiyor.",
    body: [
      "Türkiye İstatistik Kurumu tarafından açıklanan verilere göre sanayi üretim endeksi yıllık bazda %4,8 artış kaydederek piyasa beklentisi olan %3,2'nin belirgin şekilde üzerinde gerçekleşti.",
      "Alt sektör detaylarında, ihracata dayalı imalat kollarında ivmelenme dikkat çekerken, dayanıklı tüketim malları üretiminde de toparlanma sinyalleri gözlendi. Analistler bu görünümün büyüme tahminlerine yukarı yönlü katkı sağlayabileceğini değerlendiriyor.",
      "Veri sonrası piyasada sanayi endeksine dayalı hisselerde sınırlı alım ilgisi görüldü; kurum raporlarında verinin orta vadeli görünümü desteklediği ifade edildi.",
    ],
  },
  {
    id: "bist-2",
    category: "bist",
    time: "08:41",
    source: "Anadolu Ajansı",
    symbol: "THYAO",
    title: "Havacılık sektöründe yolcu sayıları rekor kırdı",
    summary: "Yaz sezonuyla birlikte iç ve dış hat yolcu sayılarında geçen yıla göre çift haneli büyüme kaydedildi.",
    body: [
      "Yaz sezonunun etkisiyle havayolu taşımacılığında yolcu sayıları rekor seviyelere ulaştı. İç ve dış hat toplam yolcu sayısı geçen yılın aynı dönemine göre çift haneli oranda büyüme kaydetti.",
      "Sektör temsilcileri, doluluk oranlarındaki artışın birim başına gelirlere olumlu yansıdığını, yakıt maliyetlerindeki nispi istikrarın da kâr marjlarını desteklediğini belirtti.",
      "Öte yandan analistler, önümüzdeki çeyrekte baz etkisinin normalleşmesiyle büyüme oranının kademeli olarak yavaşlayabileceğine dikkat çekiyor; yine de yıl geneli görünümün pozitif kaldığı vurgulanıyor.",
    ],
  },
  {
    id: "makro-1",
    category: "makro",
    time: "13:52",
    source: "Foreks Haber",
    title: "Merkez Bankası faiz kararı bu hafta açıklanacak",
    summary:
      "Piyasa katılımcılarının çoğunluğu politika faizinin sabit tutulmasını beklerken, karar sonrası açıklanacak metin yakından izlenecek.",
    body: [
      "Türkiye Cumhuriyet Merkez Bankası'nın bu hafta gerçekleştireceği Para Politikası Kurulu toplantısı öncesinde piyasa katılımcılarının büyük çoğunluğu politika faizinin mevcut seviyede sabit tutulmasını bekliyor.",
      "Karardan çok, toplantı sonrası yayımlanacak metnin dili yakından izlenecek; özellikle enflasyon patikasına ilişkin ileriye dönük yönlendirmenin piyasa fiyatlamalarında belirleyici olması bekleniyor.",
      "Bazı kurumlar, yıl sonuna kadar sınırlı bir indirim alanı olduğunu, ancak bunun küresel likidite koşullarına ve yurt içi enflasyon seyrine bağlı kalacağını değerlendiriyor.",
    ],
  },
  {
    id: "makro-2",
    category: "makro",
    time: "09:58",
    source: "Dünya Gazetesi",
    title: "Cari işlemler açığı beklentilerin altında kaldı",
    summary:
      "Aylık cari işlemler açığı, enerji hariç dengede iyileşme sayesinde piyasa tahminlerinin altında gerçekleşti.",
    body: [
      "Açıklanan ödemeler dengesi verilerine göre aylık cari işlemler açığı piyasa beklentisinin altında gerçekleşti. Enerji hariç cari dengede gözlenen iyileşme, açığın sınırlı kalmasında belirleyici oldu.",
      "Turizm gelirlerindeki güçlü seyrin de dengeyi desteklediği belirtilirken, ithalat talebinin yıl genelinde ölçülü kalması analistlerce olumlu karşılandı.",
      "Kurumlar, mevcut eğilimin sürmesi halinde yıl sonu cari açık/GSYH oranı tahminlerinde aşağı yönlü revizyon yapılabileceğini ifade ediyor.",
    ],
  },
  {
    id: "bulten-2",
    category: "bulten",
    time: "18:22",
    source: "Bloomberg HT",
    symbol: "BTC",
    title: "Küresel piyasalarda risk iştahı toparlanıyor",
    summary:
      "ABD borsalarındaki pozitif kapanışın ardından Asya piyasaları da yükselişle güne başladı. Emtia fiyatlarında karışık bir seyir izleniyor.",
    body: [
      "ABD borsalarının pozitif bir kapanış gerçekleştirmesinin ardından Asya piyasaları da güne alıcılı bir seyirle başladı. Küresel risk iştahındaki toparlanma, gelişmekte olan piyasa para birimlerine de sınırlı destek sağladı.",
      "Kripto para piyasalarında Bitcoin, artan risk iştahıyla birlikte güne yükselişle başlarken, emtia tarafında fiyatlar karışık bir görünüm sergiliyor; enerji fiyatlarında sınırlı gerileme, değerli metallerde ise yatay seyir dikkat çekiyor.",
      "Analistler, bu hafta açıklanacak küresel enflasyon verilerinin risk iştahındaki toparlanmanın kalıcılığı açısından belirleyici olacağını değerlendiriyor.",
    ],
  },
];

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

  const filtered = useMemo(
    () => (activeTab === "tumu" ? articles : articles.filter((article) => article.category === activeTab)),
    [activeTab],
  );
  const featured = filtered.find((article) => article.featured);
  const featuredLogoMatch = featured ? matchNewsLogo(featured.symbol ?? featured.title) : null;
  const featuredSourceLogo = featured ? matchSourceLogo(featured.source) : null;
  const bulletinItems = filtered.filter((article) => !article.featured);
  const showPortfolio = activeTab === "tumu" || activeTab === "portfoy";

  if (loading) {
    return <LoadingState label="Bülten yükleniyor" />;
  }

  if (error || !data) {
    return <ErrorState message={error ?? "Bülten verisi boş döndü."} onRetry={refetch} />;
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
                symbol={article.symbol}
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
