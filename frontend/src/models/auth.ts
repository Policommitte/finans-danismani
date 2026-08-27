export type User = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  risk_tolerance: string | null;
  monthly_income: number | null;
  onboarding_completed: boolean;
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
