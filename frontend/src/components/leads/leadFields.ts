import type { LeadQueueItem } from "../../models/leads";

/**
 * Lead satirlarinin TURETILMIS alanlari - tablo ve filtre paneli AYNI
 * mantigi kullansin diye tek yerde toplandi. Backend bu alanlari
 * gondermez; hepsi mevcut alanlardan hesaplanir.
 */

export type LeadStatus =
  // Danismanin ELLE isaretledigi gorusme sonuclari
  | "accepted"
  | "declined"
  | "unreachable"
  // Tarama motorunun urettigi durumlar. `bsd` backend'deki `decision`
  // degeriyle ayni kalir - orada da BSD (bireysel satis danismani) kuyrugu.
  | "bsd"
  | "email_sent"
  | "email_pending"
  | "excluded";

export const STATUS_LABELS: Record<LeadStatus, string> = {
  accepted: "Kabul etti",
  declined: "İstemiyor",
  unreachable: "Ulaşılamadı",
  bsd: "Aranacak",
  email_sent: "Mail gönderildi",
  email_pending: "Mail bekliyor",
  excluded: "Dışlandı",
};

/** Rozet rengi: aksiyon bekleyenler dikkat cekici, kapananlar sonuca gore. */
export const STATUS_CLASSES: Record<LeadStatus, string> = {
  accepted: "app-success-box border",
  declined: "app-danger-box border",
  // Aranacak ile AYNI ton, cunku ikisi de "hala aranmali" demek.
  unreachable: "app-warning-box border",
  bsd: "app-warning-box border",
  email_pending: "app-warning-box border",
  email_sent: "app-primary-soft",
  excluded: "app-card-muted app-muted",
};

/**
 * Gorusme sonucu YALNIZCA bu durumlarda isaretlenebilir; digerlerinde
 * rozet duz bir etiket olarak kalir (menu oku gosterilmez).
 *
 * Disarida kalanlar mail kuyrugundaki ve dislanan kisilerdir - danisman
 * onlari telefonla aramaz, dolayisiyla isaretleyecek bir gorusme sonucu
 * da olusmaz.
 */
export const OUTCOME_EDITABLE_STATUSES: ReadonlySet<LeadStatus> = new Set<LeadStatus>([
  "bsd",
  "unreachable",
  "accepted",
  "declined",
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
export function resolveStatus(item: LeadQueueItem): LeadStatus {
  if (item.call_outcome === "KABUL") return "accepted";
  if (item.call_outcome === "ISTEMIYOR") return "declined";
  if (item.call_outcome === "ULASILAMADI") return "unreachable";
  if (item.decision === "BSD") return "bsd";
  if (item.decision === "EXCLUDED") return "excluded";
  return item.mail_gonderildi ? "email_sent" : "email_pending";
}

/**
 * Anahtarlar backend'deki `lead_rules.uygunluk_degerlendir` donus
 * degerleriyle birebir eslesmeli; orada yeni bir dislama nedeni eklenirse
 * buraya da eklenmeli, yoksa danismana ham Ingilizce enum gorunur.
 */
export const EXCLUSION_REASON_LABELS: Record<string, string> = {
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

export function exclusionReasonLabel(item: LeadQueueItem): string | null {
  if (!item.exclusion_reason) return null;
  return EXCLUSION_REASON_LABELS[item.exclusion_reason] ?? item.exclusion_reason;
}

/** Dogum tarihinden yas; tarih yoksa ya da gecersizse `null`. */
export function calculateAge(birthDate: string | null): number | null {
  if (!birthDate) return null;
  const birth = new Date(birthDate);
  if (Number.isNaN(birth.getTime())) return null;

  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age -= 1;
  }
  return age >= 0 && age < 130 ? age : null;
}

export const moneyFormat = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 0,
});

export const dateFormat = new Intl.DateTimeFormat("tr-TR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

/**
 * Filtre paneli ve tablo kartinin ORTAK yuksekligi. Ikisi de ayni sabiti
 * kullanir; boylece cerceveler her zaman esit boyda durur ve tek yerden
 * ayarlanir. Liste bu yuksekligi asarsa scroll ile gezilir.
 */
export const PANEL_HEIGHT = "lg:h-[39rem]";

/**
 * Telefonu okunur gruplara ayirir: "+905539607671" -> "+90 553 960 7671".
 * Veri tek bicimde gelmiyor (bazi kayitlar "0555..." seklinde), bu yuzden
 * once rakamlar ayiklanir; taninmayan bir uzunluk gelirse deger OLDUGU GIBI
 * gosterilir - uydurma bir bicime zorlanmaz.
 */
export function formatPhone(raw: string | null): string {
  if (!raw) return "—";
  const digits = raw.replace(/\D/g, "");

  if (digits.length === 12 && digits.startsWith("90")) {
    return `+90 ${digits.slice(2, 5)} ${digits.slice(5, 8)} ${digits.slice(8)}`;
  }
  if (digits.length === 11 && digits.startsWith("0")) {
    return `0${digits.slice(1, 4)} ${digits.slice(4, 7)} ${digits.slice(7)}`;
  }
  if (digits.length === 10) {
    return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6)}`;
  }
  return raw;
}
