import type { ReactNode } from "react";

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

const socialLinks: { label: string; href: string; icon: ReactNode }[] = [
  {
    label: "Facebook",
    href: "#",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M13.5 9H15V6.2c-.3-.04-1.32-.13-2.5-.13-2.48 0-4.18 1.51-4.18 4.29V12H6v3h2.32v7h3V15h2.4l.38-3h-2.78v-1.63c0-.87.24-1.37 1.18-1.37z" />
      </svg>
    ),
  },
  {
    label: "Instagram",
    href: "#",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
        <circle cx="12" cy="12" r="3.7" />
        <circle cx="17.1" cy="6.9" r="1" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    label: "X",
    href: "#",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M4 4h3.6l4.2 5.7L16.6 4H20l-6.2 7.6L20.3 20h-3.6l-4.5-6.1L7 20H3.6l6.6-8.1z" />
      </svg>
    ),
  },
  {
    label: "YouTube",
    href: "#",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="6.5" width="18" height="11" rx="3.5" />
        <path d="M10.5 9.7v4.6l4-2.3z" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    label: "LinkedIn",
    href: "#",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24">
        <rect width="24" height="24" rx="4.5" fill="#0A66C2" />
        <path
          fill="#fff"
          d="M7.35 9.6H4.7v9.6h2.65V9.6Zm-1.32-1.2a1.53 1.53 0 1 0 0-3.06 1.53 1.53 0 0 0 0 3.06ZM9.15 9.6h2.54v1.31h.04c.35-.66 1.22-1.36 2.51-1.36 2.68 0 3.18 1.77 3.18 4.06v5.59h-2.65v-4.95c0-1.18-.02-2.7-1.64-2.7-1.65 0-1.9 1.29-1.9 2.62v5.03H9.15V9.6Z"
        />
      </svg>
    ),
  },
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
            <a
              href="#"
              className="rounded-full border border-white/15 bg-white/5 px-3 py-1.5 font-medium transition hover:bg-white/10 hover:text-white"
            >
              Sıkça Sorulan Sorular
            </a>
          </div>

          <div className="flex items-center gap-3">
            {socialLinks.map((social) => (
              <a
                key={social.label}
                href={social.href}
                aria-label={social.label}
                className="grid h-9 w-9 place-items-center rounded-full bg-white text-[var(--color-panel-dark)] transition hover:-translate-y-0.5 hover:shadow-md"
              >
                {social.icon}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
