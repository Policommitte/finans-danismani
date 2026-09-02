export type EconomicEventImportance = "low" | "medium" | "high";

export type EconomicEvent = {
  event_date: string;
  /** Europe/Istanbul saatiyle "HH:MM" - bilinmiyorsa null. */
  event_time: string | null;
  country: string;
  event_name: string;
  importance: EconomicEventImportance;
  expected: string | null;
  actual: string | null;
  previous: string | null;
  /** "TCMB" | "TÜİK" | "Otomatik (Yahoo Finance)" gibi kaynak etiketi. */
  source_label: string;
};

export type EconomicCalendarResponse = {
  items: EconomicEvent[];
};
