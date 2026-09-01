"use client";

import { useMemo, useState } from "react";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { LeadFilters, BOS_FILTRE } from "../../components/leads/LeadFilters";
import type { BakiyeAraligi, LeadFiltre, YasAraligi } from "../../components/leads/LeadFilters";
import { LeadTable } from "../../components/leads/LeadTable";
import { durumBelirle, yasHesapla } from "../../components/leads/leadFields";
import { useLeads } from "../../hooks/useLeads";
import type { LeadQueueItem } from "../../models/leads";

/** `lead_rules.py` esikleriyle ayni: 120K alt sinir, 500K BSD esigi, 1M ust sinir. */
function bakiyeAraligi(likitPara: number): BakiyeAraligi {
  if (likitPara >= 120_000 && likitPara < 500_000) return "120-500";
  if (likitPara >= 500_000 && likitPara < 1_000_000) return "500-1000";
  return "diger";
}

function yasAraligi(item: LeadQueueItem): YasAraligi {
  const yas = yasHesapla(item.birth_date);
  if (yas === null) return "bilinmiyor";
  return yas >= 25 && yas <= 45 ? "25-45" : "disi";
}

export default function DanismanPage() {
  const leads = useLeads();
  const [filtre, setFiltre] = useState<LeadFiltre>(BOS_FILTRE);

  // Uc kuyruk tek listede birlesir. Ayni kullanici birden fazla kuyrukta
  // gorunebilir (orn. mail gonderilmis ama son taramada EXCLUDED olmus);
  // `user_id` bazinda tekillestirilir, once gelen kazanir - siralama
  // BSD > otonom > dislanan, yani aksiyon gerektiren karar one cikar.
  const tumLeadler = useMemo(() => {
    if (!leads.data) return [];
    const harita = new Map<number, LeadQueueItem>();
    for (const liste of [leads.data.bsd, leads.data.autonomous, leads.data.excluded]) {
      for (const item of liste.items) {
        if (!harita.has(item.user_id)) harita.set(item.user_id, item);
      }
    }
    return [...harita.values()];
  }, [leads.data]);

  const durumSayaclari = useMemo(() => {
    const sayac: Record<string, number> = {};
    for (const item of tumLeadler) {
      const durum = durumBelirle(item);
      sayac[durum] = (sayac[durum] ?? 0) + 1;
    }
    return sayac;
  }, [tumLeadler]);

  const filtreli = useMemo(() => {
    const arama = filtre.arama.trim().toLocaleLowerCase("tr");

    return tumLeadler.filter((item) => {
      if (arama) {
        const metin = `${item.first_name} ${item.last_name} ${item.email}`.toLocaleLowerCase("tr");
        if (!metin.includes(arama)) return false;
      }
      if (filtre.durumlar.length > 0 && !filtre.durumlar.includes(durumBelirle(item))) {
        return false;
      }
      if (filtre.bakiye.length > 0 && !filtre.bakiye.includes(bakiyeAraligi(item.likit_para))) {
        return false;
      }
      if (filtre.yas.length > 0 && !filtre.yas.includes(yasAraligi(item))) {
        return false;
      }
      return true;
    });
  }, [tumLeadler, filtre]);

  if (leads.loading) {
    return <LoadingState label="Lead verileri yukleniyor" />;
  }

  if (leads.error || !leads.data) {
    return <ErrorState message={leads.error ?? "Lead verisi bos dondu."} onRetry={leads.refetch} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">Danışman</h1>
        <p className="mt-1 text-sm app-muted">
          {filtreli.length} lead gösteriliyor
          {filtreli.length !== tumLeadler.length ? ` (toplam ${tumLeadler.length})` : ""}.
        </p>
      </div>

      {/* Grid ogeleri ayni satir yuksekligini paylasir (varsayilan stretch):
          tablo karti sol filtre paneliyle AYNI boyda durur. Kartin ici flex
          kolon oldugu icin kaydirma alani bu yuksekligi doldurur - altta
          yalnizca ince bir nefes payi kalir. */}
      <div className="grid gap-4 lg:grid-cols-[13rem_1fr]">
        <LeadFilters filtre={filtre} onDegis={setFiltre} durumSayaclari={durumSayaclari} />
        <LeadTable items={filtreli} />
      </div>
    </div>
  );
}
