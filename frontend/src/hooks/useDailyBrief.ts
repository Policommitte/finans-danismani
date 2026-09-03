"use client";

import { useCallback, useEffect, useState } from "react";
import type { AppLanguage } from "../contexts/LanguageContext";
import type { Holding, PortfolioSummary } from "../models/portfolio";
import type { PaperOrder, TradingAccount } from "../models/trading";
import { getPortfolioHoldings, getPortfolioSummary } from "../services/portfolioService";
import { getPaperOrders, getTradingAccount } from "../services/tradingService";

export type DailyBriefTone = "positive" | "negative" | "flat";

export type DailyBrief = {
  tone: DailyBriefTone;
  /** Baloncukta gorunen TEK cumlelik ozet - gunun yonunu soyler, detay vermez. */
  teaser: string;
  /** Baloncugun altindaki davet satiri. */
  actionLabel: string;
  /** Kullanici balonunda gorunecek kisa metin (gomulu istemin ilk satiri). */
  displayText: string;
  /** Sohbet acilinca arka planda gonderilen gomulu istem. */
  prompt: string;
};

//: Gunluk degisim bu esigin altindaysa "yatay" sayilir. Yuzde iki hanede
//: gosterildigi icin daha kucuk hareketler baloncukta "%0,00 artida" gibi
//: anlamsiz bir cumleye donusurdu.
const FLAT_THRESHOLD_PCT = 0.05;

//: Baloncuk sayfa acilir acilmaz degil, kisa bir gecikmeyle gelir: sayfa
//: gecis perdesi kapanmadan cikarsa goz kacirir, ustelik asistanin kendi
//: soz almasi gibi durmaz.
const SHOW_DELAY_MS = 1400;

//: Isteme yazilan sembol sayisi. Portfoyun tamami yazilirsa hem baglam
//: sisiyor hem de piyasa ajani onemsiz pozisyonlar icin de haber ariyor.
const PROMPT_SYMBOL_COUNT = 5;

//: Isteme ayrintisiyla yazilan "gunun hareketlisi" pozisyon sayisi -
//: backend'in varlik karti sinirlyla (`KART_SEMBOL_SINIRI`) ayni.
const TOP_MOVER_COUNT = 3;

//: ⚠️ GECICI - DEBUGGING ICIN ACIK. Davet normalde kullanici basina GUNDE
//: BIR KEZ gosterilir; bu bayrak acikken her giriste (ve her sayfa
//: yenilemesinde) yeniden cikar, "gorulduye" de yazilmaz. Normal davranisa
//: donmek icin TEK YAPILACAK: `false`.
const DEBUG_ALWAYS_SHOW: boolean = true;

const STORAGE_PREFIX = "polifin-daily-brief-v1";

function storageKey(userId: number): string {
  return `${STORAGE_PREFIX}:${userId}`;
}

/** Yerel takvim gunu (YYYY-AA-GG). */
function dateKey(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function todayKey(): string {
  return dateKey(new Date());
}

function wasShownToday(userId: number): boolean {
  try {
    return window.localStorage.getItem(storageKey(userId)) === todayKey();
  } catch {
    // Depolama kapaliysa davet her giriste gosterilir - kayip senaryo bu
    // degil, hic gosterilmemesi olurdu.
    return false;
  }
}

function markShownToday(userId: number): void {
  try {
    window.localStorage.setItem(storageKey(userId), todayKey());
  } catch {
    // Yazilamamasi akisi bozmaz.
  }
}

function formatPct(value: number, language: AppLanguage): string {
  return new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(value));
}

/** Isaretli yuzde - "%" mutlak degeri bicimledigi icin isaret ONE alinir. */
function formatSignedPct(value: number, language: AppLanguage): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}%${formatPct(value, language)}`;
}

function formatTry(value: number, language: AppLanguage): string {
  return new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatSignedTry(value: number, language: AppLanguage): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${formatTry(Math.abs(value), language)}`;
}

function resolveTone(summary: PortfolioSummary): DailyBriefTone {
  const changePct = summary.daily_change_pct;
  if (changePct != null) {
    if (changePct > FLAT_THRESHOLD_PCT) {
      return "positive";
    }
    if (changePct < -FLAT_THRESHOLD_PCT) {
      return "negative";
    }
    return "flat";
  }

  // Yuzde hesaplanamadigi durumda (ornegin dunku kapanis degeri yoksa) TL
  // tutarinin isareti yon icin yeterli.
  if (summary.daily_change_try > 0) {
    return "positive";
  }
  return summary.daily_change_try < 0 ? "negative" : "flat";
}

