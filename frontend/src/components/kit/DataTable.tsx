import type { ReactNode } from "react";
import { useState, useMemo } from "react";
import {
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Search,
  X,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
} from "lucide-react";
import { cn } from "@/utils";
import { Empty } from "./ui";

export interface Column<T> {
  key: string;
  header: ReactNode;
  render?: (row: T) => ReactNode;
  align?: "start" | "end" | "center";
  className?: string;
  mono?: boolean;
  sortable?: boolean;
  /** Custom sort comparator function if default string/number compare isn't enough */
  sortFn?: (a: T, b: T) => number;
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
  /** Enable client-side search across column values */
  searchable?: boolean;
  searchPlaceholder?: string;
  /** Enable client-side pagination */
  pagination?: boolean;
  defaultPageSize?: number;
  pageSizeOptions?: number[];
  /** Optional toolbar extra actions */
  toolbarActions?: ReactNode;
}

function getNestedValue(row: any, key: string) {
  if (!row) return undefined;
  return key.split(".").reduce((acc, part) => (acc == null ? acc : acc[part]), row);
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
  dense: initialDense = false,
  searchable = true,
  searchPlaceholder = "Search records…",
  pagination = true,
  defaultPageSize = 25,
  pageSizeOptions = [10, 25, 50, 100],
  toolbarActions,
}: Props<T>) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);
  const [isDense, setIsDense] = useState(initialDense);

  const align = (a?: string) => (a === "end" ? "text-end" : a === "center" ? "text-center" : "text-start");

  // Handle Sort Toggle
  const handleSort = (key: string, column: Column<T>) => {
    if (column.sortable === false) return;
    if (sortKey === key) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else {
        setSortKey(null);
        setSortDirection("asc");
      }
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  // Filter Rows
  const filteredRows = useMemo(() => {
    if (!searchTerm.trim()) return rows;
    const term = searchTerm.toLowerCase();
    return rows.filter((row) =>
      columns.some((col) => {
        const val = getNestedValue(row, col.key);
        if (val == null) return false;
        return String(val).toLowerCase().includes(term);
      }),
    );
  }, [rows, searchTerm, columns]);

  // Sort Rows
  const sortedRows = useMemo(() => {
    if (!sortKey) return filteredRows;
    const col = columns.find((c) => c.key === sortKey);
    const sorted = [...filteredRows];

    if (col?.sortFn) {
      sorted.sort((a, b) => (sortDirection === "asc" ? col.sortFn!(a, b) : col.sortFn!(b, a)));
    } else {
      sorted.sort((a, b) => {
        const valA = getNestedValue(a, sortKey);
        const valB = getNestedValue(b, sortKey);
        if (valA == null && valB == null) return 0;
        if (valA == null) return 1;
        if (valB == null) return -1;
        if (typeof valA === "number" && typeof valB === "number") {
          return sortDirection === "asc" ? valA - valB : valB - valA;
        }
        return sortDirection === "asc"
          ? String(valA).localeCompare(String(valB))
          : String(valB).localeCompare(String(valA));
      });
    }
    return sorted;
  }, [filteredRows, sortKey, sortDirection, columns]);

  // Paginate Rows
  const totalItems = sortedRows.length;
  const totalPages = pagination ? Math.max(1, Math.ceil(totalItems / pageSize)) : 1;
  const currentPage = Math.min(page, totalPages);

  const displayedRows = useMemo(() => {
    if (!pagination) return sortedRows;
    const start = (currentPage - 1) * pageSize;
    return sortedRows.slice(start, start + pageSize);
  }, [sortedRows, pagination, currentPage, pageSize]);

  // Checkbox selections
  const allCurrentIds = displayedRows.map(rowKey);
  const allSelected =
    selectable && allCurrentIds.length > 0 && allCurrentIds.every((id) => selected.includes(id));

  const toggleSelectAll = () => {
    if (!onSelect) return;
    if (allSelected) {
      onSelect(selected.filter((id) => !allCurrentIds.includes(id)));
    } else {
      const merged = Array.from(new Set([...selected, ...allCurrentIds]));
      onSelect(merged);
    }
  };

  const toggleOne = (id: string | number) => {
    if (!onSelect) return;
    onSelect(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  };

  const showToolbar = (searchable && rows.length > 0) || toolbarActions;

  return (
    <div className="flex flex-col gap-3">
      {/* ── DataTable Control Toolbar ── */}
      {showToolbar && (
        <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between px-1">
          <div className="flex items-center gap-2">
            {searchable && (
              <div className="relative min-w-[220px] max-w-sm flex-1 sm:w-72">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setPage(1);
                  }}
                  placeholder={searchPlaceholder}
                  className="input-field pl-9 pr-8 text-xs py-1.5"
                />
                {searchTerm && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchTerm("");
                      setPage(1);
                    }}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                    aria-label="Clear search"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto">
            {toolbarActions}
            <button
              type="button"
              onClick={() => setIsDense((d) => !d)}
              title={isDense ? "Comfortable density" : "Compact density"}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 shadow-2xs hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800",
                isDense && "border-indigo-300 bg-indigo-50 text-indigo-700 dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300",
              )}
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{isDense ? "Compact" : "Normal"}</span>
            </button>
          </div>
        </div>
      )}

      {/* ── Table Container ── */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs dark:border-slate-800 dark:bg-slate-950">
        <div className="max-w-full overflow-x-auto custom-scrollbar">
          <table className="w-full min-w-max border-collapse">
            <thead>
              <tr>
                {selectable && (
                  <th className="table-header-cell w-10 text-center">
                    <input
                      type="checkbox"
                      checked={!!allSelected}
                      onChange={toggleSelectAll}
                      className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                      aria-label="Select all"
                    />
                  </th>
                )}
                {columns.map((c) => {
                  const isCurrentSort = sortKey === c.key;
                  const canSort = c.sortable !== false;
                  return (
                    <th
                      key={c.key}
                      onClick={() => handleSort(c.key, c)}
                      className={cn(
                        "table-header-cell transition-colors",
                        canSort && "cursor-pointer select-none hover:bg-slate-100 dark:hover:bg-slate-800/60",
                        align(c.align),
                        c.className,
                      )}
                    >
                      <div
                        className={cn(
                          "inline-flex items-center gap-1.5",
                          c.align === "end" && "flex-row-reverse",
                        )}
                      >
                        <span>{c.header}</span>
                        {canSort && (
                          <span className="text-slate-400">
                            {isCurrentSort ? (
                              sortDirection === "asc" ? (
                                <ChevronUp className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                              ) : (
                                <ChevronDown className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                              )
                            ) : (
                              <ChevronsUpDown className="h-3.5 w-3.5 opacity-40 hover:opacity-100" />
                            )}
                          </span>
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                // Shimmer Skeleton Loading
                Array.from({ length: 6 }).map((_, rIdx) => (
                  <tr key={`skel-${rIdx}`} className="border-b border-slate-100 dark:border-slate-800/60">
                    {selectable && (
                      <td className="table-cell w-10 text-center">
                        <div className="mx-auto h-4 w-4 rounded bg-slate-200 dark:bg-slate-800 skeleton-shimmer" />
                      </td>
                    )}
                    {columns.map((_, cIdx) => (
                      <td key={`skel-c-${cIdx}`} className={cn("table-cell", isDense ? "py-2.5" : "py-3.5")}>
                        <div
                          className="h-3.5 rounded bg-slate-200 dark:bg-slate-800 skeleton-shimmer"
                          style={{
                            width: `${Math.max(45, ((rIdx + cIdx * 7) % 5) * 15 + 40)}%`,
                          }}
                        />
                      </td>
                    ))}
                  </tr>
                ))
              ) : displayedRows.length === 0 ? (
                <tr>
                  <td colSpan={columns.length + (selectable ? 1 : 0)}>
                    <Empty>{empty || "No records match the current filters."}</Empty>
                  </td>
                </tr>
              ) : (
                displayedRows.map((row) => {
                  const id = rowKey(row);
                  const isSelected = selected.includes(id);
                  return (
                    <tr
                      key={id}
                      className={cn(
                        "table-row cursor-default",
                        onRowClick && "cursor-pointer",
                        isSelected && "bg-indigo-50/50 dark:bg-indigo-950/20",
                        rowClassName?.(row),
                      )}
                      onClick={() => onRowClick?.(row)}
                    >
                      {selectable && (
                        <td className="table-cell w-10 text-center" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleOne(id)}
                            className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                            aria-label="Select row"
                          />
                        </td>
                      )}
                      {columns.map((c) => {
                        const content = c.render ? c.render(row) : getNestedValue(row, c.key);
                        return (
                          <td
                            key={c.key}
                            className={cn(
                              "table-cell",
                              isDense ? "py-2" : "py-3",
                              align(c.align),
                              c.mono && "mono",
                              c.className,
                            )}
                          >
                            {content === null || content === undefined || content === "" ? (
                              <span className="text-slate-300 dark:text-slate-600">—</span>
                            ) : (
                              (content as ReactNode)
                            )}
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

        {/* ── Pagination Footer ── */}
        {pagination && totalItems > 0 && !loading && (
          <div className="flex flex-col gap-3 border-t border-slate-200 bg-slate-50/70 px-4 py-3 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900/40">
            <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
              <span>
                Showing <strong className="text-slate-700 dark:text-slate-200">{(currentPage - 1) * pageSize + 1}</strong> to{" "}
                <strong className="text-slate-700 dark:text-slate-200">{Math.min(currentPage * pageSize, totalItems)}</strong> of{" "}
                <strong className="text-slate-700 dark:text-slate-200">{totalItems}</strong> entries
              </span>
              <div className="flex items-center gap-1.5">
                <span>Per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setPage(1);
                  }}
                  className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                >
                  {pageSizeOptions.map((sz) => (
                    <option key={sz} value={sz}>
                      {sz}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center gap-1 self-end sm:self-auto">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
                className="btn-icon h-8 w-8 rounded-md border border-slate-200 bg-white text-slate-600 disabled:opacity-30 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-300"
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <div className="flex items-center gap-1 px-2 text-xs font-medium text-slate-700 dark:text-slate-300">
                <span>Page</span>
                <span className="font-semibold text-indigo-600 dark:text-indigo-400">{currentPage}</span>
                <span>of</span>
                <span>{totalPages}</span>
              </div>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages}
                className="btn-icon h-8 w-8 rounded-md border border-slate-200 bg-white text-slate-600 disabled:opacity-30 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-300"
                aria-label="Next page"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
