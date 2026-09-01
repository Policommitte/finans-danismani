"use client";

import type { LeadDurum } from "./leadFields";
import { DURUM_ETIKETLERI, PANEL_YUKSEKLIGI } from "./leadFields";

export type BakiyeAraligi = "120-500" | "500-1000" | "diger";
export type YasAraligi = "25-45" | "disi" | "bilinmiyor";

export type LeadFiltre = {
  arama: string;
  durumlar: LeadDurum[];
  bakiye: BakiyeAraligi[];
  yas: YasAraligi[];
};

export const BOS_FILTRE: LeadFiltre = { arama: "", durumlar: [], bakiye: [], yas: [] };

const BAKIYE_ETIKETLERI: Record<BakiyeAraligi, string> = {
  "120-500": "120K - 500K ₺",
  "500-1000": "500K - 1M ₺",
  diger: "Aralık dışı",
};

const YAS_ETIKETLERI: Record<YasAraligi, string> = {
  "25-45": "25 - 45 yaş",
  disi: "Aralık dışı",
  bilinmiyor: "Bilinmiyor",
};

/** Bir listedeki degeri ekler ya da cikarir (cok secimli filtre davranisi). */
function degistir<T>(liste: T[], deger: T): T[] {
  return liste.includes(deger) ? liste.filter((d) => d !== deger) : [...liste, deger];
}

function FiltreGrubu<T extends string>({
  baslik,
  secenekler,
  etiketler,
  secili,
  sayaclar,
  onDegis,
}: {
  baslik: string;
  secenekler: readonly T[];
  etiketler: Record<T, string>;
  secili: T[];
  sayaclar?: Record<string, number>;
  onDegis: (deger: T) => void;
}) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide app-muted">{baslik}</h3>
      <div className="space-y-1">
        {secenekler.map((secenek) => {
          const aktif = secili.includes(secenek);
          return (
            <button
              key={secenek}
              type="button"
              onClick={() => onDegis(secenek)}
              aria-pressed={aktif}
              className={`flex w-full items-center justify-between rounded-md border px-3 py-1.5 text-left text-sm transition ${
                aktif ? "app-primary border-transparent" : "app-card app-border app-subtle-hover"
              }`}
            >
              <span>{etiketler[secenek]}</span>
              {sayaclar ? (
                <span className={`text-xs ${aktif ? "" : "app-muted"}`}>
                  {sayaclar[secenek] ?? 0}
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
  filtre,
  onDegis,
  durumSayaclari,
}: {
  filtre: LeadFiltre;
  onDegis: (yeni: LeadFiltre) => void;
  durumSayaclari: Record<string, number>;
}) {
  const aktifVar =
    filtre.arama.trim() !== "" ||
    filtre.durumlar.length > 0 ||
    filtre.bakiye.length > 0 ||
    filtre.yas.length > 0;

  return (
    <aside
      className={`${PANEL_YUKSEKLIGI} space-y-5 overflow-auto rounded-xl border app-card p-4 shadow-sm`}
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold app-heading">Filtreler</h2>
        {aktifVar && (
          <button
            type="button"
            onClick={() => onDegis(BOS_FILTRE)}
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
          value={filtre.arama}
          onChange={(e) => onDegis({ ...filtre, arama: e.target.value })}
          placeholder="İsim veya e-posta ara"
          className="w-full rounded-md border px-3 py-2 text-sm outline-none app-input"
        />
      </label>

      <FiltreGrubu
        baslik="Durum"
        secenekler={["bsd", "mail_gonderildi", "mail_bekliyor", "dislandi"] as const}
        etiketler={DURUM_ETIKETLERI}
        secili={filtre.durumlar}
        sayaclar={durumSayaclari}
        onDegis={(d) => onDegis({ ...filtre, durumlar: degistir(filtre.durumlar, d) })}
      />

      <FiltreGrubu
        baslik="Atıl bakiye"
        secenekler={["120-500", "500-1000", "diger"] as const}
        etiketler={BAKIYE_ETIKETLERI}
        secili={filtre.bakiye}
        onDegis={(d) => onDegis({ ...filtre, bakiye: degistir(filtre.bakiye, d) })}
      />

      <FiltreGrubu
        baslik="Yaş"
        secenekler={["25-45", "disi", "bilinmiyor"] as const}
        etiketler={YAS_ETIKETLERI}
        secili={filtre.yas}
        onDegis={(d) => onDegis({ ...filtre, yas: degistir(filtre.yas, d) })}
      />
    </aside>
  );
}
