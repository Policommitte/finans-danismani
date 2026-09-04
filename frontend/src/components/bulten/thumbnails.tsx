type Topic = "havacilik" | "sehir" | "sanayi" | "banka" | "grafik" | "kuresel" | "varlik";

const topicGradients: Record<Topic, [string, string]> = {
  havacilik: ["#0c4a6e", "#38bdf8"],
  sehir: ["#0f172a", "#334155"],
  sanayi: ["#1c1917", "#57534e"],
  banka: ["#172554", "#3b82f6"],
  grafik: ["#134e4a", "#14b8a6"],
  kuresel: ["#1e1b4b", "#7c3aed"],
  //: Belirgin bir konu/foto eslesmesi olmayan TUM varliklarin (ticker kodu
  //: THY/SASA/BTC gibi bilinen anahtar kelimelerle eslesmiyorsa - orn. EREGL,
  //: TUPRS, AAPL, BIMAS) dustugu GENEL varsayilan. Once buraya dusenler eskiden
  //: neredeyse gorunmez (opacity 0.06-0.08) iki daireyle "duz koyu arka plan"
  //: gibi gorunuyordu (bkz. bulten-kapak-gorseli-eksik hata raporu).
  varlik: ["#111827", "#3730a3"],
};

const topicIcons: Record<Topic, string> = {
  havacilik:
    '<g transform="translate(206,26) scale(3.1) rotate(12)" fill="#fff" fill-opacity="0.88"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></g>',
  sehir:
    '<g transform="translate(210,20)" fill="#fff" fill-opacity="0.85"><rect x="0" y="48" width="16" height="52"/><rect x="20" y="26" width="16" height="74"/><rect x="40" y="58" width="16" height="42"/><rect x="60" y="10" width="16" height="90"/><rect x="80" y="40" width="16" height="60"/></g>',
  sanayi:
    '<g transform="translate(205,42)" fill="#fff" fill-opacity="0.85"><rect x="0" y="30" width="80" height="38"/><rect x="10" y="8" width="10" height="22"/><rect x="30" y="0" width="10" height="30"/><rect x="50" y="14" width="10" height="16"/><circle cx="65" cy="-6" r="5" fill-opacity="0.5"/></g>',
  banka:
    '<g transform="translate(208,32)" fill="#fff" fill-opacity="0.85"><polygon points="40,0 80,22 0,22"/><rect x="6" y="24" width="9" height="46"/><rect x="22" y="24" width="9" height="46"/><rect x="38" y="24" width="9" height="46"/><rect x="54" y="24" width="9" height="46"/><rect x="70" y="24" width="9" height="46"/><rect x="0" y="72" width="80" height="9"/></g>',
  grafik:
    '<g transform="translate(200,28)" fill="#fff" fill-opacity="0.85"><rect x="0" y="52" width="16" height="32"/><rect x="22" y="32" width="16" height="52"/><rect x="44" y="14" width="16" height="70"/><rect x="66" y="38" width="16" height="46"/><polyline points="8,50 30,30 52,12 74,36" fill="none" stroke="#fff" stroke-opacity="0.55" stroke-width="3"/></g>',
  kuresel:
    '<g transform="translate(228,38)" fill="none" stroke="#fff" stroke-opacity="0.85" stroke-width="3"><circle cx="32" cy="32" r="32"/><ellipse cx="32" cy="32" rx="32" ry="13"/><line x1="0" y1="32" x2="64" y2="32"/><line x1="32" y1="0" x2="32" y2="64"/></g>',
  varlik:
    '<g transform="translate(202,30)" fill="#fff" fill-opacity="0.85"><rect x="0" y="16" width="8" height="46" rx="1.5"/><rect x="16" y="30" width="8" height="32" rx="1.5"/><rect x="32" y="4" width="8" height="58" rx="1.5"/><rect x="48" y="22" width="8" height="40" rx="1.5"/><rect x="64" y="12" width="8" height="50" rx="1.5"/><polyline points="4,14 20,28 36,2 52,20 68,10" fill="none" stroke="#fff" stroke-opacity="0.6" stroke-width="3"/></g>',
};

//: Basit, deterministik dize karistirici (hash) - AYNI seed HER ZAMAN AYNI
//: indeksi verir (bir varligin karti sayfa yenilense de degismez), ama
//: FARKLI seed'ler (orn. NVDA vs AAPL) buyuk ihtimalle FARKLI indekslere
//: duser. Kriptografik degil, yalnizca gorsel cesitlendirme icin.
function seedHash(seed: string): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return hash;
}

