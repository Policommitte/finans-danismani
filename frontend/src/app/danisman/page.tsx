"use client";

import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { LeadQueueTable } from "../../components/leads/LeadQueueTable";
import { useLeads } from "../../hooks/useLeads";

export default function DanismanPage() {
  const leads = useLeads();

  if (leads.loading) {
    return <LoadingState label="Lead verileri yukleniyor" />;
  }

  if (leads.error || !leads.data) {
    return <ErrorState message={leads.error ?? "Lead verisi bos dondu."} onRetry={leads.refetch} />;
  }

  const { bsd, autonomous } = leads.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">Danışman</h1>
        <p className="mt-1 text-sm app-muted">
          Aranacak kişiler ve otomatik davet gönderilenler.
        </p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <LeadQueueTable title="Aranacaklar" items={bsd.items} variant="bsd" />
        <LeadQueueTable title="Mail gönderildi" items={autonomous.items} variant="autonomous" />
      </div>
    </div>
  );
}