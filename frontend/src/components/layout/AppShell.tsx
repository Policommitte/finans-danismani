"use client";

import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { LanguageProvider } from "../../contexts/LanguageContext";
import { useAuth } from "../../hooks/useAuth";
import { ChatWidget } from "../chat/ChatWidget";
import { AssetSummaryModal } from "../market/AssetSummaryModal";
import { MarketTicker } from "./MarketTicker";
import { Sidebar } from "./Sidebar";
import { SiteFooter } from "./SiteFooter";

function AppShellContent({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isLogin = pathname === "/login";
  const isPublic = pathname === "/" || isLogin;
  const isLanding = pathname === "/";
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.loading && !auth.user && !auth.hasToken && !isPublic) {
      router.replace("/login");
    }
  }, [auth.hasToken, auth.loading, auth.user, isPublic, router]);

  if (isLogin) {
    return children;
  }

  return (
    <div className="min-h-screen app-bg">
      <MarketTicker
        onSelect={setSelectedSymbol}
        onLogout={auth.logout}
        isAuthenticated={Boolean(auth.user)}
      />
      {isLanding ? (
        <>
          {children}
          <SiteFooter className="ml-24 w-[calc(100%-6rem)]" />
        </>
      ) : (
        <>
          <Sidebar />
          <div className="ml-24 flex min-h-screen w-[calc(100%-6rem)] flex-col pt-20">
            <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8">{children}</main>
            <SiteFooter />
          </div>
          {auth.user && <ChatWidget />}
        </>
      )}
      {selectedSymbol ? (
        <AssetSummaryModal symbol={selectedSymbol} onClose={() => setSelectedSymbol(null)} />
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