function buildTeaser(
  summary: PortfolioSummary,
  tone: DailyBriefTone,
  language: AppLanguage,
): string {
  if (tone === "flat") {
    return language === "tr"
      ? "Portföyün bugün yatay seyrediyor."
      : "Your portfolio is flat today.";
  }

  const isUp = tone === "positive";

  if (summary.daily_change_pct == null) {
    const amount = formatSignedTry(summary.daily_change_try, language);
    return language === "tr"
      ? `Portföyün bugün ${amount} ${isUp ? "kazandı" : "kaybetti"}.`
      : `Your portfolio is ${amount} today.`;
  }

  const pct = formatPct(summary.daily_change_pct, language);
  return language === "tr"
    ? `Portföyün bugün %${pct} ${isUp ? "artıda" : "ekside"}.`
    : `Your portfolio is ${pct}% ${isUp ? "up" : "down"} today.`;
}

/** Degeri en buyuk pozisyonlarin sembolleri (istemde kullanilir). */
function topSymbols(holdings: Holding[]): string[] {
  return [...holdings]
    .sort((a, b) => b.market_value_try - a.market_value_try)
    .slice(0, PROMPT_SYMBOL_COUNT)
    .map((holding) => holding.symbol);
}

/** Bugun mutlak yuzde olarak en cok degisen pozisyonlar. */
function topMovers(holdings: Holding[]): Holding[] {
  return holdings
    .filter((holding) => holding.daily_change_pct != null)
    .sort((a, b) => Math.abs(b.daily_change_pct ?? 0) - Math.abs(a.daily_change_pct ?? 0))
    .slice(0, TOP_MOVER_COUNT);
}

/**
 * Bugun gerceklesen emirlerin nakde net etkisi.
 *
 * Nakit bakiyenin GECMISI yok (tek bir anlik deger doner), bu yuzden
 * "likit paradaki degisim" bugunku dolumlardan turetilir: satis nakdi
 * artirir, alis azaltir, komisyon her iki yonde de dusulur.
 */
function todaysCashFlow(orders: PaperOrder[]): { count: number; net: number } {
  const today = todayKey();
  let net = 0;
  let count = 0;

  for (const order of orders) {
    if (order.status !== "FILLED" || !order.filled_at) {
      continue;
    }
    const filledAt = new Date(order.filled_at);
    if (Number.isNaN(filledAt.getTime()) || dateKey(filledAt) !== today) {
      continue;
    }
    const price = order.average_fill_price ?? order.quoted_price;
    const amount = order.filled_quantity * price;
    net += (order.side === "SELL" ? amount : -amount) - order.commission;
    count += 1;
  }

  return { count, net };
}

function moverLines(
  holdings: Holding[],
  totalValue: number,
  language: AppLanguage,
): string[] {
  return topMovers(holdings).map((holding) => {
    const pct = formatSignedPct(holding.daily_change_pct ?? 0, language);
    const weight = totalValue > 0 ? (holding.market_value_try / totalValue) * 100 : 0;
    const amount = formatSignedTry(holding.daily_change_try, language);
    return language === "tr"
      ? `- ${holding.symbol} (${holding.asset_name}): bugün ${pct}, ${amount}, portföy payı %${formatPct(weight, language)}`
      : `- ${holding.symbol} (${holding.asset_name}): ${pct} today, ${amount}, ${formatPct(weight, language)}% of the portfolio`;
  });
}

/**
 * Sohbete gomulu gunluk brifing istemi.
 *
 * ILK SATIR AYRI TUTULUR: yeni sohbetin basligi backend'de ilk mesajin ILK
 * SATIRINDAN uretilir (bkz. `app/services/chat.py::sohbet_bul_veya_ac`).
 *
 * Kelime secimi kasitli: yonlendirme kural tabanlidir (bkz.
 * `orchestrator.py::INTENT_KEYWORDS`) - "portföyümde" portfoy, "haber"
 * piyasa, "risk" risk ajanini tetikler. Semboller de yazilir, yoksa piyasa
 * ajani portfoyle ilgisiz genel gunun haberlerini getirir.
 *
 * Rakamlar isteme GOMULUR: sentezleyiciye yalnizca ajanlarin ozet METNI
 * gidiyor (bkz. `_ajan_metni`), nakit bakiye ve emir gecmisi hicbir ajanda
 * yok - buradan verilmezse brifing onlardan hic bahsedemez.
 */
