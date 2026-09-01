export type NavItem = {
  key: string;
  href: string;
  label: { tr: string; en: string };
  icon: string;
  tourId: string;
};

//: Sidebar.tsx (giris yapilmis her sayfa) ile page.tsx'deki LandingSideMenu
//: (giris yapilmamis "/" sayfasi) TEK bu listeyi kullanir - iki ayri yerde
//: tanimlanip zamanla farklilasmasinlar diye (bkz. gecmiste "Piyasa" vs
//: "Piyasalar", "Ayarlar" vs "Destek" tutarsizligi).
export const mainNavItems: NavItem[] = [
  { key: "home", href: "/", label: { tr: "Ana Sayfa", en: "Home" }, icon: "/ana-sayfa.svg", tourId: "nav-home" },
  {
    key: "dashboard",
    href: "/dashboard",
    label: { tr: "Genel Bakış", en: "Overview" },
    icon: "/analiz.svg",
    tourId: "nav-dashboard",
  },
  {
    key: "newsletter",
    href: "/bulten",
    label: { tr: "Bülten", en: "Newsletter" },
    icon: "/bulten.svg",
    tourId: "nav-bulten",
  },
  {
    key: "market",
    href: "/market",
    label: { tr: "İşlemler", en: "Trading" },
    icon: "/piyasa.svg",
    tourId: "nav-market",
  },
  {
    key: "game",
    href: "/yatirim-oyunu",
    label: { tr: "Yatırım Oyunu", en: "Investment Game" },
    icon: "/oyun.svg",
    tourId: "nav-game",
  },
];

export const utilityNavItems: NavItem[] = [
  {
    key: "profile",
    href: "/profile",
    label: { tr: "Profil", en: "Profile" },
    icon: "/profil.svg",
    tourId: "nav-profile",
  },
  {
    key: "support",
    href: "/destek",
    label: { tr: "Destek", en: "Support" },
    icon: "/destek.svg",
    tourId: "nav-destek",
  },
];
