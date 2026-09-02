import type { LeadQueueItem } from "../../models/leads";

/**
 * Lead satirlarinin TURETILMIS alanlari - tablo ve filtre paneli AYNI
 * mantigi kullansin diye tek yerde toplandi. Backend bu alanlari
 * gondermez; hepsi mevcut alanlardan hesaplanir.
 */

export type LeadDurum =
  // Danismanin ELLE isaretledigi gorusme sonuclari
  | "kabul"
  | "istemiyor"
  | "ulasilamadi"
  // Tarama motorunun urettigi durumlar
  | "bsd"
  | "mail_gonderildi"
  | "mail_bekliyor"
  | "dislandi";

export const DURUM_ETIKETLERI: Record<LeadDurum, string> = {
  kabul: "Kabul etti",
  istemiyor: "İstemiyor",
  ulasilamadi: "Ulaşılamadı",
  bsd: "Aranacak",
  mail_gonderildi: "Mail gönderildi",
  mail_bekliyor: "Mail bekliyor",
  dislandi: "Dışlandı",
};

/** Rozet rengi: aksiyon bekleyenler dikkat cekici, kapananlar sonuca gore. */
export const DURUM_SINIFLARI: Record<LeadDurum, string> = {
  kabul: "app-success-box border",
  istemiyor: "app-danger-box border",
  // Aranacak ile AYNI ton, cunku ikisi de "hala aranmali" demek.
  ulasilamadi: "app-warning-box border",
  bsd: "app-warning-box border",
  mail_bekliyor: "app-warning-box border",
  mail_gonderildi: "app-primary-soft",
  dislandi: "app-card-muted app-muted",
};

/**
 * Gorusme sonucu YALNIZCA bu durumlarda isaretlenebilir; digerlerinde
 * rozet duz bir etiket olarak kalir (menu oku gosterilmez).
 *
 * Disarida kalanlar mail kuyrugundaki ve dislanan kisilerdir - danisman
 * onlari telefonla aramaz, dolayisiyla isaretleyecek bir gorusme sonucu
 * da olusmaz.
 */
export const SONUC_ISARETLENEBILIR: ReadonlySet<LeadDurum> = new Set<LeadDurum>([
  "bsd",
  "ulasilamadi",
  "kabul",
  "istemiyor",
]);

/**
 * Sira onemli:
 *
 * 1. Danismanin elle isaretledigi sonuc HER SEYIN onunde gelir - o kisi
 *    icin motorun karari artik gecmis bilgidir.
 * 2. Sonra `decision`: `mail_gonderildi` alani YALNIZCA otonom uctan gelen
 *    satirlarda doldurulur, BSD ve dislanan satirlarda sema varsayilani
 *    olan `false` gelir (bkz. `services/leads.py::_kuyruk_getir`).
 */
export function durumBelirle(item: LeadQueueItem): LeadDurum {
  if (item.call_outcome === "KABUL") return "kabul";
  if (item.call_outcome === "ISTEMIYOR") return "istemiyor";
  if (item.call_outcome === "ULASILAMADI") return "ulasilamadi";
  if (item.decision === "BSD") return "bsd";
  if (item.decision === "EXCLUDED") return "dislandi";
  return item.mail_gonderildi ? "mail_gonderildi" : "mail_bekliyor";
}

/**
 * Anahtarlar backend'deki `lead_rules.uygunluk_degerlendir` donus
 * degerleriyle birebir eslesmeli; orada yeni bir dislama nedeni eklenirse
 * buraya da eklenmeli, yoksa danismana ham Ingilizce enum gorunur.
 */
export const DISLAMA_NEDENLERI: Record<string, string> = {
  consent_missing: "İletişim izni yok",
  email_missing: "E-posta adresi yok",
  income_below_threshold: "Beyan edilmiş geliri yok",
  already_invested: "Zaten yatırım yapmış",
  balance_below_threshold: "Atıl bakiyesi çok düşük",
  above_upper_limit: "Zaten üst segment (kampanya dışı)",
  recently_active: "Yakın zamanda aktif",
  cooldown_active: "Yakın zamanda mail gönderildi",
  advisor_closed: "Danışman kapattı",
};

export function dislamaNedeni(item: LeadQueueItem): string | null {
  if (!item.exclusion_reason) return null;
  return DISLAMA_NEDENLERI[item.exclusion_reason] ?? item.exclusion_reason;
}

/** Dogum tarihinden yas; tarih yoksa ya da gecersizse `null`. */
export function yasHesapla(birthDate: string | null): number | null {
  if (!birthDate) return null;
  const dogum = new Date(birthDate);
  if (Number.isNaN(dogum.getTime())) return null;

  const bugun = new Date();
  let yas = bugun.getFullYear() - dogum.getFullYear();
  const ayFarki = bugun.getMonth() - dogum.getMonth();
  if (ayFarki < 0 || (ayFarki === 0 && bugun.getDate() < dogum.getDate())) {
    yas -= 1;
  }
  return yas >= 0 && yas < 130 ? yas : null;
}

export const paraFormat = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 0,
});

export const tarihFormat = new Intl.DateTimeFormat("tr-TR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

/**
 * Filtre paneli ve tablo kartinin ORTAK yuksekligi. Ikisi de ayni sabiti
 * kullanir; boylece cerceveler her zaman esit boyda durur ve tek yerden
 * ayarlanir. Liste bu yuksekligi asarsa scroll ile gezilir.
 */
export const PANEL_YUKSEKLIGI = "lg:h-[39rem]";

/**
 * Telefonu okunur gruplara ayirir: "+905539607671" -> "+90 553 960 7671".
 * Veri tek bicimde gelmiyor (bazi kayitlar "0555..." seklinde), bu yuzden
 * once rakamlar ayiklanir; taninmayan bir uzunluk gelirse deger OLDUGU GIBI
 * gosterilir - uydurma bir bicime zorlanmaz.
 */
export function telefonFormat(ham: string | null): string {
  if (!ham) return "—";
  const rakam = ham.replace(/\D/g, "");

  if (rakam.length === 12 && rakam.startsWith("90")) {
    return `+90 ${rakam.slice(2, 5)} ${rakam.slice(5, 8)} ${rakam.slice(8)}`;
  }
  if (rakam.length === 11 && rakam.startsWith("0")) {
    return `0${rakam.slice(1, 4)} ${rakam.slice(4, 7)} ${rakam.slice(7)}`;
  }
  if (rakam.length === 10) {
    return `${rakam.slice(0, 3)} ${rakam.slice(3, 6)} ${rakam.slice(6)}`;
  }
  return ham;
}
