import type { ReactNode } from "react";
import { useEffect } from "react";
import { X, Loader2 } from "lucide-react";
import PageMeta from "@/components/common/PageMeta";
import { cn } from "@/utils";

export function PageHeader({
  title,
  subtitle,
  actions,
  eyebrow,
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <>
      <PageMeta title={`${title} | Saint Jean HRMS`} description={typeof subtitle === "string" ? subtitle : title} />
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between animate-fade-in">
        <div>
          {eyebrow && <p className="section-label mb-1">{eyebrow}</p>}
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-secondary-c">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2.5">{actions}</div>}
      </div>
    </>
  );
}

export function Card({
  title,
  actions,
  children,
  className,
  padded = true,
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <section className={cn("card animate-fade-in", className)}>
      {(title || actions) && (
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3.5"
          style={{ borderColor: "var(--border-color)" }}
        >
          {title && <h2 className="text-sm font-semibold tracking-tight text-primary-c">{title}</h2>}
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={padded ? "p-5" : ""}>{children}</div>
    </section>
  );
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: ReactNode; hidden?: boolean; badge?: number | string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="tab-bar no-scrollbar mb-5">
      {tabs
        .filter((t) => !t.hidden)
        .map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange(t.id)}
            className={cn("tab-item inline-flex items-center gap-2", active === t.id && "tab-item-active")}
          >
            <span>{t.label}</span>
            {t.badge !== undefined && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                {t.badge}
              </span>
            )}
          </button>
        ))}
    </div>
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
  size = "md",
}: {
  open: boolean;
  title: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  const width = { sm: "max-w-md", md: "max-w-xl", lg: "max-w-3xl", xl: "max-w-5xl" }[size];

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={cn("modal-box", width)}>
        <div className="modal-header">
          <h3 className="text-base font-semibold tracking-tight text-primary-c">{title}</h3>
          <button
            type="button"
            className="btn-icon rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
        {footer && (
          <div
            className="sticky bottom-0 flex justify-end gap-2.5 border-t px-6 py-3.5"
            style={{ borderColor: "var(--border-color)", background: "var(--surface)" }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

const TONES: Record<string, string> = {
  green: "badge-green",
  red: "badge-red",
  yellow: "badge-yellow",
  orange: "badge-orange",
  blue: "badge-blue",
  gray: "badge-gray",
  purple: "badge-purple",
  teal: "badge-teal",
};

const DOT_TONES: Record<string, string> = {
  green: "bg-emerald-500",
  red: "bg-red-500",
  yellow: "bg-amber-500",
  orange: "bg-orange-500",
  blue: "bg-blue-500",
  gray: "bg-slate-400",
  purple: "bg-indigo-500",
  teal: "bg-teal-500",
};

/** Colour mapping of the usual statuses of the application. */
const STATUS_TONE: Record<string, string> = {
  ACTIVE: "green",
  APPROVED: "green",
  VALIDATED: "green",
  PRESENT: "green",
  PAID: "teal",
  POSTED: "teal",
  CLOSED: "gray",
  PUBLISHED: "green",
  REPAID: "gray",
  ISSUED: "green",
  OK: "green",
  DRAFT: "gray",
  OPENED: "blue",
  IN_PREPARATION: "blue",
  CALCULATED: "purple",
  VERIFIED: "teal",
  SUBMITTED: "yellow",
  PENDING: "yellow",
  MODIFICATION: "orange",
  SUSPENDED: "orange",
  INTERRUPTED: "orange",
  CONSOLIDATED: "teal",
  LOCKED: "purple",
  LEAVE: "purple",
  MISSION: "blue",
  HOLIDAY: "teal",
  REST: "gray",
  DIFFERENCE: "orange",
  FUTURE: "gray",
  NEW: "blue",
  CHANGED: "orange",
  LEFT: "gray",
  ABSENT: "red",
  REFUSED: "red",
  TERMINATED: "red",
  EXPIRED: "gray",
  CANCELLED: "gray",
  REVERSED: "red",
  ARCHIVED: "gray",
  INACTIVE: "gray",
  NOT_EMPLOYED: "gray",
  NONE: "gray",
};

export function Badge({
  children,
  tone = "gray",
  dot = false,
}: {
  children: ReactNode;
  tone?: string;
  dot?: boolean;
}) {
  return (
    <span className={TONES[tone] || "badge-gray"}>
      {dot && <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", DOT_TONES[tone] || "bg-slate-400")} />}
      {children}
    </span>
  );
}

export function StatusBadge({
  value,
  label,
  dot = true,
}: {
  value?: string | null;
  label?: string | null;
  dot?: boolean;
}) {
  if (!value) return <span className="text-muted-c">—</span>;
  const text = label || value.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
  const tone = STATUS_TONE[value] || "gray";
  return (
    <Badge tone={tone} dot={dot}>
      {text}
    </Badge>
  );
}

export function KpiTile({
  label,
  value,
  hint,
  accent = "var(--primary)",
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  accent?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="stat-card kpi-tile animate-fade-in" style={{ ["--kpi-accent" as any]: accent }}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="section-label">{label}</p>
          <p className="kpi-value mt-2 truncate">{value}</p>
          {hint && <p className="mt-1 text-xs text-muted-c">{hint}</p>}
        </div>
        {icon && (
          <span
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl shadow-xs"
            style={{
              background: `color-mix(in srgb, ${accent} 12%, transparent)`,
              color: accent,
            }}
          >
            {icon}
          </span>
        )}
      </div>
    </div>
  );
}

export function Empty({ children = "Nothing to show yet." }: { children?: ReactNode }) {
  return (
    <div className="py-12 text-center text-sm text-muted-c">
      <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800">
        <span className="text-lg">∅</span>
      </div>
      {children}
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2.5 py-10 text-sm text-muted-c">
      <Loader2 className="h-5 w-5 animate-spin text-indigo-600 dark:text-indigo-400" />
      <span>{label}</span>
    </div>
  );
}

export function Field({
  label,
  children,
  hint,
  required,
  className,
}: {
  label: ReactNode;
  children: ReactNode;
  hint?: ReactNode;
  required?: boolean;
  className?: string;
}) {
  return (
    <label className={cn("block", className)}>
      <span className="field-label">
        {label}
        {required && <span className="text-red-500"> *</span>}
      </span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted-c">{hint}</span>}
    </label>
  );
}

export function Banner({
  tone = "info",
  children,
}: {
  tone?: "info" | "error" | "success" | "warning";
  children: ReactNode;
}) {
  return <div className={`${tone}-banner`}>{children}</div>;
}

export function DefinitionList({ items }: { items: [ReactNode, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3.5 sm:grid-cols-2">
      {items.map(([k, v], i) => (
        <div key={i} className="flex flex-col">
          <dt className="section-label">{k}</dt>
          <dd className="mt-0.5 text-sm font-medium text-primary-c">{v ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}
