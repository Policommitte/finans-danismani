/**
 * Sohbete yazilan serbest metinden AL/SAT niyetini ve varligi cozer.
 *
 * NEDEN FRONTEND'DE (ve LLM'de degil): projede zaten ayni desen var -
 * "yatirim yapmak istiyorum" akisi (`useInvestmentPackageFlow`) da niyeti
 * YEREL yakalar, hicbir mesaj backend'e gitmez. Ayni yaklasim burada da
 * secildi: emir onerisi para hareketi baslatan bir adim, LLM'in serbest
 * yorumuna birakmak yerine ACIK ve ONGORULEBILIR kaliplarla tetiklenmesi
 * tercih edildi. Kullanici yine de her emri karttan TEK TEK onaylar.
 *
 * ⚠️ SEMBOL COZUMU BACKEND'DEKININ SADELESTIRILMIS IKIZI. Asil/kalibre
 * edilmis surum `app/agents/market_research.py::resolve_symbol`'dur; burada
 * yalnizca en guclu iki katman (tam kod eslesmesi + kod/ad + Turkce ek)
 * tekrarlanir. Ikisi ayrisirsa kullaniciya gorunen sonuc "varligi bulamadim"
 * mesajidir - yanlis varlikta emir ONERILMEZ, cunku onerilen sembol her
 * durumda katalogdan (`/api/market/assets`) gelir.
 */

import type { Asset } from "../models/market";
import { parseBudgetInput } from "./budgetInput";

export type TradeSide = "BUY" | "SELL";

export type TradeIntent = {
  side: TradeSide;
  /** Acikca yazilmis adet ("5 lot", "3 adet") - yoksa `null`. */
  quantity: number | null;
  /** Acikca yazilmis TL butcesi ("10 bin TL'lik") - yoksa `null`. */
  amountTry: number | null;
};

//: Turkce harfleri ASCII karsiliklarina cevirir (backend `_TR_TRANSLATION`
//: ile ayni kume) - "ereğli" ile "eregli" ayni sekilde eslessin diye.
const TR_MAP: Record<string, string> = {
  ç: "c", ğ: "g", ı: "i", ö: "o", ş: "s", ü: "u",
  Ç: "c", Ğ: "g", İ: "i", I: "i", Ö: "o", Ş: "s", Ü: "u",
  â: "a", î: "i", û: "u",
};

export function normalizeTr(text: string): string {
  return text.replace(/[çğıöşüÇĞİIÖŞÜâîû]/g, (ch) => TR_MAP[ch] ?? ch).toLowerCase();
}

//: ALIM fiilleri. "satin al" da buraya duser - `\b` sinirlari sayesinde
//: "satin" SATIM desenine TAKILMAZ ("sat" tam kelime degil).
const BUY_PATTERN =
  /\b(?:satin\s+)?al(?:sana|alim|ayim|acagim|acaksin|iyorum|abilir|abilirsin|mak|im|ir)?\b/;

//: SATIM fiilleri. "satin" bilerek KAPSAM DISI (bkz. yukarisi).
const SELL_PATTERN =
  /\bsat(?:sana|alim|ayim|acagim|acaksin|iyorum|abilir|abilirsin|mak|im|ar|is)?\b/;

//: Tavsiye SORUSU kaliplari - emir onerisi URETILMEZ. "alsam mi", "alinir
//: mi", "almali miyim" gibi sorular bir emir talebi degil, fikir sorusudur;
//: bunlara kart cikarmak kullaniciyi islem yapmaya itmis olurdu.
const ADVICE_QUESTION = /\b(mi|mu)\b/;

//: Soru kelimeleri. Cumlede soru varsa bu bir EMIR degil bilgi
//: talebidir: "hisse alim maliyetim ne" -> normal sohbete gitmeli,
//: kart cikmamali. Bilincli olarak MUHAFAZAKAR - emin olmadigimiz
//: cumleyi sohbete birakmak, kullanicinin istemedigi bir emir kartini
//: onune koymaktan iyidir; emir isteyen net yazabilir ("5 lot THYAO al").
const QUESTION_WORD =
  /\b(ne|nedir|neden|niye|nicin|nasil|hangi|kac|kacta|kactan|kim|nerede)\b/;

