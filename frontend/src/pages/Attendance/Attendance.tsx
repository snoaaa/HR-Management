import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, firstOfMonthISO, fmt, todayISO } from "@/api/helpers";
import CrudSection, { ExportButtons } from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { FormModal, PromptModal } from "@/components/kit/Form";
import { useApiList, useHashTab, useOptions } from "@/components/kit/hooks";
import {
  MONTHS,
  WEEKDAYS,
  departmentField,
  employeeField,
  positionField,
  siteField,
} from "@/components/kit/options";
import { Banner, Card, PageHeader, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";
import ScheduleEditor from "./ScheduleEditor";

interface Day {
  id: number;
  employee: number;
  employee_name: string;
  date: string;
  status: string;
  status_label: string;
  expected_minutes: number;
  worked_minutes: number;
  late_minutes: number;
  early_departure_minutes: number;
  missing_minutes: number;
  overtime_minutes: number;
  overtime_day_minutes: number;
  overtime_night_minutes: number;
  overtime_rest_day_minutes: number;
  overtime_holiday_minutes: number;
  overtime_status: string;
  absence_justified: boolean;
  absence_justification: string;
  open_clocking: boolean;
}

function Filters({ value, onChange, extra }: { value: Record<string, string>; onChange: (v: Record<string, string>) => void; extra?: React.ReactNode }) {
  const departments = useOptions("organisation/departments/", (d) => d.name);
  return (
    <div className="flex flex-wrap items-end gap-2 border-b p-4" style={{ borderColor: "var(--border-color)" }}>
      <label>
        <span className="field-label">From</span>
        <input type="date" className="input-field" value={value.start} onChange={(e) => onChange({ ...value, start: e.target.value })} />
      </label>
      <label>
        <span className="field-label">To</span>
        <input type="date" className="input-field" value={value.end} onChange={(e) => onChange({ ...value, end: e.target.value })} />
      </label>
      <label>
        <span className="field-label">Department</span>
        <select className="input-field" value={value.department || ""} onChange={(e) => onChange({ ...value, department: e.target.value })}>
          <option value="">All</option>
          {departments.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
      </label>
      {extra}
    </div>
  );
}

function DailyAttendance({ overtimeOnly = false }: { overtimeOnly?: boolean }) {
  const [filters, setFilters] = useState<Record<string, string>>({
    start: firstOfMonthISO(),
    end: todayISO(),
    department: "",
    status: "",
    overtime_status: overtimeOnly ? "PENDING" : "",
  });
  const params: Record<string, string> = { date__gte: filters.start, date__lte: filters.end };
  if (filters.department) params.employee__department = filters.department;
  if (filters.status) params.status = filters.status;
  if (filters.overtime_status) params.overtime_status = filters.overtime_status;
  const { rows, loading, reload } = useApiList<Day>("attendance/days/", params);
  const [selected, setSelected] = useState<(string | number)[]>([]);
  const [justify, setJustify] = useState<Day | null>(null);
  const { can } = usePermissions();
  const toast = useToast();

  const decide = async (decision: "APPROVED" | "REFUSED") => {
    try {
      const res = await api.post("attendance/days/decide_overtime/", { ids: selected, decision });
      toast.success(`${res.data.decided} day(s) ${decision.toLowerCase()}`);
      setSelected([]);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  const recompute = async () => {
    try {
      const res = await api.post("attendance/days/recompute/", { start: filters.start, end: filters.end });
      toast.success(`${res.data.computed_days} day(s) computed`);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <Card padded={false}>
      <Filters
        value={filters}
        onChange={setFilters}
        extra={
          <>
            <label>
              <span className="field-label">Status</span>
              <select className="input-field" value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
                <option value="">All</option>
                {["PRESENT", "ABSENT", "LEAVE", "MISSION", "HOLIDAY", "REST", "SUSPENDED"].map((s) => (
                  <option key={s} value={s}>
                    {s.toLowerCase()}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="field-label">Overtime</span>
              <select className="input-field" value={filters.overtime_status} onChange={(e) => setFilters({ ...filters, overtime_status: e.target.value })}>
                <option value="">All</option>
                <option value="PENDING">To approve</option>
                <option value="APPROVED">Approved</option>
                <option value="REFUSED">Refused</option>
              </select>
            </label>
            <div className="ms-auto flex flex-wrap gap-2">
              {can("attendance", "modify") && (
                <button type="button" className="btn-secondary" onClick={recompute}>
                  ↻ Recompute
                </button>
              )}
              {can("attendance", "validate") && (
                <>
                  <button type="button" className="btn-teal" disabled={!selected.length} onClick={() => decide("APPROVED")}>
                    Approve overtime ({selected.length})
                  </button>
                  <button type="button" className="btn-danger" disabled={!selected.length} onClick={() => decide("REFUSED")}>
                    Refuse
                  </button>
                </>
              )}
            </div>
          </>
        }
      />
      <DataTable<Day>
        rows={rows}
        loading={loading}
        selectable={can("attendance", "validate")}
        selected={selected}
        onSelect={setSelected}
        dense
        empty="No computed day for this selection. Use “Recompute” after recording clockings."
        columns={[
          { key: "date", header: "Date", render: (d) => fmt.date(d.date) },
          { key: "employee_name", header: "Employee", render: (d) => <span className="font-medium text-primary-c">{d.employee_name}</span> },
          { key: "status", header: "Status", render: (d) => (
            <span className="flex items-center gap-1">
              <StatusBadge value={d.status} label={d.status_label} />
              {d.open_clocking && <span className="badge-orange" title="Entry without exit">open</span>}
            </span>
          ) },
          { key: "expected_minutes", header: "Expected", align: "end", mono: true, render: (d) => fmt.minutes(d.expected_minutes) },
          { key: "worked_minutes", header: "Worked", align: "end", mono: true, render: (d) => fmt.minutes(d.worked_minutes) },
          { key: "late_minutes", header: "Late", align: "end", mono: true, render: (d) => (d.late_minutes ? <span className="text-sap-critical">{d.late_minutes} min</span> : "—") },
          { key: "missing_minutes", header: "Missing", align: "end", mono: true, render: (d) => fmt.minutes(d.missing_minutes) },
          {
            key: "overtime_minutes",
            header: "Overtime",
            align: "end",
            render: (d) =>
              d.overtime_minutes ? (
                <span className="flex flex-col items-end">
                  <span className="mono text-primary-c">{fmt.minutes(d.overtime_minutes)}</span>
                  <StatusBadge value={d.overtime_status} />
                </span>
              ) : (
                "—"
              ),
          },
          {
            key: "absence",
            header: "Absence",
            render: (d) =>
              d.status === "ABSENT" ? (
                d.absence_justified ? (
                  <span className="badge-green" title={d.absence_justification}>justified</span>
                ) : can("attendance", "modify") ? (
                  <button type="button" className="btn-ghost text-xs text-sap-negative" onClick={() => setJustify(d)}>
                    Unjustified – qualify
                  </button>
                ) : (
                  <span className="badge-red">unjustified</span>
                )
              ) : null,
          },
        ]}
      />
      <PromptModal
        open={!!justify}
        title="Qualify the absence (BN-41)"
        message={justify ? `${justify.employee_name} – ${fmt.date(justify.date)}. A justified absence is not deducted from the salary.` : ""}
        commentLabel="Justification"
        commentRequired
        confirmLabel="Mark as justified"
        onClose={() => setJustify(null)}
        onConfirm={async (v) => {
          await api.post(`attendance/days/${justify!.id}/justify/`, { justified: true, justification: v.comment });
          reload();
        }}
      />
    </Card>
  );
}

function Clockings() {
  const [report, setReport] = useState<any>(null);
  const [day, setDay] = useState(todayISO());
  const toast = useToast();
  const upload = async (file: File | null) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await api.post("attendance/clockings/import/", form, { headers: { "Content-Type": "multipart/form-data" } });
      setReport(res.data);
      toast.success(`${res.data.imported} clocking(s) imported`);
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <div className="space-y-4">
      <Card title="Import a badge / biometric file (BN-37, BN-180)">
        <div className="flex flex-wrap items-center gap-3">
          <input type="file" accept=".csv,.txt" className="input-field max-w-sm" onChange={(e) => upload(e.target.files?.[0] || null)} />
          <p className="text-xs text-muted-c">
            CSV with <span className="mono">matriculation;date;time_in;time_out</span> or <span className="mono">matriculation;timestamp;direction</span> (IN / OUT).
          </p>
        </div>
        {report && (
          <div className="mt-4 space-y-2">
            <Banner tone={report.rejected.length ? "warning" : "success"}>
              {report.imported} line(s) imported, {report.rejected.length} rejected.
            </Banner>
            {report.rejected.length > 0 && (
              <DataTable
                rows={report.rejected}
                rowKey={(r: any) => `${r.line}-${r.reason}`}
                columns={[
                  { key: "line", header: "Line", mono: true },
                  { key: "reason", header: "Reason of the rejection" },
                  { key: "data", header: "Data", render: (r: any) => <span className="mono text-xs">{Object.values(r.data || {}).join(" ; ")}</span> },
                ]}
              />
            )}
          </div>
        )}
      </Card>
      <div className="flex items-center gap-2">
        <span className="field-label mb-0">Day</span>
        <input type="date" className="input-field w-44" value={day} onChange={(e) => setDay(e.target.value)} />
      </div>
      <CrudSection
        endpoint="attendance/clockings/"
        params={{ date: day }}
        title="Entries and exits"
        description="Manual entry by HR (BN-37). A deleted or regularised clocking stays visible but inactive (BN-44)."
        canEdit={(c: any) => c.is_active}
        canDelete={(c: any) => c.is_active}
        columns={[
          { key: "employee_name", header: "Employee", render: (c: any) => <span className="font-medium text-primary-c">{c.employee_name}</span> },
          { key: "time_in", header: "In", mono: true, render: (c: any) => c.time_in?.slice(0, 5) },
          { key: "time_out", header: "Out", mono: true, render: (c: any) => c.time_out?.slice(0, 5) || <span className="badge-orange">open</span> },
          { key: "source_label", header: "Source" },
          { key: "is_active", header: "State", render: (c: any) => (c.is_active ? <span className="badge-green">active</span> : <span className="badge-gray">replaced</span>) },
        ]}
        fields={[
          employeeField(),
          { name: "date", label: "Date", type: "date", required: true },
          { name: "time_in", label: "Entry", type: "time", required: true },
          { name: "time_out", label: "Exit", type: "time" },
        ]}
        defaults={{ date: day }}
        toForm={(c: any) => ({ ...c, time_in: c.time_in?.slice(0, 5), time_out: c.time_out?.slice(0, 5) })}
      />
    </div>
  );
}

function Sheet() {
  const [filters, setFilters] = useState<Record<string, string>>({ start: firstOfMonthISO(), end: todayISO(), department: "", granularity: "monthly" });
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
  const { rows, loading } = useApiList<any>("attendance/sheet/", params);
  return (
    <Card padded={false}>
      <Filters
        value={filters}
        onChange={setFilters}
        extra={
          <>
            <label>
              <span className="field-label">Grouping</span>
              <select className="input-field" value={filters.granularity} onChange={(e) => setFilters({ ...filters, granularity: e.target.value })}>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </label>
            <div className="ms-auto">
              <ExportButtons url="attendance/sheet/" params={params} />
            </div>
          </>
        }
      />
      <DataTable
        rows={rows}
        loading={loading}
        dense
        rowKey={(r: any) => `${r.employee_id}-${r.period}`}
        columns={[
          { key: "employee", header: "Employee", render: (r: any) => <span className="font-medium text-primary-c">{r.employee}</span> },
          { key: "department", header: "Department" },
          { key: "period", header: "Period", mono: true },
          ...(filters.granularity === "daily" ? [{ key: "status", header: "Status" }] : []),
          { key: "expected_hours", header: "Expected h", align: "end", mono: true },
          { key: "worked_hours", header: "Worked h", align: "end", mono: true },
          { key: "late_minutes", header: "Late min", align: "end", mono: true },
          { key: "missing_hours", header: "Missing h", align: "end", mono: true },
          { key: "overtime_hours", header: "Overtime h", align: "end", mono: true },
          { key: "absent_days", header: "Absences", align: "end", mono: true },
          { key: "unjustified_absent_days", header: "Unjustified", align: "end", mono: true },
          { key: "leave_days", header: "Leave", align: "end", mono: true },
        ]}
      />
    </Card>
  );
}

function Periods() {
  const { rows, reload } = useApiList<any>("attendance/periods/");
  const [open, setOpen] = useState(false);
  const now = new Date();
  return (
    <>
      <div className="mb-3 flex justify-end">
        <button type="button" className="btn-primary" onClick={() => setOpen(true)}>
          Consolidate a month
        </button>
      </div>
      <Card padded={false}>
        <DataTable
          rows={rows}
          empty="No consolidated period. Periods are locked automatically when the payroll is validated (BN-45)."
          columns={[
            { key: "period", header: "Period", render: (p: any) => `${MONTHS[p.month - 1]} ${p.year}` },
            { key: "status", header: "Status", render: (p: any) => <StatusBadge value={p.status} /> },
            { key: "employees", header: "Employees", align: "end", mono: true, render: (p: any) => p.summary?.employees },
            { key: "absences", header: "Absences", align: "end", mono: true, render: (p: any) => p.summary?.absences },
            { key: "unjustified", header: "Unjustified", align: "end", mono: true, render: (p: any) => p.summary?.unjustified_absences },
            { key: "pending_overtime", header: "Overtime to approve", align: "end", mono: true, render: (p: any) => p.summary?.pending_overtime },
            { key: "consolidated_at", header: "Consolidated", render: (p: any) => fmt.datetime(p.consolidated_at) },
            { key: "locked_at", header: "Locked", render: (p: any) => fmt.datetime(p.locked_at) },
          ]}
        />
      </Card>
      <FormModal
        open={open}
        title="Consolidate the attendance"
        size="sm"
        fields={[
          { name: "year", label: "Year", type: "number", required: true },
          { name: "month", label: "Month", type: "select", required: true, options: MONTHS.map((m, i) => ({ value: i + 1, label: m })) },
        ]}
        initial={{ year: now.getFullYear(), month: now.getMonth() + 1 }}
        onClose={() => setOpen(false)}
        onSaved={reload}
        onSubmit={(p) => api.post("attendance/periods/consolidate/", { year: Number(p.year), month: Number(p.month) })}
        submitLabel="Consolidate"
      />
    </>
  );
}

function Configuration() {
  const [section, setSection] = useState("calendars");
  return (
    <>
      <div className="mb-4 flex flex-wrap gap-2">
        {[
          ["calendars", "Calendars & holidays"],
          ["schedules", "Schedule models"],
          ["assignments", "Assignments"],
          ["exceptions", "Exceptions"],
        ].map(([id, label]) => (
          <button key={id} type="button" className={section === id ? "btn-primary btn-sm" : "btn-secondary btn-sm"} onClick={() => setSection(id)}>
            {label}
          </button>
        ))}
      </div>
      {section === "calendars" && (
        <div className="space-y-6">
          <CrudSection
            endpoint="attendance/calendars/"
            title="Working calendars (BN-61, BN-08)"
            description="Weekly rest days per site; the calendar without site is the default one."
            columns={[
              { key: "name", header: "Name" },
              { key: "site_name", header: "Site", render: (c: any) => c.site_name || <span className="badge-purple">default</span> },
              { key: "rest_days", header: "Rest days", render: (c: any) => (c.rest_days || []).map((d: number) => WEEKDAYS[d]).join(", ") },
            ]}
            fields={[
              { name: "name", label: "Name", required: true },
              siteField(),
              { name: "rest_days", label: "Rest days (0 = Monday … 6 = Sunday)", type: "json", hint: "e.g. [5, 6] for Saturday and Sunday", rows: 2 },
            ]}
            defaults={{ rest_days: [5, 6] }}
          />
          <CrudSection
            endpoint="attendance/holidays/"
            title="Public holidays"
            description="Recurring holidays come back every year; add movable religious holidays each year."
            columns={[
              { key: "name", header: "Holiday" },
              { key: "date", header: "Date", render: (h: any) => (h.recurring ? new Date(h.date).toLocaleDateString("en-GB", { day: "numeric", month: "long" }) : fmt.date(h.date)) },
              { key: "recurring", header: "Every year", render: (h: any) => (h.recurring ? <span className="badge-teal">yes</span> : "no") },
              { key: "site_name", header: "Site", render: (h: any) => h.site_name || "All sites" },
            ]}
            fields={[
              { name: "name", label: "Name", required: true },
              { name: "date", label: "Date", type: "date", required: true },
              { name: "recurring", label: "Recurring", type: "checkbox" },
              siteField("site", "Only for site"),
            ]}
          />
        </div>
      )}
      {section === "schedules" && <ScheduleEditor />}
      {section === "assignments" && (
        <CrudSection
          endpoint="attendance/assignments/"
          title="Schedule assignments (BN-60)"
          description="Assign a schedule to an employee, a position, a team or a site. The most specific assignment applies; without target it applies to the whole organisation."
          columns={[
            { key: "schedule_name", header: "Schedule" },
            { key: "target_label", header: "Applies to" },
            { key: "effective_from", header: "From", render: (a: any) => fmt.date(a.effective_from) },
            { key: "effective_to", header: "To", render: (a: any) => fmt.date(a.effective_to) },
          ]}
          fields={[
            { name: "schedule", label: "Schedule", type: "select", required: true, optionsUrl: "attendance/schedules/", optionLabel: (s) => s.name },
            { ...employeeField("employee", "Employee", false) },
            positionField(),
            departmentField(),
            siteField(),
            { name: "effective_from", label: "From", type: "date", required: true },
            { name: "effective_to", label: "To", type: "date" },
          ]}
        />
      )}
      {section === "exceptions" && (
        <CrudSection
          endpoint="attendance/exceptions/"
          title="Exceptions (BN-60)"
          description="Other hours or a day off for one employee on one day."
          columns={[
            { key: "employee_name", header: "Employee" },
            { key: "date", header: "Date", render: (e: any) => fmt.date(e.date) },
            { key: "hours", header: "Hours", render: (e: any) => (e.is_day_off ? <span className="badge-gray">day off</span> : `${e.start_time?.slice(0, 5)} → ${e.end_time?.slice(0, 5)}`) },
            { key: "reason", header: "Reason" },
          ]}
          fields={[
            employeeField(),
            { name: "date", label: "Date", type: "date", required: true },
            { name: "is_day_off", label: "Day off", type: "checkbox" },
            { name: "start_time", label: "Start", type: "time", hidden: (v) => !!v.is_day_off },
            { name: "end_time", label: "End", type: "time", hidden: (v) => !!v.is_day_off },
            { name: "break_minutes", label: "Break (min)", type: "number", hidden: (v) => !!v.is_day_off },
            { name: "reason", label: "Reason" },
          ]}
        />
      )}
    </>
  );
}

export default function Attendance() {
  const [tab, setTab] = useHashTab("days");
  const { can } = usePermissions();
  const hr = can("attendance", "modify");
  return (
    <>
      <PageHeader eyebrow="Time & absence" title="Attendance & time tracking" subtitle="Entries and exits, lateness, overtime and absences (M-05)." />
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "days", label: "Daily attendance" },
          { id: "overtime", label: "Overtime to approve", hidden: !can("attendance", "validate") },
          { id: "clockings", label: "Clockings", hidden: !hr },
          { id: "regularisations", label: "Regularisations" },
          { id: "missions", label: "Missions" },
          { id: "sheet", label: "Attendance sheet" },
          { id: "periods", label: "Periods", hidden: !hr },
          { id: "configuration", label: "Calendars & schedules", hidden: !can("planning", "modify") },
        ]}
      />
      {tab === "days" && <DailyAttendance key="days" />}
      {tab === "overtime" && <DailyAttendance key="overtime" overtimeOnly />}
      {tab === "clockings" && <Clockings />}
      {tab === "regularisations" && (
        <CrudSection
          endpoint="attendance/regularisations/"
          title="Clocking regularisations (BN-44)"
          description="A forgotten or wrong clocking is corrected after approval of the line manager; the original stays visible."
          canEdit={false}
          canDelete={false}
          createLabel="+ Request a regularisation"
          columns={[
            { key: "employee_name", header: "Employee" },
            { key: "date", header: "Date", render: (r: any) => fmt.date(r.date) },
            { key: "hours", header: "Proposed", mono: true, render: (r: any) => `${r.time_in?.slice(0, 5)} → ${r.time_out?.slice(0, 5) || "…"}` },
            { key: "justification", header: "Justification" },
            { key: "status", header: "Status", render: (r: any) => <StatusBadge value={r.status} /> },
            { key: "decision_comment", header: "Comment" },
          ]}
          fields={[
            employeeField(),
            { name: "date", label: "Date", type: "date", required: true },
            { name: "time_in", label: "Entry", type: "time", required: true },
            { name: "time_out", label: "Exit", type: "time" },
            { name: "justification", label: "Justification", type: "textarea", required: true },
          ]}
        />
      )}
      {tab === "missions" && (
        <CrudSection
          endpoint="attendance/missions/"
          title="Missions and field work (BN-43)"
          canCreate={hr}
          canEdit={hr}
          canDelete={hr}
          columns={[
            { key: "employee_name", header: "Employee" },
            { key: "start_date", header: "From", render: (m: any) => fmt.date(m.start_date) },
            { key: "end_date", header: "To", render: (m: any) => fmt.date(m.end_date) },
            { key: "place", header: "Place" },
            { key: "purpose", header: "Purpose" },
          ]}
          fields={[
            employeeField(),
            { name: "start_date", label: "From", type: "date", required: true },
            { name: "end_date", label: "To", type: "date", required: true },
            { name: "place", label: "Place", required: true },
            { name: "purpose", label: "Purpose", required: true },
          ]}
        />
      )}
      {tab === "sheet" && <Sheet />}
      {tab === "periods" && <Periods />}
      {tab === "configuration" && <Configuration />}
    </>
  );
}
