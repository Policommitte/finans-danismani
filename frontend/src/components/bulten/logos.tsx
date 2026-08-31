import type { ReactNode } from "react";

function TurkishAirlinesLogo() {
  return (
    <img
      src="/logos/thy.png.png"
      alt="Turkish Airlines"
      className="h-full w-full object-cover"
      style={{ objectPosition: "left center" }}
    />
  );
}

function BitcoinLogo() {
  return (
    <svg viewBox="0 0 64 64" preserveAspectRatio="xMidYMid meet" className="h-full w-full">
      <circle cx="32" cy="32" r="32" fill="#F7931A" />
      <path
        fill="#fff"
        d="M44.5 28.7c.6-4.1-2.5-6.3-6.8-7.8l1.4-5.6-3.4-.9-1.4 5.5c-.9-.2-1.8-.4-2.7-.7l1.4-5.5-3.4-.9-1.4 5.6c-.7-.2-1.5-.3-2.2-.5l-4.7-1.2-.9 3.6s2.5.6 2.5.6c1.4.3 1.6 1.3 1.6 2l-1.6 6.3.3.1-.3-.1-2.2 8.8c-.2.4-.6 1.1-1.6.8 0 0-2.5-.6-2.5-.6l-1.7 3.9 4.4 1.1c.8.2 1.6.4 2.4.6l-1.4 5.7 3.4.9 1.4-5.6c.9.2 1.8.5 2.7.7l-1.4 5.5 3.4.9 1.4-5.7c5.8 1.1 10.2.7 12-4.6 1.5-4.3-.1-6.7-3.1-8.3 2.2-.5 3.9-2 4.3-5zm-7.8 10.9c-1.1 4.3-8.4 2-10.8 1.4l1.9-7.7c2.4.6 10 1.8 8.9 6.3zm1.1-11c-1 3.9-7.1 1.9-9.1 1.4l1.8-7c2 .5 8.4 1.4 7.3 5.6z"
      />
    </svg>
  );
}

function SasaLogo() {
  return (
    <svg viewBox="0 0 200 80" preserveAspectRatio="xMidYMid meet" className="h-full w-full">
      <rect width="200" height="80" fill="#0018A8" />
      <text
        x="100"
        y="53"
        textAnchor="middle"
        fontFamily="Arial, Helvetica, sans-serif"
        fontWeight="800"
        fontSize="34"
        letterSpacing="2"
        fill="#fff"
      >
        SASA
      </text>
    </svg>
  );
}

export function BorsaIstanbulLogo() {
  return (
    <svg viewBox="0 0 200 200" preserveAspectRatio="xMidYMid meet" className="h-full w-full">
      <defs>
        <linearGradient id="bist-mark-gradient" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#6FD1DE" />
          <stop offset="1" stopColor="#00A0B0" />
        </linearGradient>
      </defs>
      <circle cx="100" cy="100" r="94" fill="url(#bist-mark-gradient)" />
      <path
        fill="#fff"
        d="M96 42c-24 22-37 45-33 70 3 17 16 29 33 27-13-7-20-19-18-33 2-15 15-25 16-41 .5-8-2-16-8-21-6 3-9 5-10-2z"
      />
      <path
        fill="#fff"
        d="M112 50c-22 20-32 42-27 66 3 15 15 26 30 25-12-7-19-18-17-31 2-14 13-24 14-38 .5-8-2-15-6-20-3-1 6-3 6-2z"
        opacity="0.9"
      />
      <rect x="88" y="52" width="18" height="18" fill="#fff" transform="rotate(45 97 61)" />
    </svg>
  );
}

export type NewsLogoMatch = {
  Logo: () => ReactNode;
  background: string;
  fill?: boolean;
};

//: Yeni bir hisse/varlik (ticker) eklerken buraya da bir marka logosu
//: eslesmesi eklemeyi unutma - eklenmezse kart jenerik bir ikonla gosterilir
//: (hata degil, sadece daha az ozgun gorunur). Bkz. thumbnails.tsx'teki
//: ayni amacli kapak-gorseli eslesmesi.
export function matchNewsLogo(seed: string): NewsLogoMatch | null {
  const s = seed.toUpperCase();

  if (s.includes("THYAO") || s.includes("THY") || s.includes("TÜRK HAVA")) {
    return { Logo: TurkishAirlinesLogo, background: "#FFF1F2" };
  }

  if (s.includes("BTC") || s.includes("BITCOIN")) {
    return { Logo: BitcoinLogo, background: "#FFF7ED" };
  }

  if (s.includes("SASA")) {
    return { Logo: SasaLogo, background: "#0018A8", fill: true };
  }

  if (s.includes("BIST") || s.includes("BORSA")) {
    return { Logo: BorsaIstanbulLogo, background: "#E6FBFA" };
  }

  return null;
}

export function matchSourceLogo(source: string): string | null {
  const s = source.toLowerCase();

  if (s.includes("bloomberg")) {
    return "/logos/bloomberg.png.png";
  }

  return null;
}
