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
    <aside className="hidden min-h-screen w-64 border-r border-slate-200 bg-white px-4 py-5 md:block">
      <div className="mb-8 px-2">
        <div className="text-sm font-semibold uppercase tracking-wide text-blue-700">Finans AI</div>
        <div className="mt-1 text-xs text-slate-500">Akilli kisisel finans danismani</div>
      </div>
      <nav className="space-y-1">
        {links.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`block rounded-md px-3 py-2 text-sm font-medium ${
                active ? "bg-blue-50 text-blue-800" : "text-slate-700 hover:bg-slate-100"
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
