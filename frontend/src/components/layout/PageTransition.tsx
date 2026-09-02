"use client";

import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useRef, useState } from "react";
import {
  AUTONOMOUS_ACTIONS_READY_EVENT,
  BULLETIN_PAGE_READY_EVENT,
  DASHBOARD_READY_EVENT,
  MARKET_PAGE_READY_EVENT,
  MARKET_TICKER_READY_EVENT,
  PAGE_TRANSITION_REQUEST_EVENT,
  type PageTransitionNavigation,
} from "./transitionEvents";

// index.css'teki karo koreografisiyle KILITLI: karo suresi (420ms) + son
// karonun gecikmesi (180ms) = 600ms. CSS'te tempo degisirse burasi da
// degismeli, yoksa gecis ya erken acilir ya bosuna bekler.
const COVER_DURATION_MS = 600;
const REVEAL_DELAY_MS = 40;
// Perdenin veri bekleyecegi ust sinir. 8 sn'ydi: backend soguk acilirken
// kullanici 8 saniye boyunca perdeye bakiyordu. Ticker gelmezse 2,5 sn
// sonra sayfa yine acilir; serit kendi iskeletiyle sonradan dolar -
// islevsel bir kayip yok, yalnizca kotu gunun tavani dusuyor.
const TICKER_READY_TIMEOUT_MS = 2500;
// Yardimci sayfalardaki veri bekleyisinin tavani. Dashboard, market/islemler
// ve bulten bu tavani BILINCLI olarak kullanmaz: bu sayfalarin ilk acilisinda
// asil veri hazir olmadan perdeyi kaldirmak, kullaniciya once bos bir
// "yukleniyor" karti sonra gercek sayfayi gosteriyordu. Bu uc sayfa kendi
// READY event'ini gonderene kadar logo + spinner gorunur kalir. Oneriler
// sayfasinda ise mevcut guvenlik tavani korunur.
const PAGE_READY_TIMEOUT_MS = 4000;

type TransitionPhase = "idle" | "covering" | "covered" | "revealing";