//: Backend'deki (services/news.py) HABER gorselleriyle AYNI dosyalar -
//: `/public/news/` her iki tarafca da paylasilir. Belirgin bir anahtar
//: kelime eslesmesi olmayan (ozellikle EREGL/TUPRS/AAPL/BIMAS gibi duz
//: ticker kodlari icin HICBIR ZAMAN eslesmeyen) hisse/ABD-Avrupa hissesi
//: kartlari, hepsi AYNI tek gradyan yerine bu havuzdan seed'e gore
//: DETERMINISTIK bir foto secer - boylece farkli hisseler farkli, ama
//: her hissenin kendi karti HER ZAMAN ayni gorunur.
const STOCK_PHOTO_POOL = [
  "/news/stock-exchange.jpg",
  "/news/data-center.jpg",
  "/news/car-assembly-line.jpg",
  "/news/agriculture-field.jpg",
  "/news/apartment-buildings.jpg",
  "/news/finance-coins-chart.jpg.png",
];

//: `models/portfolio.ts` Holding.asset_class degerleriyle birebir - bir
//: varligin SINIFI kesin bilindiginde (portfoy karti gibi) en guvenilir
//: eslesme budur; baslik anahtar kelimesi eslesmesinden ONCE denenir.
const ASSET_CLASS_PHOTO: Record<string, string> = {
  CRYPTO: "/news/crypto-coins.jpg.jfif",
  GOLD: "/news/gold-bar.jpg",
  FOREX: "/news/euro-banknotes.jpg",
  COMMODITY: "/news/oil-pumpjack.jpg",
};

export function assetClassPhoto(assetClass: string | undefined): string | null {
  return assetClass ? ASSET_CLASS_PHOTO[assetClass] ?? null : null;
}

//: YENI BIR HISSE/VARLIK (ticker) eklendiginde bu fonksiyona (veya
//: detectPhoto'ya) o ticker icin bir anahtar kelime eslesmesi eklemeyi
//: UNUTMA - aksi halde asagidaki jenerik "varlik" ikonuna duser (bkz.
//: topicThumbnail). Bu unutma HATA vermez, sadece konsola uyari basar.
function detectTopic(seed: string): Topic | null {
  const s = seed.toLowerCase();

  if (s.includes("hava") || s.includes("yolcu") || s.includes("thy") || s.includes("uçuş")) {
    return "havacilik";
  }

  if (s.includes("banka") && (s.includes("merkez") || s.includes("faiz") || s.includes("tcmb"))) {
    return "banka";
  }

  if (s.includes("bist") || s.includes("borsa") || s.includes("endeks") || s.includes("banka")) {
    return "sehir";
  }

  if (s.includes("sanayi") || s.includes("üretim") || s.includes("fabrika")) {
    return "sanayi";
  }

  if (s.includes("enflasyon") || s.includes("cari") || s.includes("ihracat") || s.includes("ithalat")) {
    return "grafik";
  }

  if (s.includes("küresel") || s.includes("global") || s.includes("kripto") || s.includes("btc") || s.includes("bitcoin")) {
    return "kuresel";
  }

  return null;
}

//: Backend'in `_KEYWORD_IMAGE_RULES`iyle (services/news.py) UYUMLU, ayni
//: yerel dosyalari kullanan konu kurallari - bir haberin/varligin
//: baslik+sembol metninde bu kelimelerden biri geciyorsa dogrudan eslesir.
const KEYWORD_PHOTO_RULES: Array<[string[], string]> = [
  [["thy", "hava", "yolcu"], "/news/thy-plane.jpg.webp"],
  [["sasa"], "/news/sasa-factory.jpg.jfif"],
  [["btc", "bitcoin", "kripto"], "/news/crypto-coins.jpg.jfif"],
  [["altın", "altin"], "/news/gold-bar.jpg"],
  [["dolar", "euro", "avro", "döviz", "doviz"], "/news/euro-banknotes.jpg"],
  [["petrol", "brent", "akaryakıt", "akaryakit", "benzin"], "/news/oil-pumpjack.jpg"],
  [["otomotiv", "otomobil"], "/news/car-assembly-line.jpg"],
  [["yapay zeka", "teknoloji", "yazılım", "yazilim"], "/news/data-center.jpg"],
  [["tarım", "tarim", "gıda", "gida"], "/news/agriculture-field.jpg"],
  [["emlak", "konut", "gayrimenkul"], "/news/apartment-buildings.jpg"],
  [["merkez", "faiz", "enflasyon", "tcmb", "tüik", "cari"], "/news/tcmb-economy.jpg.jpg"],
  [["borsa", "bist", "hisse senedi", "gong"], "/news/stock-exchange.jpg"],
  [["küresel", "global", "piyasa"], "/news/finance-coins-chart.jpg.png"],
];