//: Adet ifadeleri: "5 lot", "3 adet", "2 tane", "10 hisse", "5 gram".
const QUANTITY_PATTERN = /(\d+(?:[.,]\d+)?)\s*(?:lot|adet|tane|hisse|gram|birim)\b/;

//: Tutar ifadesi sayilmasi icin metinde para birimi GECMELI - aksi halde
//: "5 lot" ifadesindeki 5 butce sanilirdi.
const CURRENCY_MARKER = /(₺|\btl\b|\btry\b|\blira)/;

/**
 * Mesajdan al/sat niyetini cikarir; emir kastedilmiyorsa `null`.
 *
 * Bilincli olarak MUHAFAZAKAR: yalnizca acik fiil kaliplari tetikler ve
 * tavsiye sorulari ("alsam mi") DISLANIR.
 */
export function parseTradeIntent(raw: string): TradeIntent | null {
  const text = normalizeTr(raw).trim();
  if (!text) return null;

  if (ADVICE_QUESTION.test(text) || QUESTION_WORD.test(text) || text.includes("?")) {
    return null;
  }

  const buy = BUY_PATTERN.test(text);
  const sell = SELL_PATTERN.test(text);
  // Ikisi birden gecen cumle ("al sat sinyalleri nedir") bir emir degildir.
  if (buy === sell) return null;

  const quantityMatch = text.match(QUANTITY_PATTERN);
  const quantity = quantityMatch ? Number(quantityMatch[1].replace(",", ".")) : null;

  // Adet acikca yazildiysa tutar aranmaz: "5 lot" ifadesindeki 5, butce degil.
  const amountTry =
    quantity === null && CURRENCY_MARKER.test(text) ? parseBudgetInput(raw) : null;

  return {
    side: buy ? "BUY" : "SELL",
    quantity: quantity !== null && Number.isFinite(quantity) && quantity > 0 ? quantity : null,
    amountTry,
  };
}

/** Sembolun ASCII/sikisik varyantlari: "USD/TRY" -> {"usd/try", "usdtry"}. */
function symbolRoots(symbol: string): string[] {
  const kok = normalizeTr(symbol);
  const sikisik = kok.replace(/[^a-z0-9]/g, "");
  return sikisik && sikisik !== kok ? [kok, sikisik] : [kok];
}

//: Kod/ad sonrasi kabul edilen Turkce ekler ("eregli" -> EREGL + "i",
//: "ereğliden" -> EREGL + "iden"). Liste bilerek SONLU: acik uclu bir ek
//: kurali ("3 harfe kadar her sey") gunluk kelimeleri sembol sanardi.
const TR_SUFFIXES = new Set([
  "", "i", "u", "a", "e", "n", "in", "un", "nin", "nun",
  "den", "dan", "ten", "tan", "de", "da", "te", "ta",
  "yi", "yu", "si", "su", "ni", "nu", "im", "an", "en",
  "ler", "lar", "leri", "lari", "lerin", "larin",
  // Kaynastirma unlusu + hal eki: "eregli-den", "aselsan-i-n"
  "iden", "idan", "uden", "udan", "nden", "ndan",
  "inden", "indan", "unden", "undan",
  "ini", "ine", "ina", "unu", "una", "sini", "sinin", "sunu", "sunun",
  "le", "la", "yle", "yla", "ile", "li", "lu", "lik", "luk",
]);

