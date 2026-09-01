"use client";

import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useRef, useState } from "react";
import { LanguageProvider, useLanguage } from "../../contexts/LanguageContext";
import { useAuth } from "../../hooks/useAuth";
import { ChatWidget } from "../chat/ChatWidget";
import { AssetSummaryModal } from "../market/AssetSummaryModal";
import { OnboardingFlow } from "../onboarding/OnboardingFlow";
import { ProductTour } from "../tour/ProductTour";
import { MarketTicker } from "./MarketTicker";
import { Sidebar } from "./Sidebar";
import { SiteFooter } from "./SiteFooter";
import { requestPageTransition } from "./transitionEvents";

function AppShellContent({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const router = useRouter();
  const { language } = useLanguage();
  const pathname = usePathname();
  const isLogin = pathname === "/login";
  const isRegister = pathname === "/register";
  const isAdvisorLogin = pathname === "/danisman-giris";
  const isLanding = pathname === "/";
  // Yarışma ekranında piyasa şeridi ve sohbet gizlenir:
  // şerit dikkat dağıtır, sohbet ise soruların cevabına erişim yolu olur.
  const isGame = pathname === "/yatirim-oyunu";
  const isPrivacyPolicy = pathname === "/gizlilik-politikasi";
  const isSupportPage = pathname === "/destek";
  // Danışman ekranındaki geniş CRM tablosu için yalnızca bu sayfanın
  // içerik kabı genişletilir; diğer sayfaların ölçüsü değişmez.
  const isWidePage = pathname === "/danisman";
  const isPublic =
    isLanding || isLogin || isRegister || isAdvisorLogin || isPrivacyPolicy || isSupportPage;
  const showHomeNavigation = !auth.user && !auth.hasToken;
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  // page.tsx'teki gerçek yarışma (soru-cevap) ekranı aktifken true olur.
  const [isGameFocused, setIsGameFocused] = useState(false);
  // Sidebar/footer SADECE gerçek yarışma (soru-cevap) sırasında gizlenir,
  // kayıt/bekleme/çalışma notu ekranlarında görünür kalır.
  const isFocusedGame = isGame && isGameFocused;
  //: Onboarding'in GORUNURLUGU, canli `onboarding_completed` bayragindan
  //: kasitli olarak AYRI tutulur: bayrak sepet ekranindaki "Devam Et"te
  //: (persistence noktasi) hemen true olur, ama tur bundan SONRA baslar.
  //: Bayragi dogrudan kosul yapsaydik, refresh() aninda OnboardingFlow
  //: unmount olur ve tur hic gorunmezdi. Bu yuzden akis SADECE kendi
  //: `onDone` cagrisiyla kapanir. `ProductTour` (asagida) BUNDAN AYRI, tekrar
  //: baslatilabilir bir urun turu - ilk-giris zorunlu akisiyla cakismaz.
  const [onboardingActive, setOnboardingActive] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const [logoutNoticeName, setLogoutNoticeName] = useState<string | null>(null);
  const explicitLogoutRef = useRef(false);
  const logoutNoticeTimerRef = useRef<number | null>(null);

  function handleLogout() {
    const firstName = auth.user?.first_name ?? "";
    explicitLogoutRef.current = true;
    auth.logout();
    if (pathname === "/") {
      setLogoutNoticeName(firstName);
      if (logoutNoticeTimerRef.current !== null) {
        window.clearTimeout(logoutNoticeTimerRef.current);
      }
      logoutNoticeTimerRef.current = window.setTimeout(() => setLogoutNoticeName(null), 3200);
      return;
    }
    requestPageTransition("/", true);
  }

  useEffect(() => {
    if (isPublic) {
      explicitLogoutRef.current = false;
      return;
    }

    if (!explicitLogoutRef.current && !auth.loading && !auth.user && !auth.hasToken) {
      requestPageTransition("/login", true);
    }
  }, [auth.hasToken, auth.loading, auth.user, isPublic]);

  useEffect(() => {
    if (!auth.user || isPublic) {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get("tour") !== "1") {
      return;
    }

    setTourOpen(true);
    params.delete("tour");
    const nextSearch = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ""}${window.location.hash}`);
  }, [auth.user, isPublic, pathname]);

  useEffect(() => () => {
    if (logoutNoticeTimerRef.current !== null) {
      window.clearTimeout(logoutNoticeTimerRef.current);
    }
  }, []);

  useEffect(() => {
    if (auth.user && auth.user.onboarding_completed === false) {
      setOnboardingActive(true);
    }
  }, [auth.user]);

  useEffect(() => {
    if (onboardingActive && isLanding) {
      // Landing sayfasi Sidebar render etmez; tur hedeflerinin DOM'da
      // olmasi icin kullaniciyi dashboard'a tasiriz.
      requestPageTransition("/dashboard", true);
    }
  }, [onboardingActive, isLanding]);

  useEffect(() => {
    function handleGameFocus(e: Event) {
      setIsGameFocused(Boolean((e as CustomEvent<boolean>).detail));
    }
    window.addEventListener("polifin-game-focus", handleGameFocus);
    return () => window.removeEventListener("polifin-game-focus", handleGameFocus);
  }, []);

  // Sayfa değişince (oyun sayfasından ayrılınca) sıfırla, takılı kalmasın.
  useEffect(() => {
    if (!isGame) setIsGameFocused(false);
  }, [isGame, pathname]);

  useEffect(() => {
    if (!auth.loading && auth.user && pathname === "/danisman" && auth.user.role !== "advisor") {
      router.replace("/dashboard");
    }
  }, [auth.loading, auth.user, pathname, router]);

  if (isLogin || isRegister || isAdvisorLogin) {
    return children;
  }

  return (

  

  
    <div className="min-h-screen app-bg">
      {!isGame && (
        <MarketTicker
          onSelect={setSelectedSymbol}
          onLogout={handleLogout}
          isAuthenticated={Boolean(auth.user)}
        />
      )}
      {isLanding ? (
        <>
          {children}
          <SiteFooter className="ml-24 w-[calc(100%-6rem)]" onStartTour={() => setTourOpen(true)} />
        </>
      ) : (
        <>
          {!isFocusedGame && <Sidebar showHome={showHomeNavigation} />}
          <div
            className={
              isFocusedGame
                ? "flex min-h-screen w-full flex-col pt-4"
                : `ml-24 flex min-h-screen w-[calc(100%-6rem)] flex-col ${isGame ? "pt-8" : "pt-20"}`
            }
          >
            <main
              className={
                isFocusedGame
                  ? "mx-auto w-full max-w-5xl flex-1 px-4 py-4"
                  : "relative w-full flex-1"
              }
            >
              {isFocusedGame ? (
                children
              ) : (
                <div
                  className={`mx-auto w-full px-4 py-8 ${
                    isWidePage ? "max-w-[100rem]" : "max-w-7xl"
                  }`}
                >
                  {children}
                </div>
              )}
            </main>
            <SiteFooter onStartTour={() => setTourOpen(true)} />
          </div>
          {!isGame && (
            <ChatWidget
              canSend={Boolean(auth.user)}
              blockedMessage={
                language === "tr"
                  ? "Soru sormadan önce giriş yapmalısınız."
                  : "You need to log in before asking a question."
              }
              onSelectAsset={setSelectedSymbol}
            />
          )}
        </>
      )}
      {selectedSymbol ? (
        <AssetSummaryModal
          symbol={selectedSymbol}
          onClose={() => setSelectedSymbol(null)}
          isAuthenticated={Boolean(auth.user)}
        />
      ) : null}
      {onboardingActive && <OnboardingFlow onDone={() => setOnboardingActive(false)} />}
      <ProductTour
        open={tourOpen}
        onClose={() => setTourOpen(false)}
        storageKey={`polifin-product-tour-v1:${auth.user?.id ?? "guest"}`}
        showHomeStep={showHomeNavigation}
      />
      {logoutNoticeName !== null ? (
        <div
          role="status"
          aria-live="polite"
          className="logout-toast fixed right-5 top-24 z-[100] flex w-[min(22rem,calc(100vw-2.5rem))] items-start gap-3 rounded-xl border app-card p-4 shadow-2xl"
        >
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-emerald-100 text-lg font-black text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" aria-hidden="true">
            ✓
          </span>
          <div>
            <div className="font-bold app-heading">
              {language === "tr" ? "Başarıyla çıkış yaptınız." : "You have signed out successfully."}
            </div>
            <div className="mt-1 text-sm app-muted">
              {logoutNoticeName
                ? language === "tr"
                  ? `Görüşmek üzere, ${logoutNoticeName}!`
                  : `See you soon, ${logoutNoticeName}!`
                : language === "tr"
                  ? "Görüşmek üzere!"
                  : "See you soon!"}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <LanguageProvider>
      <AppShellContent>{children}</AppShellContent>
    </LanguageProvider>
  );
}
