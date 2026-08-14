import type { LoginRequest, TokenResponse, User } from "../models/auth";
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

export async function getMe(): Promise<User> {
  return apiRequest<User>("/api/auth/me");
}

export function logout(): void {
  clearAccessToken();
}
