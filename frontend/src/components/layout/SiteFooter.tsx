"use client";

import Link from "next/link";
import { useRef, useState } from "react";
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
      { label: "Gizlilik Politikası", href: "/gizlilik-politikasi" },
      { label: "Sıkça Sorulan Sorular", href: "/destek#sss" },
    ],
    help: "Yardım",
    about: "Hakkımızda",
    aboutEyebrow: "POLİFİN HAKKINDA",
    aboutTitle: "Finansal kararları daha anlaşılır hale getiren kişisel asistan.",
    aboutBody: "Polifin; portföy takibini, piyasa verilerini ve yapay zeka destekli finansal içgörüleri aynı deneyimde bir araya getirir. Amacımız, karmaşık finansal bilgileri kullanıcıların daha rahat takip edebileceği açık ve düzenli bir yapıya dönüştürmektir.",
    closeAbout: "Hakkımızda bölümünü kapat",
    highlights: [
      { index: "01", title: "Portföy görünümü", description: "Varlık dağılımını, performansı ve risk göstergelerini tek yerde anlaşılır biçimde sunar." },
      { index: "02", title: "Piyasa takibi", description: "Endeksleri, döviz kurlarını ve öne çıkan varlıkları güncel piyasa verileriyle izlemeyi kolaylaştırır." },
      { index: "03", title: "AI destekli içgörü", description: "Finansal verileri ve haber akışını kişisel portföy bağlamında yorumlayan bir asistan deneyimi sağlar." },
    ],
    navLabel: "Alt menü",
    disclaimerLead: "Polifin, geliştirme aşamasındaki bir",
    disclaimerStrong: "kişisel finans asistanı prototipidir",
    disclaimerEnd: "Gösterilen veriler temsilidir; yatırım tavsiyesi niteliği taşımaz.",
  },
  en: {
    links: [
      { label: "Privacy Policy", href: "/gizlilik-politikasi" },
      { label: "Frequently Asked Questions", href: "/destek#sss" },
    ],
    help: "Help",
    about: "About Us",
    aboutEyebrow: "ABOUT POLIFIN",
    aboutTitle: "A personal assistant that makes financial decisions easier to understand.",
    aboutBody: "Polifin brings portfolio tracking, market data and AI-supported financial insights together in one experience. Our aim is to turn complex financial information into a clear and organized structure that is easier to follow.",
    closeAbout: "Close the About Us section",
    highlights: [
      { index: "01", title: "Portfolio overview", description: "Presents asset allocation, performance and risk indicators clearly in one place." },
      { index: "02", title: "Market tracking", description: "Makes it easier to follow indices, exchange rates and featured assets with current market data." },
      { index: "03", title: "AI-supported insight", description: "Provides an assistant experience that interprets financial data and news in the context of a personal portfolio." },
    ],
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
  const [aboutOpen, setAboutOpen] = useState(false);
  const footerRef = useRef<HTMLElement | null>(null);

  function setAboutVisibility(nextOpen: boolean) {
    const anchorTop = footerRef.current?.getBoundingClientRect().top;
    setAboutOpen(nextOpen);

    if (anchorTop == null) {
      return;
    }

    const footerAnchorTop = anchorTop;
    const startedAt = performance.now();

    function keepFooterAnchored(now: number) {
      const footer = footerRef.current;
      if (!footer) {
        return;
      }

      const offset = footer.getBoundingClientRect().top - footerAnchorTop;
      if (Math.abs(offset) > 0.5) {
        window.scrollBy(0, offset);
      }

      if (now - startedAt < 550) {
        window.requestAnimationFrame(keepFooterAnchored);
      }
    }

    window.requestAnimationFrame(keepFooterAnchored);
  }

  function toggleAbout() {
    setAboutVisibility(!aboutOpen);
  }

  return (
    <div className={`${className} [overflow-anchor:none]`}>
      <div
        className={`grid transition-[grid-template-rows] duration-500 ease-in-out ${
          aboutOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
          <section
            id="hakkimizda"
            aria-hidden={!aboutOpen}
            inert={!aboutOpen}
            className="scroll-mt-24 border-t app-border app-card-muted"
          >
            <div className="mx-auto max-w-7xl px-6 py-14 md:px-10 md:py-16">
              <div className="flex items-start justify-between gap-8">
                <div className="max-w-4xl">
                  <p className="text-sm font-black tracking-wide app-primary-text">{text.aboutEyebrow}</p>
                  <h2 className="mt-4 max-w-3xl text-3xl font-black leading-tight app-heading md:text-4xl">
                    {text.aboutTitle}
                  </h2>
                  <p className="mt-5 max-w-3xl text-base leading-7 app-muted md:text-lg">
                    {text.aboutBody}
                  </p>
                </div>
                <button
                  type="button"
                  aria-label={text.closeAbout}
                  onClick={() => setAboutVisibility(false)}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border app-border text-xl app-muted transition hover:bg-[var(--color-surface)] hover:text-[var(--color-heading)]"
                >
                  x
                </button>
              </div>

              <div className="mt-12 grid border-t app-border md:grid-cols-3">
                {text.highlights.map((item) => (
                  <div
                    key={item.index}
                    className="border-b app-border py-7 md:border-b-0 md:border-r md:px-7 md:first:pl-0 md:last:border-r-0 md:last:pr-0"
                  >
                    <div className="text-xs font-black app-primary-text">{item.index}</div>
                    <h3 className="mt-3 text-lg font-black app-heading">{item.title}</h3>
                    <p className="mt-3 text-sm leading-6 app-muted">{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      </div>

      <footer ref={footerRef} className="bg-[var(--color-market-bar)] px-4 py-8">
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
            <button
              type="button"
              aria-expanded={aboutOpen}
              aria-controls="hakkimizda"
              onClick={toggleAbout}
              className={`w-fit text-left transition hover:text-[var(--color-market-text)] ${
                aboutOpen ? "text-[var(--color-market-text)]" : ""
              }`}
            >
              {text.about}
            </button>
            {text.links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="w-fit text-left transition hover:text-[var(--color-market-text)]"
              >
                {link.label}
              </Link>
            ))}
            {onStartTour ? (
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
