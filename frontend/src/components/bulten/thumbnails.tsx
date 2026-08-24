const gradientPalette: [string, string][] = [
  ["#172554", "#1d4ed8"],
  ["#0f172a", "#0891b2"],
  ["#111827", "#334155"],
  ["#1d4ed8", "#60a5fa"],
  ["#172554", "#7c3aed"],
];

type Topic = "havacilik" | "sehir" | "sanayi" | "banka" | "grafik" | "kuresel";

const topicGradients: Record<Topic, [string, string]> = {
  havacilik: ["#0c4a6e", "#38bdf8"],
  sehir: ["#0f172a", "#334155"],
  sanayi: ["#1c1917", "#57534e"],
  banka: ["#172554", "#3b82f6"],
  grafik: ["#134e4a", "#14b8a6"],
  kuresel: ["#1e1b4b", "#7c3aed"],
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
};

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

function hashSeed(seed: string) {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function detectPhoto(seed: string): string | null {
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
  const topic = detectTopic(seed);
  const [from, to] = topic ? topicGradients[topic] : gradientPalette[hashSeed(seed) % gradientPalette.length];
  const icon = topic
    ? topicIcons[topic]
    : '<circle cx="252" cy="28" r="46" fill="#ffffff" fill-opacity="0.08" /><circle cx="34" cy="118" r="58" fill="#ffffff" fill-opacity="0.06" />';

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
