/**
 * Axios instance pre-configured for the Quizbee API.
 *
 * Interceptors handle two concerns automatically:
 * - Request:  reads the `access_token` cookie and injects it as a Bearer header
 * - Response: on 401, clears auth cookies and redirects to /login (skipped on
 *             /take routes, which are public and use anonymous sessions)
 *
 * Base URL is controlled by NEXT_PUBLIC_API_URL (defaults to localhost for dev).
 */

import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({ baseURL: API_URL });

// Attach access token from cookie on every request
api.interceptors.request.use((config) => {
  if (typeof document !== "undefined") {
    const match = document.cookie.match(/(?:^|; )access_token=([^;]*)/);
    if (match) config.headers.Authorization = `Bearer ${decodeURIComponent(match[1])}`;
  }
  return config;
});

// On 401, clear cookies and redirect to login — but not on public /take routes
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (
      err?.response?.status === 401 &&
      typeof window !== "undefined" &&
      !window.location.pathname.startsWith("/take")
    ) {
      clearAuthCookies();
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

/**
 * Persist both JWT tokens as session cookies after a successful login.
 * SameSite=Lax prevents CSRF while allowing same-site navigation.
 * No Secure flag — dev runs over HTTP; production should enforce HTTPS at the
 * reverse proxy level.
 */
export function setAuthCookies(accessToken: string, refreshToken: string) {
  document.cookie = `access_token=${encodeURIComponent(accessToken)}; path=/; SameSite=Lax`;
  document.cookie = `refresh_token=${encodeURIComponent(refreshToken)}; path=/; SameSite=Lax`;
}

/** Expire both auth cookies immediately (logout or forced re-auth). */
export function clearAuthCookies() {
  document.cookie = "access_token=; path=/; max-age=0";
  document.cookie = "refresh_token=; path=/; max-age=0";
}
