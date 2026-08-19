"use client";

import type { User } from "../../models/auth";
import Button from "../ui/Button";
import { ThemeToggle } from "../ui/ThemeToggle";

export function Header({ user, onLogout }: { user: User | null; onLogout: () => void }) {
  return (
    <header className="sticky top-0 z-20 border-b app-border app-surface px-4 py-3 backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold app-heading">Akilli Kisisel Finans Danismani</div>
          <div className="text-xs app-muted">Backend FastAPI endpointleri ile entegre</div>
        </div>
        {user && (
          <div className="flex items-center gap-3">
            <div className="hidden text-right text-sm sm:block">
              <div className="font-medium app-heading">
                {user.first_name} {user.last_name}
              </div>
              <div className="text-xs app-muted">{user.email}</div>
            </div>
            <ThemeToggle />
            <Button variant="secondary" onClick={onLogout}>
              Cikis
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
