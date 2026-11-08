import { useState } from "react";
import api from "@/api/axiosConfig";
import { fmt } from "@/api/helpers";
import { FormModal } from "@/components/kit/Form";
import type { FieldDef } from "@/components/kit/Form";
import { useApiList } from "@/components/kit/hooks";
import { WEEKDAYS } from "@/components/kit/options";
import { Card, StatusBadge } from "@/components/kit/ui";

interface Day {
  weekday: number;
  start_time: string;
  end_time: string;
  break_minutes: number;
  expected_minutes?: number;
}
interface Schedule {
  id: number;
  code: string;
  name: string;
  schedule_type: string;
  flexible_daily_minutes: number;
  is_active: boolean;
  weekly_minutes: number;
  days: Day[];
}

const TYPES = [
  { value: "FIXED", label: "Fixed hours" },
  { value: "FLEXIBLE", label: "Flexible hours" },
  { value: "SHIFT", label: "Rotating shifts (timetable)" },
  { value: "PART_TIME", label: "Part time" },
];

const FIELDS: FieldDef[] = [
  { name: "code", label: "Code", required: true },
  { name: "name", label: "Name", required: true },
  { name: "schedule_type", label: "Type", type: "select", options: TYPES, required: true },
  { name: "flexible_daily_minutes", label: "Flexible: minutes per day", type: "number", hidden: (v) => v.schedule_type !== "FLEXIBLE" },
  { name: "is_active", label: "Active", type: "checkbox" },
];

/** BN-59: work schedule models with their daily hours and breaks. */
export default function ScheduleEditor() {
  const { rows, reload } = useApiList<Schedule>("attendance/schedules/");
  const [editing, setEditing] = useState<Schedule | null | undefined>(undefined);
  const [days, setDays] = useState<Day[]>([]);

  const open = (s: Schedule | null) => {
    setDays(
      s?.days?.length
        ? s.days.map((d) => ({ ...d, start_time: d.start_time.slice(0, 5), end_time: d.end_time.slice(0, 5) }))
        : [0, 1, 2, 3, 4].map((w) => ({ weekday: w, start_time: "08:00", end_time: "17:00", break_minutes: 60 })),
    );
    setEditing(s);
  };

  const setDay = (index: number, patch: Partial<Day>) => setDays((prev) => prev.map((d, i) => (i === index ? { ...d, ...patch } : d)));

  return (
    <>
      <div className="mb-3 flex justify-end">
        <button type="button" className="btn-primary" onClick={() => open(null)}>
          + New schedule
        </button>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {rows.map((s) => (
          <Card
            key={s.id}
            title={
              <span className="flex items-center gap-2">
                {s.name} <span className="mono text-xs text-muted-c">{s.code}</span>
              </span>
            }
            actions={
              <>
                <StatusBadge value={s.is_active ? "ACTIVE" : "INACTIVE"} />
                <button type="button" className="btn-ghost" onClick={() => open(s)}>
                  Edit
                </button>
              </>
            }
          >
            <p className="mb-2 text-xs text-muted-c">
              {TYPES.find((t) => t.value === s.schedule_type)?.label} · {fmt.minutes(s.weekly_minutes)} per week
            </p>
            <div className="grid grid-cols-7 gap-1">
              {WEEKDAYS.map((name, w) => {
                const day = s.days.find((d) => d.weekday === w);
                return (
                  <div
                    key={name}
                    className="rounded-md px-1 py-1.5 text-center text-[11px]"
                    style={{ background: day ? "var(--odoo-teal-light)" : "var(--surface-3)" }}
                  >
                    <p className="font-semibold text-primary-c">{name.slice(0, 3)}</p>
                    <p className="mono text-muted-c">{day ? `${day.start_time.slice(0, 5)}` : "rest"}</p>
                    {day && <p className="mono text-muted-c">{day.end_time.slice(0, 5)}</p>}
                  </div>
                );
              })}
            </div>
          </Card>
        ))}
      </div>
      {editing !== undefined && (
        <FormModal
          open
          title={editing ? `Schedule ${editing.code}` : "New schedule"}
          fields={FIELDS}
          initial={editing || { schedule_type: "FIXED", is_active: true }}
          size="lg"
          onClose={() => setEditing(undefined)}
          onSaved={reload}
          onSubmit={(payload) => {
            const body = { ...payload, days: days.map((d) => ({ ...d, break_minutes: Number(d.break_minutes) || 0 })) };
            return editing ? api.put(`attendance/schedules/${editing.id}/`, body) : api.post("attendance/schedules/", body);
          }}
          intro={
            <div>
              <p className="section-label mb-2">Working days</p>
              <div className="space-y-1.5">
                {days.map((d, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-2">
                    <select className="input-field w-36" value={d.weekday} onChange={(e) => setDay(i, { weekday: Number(e.target.value) })}>
                      {WEEKDAYS.map((name, w) => (
                        <option key={name} value={w}>
                          {name}
                        </option>
                      ))}
                    </select>
                    <input type="time" className="input-field w-28" value={d.start_time} onChange={(e) => setDay(i, { start_time: e.target.value })} />
                    <span className="text-muted-c">→</span>
                    <input type="time" className="input-field w-28" value={d.end_time} onChange={(e) => setDay(i, { end_time: e.target.value })} />
                    <input type="number" className="input-field w-24" value={d.break_minutes} onChange={(e) => setDay(i, { break_minutes: Number(e.target.value) })} />
                    <span className="text-xs text-muted-c">min break</span>
                    <button type="button" className="btn-icon" onClick={() => setDays((p) => p.filter((_, k) => k !== i))} aria-label="Remove">
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="btn-ghost mt-2"
                onClick={() => setDays((p) => [...p, { weekday: 5, start_time: "08:00", end_time: "12:00", break_minutes: 0 }])}
              >
                + Add a day
              </button>
            </div>
          }
        />
      )}
    </>
  );
}
