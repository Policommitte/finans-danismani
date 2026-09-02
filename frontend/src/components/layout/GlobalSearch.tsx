"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { useLanguage } from "../../contexts/LanguageContext";
import type { Asset } from "../../models/market";
import { getMarketAssets } from "../../services/marketService";
import { mainNavItems, utilityNavItems, type NavItem } from "./navItems";
import { requestPageTransition } from "./transitionEvents";

//: Varlik listesi oturum boyunca degismez; paleti her acista yeniden
//: cekmemek icin modul duzeyinde onbellege alinir - MarketTicker'daki
//: `cachedTickerItems` ile ayni desen.
export const ASSET_MODAL_CLOSED_EVENT = "polifin:asset-modal-closed";
let cachedAssets: Asset[] = [];

//: Sorgu bosken gosterilen "hizli baslangic" listesi. Burada olup da varlik
//: evreninde bulunmayan sembol sessizce atlanir, liste degisirse kirilmaz.
const HIZLI_SEMBOLLER = ["THYAO", "GARAN", "BTC", "XAUTRY", "USDTRY"];
const MAX_VARLIK = 8;
const MAX_SAYFA = 4;

const fiyatFormat = new Intl.NumberFormat("tr-TR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

//: Turkce'ye duyarli arama anahtari: "İş" ~ "is", "BIST" ~ "bıst",
//: "Şişecam" ~ "sisecam". Once I/İ/ı tek bir "i"ye indirgenir (noktali/
//: noktasiz ayrimi aramada is gormez), sonra kalan aksanlar NFD ile
//: ayristirilip atilir.
function aramaAnahtari(value: string): string {
  return value
    .replace(/[İIı]/g, "i")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

type Satir = { tur: "varlik"; asset: Asset } | { tur: "sayfa"; item: NavItem };

function AramaIkonu({ className = "" }: { className?: string }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      className={`shrink-0 ${className}`}
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.6-3.6" />
    </svg>
  );
}

export function GlobalSearch({
  onSelectSymbol,
  isAuthenticated,
}: {
  onSelectSymbol: (symbol: string) => void;
  isAuthenticated: boolean;
}) {
  const { language } = useLanguage();
  const tr = language === "tr";

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [assets, setAssets] = useState<Asset[]>(() => cachedAssets);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);

  //: Kart bu paletten mi acildi? Yalnizca o zaman geri donulur - ust
  //: seritteki sembole tiklanarak acilan kart kapaninca palet acilmaz.
  const yenidenAcRef = useRef(false);

  // Varlik listesi YALNIZCA palet ilk kez acildiginda cekilir; kapaliyken
  // ust cubuk fazladan tek bir istek bile atmaz.
  useEffect(() => {
    if (!open || !isAuthenticated || cachedAssets.length > 0) {
      return;
    }
    let active = true;
    setLoading(true);
    getMarketAssets()
      .then((response) => {
        if (active) {
          cachedAssets = response.items;
          setAssets(response.items);
        }
      })
      .catch(() => {
        if (active) setAssets([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [open, isAuthenticated]);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
    }
  }, [open]);

  // Escape her yerden kapatir, Cmd/Ctrl+K her yerden acar. Kisayol ROZETI
  // bilerek gosterilmez - dugme sade kalsin.
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        return;
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((current) => !current);
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  useEffect(() => {
    function handleKartKapandi() {
      if (!yenidenAcRef.current) {
        return;
      }
      yenidenAcRef.current = false;
      setOpen(true);
    }
    window.addEventListener(ASSET_MODAL_CLOSED_EVENT, handleKartKapandi);
    return () => window.removeEventListener(ASSET_MODAL_CLOSED_EVENT, handleKartKapandi);
  }, []);

  const anahtar = aramaAnahtari(query.trim());

  const varliklar = useMemo(() => {
    if (!anahtar) {
      const oncelikli = HIZLI_SEMBOLLER.map((sembol) =>
        assets.find((asset) => asset.symbol === sembol),
      ).filter((asset): asset is Asset => Boolean(asset));
      return (oncelikli.length > 0 ? oncelikli : assets).slice(0, 5);
    }
    // Sembolle BASLAYAN sonuc, adin ortasinda gecen sonuctan once gelir:
    // "th" yazinca THYAO en ustte olsun diye.
    return assets
      .map((asset) => {
        const sembol = aramaAnahtari(asset.symbol);
        const ad = aramaAnahtari(asset.name);
        if (sembol.startsWith(anahtar)) return { asset, puan: 0 };
        if (ad.startsWith(anahtar)) return { asset, puan: 1 };
        if (sembol.includes(anahtar)) return { asset, puan: 2 };
        if (ad.includes(anahtar)) return { asset, puan: 3 };
        return null;
      })
      .filter((e): e is { asset: Asset; puan: number } => e !== null)
      .sort((a, b) => a.puan - b.puan)
      .slice(0, MAX_VARLIK)
      .map((e) => e.asset);
  }, [anahtar, assets]);

  const sayfalar = useMemo(() => {
    const hepsi = [...mainNavItems, ...utilityNavItems];
    if (!anahtar) {
      return hepsi.slice(0, MAX_SAYFA);
    }
    return hepsi
      .filter(
        (item) =>
          aramaAnahtari(item.label.tr).includes(anahtar) ||
          aramaAnahtari(item.label.en).includes(anahtar),
      )
      .slice(0, MAX_SAYFA);
  }, [anahtar]);

  // Klavye gezinmesi tek bir duz liste uzerinde yurur; bolum basliklari
  // yalnizca gorsel gruplama.
  const satirlar = useMemo<Satir[]>(
    () => [
      ...varliklar.map((asset) => ({ tur: "varlik" as const, asset })),
      ...sayfalar.map((item) => ({ tur: "sayfa" as const, item })),
    ],
    [sayfalar, varliklar],
  );

  useEffect(() => {
    setActiveIndex(0);
  }, [query, open]);

  useEffect(() => {
    listRef.current?.querySelector('[data-active="true"]')?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  const kapat = useCallback(() => {
    setOpen(false);
    setQuery("");
  }, []);

  const sec = useCallback(
    (satir: Satir) => {
      if (satir.tur === "varlik") {
        // Sorgu BILEREK temizlenmez: kart kapatilinca palet ayni arama
        // sonuclariyla geri gelir (bkz. ASSET_MODAL_CLOSED_EVENT).
        yenidenAcRef.current = true;
        setOpen(false);
        onSelectSymbol(satir.asset.symbol);
        return;
      }
      kapat();
      requestPageTransition(satir.item.href);
    },
    [kapat, onSelectSymbol],
  );

  function handleInputKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (satirlar.length === 0) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => (current + 1) % satirlar.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => (current - 1 + satirlar.length) % satirlar.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      sec(satirlar[activeIndex] ?? satirlar[0]);
    }
  }

  const satirSinifi = (seciliMi: boolean) =>
    `flex w-full items-center gap-3 px-4 py-2.5 text-left transition ${
      seciliMi ? "bg-[var(--color-surface-muted)]" : ""
    }`;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={tr ? "Ara" : "Search"}
        className="flex h-10 w-10 shrink-0 items-center justify-center gap-2 rounded-md border app-border app-surface app-muted transition hover:opacity-80 md:w-56 md:justify-start md:px-3 lg:w-72 xl:w-80"
      >
        <AramaIkonu />
        <span className="hidden text-sm md:inline">{tr ? "Ara" : "Search"}</span>
      </button>

      {open ? (
        <div
          role="presentation"
          onClick={kapat}
          className="fixed inset-0 z-[90] flex items-start justify-center bg-black/50 px-4 pt-24 backdrop-blur-sm"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={tr ? "Arama" : "Search"}
            onClick={(event) => event.stopPropagation()}
            className="w-full max-w-xl overflow-hidden rounded-2xl border app-card shadow-2xl"
          >
            <div className="flex items-center gap-3 border-b app-border px-4 py-3.5">
              <AramaIkonu className="app-muted" />
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={handleInputKeyDown}
                placeholder={tr ? "Hisse, kripto veya döviz ara..." : "Search stocks, crypto or FX..."}
                className="min-w-0 flex-1 bg-transparent text-base outline-none app-heading placeholder:text-[var(--color-muted)]"
              />
              <button
                type="button"
                onClick={kapat}
                aria-label={tr ? "Aramayı kapat" : "Close search"}
                className="grid h-7 w-7 shrink-0 place-items-center rounded-md border app-border app-surface app-muted transition hover:opacity-80"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  aria-hidden="true"
                >
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>

            <div ref={listRef} className="max-h-[22rem] overflow-y-auto py-2">
              {!isAuthenticated ? (
                <div className="px-4 py-6 text-center text-sm app-muted">
                  {tr
                    ? "Varlık araması ve yapay zeka destekli varlık analizi için giriş yapmalısınız."
                    : "Sign in to search assets and get AI-powered asset analysis."}
                  <Link
                    href="/login"
                    onClick={kapat}
                    className="mt-3 block font-semibold app-primary-text hover:opacity-80"
                  >
                    {tr ? "Giriş Yap" : "Sign in"}
                  </Link>
                </div>
              ) : loading && assets.length === 0 ? (
                <div className="px-4 py-6 text-center text-sm app-muted">
                  {tr ? "Varlıklar yükleniyor…" : "Loading assets…"}
                </div>
              ) : (
                <>
                  {varliklar.length > 0 ? (
                    <>
                      <div className="px-4 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider app-muted">
                        {anahtar
                          ? tr
                            ? "Varlıklar"
                            : "Assets"
                          : tr
                            ? "Hızlı başlangıç"
                            : "Quick start"}
                      </div>
                      {varliklar.map((asset, index) => {
                        const seciliMi = activeIndex === index;
                        const artida = (asset.daily_change_pct ?? 0) >= 0;
                        return (
                          <button
                            key={asset.symbol}
                            type="button"
                            data-active={seciliMi}
                            onMouseMove={() => setActiveIndex(index)}
                            onClick={() => sec({ tur: "varlik", asset })}
                            className={satirSinifi(seciliMi)}
                          >
                            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md app-primary-soft text-[11px] font-bold">
                              {asset.symbol.slice(0, 2).toUpperCase()}
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-sm font-semibold app-heading">
                                {asset.symbol}
                              </span>
                              <span className="block truncate text-xs app-muted">{asset.name}</span>
                            </span>
                            <span className="shrink-0 text-right">
                              <span className="block text-sm font-semibold app-heading">
                                {fiyatFormat.format(asset.current_price)} {asset.currency}
                              </span>
                              <span
                                className={`block text-xs font-semibold ${artida ? "app-success" : "app-danger"}`}
                              >
                                {asset.daily_change_pct == null
                                  ? "—"
                                  : `${artida ? "+" : ""}${asset.daily_change_pct.toFixed(2)}%`}
                              </span>
                            </span>
                          </button>
                        );
                      })}
                    </>
                  ) : null}

                  {sayfalar.length > 0 ? (
                    <>
                      <div className="px-4 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wider app-muted">
                        {tr ? "Sayfalar" : "Navigation"}
                      </div>
                      {sayfalar.map((item, index) => {
                        const satirIndex = varliklar.length + index;
                        const seciliMi = activeIndex === satirIndex;
                        return (
                          <button
                            key={item.key}
                            type="button"
                            data-active={seciliMi}
                            onMouseMove={() => setActiveIndex(satirIndex)}
                            onClick={() => sec({ tur: "sayfa", item })}
                            className={satirSinifi(seciliMi)}
                          >
                            <span
                              className="grid h-8 w-8 shrink-0 place-items-center rounded-md border app-border app-muted"
                              aria-hidden="true"
                            >
                              ↗
                            </span>
                            <span className="flex-1 truncate text-sm font-semibold app-heading">
                              {item.label[language]}
                            </span>
                          </button>
                        );
                      })}
                    </>
                  ) : null}

                  {satirlar.length === 0 ? (
                    <div className="px-4 py-6 text-center text-sm app-muted">
                      {tr ? `"${query}" için sonuç yok.` : `No results for "${query}".`}
                    </div>
                  ) : null}
                </>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}