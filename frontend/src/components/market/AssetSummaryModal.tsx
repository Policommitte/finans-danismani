"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Asset, HistoryResponse, OhlcResponse, TechnicalResponse } from "../../models/market";
import {
  getMarketAssets,
  getMarketHistory,
  getMarketOhlc,
  getMarketTechnical,
  streamQuickAnalysis,
} from "../../services/marketService";
import { CandlestickChart } from "./CandlestickChart";
import { TechnicalDetailView } from "./TechnicalDetailView";
import { TechnicalSummaryStrip } from "./TechnicalSummaryStrip";

/**
 * Varlik karti icin TEK SEFERLIK "Polifin AI Analizi" metni.
 *
 * ⚠️ KASITLI OLARAK `ChatContext` KULLANMAZ (bkz. `marketService.streamQuickAnalysis`
 * docstring'i). Onceki halde bu analiz `useChat().sendMessage(...)` ile
 * PAYLASIMLI sohbet baglamina gonderiliyordu - kullanici widget'i actiginda
 * hic yazmadigi "X hakkinda kisa bir yatirim analizi yap" sorusunu kendi
 * sohbet gecmisinde goruyordu. Bu hook TAMAMEN yerel state tutar; ne
 * widget'a ne kalici sohbet gecmisine hicbir sey sizmaz.
 */
function useQuickAnalysis(symbol: string, isAuthenticated: boolean) {
  const [content, setContent] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    // ⚠️ BURADA "sadece bir kez sor" REF'I KULLANILMAZ. React StrictMode
    // (frontend/next.config.js: reactStrictMode=true) gelistirmede HER
    // effect'i mount->cleanup->mount olarak IKI KEZ calistirir - bir ref
    // koruması ikinci calistirmayi engellerdi ama asagidaki cleanup zaten
    // ILK istegi abort() ile iptal etmisti; sonuc TAMAMEN cevapsiz kalan
    // bir istek olurdu (canli olculdu - kutu sonsuza dek "Analiz
    // hazirlaniyor..." de takili kaliyordu). AbortController + cleanup tek
    // basina yeterli: her effect calistirmasi ONCEKI istegi iptal edip
    // KENDI TEMIZ istegini baslatir, StrictMode'un ikinci calistirmasi da
    // dahil - sonda hep TEK ve TAMAMLANAN bir istek kalir.
    setContent("");
    setStatus(null);
    setError(null);
    setIsStreaming(true);

    const controller = new AbortController();
    streamQuickAnalysis(
      symbol,
      (event) => {
        if (event.type === "status") setStatus(event.message);
        if (event.type === "token") setContent((current) => current + event.content);
        if (event.type === "error") setError(event.message);
        if (event.type === "done") setIsStreaming(false);
      },
      controller.signal,
    )
      .catch((exc) => {
        // Modal kapanip AbortController.abort() cagrildiginda `fetch` bu
        // istisnayla reddeder - bu bir HATA DEGIL, kullanicinin kendi
        // eylemi. Sessizce yutulur.
        if (exc instanceof DOMException && exc.name === "AbortError") {
          return;
        }
        setError("Analiz şu anda alınamadı.");
      })
      .finally(() => setIsStreaming(false));

    return () => controller.abort();
  }, [symbol, isAuthenticated]);

  return { content, status, error, isStreaming };
}

const RANGE_TABS: { label: string; days: number }[] = [
  { label: "1G", days: 1 },
  { label: "1H", days: 7 },
  { label: "1A", days: 30 },
  { label: "3A", days: 90 },
  { label: "1Y", days: 365 },
];

const ASSET_CLASS_LABELS: Record<string, string> = {
  STOCK: "Hisse",
  USA_STOCK: "ABD hissesi",
  EU_STOCK: "Avrupa hissesi",
  CRYPTO: "Kripto",
  FOREX: "Döviz",
  GOLD: "Altın",
  BOND: "Tahvil",
  FUND: "Fon",
};

const priceFormat = new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function assetClassLabel(assetClass: string): string {
  return ASSET_CLASS_LABELS[assetClass.toUpperCase()] ?? assetClass;
}

