import api from "./axiosConfig";

/** Extract a readable message from a DRF error response. */
export function apiError(err: any, fallback = "An error occurred."): string {
  const data = err?.response?.data;
  if (!data) return err?.message || fallback;
  if (typeof data === "string") return data.slice(0, 300);
  if (data instanceof Blob) return fallback;
  if (data.detail) return String(data.detail);
  if (Array.isArray(data)) return data.join(" ");
  const parts: string[] = [];
  for (const [key, value] of Object.entries(data)) {
    const text = Array.isArray(value) ? value.join(" ") : typeof value === "object" ? JSON.stringify(value) : String(value);
    parts.push(key === "non_field_errors" ? text : `${key}: ${text}`);
  }
  return parts.join(" · ") || fallback;
}

async function blobError(err: any): Promise<string> {
  const data = err?.response?.data;
  if (data instanceof Blob) {
    try {
      const text = await data.text();
      const json = JSON.parse(text);
      return json.detail || text;
    } catch {
      return "The file could not be produced.";
    }
  }
  return apiError(err);
}

function filenameFrom(disposition: string | undefined, fallback: string) {
  const match = disposition?.match(/filename="?([^";]+)"?/);
  return match ? match[1] : fallback;
}

/**
 * Download a file produced by the API (PDF, CSV, XLSX) with the auth header.
 * PDFs are opened in a new tab, other files are saved.
 */
export async function downloadFile(
  url: string,
  options: { method?: "get" | "post"; data?: unknown; params?: Record<string, unknown>; filename?: string; open?: boolean } = {},
) {
  try {
    const response = await api.request({
      url,
      method: options.method || "get",
      data: options.data,
      params: options.params,
      responseType: "blob",
    });
    const type = String(response.headers["content-type"] || "application/octet-stream");
    const blob = new Blob([response.data], { type });
    const href = URL.createObjectURL(blob);
    const name = filenameFrom(String(response.headers["content-disposition"] || ""), options.filename || "document");
    const shouldOpen = options.open ?? type.includes("pdf");
    if (shouldOpen) {
      const win = window.open(href, "_blank");
      if (!win) triggerSave(href, name);
    } else {
      triggerSave(href, name);
    }
    setTimeout(() => URL.revokeObjectURL(href), 60_000);
  } catch (err) {
    throw new Error(await blobError(err));
  }
}

function triggerSave(href: string, name: string) {
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

/** Normalise list responses (plain array or paginated). */
export function asList<T>(data: any): T[] {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

export const fmt = {
  money(value: unknown, currency = "XAF") {
    if (value === null || value === undefined || value === "") return "—";
    const n = Number(value);
    if (Number.isNaN(n)) return String(value);
    return `${n.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} ${currency}`;
  },
  number(value: unknown, digits = 2) {
    if (value === null || value === undefined || value === "") return "—";
    const n = Number(value);
    return Number.isNaN(n) ? String(value) : n.toLocaleString("fr-FR", { maximumFractionDigits: digits });
  },
  date(value: unknown) {
    if (!value) return "—";
    const d = new Date(String(value));
    return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString("fr-FR");
  },
  datetime(value: unknown) {
    if (!value) return "—";
    const d = new Date(String(value));
    return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
  },
  minutes(value: unknown) {
    const n = Number(value || 0);
    if (!n) return "—";
    return `${Math.floor(n / 60)}h${String(n % 60).padStart(2, "0")}`;
  },
};

export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function firstOfMonthISO() {
  return todayISO().slice(0, 8) + "01";
}
