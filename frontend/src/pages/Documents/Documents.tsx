import { useState } from "react";
import { apiError, downloadFile, fmt } from "@/api/helpers";
import CrudSection from "@/components/kit/CrudSection";
import { FormGrid } from "@/components/kit/Form";
import { useHashTab } from "@/components/kit/hooks";
import { employeeField, opt } from "@/components/kit/options";
import SearchSelect from "@/components/kit/SearchSelect";
import { Badge, Banner, Card, PageHeader, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

export const CERTIFICATES = opt([
  ["WORK_CERTIFICATE", "Work certificate"],
  ["EMPLOYMENT_ATTESTATION", "Employment attestation"],
  ["SALARY_ATTESTATION", "Salary attestation"],
  ["PRESENCE_ATTESTATION", "Attestation of presence"],
]);
const DECISIONS = opt([["PROMOTION_DECISION", "Promotion decision"], ["TRANSFER_DECISION", "Transfer decision"], ["DISCIPLINARY_LETTER", "Disciplinary letter"]]);
const CATEGORIES = opt([["CONTRACT", "Contract"], ["CERTIFICATE", "Certificate"], ["LEAVE", "Leave"], ["PAYROLL", "Payroll"], ["DECISION", "Decision"], ["OTHER", "Other"]]);

function Generate() {
  const toast = useToast();
  const [employee, setEmployee] = useState<number | null>(null);
  const [decision, setDecision] = useState<Record<string, any>>({ code: "PROMOTION_DECISION" });
  const issue = async (code: string) => {
    if (!employee) return toast.error("Choose an employee first.");
    try {
      await downloadFile(`documents/certificates/${code}/`, { params: { employee } });
    } catch (err: any) {
      toast.error(err.message);
    }
  };
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Certificates and attestations">
        <div className="space-y-3">
          <SearchSelect url="employees/" value={employee} onChange={(v) => setEmployee(v ? Number(v) : null)} placeholder="Search the employee by name or matriculation…" />
          <div className="flex flex-wrap gap-2">
            {CERTIFICATES.map((c) => (
              <button key={c.value} type="button" className="btn-secondary" onClick={() => issue(c.value)}>{c.label}</button>
            ))}
          </div>
          <p className="text-xs text-muted-c">Every document is archived with its date, author and recipient.</p>
        </div>
      </Card>
      <Card title="Decisions and letters">
        <form className="space-y-3" onSubmit={async (e) => {
          e.preventDefault();
          try {
            await downloadFile("documents/decisions/", { method: "post", data: decision });
          } catch (err: any) {
            toast.error(err.message);
          }
        }}>
          <FormGrid
            fields={[
              { name: "code", label: "Document", type: "select", required: true, options: DECISIONS },
              { ...employeeField(), full: false },
              { name: "subject", label: "Subject", required: true, full: true },
              { name: "effective_date", label: "Effective date", type: "date" },
              { name: "details", label: "Details", type: "textarea" },
            ]}
            values={decision}
            onChange={(n, v) => setDecision((p) => ({ ...p, [n]: v }))}
          />
          <button type="submit" className="btn-primary">Generate</button>
        </form>
      </Card>
    </div>
  );
}

/** M-12 – templates, generation and archive of the documents. */
export default function Documents() {
  const [tab, setTab] = useHashTab("generate");
  const toast = useToast();
  const { can } = usePermissions();
  const [previewFor, setPreviewFor] = useState<number | null>(null);
  return (
    <>
      <PageHeader title="Documents" eyebrow="Documents" subtitle="Every document carries the logo and the legal identification of the organisation." />
      <Tabs active={tab} onChange={setTab} tabs={[
        { id: "generate", label: "Generate" },
        { id: "requests", label: "Requests" },
        { id: "issued", label: "Issued documents" },
        { id: "templates", label: "Templates", hidden: !can("documents", "modify") },
      ]} />
      {tab === "generate" && <Generate />}
      {tab === "requests" && (
        <CrudSection
          endpoint="documents/requests/"
          title="Requests of the employees"
          canCreate={false}
          canEdit={false}
          canDelete={false}
          rowActions={[{
            label: "Issue", show: (r: any) => r.status === "PENDING", onClick: async (r: any, reload) => {
              try {
                await downloadFile(`documents/certificates/${r.template_code}/`, { params: { employee: r.employee } });
                reload();
              } catch (err: any) {
                toast.error(err.message);
              }
            },
          }]}
          columns={[
            { key: "created_at", header: "Asked on", render: (r: any) => fmt.date(r.created_at) },
            { key: "employee_name", header: "Employee" },
            { key: "template_code", header: "Document", render: (r: any) => CERTIFICATES.find((c) => c.value === r.template_code)?.label || r.template_code },
            { key: "reason", header: "Reason" },
            { key: "status", header: "Status", render: (r: any) => <StatusBadge value={r.status} /> },
          ]}
        />
      )}
      {tab === "issued" && (
        <CrudSection
          endpoint="documents/issued/"
          title="Archive of the issued documents"
          canCreate={false}
          canEdit={false}
          canDelete={false}
          rowActions={[{ label: "Download", onClick: (d: any) => downloadFile(`documents/issued/${d.id}/download/`).catch((err) => toast.error(err.message)) }]}
          columns={[
            { key: "issued_at", header: "Issued", render: (d: any) => fmt.datetime(d.issued_at) },
            { key: "reference", header: "Reference", mono: true },
            { key: "title", header: "Document" },
            { key: "recipient", header: "Recipient" },
            { key: "issued_by_name", header: "By" },
            { key: "is_duplicate", header: "", render: (d: any) => (d.is_duplicate ? <Badge tone="orange">Duplicate</Badge> : null) },
          ]}
        />
      )}
      {tab === "templates" && (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Banner tone="info">Templates use variables such as {"{{ employee.surname }}"}, {"{{ company.corporate_name }}"}, {"{{ today|date:\"d/m/Y\" }}"}, {"{{ amount|money }}"}.</Banner>
            <SearchSelect className="w-72" url="employees/" value={previewFor} onChange={(v) => setPreviewFor(v ? Number(v) : null)} placeholder="Employee used for the previews…" />
          </div>
          <CrudSection
            endpoint="documents/templates/"
            title="Document templates"
            modalSize="xl"
            fields={[
              { name: "code", label: "Code", required: true },
              { name: "name", label: "Name", required: true },
              { name: "category", label: "Category", type: "select", options: CATEGORIES },
              { name: "footer", label: "Footer" },
              { name: "body", label: "Body (HTML)", type: "textarea", rows: 18, full: true },
              { name: "signature_block", label: "Signature block (HTML)", type: "textarea", rows: 4, full: true },
              { name: "is_active", label: "Active", type: "checkbox" },
            ]}
            defaults={{ category: "OTHER", is_active: true }}
            rowActions={[{
              label: "Preview", onClick: (t: any) => downloadFile(`documents/templates/${t.id}/preview/`, { params: previewFor ? { employee: previewFor } : {} })
                .catch((err) => toast.error(apiError(err) || err.message)),
            }]}
            columns={[
              { key: "name", header: "Template", render: (t: any) => <span className="font-medium text-primary-c">{t.name}</span> },
              { key: "code", header: "Code", mono: true },
              { key: "category", header: "Category" },
              { key: "updated_at", header: "Modified", render: (t: any) => `${fmt.datetime(t.updated_at)}${t.updated_by_name ? ` by ${t.updated_by_name}` : ""}` },
            ]}
          />
        </>
      )}
    </>
  );
}
