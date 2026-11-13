import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { AngleDownIcon, AngleUpIcon } from "@/icons";
import { cn } from "@/utils";
import { TableExportButtons, nodeText } from "./tableExport";
import { Empty, Spinner } from "./ui";

export interface Column<T> {
  key: string;
  header: ReactNode;
  render?: (row: T) => ReactNode;
  align?: "start" | "end" | "center";
  className?: string;
  mono?: boolean;
  /** Set to false to forbid sorting on this column. */
  sortable?: boolean;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  loading?: boolean;
  empty?: ReactNode;
  rowKey?: (row: T) => string | number;
  onRowClick?: (row: T) => void;
  selectable?: boolean;
  selected?: (string | number)[];
  onSelect?: (ids: (string | number)[]) => void;
  rowClassName?: (row: T) => string;
  footer?: ReactNode;
  dense?: boolean;
  /** Title of the PDF / Excel extraction of the displayed rows (shows the buttons). */
  exportTitle?: string;
  exportSubtitle?: string;
  /** Rows per page; 0 shows every row. Lists longer than one page get a pager. */
  pageSize?: number;
  /** Click on a column header to sort (on by default). */
  sortable?: boolean;
}

const PAGE_SIZES = [10, 25, 50, 100];

function value(row: any, key: string) {
  return key.split(".").reduce((acc, part) => (acc == null ? acc : acc[part]), row);
}

/** Value used to order the rows of a column: the raw field, else the displayed text. */
function sortValue<T>(column: Column<T>, row: T): string | number {
  const raw = value(row, column.key);
  if (typeof raw === "number") return raw;
  if (typeof raw === "boolean") return raw ? 1 : 0;
  if (typeof raw === "string" && raw !== "") {
    return /^-?\d+(\.\d+)?$/.test(raw) ? Number(raw) : raw.toLowerCase();
  }
  return column.render ? nodeText(column.render(row)).trim().toLowerCase() : "";
}

