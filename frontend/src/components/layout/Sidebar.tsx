"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "../../contexts/LanguageContext";

type NavItem = {
  href: string;
  label: { tr: string; en: string };
  icon: string;
  tourId?: string;
};

const mainLinks: NavItem[] = [
  { href: "/", label: { tr: "Ana Sayfa", en: "Home" }, icon: "/ana-sayfa.svg", tourId: "nav-home" },
  {
    href: "/dashboard",
    label: { tr: "Genel Bakış", en: "Overview" },
    icon: "/analiz.svg",
    tourId: "nav-dashboard",
  },
  { href: "/bulten", label: { tr: "Bülten", en: "Newsletter" }, icon: "/bulten.svg", tourId: "nav-bulten" },
  { href: "/market", label: { tr: "Piyasalar", en: "Markets" }, icon: "/piyasa.svg", tourId: "nav-market" },
];

const utilityLinks: NavItem[] = [
  { href: "/profile", label: { tr: "Profil", en: "Profile" }, icon: "/profil.svg", tourId: "nav-profile" },
  { href: "/destek", label: { tr: "Destek", en: "Support" }, icon: "/destek.svg", tourId: "nav-destek" },
];

function MenuIcon({ item }: { item: NavItem }) {
  return (
    <span
      aria-hidden="true"
      className="block h-5 w-5 shrink-0 bg-current [mask-position:center] [mask-repeat:no-repeat] [mask-size:contain]"
      style={{
        maskImage: `url('${item.icon}')`,
        WebkitMaskImage: `url('${item.icon}')`,
      }}
    />
  );
}

function NavList({ items }: { items: NavItem[] }) {
  const pathname = usePathname();
  const { language } = useLanguage();

  return (
    <nav className="space-y-4">
      {items.map((item) => {
        const active = pathname === item.href || (item.href === "/dashboard" && pathname === "/portfolio");

        return (
          <Link
            key={item.href}
            href={item.href}
            data-tour={item.tourId}
            aria-current={active ? "page" : undefined}
            className={`group relative flex h-16 w-full items-center justify-center overflow-visible rounded-md border px-0 transition ${
              active
                ? "border-white/20 bg-white/10 text-white"
                : "border-white/10 bg-white/[0.06] text-white/70 hover:border-white/30 hover:bg-white/15 hover:text-white"
            }`}
          >
            {active ? (
              <span className="absolute bottom-2 left-0 top-2 w-1 rounded-r-full bg-[var(--color-primary)]" />
            ) : null}
            <MenuIcon item={item} />
            <span
              className={`pointer-events-none absolute left-1/2 -top-3 z-[70] -translate-x-1/2 whitespace-nowrap px-1 text-[11px] font-bold leading-none transition-colors ${
                active ? "text-white" : "text-white/70 group-hover:text-white"
              }`}
            >
              {item.label[language]}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar({ onStartTour }: { onStartTour: () => void }) {
  const { language } = useLanguage();

  return (
    <aside className="fixed bottom-0 left-0 top-0 z-50 flex w-24 flex-col overflow-visible bg-[var(--color-market-bar)] px-6 py-6 shadow-2xl">
      {/* Logo artik MarketTicker'daki ust seritte gosteriliyor - burada tekrar
          etmemesi icin sadece bosluk birakilir (bkz. MarketTicker.tsx Link). */}
      <div aria-hidden="true" className="h-20 shrink-0" />
      <div className="mt-8">
        <NavList items={mainLinks} />
      </div>
      <div className="mt-auto pt-6">
        <div className="space-y-7">
          <button
            type="button"
            data-tour="start-tour"
            onClick={(event) => {
              event.currentTarget.blur();
              onStartTour();
            }}
            className="group relative flex h-16 w-full items-center justify-center overflow-visible rounded-md border border-white/10 bg-white/[0.06] px-0 text-white/70 transition hover:border-white/30 hover:bg-white/15 hover:text-white"
            aria-label={language === "tr" ? "Platform yardım turunu başlat" : "Start the platform help tour"}
            title={language === "tr" ? "Platform yardım turunu başlat" : "Start the platform help tour"}
          >
            <span aria-hidden="true" className="text-2xl font-black leading-none">?</span>
            <span className="pointer-events-none absolute left-1/2 -top-4 z-[70] -translate-x-1/2 whitespace-nowrap px-1 text-[13px] font-bold leading-none text-white/70 transition-colors group-hover:text-white">
              {language === "tr" ? "Yardım" : "Help"}
            </span>
          </button>
          <NavList items={utilityLinks} />
        </div>
      </div>
    </aside>
  );
}
