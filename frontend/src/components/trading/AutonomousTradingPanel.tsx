"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLanguage } from "../../contexts/LanguageContext";
import { useRecommendations } from "../../hooks/useRecommendations";
import type { Recommendation, RecommendationStatus } from "../../models/recommendation";
import { ErrorState } from "../feedback/ErrorState";
import { LoadingState } from "../feedback/LoadingState";
import {
  AUTONOMOUS_ACTIONS_READY_EVENT,
  MARKET_PAGE_READY_EVENT,
} from "../layout/transitionEvents";
import { RecommendationCard } from "../recommendations/RecommendationCard";

const TABS: Array<{
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

export function AutonomousTradingPanel({ onReady }: { onReady?: () => void }) {
  const { language } = useLanguage();
  const rec = useRecommendations();
  const [active, setActive] = useState("open");

  useEffect(() => {
    if (rec.loading) return;
    const frame = window.requestAnimationFrame(() => {
      document.documentElement.dataset.autonomousActionsReady = "true";
      document.documentElement.dataset.marketPageReady = "true";
      window.dispatchEvent(new Event(AUTONOMOUS_ACTIONS_READY_EVENT));
      window.dispatchEvent(new Event(MARKET_PAGE_READY_EVENT));
      onReady?.();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [rec.loading, onReady]);

  const locale = language === "tr" ? "tr-TR" : "en-US";
  const money = useMemo(
    () => new Intl.NumberFormat(locale, { style: "currency", currency: "TRY" }),
    [locale],
  );
  const tab = TABS.find((item) => item.key === active) ?? TABS[0];

  const effectiveStatus = useCallback((item: Recommendation): RecommendationStatus => {
    const open = item.status === "PUBLISHED" || item.status === "VIEWED";
    if (open && new Date(item.expires_at).getTime() <= Date.now()) return "EXPIRED";
    return item.status;
  }, []);

  const items = useMemo(
    () => (rec.data?.items ?? []).filter((item) => tab.statuses.includes(effectiveStatus(item))),
    [rec.data, tab, effectiveStatus],
  );

  function badge(statuses: RecommendationStatus[]) {
    return (rec.data?.items ?? []).filter((item) => statuses.includes(effectiveStatus(item))).length;
  }

  if (rec.loading && !rec.data) {
    return (
      <LoadingState
        label={language === "tr" ? "Otonom işlemler yükleniyor" : "Loading autonomous trades"}
      />
    );
  }

  if (!rec.data) {
    return (
      <ErrorState
        message={
          rec.error ??
          (language === "tr" ? "Otonom öneriler alınamadı." : "Could not load recommendations.")
        }
        onRetry={rec.refetch}
      />
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm app-muted">
        {language === "tr"
          ? "Portföyün ve risk profiline göre üretilen öneriler. Onaylamadan hiçbir emir iletilmez."
          : "Recommendations generated from your portfolio and risk profile. No order is placed without your approval."}
      </p>

      {rec.data.account && (
        <div className="grid gap-3 rounded-xl border app-border p-4 sm:grid-cols-3">
          <div>
            <p className="text-xs app-muted">
              {language === "tr" ? "Kullanılabilir likit para" : "Available cash"}
            </p>
            <p className="mt-1 text-lg font-semibold app-heading">
              {money.format(rec.data.account.available_balance)}
            </p>
          </div>
          <div>
            <p className="text-xs app-muted">
              {language === "tr" ? "Emirlerde bloke" : "Reserved for orders"}
            </p>
            <p className="mt-1 text-lg font-semibold app-heading">
              {money.format(rec.data.account.reserved_balance)}
            </p>
          </div>
          <div>
            <p className="text-xs app-muted">{language === "tr" ? "Toplam" : "Total"}</p>
            <p className="mt-1 text-lg font-semibold app-heading">
              {money.format(rec.data.account.available_balance + rec.data.account.reserved_balance)}
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2 rounded-xl app-card-muted p-1">
        {TABS.map((item) => {
          const count = badge(item.statuses);
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => setActive(item.key)}
              className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
                active === item.key ? "bg-[#454466] text-white" : "app-muted"
              }`}
            >
              {language === "tr" ? item.tr : item.en}
              {count > 0 && <span className="ml-2 text-xs opacity-80">{count}</span>}
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
