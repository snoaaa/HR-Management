import { useState } from "react";
import { confirmDialog } from "./confirm";
import { DownloadIcon, PlusIcon, SearchIcon } from "@/icons";
import type { ReactNode } from "react";
import api from "@/api/axiosConfig";
import { apiError, downloadFile } from "@/api/helpers";
import { useToast } from "@/context/ToastContext";
import DataTable from "./DataTable";
import type { Column } from "./DataTable";
import { FormModal } from "./Form";
import type { FieldDef } from "./Form";
import { useApiList } from "./hooks";
import { TableExportButtons } from "./tableExport";

export interface RowAction<T> {
  label: string;
  onClick: (row: T, reload: () => void) => void;
  show?: (row: T) => boolean;
  tone?: "danger" | "primary";
}

interface Props<T> {
  endpoint: string;
  columns: Column<T>[];
  fields?: FieldDef[];
  params?: Record<string, unknown>;
  title?: ReactNode;
  description?: ReactNode;
  canCreate?: boolean;
  canEdit?: boolean | ((row: T) => boolean);
  canDelete?: boolean | ((row: T) => boolean);
  createLabel?: string;
  defaults?: Record<string, any>;
  /** Build the initial values of the edit form from a row. */
  toForm?: (row: T) => Record<string, any>;
  rowActions?: RowAction<T>[];
  toolbar?: (reload: () => void, rows: T[]) => ReactNode;
  onRowClick?: (row: T) => void;
  modalSize?: "sm" | "md" | "lg" | "xl";
  emptyText?: ReactNode;
  filter?: (row: T) => boolean;
  /** Show a search box filtering the rows on every displayed value. */
  searchable?: boolean;
  /** Title of the PDF / Excel extraction (defaults to the section title; false hides it). */
  exportTitle?: string | false;
}

export function matchesSearch(row: unknown, query: string) {
  const words = normalise(query).split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  const text = normalise(JSON.stringify(row));
  return words.every((w) => text.includes(w));
}

function normalise(text: string) {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");
}

