import type { Metadata } from "next";
import "../index.css";
import { AppShell } from "../components/layout/AppShell";

export const metadata: Metadata = {
  title: "Akilli Kisisel Finans Danismani",
  description: "Portfoy, piyasa, risk ve AI destekli finans danismani arayuzu",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
