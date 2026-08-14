"use client";

import type { User } from "../../models/auth";
import Button from "../ui/Button";

export function Header({ user, onLogout }: { user: User | null; onLogout: () => void }) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-900">Akilli Kisisel Finans Danismani</div>
          <div className="text-xs text-slate-500">Backend FastAPI endpointleri ile entegre</div>
        </div>
        {user && (
          <div className="flex items-center gap-3">
            <div className="hidden text-right text-sm sm:block">
              <div className="font-medium text-slate-900">
                {user.first_name} {user.last_name}
              </div>
              <div className="text-xs text-slate-500">{user.email}</div>
            </div>
            <Button variant="secondary" onClick={onLogout}>
              Cikis
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