/** A complete list / create / edit / delete section configured by props. */
export default function CrudSection<T extends { id?: number | string }>({
  endpoint,
  columns,
  fields = [],
  params,
  title,
  description,
  canCreate = true,
  canEdit = true,
  canDelete = true,
  createLabel = "New",
  defaults,
  toForm,
  rowActions = [],
  toolbar,
  onRowClick,
  modalSize = "md",
  emptyText,
  filter,
  searchable = true,
  exportTitle,
}: Props<T>) {
  const [search, setSearch] = useState("");
  const { rows, loading, reload } = useApiList<T>(endpoint, params);
  const [editing, setEditing] = useState<T | null>(null);
  const [creating, setCreating] = useState(false);
  const toast = useToast();

  const allowed = (rule: boolean | ((row: T) => boolean), row: T) => (typeof rule === "function" ? rule(row) : rule);

  const remove = async (row: T) => {
    if (!(await confirmDialog({ title: "Delete this item?", message: "It will be removed permanently. This cannot be undone.", confirmLabel: "Delete", danger: true }))) return;
    try {
      await api.delete(`${endpoint}${row.id}/`);
      toast.success("Deleted");
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  const hasActions = fields.length > 0 && (canEdit || canDelete) || rowActions.length > 0;
  const allColumns: Column<T>[] = hasActions
    ? [
        ...columns,
        {
          key: "__actions",
          header: "",
          align: "end",
          render: (row) => (
            <div className="flex justify-end gap-1" onClick={(e) => e.stopPropagation()}>
              {rowActions
                .filter((a) => !a.show || a.show(row))
                .map((a) => (
                  <button
                    key={a.label}
                    type="button"
                    className={a.tone === "danger" ? "btn-ghost text-error-600 dark:text-error-400" : "btn-ghost text-brand-c"}
                    onClick={() => a.onClick(row, reload)}
                  >
                    {a.label}
                  </button>
                ))}
              {fields.length > 0 && allowed(canEdit, row) && (
                <button type="button" className="btn-soft" onClick={() => setEditing(row)}>
                  Edit
                </button>
              )}
              {allowed(canDelete, row) && (
                <button type="button" className="btn-ghost text-error-600 dark:text-error-400" onClick={() => remove(row)}>
                  Delete
                </button>
              )}
            </div>
          ),
        },
      ]
    : columns;

  const visible = (filter ? rows.filter(filter) : rows).filter((row) => matchesSearch(row, search));

  return (
    <div className="space-y-4">
      {(title || description || canCreate || toolbar || searchable || exportTitle) && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            {title && <h3 className="text-base font-semibold text-primary-c">{title}</h3>}
            {description && <p className="mt-0.5 text-[13px] text-muted-c">{description}</p>}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {searchable && (
              <label className="search-box">
                <SearchIcon />
                <input
                  type="search"
                  className="input-field w-64"
                  placeholder="Search by name, code…"
                  aria-label="Search this list"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </label>
            )}
            {toolbar?.(reload, rows)}
            {exportTitle !== false && (exportTitle || typeof title === "string") && (
              <TableExportButtons title={(exportTitle || title) as string} columns={columns} rows={visible} />
            )}
            {canCreate && fields.length > 0 && (
              <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
                <PlusIcon className="size-4" />
                {createLabel.replace(/^\+\s*/, "")}
              </button>
            )}
          </div>
        </div>
      )}
      <div className="card overflow-hidden">
        <DataTable columns={allColumns} rows={visible} loading={loading} onRowClick={onRowClick} empty={emptyText} />
      </div>
      <FormModal
        open={creating}
        title={typeof title === "string" ? `New – ${title}` : "New"}
        fields={fields}
        initial={defaults}
        endpoint={endpoint}
        onClose={() => setCreating(false)}
        onSaved={reload}
        size={modalSize}
      />
      <FormModal
        open={!!editing}
        title={typeof title === "string" ? `Edit – ${title}` : "Edit"}
        fields={fields}
        initial={editing ? (toForm ? toForm(editing) : (editing as any)) : undefined}
        endpoint={endpoint}
        id={editing?.id}
        onClose={() => setEditing(null)}
        onSaved={reload}
        size={modalSize}
      />
    </div>
  );
}

/** Buttons exporting a list in several formats (BN-126). */
export function ExportButtons({ url, params, formats = ["xlsx", "csv", "pdf"] }: {
  url: string;
  params?: Record<string, unknown>;
  formats?: ("csv" | "xlsx" | "pdf")[];
}) {
  const toast = useToast();
  const run = async (format: string) => {
    try {
      await downloadFile(url, { params: { ...params, file_format: format }, open: format === "pdf" });
    } catch (err: any) {
      toast.error(err.message);
    }
  };
  return (
    <div className="inline-flex overflow-hidden rounded-xl border" style={{ borderColor: "var(--border-strong)", background: "var(--surface)" }}>
      {formats.map((f) => (
        <button key={f} type="button" className="btn-ghost rounded-none border-e px-3 last:border-e-0" style={{ borderColor: "var(--border-color)" }} onClick={() => run(f)}>
          <DownloadIcon className="size-4" /> {f === "xlsx" ? "Excel" : f.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

/** Button opening or downloading a document produced by the API. */
export function DownloadButton({
  url,
  label,
  params,
  method,
  data,
  className = "btn-secondary",
  disabled,
}: {
  url: string;
  label: ReactNode;
  params?: Record<string, unknown>;
  method?: "get" | "post";
  data?: unknown;
  className?: string;
  disabled?: boolean;
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try {
      await downloadFile(url, { params, method, data });
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <button type="button" className={className} onClick={run} disabled={busy || disabled}>
      {busy ? "Preparing…" : label}
    </button>
  );
}
