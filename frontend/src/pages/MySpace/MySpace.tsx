import { useNavigate } from "react-router";
import { downloadFile, firstOfMonthISO, fmt, todayISO } from "@/api/helpers";
import ClockWidget from "@/components/dashboard/ClockWidget";
import CrudSection, { DownloadButton } from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { useApiList } from "@/components/kit/hooks";
import { opt } from "@/components/kit/options";
import { Badge, Banner, Card, PageHeader, StatusBadge } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";
import { CERTIFICATES } from "../Documents/Documents";

function NoRecord() {
  return <Banner tone="info">No employee record is linked to your account.</Banner>;
}

/** BN-151: my attendance, my timetable, regularisation of my clockings. */
export function MyTime() {
  const { employee_id } = usePermissions();
  const { rows: days, loading } = useApiList<any>(employee_id ? "attendance/days/" : null, { employee: employee_id, date__gte: firstOfMonthISO() });
  const { rows: shifts } = useApiList<any>(employee_id ? "planning/entries/" : null, { employee: employee_id, date__gte: todayISO() });
  if (!employee_id) return <NoRecord />;
  return (
    <>
      <PageHeader title="My time & timetable" eyebrow="My space" />
      <div className="grid gap-4 lg:grid-cols-3">
        <ClockWidget />
        <Card title="My next shifts" padded={false} className="lg:col-span-2">
          <DataTable exportTitle="My next shifts" rows={shifts} empty="No published shift." columns={[
            { key: "date", header: "Date", render: (e: any) => fmt.date(e.date) },
            { key: "shift_name", header: "Shift", render: (e: any) => <span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-sm" style={{ background: e.shift_color }} />{e.shift_name}</span> },
            { key: "hours", header: "Hours", render: (e: any) => `${String(e.start_time).slice(0, 5)} – ${String(e.end_time).slice(0, 5)}` },
            { key: "timetable_name", header: "Timetable" },
          ]} />
        </Card>
      </div>
      <div className="mt-4 space-y-4">
        <Card title="My attendance this month" padded={false}>
          <DataTable exportTitle="My attendance" rows={days} loading={loading} columns={[
            { key: "date", header: "Date", render: (d: any) => fmt.date(d.date) },
            { key: "status", header: "Status", render: (d: any) => <StatusBadge value={d.status} label={d.status_label} /> },
            { key: "worked_minutes", header: "Worked", render: (d: any) => fmt.minutes(d.worked_minutes) },
            { key: "late_minutes", header: "Late", render: (d: any) => fmt.minutes(d.late_minutes) },
            { key: "overtime_minutes", header: "Overtime", render: (d: any) => fmt.minutes(d.overtime_minutes) },
            { key: "overtime_status", header: "Overtime status", render: (d: any) => (d.overtime_status !== "NONE" ? <StatusBadge value={d.overtime_status} /> : null) },
          ]} />
        </Card>
        <CrudSection
          endpoint="attendance/regularisations/"
          params={{ employee: employee_id }}
          title="Correct a clocking"
          description="A forgotten or wrong clocking is corrected after the approval of your manager; the original stays visible."
          createLabel="+ Request a correction"
          canEdit={false}
          canDelete={false}
          defaults={{ employee: employee_id }}
          fields={[
            { name: "employee", label: "Employee", type: "number", hidden: () => true, alwaysSend: true },
            { name: "clocking", label: "Clocking to correct (empty if forgotten)", type: "select", optionsUrl: `attendance/clockings/?employee=${employee_id}&is_active=true`,
              optionLabel: (c: any) => `${c.date} ${String(c.time_in).slice(0, 5)}–${c.time_out ? String(c.time_out).slice(0, 5) : "…"}`, full: true },
            { name: "date", label: "Date", type: "date", required: true },
            { name: "time_in", label: "Entry", type: "time", required: true },
            { name: "time_out", label: "Exit", type: "time" },
            { name: "justification", label: "Justification", type: "textarea", required: true },
          ]}
          columns={[
            { key: "date", header: "Date", render: (r: any) => fmt.date(r.date) },
            { key: "hours", header: "Corrected hours", render: (r: any) => `${String(r.time_in).slice(0, 5)} – ${r.time_out ? String(r.time_out).slice(0, 5) : "…"}` },
            { key: "justification", header: "Justification" },
            { key: "status", header: "Status", render: (r: any) => <StatusBadge value={r.status} /> },
          ]}
        />
      </div>
    </>
  );
}

/** BN-150: my payslips and annual statements. */
export function MyPayslips() {
  const { employee_id } = usePermissions();
  const { rows, loading } = useApiList<any>(employee_id ? "payroll/payslips/mine/" : null);
  if (!employee_id) return <NoRecord />;
  const year = new Date().getFullYear();
  return (
    <>
      <PageHeader title="My payslips" eyebrow="My space" actions={
        <>
          <DownloadButton url="payroll/annual-statement/" params={{ year: year - 1 }} label={`Annual statement ${year - 1}`} />
          <DownloadButton url="payroll/annual-statement/" params={{ year }} label={`Annual statement ${year}`} />
        </>
      } />
      <Card padded={false}>
        <DataTable exportTitle="My payslips" rows={rows} loading={loading} empty="No validated payslip yet." columns={[
          { key: "period_label", header: "Period" },
          { key: "gross", header: "Gross", align: "end", render: (p: any) => fmt.money(p.gross) },
          { key: "net_payable", header: "Net payable", align: "end", render: (p: any) => <span className="mono font-semibold">{fmt.money(p.net_payable)}</span> },
          { key: "pdf", header: "", align: "end", render: (p: any) => <DownloadButton url={`payroll/payslips/${p.id}/pdf/`} label="Download" className="btn-ghost text-brand-600" /> },
        ]} />
      </Card>
    </>
  );
}

const CORRECTION_FIELDS = opt([
  ["address", "Address"], ["city", "City"], ["region", "Region"], ["postal_box", "P.O. Box"], ["maiden_name", "Maiden name"], ["blood_group", "Blood group"], ["spoken_languages", "Spoken languages"], ["phone_number", "Telephone"], ["phone_number_2", "Second telephone"], ["personal_email", "Personal e-mail"],
  ["marital_status", "Marital status"], ["emergency_contact_name", "Emergency contact"], ["emergency_contact_number", "Emergency contact number"],
  ["emergency_contact_relationship", "Emergency contact relationship"], ["identity_document_number", "Identity document number"],
  ["identity_document_validity", "Identity document validity"], ["bank_name", "Bank"], ["bank_branch", "Bank branch"], ["account_number", "Account number"],
  ["bank_key", "Bank key"], ["place_of_birth", "Place of birth"], ["nationality", "Nationality"],
  ["social_insurance_number", "Social insurance number"], ["tax_identification_number", "Tax identification number"],
]);

/** BN-148 / BN-150 / BN-152 / BN-177: my documents, requests and personal data. */
export function MyDocuments() {
  const toast = useToast();
  const { employee_id } = usePermissions();
  if (!employee_id) return <NoRecord />;
  const print = (code: string) => downloadFile(`documents/certificates/${code}/`).catch((err) => toast.error(err.message));
  return (
    <>
      <PageHeader title="My documents" eyebrow="My space" actions={
        <button type="button" className="btn-secondary" onClick={() => downloadFile("employees/me/data/", { open: false, filename: "my-personal-data.json" }).catch((err) => toast.error(err.message))}>
          Download my personal data
        </button>
      } />
      <div className="space-y-4">
        <Card title="Print an attestation now">
          <div className="flex flex-wrap gap-2">
            {CERTIFICATES.map((c) => <button key={c.value} type="button" className="btn-secondary" onClick={() => print(c.value)}>{c.label}</button>)}
          </div>
        </Card>
        <CrudSection
          endpoint="documents/issued/"
          params={{ employee: employee_id }}
          title="My documents"
          canCreate={false}
          canEdit={false}
          canDelete={false}
          rowActions={[{ label: "Download", onClick: (d: any) => downloadFile(`documents/issued/${d.id}/download/`).catch((err) => toast.error(err.message)) }]}
          columns={[
            { key: "issued_at", header: "Date", render: (d: any) => fmt.date(d.issued_at) },
            { key: "title", header: "Document" },
            { key: "reference", header: "Reference", mono: true },
          ]}
        />
        <CrudSection
          endpoint="employees/corrections/"
          title="Correct an item of my record"
          description="Your request is checked by HR before the correction."
          createLabel="+ Request a correction"
          canEdit={false}
          canDelete={false}
          fields={[
            { name: "field_name", label: "Item", type: "select", required: true, options: CORRECTION_FIELDS },
            { name: "requested_value", label: "Correct value", required: true },
            { name: "reason", label: "Reason", full: true },
          ]}
          columns={[
            { key: "created_at", header: "Date", render: (r: any) => fmt.date(r.created_at) },
            { key: "field_label", header: "Item" },
            { key: "current_value", header: "Current" },
            { key: "requested_value", header: "Requested" },
            { key: "status", header: "Status", render: (r: any) => <StatusBadge value={r.status} /> },
          ]}
        />
      </div>
    </>
  );
}

/** BN-83: my evaluations (as employee or as evaluator). */
export function MyEvaluations() {
  const navigate = useNavigate();
  const { rows, loading } = useApiList<any>("evaluation/evaluations/mine/");
  return (
    <>
      <PageHeader title="My evaluations" eyebrow="My space" />
      <Card padded={false}>
        <DataTable exportTitle="My evaluations" rows={rows} loading={loading} empty="No evaluation." onRowClick={(e: any) => navigate(`/evaluation/${e.id}`)} columns={[
          { key: "campaign_name", header: "Campaign" },
          { key: "employee_name", header: "Employee" },
          { key: "status_label", header: "Status" },
          { key: "final_score", header: "Score", align: "end", render: (e: any) => (e.final_score ? `${fmt.number(e.final_score, 1)} / 100` : "—") },
        ]} />
      </Card>
    </>
  );
}

/** BN-78 / BN-79: my trainings and training requests. */
export function MyTraining() {
  const { rows, loading } = useApiList<any>("training/sessions/mine/");
  return (
    <>
      <PageHeader title="My training" eyebrow="My space" />
      <div className="space-y-4">
        <Card padded={false} title="My sessions">
          <DataTable exportTitle="My training" rows={rows} loading={loading} empty="No training yet." columns={[
            { key: "session_start", header: "Date", render: (p: any) => fmt.date(p.session_start) },
            { key: "session_title", header: "Training" },
            { key: "status", header: "Attendance" },
            { key: "result", header: "Result", render: (p: any) => <Badge tone={p.result === "PASSED" ? "green" : p.result === "FAILED" ? "red" : "gray"}>{p.result}</Badge> },
            { key: "certificate_validity", header: "Certificate valid until", render: (p: any) => fmt.date(p.certificate_validity) },
          ]} />
        </Card>
        <CrudSection
          endpoint="training/needs/"
          title="My training requests"
          createLabel="+ Request a training"
          canEdit={false}
          canDelete={false}
          fields={[
            { name: "subject", label: "Training wanted", required: true, full: true },
            { name: "skill", label: "Skill (optional)", type: "select", optionsUrl: "training/skills/", optionLabel: (s: any) => s.name },
            { name: "year", label: "Year", type: "number", required: true },
          ]}
          defaults={{ year: new Date().getFullYear() }}
          columns={[
            { key: "subject", header: "Subject" },
            { key: "year", header: "Year" },
            { key: "status", header: "Status" },
          ]}
        />
      </div>
    </>
  );
}
