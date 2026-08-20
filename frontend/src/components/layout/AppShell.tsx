"use client";

import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";
import { useAuth } from "../../hooks/useAuth";
import { ChatWidget } from "../chat/ChatWidget";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { SiteFooter } from "./SiteFooter";

export function AppShell({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isLogin = pathname === "/login";
  const isPublic = pathname === "/" || isLogin;
  const isLanding = pathname === "/";

  useEffect(() => {
    if (!auth.loading && !auth.user && !auth.hasToken && !isPublic) {
      router.replace("/login");
    }
  }, [auth.hasToken, auth.loading, auth.user, isPublic, router]);

  if (isPublic) {
    return (
      <>
        {children}
        {!isLogin && <SiteFooter className={isLanding ? "ml-24 w-[calc(100%-6rem)]" : ""} />}
      </>
    );
  }

  return (
    <div className="min-h-screen app-bg">
      <div className="flex">
        <Sidebar />
        <div className="min-w-0 flex-1">
          <Header user={auth.user} onLogout={auth.logout} />
          <main className="mx-auto w-full max-w-7xl px-4 py-6">{children}</main>
          <SiteFooter />
        </div>
      </div>
      {auth.user && <ChatWidget />}
    </div>
  );
}
