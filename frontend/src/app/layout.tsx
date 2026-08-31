import type { Metadata } from "next";
import Script from "next/script";
import "../index.css";
import "blobatar/motion.css";
import { AppShell } from "../components/layout/AppShell";
import { PageTransition } from "../components/layout/PageTransition";
import { AuthProvider } from "../hooks/useAuth";

export const metadata: Metadata = {
  title: "Akıllı Kişisel Finans Asistanı",
  description: "Portfoy, piyasa ve AI destekli finans danismani arayuzu",
};

const themeScript = `
(() => {
  try {
    const savedTheme = window.localStorage.getItem("app-theme") ?? window.localStorage.getItem("landing-theme");
    const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const theme = savedTheme === "light" || savedTheme === "dark" ? savedTheme : systemPrefersDark ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
  } catch {
    document.documentElement.dataset.theme = "light";
  }
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <head>
        <Script id="theme-script" strategy="beforeInteractive" dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      {/*
        suppressHydrationWarning BURADA DA GEREKLI (html'de olmasi yetmiyor):
        React bu bayragi TEK SEVIYE uygular, yani <html> uzerindeki bayrak
        <body>'nin KENDI ozniteliklerindeki farki susturmaz.

        Somut vaka: bazi tarayici eklentileri React yuklenmeden once <body>'ye
        sinif ekliyor (orn. Video Speed Controller -> "vsc-initialized").
        Sunucudan gelen HTML'de o sinif yok, istemcide var -> hydration
        uyarisi. Uygulamanin kodunda bir hata YOK; React'in kendi hata metni de
        bu ihtimali sayiyor.

        Bayragi tum agaca degil yalnizca <body> etiketine koyuyoruz: icerideki
        gercek hydration hatalari gorunur kalsin.
      */}
      <body suppressHydrationWarning>
        <AuthProvider>
          <PageTransition>
            <AppShell>{children}</AppShell>
          </PageTransition>
        </AuthProvider>
      </body>
    </html>
  );
}
