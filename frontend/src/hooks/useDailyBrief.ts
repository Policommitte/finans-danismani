"use client";

import { useCallback, useEffect, useState } from "react";
import type { AppLanguage } from "../contexts/LanguageContext";
import type { Holding, PortfolioSummary } from "../models/portfolio";
import { getPortfolioHoldings, getPortfolioSummary } from "../services/portfolioService";

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

//: ⚠️ GECICI - DEBUGGING ICIN ACIK. Davet normalde kullanici basina GUNDE
//: BIR KEZ gosterilir; bu bayrak acikken her giriste (ve her sayfa
//: yenilemesinde) yeniden cikar, "gorulduye" de yazilmaz. Normal davranisa
//: donmek icin TEK YAPILACAK: `false`.
const DEBUG_ALWAYS_SHOW: boolean = true;

const STORAGE_PREFIX = "polifin-daily-brief-v1";

function storageKey(userId: number): string {
  return `${STORAGE_PREFIX}:${userId}`;
}

/** Yerel takvim gunu (YYYY-AA-GG) - ozet gunde bir kez gosterilir. */
function todayKey(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
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

function formatSignedTry(value: number, language: AppLanguage): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  const formatted = new Intl.NumberFormat(language === "tr" ? "tr-TR" : "en-US", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(Math.abs(value));
  return `${sign}${formatted}`;
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

/**
 * Sohbete gomulu gunluk ozet istemi.
 *
 * ILK SATIR AYRI TUTULUR: yeni sohbetin basligi backend'de ilk mesajin ILK
 * SATIRINDAN uretilir (bkz. `app/services/chat.py::sohbet_bul_veya_ac`) -
 * yonergelerle baslasaydi sohbet listesinde "Son 24 saatte portfoyumde one
 * cikan..." gibi bir baslik kalirdi.
 *
 * Kelime secimi de kasitli: yonlendirme kural tabanlidir (bkz.
 * `app/engine/orchestrator.py::INTENT_KEYWORDS`). "portföyümde" portfoy
 * ajanini, "haber" piyasa arastirmasini, "risk" ise risk ajanini tetikler -
 * ucu de TEK seferde calisip tek yanitta birlesir.
 *
 * Baslica semboller de isteme YAZILIR: piyasa ajani haberleri sorgudan
 * arar, sembol gecmezse portfoyu ilgilendiren degil GENEL gunun haberlerini
 * getirir - davetin vaadi ise "seni ilgilendiren haber".
 */
function buildPrompt(
  summary: PortfolioSummary,
  symbols: string[],
  language: AppLanguage,
): { displayText: string; prompt: string } {
  const change =
    summary.daily_change_pct == null
      ? formatSignedTry(summary.daily_change_try, language)
      : `%${formatPct(summary.daily_change_pct, language)} (${formatSignedTry(summary.daily_change_try, language)})`;

  if (language === "en") {
    const displayText = "What happened in my portfolio today?";
    return {
      displayText,
      prompt: [
        displayText,
        `Summarise the most important moves in my portfolio over the last 24 hours and any news that concerns my holdings. Today's portfolio change: ${change}.`,
        ...(symbols.length > 0 ? [`My largest holdings: ${symbols.join(", ")}.`] : []),
        "Rules:",
        "- At most 6 short bullets, under 120 words in total.",
        "- Name the biggest gaining and losing positions with their percentages.",
        "- If a news item directly concerns one of my holdings, explain it in one sentence; otherwise say there is nothing notable.",
        "- Mention a notable change in my risk profile in a single sentence.",
        "- No investment advice; close with one short question inviting me to dig deeper.",
      ].join("\n"),
    };
  }

  const displayText = "Bugün portföyümde ne oldu?";
  return {
    displayText,
    prompt: [
      displayText,
      `Son 24 saatte portföyümde öne çıkan hareketleri ve varlıklarımı ilgilendiren haberleri özetle. Portföyün bugünkü değişimi: ${change}.`,
      ...(symbols.length > 0 ? [`Portföyümdeki başlıca varlıklar: ${symbols.join(", ")}.`] : []),
      "Kurallar:",
      "- En fazla 6 kısa madde, toplamda 120 kelimeyi aşma.",
      "- En çok kazandıran ve en çok kaybettiren pozisyonları yüzdesiyle söyle.",
      "- Portföyümdeki bir varlığı doğrudan ilgilendiren haber varsa tek cümleyle açıkla; yoksa öne çıkan haber olmadığını söyle.",
      "- Risk durumumda dikkat çeken bir değişiklik varsa tek cümleyle belirt.",
      "- Yatırım tavsiyesi verme; sonunda devam etmeye davet eden kısa bir soru sor.",
    ].join("\n"),
  };
}

/** Degeri en buyuk pozisyonlarin sembolleri (istemde kullanilir). */
function topSymbols(holdings: Holding[]): string[] {
  return [...holdings]
    .sort((a, b) => b.market_value_try - a.market_value_try)
    .slice(0, PROMPT_SYMBOL_COUNT)
    .map((holding) => holding.symbol);
}

function buildBrief(
  summary: PortfolioSummary,
  holdings: Holding[],
  language: AppLanguage,
): DailyBrief | null {
  // Bos portfoyde anlatilacak bir gun yok - davet gosterilmez.
  if (summary.holding_count === 0 && summary.total_value_try === 0) {
    return null;
  }

  const tone = resolveTone(summary);
  const { displayText, prompt } = buildPrompt(summary, topSymbols(holdings), language);

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
      try {
        // Varliklar YALNIZCA isteme yazilacak sembolleri besler; alinamamasi
        // daveti iptal etmez, ozet o zaman sembolsuz istemle calisir.
        const [summaryResponse, holdingsResponse] = await Promise.all([
          getPortfolioSummary(),
          getPortfolioHoldings().catch(() => null),
        ]);
        summary = summaryResponse;
        holdings = holdingsResponse?.items ?? [];
      } catch {
        // Davet mesaji kritik degil: portfoy ozeti alinamadiysa sessizce
        // vazgecilir, kullaniciya hata gosterilmez.
        return;
      }

      if (cancelled) {
        return;
      }

      const nextBrief = buildBrief(summary, holdings, language);
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