export default function DataTable<T>({
  columns,
  rows,
  loading,
  empty,
  rowKey = (r: any) => r.id,
  onRowClick,
  selectable,
  selected = [],
  onSelect,
  rowClassName,
  footer,
  dense,
  exportTitle,
  exportSubtitle,
  pageSize = 25,
  sortable = true,
}: Props<T>) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(pageSize);

  const sorted = useMemo(() => {
    const column = sort && columns.find((c) => c.key === sort.key);
    if (!sort || !column) return rows;
    return [...rows].sort((a, b) => {
      const x = sortValue(column, a);
      const y = sortValue(column, b);
      if (x === y) return 0;
      if (x === "") return 1; // empty values stay at the end
      if (y === "") return -1;
      const order = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true });
      return order * sort.dir;
    });
  }, [rows, sort, columns]);

  const paged = size > 0 && sorted.length > size;
  const pageCount = paged ? Math.ceil(sorted.length / size) : 1;
  const current = Math.min(page, pageCount - 1);
  const shown = paged ? sorted.slice(current * size, current * size + size) : sorted;

  useEffect(() => setPage(0), [rows.length, sort?.key, sort?.dir, size]);

  const allIds = rows.map(rowKey);
  const allSelected = selectable && allIds.length > 0 && allIds.every((id) => selected.includes(id));
  const toggle = (id: string | number) =>
    onSelect?.(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  const align = (a?: string) => (a === "end" ? "text-end" : a === "center" ? "text-center" : "text-start");
  const canSort = (c: Column<T>) => sortable && c.sortable !== false && !c.key.startsWith("__") && nodeText(c.header).trim() !== "";
  const toggleSort = (key: string) =>
    setSort((prev) => (prev?.key !== key ? { key, dir: 1 } : prev.dir === 1 ? { key, dir: -1 } : null));

  return (
    <>
      {exportTitle && !loading && rows.length > 0 && (
        <div className="flex items-center justify-between gap-3 border-b px-4 py-2.5" style={{ borderColor: "var(--border-color)" }}>
          <span className="text-xs text-muted-c">
            {rows.length} {rows.length === 1 ? "result" : "results"}
          </span>
          <TableExportButtons title={exportTitle} subtitle={exportSubtitle} columns={columns} rows={sorted} />
        </div>
      )}
      <div className="custom-scrollbar max-w-full overflow-x-auto">
        <table className="w-full min-w-max border-collapse">
          <thead>
            <tr>
              {selectable && (
                <th className="table-header-cell w-8">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-brand-500"
                    checked={!!allSelected}
                    onChange={() => onSelect?.(allSelected ? [] : allIds)}
                    aria-label="Select all"
                  />
                </th>
              )}
              {columns.map((c) => {
                const active = sort?.key === c.key;
                return (
                  <th
                    key={c.key}
                    className={cn("table-header-cell", align(c.align), c.className)}
                    aria-sort={active ? (sort.dir === 1 ? "ascending" : "descending") : undefined}
                  >
                    {canSort(c) ? (
                      <button
                        type="button"
                        onClick={() => toggleSort(c.key)}
                        title="Click to sort"
                        className={cn(
                          "group inline-flex items-center gap-1 font-semibold transition-colors hover:text-(--text-primary)",
                          active && "text-(--brand-strong)",
                        )}
                      >
                        {c.header}
                        {active && sort.dir === -1 ? (
                          <AngleDownIcon className="size-3.5" />
                        ) : (
                          <AngleUpIcon className={cn("size-3.5", !active && "opacity-0 group-hover:opacity-50")} />
                        )}
                      </button>
                    ) : (
                      c.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0)}>
                  <Spinner />
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0)}>
                  <Empty>{empty}</Empty>
                </td>
              </tr>
            ) : (
              shown.map((row) => {
                const id = rowKey(row);
                return (
                  <tr
                    key={id}
                    className={cn("table-row transition-colors", onRowClick && "cursor-pointer", rowClassName?.(row))}
                    onClick={() => onRowClick?.(row)}
                  >
                    {selectable && (
                      <td className="table-cell" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-brand-500"
                          checked={selected.includes(id)}
                          onChange={() => toggle(id)}
                          aria-label="Select"
                        />
                      </td>
                    )}
                    {columns.map((c) => {
                      const content = c.render ? c.render(row) : value(row, c.key);
                      return (
                        <td
                          key={c.key}
                          className={cn("table-cell", dense && "py-2", align(c.align), c.mono && "mono", c.className)}
                        >
                          {content === null || content === undefined || content === "" ? "—" : (content as ReactNode)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
          {footer && <tfoot>{footer}</tfoot>}
        </table>
      </div>
      {paged && !loading && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-2.5 text-[13px] text-secondary-c" style={{ borderColor: "var(--border-color)" }}>
          <span>
            Showing <strong className="text-primary-c">{current * size + 1}–{Math.min((current + 1) * size, sorted.length)}</strong> of{" "}
            <strong className="text-primary-c">{sorted.length}</strong>
          </span>
          <div className="flex items-center gap-2">
            <label className="hidden items-center gap-2 sm:flex">
              Rows per page
              <select
                className="input-field !min-h-8 !w-auto !py-1 !text-[13px]"
                value={size}
                onChange={(e) => setSize(Number(e.target.value))}
                aria-label="Rows per page"
              >
                {PAGE_SIZES.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className="btn-secondary btn-sm" disabled={current === 0} onClick={() => setPage(current - 1)}>
              Previous
            </button>
            <span className="px-1">
              Page {current + 1} / {pageCount}
            </span>
            <button type="button" className="btn-secondary btn-sm" disabled={current >= pageCount - 1} onClick={() => setPage(current + 1)}>
              Next
            </button>
          </div>
        </div>
      )}
    </>
  );
}
