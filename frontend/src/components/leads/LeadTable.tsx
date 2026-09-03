"use client";

import { useMemo, useState } from "react";
import type { CallOutcomeInput, LeadQueueItem } from "../../models/leads";
import Badge from "../ui/Badge";
import Card from "../ui/Card";
import { CallOutcomeMenu } from "./CallOutcomeMenu";
import { ScoreReasonsPopover } from "./ScoreReasonsPopover";
import {
  STATUS_LABELS,
  STATUS_CLASSES,
  OUTCOME_EDITABLE_STATUSES,
  PANEL_HEIGHT,
  formatPhone,
  exclusionReasonLabel,
  resolveStatus,
  moneyFormat,
  dateFormat,
  calculateAge,
} from "./leadFields";

/**
 * SABIT yukseklik: liste kac satir olursa olsun cerceve buyumez, tasan
 * satirlara scroll ile bakilir. Grid satirini bu kart belirledigi icin
 * (varsayilan `stretch`) sol filtre paneli de ayni boya gelir.
 *
 * `!pb-1`: kaydirma cubugunun altinda ince bir nefes payi birakir.
 */
const CARD_CLASS = `flex h-[34rem] ${PANEL_HEIGHT} flex-col overflow-hidden !px-0 !pt-0 !pb-1`;
const SCROLL_CLASS = "flex-1 overflow-auto";

//: Siralanabilen sutunlar, danismanin kuyrugu onceliklendirirken baktigi
//: olculer: atil bakiye, sisteme eklenme tarihi ve skor. Ad/durum/dogum
//: tarihi/gelir tanitici bilgidir, basliklarinda ok gosterilmez.
type SortField = "balance" | "registered" | "score";
type SortDirection = "asc" | "desc";

const COLUMNS: Array<{ field: SortField | null; title: string; alignRight?: boolean }> = [
  { field: null, title: "Lead adı" },
  { field: null, title: "Durum" },
  { field: null, title: "Telefon" },
  { field: null, title: "E-posta" },
  { field: null, title: "Doğum tarihi" },
  { field: null, title: "Gelir", alignRight: true },
  { field: "balance", title: "Atıl bakiye", alignRight: true },
  { field: null, title: "TCKN" },
  { field: "registered", title: "Eklenme tarihi" },
  { field: "score", title: "Skor", alignRight: true },
];

function sortValue(item: LeadQueueItem, field: SortField): number {
  if (field === "balance") return item.likit_para;
  if (field === "score") return item.score;
  // Tarihi bilinmeyenler her zaman sona dussun (hangi yonde siralanirsa
  // siralansin degil - `desc`'te en kucuk, `asc`'te en buyuk olmalari
  // gerekirdi; basitlik icin 0 kabul edip en eski gibi davraniyoruz).
  return item.registered_at ? Date.parse(item.registered_at) : 0;
}

export function LeadTable({
  items,
  onOutcomeSelect,
  savingUserId,
}: {
  items: LeadQueueItem[];
  onOutcomeSelect: (userId: number, outcome: CallOutcomeInput) => void;
  /** Su an kaydedilmekte olan satir; menu o sure boyunca kilitlenir. */
  savingUserId: number | null;
}) {
  const [sort, setSort] = useState<{ field: SortField; direction: SortDirection }>({
    field: "score",
    direction: "desc",
  });

  const sortedItems = useMemo(() => {
    const copy = [...items];
    copy.sort((a, b) => {
      const diff = sortValue(a, sort.field) - sortValue(b, sort.field);
      return sort.direction === "asc" ? diff : -diff;
    });
    return copy;
  }, [items, sort]);

  function handleHeaderClick(field: SortField) {
    setSort((current) =>
      current.field === field
        ? { field, direction: current.direction === "asc" ? "desc" : "asc" }
        : // Iki sutun da sayisal; yeni sutuna gecince buyukten kucuge
          // baslamak daha anlamli.
          { field, direction: "desc" },
    );
  }

  if (items.length === 0) {
    return (
      <Card className={CARD_CLASS}>
        <div className={`${SCROLL_CLASS} flex items-center justify-center`}>
          <p className="text-sm app-muted">Bu filtrelerle eşleşen kimse yok.</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className={CARD_CLASS}>
      <div className={SCROLL_CLASS}>
        <table className="min-w-full text-left text-sm">
          <thead className="sticky top-0 z-10 app-card-muted text-xs uppercase app-muted shadow-[0_1px_0_var(--color-border)]">
            <tr>
              {COLUMNS.map((column) => (
                <th
                  key={column.title}
                  className={`px-3 py-3 font-semibold ${column.alignRight ? "text-right" : ""}`}
                >
                  {column.field ? (
                    <button
                      type="button"
                      onClick={() => handleHeaderClick(column.field as SortField)}
                      className="inline-flex items-center gap-1 uppercase transition hover:opacity-80"
                    >
                      {column.title}
                      <span aria-hidden="true" className="text-[10px]">
                        {sort.field === column.field ? (sort.direction === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </button>
                  ) : (
                    column.title
                  )}
                </th>
              ))}
            </tr>
          </thead>

          <tbody className="divide-y app-border-soft">
            {sortedItems.map((item) => {
              const status = resolveStatus(item);
              const reason = exclusionReasonLabel(item);
              const age = calculateAge(item.birth_date);

              return (
                <tr key={item.user_id} className="app-subtle-hover">
                  <td className="whitespace-nowrap px-3 py-3 font-semibold app-heading">
                    {item.first_name} {item.last_name}
                  </td>

                  <td className="px-3 py-3">
                    {OUTCOME_EDITABLE_STATUSES.has(status) ? (
                      <CallOutcomeMenu
                        status={status}
                        currentOutcome={item.call_outcome}
                        saving={savingUserId === item.user_id}
                        onSelect={(outcome) => onOutcomeSelect(item.user_id, outcome)}
                      />
                    ) : (
                      <Badge className={STATUS_CLASSES[status]}>{STATUS_LABELS[status]}</Badge>
                    )}
                    {reason && <p className="mt-1 text-xs app-muted">{reason}</p>}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 app-heading">
                    {formatPhone(item.phone_number)}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 app-muted">{item.email}</td>

                  <td className="whitespace-nowrap px-3 py-3">
                    {item.birth_date ? (
                      <>
                        <p className="app-heading">
                          {dateFormat.format(new Date(item.birth_date))}
                        </p>
                        {age !== null && <p className="mt-0.5 text-xs app-muted">{age} yaş</p>}
                      </>
                    ) : (
                      <span className="app-muted">—</span>
                    )}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 text-right app-heading">
                    {moneyFormat.format(item.monthly_income)}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 text-right font-semibold app-heading">
                    {moneyFormat.format(item.likit_para)}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 app-muted">
                    {item.tckn_last4 ? `•••• ${item.tckn_last4}` : "—"}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 app-heading">
                    {item.registered_at
                      ? dateFormat.format(new Date(item.registered_at))
                      : <span className="app-muted">—</span>}
                  </td>

                  <td className="px-3 py-3">
                    <span className="flex items-center justify-end gap-2">
                      <span className="font-semibold app-heading">{item.score}</span>
                      <ScoreReasonsPopover reasons={item.reasons} />
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
