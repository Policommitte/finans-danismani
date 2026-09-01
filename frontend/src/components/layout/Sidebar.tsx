"use client";

import {
  Home,
  LayoutDashboard,
  Newspaper,
  Zap,
  LineChart,
  Trophy,
  UserCircle,
  LifeBuoy,
  type LucideIcon,
} from "lucide-react";
import { usePathname } from "next/navigation";
import { useLanguage } from "../../contexts/LanguageContext";
import { useAuth } from "../../hooks/useAuth";
import { DesktopSidebar, Sidebar as SidebarPrimitive, SidebarLink } from "../ui/sidebar";
import { mainNavItems, utilityNavItems, type NavItem } from "./navItems";

//: navItems.ts'teki eski mask-image SVG ikonlarinin lucide-react karsiliklari -
//: Aceternity sidebar primitive'i (ui/sidebar.tsx) duz React ikon elemani
//: bekliyor, mask-image tabanli yaklasimi kullanmiyor.
const ICONS: Record<string, LucideIcon> = {
  home: Home,
  dashboard: LayoutDashboard,
  newsletter: Newspaper,
  recommendations: Zap,
  market: LineChart,
  game: Trophy,
  profile: UserCircle,
  support: LifeBuoy,
};

function NavLinks({ items, pathname }: { items: NavItem[]; pathname: string }) {
  const { language } = useLanguage();

  return (
    <>
      {items.map((item) => {
        const active = pathname === item.href || (item.href === "/dashboard" && pathname === "/portfolio");
        const Icon = ICONS[item.key] ?? Home;

        return (
          <SidebarLink
            key={item.href}
            link={{
              label: item.label[language],
              href: item.href,
              icon: (
                <Icon
                  className={`h-5 w-5 shrink-0 ${active ? "text-white" : "text-white/70"}`}
                />
              ),
            }}
            data-tour={item.tourId}
            aria-current={active ? "page" : undefined}
            className={`rounded-md px-2 ${
              active ? "bg-white/10 text-white" : "text-white/70 hover:bg-white/[0.06] hover:text-white"
            }`}
          />
        );
      })}
    </>
  );
}

export function Sidebar() {
  const auth = useAuth();
  const pathname = usePathname();
  //: Giris yapmis kullanicinin zaten "Genel Bakis" (dashboard) ekrani var -
  //: herkese acik pazarlama amacli anasayfaya ("/") gitmesine gerek yok,
  //: kafa karistirir. page.tsx'teki LandingSideMenu de AYNI listeyi ("home"
  //: haric) kullanir - bkz. navItems.ts docstring'i.
  const items = auth.user ? mainNavItems.filter((item) => item.key !== "home") : mainNavItems;

  return (
    <SidebarPrimitive>
      {/* Kapaliyken 96px, uzerine gelince 300px'e acilip icerigin USTUNE biner
          (fixed + shadow) - sayfa icerigi kaymaz, mevcut layout/marjin sistemine
          (AppShell, MarketTicker) dokunulmaz. `flex flex-col` (on-prefiksiz)
          primitive'in kendi `hidden md:flex` tabanini gecersiz kilar - bu
          site ayri bir mobil menu tasarimi kullanmiyor (eski Sidebar.tsx da
          tum genisliklerde ayni sekilde gorunuyordu), MobileSidebar bu yuzden
          kasitli olarak kullanilmadi (paylasilan hover/acik state'i mobil
          panelin masaustu hover'da da acilmasina yol aciyordu). */}
      <DesktopSidebar className="fixed bottom-0 left-0 top-0 z-50 flex h-screen flex-col overflow-visible border-r border-white/10 bg-[var(--color-market-bar)] pb-6 pt-24 shadow-2xl">
        <div className="flex flex-1 flex-col gap-1 overflow-y-auto overflow-x-hidden">
          <NavLinks items={items} pathname={pathname} />
        </div>
        <div className="mt-auto flex flex-col gap-1 border-t border-white/10 pt-4">
          <NavLinks items={utilityNavItems} pathname={pathname} />
        </div>
      </DesktopSidebar>
    </SidebarPrimitive>
  );
}