export function detectPhoto(seed: string): string | null {
  const s = seed.toLowerCase();
  for (const [keywords, photo] of KEYWORD_PHOTO_RULES) {
    if (keywords.some((keyword) => s.includes(keyword))) {
      return photo;
    }
  }
  return null;
}

export function newsThumbnail(seed: string) {
  return detectPhoto(seed) ?? topicThumbnail(seed);
}

//: Portfoy kartlari icin: varlik sinifi -> anahtar kelime -> (hala
//: eslesmediyse) sembole gore SABIT bir gercek fotograf. `topicThumbnail`
//: SVG ikonu yalnizca hicbiri tutmadiginda (COK nadir - STOCK/USA_STOCK/
//: EU_STOCK disindaki siniflar zaten ASSET_CLASS_PHOTO'da) devreye girer.
export function holdingThumbnail(seed: string, assetClass?: string) {
  return (
    assetClassPhoto(assetClass)
    ?? detectPhoto(seed)
    ?? STOCK_PHOTO_POOL[seedHash(seed) % STOCK_PHOTO_POOL.length]
  );
}

//: STOCK_PHOTO_POOL yalnizca 6 gercek fotograftan olustugu icin, 6'dan
//: fazla varligi olan bir portfoyde iki hissenin AYNI fotografa dusmesi
//: istatistiksel olarak beklenir (dogum gunu paradoksu - 6 kutuda 6 oge
//: icin carpisma olasiligi >%98). Bu durumda bile kartlarin birbirinden
//: AYRISTIRILABILIR gorunmesi icin, sadece havuzdan sectigimiz (yani
//: varlik sinifi/anahtar kelime ile GERCEKTEN eslesmeyen) kartlara,
//: seed'e gore deterministik bir renk tonu (hue-rotate) uygulanir - ayni
//: foto, farkli hisseler icin farkli renklerde gorunur. Gercek eslesmeler
//: (altin/kripto/doviz gibi) rengi DOGRU temsil ettigi icin dokunulmaz.
export function holdingImageFilter(seed: string, assetClass?: string): string | undefined {
  if (assetClassPhoto(assetClass) || detectPhoto(seed)) {
    return undefined;
  }
  const hash = seedHash(seed);
  const hueDeg = hash % 360;
  const saturationPct = 100 + (Math.floor(hash / 360) % 40); // 100-139
  return `hue-rotate(${hueDeg}deg) saturate(${saturationPct}%)`;
}

export function topicThumbnail(seed: string) {
  //: Bilinen bir konu (havacilik/banka/... - anlatimsal Turkce anahtar
  //: kelimelerden gelir) eslesmezse - ozellikle EREGL/TUPRS/AAPL/BIMAS gibi
  //: duz ticker kodlari icin HICBIR zaman eslesmez - "varlik" (genel hisse/
  //: finansal varlik) konusuna dusulur. Eskiden bu durumda gradyan rastgele
  //: (hashSeed ile) seciliyor VE ikon neredeyse gorunmez opacity'deydi
  //: (0.06-0.08) - sonuc "duz koyu arka plan" gibi algilaniyordu. Artik HER
  //: eslesmeyen varlik ayni, belirgin (opacity 0.85) hisse/grafik ikonuyla
  //: tutarli bir kapak gorseli alir.
  const matchedTopic = detectTopic(seed);
  if (!matchedTopic && process.env.NODE_ENV !== "production") {
    // eslint-disable-next-line no-console
    console.warn(
      `UYARI: "${seed}" için kapak görseli eşleşmesi tanımlı değil, jenerik ikon kullanılıyor. ` +
        "Yeni bir hisse/varlık eklediysen thumbnails.tsx'teki detectPhoto/detectTopic'e de eşleşme ekle.",
    );
  }
  const topic = matchedTopic ?? "varlik";
  const [from, to] = topicGradients[topic];
  const icon = topicIcons[topic];

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="140" viewBox="0 0 300 140">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="${from}" />
        <stop offset="1" stop-color="${to}" />
      </linearGradient>
    </defs>
    <rect width="300" height="140" fill="url(#g)" />
    ${icon}
  </svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}
