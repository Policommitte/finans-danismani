"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/portfolio", label: "Portfoy" },
  { href: "/market", label: "Piyasa" },
  { href: "/risk", label: "Risk" },
  { href: "/reports", label: "Raporlar" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden min-h-screen w-64 border-r app-border app-surface px-4 py-5 md:block">
      <div className="mb-8 px-2">
        <div className="text-sm font-semibold uppercase tracking-wide app-primary-text">Finans AI</div>
        <div className="mt-1 text-xs app-muted">Akilli kisisel finans danismani</div>
      </div>
      <nav className="space-y-1">
        {links.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`block rounded-md px-3 py-2 text-sm font-medium ${
                active ? "app-primary-soft" : "app-muted app-subtle-hover"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
