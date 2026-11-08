import { useMemo, useState } from "react";
import { useApiList, useOptions } from "@/components/kit/hooks";
import { MONTHS } from "@/components/kit/options";
import { Card, Empty, Spinner } from "@/components/kit/ui";
import { cn } from "@/utils";

interface LeaveRow {
  id: number;
  employee: number;
  employee_name: string;
  department_name: string;
  leave_type_name: string;
  leave_type_color: string;
  start_date: string;
  end_date: string;
  effective_end_date: string;
  status: string;
}

/** BN-55: annual leave plan displayed as a calendar per team / department. */
export default function LeavePlan() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [department, setDepartment] = useState("");
  const departments = useOptions("organisation/departments/", (d) => d.name);
  const { rows, loading } = useApiList<LeaveRow>("leave/requests/plan/", { year, ...(department ? { department } : {}) });

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const days = Array.from({ length: daysInMonth }, (_, i) => new Date(year, month, i + 1));

  const byEmployee = useMemo(() => {
    const map = new Map<number, { name: string; department: string; leaves: LeaveRow[] }>();
    rows.forEach((r) => {
      const item = map.get(r.employee) || { name: r.employee_name, department: r.department_name, leaves: [] };
      item.leaves.push(r);
      map.set(r.employee, item);
    });
    return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
  }, [rows]);

  const leaveOn = (leaves: LeaveRow[], day: Date) => {
    const iso = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
    return leaves.find((l) => l.start_date <= iso && (l.effective_end_date || l.end_date) >= iso);
  };

  const legend = Array.from(new Map(rows.map((r) => [r.leave_type_name, r.leave_type_color])).entries());

  return (
    <Card
      padded={false}
      title="Leave plan"
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <select className="input-field w-auto" value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="">All departments</option>
            {departments.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
          <button type="button" className="btn-icon" onClick={() => (month === 0 ? (setMonth(11), setYear(year - 1)) : setMonth(month - 1))} aria-label="Previous month">
            ‹
          </button>
          <span className="min-w-32 text-center text-sm font-semibold text-primary-c">
            {MONTHS[month]} {year}
          </span>
          <button type="button" className="btn-icon" onClick={() => (month === 11 ? (setMonth(0), setYear(year + 1)) : setMonth(month + 1))} aria-label="Next month">
            ›
          </button>
        </div>
      }
    >
      {loading ? (
        <Spinner />
      ) : byEmployee.length === 0 ? (
        <Empty>No leave planned this year for this selection.</Empty>
      ) : (
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full min-w-max border-collapse text-xs">
            <thead>
              <tr>
                <th className="table-header-cell sticky start-0 z-1 min-w-48">Employee</th>
                {days.map((d) => (
                  <th key={d.getDate()} className={cn("table-header-cell px-0 text-center", [0, 6].includes(d.getDay()) && "opacity-50")}>
                    <span className="block w-7">{d.getDate()}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {byEmployee.map((e) => (
                <tr key={e.name} className="table-row">
                  <td className="table-cell sticky start-0 z-1" style={{ background: "var(--surface)" }}>
                    <p className="font-medium text-primary-c">{e.name}</p>
                    <p className="text-[11px] text-muted-c">{e.department}</p>
                  </td>
                  {days.map((d) => {
                    const leave = leaveOn(e.leaves, d);
                    return (
                      <td key={d.getDate()} className="border-b p-0.5" style={{ borderColor: "var(--row-divider)" }}>
                        {leave && (
                          <span
                            title={`${leave.leave_type_name} (${leave.status.toLowerCase()})`}
                            className={cn("block h-6 w-7 rounded", leave.status !== "APPROVED" && "opacity-50 ring-1 ring-inset ring-white")}
                            style={{ background: leave.leave_type_color, backgroundImage: leave.status === "SUBMITTED" ? "repeating-linear-gradient(45deg, transparent, transparent 3px, rgba(255,255,255,.4) 3px, rgba(255,255,255,.4) 6px)" : undefined }}
                          />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {legend.length > 0 && (
        <div className="flex flex-wrap gap-3 border-t px-5 py-3 text-xs text-secondary-c" style={{ borderColor: "var(--border-color)" }}>
          {legend.map(([name, color]) => (
            <span key={name} className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded" style={{ background: color }} /> {name}
            </span>
          ))}
          <span className="text-muted-c">Hatched = waiting for approval</span>
        </div>
      )}
    </Card>
  );
}
