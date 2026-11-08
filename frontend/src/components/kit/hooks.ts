import { useCallback, useEffect, useRef, useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, asList } from "@/api/helpers";

/** Load a list from the API; `reload` refreshes it. Pass null to skip. */
export function useApiList<T = any>(endpoint: string | null, params?: Record<string, unknown>) {
  const [rows, setRows] = useState<T[]>([]);
  const [loading, setLoading] = useState(!!endpoint);
  const [error, setError] = useState<string | null>(null);
  const key = JSON.stringify(params || {});

  const reload = useCallback(async () => {
    if (!endpoint) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(endpoint, { params });
      setRows(asList<T>(res.data));
    } catch (err) {
      setError(apiError(err));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [endpoint, key]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { rows, setRows, loading, error, reload };
}

/** Load a single resource. */
export function useApiItem<T = any>(endpoint: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(!!endpoint);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!endpoint) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(endpoint);
      setData(res.data);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, setData, loading, error, reload };
}

export interface Option {
  value: string | number;
  label: string;
}

const optionCache = new Map<string, Promise<Option[]>>();

/** Options of a select loaded from an endpoint, cached for the session. */
export function useOptions(url: string | undefined, label: (row: any) => string, value: (row: any) => any = (r) => r.id) {
  const [options, setOptions] = useState<Option[]>([]);
  const labelRef = useRef(label);
  const valueRef = useRef(value);

  useEffect(() => {
    if (!url) return;
    let alive = true;
    if (!optionCache.has(url)) {
      optionCache.set(
        url,
        api
          .get(url)
          .then((res) => asList<any>(res.data))
          .catch(() => {
            optionCache.delete(url);
            return [];
          }) as Promise<any>,
      );
    }
    optionCache.get(url)!.then((rows: any) => {
      if (alive) setOptions(rows.map((r: any) => ({ value: valueRef.current(r), label: labelRef.current(r) })));
    });
    return () => {
      alive = false;
    };
  }, [url]);

  return options;
}

export function clearOptionCache(prefix?: string) {
  for (const key of Array.from(optionCache.keys())) {
    if (!prefix || key.startsWith(prefix)) optionCache.delete(key);
  }
}

/** Active tab synchronised with the URL hash. */
export function useHashTab(defaultTab: string) {
  const read = () => window.location.hash.replace("#", "") || defaultTab;
  const [tab, setTab] = useState(read);
  useEffect(() => {
    const onHash = () => setTab(read());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const change = (next: string) => {
    window.history.replaceState(null, "", `#${next}`);
    setTab(next);
  };
  return [tab, change] as const;
}
