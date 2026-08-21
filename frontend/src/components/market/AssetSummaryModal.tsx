"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useChatStream } from "../../hooks/useChatStream";
import type { Asset, HistoryResponse } from "../../models/market";
import { getMarketAssets, getMarketHistory } from "../../services/marketService";

const RANGE_TABS: { label: string; days: number }[] = [
  { label: "1G", days: 1 },
  { label: "1H", days: 7 },
  { label: "1A", days: 30 },
  { label: "3A", days: 90 },
  { label: "1Y", days: 365 },
];

const priceFormat = new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function AssetSummaryModal({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const [asset, setAsset] = useState<Asset | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [rangeDays, setRangeDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const chat = useChatStream();
  const askedRef = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    getMarketAssets()
      .then((response) => {
        if (active) {
          setAsset(response.items.find((item) => item.symbol === symbol) ?? null);
        }
      })
      .catch(() => {
        if (active) setAsset(null);
      });
    return () => {
      active = false;
    };
  }, [symbol]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getMarketHistory(symbol, rangeDays)
      .then((response) => {
        if (active) setHistory(response);
      })
      .catch(() => {
        if (active) setHistory(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [symbol, rangeDays]);

  useEffect(() => {
    if (askedRef.current === symbol) {
      return;
    }
    askedRef.current = symbol;
    chat.sendMessage(`${symbol} hakkında kısa bir yatırım analizi yap.`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  const historyTrendPositive =
    history && history.points.length >= 2
      ? history.points[history.points.length - 1].price >= history.points[0].price
      : null;
  const changeIsPositive = asset?.daily_change_pct != null ? asset.daily_change_pct >= 0 : historyTrendPositive;
  const lineColor =
    changeIsPositive == null ? "var(--color-primary)" : changeIsPositive ? "var(--color-success)" : "var(--color-danger)";
  const changeClass = changeIsPositive ? "app-success" : "app-danger";
  const lastAssistantMessage = [...chat.messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border app-card shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b app-border px-5 py-4">
          <div>
            <div className="text-lg font-bold app-heading">{symbol}</div>
            <div className="text-sm app-muted">{asset?.name ?? "Varlık Özeti"}</div>
          </div>
          <button type="button" onClick={onClose} className="rounded px-2 py-1 text-xl leading-none app-muted hover:opacity-80">
            ×
          </button>
        </div>

        <div className="px-5 py-4">
          <div className="flex items-end gap-3">
            <div className="text-3xl font-bold app-heading">
              {asset ? `${priceFormat.format(asset.current_price)} ${asset.currency}` : "—"}
            </div>
            {asset?.daily_change_pct != null && (
              <span className={`mb-1 inline-flex items-center gap-1 text-sm font-semibold ${changeClass}`}>
                {changeIsPositive ? "▲" : "▼"} %{priceFormat.format(Math.abs(asset.daily_change_pct))}
              </span>
            )}
          </div>

          <div className="mt-4 inline-flex gap-1 rounded-lg border app-border bg-[var(--color-surface-muted)] p-1">
            {RANGE_TABS.map((tab) => (
              <button
                key={tab.label}
                type="button"
                onClick={() => setRangeDays(tab.days)}
                className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                  rangeDays === tab.days ? "app-primary" : "app-muted hover:opacity-80"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="mt-4 h-56">
            {loading ? (
              <div className="flex h-full items-center justify-center text-sm app-muted">Grafik yükleniyor…</div>
            ) : history && history.points.length > 0 ? (
              <ResponsiveContainer>
                <LineChart data={history.points}>
                  <CartesianGrid stroke="var(--color-chart-grid)" strokeDasharray="3 3" />
                  <XAxis dataKey="ts" tick={{ fontSize: 10, fill: "var(--color-muted)" }} minTickGap={30} />
                  <YAxis tick={{ fontSize: 10, fill: "var(--color-muted)" }} domain={["auto", "auto"]} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-surface)",
                      borderColor: "var(--color-border)",
                      color: "var(--color-text)",
                    }}
                  />
                  <Line type="monotone" dataKey="price" stroke={lineColor} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm app-muted">Bu aralık için veri yok.</div>
            )}
          </div>

          <div className="mt-5 rounded-lg app-primary-soft p-3.5 text-sm">
            <div className="mb-1.5 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
              <span>Polifin AI Analizi</span>
              {chat.isStreaming && <span className="app-muted normal-case">{chat.status ?? "…"}</span>}
            </div>
            <p className="whitespace-pre-wrap leading-relaxed">
              {chat.error ? chat.error : lastAssistantMessage?.content || "Analiz hazırlanıyor…"}
            </p>
          </div>

          <div className="mt-5 flex gap-3">
            <Link
              href="/market"
              onClick={onClose}
              className="flex-1 rounded-lg app-primary px-4 py-2.5 text-center text-sm font-semibold transition hover:opacity-90"
            >
              İşlem Ekranına Git
            </Link>
            <button
              type="button"
              className="flex-1 rounded-lg border app-border app-surface px-4 py-2.5 text-sm font-semibold app-muted transition hover:opacity-80"
              onClick={() => window.alert("Alarm kurma özelliği yakında eklenecek.")}
            >
              Alarm Kur
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
