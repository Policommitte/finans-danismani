"use client";

import { useEffect } from "react";
import { ErrorState } from "../feedback/ErrorState";
import { LoadingState } from "../feedback/LoadingState";
import { useAsyncData } from "../../hooks/useAsyncData";
import type { EconomicEvent, EconomicEventImportance } from "../../models/economicCalendar";
import { getEconomicCalendar } from "../../services/economicCalendarService";

//: Onem rengi - turuncu (--color-cta) BILINCLI olarak kullanilmiyor (sitenin
//: geri kalaninda zaten kaldirildi). high = kirmizi (aciliyet), medium =
//: altin/sari, low = notr gri - "dusuk onem" bir basari/olumlu durum
//: olmadigi icin yesil KULLANILMAZ.
const IMPORTANCE_COLOR: Record<EconomicEventImportance, string> = {
  high: "var(--color-danger)",
  medium: "var(--color-chart-yellow)",
  low: "var(--color-muted)",
};

const IMPORTANCE_LABEL: Record<EconomicEventImportance, string> = {
  high: "Yüksek",
  medium: "Orta",
  low: "Düşük",
};

function ImportanceBadge({ importance }: { importance: EconomicEventImportance }) {
  const color = IMPORTANCE_COLOR[importance];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold"
      style={{ background: `color-mix(in srgb, ${color} 16%, transparent)`, color }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {IMPORTANCE_LABEL[importance]}
    </span>
  );
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" });
}

function EventRow({ event }: { event: EconomicEvent }) {
  return (
    <tr className="app-border border-b last:border-0">
      <td className="whitespace-nowrap px-4 py-3 text-sm app-heading">{formatDate(event.event_date)}</td>
      <td className="whitespace-nowrap px-4 py-3 text-sm tabular-nums app-muted">{event.event_time ?? "—"}</td>
      <td className="whitespace-nowrap px-4 py-3 text-sm font-semibold app-muted">{event.country}</td>
      <td className="px-4 py-3 text-sm app-heading">
        {event.event_name}
        <span className="mt-0.5 block text-xs app-muted">{event.source_label}</span>
      </td>
      <td className="whitespace-nowrap px-4 py-3">
        <ImportanceBadge importance={event.importance} />
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-sm app-muted">{event.previous ?? "—"}</td>
      <td className="whitespace-nowrap px-4 py-3 text-sm app-heading">{event.actual ?? "—"}</td>
    </tr>
  );
}

export function EconomicCalendarTab({ onReady }: { onReady?: () => void }) {
  const { data, loading, error, refetch } = useAsyncData(getEconomicCalendar, []);

  useEffect(() => {
    if (loading) return;

    const frame = window.requestAnimationFrame(() => onReady?.());
    return () => window.cancelAnimationFrame(frame);
  }, [loading, onReady]);

  if (loading && !data) {
    return <LoadingState label="Ekonomik takvim yükleniyor" />;
  }

  if (error && !data) {
    return <ErrorState message={error} onRetry={refetch} />;
  }

  const items = data?.items ?? [];

  return (
    <div className="space-y-3">
      <p className="text-sm app-muted">
        Türkiye&apos;ye özel veriler (TCMB, TÜİK) yıl boyu resmi kaynaklardan; diğer büyük ekonomilerin
        verileri (ABD, AB, Japonya vb.) Yahoo Finance&apos;ten otomatik çekilir. Saatler Türkiye saatiyle
        gösterilir.
      </p>
      <p className="text-xs app-muted">
        Not: Yahoo Finance yalnızca yaklaşan birkaç haftalık dönemi yayımlıyor; Türkiye&apos;ye özel
        olaylar yıl sonuna kadar, global olaylar ise Yahoo&apos;nun yayımladığı kadarıyla listelenir.
        Ücretsiz veri kaynağı piyasa beklentisi (konsensüs) rakamı sağlamadığı için &quot;Beklenti&quot;
        sütunu gösterilmiyor; &quot;Önceki&quot; ve &quot;Gerçekleşen&quot; yalnızca veri kaynağında
        mevcutsa görünür.
      </p>
      {items.length === 0 ? (
        <div className="rounded-lg border app-card p-6 text-sm app-muted">
          Şu an listelenecek bir ekonomik olay yok.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border app-border app-card">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <thead>
              <tr className="app-border border-b text-xs font-semibold uppercase tracking-wide app-muted">
                <th className="px-4 py-3">Tarih</th>
                <th className="px-4 py-3">Saat</th>
                <th className="px-4 py-3">Ülke</th>
                <th className="px-4 py-3">Olay</th>
                <th className="px-4 py-3">Önem</th>
                <th className="px-4 py-3">Önceki</th>
                <th className="px-4 py-3">Gerçekleşen</th>
              </tr>
            </thead>
            <tbody>
              {items.map((event, index) => (
                <EventRow key={`${event.event_date}-${event.event_name}-${index}`} event={event} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