//: Kullanicinin gunluk dilde kullandigi ama katalog ADIYLA eslesmeyen
//: isimler. Backend'deki `_SEMBOL_TAKMA_ADLARI` ile AYNI kume - orada
//: gerekcesi tek tek yazili (orn. USD/TRY'nin adi "Amerikan Dolari", ilk
//: kelimesi "amerikan"; kullanici ise "dolar" der).
const ALIASES: Record<string, string> = {
  dolar: "USD/TRY", dolari: "USD/TRY", dolarin: "USD/TRY",
  usd: "USD/TRY", usdtry: "USD/TRY",
  eur: "EUR/TRY", eurtry: "EUR/TRY", eurosu: "EUR/TRY", euronun: "EUR/TRY",
  altin: "GRAM_ALTIN", altini: "GRAM_ALTIN", altinin: "GRAM_ALTIN",
  gumusu: "GUMUS", gumusun: "GUMUS",
  bim: "BIMAS", bimin: "BIMAS",
  koc: "KCHOL", kocun: "KCHOL",
  lilly: "LLY", thy: "THYAO",
  petrol: "BRENT", petrolu: "BRENT", petrolun: "BRENT",
  berkshire: "BRK-B", coca: "KO", cola: "KO", att: "T",
  tahvil: "US10Y", tahvili: "US10Y", tahvilin: "US10Y",
};

function matchesWithSuffix(token: string, kok: string): boolean {
  return token.startsWith(kok) && TR_SUFFIXES.has(token.slice(kok.length));
}

/**
 * Metindeki varligi KATALOGDAN cozer; tahmin uretmez.
 *
 * Katalogda gercekten var olan bir sembolle eslesmezse `null` doner - boylece
 * "HISSE" gibi uydurma bir kodla emir onerilmesi YAPISAL OLARAK imkansizdir.
 */
export function resolveAssetFromText(raw: string, assets: Asset[]): Asset | null {
  const text = normalizeTr(raw);
  const tokens = text.match(/[a-z0-9]+/g) ?? [];
  if (tokens.length === 0) return null;

  // (puan, konum) - once puan (tam eslesme > ekli eslesme), esitlikte
  // cumlede ONCE gecen kazanir.
  let best: { asset: Asset; score: number; position: number } | null = null;

  const consider = (asset: Asset, score: number, position: number) => {
    if (
      best === null ||
      score > best.score ||
      (score === best.score && position < best.position)
    ) {
      best = { asset, score, position };
    }
  };

  for (const asset of assets) {
    const roots = symbolRoots(asset.symbol);
    // Cok kisa kodlar (KO, T) gunluk kelimelerle cakisir; yalnizca HAM
    // metinde BUYUK HARFLE tam kelime olarak yazildiysa kabul edilir.
    if (asset.symbol.replace(/[^A-Za-z0-9]/g, "").length < 3) {
      const strict = new RegExp(`(?<![A-Za-z0-9])${asset.symbol}(?![A-Za-z0-9])`);
      if (strict.test(raw)) consider(asset, 3, raw.indexOf(asset.symbol));
      continue;
    }

    let matched = false;
    tokens.forEach((token, index) => {
      if (matched) return;
      if (roots.includes(token)) {
        consider(asset, 3, index);
        matched = true;
      } else if (roots.some((kok) => matchesWithSuffix(token, kok))) {
        consider(asset, 2, index);
        matched = true;
      }
    });
    if (matched) continue;

    const name = normalizeTr(asset.name).trim();
    if (name && text.includes(name)) {
      consider(asset, 3, text.indexOf(name));
      continue;
    }
    // Adin ilk kelimesi ("aselsan", "erdemir") - kisa kelimeler (\"bim\")
    // gunluk dille cakismasin diye en az 5 harf istenir.
    const firstWord = name.split(/\s+/)[0] ?? "";
    if (firstWord.length >= 5) {
      tokens.forEach((token, index) => {
        if (matched) return;
        if (matchesWithSuffix(token, firstWord)) {
          consider(asset, 2, index);
          matched = true;
        }
      });
    }
  }

  // TAKMA ADLAR EN SON denenir: gercek bir kod/ad eslesmesi bulunduysa o
  // kazanmali (backend `resolve_symbol` ile ayni sira).
  if (best === null) {
    for (const [index, token] of tokens.entries()) {
      const symbol = ALIASES[token];
      if (!symbol) continue;
      const asset = assets.find((item) => item.symbol.toUpperCase() === symbol);
      if (asset) {
        consider(asset, 2, index);
        break;
      }
    }
  }

  return best ? (best as { asset: Asset }).asset : null;
}
