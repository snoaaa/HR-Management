import type { ReactNode } from "react";
import { useEffect } from "react";
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
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between animate-fade-in">
        <div>
          {eyebrow && <p className="section-label mb-1">{eyebrow}</p>}
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-secondary-c">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </>
  );
}

export function Card({ title, actions, children, className, padded = true }: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <section className={cn("card animate-fade-in", className)}>
      {(title || actions) && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b px-5 py-3.5" style={{ borderColor: "var(--border-color)" }}>
          {title && <h2 className="text-sm font-semibold text-primary-c">{title}</h2>}
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={padded ? "p-5" : ""}>{children}</div>
    </section>
  );
}

export function Tabs({ tabs, active, onChange }: { tabs: { id: string; label: ReactNode; hidden?: boolean }[]; active: string; onChange: (id: string) => void }) {
  return (
    <div className="tab-bar no-scrollbar mb-5">
      {tabs
        .filter((t) => !t.hidden)
        .map((t) => (
          <button key={t.id} type="button" onClick={() => onChange(t.id)} className={cn("tab-item", active === t.id && "tab-item-active")}>
            {t.label}
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
          <h3 className="text-base font-semibold text-primary-c">{title}</h3>
          <button type="button" className="btn-icon" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
        {footer && (
          <div className="sticky bottom-0 flex justify-end gap-2 border-t px-6 py-3" style={{ borderColor: "var(--border-color)", background: "var(--surface)" }}>
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

/** Colour of the usual statuses of the application. */
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

export function Badge({ children, tone = "gray" }: { children: ReactNode; tone?: string }) {
  return <span className={TONES[tone] || "badge-gray"}>{children}</span>;
}

export function StatusBadge({ value, label }: { value?: string | null; label?: string | null }) {
  if (!value) return <span className="text-muted-c">—</span>;
  const text = label || value.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
  return <Badge tone={STATUS_TONE[value] || "gray"}>{text}</Badge>;
}

export function KpiTile({ label, value, hint, accent = "var(--odoo-purple)", icon }: {
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
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white" style={{ background: accent }}>
            {icon}
          </span>
        )}
      </div>
    </div>
  );
}

export function Empty({ children = "Nothing to show yet." }: { children?: ReactNode }) {
  return <div className="py-10 text-center text-sm text-muted-c">{children}</div>;
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-c">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-200 border-t-brand-500" />
      {label}
    </div>
  );
}

export function Field({ label, children, hint, required, className }: {
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
        {required && <span className="text-error-500"> *</span>}
      </span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted-c">{hint}</span>}
    </label>
  );
}

export function Banner({ tone = "info", children }: { tone?: "info" | "error" | "success" | "warning"; children: ReactNode }) {
  return <div className={`${tone}-banner`}>{children}</div>;
}

export function DefinitionList({ items }: { items: [ReactNode, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
      {items.map(([k, v], i) => (
        <div key={i} className="flex flex-col">
          <dt className="section-label">{k}</dt>
          <dd className="mt-0.5 text-sm text-primary-c">{v ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}
