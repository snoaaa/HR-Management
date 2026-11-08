import { useState } from "react";
import { fmt } from "@/api/helpers";
import CrudSection, { ExportButtons } from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { useApiList, useHashTab } from "@/components/kit/hooks";
import { employeeField } from "@/components/kit/options";
import { Card, PageHeader, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import LeavePlan from "./LeavePlan";
import LeaveRequestForm from "./LeaveRequestForm";
import LeaveRequestsTable from "./LeaveRequestsTable";
import type { LeaveRequest } from "./LeaveRequestsTable";

function Requests() {
  const [status, setStatus] = useState("SUBMITTED");
  const [creating, setCreating] = useState(false);
  const { can } = usePermissions();
  const { rows, loading, reload } = useApiList<LeaveRequest>("leave/requests/", status ? { status } : undefined);
  return (
    <Card
      padded={false}
      title="Requests"
      actions={
        <>
          <select className="input-field w-auto" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            <option value="SUBMITTED">Waiting for approval</option>
            <option value="APPROVED">Approved</option>
            <option value="INTERRUPTED">Interrupted</option>
            <option value="REFUSED">Refused</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
          {can("leave", "modify") && (
            <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
              + Request for an employee
            </button>
          )}
        </>
      }
    >
      <LeaveRequestsTable rows={rows} loading={loading} reload={reload} />
      <LeaveRequestForm open={creating} onClose={() => setCreating(false)} onSaved={reload} forEmployee />
    </Card>
  );
}

function Balances() {
  const year = new Date().getFullYear();
  const { rows, loading } = useApiList<any>("leave/requests/balances/", { year });
  const { can } = usePermissions();
  return (
    <Card padded={false} title={`Balances ${year} (BN-49)`} actions={can("leave", "export") && <ExportButtons url="leave/requests/balances/" params={{ year }} />}>
      <DataTable
        rows={rows}
        loading={loading}
        rowKey={(r: any) => r.employee}
        columns={[
          { key: "employee_name", header: "Employee", render: (r: any) => <span className="font-medium text-primary-c">{r.employee_name}</span> },
          { key: "matriculation", header: "Matriculation", mono: true },
          { key: "department", header: "Department" },
          { key: "carried_over", header: "Carried over", align: "end", mono: true, render: (r: any) => fmt.number(r.carried_over) },
          { key: "acquired", header: "Acquired", align: "end", mono: true, render: (r: any) => fmt.number(r.acquired) },
          { key: "taken", header: "Taken", align: "end", mono: true, render: (r: any) => fmt.number(r.taken) },
          { key: "pending", header: "Pending", align: "end", mono: true, render: (r: any) => fmt.number(r.pending) },
          { key: "remaining", header: "Remaining", align: "end", mono: true, render: (r: any) => <b className="text-primary-c">{fmt.number(r.remaining)}</b> },
        ]}
      />
    </Card>
  );
}

function Configuration() {
  return (
    <div className="space-y-8">
      <CrudSection
        endpoint="leave/types/"
        title="Leave and absence types (BN-46, BN-47)"
        modalSize="lg"
        columns={[
          {
            key: "name",
            header: "Type",
            render: (t: any) => (
              <span className="flex items-center gap-2">
                <span className="h-3 w-3 rounded" style={{ background: t.color }} />
                <span className="font-medium text-primary-c">{t.name}</span>
                <span className="mono text-[11px] text-muted-c">{t.code}</span>
              </span>
            ),
          },
          { key: "is_paid", header: "Paid", render: (t: any) => (t.is_paid ? <span className="badge-green">paid</span> : <span className="badge-red">unpaid</span>) },
          { key: "consumes_entitlement", header: "Uses balance", render: (t: any) => (t.consumes_entitlement ? "yes" : "no") },
          { key: "counting_rule", header: "Counting", render: (t: any) => (t.counting_rule === "WORKING_DAYS" ? "working days" : "calendar days") },
          { key: "max_days_per_request", header: "Max days", align: "end", mono: true },
          { key: "is_active", header: "Active", render: (t: any) => (t.is_active ? "yes" : "no") },
        ]}
        fields={[
          { name: "code", label: "Code", required: true },
          { name: "name", label: "Name", required: true },
          { name: "is_paid", label: "Paid", type: "checkbox" },
          { name: "consumes_entitlement", label: "Consumes the annual entitlement", type: "checkbox" },
          { name: "requires_document", label: "Supporting document required", type: "checkbox" },
          { name: "generates_deduction", label: "Generates a salary deduction", type: "checkbox" },
          { name: "counts_for_seniority", label: "Counts for seniority", type: "checkbox" },
          { name: "pays_leave_allowance", label: "Pays the leave allowance", type: "checkbox" },
          {
            name: "counting_rule",
            label: "Counting rule (BN-52)",
            type: "select",
            options: [
              { value: "WORKING_DAYS", label: "Working days" },
              { value: "CALENDAR_DAYS", label: "Calendar days" },
            ],
          },
          { name: "max_days_per_request", label: "Max days per request", type: "number" },
          { name: "color", label: "Colour", type: "color" },
          { name: "is_active", label: "Active", type: "checkbox" },
        ]}
        defaults={{ is_paid: true, counts_for_seniority: true, counting_rule: "WORKING_DAYS", color: "#714b67", is_active: true }}
      />
      <CrudSection
        endpoint="leave/rules/"
        title="Entitlement rules (BN-48, BN-56)"
        description="Dated rules: a change applies from its effective date only."
        modalSize="lg"
        columns={[
          { key: "name", header: "Rule" },
          { key: "effective_from", header: "From", render: (r: any) => fmt.date(r.effective_from) },
          { key: "days_per_month", header: "Days / month", align: "end", mono: true },
          { key: "seniority_brackets", header: "Seniority", render: (r: any) => (r.seniority_brackets || []).map((b: any) => `${b.years}y:+${b.extra_days}`).join(" · ") },
          { key: "max_carry_over_days", header: "Max carry-over", align: "end", mono: true },
          { key: "allowance", header: "Allowance", render: (r: any) => `${r.allowance_reference_months} months / ${r.allowance_days_divisor}` },
        ]}
        fields={[
          { name: "name", label: "Name", required: true },
          { name: "effective_from", label: "Effective from", type: "date", required: true },
          { name: "days_per_month", label: "Days acquired per month", type: "number", step: "0.01", required: true },
          { name: "max_carry_over_days", label: "Max carry-over (days)", type: "number" },
          { name: "seniority_brackets", label: "Seniority brackets", type: "json", hint: '[{"years": 5, "extra_days": 2}, …]' },
          { name: "allowance_reference_months", label: "Allowance: reference months", type: "number" },
          { name: "allowance_days_divisor", label: "Allowance: daily divisor", type: "number", step: "0.01" },
        ]}
        defaults={{ seniority_brackets: [], allowance_reference_months: 12, allowance_days_divisor: 26 }}
      />
      <CrudSection
        endpoint="leave/adjustments/"
        title="Adjustments & opening balances (BN-48, BN-179)"
        canEdit={false}
        columns={[
          { key: "employee_name", header: "Employee" },
          { key: "year", header: "Year", mono: true },
          { key: "kind", header: "Kind", render: (a: any) => <span className="badge-purple">{a.kind.toLowerCase()}</span> },
          { key: "days", header: "Days", align: "end", mono: true },
          { key: "reason", header: "Reason" },
        ]}
        fields={[
          employeeField(),
          { name: "year", label: "Year", type: "number", required: true },
          {
            name: "kind",
            label: "Kind",
            type: "select",
            required: true,
            options: [
              { value: "OPENING", label: "Opening balance" },
              { value: "EXTRA", label: "Additional entitlement" },
              { value: "CORRECTION", label: "Correction" },
            ],
          },
          { name: "days", label: "Days (negative to remove)", type: "number", step: "0.5", required: true },
          { name: "reason", label: "Reason", required: true },
        ]}
        defaults={{ year: new Date().getFullYear(), kind: "EXTRA" }}
      />
    </div>
  );
}

export default function LeaveAdmin() {
  const [tab, setTab] = useHashTab("requests");
  const { can } = usePermissions();
  return (
    <>
      <PageHeader eyebrow="Time & absence" title="Leave & absence" subtitle="Requests, approvals, balances and the annual plan (M-06)." />
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "requests", label: "Requests" },
          { id: "plan", label: "Annual plan" },
          { id: "balances", label: "Balances" },
          { id: "configuration", label: "Configuration", hidden: !can("leave", "modify") },
        ]}
      />
      {tab === "requests" && <Requests />}
      {tab === "plan" && <LeavePlan />}
      {tab === "balances" && <Balances />}
      {tab === "configuration" && <Configuration />}
    </>
  );
}
