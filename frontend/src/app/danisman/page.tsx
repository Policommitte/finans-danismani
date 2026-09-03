"use client";

import { useMemo, useState } from "react";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { LeadFilters, EMPTY_FILTER } from "../../components/leads/LeadFilters";
import type { BalanceRange, LeadFilter } from "../../components/leads/LeadFilters";
import { LeadTable } from "../../components/leads/LeadTable";
import { resolveStatus } from "../../components/leads/leadFields";
import { useLeads } from "../../hooks/useLeads";
import type { LeadQueueItem } from "../../models/leads";

/** `lead_rules.py` esikleriyle ayni: 120K alt sinir, 500K BSD esigi, 1M ust sinir. */
function balanceRange(idleCash: number): BalanceRange {
  if (idleCash >= 120_000 && idleCash < 500_000) return "120-500";
  if (idleCash >= 500_000 && idleCash < 1_000_000) return "500-1000";
  return "other";
}

export default function DanismanPage() {
  const leads = useLeads();
  const [filter, setFilter] = useState<LeadFilter>(EMPTY_FILTER);

  // Uc kuyruk tek listede birlesir. Ayni kullanici birden fazla kuyrukta
  // gorunebilir (orn. mail gonderilmis ama son taramada EXCLUDED olmus);
  // `user_id` bazinda tekillestirilir, once gelen kazanir - siralama
  // BSD > otonom > dislanan, yani aksiyon gerektiren karar one cikar.
  const allLeads = useMemo(() => {
    if (!leads.data) return [];
    const byUserId = new Map<number, LeadQueueItem>();
    for (const queue of [leads.data.bsd, leads.data.autonomous, leads.data.excluded]) {
      for (const item of queue.items) {
        if (!byUserId.has(item.user_id)) byUserId.set(item.user_id, item);
      }
    }
    return [...byUserId.values()];
  }, [leads.data]);

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const item of allLeads) {
      const status = resolveStatus(item);
      counts[status] = (counts[status] ?? 0) + 1;
    }
    return counts;
  }, [allLeads]);

  const filteredLeads = useMemo(() => {
    const search = filter.search.trim().toLocaleLowerCase("tr");

    return allLeads.filter((item) => {
      if (search) {
        const haystack = `${item.first_name} ${item.last_name} ${item.email}`.toLocaleLowerCase(
          "tr",
        );
        if (!haystack.includes(search)) return false;
      }
      if (filter.statuses.length > 0 && !filter.statuses.includes(resolveStatus(item))) {
        return false;
      }
      if (filter.balance.length > 0 && !filter.balance.includes(balanceRange(item.likit_para))) {
        return false;
      }
      return true;
    });
  }, [allLeads, filter]);

  if (leads.loading) {
    return <LoadingState label="Lead verileri yukleniyor" />;
  }

  if (leads.error || !leads.data) {
    return <ErrorState message={leads.error ?? "Lead verisi bos dondu."} onRetry={leads.refetch} />;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold app-heading">Danışman Paneli</h1>

      {/* Grid ogeleri ayni satir yuksekligini paylasir (varsayilan stretch):
          tablo karti sol filtre paneliyle AYNI boyda durur. Kartin ici flex
          kolon oldugu icin kaydirma alani bu yuksekligi doldurur - altta
          yalnizca ince bir nefes payi kalir. */}
      <div className="grid gap-4 lg:grid-cols-[13rem_1fr]">
        <LeadFilters filter={filter} onChange={setFilter} statusCounts={statusCounts} />
        <LeadTable
          items={filteredLeads}
          onOutcomeSelect={leads.saveOutcome}
          savingUserId={leads.savingUserId}
        />
      </div>
    </div>
  );
}
