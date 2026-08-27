"use client";

import { useEffect, useRef } from "react";

const TOUR_STEPS = [
  {
    element: '[data-tour="nav-dashboard"]',
    popover: {
      title: "Genel Bakış",
      description: "Portföyünün toplam değerini, günlük değişimini ve risk skorunu buradan izlersin.",
    },
  },
  {
    element: '[data-tour="portfolio-section"]',
    popover: {
      title: "Portföyün",
      description: "Sahip olduğun tüm varlıklar, adetleri ve kâr/zararı bu tabloda.",
    },
  },
  {
    element: '[data-tour="nav-bulten"]',
    popover: {
      title: "Bülten",
      description: "Piyasayı etkileyebilecek güncel haberler ve analizler burada.",
    },
  },
  {
    element: '[data-tour="nav-destek"]',
    popover: {
      title: "Destek",
      description: "Sorularin için sıkça sorulanlar ve destek talebi oluşturma burada.",
    },
  },
  {
    element: '[data-tour="nav-profil"]',
    popover: {
      title: "Profilin",
      description: "Risk profilini, hedeflerini ve hesap ayarlarını buradan yönetirsin.",
    },
  },
];

export function OnboardingTour({ onFinish }: { onFinish: () => void }) {
  const finishedRef = useRef(false);

  useEffect(() => {
    let driverObj: { drive: () => void; destroy: () => void } | null = null;
    let active = true;

    async function start() {
      const { driver } = await import("driver.js");
      await import("driver.js/dist/driver.css");
      if (!active) return;

      driverObj = driver({
        showProgress: true,
        allowClose: false,
        showButtons: ["next", "previous"],
        nextBtnText: "İleri",
        prevBtnText: "Geri",
        doneBtnText: "Bitir",
        steps: TOUR_STEPS,
        onDestroyed: () => {
          if (!finishedRef.current) {
            finishedRef.current = true;
            onFinish();
          }
        },
      });
      driverObj.drive();
    }

    void start();

    return () => {
      active = false;
      driverObj?.destroy();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}
