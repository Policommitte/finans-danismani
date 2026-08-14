export type User = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  risk_tolerance: string | null;
  monthly_income: number | null;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};
