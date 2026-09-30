import { apiFetch } from "./client";

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: "ADMIN" | "MAIN_ADMIN";
  is_active: boolean;
  last_login?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface LoginPayload {
  email: string;
  password: string;
  remember_me?: boolean;
}

export async function loginApi(payload: LoginPayload): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMeApi(): Promise<UserProfile> {
  return apiFetch<UserProfile>("/api/auth/me");
}

export async function logoutApi(): Promise<{ message: string }> {
  return apiFetch<{ message: string }>("/api/auth/logout", {
    method: "POST",
  });
}