export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [phase, setPhase] = useState<TransitionPhase>("covered");
  const phaseRef = useRef<TransitionPhase>("covered");
  const destinationRef = useRef<string | null>(null);
  const navigationTimerRef = useRef<number | null>(null);
  const revealTimerRef = useRef<number | null>(null);

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

  useEffect(() => {
    let revealStarted = false;
    let tickerWaitExpired = false;
    let pageWaitExpired = false;

    function revealPage() {
      if (revealStarted) {
        return;
      }

      revealStarted = true;
      revealTimerRef.current = window.setTimeout(() => {
        phaseRef.current = "revealing";
        setPhase("revealing");
        destinationRef.current = null;
      }, REVEAL_DELAY_MS);
    }

    function requiredDataIsReady() {
      const tickerIsReady = document.documentElement.dataset.marketTickerReady === "true";
      const dashboardIsReady = document.documentElement.dataset.dashboardReady === "true";
      const marketPageIsReady = document.documentElement.dataset.marketPageReady === "true";
      const bulletinPageIsReady = document.documentElement.dataset.bulletinPageReady === "true";
      const autonomousActionsIsReady = document.documentElement.dataset.autonomousActionsReady === "true";
      const pageHasTicker = pathname !== "/login" && pathname !== "/register";
      const pageNeedsDashboard = pathname === "/dashboard" || pathname === "/portfolio";
      const pageNeedsMarket = pathname === "/market";
      const pageNeedsBulletin = pathname === "/bulten";
      const pageNeedsAutonomousActions = pathname === "/oneriler";

      return (
        (!pageHasTicker || tickerIsReady || tickerWaitExpired) &&
        (!pageNeedsDashboard || dashboardIsReady) &&
        (!pageNeedsMarket || marketPageIsReady) &&
        (!pageNeedsBulletin || bulletinPageIsReady) &&
        (!pageNeedsAutonomousActions || autonomousActionsIsReady || pageWaitExpired)
      );
    }

    function handleDataReady() {
      if (requiredDataIsReady()) {
        revealPage();
      }
    }

    let tickerReadyTimeout: number | null = null;
    let pageReadyTimeout: number | null = null;

    if (!requiredDataIsReady()) {
      window.addEventListener(MARKET_TICKER_READY_EVENT, handleDataReady);
      window.addEventListener(DASHBOARD_READY_EVENT, handleDataReady);
      window.addEventListener(MARKET_PAGE_READY_EVENT, handleDataReady);
      window.addEventListener(BULLETIN_PAGE_READY_EVENT, handleDataReady);
      window.addEventListener(AUTONOMOUS_ACTIONS_READY_EVENT, handleDataReady);
      tickerReadyTimeout = window.setTimeout(() => {
        tickerWaitExpired = true;
        handleDataReady();
      }, TICKER_READY_TIMEOUT_MS);
      pageReadyTimeout = window.setTimeout(() => {
        pageWaitExpired = true;
        handleDataReady();
      }, PAGE_READY_TIMEOUT_MS);
    } else {
      revealPage();
    }

    return () => {
      window.removeEventListener(MARKET_TICKER_READY_EVENT, handleDataReady);
      window.removeEventListener(DASHBOARD_READY_EVENT, handleDataReady);
      window.removeEventListener(MARKET_PAGE_READY_EVENT, handleDataReady);
      window.removeEventListener(BULLETIN_PAGE_READY_EVENT, handleDataReady);
      window.removeEventListener(AUTONOMOUS_ACTIONS_READY_EVENT, handleDataReady);
      if (tickerReadyTimeout !== null) {
        window.clearTimeout(tickerReadyTimeout);
      }
      if (pageReadyTimeout !== null) {
        window.clearTimeout(pageReadyTimeout);
      }
      if (revealTimerRef.current !== null) {
        window.clearTimeout(revealTimerRef.current);
      }
    };
  }, [pathname]);

  useEffect(() => {
    if (phase !== "revealing") {
      return;
    }

    const timer = window.setTimeout(() => setPhase("idle"), COVER_DURATION_MS);
    return () => window.clearTimeout(timer);
  }, [phase]);

  useEffect(() => {
    function beginNavigation(destination: string, replace = false) {
      if (phaseRef.current === "covering") {
        return;
      }

      if (phaseRef.current === "covered") {
        destinationRef.current = destination;
        if (replace) {
          router.replace(destination);
        } else {
          router.push(destination);
        }
        return;
      }

      const destinationUrl = new URL(destination, window.location.href);
      const currentUrl = new URL(window.location.href);
      const isSameLocation =
        destinationUrl.pathname === currentUrl.pathname &&
        destinationUrl.search === currentUrl.search &&
        destinationUrl.hash === currentUrl.hash;

      if (isSameLocation) {
        destinationRef.current = null;
        phaseRef.current = "idle";
        setPhase("idle");
        return;
      }

      if (destinationUrl.pathname === "/dashboard" || destinationUrl.pathname === "/portfolio") {
        delete document.documentElement.dataset.dashboardReady;
      }
      if (destinationUrl.pathname === "/market") {
        delete document.documentElement.dataset.marketPageReady;
      }
      if (destinationUrl.pathname === "/bulten") {
        delete document.documentElement.dataset.bulletinPageReady;
      }
      if (destinationUrl.pathname === "/oneriler") {
        delete document.documentElement.dataset.autonomousActionsReady;
      }

      destinationRef.current = destination;
      phaseRef.current = "covering";
      setPhase("covering");

      // Rota, perde KAPANIRKEN onceden yuklenir. Eskiden router.push perde
      // tamamen kapanana kadar bekliyordu ve hedef sayfanin kodu/verisi
      // ancak o zaman istenmeye baslaniyordu - yukleme ile animasyon pes
      // pese calisiyordu. Prefetch ikisini ust uste bindirir; gorsel hicbir
      // sey degismez, perde acildiginda sayfa cogunlukla hazirdir.
      try {
        router.prefetch(destination);
      } catch {
        // prefetch en-iyi-caba: desteklenmeyen ortamda gecis yine calisir.
      }

      navigationTimerRef.current = window.setTimeout(() => {
        phaseRef.current = "covered";
        setPhase("covered");

        if (replace) {
          router.replace(destinationRef.current ?? "/");
        } else {
          router.push(destinationRef.current ?? "/");
        }
      }, COVER_DURATION_MS);
    }

    function handleTransitionRequest(event: Event) {
      const navigationEvent = event as CustomEvent<PageTransitionNavigation>;
      const { href, replace = false } = navigationEvent.detail;
      beginNavigation(href, replace);
    }

    function handleDocumentClick(event: MouseEvent) {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey ||
        phaseRef.current === "covering" ||
        phaseRef.current === "covered"
      ) {
        return;
      }

      const target = event.target;
      const anchor = target instanceof Element ? target.closest("a") : null;

      if (
        !(anchor instanceof HTMLAnchorElement) ||
        anchor.target === "_blank" ||
        anchor.hasAttribute("download") ||
        anchor.dataset.noPageTransition === "true"
      ) {
        return;
      }

      const destination = new URL(anchor.href, window.location.href);
      const current = new URL(window.location.href);
      const isSameDocumentHash =
        destination.pathname === current.pathname &&
        destination.search === current.search &&
        destination.hash !== current.hash;

      if (
        destination.origin !== current.origin ||
        !["http:", "https:"].includes(destination.protocol) ||
        isSameDocumentHash ||
        destination.href === current.href
      ) {
        return;
      }

      event.preventDefault();
      beginNavigation(`${destination.pathname}${destination.search}${destination.hash}`);
    }

    document.addEventListener("click", handleDocumentClick, true);
    window.addEventListener(PAGE_TRANSITION_REQUEST_EVENT, handleTransitionRequest);
    return () => {
      document.removeEventListener("click", handleDocumentClick, true);
      window.removeEventListener(PAGE_TRANSITION_REQUEST_EVENT, handleTransitionRequest);
      if (navigationTimerRef.current !== null) {
        window.clearTimeout(navigationTimerRef.current);
      }
    };
  }, [router]);

  const overlayVisible = phase !== "idle";
  const tilesCovered = phase === "covering" || phase === "covered";

  return (
    <>
      {children}
      <div
        aria-hidden="true"
        data-phase={phase}
        className={`page-transition ${overlayVisible ? "page-transition--visible" : ""} ${
          tilesCovered ? "page-transition--covered" : ""
        }`}
      >
        <div className="page-transition__brand">
          <span className="page-transition__logo" />
          <span className="page-transition__spinner" />
        </div>
        {Array.from({ length: 5 }, (_, index) => (
          <span key={index} className="page-transition__tile" />
        ))}
      </div>
    </>
  );
}
