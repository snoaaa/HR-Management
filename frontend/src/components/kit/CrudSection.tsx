import { useState } from "react";
import type { ReactNode } from "react";
import api from "@/api/axiosConfig";
import { apiError, downloadFile } from "@/api/helpers";
import { useToast } from "@/context/ToastContext";
import DataTable from "./DataTable";
import type { Column } from "./DataTable";
import { FormModal } from "./Form";
import type { FieldDef } from "./Form";
import { useApiList } from "./hooks";

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
  createLabel = "+ New",
  defaults,
  toForm,
  rowActions = [],
  toolbar,
  onRowClick,
  modalSize = "md",
  emptyText,
  filter,
}: Props<T>) {
  const { rows, loading, reload } = useApiList<T>(endpoint, params);
  const [editing, setEditing] = useState<T | null>(null);
  const [creating, setCreating] = useState(false);
  const toast = useToast();

  const allowed = (rule: boolean | ((row: T) => boolean), row: T) => (typeof rule === "function" ? rule(row) : rule);

  const remove = async (row: T) => {
    if (!window.confirm("Delete this item?")) return;
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
                    className={a.tone === "danger" ? "btn-ghost text-error-600" : "btn-ghost text-brand-600 dark:text-brand-300"}
                    onClick={() => a.onClick(row, reload)}
                  >
                    {a.label}
                  </button>
                ))}
              {fields.length > 0 && allowed(canEdit, row) && (
                <button type="button" className="btn-ghost text-brand-600 dark:text-brand-300" onClick={() => setEditing(row)}>
                  Edit
                </button>
              )}
              {allowed(canDelete, row) && (
                <button type="button" className="btn-ghost text-error-600" onClick={() => remove(row)}>
                  Delete
                </button>
              )}
            </div>
          ),
        },
      ]
    : columns;

  const visible = filter ? rows.filter(filter) : rows;

  return (
    <div className="space-y-3">
      {(title || description || canCreate || toolbar) && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            {title && <h3 className="text-sm font-semibold text-primary-c">{title}</h3>}
            {description && <p className="text-xs text-muted-c">{description}</p>}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {toolbar?.(reload, rows)}
            {canCreate && fields.length > 0 && (
              <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
                {createLabel}
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
    <div className="inline-flex overflow-hidden rounded-lg border" style={{ borderColor: "var(--border-color)" }}>
      {formats.map((f) => (
        <button key={f} type="button" className="btn-ghost rounded-none px-3 text-xs uppercase" onClick={() => run(f)}>
          ⤓ {f}
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
}: {
  url: string;
  label: ReactNode;
  params?: Record<string, unknown>;
  method?: "get" | "post";
  data?: unknown;
  className?: string;
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
    <button type="button" className={className} onClick={run} disabled={busy}>
      {busy ? "Preparing…" : label}
    </button>
  );
}
