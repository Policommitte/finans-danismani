"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { User } from "../../models/auth";

const links = [
  {
    href: "/dashboard",
    label: "Genel Bakış",
    icon: (
      <>
        <path d="M3 10.5L12 3L21 10.5" />
        <path d="M5.5 9V20C5.5 20.5523 5.94772 21 6.5 21H9.5C10.0523 21 10.5 20.5523 10.5 20V15C10.5 14.4477 10.9477 14 11.5 14H12.5C13.0523 14 13.5 14.4477 13.5 15V20C13.5 20.5523 13.9477 21 14.5 21H17.5C18.0523 21 18.5 20.5523 18.5 20V9" />
      </>
    ),
  },
  {
    href: "/portfolio",
    label: "Portföy",
    icon: (
      <>
        <rect x="3" y="7.5" width="18" height="12" rx="2" />
        <path d="M8.5 7.5V6C8.5 4.89543 9.39543 4 10.5 4H13.5C14.6046 4 15.5 4.89543 15.5 6V7.5" />
        <path d="M3 12.5H21" />
        <path d="M10.5 12.5V14" />
        <path d="M13.5 12.5V14" />
      </>
    ),
  },
  {
    href: "/bulten",
    label: "Bülten",
    icon: (
      <>
        <path d="M4 4h13l3 3v13a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" />
        <path d="M8 9h8" />
        <path d="M8 13h8" />
        <path d="M8 17h5" />
      </>
    ),
  },
  {
    href: "/islemler",
    label: "İşlemler",
    icon: (
      <>
        <path d="M7 7h11l-3-3" />
        <path d="M7 7l3 3" />
        <path d="M17 17H6l3-3" />
        <path d="M17 17l-3 3" />
      </>
    ),
  },
  {
    href: "/yatirim-oyunu",
    label: "Yatırım Oyunu",
    icon: (
      <>
        <path d="M8 21h8" />
        <path d="M12 17v4" />
        <path d="M7 4h10v5a5 5 0 0 1-10 0z" />
        <path d="M17 5h3a2 2 0 0 1-2 4h-1" />
        <path d="M7 5H4a2 2 0 0 0 2 4h1" />
      </>
    ),
  },
  {
    href: "/destek",
    label: "Destek",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 1.7-2.5 2.1-2.5 3.8" />
        <path d="M12 17h.01" />
      </>
    ),
  },
  {
    href: "/profile",
    label: "Profil",
    icon: (
      <>
        <circle cx="12" cy="8" r="3.5" />
        <path d="M4.5 20C4.5 16.5482 7.68629 13.75 12 13.75C16.3137 13.75 19.5 16.5482 19.5 20" />
      </>
    ),
  },
];

const systemLinks = [
  {
    href: "/settings",
    label: "Ayarlar",
    icon: (
      <>
        <path
          d="M13.4 3.2C13.35 2.85 13.05 2.6 12.7 2.6H11.3C10.95 2.6 10.65 2.85 10.6 3.2L10.35 4.85C9.75 5.03 9.19 5.29 8.68 5.62L7.16 4.95C6.84 4.81 6.47 4.91 6.27 5.2L5.57 6.4C5.39 6.7 5.44 7.08 5.7 7.32L6.92 8.42C6.82 9.03 6.82 9.65 6.92 10.26L5.7 11.36C5.44 11.6 5.39 11.98 5.57 12.28L6.27 13.48C6.47 13.77 6.84 13.87 7.16 13.73L8.68 13.06C9.19 13.39 9.75 13.65 10.35 13.83L10.6 15.48C10.65 15.83 10.95 16.08 11.3 16.08H12.7C13.05 16.08 13.35 15.83 13.4 15.48L13.65 13.83C14.25 13.65 14.81 13.39 15.32 13.06L16.84 13.73C17.16 13.87 17.53 13.77 17.73 13.48L18.43 12.28C18.61 11.98 18.56 11.6 18.3 11.36L17.08 10.26C17.18 9.65 17.18 9.03 17.08 8.42L18.3 7.32C18.56 7.08 18.61 6.7 18.43 6.4L17.73 5.2C17.53 4.91 17.16 4.81 16.84 4.95L15.32 5.62C14.81 5.29 14.25 5.03 13.65 4.85L13.4 3.2Z"
          transform="translate(0.5, 3)"
        />
        <circle cx="12.5" cy="12.3" r="2.4" />
      </>
    ),
  },
];

function NavList({ items, pathname }: { items: typeof links; pathname: string }) {
  return (
    <nav className="flex flex-col gap-1">
      {items.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-label={link.label}
            className={`group relative flex items-center justify-center rounded-lg px-3 py-2.5 transition ${
              active ? "bg-white text-[var(--color-panel-dark)] shadow" : "text-white/75 hover:bg-white/10"
            }`}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={active ? 2 : 1.8}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="shrink-0"
            >
              {link.icon}
            </svg>
            <span
              role="tooltip"
              className="pointer-events-none absolute left-full top-1/2 z-50 ml-3 -translate-y-1/2 whitespace-nowrap rounded-md app-card border px-2.5 py-1.5 text-xs font-medium app-heading opacity-0 shadow-md transition group-hover:opacity-100"
            >
              {link.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar({ user }: { user: User | null }) {
  const pathname = usePathname();
  const initials = user ? `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`.toUpperCase() : "?";

  return (
    <aside className="sticky top-0 hidden h-screen w-[72px] shrink-0 flex-col items-center overflow-y-auto bg-[var(--color-panel-dark)] px-2 py-5 text-white md:flex">
      <div className="grid h-11 w-11 place-items-center rounded-xl bg-white">
        <span
          aria-hidden="true"
          className="block h-5 w-5 bg-[#0f172a] [mask-image:url('/polifin-logo-clean.svg')] [mask-position:center] [mask-repeat:no-repeat] [mask-size:contain]"
        />
        <span className="sr-only">POLIFIN</span>
      </div>

      <div className="mt-7 w-full">
        <NavList items={links} pathname={pathname} />
      </div>

      <div className="mt-6 w-full border-t border-white/10 pt-4">
        <NavList items={systemLinks} pathname={pathname} />
      </div>

      <div className="group relative mt-auto flex items-center justify-center border-t border-white/10 pt-4">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-white/10 text-xs font-semibold">
          {initials || "?"}
        </div>
        {user && (
          <span
            role="tooltip"
            className="pointer-events-none absolute left-full bottom-0 z-50 ml-3 whitespace-nowrap rounded-md app-card border px-2.5 py-1.5 text-xs font-medium app-heading opacity-0 shadow-md transition group-hover:opacity-100"
          >
            {user.first_name} {user.last_name}
          </span>
        )}
      </div>
    </aside>
  );
}
