import Link from "next/link";

function PhoneIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.362 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.338 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  );
}

function PinIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

const socialLinks = [
  { label: "Facebook", src: "/social/facebook.png" },
  { label: "Instagram", src: "/social/instagram.jpg" },
  { label: "X", src: "/social/x.png" },
  { label: "YouTube", src: "/social/youtube.png" },
  { label: "LinkedIn", src: "/social/linkedin.png" },
];

export function Footer() {
  return (
    <footer className="mt-6 bg-[var(--color-panel-dark)] text-white">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-start gap-6 px-4 py-5 pr-20">
        <p className="max-w-md text-xs text-white/55">
          Bu bir <strong className="text-white/80">UI konsept (mock)</strong> çalışmasıdır; yatırım tavsiyesi değildir; tüm veriler
          temsilidir. © 2026 Polifin.
        </p>

        <div className="ml-auto flex flex-col items-end gap-3">
          <div className="flex flex-wrap items-center justify-end gap-x-5 gap-y-2 text-xs text-white/70">
            <a href="tel:+908502552000" className="flex items-center gap-1.5 transition hover:text-white">
              <PhoneIcon />
              0850 255 20 00
            </a>
            <span className="flex items-center gap-1.5">
              <PinIcon />
              Kurtköy / İstanbul
            </span>
            <Link
              href="/destek#sss"
              className="rounded-full border border-white/15 bg-white/5 px-3 py-1.5 font-medium transition hover:bg-white/10 hover:text-white"
            >
              Sıkça Sorulan Sorular
            </Link>
          </div>

          <div className="flex items-center gap-3">
            {socialLinks.map((social) => (
              <a
                key={social.label}
                href="#"
                aria-label={social.label}
                className="grid h-9 w-9 place-items-center overflow-hidden rounded-full shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <img src={social.src} alt="" className="h-9 w-9 rounded-full object-cover" />
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
