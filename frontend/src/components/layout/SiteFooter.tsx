"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage } from "../../contexts/LanguageContext";

type SiteFooterProps = {
  className?: string;
  onStartTour?: () => void;
};

const socialLinks = [
  { label: "Facebook", src: "/social/facebook.png" },
  { label: "Instagram", src: "/social/instagram.jpg" },
  { label: "X", src: "/social/x.png" },
  { label: "YouTube", src: "/social/youtube.png" },
  { label: "LinkedIn", src: "/social/linkedin.png" },
];

const footerCopy = {
  tr: {
    links: [
      { label: "Hakkımızda", href: "/hakkimizda" },
      { label: "Gizlilik Politikası", href: "/gizlilik-politikasi" },
      { label: "Sıkça Sorulan Sorular", href: "/destek#sss" },
    ],
    help: "Yardım",
    navLabel: "Alt menü",
    disclaimerLead: "Polifin, geliştirme aşamasındaki bir",
    disclaimerStrong: "kişisel finans asistanı prototipidir",
    disclaimerEnd: "Gösterilen veriler temsilidir; yatırım tavsiyesi niteliği taşımaz.",
  },
  en: {
    links: [
      { label: "About Us", href: "/hakkimizda" },
      { label: "Privacy Policy", href: "/gizlilik-politikasi" },
      { label: "Frequently Asked Questions", href: "/destek#sss" },
    ],
    help: "Help",
    navLabel: "Footer navigation",
    disclaimerLead: "Polifin is a",
    disclaimerStrong: "personal finance assistant prototype",
    disclaimerEnd: "The data shown is representative and does not constitute investment advice.",
  },
};

function PhoneIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24" fill="none">
      <path
        d="M6.6 4.5 9 6.9 7.7 9c.9 1.8 2.5 3.4 4.3 4.3l2.1-1.3 2.4 2.4-.8 3.1c-.2.7-.8 1.1-1.5 1A12.4 12.4 0 0 1 5.5 9.8c-.1-.7.3-1.3 1-1.5l.1-3.8Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.8"
      />
    </svg>
  );
}

function PinIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 21s6-5.2 6-11a6 6 0 1 0-12 0c0 5.8 6 11 6 11Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.8"
      />
      <circle cx="12" cy="10" r="2" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function SiteFooter({ className = "", onStartTour }: SiteFooterProps) {
  const { language } = useLanguage();
  const text = footerCopy[language];
  //: `onStartTour` sunucuda da fonksiyon olarak gecer (props aninda ayni),
  //: ama turu "mount olmus" DOM'a (Sidebar/nav data-tour hedefleri) baglayan
  //: ProductTour sadece client'ta anlamli - bu yuzden ilk render'i (server VE
  //: client'in ilk boyasi) her zaman ayni "/destek" Link'ine sabitleriz, buton
  //: SADECE mount sonrasi devreye girer. Boylece hydration'da yapisal fark
  //: (server'da Link, client'ta button) hic olusmaz.
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className={className}>
      <footer className="bg-[var(--color-market-bar)] px-4 py-8">
        <div className="mx-auto grid max-w-7xl gap-8 text-[var(--color-market-muted)] lg:grid-cols-[1fr_1fr_1.15fr]">
          <div className="flex flex-col gap-5">
            <div className="flex flex-wrap items-center gap-5 text-sm font-semibold">
              <span className="flex items-center gap-2">
                <PhoneIcon />
                0850 255 20 00
              </span>
              <span className="flex items-center gap-2">
                <PinIcon />
                Kurtköy / İstanbul
              </span>
            </div>

            <div className="flex items-center gap-4">
              {socialLinks.map((link) => (
                <button
                  key={link.label}
                  type="button"
                  aria-label={link.label}
                  className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-full bg-transparent shadow-sm transition hover:-translate-y-0.5 hover:brightness-110"
                >
                  <img src={link.src} alt="" className="h-8 w-8 rounded-full object-cover" />
                </button>
              ))}
            </div>
          </div>

          <nav aria-label={text.navLabel} className="grid gap-2 text-sm font-semibold sm:grid-cols-2 lg:grid-cols-1">
            {text.links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="w-fit text-left transition hover:text-[var(--color-market-text)]"
              >
                {link.label}
              </Link>
            ))}
            {mounted && onStartTour ? (
              <button
                type="button"
                onClick={onStartTour}
                className="w-fit text-left transition hover:text-[var(--color-market-text)]"
              >
                {text.help}
              </button>
            ) : (
              <Link href="/destek" className="w-fit text-left transition hover:text-[var(--color-market-text)]">
                {text.help}
              </Link>
            )}
          </nav>

          <p className="max-w-2xl text-left text-sm leading-6 lg:text-right">
            {text.disclaimerLead}{" "}
            <span className="font-black text-[var(--color-market-text)]">{text.disclaimerStrong}</span>.{" "}
            {text.disclaimerEnd} © 2026 Polifin.
          </p>
        </div>
      </footer>
    </div>
  );
}
