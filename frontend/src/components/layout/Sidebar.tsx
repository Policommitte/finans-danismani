"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "../../contexts/LanguageContext";
import { useAuth } from "../../hooks/useAuth";
import { mainNavItems, utilityNavItems, type NavItem } from "./navItems";

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
              className={`pointer-events-none absolute left-1/2 -top-3 z-[70] w-[88px] -translate-x-1/2 whitespace-normal px-1 text-center text-[11px] font-bold leading-[1.05] transition-colors ${
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

export function Sidebar() {
  const auth = useAuth();
  //: Giris yapmis kullanicinin zaten "Genel Bakis" (dashboard) ekrani var -
  //: herkese acik pazarlama amacli anasayfaya ("/") gitmesine gerek yok,
  //: kafa karistirir. page.tsx'teki LandingSideMenu de AYNI listeyi ("home"
  //: haric) kullanir - bkz. navItems.ts docstring'i.
  const items = auth.user ? mainNavItems.filter((item) => item.key !== "home") : mainNavItems;

  return (
    <aside className="fixed bottom-0 left-0 top-0 z-50 flex w-24 flex-col overflow-visible bg-[var(--color-market-bar)] px-6 py-6 shadow-2xl">
      {/* Logo artik MarketTicker'daki ust seritte gosteriliyor - burada tekrar
          etmemesi icin sadece bosluk birakilir (bkz. MarketTicker.tsx Link). */}
      <div aria-hidden="true" className="h-20 shrink-0" />
      <div className="mt-8">
        <NavList items={items} />
      </div>
      <div className="mt-auto pt-6">
        <NavList items={utilityNavItems} />
      </div>
    </aside>
  );
}
