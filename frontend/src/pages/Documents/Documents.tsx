import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, downloadFile, fmt } from "@/api/helpers";
import DataTable from "@/components/kit/DataTable";
import { useApiList, useHashTab, useOptions } from "@/components/kit/hooks";
import { Card, Modal, PageHeader, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

const CERTIFICATE_TYPES = [
  { code: "EMPLOYMENT_ATTESTATION", label: "Employment Attestation (Attestation de travail)" },
  { code: "WORK_CERTIFICATE", label: "Work Certificate (Certificat de travail)" },
  { code: "SALARY_ATTESTATION", label: "Salary Attestation (Attestation de salaire)" },
  { code: "PRESENCE_ATTESTATION", label: "Presence Attestation (Attestation de présence)" },
];

function GenerateCertificate() {
  const employees = useOptions("employees/", (e) => `${e.full_name || `${e.surname} ${e.given_names}`} (${e.matriculation})`);
  const [employeeId, setEmployeeId] = useState("");
  const [certCode, setCertCode] = useState(CERTIFICATE_TYPES[0].code);
  const [generating, setGenerating] = useState(false);
  const toast = useToast();

  const handleGenerate = async () => {
    if (!employeeId) {
      toast.error("Please select an employee");
      return;
    }
    setGenerating(true);
    try {
      await downloadFile(`documents/certificates/${certCode}/?employee=${employeeId}`, {
        method: "get",
        filename: `${certCode.toLowerCase()}_${employeeId}.pdf`,
        open: true,
      });
      toast.success("Certificate generated and opened");
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <Card title="Issue an official certificate (BN-123)">
      <p className="text-xs text-muted-c mb-4">Generate and archive an attested legal document from official templates.</p>
      <div className="max-w-xl space-y-4">
        <label>
          <span className="field-label">Employee</span>
          <select className="input-field" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
            <option value="">Select employee...</option>
            {employees.map((e) => (
              <option key={e.value} value={e.value}>
                {e.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">Document type</span>
          <select className="input-field" value={certCode} onChange={(e) => setCertCode(e.target.value)}>
            {CERTIFICATE_TYPES.map((t) => (
              <option key={t.code} value={t.code}>
                {t.label}
              </option>
            ))}
          </select>
        </label>

        <div className="pt-2">
          <button type="button" className="btn-primary" disabled={generating} onClick={handleGenerate}>
            {generating ? "Generating PDF..." : "Generate and download PDF →"}
          </button>
        </div>
      </div>
    </Card>
  );
}

function IssuedArchive() {
  const { rows, loading } = useApiList<any>("documents/issued/");
  const toast = useToast();

  const downloadDoc = async (doc: any) => {
    try {
      await downloadFile(`documents/issued/${doc.id}/download/`, {
        filename: `${doc.reference || "document"}.pdf`,
        open: true,
      });
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <Card padded={false} title="Issued documents archive (BN-127)">
      <DataTable
        rows={rows}
        loading={loading}
        empty="No issued documents in the archive yet."
        columns={[
          {
            key: "reference",
            header: "Reference",
            mono: true,
            render: (d: any) => <span className="font-semibold text-primary-c">{d.reference}</span>,
          },
          { key: "title", header: "Document Title" },
          { key: "employee_name", header: "Employee" },
          { key: "issued_at", header: "Issued at", render: (d: any) => fmt.datetime(d.issued_at) },
          { key: "issued_by_name", header: "Issued by" },
          {
            key: "actions",
            header: "",
            align: "end",
            render: (d: any) => (
              <button type="button" className="btn-ghost text-xs" onClick={() => downloadDoc(d)}>
                Download PDF
              </button>
            ),
          },
        ]}
      />
    </Card>
  );
}

function TemplatesEditor() {
  const { rows, loading, reload } = useApiList<any>("documents/templates/");
  const [editing, setEditing] = useState<any>(null);
  const toast = useToast();

  const previewTemplate = async (template: any) => {
    try {
      await downloadFile(`documents/templates/${template.id}/preview/`, {
        filename: `preview_${template.code}.pdf`,
        open: true,
      });
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <>
      <Card padded={false} title="Document templates (BN-125)">
        <DataTable
          rows={rows}
          loading={loading}
          columns={[
            {
              key: "name",
              header: "Template",
              render: (t: any) => (
                <div>
                  <span className="font-medium text-primary-c">{t.name}</span>
                  <span className="block text-[11px] mono text-muted-c">{t.code}</span>
                </div>
              ),
            },
            { key: "category", header: "Category" },
            { key: "updated_at", header: "Last modified", render: (t: any) => fmt.datetime(t.updated_at) },
            {
              key: "actions",
              header: "",
              align: "end",
              render: (t: any) => (
                <div className="flex justify-end gap-1">
                  <button type="button" className="btn-ghost text-xs" onClick={() => previewTemplate(t)}>
                    Preview PDF
                  </button>
                  <button type="button" className="btn-ghost text-xs" onClick={() => setEditing(t)}>
                    Edit HTML
                  </button>
                </div>
              ),
            },
          ]}
        />
      </Card>

      {editing && (
        <Modal open={true} onClose={() => setEditing(null)} title={`Edit template: ${editing.name}`} size="xl">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api.patch(`documents/templates/${editing.id}/`, {
                  name: editing.name,
                  body: editing.body,
                });
                toast.success("Template saved");
                setEditing(null);
                reload();
              } catch (err) {
                toast.error(apiError(err));
              }
            }}
            className="space-y-4"
          >
            <label>
              <span className="field-label">Template name</span>
              <input
                className="input-field"
                value={editing.name}
                onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                required
              />
            </label>
            <label>
              <span className="field-label">HTML / Django Template Body</span>
              <textarea
                className="input-field font-mono text-xs"
                rows={12}
                value={editing.body}
                onChange={(e) => setEditing({ ...editing, body: e.target.value })}
                required
              />
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="btn-secondary" onClick={() => setEditing(null)}>
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Save template
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

function DocumentRequests() {
  const { rows, loading, reload } = useApiList<any>("documents/requests/");
  const toast = useToast();

  const handleIssue = async (req: any) => {
    try {
      await downloadFile(`documents/certificates/${req.template_code}/?employee=${req.employee}`, {
        method: "post",
        filename: `${req.template_code.toLowerCase()}_${req.employee}.pdf`,
        open: true,
      });
      toast.success("Certificate issued and downloaded");
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <Card padded={false} title="Employee attestation requests (BN-152)">
      <DataTable
        rows={rows}
        loading={loading}
        empty="No pending document request."
        columns={[
          { key: "employee_name", header: "Employee" },
          { key: "template_code", header: "Requested Document" },
          { key: "reason", header: "Reason" },
          { key: "created_at", header: "Requested at", render: (r: any) => fmt.datetime(r.created_at) },
          { key: "status", header: "Status", render: (r: any) => <StatusBadge value={r.status} /> },
          {
            key: "actions",
            header: "",
            align: "end",
            render: (r: any) =>
              r.status === "PENDING" && (
                <button type="button" className="btn-primary text-xs" onClick={() => handleIssue(r)}>
                  Issue document
                </button>
              ),
          },
        ]}
      />
    </Card>
  );
}

export default function Documents() {
  const [tab, setTab] = useHashTab("generate");
  const { can } = usePermissions();

  return (
    <>
      <PageHeader
        eyebrow="Documents"
        title="Document Management (M-12)"
        subtitle="Issue legal certificates, customize document templates, and browse the certified archive."
      />
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "generate", label: "Issue certificate (BN-123)" },
          { id: "archive", label: "Issued archive (BN-127)" },
          { id: "requests", label: "Employee requests (BN-152)" },
          ...(can("documents", "modify") ? [{ id: "templates", label: "Templates editor (BN-125)" }] : []),
        ]}
      />
      {tab === "generate" && <GenerateCertificate />}
      {tab === "archive" && <IssuedArchive />}
      {tab === "requests" && <DocumentRequests />}
      {tab === "templates" && <TemplatesEditor />}
    </>
  );
}

