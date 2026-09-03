import type { PercentageBasketPreview } from "../../models/trading";

export type InfluencerBasketAllocation = {
  symbol: string;
  weightPct: number;
};

export type InfluencerBasket = {
  id: string;
  figureName: string;
  role?: { tr: string; en: string };
  photoSrc: string;
  photoFocus?: string;
  photoScale?: number;
  title: { tr: string; en: string };
  description: { tr: string; en: string };
  allocations: InfluencerBasketAllocation[];
};

export type InfluencerBasketOrderItem = {
  symbol: string;
  name: string;
  assetClass: string;
  currency: string;
  weightPct: number;
  quotedPriceTry: number;
  quantity: number;
  estimatedGross: number;
  estimatedReserve: number;
};

export type InfluencerBasketPlan = {
  basket: InfluencerBasket;
  items: InfluencerBasketOrderItem[];
  missingSymbols: string[];
  skippedSymbols: string[];
  availableBalance: number;
  investableGross: number;
  estimatedGross: number;
  estimatedReserve: number;
  remainingBalance: number;
};

const BASKET_DISPLAY_ORDER = [
  "feridun-aktas-coklu-varlik-demo",
  "warren-buffett-deger-demo",
  "ozgur-demirtas-makro-denge-demo",
  "tunc-satiroglu-trend-demo",
];

/**
 * These are explicitly fictional product demos, not portfolios published or
 * endorsed by the named people. Keeping the notice in the UI is mandatory.
 */
export const INFLUENCER_BASKETS: InfluencerBasket[] = [
  {
    id: "ozgur-demirtas-makro-denge-demo",
    figureName: "Özgür Demirtaş",
    role: {
      tr: "Prof. Dr. · Sabancı Üniversitesi Finans Kürsü Başkanı",
      en: "Professor · Chair of Finance, Sabancı University",
    },
    photoSrc: "/images/influencers/ozgur-demirtas.jpg",
    title: { tr: "Makro Denge Senaryosu", en: "Macro Balance Scenario" },
    description: {
      tr: "BIST hisseleri, kripto, kıymetli maden ve döviz ağırlıklı temsili makro dağılım.",
      en: "A sample macro allocation focused on BIST stocks, crypto, precious metals and FX.",
    },
    allocations: [
      { symbol: "THYAO", weightPct: 15 },
      { symbol: "TCELL", weightPct: 15 },
      { symbol: "GRAM_ALTIN", weightPct: 20 },
      { symbol: "GUMUS", weightPct: 15 },
      { symbol: "BTC", weightPct: 10 },
      { symbol: "USD/TRY", weightPct: 15 },
      { symbol: "EUR/TRY", weightPct: 10 },
    ],
  },
  {
    id: "tunc-satiroglu-trend-demo",
    figureName: "Tunç Şatıroğlu",
    role: {
      tr: "Finansal Analist · Kanal Finans Kurucusu",
      en: "Financial Analyst · Founder of Kanal Finans",
    },
    photoSrc: "/images/influencers/tunc-satiroglu.png",
    title: { tr: "Trend ve Teknik Denge Senaryosu", en: "Trend and Technical Balance Scenario" },
    description: {
      tr: "BIST sanayi ve savunma hisselerini emtia ve kriptoyla birleştiren temsili trend dağılımı.",
      en: "A sample trend allocation combining BIST industrial and defense stocks with commodities and crypto.",
    },
    allocations: [
      { symbol: "ASELS", weightPct: 20 },
      { symbol: "TUPRS", weightPct: 20 },
      { symbol: "EREGL", weightPct: 15 },
      { symbol: "SASA", weightPct: 10 },
      { symbol: "TOASO", weightPct: 10 },
      { symbol: "BAKIR", weightPct: 15 },
      { symbol: "BTC", weightPct: 10 },
    ],
  },
  {
    id: "warren-buffett-deger-demo",
    figureName: "Warren Buffett",
    role: {
      tr: "Yatırımcı · Berkshire Hathaway Yönetim Kurulu Başkanı",
      en: "Investor · Chairman of Berkshire Hathaway",
    },
    photoSrc: "/images/influencers/warren-buffett.jpg",
    title: { tr: "Değer Odaklı Senaryo", en: "Value-Focused Scenario" },
    description: {
      tr: "ABD ve BIST şirketlerini kıymetli maden ve dövizle tamamlayan uzun vadeli temsili dağılım.",
      en: "A long-term sample allocation combining US and BIST companies with precious metals and FX.",
    },
    allocations: [
      { symbol: "BRK-B", weightPct: 30 },
      { symbol: "JPM", weightPct: 20 },
      { symbol: "AAPL", weightPct: 15 },
      { symbol: "BIMAS", weightPct: 15 },
      { symbol: "KCHOL", weightPct: 10 },
      { symbol: "GUMUS", weightPct: 10 },
    ],
  },
  {
    id: "feridun-aktas-coklu-varlik-demo",
    figureName: "Feridun Aktaş",
    role: {
      tr: "Teknoloji Yöneticisi · Intertech CEO’su",
      en: "Technology Executive · CEO of Intertech",
    },
    photoSrc: "https://media.licdn.com/dms/image/v2/D4D22AQGYsuIo6i2w5A/feedshare-shrink_1280/B4DZoPx7AGJcAs-/0/1761201338536?e=2147483647&v=beta&t=cOlGbEyK2nxNDB8oY814ZwlwUaINqizMw96DRFmCLIg",
    photoFocus: "85% 12%",
    photoScale: 2.15,
    title: { tr: "Teknoloji ve Dijital Dönüşüm Senaryosu", en: "Technology and Digital Transformation Scenario" },
    description: {
      tr: "ABD teknoloji hisseleri ve dijital varlıklara odaklanan temsili büyüme dağılımı.",
      en: "A sample growth allocation focused on US technology stocks and digital assets.",
    },
    allocations: [
      { symbol: "MSFT", weightPct: 25 },
      { symbol: "NVDA", weightPct: 20 },
      { symbol: "AAPL", weightPct: 15 },
      { symbol: "GOOG", weightPct: 15 },
      { symbol: "META", weightPct: 10 },
      { symbol: "BTC", weightPct: 10 },
      { symbol: "USD/TRY", weightPct: 5 },
    ],
  },
].sort(
  (left, right) =>
    BASKET_DISPLAY_ORDER.indexOf(left.id) - BASKET_DISPLAY_ORDER.indexOf(right.id),
);

export function buildInfluencerBasketPlan(
  basket: InfluencerBasket,
  preview: PercentageBasketPreview,
): InfluencerBasketPlan {
  return {
    basket,
    items: preview.items.map((item) => ({
      symbol: item.symbol,
      name: item.asset_name,
      assetClass: item.asset_class,
      currency: item.currency,
      weightPct: item.weight_pct,
      quotedPriceTry: item.quoted_price_try,
      quantity: item.quantity,
      estimatedGross: item.estimated_gross,
      estimatedReserve: item.estimated_reserve,
    })),
    missingSymbols: preview.unavailable_symbols,
    skippedSymbols: preview.unaffordable_symbols,
    availableBalance: preview.available_balance,
    investableGross: preview.investable_gross,
    estimatedGross: preview.estimated_gross,
    estimatedReserve: preview.estimated_reserve,
    remainingBalance: preview.remaining_balance,
  };
}
