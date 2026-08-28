/**
 * Varlik sinifina gore adet kurallari — backend `app/core/quantity.py` ile
 * AYNI kumeleri tasir.
 *
 * Buradaki kontrol yalnizca ARAYUZ KOLAYLIGIDIR; son sozu backend soyler
 * (istemci dogrulamasi atlanabilir). Iki taraf ayrisirsa kullanici arayuzun
 * kabul ettigi bir adette sunucu hatasi alir, o yuzden kumeler elle senkron
 * tutulur.
 */

/** Tam adet alinan siniflar. Gram altin "0,38 gram" diye alinmaz. */
export const BOLUNMEZ_SINIFLAR = new Set([
  "STOCK",
  "USA_STOCK",
  "EU_STOCK",
  "ETF",
  "GOLD",
  "COMMODITY",
  "BOND",
]);

/** Yalnizca doviz: 0,25'in katlari. */
export const CEYREK_ADIMLI_SINIFLAR = new Set(["FOREX"]);
export const CEYREK_ADIM = 0.25;

/** Yalnizca kripto serbest ondalik alir. */
export const SERBEST_SINIFLAR = new Set(["CRYPTO"]);

function sinif(assetClass: string | undefined | null): string {
  return (assetClass ?? "").toUpperCase();
}

export function bolunmezMi(assetClass: string | undefined | null): boolean {
  return BOLUNMEZ_SINIFLAR.has(sinif(assetClass));
}

export function ceyrekAdimliMi(assetClass: string | undefined | null): boolean {
  return CEYREK_ADIMLI_SINIFLAR.has(sinif(assetClass));
}

export function adetAdimi(assetClass: string | undefined | null): string {
  if (ceyrekAdimliMi(assetClass)) return "0.25";
  if (SERBEST_SINIFLAR.has(sinif(assetClass))) return "any";
  return "1";
}

export function adetGecerliMi(adet: number, assetClass: string | undefined | null): boolean {
  if (!Number.isFinite(adet) || adet <= 0) return false;
  if (ceyrekAdimliMi(assetClass)) {
    return Math.abs(adet / CEYREK_ADIM - Math.round(adet / CEYREK_ADIM)) < 1e-6;
  }
  if (SERBEST_SINIFLAR.has(sinif(assetClass))) return true;
  return Number.isInteger(adet);
}

export function gecersizAdetMesaji(
  assetClass: string | undefined | null,
  language: string,
): string {
  if (ceyrekAdimliMi(assetClass)) {
    return language === "tr"
      ? "Döviz emirleri 0,25'in katları olmalıdır."
      : "Currency orders must be in multiples of 0.25.";
  }
  return language === "tr"
    ? "Bu varlık tam adet alınıp satılır."
    : "This asset can only be traded in whole units.";
}
