type SiteFooterProps = {
  className?: string;
};

const socialLinks = [
  { label: "Facebook", src: "/social/facebook.png" },
  { label: "Instagram", src: "/social/instagram.jpg" },
  { label: "X", src: "/social/x.png" },
  { label: "YouTube", src: "/social/youtube.png" },
  { label: "LinkedIn", src: "/social/linkedin.png" },
];

const footerLinks = [
  "Hakkımızda",
  "Gizlilik Politikası",
  "Sıkça Sorulan Sorular",
];

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

export function SiteFooter({ className = "" }: SiteFooterProps) {
  return (
    <footer className={`bg-[var(--color-market-bar)] px-4 py-8 ${className}`}>
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

        <nav aria-label="Alt menü" className="grid gap-2 text-sm font-semibold sm:grid-cols-2 lg:grid-cols-1">
          {footerLinks.map((link) => (
            <button
              key={link}
              type="button"
              className="w-fit text-left transition hover:text-[var(--color-market-text)]"
            >
              {link}
            </button>
          ))}
        </nav>

        <p className="max-w-2xl text-left text-sm leading-6 lg:text-right">
          Polifin, geliştirme aşamasındaki bir{" "}
          <span className="font-black text-[var(--color-market-text)]">kişisel finans asistanı prototipidir</span>.
          Gösterilen veriler temsilidir; yatırım tavsiyesi niteliği taşımaz. © 2026 Polifin.
        </p>
      </div>
    </footer>
  );
}
