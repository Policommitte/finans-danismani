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

export function detectPhoto(seed: string): string | null {
  const s = seed.toLowerCase();

  if (s.includes("thy") || s.includes("hava") || s.includes("yolcu")) {
    return "/news/thy-plane.jpg.webp";
  }

  if (s.includes("sasa")) {
    return "/news/sasa-factory.jpg.jfif";
  }

  if (s.includes("btc") || s.includes("bitcoin") || s.includes("kripto")) {
    return "/news/crypto-coins.jpg.jfif";
  }

  if (s.includes("merkez") || s.includes("faiz") || s.includes("enflasyon") || s.includes("tcmb") || s.includes("tüik") || s.includes("cari")) {
    return "/news/tcmb-economy.jpg.jpg";
  }

  if (s.includes("küresel") || s.includes("global") || s.includes("piyasa")) {
    return "/news/finance-coins-chart.jpg.png";
  }

  return null;
}

export function newsThumbnail(seed: string) {
  return detectPhoto(seed) ?? topicThumbnail(seed);
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
