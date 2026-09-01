export type User = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  risk_tolerance: string | null;
  monthly_income: number | null;
  onboarding_completed: boolean;
  /** False ise AppShell urun turunu (ProductTour) otomatik acar - yalnizca
   * onboarding tamamlandiktan sonra, ilk kayitta bir kez. */
  has_seen_tour: boolean;
  role: string;
  /** TC Kimlik No'nun son 4 hanesi - tam numara hicbir yanitta donmez. */
  tckn_last4: string | null;
  birth_date: string | null;
  phone_number: string | null;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  /** 11 haneli TC Kimlik No - NVI ile dogrulanir, backend'e DUZ METIN gider
   * ama hicbir yerde duz metin olarak saklanmaz/donmez. */
  tckn: string;
  /** "YYYY-AA-GG" - native `<input type="date">` cikisiyla birebir eslesir. */
  birth_date: string;
  phone_number: string;
};

export type RiskTier = "LOW" | "MEDIUM" | "HIGH";

export type OnboardingCompleteRequest = {
  risk_tolerance: RiskTier;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};
