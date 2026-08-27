"use client";

import { useEffect } from "react";
import { getDashboardSummary } from "../services/dashboardService";
import { useAsyncData } from "./useAsyncData";

export function useDashboard() {
  const dashboard = useAsyncData(getDashboardSummary, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void dashboard.refresh();
    }, 60_000);

    return () => window.clearInterval(timer);
  }, [dashboard.refresh]);

  return dashboard;
}
