import { useEffect, useMemo, useRef, useState } from "react";
import api from "@/api/axiosConfig";
import { asList } from "@/api/helpers";
import { cn } from "@/utils";
import type { Option } from "./hooks";

/**
 * Searchable picker used for every relation field: the user types a name,
 * a matriculation or a code and picks in the list. The user never has to
 * know or type an identifier.
 */
interface Props {
  value: any;
  onChange: (value: any, row?: any) => void;
  /** Endpoint searched with ?search= (server side) and filtered on screen. */
  url?: string;
  /** Static options (filtered on screen). */
  options?: Option[];
  label?: (row: any) => string;
  valueOf?: (row: any) => any;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  params?: Record<string, unknown>;
  className?: string;
}

const MAX_RESULTS = 40;

function defaultLabel(row: any) {
  if (row.full_name && row.matriculation_number) return `${row.full_name} (${row.matriculation_number})`;
  return row.full_name || row.name || row.title || row.label || row.code || row.username || "—";
}

function normalise(text: string) {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");
}

export default function SearchSelect({
  value,
  onChange,
  url,
  options,
  label = defaultLabel,
  valueOf = (row) => row.id,
  placeholder = "Type to search…",
  required,
  disabled,
  params,
  className,
}: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<Option[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState("");
  const [highlight, setHighlight] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const labelRef = useRef(label);
  const valueRef = useRef(valueOf);
  useEffect(() => {
    labelRef.current = label;
    valueRef.current = valueOf;
  });
  const paramsKey = JSON.stringify(params || {});

  // Label of the current value (form opened on an existing record).
  useEffect(() => {
    if (value === null || value === undefined || value === "") {
      setSelectedLabel("");
      return;
    }
    const known = (options || rows).find((o) => String(o.value) === String(value));
    if (known) {
      setSelectedLabel(known.label);
      return;
    }
    if (!url) return;
    let alive = true;
    const base = url.split("?")[0];
    api
      .get(`${base}${value}/`)
      .then((res) => alive && setSelectedLabel(labelRef.current(res.data)))
      .catch(() => alive && setSelectedLabel(String(value)));
    return () => {
      alive = false;
    };
  }, [value, url, options]);

  // Server search, debounced.
  useEffect(() => {
    if (!url || !open) return;
    let alive = true;
    setLoading(true);
    const timer = window.setTimeout(() => {
      api
        .get(url, { params: { ...(params || {}), search: query || undefined } })
        .then((res) => {
          if (!alive) return;
          setRows(asList<any>(res.data).map((r) => ({ value: valueRef.current(r), label: labelRef.current(r) })));
        })
        .catch(() => alive && setRows([]))
        .finally(() => alive && setLoading(false));
    }, 250);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [url, open, query, paramsKey]);

  // Close when clicking outside.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const results = useMemo(() => {
    const source = options || rows;
    const words = normalise(query).split(/\s+/).filter(Boolean);
    const filtered = words.length
      ? source.filter((o) => {
          const text = normalise(o.label);
          return words.every((w) => text.includes(w));
        })
      : source;
    return filtered.slice(0, MAX_RESULTS);
  }, [options, rows, query]);

  const pick = (option: Option | null) => {
    onChange(option ? option.value : null);
    setSelectedLabel(option ? option.label : "");
    setQuery("");
    setOpen(false);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setHighlight((h) => Math.min(h + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter" && open) {
      e.preventDefault();
      if (results[highlight]) pick(results[highlight]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={box} className={cn("relative", className)}>
      <input
        type="text"
        className="input-field pe-8"
        placeholder={selectedLabel || placeholder}
        value={open ? query : selectedLabel}
        disabled={disabled}
        onFocus={() => {
          setOpen(true);
          setHighlight(0);
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setHighlight(0);
        }}
        onKeyDown={onKey}
        autoComplete="off"
      />
      {/* Keeps the native "required" validation of the form. */}
      <input
        tabIndex={-1}
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-0 opacity-0"
        required={required}
        value={value ?? ""}
        onChange={() => undefined}
      />
      {value !== null && value !== undefined && value !== "" && !disabled && (
        <button
          type="button"
          className="absolute end-2 top-1/2 -translate-y-1/2 text-xs text-muted-c hover:text-primary-c"
          onClick={() => pick(null)}
          aria-label="Clear"
        >
          ✕
        </button>
      )}
      {open && !disabled && (
        <ul
          className="absolute z-50 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border py-1 shadow-lg"
          style={{ background: "var(--surface)", borderColor: "var(--border-color)" }}
        >
          {loading && results.length === 0 && <li className="px-3 py-2 text-xs text-muted-c">Searching…</li>}
          {!loading && results.length === 0 && <li className="px-3 py-2 text-xs text-muted-c">No result</li>}
          {results.map((option, index) => (
            <li
              key={String(option.value)}
              onMouseDown={(e) => {
                e.preventDefault();
                pick(option);
              }}
              onMouseEnter={() => setHighlight(index)}
              className={cn(
                "cursor-pointer px-3 py-1.5 text-sm text-primary-c",
                index === highlight && "bg-brand-50 dark:bg-white/5",
                String(option.value) === String(value) && "font-semibold",
              )}
            >
              {option.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
