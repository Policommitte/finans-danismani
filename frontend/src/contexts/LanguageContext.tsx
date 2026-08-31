"use client";

import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";

export type AppLanguage = "tr" | "en";

type LanguageContextValue = {
  language: AppLanguage;
  toggleLanguage: () => void;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<AppLanguage>("tr");

  useEffect(() => {
    const savedLanguage = window.localStorage.getItem("landing-language");
    if (savedLanguage === "tr" || savedLanguage === "en") {
      setLanguage(savedLanguage);
    }

    function handleLanguageChange(event: Event) {
      const nextLanguage = (event as CustomEvent<AppLanguage>).detail;
      if (nextLanguage === "tr" || nextLanguage === "en") {
        setLanguage(nextLanguage);
      }
    }

    window.addEventListener("polifin-language-change", handleLanguageChange);
    return () => window.removeEventListener("polifin-language-change", handleLanguageChange);
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      //: `setLanguage`'a verilen updater fonksiyonu SAF olmali (React
      //: StrictMode gelistirmede arilik kontrolu icin updater'lari IKI KEZ
      //: cagirir). Yan etkileri (localStorage yazma, event dispatch) eskiden
      //: updater'in ICINDE calistiriyorduk - StrictMode ikinci cagrida bunlari
      //: TEKRAR tetikliyor, dispatch edilen event bu Provider'in kendi
      //: dinleyicisine (asagida) geri donup ikinci bir setLanguage cagrisi
      //: yapiyor ve dil goruli tr->en->tr diye salinip GORUNURDE HIC
      //: DEGISMIYORDU. Yan etkiler artik updater DISINDA, sadece bir kez.
      toggleLanguage: () => {
        const nextLanguage = language === "tr" ? "en" : "tr";
        window.localStorage.setItem("landing-language", nextLanguage);
        window.dispatchEvent(new CustomEvent("polifin-language-change", { detail: nextLanguage }));
        setLanguage(nextLanguage);
      },
    }),
    [language],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used inside LanguageProvider");
  }
  return context;
}