function buildPrompt(
  summary: PortfolioSummary,
  holdings: Holding[],
  account: TradingAccount | null,
  orders: PaperOrder[],
  language: AppLanguage,
): { displayText: string; prompt: string } {
  const symbols = topSymbols(holdings);
  const movers = moverLines(holdings, summary.total_value_try, language);
  const cashFlow = todaysCashFlow(orders);
  const change =
    summary.daily_change_pct == null
      ? formatSignedTry(summary.daily_change_try, language)
      : `${formatSignedPct(summary.daily_change_pct, language)} (${formatSignedTry(summary.daily_change_try, language)})`;
  const pnl = `${formatSignedTry(summary.total_pnl_try, language)}${
    summary.total_pnl_pct == null ? "" : ` (${formatSignedPct(summary.total_pnl_pct, language)})`
  }`;

  if (language === "en") {
    const displayText = "What happened in my portfolio today?";
    return {
      displayText,
      prompt: [
        displayText,
        "Write my daily portfolio briefing from the figures below.",
        "",
        "Portfolio (TRY):",
        `- Total value: ${formatTry(summary.total_value_try, language)}, today ${change}`,
        `- Total profit/loss: ${pnl}`,
        account
          ? `- Cash: ${formatTry(account.available_balance + account.reserved_balance, language)} (available ${formatTry(account.available_balance, language)}, reserved in orders ${formatTry(account.reserved_balance, language)})`
          : "- Cash: unavailable",
        cashFlow.count > 0
          ? `- Orders filled today: ${cashFlow.count}, net cash impact ${formatSignedTry(cashFlow.net, language)}`
          : "- No orders were filled today, so cash moved only with valuations.",
        ...(symbols.length > 0 ? [`- Largest holdings: ${symbols.join(", ")}`] : []),
        ...(movers.length > 0 ? ["", "Biggest movers today:", ...movers] : []),
        "",
        "Briefing rules:",
        "1. Start with the overall picture: portfolio value and today's change, cash and today's order impact, where the total profit/loss stands.",
        "2. Then walk through the movers above ONE BY ONE: percentage, TRY impact and portfolio weight, and which one drove the day.",
        "3. Then the news: if any source you have concerns one of my holdings, summarise it and explain which holding it affects and how. Do NOT say there is no news when your source list is not empty.",
        "4. Mention any notable change in my risk profile in one sentence.",
        "5. 200-250 words, flowing paragraphs, no headings. Do not invent numbers. Close with one short question.",
      ].join("\n"),
    };
  }

  const displayText = "Bugün portföyümde ne oldu?";
  return {
    displayText,
    prompt: [
      displayText,
      "Aşağıdaki rakamlara dayanarak günlük portföy brifingimi yaz.",
      "",
      "Portföy (TL):",
      `- Toplam değer: ${formatTry(summary.total_value_try, language)}, bugün ${change}`,
      `- Toplam kar/zarar: ${pnl}`,
      account
        ? `- Likit nakit: ${formatTry(account.available_balance + account.reserved_balance, language)} (kullanılabilir ${formatTry(account.available_balance, language)}, emirlerde bloke ${formatTry(account.reserved_balance, language)})`
        : "- Likit nakit: bilgi alınamadı",
      cashFlow.count > 0
        ? `- Bugün gerçekleşen emir: ${cashFlow.count} adet, nakde net etkisi ${formatSignedTry(cashFlow.net, language)}`
        : "- Bugün gerçekleşen emir yok, nakit yalnızca değerlemeyle değişti.",
      ...(symbols.length > 0 ? [`- Başlıca varlıklar: ${symbols.join(", ")}`] : []),
      ...(movers.length > 0 ? ["", "Bugün en çok hareket eden pozisyonlar:", ...movers] : []),
      "",
      "Brifing kuralları:",
      "1. Önce genel durum: portföy değeri ve bugünkü değişimi, likit nakit ve bugünkü emirlerin nakde etkisi, toplam kar/zararın nerede durduğu.",
      "2. Sonra yukarıdaki hareketli pozisyonları TEK TEK açıkla: yüzde, TL etkisi ve portföy payı; günün sonucunu hangisi belirledi.",
      "3. Sonra haberler: elindeki kaynaklarda portföyümdeki bir varlığı ya da şirketi ilgilendiren haber varsa özetle ve hangi varlığımı nasıl etkilediğini açıkla. Kaynak listen boş değilken \"öne çıkan haber yok\" DEME.",
      "4. Risk profilimde dikkat çeken bir değişiklik varsa tek cümleyle söyle.",
      "5. 200-250 kelime, akıcı paragraflar, başlık kullanma. Yeni sayı üretme. Sonunda kısa bir soru sor.",
    ].join("\n"),
  };
}

