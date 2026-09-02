"use client";

import { useMemo, useState } from "react";
import type { CallOutcomeInput, LeadQueueItem } from "../../models/leads";
import Badge from "../ui/Badge";
import Card from "../ui/Card";
import { CallOutcomeMenu } from "./CallOutcomeMenu";
import { ScoreReasonsPopover } from "./ScoreReasonsPopover";
import {
  DURUM_ETIKETLERI,
  DURUM_SINIFLARI,
  SONUC_ISARETLENEBILIR,
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

//: Siralanabilen sutunlar, danismanin kuyrugu onceliklendirirken baktigi
//: olculer: atil bakiye, sisteme eklenme tarihi ve skor. Ad/durum/dogum
//: tarihi/gelir tanitici bilgidir, basliklarinda ok gosterilmez.
type SiraAlani = "bakiye" | "eklenme" | "skor";
type SiraYonu = "asc" | "desc";

const SUTUNLAR: Array<{ alan: SiraAlani | null; baslik: string; sagaYasli?: boolean }> = [
  { alan: null, baslik: "Lead adı" },
  { alan: null, baslik: "Durum" },
  { alan: null, baslik: "Telefon" },
  { alan: null, baslik: "E-posta" },
  { alan: null, baslik: "Doğum tarihi" },
  { alan: null, baslik: "Gelir", sagaYasli: true },
  { alan: "bakiye", baslik: "Atıl bakiye", sagaYasli: true },
  { alan: null, baslik: "TCKN" },
  { alan: "eklenme", baslik: "Eklenme tarihi" },
  { alan: "skor", baslik: "Skor", sagaYasli: true },
];

function siralamaDegeri(item: LeadQueueItem, alan: SiraAlani): number {
  if (alan === "bakiye") return item.likit_para;
  if (alan === "skor") return item.score;
  // Tarihi bilinmeyenler her zaman sona dussun (hangi yonde siralanirsa
  // siralansin degil - `desc`'te en kucuk, `asc`'te en buyuk olmalari
  // gerekirdi; basitlik icin 0 kabul edip en eski gibi davraniyoruz).
  return item.registered_at ? Date.parse(item.registered_at) : 0;
}

export function LeadTable({
  items,
  onSonucSec,
  kaydedilenId,
}: {
  items: LeadQueueItem[];
  onSonucSec: (userId: number, outcome: CallOutcomeInput) => void;
  /** Su an kaydedilmekte olan satir; menu o sure boyunca kilitlenir. */
  kaydedilenId: number | null;
}) {
  const [sira, setSira] = useState<{ alan: SiraAlani; yon: SiraYonu }>({
    alan: "skor",
    yon: "desc",
  });

  const sirali = useMemo(() => {
    const kopya = [...items];
    kopya.sort((a, b) => {
      const fark = siralamaDegeri(a, sira.alan) - siralamaDegeri(b, sira.alan);
      return sira.yon === "asc" ? fark : -fark;
    });
    return kopya;
  }, [items, sira]);

  function basligaTikla(alan: SiraAlani) {
    setSira((mevcut) =>
      mevcut.alan === alan
        ? { alan, yon: mevcut.yon === "asc" ? "desc" : "asc" }
        : // Iki sutun da sayisal; yeni sutuna gecince buyukten kucuge
          // baslamak daha anlamli.
          { alan, yon: "desc" },
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
                    {SONUC_ISARETLENEBILIR.has(durum) ? (
                      <CallOutcomeMenu
                        durum={durum}
                        mevcutSonuc={item.call_outcome}
                        kaydediliyor={kaydedilenId === item.user_id}
                        onSec={(outcome) => onSonucSec(item.user_id, outcome)}
                      />
                    ) : (
                      <Badge className={DURUM_SINIFLARI[durum]}>{DURUM_ETIKETLERI[durum]}</Badge>
                    )}
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

                  <td className="whitespace-nowrap px-3 py-3 app-heading">
                    {item.registered_at
                      ? tarihFormat.format(new Date(item.registered_at))
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
