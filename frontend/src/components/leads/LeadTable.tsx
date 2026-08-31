"use client";

import { useMemo, useState } from "react";
import type { LeadQueueItem } from "../../models/leads";
import Badge from "../ui/Badge";
import Card from "../ui/Card";
import { ScoreReasonsPopover } from "./ScoreReasonsPopover";
import {
  DURUM_ETIKETLERI,
  PANEL_YUKSEKLIGI,
  telefonFormat,
  dislamaNedeni,
  durumBelirle,
  paraFormat,
  tarihFormat,
  yasHesapla,
} from "./leadFields";

/**
 * SABIT yukseklik: liste kac satir olursa olsun cerceve buyumez, tasan
 * satirlara scroll ile bakilir. Grid satirini bu kart belirledigi icin
 * (varsayilan `stretch`) sol filtre paneli de ayni boya gelir.
 *
 * `!pb-1`: kaydirma cubugunun altinda ince bir nefes payi birakir.
 */
const KART_SINIFI = `flex h-[34rem] ${PANEL_YUKSEKLIGI} flex-col overflow-hidden !px-0 !pt-0 !pb-1`;
const KAYDIRMA_SINIFI = "flex-1 overflow-auto";

type SiraAlani = "ad" | "durum" | "yas" | "gelir" | "bakiye" | "skor";
type SiraYonu = "asc" | "desc";

const SUTUNLAR: Array<{ alan: SiraAlani | null; baslik: string; sagaYasli?: boolean }> = [
  { alan: "ad", baslik: "Lead adı" },
  { alan: "durum", baslik: "Durum" },
  { alan: null, baslik: "Telefon" },
  { alan: null, baslik: "E-posta" },
  { alan: "yas", baslik: "Doğum tarihi" },
  { alan: "gelir", baslik: "Gelir", sagaYasli: true },
  { alan: "bakiye", baslik: "Atıl bakiye", sagaYasli: true },
  { alan: null, baslik: "TCKN" },
  { alan: "skor", baslik: "Skor", sagaYasli: true },
];

/** Durum rozetinin rengi: aksiyon bekleyenler dikkat cekici, digerleri sakin. */
const DURUM_SINIFLARI: Record<string, string> = {
  bsd: "app-warning-box border",
  mail_bekliyor: "app-warning-box border",
  mail_gonderildi: "app-primary-soft",
  dislandi: "app-card-muted app-muted",
};

function siralamaDegeri(item: LeadQueueItem, alan: SiraAlani): number | string {
  switch (alan) {
    case "ad":
      return `${item.first_name} ${item.last_name}`.toLocaleLowerCase("tr");
    case "durum":
      return DURUM_ETIKETLERI[durumBelirle(item)];
    case "yas":
      // Dogum tarihi bilinmeyenler her zaman sona dussun.
      return yasHesapla(item.birth_date) ?? -1;
    case "gelir":
      return item.monthly_income;
    case "bakiye":
      return item.likit_para;
    case "skor":
      return item.score;
  }
}

export function LeadTable({ items }: { items: LeadQueueItem[] }) {
  const [sira, setSira] = useState<{ alan: SiraAlani; yon: SiraYonu }>({
    alan: "skor",
    yon: "desc",
  });

  const sirali = useMemo(() => {
    const kopya = [...items];
    kopya.sort((a, b) => {
      const av = siralamaDegeri(a, sira.alan);
      const bv = siralamaDegeri(b, sira.alan);
      const fark =
        typeof av === "string" && typeof bv === "string"
          ? av.localeCompare(bv, "tr")
          : Number(av) - Number(bv);
      return sira.yon === "asc" ? fark : -fark;
    });
    return kopya;
  }, [items, sira]);

  function basligaTikla(alan: SiraAlani) {
    setSira((mevcut) =>
      mevcut.alan === alan
        ? { alan, yon: mevcut.yon === "asc" ? "desc" : "asc" }
        : // Yeni sutuna gecince sayisal alanlar buyukten kucuge daha
          // anlamli; metin alani alfabetik baslasin.
          { alan, yon: alan === "ad" ? "asc" : "desc" },
    );
  }

  if (items.length === 0) {
    return (
      <Card className={KART_SINIFI}>
        <div className={`${KAYDIRMA_SINIFI} flex items-center justify-center`}>
          <p className="text-sm app-muted">Bu filtrelerle eşleşen kimse yok.</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className={KART_SINIFI}>
      <div className={KAYDIRMA_SINIFI}>
        <table className="min-w-full text-left text-sm">
          <thead className="sticky top-0 z-10 app-card-muted text-xs uppercase app-muted shadow-[0_1px_0_var(--color-border)]">
            <tr>
              {SUTUNLAR.map((sutun) => (
                <th
                  key={sutun.baslik}
                  className={`px-3 py-3 font-semibold ${sutun.sagaYasli ? "text-right" : ""}`}
                >
                  {sutun.alan ? (
                    <button
                      type="button"
                      onClick={() => basligaTikla(sutun.alan as SiraAlani)}
                      className="inline-flex items-center gap-1 uppercase transition hover:opacity-80"
                    >
                      {sutun.baslik}
                      <span aria-hidden="true" className="text-[10px]">
                        {sira.alan === sutun.alan ? (sira.yon === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </button>
                  ) : (
                    sutun.baslik
                  )}
                </th>
              ))}
            </tr>
          </thead>

          <tbody className="divide-y app-border-soft">
            {sirali.map((item) => {
              const durum = durumBelirle(item);
              const neden = dislamaNedeni(item);
              const yas = yasHesapla(item.birth_date);

              return (
                <tr key={item.user_id} className="app-subtle-hover">
                  <td className="whitespace-nowrap px-3 py-3 font-semibold app-heading">
                    {item.first_name} {item.last_name}
                  </td>

                  <td className="px-3 py-3">
                    <Badge className={DURUM_SINIFLARI[durum]}>{DURUM_ETIKETLERI[durum]}</Badge>
                    {neden && <p className="mt-1 text-xs app-muted">{neden}</p>}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 app-heading">
                    {telefonFormat(item.phone_number)}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 app-muted">{item.email}</td>

                  <td className="whitespace-nowrap px-3 py-3">
                    {item.birth_date ? (
                      <>
                        <p className="app-heading">
                          {tarihFormat.format(new Date(item.birth_date))}
                        </p>
                        {yas !== null && <p className="mt-0.5 text-xs app-muted">{yas} yaş</p>}
                      </>
                    ) : (
                      <span className="app-muted">—</span>
                    )}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 text-right app-heading">
                    {paraFormat.format(item.monthly_income)}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 text-right font-semibold app-heading">
                    {paraFormat.format(item.likit_para)}
                  </td>

                  <td className="whitespace-nowrap px-3 py-3 app-muted">
                    {item.tckn_last4 ? `•••• ${item.tckn_last4}` : "—"}
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
