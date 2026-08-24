"use client";

import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { ChatWidget } from "../chat/ChatWidget";
import { AssetSummaryModal } from "../market/AssetSummaryModal";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { MarketTicker } from "./MarketTicker";
import { Sidebar } from "./Sidebar";
import { SiteFooter } from "./SiteFooter";

export function AppShell({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isLogin = pathname === "/login";
  const isPublic = pathname === "/" || isLogin;
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.loading && !auth.user && !auth.hasToken && !isPublic) {
      router.replace("/login");
    }
  }, [auth.hasToken, auth.loading, auth.user, isPublic, router]);

  if (isPublic) {
    return (
      <>
        {children}
        {!isLogin && <SiteFooter />}
      </>
    );
  }

  return (
    <div className="flex min-h-screen flex-col app-bg">
      <MarketTicker onSelect={setSelectedSymbol} />
      <div className="flex flex-1">
        <Sidebar user={auth.user} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header user={auth.user} onLogout={auth.logout} />
          <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">{children}</main>
          <Footer />
        </div>
      </div>
      {auth.user && <ChatWidget />}
      {selectedSymbol && <AssetSummaryModal symbol={selectedSymbol} onClose={() => setSelectedSymbol(null)} />}
    </div>
  );
}
