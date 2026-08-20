import type { Metadata } from "next";
import Script from "next/script";
import "../index.css";
import { AppShell } from "../components/layout/AppShell";
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
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
