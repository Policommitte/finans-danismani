export type LeadQueueItem = {
  user_id: number;
  first_name: string;
  last_name: string;
  email: string;
  decision: string;
  exclusion_reason: string | null;
  score: number;
  score_components: Record<string, number>;
  reasons: string[];
  total_value_try: number;
  monthly_income: number;
  likit_para: number;
  phone_number: string | null;
  /** Yas EKRANDA bundan turetilir (bkz. `yasHesapla`), ayrica saklanmaz. */
  birth_date: string | null;
  tckn_last4: string | null;
  /**
   * Musterinin sisteme eklendigi an (`users.created_at`). Asagidaki
   * `created_at` ile KARISTIRILMAMALI: o, satirin hangi taramada/temasta
   * uretildigini soyler ve her taramada degisir.
   */
  registered_at: string | null;
  days_since_activity: number | null;
  /** Danismanin son isaretledigi gorusme sonucu; hic isaretlenmediyse null. */
  call_outcome: CallOutcome | null;
  call_outcome_at: string | null;
  mail_gonderildi: boolean;
  created_at: string;
};

/**
 * `ACIK` bir sonuc DEGIL, "sonucu temizle" komutudur: yalnizca ISTEKTE
 * gonderilir, yanitta hic gorunmez (backend onu null'a cevirir).
 */
export type CallOutcome = "KABUL" | "ISTEMIYOR" | "ULASILAMADI";
export type CallOutcomeInput = CallOutcome | "ACIK";

export type LeadScanSummary = {
  scan_id: number | null;
  trigger: string | null;
  started_at: string | null;
  finished_at: string | null;
  scanned_count: number;
  bsd_count: number;
  autonomous_count: number;
  excluded_count: number;
  emailed_count: number;
  skipped: boolean;
  skip_reason: string | null;
};

export type LeadQueueResponse = {
  items: LeadQueueItem[];
  count: number;
  scan: LeadScanSummary;
};