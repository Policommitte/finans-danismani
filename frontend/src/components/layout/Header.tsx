"use client";

import type { User } from "../../models/auth";
import { ThemeToggle } from "../ui/ThemeToggle";

export function Header({ user, onLogout }: { user: User | null; onLogout: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-4 border-b app-border app-surface px-4 py-3 backdrop-blur">
      <div className="ml-auto flex items-center gap-3">
        <div className="relative hidden w-64 sm:block">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 app-muted"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
          <input
            type="text"
            placeholder="Varlık, haber veya emir ara..."
            className="w-full rounded-lg border app-input py-2 pl-9 pr-3 text-sm outline-none focus:border-[var(--color-primary)]"
          />
        </div>
        <button
          type="button"
          aria-label="Bildirimler"
          className="relative grid h-10 w-10 place-items-center rounded-lg border app-border app-surface app-muted transition hover:opacity-80"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6" />
            <path d="M10 19a2 2 0 0 0 4 0" />
          </svg>
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-[var(--color-danger)]" />
        </button>
        <ThemeToggle />
        {user && (
          <button
            type="button"
            onClick={onLogout}
            className="rounded-lg border app-border app-surface px-3 py-2 text-sm font-medium app-muted transition hover:opacity-80"
          >
            Çıkış
          </button>
        )}
      </div>
    </header>
  );
}
