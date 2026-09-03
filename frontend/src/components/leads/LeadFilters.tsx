"use client";

import type { LeadStatus } from "./leadFields";
import { STATUS_LABELS, PANEL_HEIGHT } from "./leadFields";

export type BalanceRange = "120-500" | "500-1000" | "other";

export type LeadFilter = {
  search: string;
  statuses: LeadStatus[];
  balance: BalanceRange[];
};

export const EMPTY_FILTER: LeadFilter = { search: "", statuses: [], balance: [] };

const BALANCE_LABELS: Record<BalanceRange, string> = {
  "120-500": "120K - 500K ₺",
  "500-1000": "500K - 1M ₺",
  other: "Aralık dışı",
};

/** Bir listedeki degeri ekler ya da cikarir (cok secimli filtre davranisi). */
function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function FilterGroup<T extends string>({
  title,
  options,
  labels,
  selected,
  counts,
  onChange,
}: {
  title: string;
  options: readonly T[];
  labels: Record<T, string>;
  selected: T[];
  counts?: Record<string, number>;
  onChange: (value: T) => void;
}) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide app-muted">{title}</h3>
      <div className="space-y-1">
        {options.map((option) => {
          const active = selected.includes(option);
          return (
            <button
              key={option}
              type="button"
              onClick={() => onChange(option)}
              aria-pressed={active}
              className={`flex w-full items-center justify-between rounded-md border px-3 py-1.5 text-left text-sm transition ${
                active ? "app-primary border-transparent" : "app-card app-border app-subtle-hover"
              }`}
            >
              <span>{labels[option]}</span>
              {counts ? (
                <span className={`text-xs ${active ? "" : "app-muted"}`}>
                  {counts[option] ?? 0}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function LeadFilters({
  filter,
  onChange,
  statusCounts,
}: {
  filter: LeadFilter;
  onChange: (next: LeadFilter) => void;
  statusCounts: Record<string, number>;
}) {
  const hasActiveFilter =
    filter.search.trim() !== "" || filter.statuses.length > 0 || filter.balance.length > 0;

  return (
    <aside
      className={`${PANEL_HEIGHT} space-y-5 overflow-auto rounded-xl border app-card p-4 shadow-sm`}
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold app-heading">Filtreler</h2>
        {hasActiveFilter && (
          <button
            type="button"
            onClick={() => onChange(EMPTY_FILTER)}
            className="text-xs font-medium app-primary-text hover:underline"
          >
            Temizle
          </button>
        )}
      </div>

      <label className="block">
        <span className="sr-only">Lead ara</span>
        <input
          type="search"
          value={filter.search}
          onChange={(event) => onChange({ ...filter, search: event.target.value })}
          placeholder="İsim veya e-posta ara"
          className="w-full rounded-md border px-3 py-2 text-sm outline-none app-input"
        />
      </label>

      <FilterGroup
        title="Durum"
        // Sira aksiyon onceligine gore: once hala aranmasi gerekenler,
        // sonra kapanmis dosyalar, en sonda motorun kendi durumlari.
        options={
          [
            "bsd",
            "unreachable",
            "accepted",
            "declined",
            "email_sent",
            "email_pending",
            "excluded",
          ] as const
        }
        labels={STATUS_LABELS}
        selected={filter.statuses}
        counts={statusCounts}
        onChange={(value) => onChange({ ...filter, statuses: toggle(filter.statuses, value) })}
      />

      <FilterGroup
        title="Atıl bakiye"
        options={["120-500", "500-1000", "other"] as const}
        labels={BALANCE_LABELS}
        selected={filter.balance}
        onChange={(value) => onChange({ ...filter, balance: toggle(filter.balance, value) })}
      />
    </aside>
  );
}
