/**
 * Varlik sinifina gore adet kurallari — backend `app/core/quantity.py` ile
 * AYNI kumeyi tasir.
 *
 * Buradaki kontrol yalnizca ARAYUZ KOLAYLIGIDIR; son sozu backend soyler
 * (istemci dogrulamasi atlanabilir). Iki taraf ayrisirsa kullanici arayuzun
 * kabul ettigi bir adette sunucu hatasi alir, o yuzden kume elle senkron
 * tutulur.
 */
export const BOLUNMEZ_SINIFLAR = new Set(["STOCK", "USA_STOCK", "EU_STOCK", "ETF"]);

export function bolunmezMi(assetClass: string | undefined | null): boolean {
  return BOLUNMEZ_SINIFLAR.has((assetClass ?? "").toUpperCase());
}

export function adetGecerliMi(adet: number, assetClass: string | undefined | null): boolean {
  if (!Number.isFinite(adet) || adet <= 0) return false;
  return bolunmezMi(assetClass) ? Number.isInteger(adet) : true;
}
