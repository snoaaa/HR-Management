import { isValidElement, useState } from "react";
import { DownloadIcon } from "@/icons";
import type { ReactNode } from "react";
import { downloadFile } from "@/api/helpers";
import { useToast } from "@/context/ToastContext";
import type { Column } from "./DataTable";

/** Visible text of a rendered cell (badges, formatted amounts, links…). */
export function nodeText(node: ReactNode): string {
  if (node === null || node === undefined || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(nodeText).join("");
  if (isValidElement(node)) {
    const props = node.props as Record<string, any>;
    // Buttons and inputs are actions, not data.
    if (node.type === "button" || node.type === "input" || props.onClick) return "";
    if (props.children !== undefined) return nodeText(props.children);
    if (props.label !== undefined) return nodeText(props.label);
    if (props.value !== undefined) return nodeText(props.value);
  }
  return "";
}

function rawValue(row: any, key: string) {
  return key.split(".").reduce((acc, part) => (acc == null ? acc : acc[part]), row);
}

function cell<T>(column: Column<T>, row: T): string | number {
  const raw = rawValue(row, column.key);
  const text = (column.render ? nodeText(column.render(row)) : raw == null ? "" : String(raw)).trim();
  // Keep real numbers numeric (Excel sums, right-aligned in the PDF).
  const number = typeof raw === "number" ? raw : typeof raw === "string" && /^-?\d+(\.\d+)?$/.test(raw) ? Number(raw) : null;
  if (number !== null) {
    const digits = text.replace(/[^0-9.,-]/g, "").replace(",", ".");
    if (!text || text === "—" || Number(digits) === number) return number;
  }
  return text === "—" ? "" : text;
}

/** Headers and rows of the displayed columns (the action columns are left out). */
export function tableData<T>(columns: Column<T>[], rows: T[]) {
  const kept = columns.filter((c) => !c.key.startsWith("__") && nodeText(c.header).trim() !== "");
  return {
    headers: kept.map((c) => nodeText(c.header).trim()),
    rows: rows.map((row) => kept.map((c) => cell(c, row))),
  };
}

/** PDF (colours of the organisation) and Excel extraction of a displayed list. */
export function TableExportButtons<T>({ title, subtitle, columns, rows }: {
  title: string;
  subtitle?: string;
  columns: Column<T>[];
  rows: T[];
}) {
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  const run = async (format: "pdf" | "xlsx") => {
    setBusy(format);
    try {
      await downloadFile("exports/table/", {
        method: "post",
        data: { title, subtitle, file_format: format, ...tableData(columns, rows) },
        open: format === "pdf",
      });
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <div className="inline-flex overflow-hidden rounded-xl border" style={{ borderColor: "var(--border-strong)", background: "var(--surface)" }} title="Download the displayed list">
      <button type="button" className="btn-ghost rounded-none px-3" disabled={!rows.length || !!busy} onClick={() => run("pdf")}>
        <DownloadIcon className="size-4" /> {busy === "pdf" ? "…" : "PDF"}
      </button>
      <button type="button" className="btn-ghost rounded-none border-s px-3" style={{ borderColor: "var(--border-color)" }} disabled={!rows.length || !!busy} onClick={() => run("xlsx")}>
        <DownloadIcon className="size-4" /> {busy === "xlsx" ? "…" : "Excel"}
      </button>
    </div>
  );
}
