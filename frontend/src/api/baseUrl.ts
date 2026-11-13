/**
 * Address of the API.
 * Always normalizes to include the trailing `/api/` path so relative
 * endpoints like `auth/login/` correctly resolve to `/api/auth/login/`.
 */
function normalizeApiUrl(raw?: string): string {
  const val = (raw || "").trim();
  if (!val) {
    return "/api/";
  }
  if (val.endsWith("/api") || val.endsWith("/api/")) {
    return val.replace(/\/+$/, "") + "/";
  }
  return val.replace(/\/+$/, "") + "/api/";
}

const rawUrl: string = import.meta.env.DEV
  ? import.meta.env.VITE_API_URL || "http://localhost:8000/api/"
  : import.meta.env.VITE_PROD_API_URL || import.meta.env.VITE_API_URL || "/api/";

export const API_URL = normalizeApiUrl(rawUrl);
