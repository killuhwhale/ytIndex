import axios from "axios";

let csrfToken: string | null = null;

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001/api",
  withCredentials: true
});

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

export function getCsrfToken() {
  return csrfToken;
}

api.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase();
  if (csrfToken && method && !["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    config.headers["X-CSRFToken"] = csrfToken;
  }
  return config;
});

api.interceptors.response.use((response) => {
  const token = response.data?.csrf_token;
  if (typeof token === "string") {
    setCsrfToken(token);
  }
  return response;
});
