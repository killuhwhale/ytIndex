import { api, getCsrfToken, setCsrfToken } from "./client";

export type AuthUser = {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
};

export type AuthState = {
  authenticated: boolean;
  csrf_token: string;
  user: AuthUser | null;
};

export async function getCurrentUser() {
  const { data } = await api.get<AuthState>("/auth/me/");
  setCsrfToken(data.csrf_token);
  return data;
}

async function ensureCsrfToken() {
  if (!getCsrfToken()) {
    await getCurrentUser();
  }
}

export async function login(email: string, password: string) {
  await ensureCsrfToken();
  const { data } = await api.post<AuthState>("/auth/login/", { email, password });
  setCsrfToken(data.csrf_token);
  return data;
}

export async function register(email: string, password: string) {
  await ensureCsrfToken();
  const { data } = await api.post<AuthState>("/auth/register/", { email, password });
  setCsrfToken(data.csrf_token);
  return data;
}

export async function logout() {
  await ensureCsrfToken();
  const { data } = await api.post<AuthState>("/auth/logout/");
  setCsrfToken(data.csrf_token);
  return data;
}

export async function requestPasswordReset(email: string) {
  await ensureCsrfToken();
  const { data } = await api.post<{ detail: string }>("/auth/password-reset/", { email });
  return data;
}

export async function confirmPasswordReset(uid: string, token: string, password: string) {
  await ensureCsrfToken();
  const { data } = await api.post<{ detail: string }>("/auth/password-reset/confirm/", { uid, token, password });
  return data;
}
