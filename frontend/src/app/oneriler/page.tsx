"use client";

import { useMemo, useState } from "react";
import { RecommendationCard } from "../../components/recommendations/RecommendationCard";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { useRecommendations } from "../../hooks/useRecommendations";
import { useLanguage } from "../../contexts/LanguageContext";
import type { RecommendationStatus } from "../../models/recommendation";

/**
 * FR-AUT-011: bekleyen, onaylanan, reddedilen ve suresi dolan oneriler
 * AYRI sekmelerde listelenir.
 */
const SEKMELER: Array<{
  key: string;
  tr: string;
  en: string;
  statuses: RecommendationStatus[];
}> = [
  { key: "open", tr: "Bekleyen", en: "Pending", statuses: ["PUBLISHED", "VIEWED"] },
  { key: "done", tr: "Onaylanan", en: "Approved", statuses: ["APPROVED", "CONVERTED"] },
  { key: "rejected", tr: "Reddedilen", en: "Rejected", statuses: ["REJECTED"] },
  { key: "closed", tr: "Süresi dolan", en: "Expired", statuses: ["EXPIRED", "HALTED"] },
];

export default function RecommendationsPage() {
  const { language } = useLanguage();
  const rec = useRecommendations();
  const [aktif, setAktif] = useState("open");

  const sekme = SEKMELER.find((s) => s.key === aktif) ?? SEKMELER[0];
  const items = useMemo(
    () => (rec.data?.items ?? []).filter((item) => sekme.statuses.includes(item.status)),
    [rec.data, sekme],
  );

  function rozet(statuses: RecommendationStatus[]) {
    const counts = rec.data?.counts ?? {};
    return statuses.reduce((toplam, s) => toplam + (counts[s] ?? 0), 0);
  }

  if (rec.loading && !rec.data) {
    return <LoadingState label={language === "tr" ? "Öneriler yükleniyor" : "Loading recommendations"} />;
  }
  if (!rec.data) {
    return (
      <ErrorState
        message={rec.error ?? (language === "tr" ? "Öneriler alınamadı." : "Could not load recommendations.")}
        onRetry={rec.refetch}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">
          {language === "tr" ? "Otonom Eylemler" : "Autonomous Actions"}
        </h1>
        <p className="mt-1 text-sm app-muted">
          {language === "tr"
            ? "Sistemin portföyün ve risk profiline göre ürettiği öneriler. Onaylamadan hiçbir emir iletilmez."
            : "Recommendations generated from your portfolio and risk profile. No order is placed without your approval."}
        </p>
      </div>

      <div className="flex flex-wrap gap-2 rounded-xl app-card-muted p-1">
        {SEKMELER.map((item) => {
          const adet = rozet(item.statuses);
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => setAktif(item.key)}
              className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
                aktif === item.key ? "bg-[#454466] text-white" : "app-muted"
              }`}
            >
              {language === "tr" ? item.tr : item.en}
              {adet > 0 && <span className="ml-2 text-xs opacity-80">{adet}</span>}
            </button>
          );
        })}
      </div>

      {rec.actionError && <p className="text-sm app-danger">{rec.actionError}</p>}
      {rec.notice && <p className="text-sm app-success">{rec.notice}</p>}

      {items.length === 0 ? (
        <p className="rounded-lg app-card-muted p-4 text-sm app-muted">
          {language === "tr"
            ? "Bu sekmede gösterilecek öneri yok."
            : "There are no recommendations in this tab."}
        </p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((item) => (
            <RecommendationCard
              key={item.id}
              recommendation={item}
              submitting={rec.submitting}
              onApprove={(id, quantity) => void rec.approve(id, quantity)}
              onReject={(id, reason) => void rec.reject(id, reason)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
