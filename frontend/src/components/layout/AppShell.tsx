"use client";

import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";
import { useAuth } from "../../hooks/useAuth";
import { ChatWidget } from "../chat/ChatWidget";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isLogin = pathname === "/login";

  useEffect(() => {
    if (!auth.loading && !auth.user && !auth.hasToken && !isLogin) {
      router.replace("/login");
    }
  }, [auth.hasToken, auth.loading, auth.user, isLogin, router]);

  if (isLogin) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex">
        <Sidebar />
        <div className="min-w-0 flex-1">
          <Header user={auth.user} onLogout={auth.logout} />
          <main className="mx-auto w-full max-w-7xl px-4 py-6">{children}</main>
        </div>
      </div>
      {auth.user && <ChatWidget />}
    </div>
  );
}