function buildBrief(
  summary: PortfolioSummary,
  holdings: Holding[],
  account: TradingAccount | null,
  orders: PaperOrder[],
  language: AppLanguage,
): DailyBrief | null {
  // Bos portfoyde anlatilacak bir gun yok - davet gosterilmez.
  if (summary.holding_count === 0 && summary.total_value_try === 0) {
    return null;
  }

  const tone = resolveTone(summary);
  const { displayText, prompt } = buildPrompt(summary, holdings, account, orders, language);

  return {
    tone,
    teaser: buildTeaser(summary, tone, language),
    actionLabel: language === "tr" ? "Günün özetini aç" : "Open today's brief",
    displayText,
    prompt,
  };
}

/**
 * Giristen sonra BIR KEZ gosterilen "bugun bilmen gerekenler" daveti.
 *
 * Yalnizca baloncugun icerigini uretir; ozetin kendisi kullanici baloncuga
 * tikladiginda normal sohbet akisindan (gomulu istemle) gelir - ayri bir
 * ozet ucu ve ikinci bir "sohbet motoru" olusmaz.
 */
export function useDailyBrief({
  enabled,
  userId,
  language,
}: {
  enabled: boolean;
  userId: number | null;
  language: AppLanguage;
}): { brief: DailyBrief | null; dismiss: () => void } {
  const [brief, setBrief] = useState<DailyBrief | null>(null);

  useEffect(() => {
    if (!enabled || userId === null) {
      setBrief(null);
      return;
    }

    if (!DEBUG_ALWAYS_SHOW && wasShownToday(userId)) {
      return;
    }

    let cancelled = false;
    let timer: number | null = null;

    async function prepareBrief(currentUserId: number) {
      let summary: PortfolioSummary;
      let holdings: Holding[] = [];
      let account: TradingAccount | null = null;
      let orders: PaperOrder[] = [];
      try {
        // Ozet DISINDAKI ucler istege bagli: alinamazsa brifing o bolumsuz
        // yazilir, davet iptal edilmez.
        const [summaryResponse, holdingsResponse, accountResponse, ordersResponse] =
          await Promise.all([
            getPortfolioSummary(),
            getPortfolioHoldings().catch(() => null),
            getTradingAccount().catch(() => null),
            getPaperOrders(50).catch(() => null),
          ]);
        summary = summaryResponse;
        holdings = holdingsResponse?.items ?? [];
        account = accountResponse;
        orders = ordersResponse?.items ?? [];
      } catch {
        // Davet mesaji kritik degil: portfoy ozeti alinamadiysa sessizce
        // vazgecilir, kullaniciya hata gosterilmez.
        return;
      }

      if (cancelled) {
        return;
      }

      const nextBrief = buildBrief(summary, holdings, account, orders, language);
      if (!nextBrief) {
        return;
      }

      timer = window.setTimeout(() => {
        if (cancelled) {
          return;
        }
        setBrief(nextBrief);
        // "Gorulduye" tam gosterim aninda yazilir: kullanici sayfayi
        // yenilerse ayni gun icinde tekrar cikmaz.
        if (!DEBUG_ALWAYS_SHOW) {
          markShownToday(currentUserId);
        }
      }, SHOW_DELAY_MS);
    }

    void prepareBrief(userId);

    return () => {
      cancelled = true;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    };
  }, [enabled, language, userId]);

  const dismiss = useCallback(() => setBrief(null), []);

  return { brief, dismiss };
}
