"use client";

import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useRef, useState } from "react";
import { LanguageProvider, useLanguage } from "../../contexts/LanguageContext";
import { useAuth } from "../../hooks/useAuth";
import { markTourSeen } from "../../services/authService";
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
  const isAbout = pathname === "/hakkimizda";
  const isSupportPage = pathname === "/destek";
  const isPublic =
    isLanding || isLogin || isRegister || isAdvisorLogin || isPrivacyPolicy || isAbout || isSupportPage;
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  // page.tsx'teki gerçek yarışma (soru-cevap) ekranı aktifken true olur.
  const [isGameFocused, setIsGameFocused] = useState(false);
  // Sidebar/footer SADECE gerçek yarışma (soru-cevap) sırasında gizlenir,
  // kayıt/bekleme/çalışma notu ekranlarında görünür kalır.
  const isFocusedGame = isGame && isGameFocused;
  //: Onboarding'in GORUNURLUGU, canli `onboarding_completed` bayragindan
  //: kasitli olarak AYRI tutulur: `onDone` cagrilana kadar akis acik kalir,
  //: boylece `auth.refresh()` sirasindaki ara render'larda erken kapanmaz.
  //: `ProductTour` (asagida) BUNDAN AYRI: onboarding bitince (`onDone`)
  //: `has_seen_tour === false` oldugu surece kendi basina otomatik acilir -
  //: ikisi ayni anda gorunmez (bkz. asagidaki tur-tetikleme efekti).
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

  //: Urun turu (ProductTour) artik footer'daki manuel bir butonla degil,
  //: kullanici ilk kez kayit olup onboarding'i (anket -> sepet) bitirdikten
  //: HEMEN sonra OTOMATIK acilir. `onboardingActive` (yerel state) YERINE
  //: BILINCLI OLARAK `auth.user.onboarding_completed` (sunucudan gelen
  //: durum) kullanilir: yeni kayitta ikisi de (`onboarding_completed` VE
  //: `has_seen_tour`) AYNI ilk render'da false gelir - `onboardingActive`
  //: kendi setEffect'inde henuz true'ya CEVRILMEMISKEN bu efekt de ayni
  //: (eski) `false` degerini gorur ve tur, anket bitmeden hemen acilirdi
  //: (canli Playwright testiyle yakalanan gercek bir yaris durumu).
  //: `onboarding_completed` ise SADECE "Devam Et" + `auth.refresh()`
  //: sonrasi, gercekten AYRI bir render turunda true olur - bu yuzden
  //: guvenli sira garantisi verir.
  useEffect(() => {
    if (auth.user && auth.user.onboarding_completed === true && auth.user.has_seen_tour === false) {
      setTourOpen(true);
    }
  }, [auth.user]);

  function handleTourClose() {
    setTourOpen(false);
    if (auth.user && auth.user.has_seen_tour === false) {
      markTourSeen()
        .then(() => auth.refresh())
        .catch(() => {
          // Kaydedilemezse tur bir sonraki girişte tekrar acilir - kotu
          // ama akis kesilmeyen bir geri dusus (network hatasi vs.).
        });
    }
  }

  //: Portfoyu olan (onboarding tamamlanmis) giris yapmis bir kullanici
  //: anasayfada ("/") HIC gorunmemeli - dogrudan dashboard'a gitmeli (bug
  //: raporu: "ana sayfa flash edip sonra yonlendiriliyor"). `auth.loading`
  //: netlesene kadar durum belirsiz sayilir; bu pencerede ve yonlendirme
  //: hedefliyken render'da `children` GOSTERILMEZ (asagida) - flash'i onleyen
  //: asil kisim budur, useEffect'in kendisi degil (o zaten render SONRASI
  //: calisir, tek basina flash'i onleyemez).
  //: Onboarding tamamlanmamis kullanicilar (portfoyu HENUZ yok) bu kosula
  //: girmez - onlar icin anasayfa/onboarding akisi eskisi gibi davranir.
  const shouldSkipLandingContent =
    isLanding && (auth.loading || Boolean(auth.user && auth.user.onboarding_completed === true));

  useEffect(() => {
    if (isLanding && !auth.loading && auth.user && auth.user.onboarding_completed === true) {
      requestPageTransition("/dashboard", true);
    }
  }, [isLanding, auth.loading, auth.user]);

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
        shouldSkipLandingContent ? null : (
          <>
            {children}
            <SiteFooter className="ml-24 w-[calc(100%-6rem)]" />
          </>
        )
      ) : (
        <>
          {!isFocusedGame && <Sidebar />}
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
                  : "mx-auto w-full max-w-7xl flex-1 px-4 py-8"
              }
            >
              {children}
            </main>
            {!isFocusedGame && <SiteFooter />}
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
        onClose={handleTourClose}
        storageKey={`polifin-product-tour-v1:${auth.user?.id ?? "guest"}`}
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