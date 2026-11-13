import type { ReactNode } from "react";
import { Empty } from "./ui";

/**
 * Flat charts in the palette of the logo (no gradients): horizontal bar lists and
 * vertical bar series, readable in light and dark mode.
 */
export const CHART_COLORS = ["#FA5A05", "#1D6FD6", "#12805C", "#E01A16", "#8A93A3", "#FFA35C", "#364152"];

export interface Datum {
  label: ReactNode;
  value: number | string;
}

export function BarList({ data, format = (v: number) => v.toLocaleString("fr-FR"), color = CHART_COLORS[0] }: {
  data: Datum[];
  format?: (value: number) => ReactNode;
  color?: string;
}) {
  if (!data.length) return <Empty />;
  const max = Math.max(...data.map((d) => Number(d.value) || 0), 1);
  return (
    <ul className="space-y-3">
      {data.map((d, index) => {
        const value = Number(d.value) || 0;
        return (
          <li key={index} className="text-sm">
            <div className="mb-1 flex justify-between gap-3">
              <span className="truncate text-secondary-c">{d.label}</span>
              <span className="mono font-semibold text-primary-c">{format(value)}</span>
            </div>
            <div className="h-2.5 rounded-full" style={{ background: "var(--surface-3)" }}>
              <div className="h-2.5 rounded-full" style={{ width: `${(value / max) * 100}%`, background: color }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function ColumnChart({ data, height = 180, format = (v: number) => v.toLocaleString("fr-FR"), series }: {
  data: Record<string, any>[];
  height?: number;
  format?: (value: number) => ReactNode;
  /** Keys plotted as grouped bars (default: "value"). */
  series?: { key: string; label: string; color?: string }[];
}) {
  const keys = series || [{ key: "value", label: "", color: CHART_COLORS[0] }];
  if (!data.length) return <Empty />;
  const max = Math.max(...data.flatMap((d) => keys.map((k) => Number(d[k.key]) || 0)), 1);
  return (
    <div>
      <div className="flex items-end gap-2 overflow-x-auto pb-1" style={{ height }}>
        {data.map((d, i) => (
          <div key={i} className="flex min-w-[2.5rem] flex-1 flex-col items-center justify-end gap-1" style={{ height: "100%" }}>
            <div className="flex w-full flex-1 items-end justify-center gap-0.5">
              {keys.map((k, j) => {
                const value = Number(d[k.key]) || 0;
                return (
                  <div
                    key={k.key}
                    title={`${k.label} ${format(value)}`}
                    className="w-full max-w-[1.75rem] rounded-t"
                    style={{ height: `${(value / max) * 100}%`, minHeight: value ? 2 : 0,
                      background: k.color || CHART_COLORS[j % CHART_COLORS.length] }}
                  />
                );
              })}
            </div>
            <span className="truncate text-[10px] text-muted-c">{d.label}</span>
          </div>
        ))}
      </div>
      {series && series.length > 1 && (
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-secondary-c">
          {series.map((k, j) => (
            <span key={k.key} className="inline-flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: k.color || CHART_COLORS[j % CHART_COLORS.length] }} />
              {k.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
