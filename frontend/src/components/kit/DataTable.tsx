import type { ReactNode } from "react";
import { cn } from "@/utils";
import { Empty, Spinner } from "./ui";

export interface Column<T> {
  key: string;
  header: ReactNode;
  render?: (row: T) => ReactNode;
  align?: "start" | "end" | "center";
  className?: string;
  mono?: boolean;
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
}

function value(row: any, key: string) {
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
  dense,
}: Props<T>) {
  const allIds = rows.map(rowKey);
  const allSelected = selectable && allIds.length > 0 && allIds.every((id) => selected.includes(id));
  const toggle = (id: string | number) =>
    onSelect?.(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  const align = (a?: string) => (a === "end" ? "text-end" : a === "center" ? "text-center" : "text-start");

  return (
    <div className="max-w-full overflow-x-auto custom-scrollbar">
      <table className="w-full min-w-max border-collapse">
        <thead>
          <tr>
            {selectable && (
              <th className="table-header-cell w-8">
                <input
                  type="checkbox"
                  checked={!!allSelected}
                  onChange={() => onSelect?.(allSelected ? [] : allIds)}
                  aria-label="Select all"
                />
              </th>
            )}
            {columns.map((c) => (
              <th key={c.key} className={cn("table-header-cell", align(c.align), c.className)}>
                {c.header}
              </th>
            ))}
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
            rows.map((row) => {
              const id = rowKey(row);
              return (
                <tr
                  key={id}
                  className={cn("table-row transition-colors", onRowClick && "cursor-pointer", rowClassName?.(row))}
                  onClick={() => onRowClick?.(row)}
                >
                  {selectable && (
                    <td className="table-cell" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" checked={selected.includes(id)} onChange={() => toggle(id)} aria-label="Select" />
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
  );
}
