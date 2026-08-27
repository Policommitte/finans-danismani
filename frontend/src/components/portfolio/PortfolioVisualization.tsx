"use client";

import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  LabelList,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useLanguage } from "../../contexts/LanguageContext";
import type { Holding, PortfolioPerformancePoint } from "../../models/portfolio";
import Card from "../ui/Card";

type ViewMode = "line" | "pie";

const colors = [
  "var(--color-primary)",
  "var(--color-success)",
  "var(--color-chart-yellow)",
  "var(--color-danger)",
  "var(--color-chart-purple)",
  "var(--color-chart-cyan)",
];

function formatTime(value: string, language: "tr" | "en"): string {
  return new Intl.DateTimeFormat(language === "tr" ? "tr-TR" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function ViewToggle({
  mode,
  onChange,
  language,
}: {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
  language: "tr" | "en";
}) {
  return (
    <div
      className="flex shrink-0 rounded-md border app-border app-card-muted p-1"
      role="group"
      aria-label={language === "tr" ? "Grafik görünümü" : "Chart view"}
    >
      <button
        type="button"
        aria-pressed={mode === "line"}
        onClick={() => onChange("line")}
        className={`rounded-md px-3 py-2 text-xs font-semibold transition ${
          mode === "line" ? "bg-[var(--color-panel-dark)] text-white shadow-sm" : "app-muted hover:text-[var(--color-heading)]"
        }`}
      >
        {language === "tr" ? "Çizgi" : "Line"}
      </button>
      <button
        type="button"
        aria-pressed={mode === "pie"}
        onClick={() => onChange("pie")}
        className={`rounded-md px-3 py-2 text-xs font-semibold transition ${
          mode === "pie" ? "bg-[var(--color-panel-dark)] text-white shadow-sm" : "app-muted hover:text-[var(--color-heading)]"
        }`}
      >
        {language === "tr" ? "Pasta (Daire)" : "Pie"}
      </button>
    </div>
  );
}

export function PortfolioVisualization({
  holdings,
  performancePoints,
  performanceLoading = false,
  performanceError = null,
}: {
  holdings: Holding[];
  performancePoints: PortfolioPerformancePoint[];
  performanceLoading?: boolean;
  performanceError?: string | null;
}) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const currency = new Intl.NumberFormat(locale, { style: "currency", currency: "TRY", maximumFractionDigits: 0 });
  const compactCurrency = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "TRY",
    notation: "compact",
    maximumFractionDigits: 1,
  });
  const [mode, setMode] = useState<ViewMode>("pie");
  const chartPoints = useMemo(
    () => performancePoints.filter((point) => !Number.isNaN(new Date(point.ts).getTime())),
    [performancePoints],
  );
  const totalValue = holdings.reduce((sum, item) => sum + item.market_value_try, 0);
  const pieData = holdings
    .filter((item) => item.market_value_try > 0)
    .map((item) => ({
      symbol: item.symbol,
      value: item.market_value_try,
      percent: totalValue > 0 ? (item.market_value_try / totalValue) * 100 : 0,
    }));

  const first = chartPoints[0]?.total_value_try ?? 0;
  const current = chartPoints.at(-1)?.total_value_try ?? totalValue;
  const change = current - first;
  const changePct = first > 0 ? (change / first) * 100 : 0;
  const positive = change >= 0;
  const performanceValues = chartPoints.map((point) => point.total_value_try);
  const minimum = performanceValues.length > 0 ? Math.min(...performanceValues) : current;
  const maximum = performanceValues.length > 0 ? Math.max(...performanceValues) : current;

  return (
    <Card className="h-full">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold app-heading">
            {mode === "line"
              ? language === "tr" ? "Portföy performansı" : "Portfolio performance"
              : language === "tr" ? "Varlık dağılımı" : "Asset allocation"}
          </h2>
          <p className="mt-1 text-xs app-muted">
            {mode === "line"
              ? language === "tr" ? "Bugün · TL bazlı" : "Today · TRY based"
              : language === "tr" ? "Her varlığın toplam portföy değerindeki payı" : "Each asset's share of the total portfolio value"}
          </p>
        </div>
        <ViewToggle mode={mode} onChange={setMode} language={language} />
      </div>

      <div className="mt-3 h-[420px] overflow-y-auto pr-1">
        {mode === "pie" ? (
          <>
            <div className="mt-4 h-72">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={pieData} dataKey="percent" nameKey="symbol" innerRadius={62} outerRadius={104} cornerRadius={9} paddingAngle={4} stroke="none">
                    {pieData.map((item, index) => <Cell key={item.symbol} fill={colors[index % colors.length]} />)}
                    <LabelList dataKey="percent" position="center" fill="#ffffff" stroke="none" fontSize={12} fontWeight={700} formatter={(value: number) => `%${Number(value).toFixed(0)}`} />
                  </Pie>
                  <Tooltip
                    formatter={(value, name) => [`%${Number(value).toFixed(2)}`, String(name)]}
                    contentStyle={{ background: "var(--color-surface)", borderColor: "var(--color-border)", borderRadius: "6px", color: "var(--color-text)", boxShadow: "0 10px 30px rgb(0 0 0 / 0.12)" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 grid gap-2.5 text-sm">
              {pieData.map((item, index) => (
                <div key={item.symbol} className="flex items-center justify-between">
                  <span className="flex items-center gap-2 app-muted">
                    <span className="h-2.5 w-2.5 rounded-[3px]" style={{ backgroundColor: colors[index % colors.length] }} />
                    {item.symbol}
                  </span>
                  <span className="font-semibold app-heading">%{item.percent.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </>
        ) : performanceLoading ? (
          <div className="grid min-h-[356px] place-items-center text-sm app-muted">
            {language === "tr" ? "Performans verisi yükleniyor..." : "Loading performance data..."}
          </div>
        ) : performanceError ? (
          <div className="grid min-h-[356px] place-items-center px-6 text-center text-sm app-danger">
            {language === "tr" ? "Performans verisi şu anda alınamıyor." : "Performance data is currently unavailable."}
          </div>
        ) : chartPoints.length === 0 ? (
          <div className="grid min-h-[356px] place-items-center text-center text-sm app-muted">
            {language === "tr" ? "Bugün için henüz yeterli gerçek fiyat geçmişi oluşmadı." : "There is not enough real price history for today yet."}
          </div>
        ) : (
          <>
            <div className="mt-3 flex items-end justify-between gap-4">
              <div className="text-2xl font-semibold app-heading">{currency.format(current)}</div>
              <span className={`text-sm font-semibold ${positive ? "app-success" : "app-danger"}`}>
                {positive ? "▲" : "▼"} %{Math.abs(changePct).toFixed(2)}
              </span>
            </div>
            <div className="mt-3 h-72">
              <ResponsiveContainer>
                <AreaChart data={chartPoints} margin={{ top: 10, right: 12, left: 4, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--color-chart-grid)" strokeDasharray="3 3" />
                  <XAxis dataKey="ts" tickFormatter={(value) => formatTime(value, language)} axisLine={false} tickLine={false} minTickGap={36} tick={{ fill: "var(--color-muted)", fontSize: 12 }} />
                  <YAxis width={72} domain={["dataMin", "dataMax"]} tickFormatter={(value) => compactCurrency.format(Number(value))} axisLine={false} tickLine={false} tick={{ fill: "var(--color-muted)", fontSize: 12 }} />
                  <Tooltip
                    labelFormatter={(label) => formatTime(String(label), language)}
                    formatter={(value) => [currency.format(Number(value)), language === "tr" ? "Portföy" : "Portfolio"]}
                    contentStyle={{ background: "var(--color-panel-dark)", border: "1px solid var(--color-border)", borderRadius: "6px", color: "var(--color-market-text)", boxShadow: "0 12px 30px rgb(0 0 0 / 0.18)" }}
                    itemStyle={{ color: "var(--color-market-text)" }}
                    labelStyle={{ color: "var(--color-on-primary-muted)" }}
                  />
                  <Area type="monotone" dataKey="total_value_try" stroke={positive ? "var(--color-success)" : "var(--color-danger)"} strokeWidth={3} fill={positive ? "var(--color-success)" : "var(--color-danger)"} fillOpacity={0.14} activeDot={{ r: 5, strokeWidth: 2, fill: "var(--color-surface)" }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-4 border-t app-border pt-4 text-sm">
              <div>
                <div className="text-xs font-semibold app-muted">{language === "tr" ? "EN YÜKSEK" : "HIGHEST"}</div>
                <div className="mt-1 font-semibold app-heading">{currency.format(maximum)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold app-muted">{language === "tr" ? "EN DÜŞÜK" : "LOWEST"}</div>
                <div className="mt-1 font-semibold app-heading">{currency.format(minimum)}</div>
              </div>
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
