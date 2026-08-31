import type {
  LoginRequest,
  OnboardingCompleteRequest,
  RegisterRequest,
  TokenResponse,
  User,
} from "../models/auth";
import { apiRequest, clearAccessToken, setAccessToken } from "./apiClient";

export async function login(payload: LoginRequest): Promise<TokenResponse> {
  const token = await apiRequest<TokenResponse>("/api/auth/login", {
    method: "POST",
    auth: false,
    body: JSON.stringify(payload),
  });
  setAccessToken(token.access_token);
  return token;
}

export async function register(payload: RegisterRequest): Promise<TokenResponse> {
  const token = await apiRequest<TokenResponse>("/api/auth/register", {
    method: "POST",
    auth: false,
    body: JSON.stringify(payload),
  });
  setAccessToken(token.access_token);
  return token;
}

export async function getMe(): Promise<User> {
  return apiRequest<User>("/api/auth/me");
}

export async function completeOnboarding(payload: OnboardingCompleteRequest): Promise<User> {
  return apiRequest<User>("/api/auth/onboarding/complete", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function logout(): void {
  clearAccessToken();
}
