import { useState } from "react";
import { useNavigate } from "react-router";
import { fmt } from "@/api/helpers";
import CrudSection from "@/components/kit/CrudSection";
import { useHashTab } from "@/components/kit/hooks";
import { departmentField, employeeField } from "@/components/kit/options";
import { PageHeader, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";

/** M-07 – timetables, shifts and shift exchanges (BN-62 → BN-67). */
export default function Planning() {
  const [tab, setTab] = useHashTab("timetables");
  const navigate = useNavigate();
  const { can } = usePermissions();
  const manage = can("planning", "modify");
  const [refresh] = useState(0);

  return (
    <>
      <PageHeader title="Planning" eyebrow="Time & absence" subtitle="Build, publish and compare the timetables of the teams." />
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "timetables", label: "Timetables" },
          { id: "shifts", label: "Shifts" },
          { id: "swaps", label: "Shift exchanges" },
        ]}
      />
      {tab === "timetables" && (
        <CrudSection
          key={refresh}
          endpoint="planning/timetables/"
          title="Timetables"
          description="Click a timetable to edit its grid."
          canCreate={manage}
          canEdit={(t: any) => manage && t.status === "DRAFT"}
          canDelete={(t: any) => manage && t.status === "DRAFT"}
          onRowClick={(t: any) => navigate(`/planning/${t.id}`)}
          fields={[
            { name: "name", label: "Name", required: true, full: true },
            departmentField("department", "Team / department", true),
            { name: "start_date", label: "From", type: "date", required: true },
            { name: "end_date", label: "To", type: "date", required: true, hint: "At most two months." },
          ]}
          columns={[
            { key: "name", header: "Name", render: (t: any) => <span className="font-medium text-primary-c">{t.name}</span> },
            { key: "department_name", header: "Team" },
            { key: "start_date", header: "Period", render: (t: any) => `${fmt.date(t.start_date)} → ${fmt.date(t.end_date)}` },
            { key: "entries_count", header: "Assignments", align: "end" },
            { key: "status", header: "Status", render: (t: any) => <StatusBadge value={t.status} /> },
          ]}
        />
      )}
      {tab === "shifts" && (
        <CrudSection
          endpoint="planning/shifts/"
          title="Shifts"
          canCreate={manage}
          canEdit={manage}
          canDelete={manage}
          fields={[
            { name: "code", label: "Code", required: true },
            { name: "name", label: "Name", required: true },
            { name: "start_time", label: "Start", type: "time", required: true },
            { name: "end_time", label: "End", type: "time", required: true, hint: "Before the start = ends the next day." },
            { name: "break_minutes", label: "Break (minutes)", type: "number" },
            { name: "color", label: "Colour", type: "color" },
            { name: "is_active", label: "Active", type: "checkbox" },
          ]}
          defaults={{ break_minutes: 30, color: "#00A09D", is_active: true }}
          columns={[
            { key: "code", header: "Code", mono: true },
            { key: "name", header: "Name", render: (s: any) => (
              <span className="inline-flex items-center gap-2">
                <span className="h-3 w-3 rounded-sm" style={{ background: s.color }} />
                {s.name}
              </span>
            ) },
            { key: "start_time", header: "Hours", render: (s: any) => `${String(s.start_time).slice(0, 5)} – ${String(s.end_time).slice(0, 5)}` },
            { key: "duration_minutes", header: "Duration", render: (s: any) => fmt.minutes(s.duration_minutes) },
          ]}
        />
      )}
      {tab === "swaps" && (
        <CrudSection
          endpoint="planning/swaps/"
          title="Shift exchanges"
          description="Approved by the line manager in the approvals inbox."
          canEdit={false}
          canDelete={false}
          createLabel="+ Request an exchange"
          fields={[
            {
              name: "entry",
              label: "Shift to give",
              type: "select",
              required: true,
              optionsUrl: "planning/entries/",
              optionLabel: (e: any) => `${e.employee_name} – ${e.date} ${e.shift_name}`,
              full: true,
            },
            employeeField("replacement", "Replaced by"),
            {
              name: "swap_with",
              label: "Shift taken in exchange (optional)",
              type: "select",
              optionsUrl: "planning/entries/",
              optionLabel: (e: any) => `${e.employee_name} – ${e.date} ${e.shift_name}`,
              full: true,
            },
            { name: "reason", label: "Reason", required: true, full: true },
          ]}
          columns={[
            { key: "entry_detail.date", header: "Date", render: (s: any) => fmt.date(s.entry_detail?.date) },
            { key: "entry_detail.shift_name", header: "Shift" },
            { key: "entry_detail.employee_name", header: "From" },
            { key: "replacement_name", header: "To" },
            { key: "reason", header: "Reason" },
            { key: "status", header: "Status", render: (s: any) => <StatusBadge value={s.status} /> },
          ]}
        />
      )}
    </>
  );
}