function GuestAccessPrompt({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const features = [
    "Çizgi ve mum grafikleri",
    "Polifin AI analizi",
    "İşlem ve alarm araçları",
  ];

  return (
    <>
      <div className="rounded-2xl border app-border bg-[var(--color-surface-muted)] px-5 py-6 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-primary-soft)] text-xl text-[var(--color-primary)]">
          <span aria-hidden="true">🔒</span>
        </div>
        <div className="mt-4 text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-primary)]">
          Üyelere özel
        </div>
        <h2 className="mt-2 text-xl font-bold app-heading">
          {symbol} grafikleri ve AI analizi için giriş yapın
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm leading-6 app-muted">
          Ayrıntılı fiyat geçmişini, çizgi ve mum grafiklerini, Polifin AI yorumunu,
          işlem araçlarını ve alarm seçeneklerini kullanmak için hesabınıza giriş yapın.
        </p>

        <div className="mt-5 grid gap-2 text-left sm:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature}
              className="rounded-xl border app-border app-surface px-3 py-3 text-xs font-semibold app-heading"
            >
              <span className="mr-2 text-[var(--color-primary)]" aria-hidden="true">
                ✓
              </span>
              {feature}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5 flex gap-3">
        <Link
          href="/login?next=/market"
          onClick={onClose}
          className="flex-1 rounded-xl app-primary px-4 py-2.5 text-center text-sm font-semibold transition hover:opacity-90"
        >
          Giriş Yap
        </Link>
        <button
          type="button"
          onClick={onClose}
          className="flex-1 rounded-xl border app-border app-surface px-4 py-2.5 text-sm font-semibold app-muted transition hover:opacity-80"
        >
          Şimdilik Kapat
        </button>
      </div>
    </>
  );
}

export function AssetSummaryModal({
  symbol,
  isAuthenticated,
  onClose,
  onNavigate,
}: {
  symbol: string;
  isAuthenticated: boolean;
  /** Kartin KAPATILMASI: carpi, arka plan tiklamasi, "Şimdilik Kapat". */
  onClose: () => void;
  //: Kart icinden BASKA BIR SAYFAYA gidilmesi. Kapatmadan ayri tutulur:
  //: aramadan acilan kart kapaninca arama paleti geri gelir, ama
  //: "İşlem Ekranına Git" ile gidilirken gelMEMELIdir. Verilmezse
  //: `onClose` gibi davranir.
  onNavigate?: () => void;
}) {
  const closeAndNavigate = onNavigate ?? onClose;
  const [asset, setAsset] = useState<Asset | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [rangeDays, setRangeDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [chartMode, setChartMode] = useState<"line" | "candle">("line");
  const [ohlc, setOhlc] = useState<OhlcResponse | null>(null);
  const [ohlcLoading, setOhlcLoading] = useState(false);
  const analysis = useQuickAnalysis(symbol, isAuthenticated);
  const [technical, setTechnical] = useState<TechnicalResponse | null>(null);
  const [technicalLoading, setTechnicalLoading] = useState(false);
  //: Gosterge tablolari modali uzatmasin diye ayri bir gorunumde durur.
  const [view, setView] = useState<"summary" | "technical">("summary");
  const [aiExpanded, setAiExpanded] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      setAsset(null);
      return;
    }

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
  }, [symbol, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      setHistory(null);
      setLoading(false);
      return;
    }

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
  }, [symbol, rangeDays, isAuthenticated]);

  useEffect(() => {
    // Mum verisi sadece "Mum" secildiginde cekilir - Yahoo'ya gereksiz
    // istek atmamak icin (bkz. app/market/yahoo.py OHLC onbellegi).
    if (!isAuthenticated || chartMode !== "candle") {
      return;
    }
    let active = true;
    setOhlcLoading(true);
    getMarketOhlc(symbol, rangeDays)
      .then((response) => {
        if (active) setOhlc(response);
      })
      .catch(() => {
        if (active) setOhlc(null);
      })
      .finally(() => {
        if (active) setOhlcLoading(false);
      });
    return () => {
      active = false;
    };
  }, [symbol, rangeDays, chartMode, isAuthenticated]);

  useEffect(() => {
    // Teknik analiz haberden BAGIMSIZ calisir: grafik sekmesinden etkilenmez,
    // sabit gunluk mumlarla hesaplanir (bkz. app/services/technical_analysis.py).
    if (!isAuthenticated) {
      setTechnical(null);
      return;
    }

    let active = true;
    setView("summary");
    setAiExpanded(false);
    setTechnicalLoading(true);
    getMarketTechnical(symbol)
      .then((response) => {
        if (active) setTechnical(response);
      })
      .catch(() => {
        if (active) setTechnical(null);
      })
      .finally(() => {
        if (active) setTechnicalLoading(false);
      });
    return () => {
      active = false;
    };
  }, [symbol, isAuthenticated]);

  const historyTrendPositive =
    history && history.points.length >= 2
      ? history.points[history.points.length - 1].price >= history.points[0].price
      : null;
  const changeIsPositive = asset?.daily_change_pct != null ? asset.daily_change_pct >= 0 : historyTrendPositive;
  const lineColor =
    changeIsPositive == null ? "var(--color-primary)" : changeIsPositive ? "var(--color-success)" : "var(--color-danger)";
  const changeClass = changeIsPositive ? "app-success" : "app-danger";
  //: AI Analizi kutusu: yukselis/dususe gore --color-brand-teal / --color-danger
  //: (marka yesili / kirmizi, ikisi de tema-duyarli); yon belirsizse notr mavi.
  const aiBoxAccent =
    changeIsPositive == null ? "var(--color-primary)" : changeIsPositive ? "var(--color-brand-teal)" : "var(--color-danger)";

  const sparklinePoints = (history?.points ?? []).slice(-20);

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-black/40 px-4 pb-4 pt-24"
      onClick={onClose}
    >
      <div
        className="max-h-[calc(100dvh-7rem)] w-full max-w-lg overflow-y-auto rounded-2xl border app-card shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b app-border app-card px-5 py-4">
          <div className="flex items-center gap-3">
            <div
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm font-bold"
              style={{ background: `color-mix(in srgb, ${lineColor} 18%, var(--color-surface))`, color: lineColor }}
            >
              {symbol.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="text-lg font-bold app-heading">{asset?.name ?? symbol}</div>
              <div className="text-xs app-muted">
                {isAuthenticated ? (
                  <>
                    {symbol}
                    {asset ? ` • ${assetClassLabel(asset.asset_class)}` : ""}
                  </>
                ) : (
                  "Detaylı piyasa görünümü"
                )}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Kapat"
            className="rounded px-2 py-1 text-xl leading-none app-muted hover:opacity-80"
          >
            ×
          </button>
        </div>

        <div className="px-5 py-4">
          {!isAuthenticated ? (
            <GuestAccessPrompt symbol={symbol} onClose={onClose} />
          ) : view === "technical" && technical ? (
            <TechnicalDetailView data={technical} onBack={() => setView("summary")} />
          ) : (
            <>
              <div className="flex items-start justify-between gap-3">
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
                {sparklinePoints.length >= 2 && (
                  <div className="h-12 w-24 shrink-0">
                    <ResponsiveContainer>
                      <LineChart data={sparklinePoints}>
                        <Line type="monotone" dataKey="price" stroke={lineColor} strokeWidth={2} dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
                <div className="inline-flex gap-1 rounded-full border app-border bg-[var(--color-surface-muted)] p-1">
                  {RANGE_TABS.map((tab) => (
                    <button
                      key={tab.label}
                      type="button"
                      onClick={() => setRangeDays(tab.days)}
                      className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${rangeDays === tab.days ? "app-primary" : "app-muted hover:opacity-80"
                        }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
                <div className="inline-flex gap-1 rounded-full border app-border bg-[var(--color-surface-muted)] p-1">
                  {(
                    [
                      { mode: "line" as const, label: "Çizgi" },
                      { mode: "candle" as const, label: "Mum" },
                    ]
                  ).map((option) => (
                    <button
                      key={option.mode}
                      type="button"
                      onClick={() => setChartMode(option.mode)}
                      className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${chartMode === option.mode ? "app-primary" : "app-muted hover:opacity-80"
                        }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-4 h-56">
                {chartMode === "candle" ? (
                  ohlcLoading ? (
                    <div className="flex h-full items-center justify-center text-sm app-muted">Mum grafiği yükleniyor…</div>
                  ) : ohlc && ohlc.candles.length > 0 ? (
                    <CandlestickChart candles={ohlc.candles} />
                  ) : (
                    <div className="flex h-full items-center justify-center px-4 text-center text-sm app-muted">
                      Bu varlık için mum grafiği verisi yok - çizgi grafiğe geçebilirsiniz.
                    </div>
                  )
                ) : loading ? (
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
                      <Line type="monotone" dataKey="price" stroke={lineColor} strokeWidth={2} dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center justify-center text-sm app-muted">Bu aralık için veri yok.</div>
                )}
              </div>

              <div
                className="mt-5 rounded-xl border p-3.5 text-sm"
                style={{
                  background: `color-mix(in srgb, ${aiBoxAccent} 12%, var(--color-surface))`,
                  borderColor: `color-mix(in srgb, ${aiBoxAccent} 40%, transparent)`,
                  boxShadow: `0 0 0 1px color-mix(in srgb, ${aiBoxAccent} 15%, transparent), 0 6px 18px -6px color-mix(in srgb, ${aiBoxAccent} 40%, transparent)`,
                }}
              >
                <div className="mb-1.5 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide" style={{ color: aiBoxAccent }}>
                  <span>Polifin AI Analizi</span>
                  {analysis.isStreaming && <span className="app-muted normal-case">{analysis.status ?? "…"}</span>}
                </div>
                <p
                  className={`whitespace-pre-wrap leading-relaxed app-heading ${aiExpanded ? "" : "line-clamp-3"
                    }`}
                >
                  {analysis.error ? analysis.error : analysis.content || "Analiz hazırlanıyor…"}
                </p>
                {!analysis.error && analysis.content.length > 160 && (
                  <button
                    type="button"
                    onClick={() => setAiExpanded((open) => !open)}
                    className="mt-1 text-xs font-semibold app-muted underline transition hover:opacity-80"
                  >
                    {aiExpanded ? "Daha az göster" : "Devamını gör"}
                  </button>
                )}
              </div>

              <TechnicalSummaryStrip
                data={technical}
                loading={technicalLoading}
                onShowDetail={() => setView("technical")}
              />

              <div className="mt-5 flex gap-3">
                <Link
                  href="/market"
                  onClick={closeAndNavigate}
                  className="flex-1 rounded-xl app-primary px-4 py-2.5 text-center text-sm font-semibold transition hover:opacity-90"
                >
                  İşlem Ekranına Git
                </Link>
                <button
                  type="button"
                  className="flex-1 rounded-xl border app-border app-surface px-4 py-2.5 text-sm font-semibold app-muted transition hover:opacity-80"
                  onClick={() => window.alert("Alarm kurma özelliği yakında eklenecek.")}
                >
                  Alarm Kur
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
