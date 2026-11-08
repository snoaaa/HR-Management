import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, downloadFile, fmt } from "@/api/helpers";
import DataTable from "@/components/kit/DataTable";
import { useApiList } from "@/components/kit/hooks";
import { Card, Modal, PageHeader, StatusBadge } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

const DOCUMENT_OPTIONS = [
  { code: "EMPLOYMENT_ATTESTATION", label: "Employment Attestation (Attestation de travail)" },
  { code: "WORK_CERTIFICATE", label: "Work Certificate (Certificat de travail)" },
  { code: "SALARY_ATTESTATION", label: "Salary Attestation (Attestation de salaire)" },
  { code: "PRESENCE_ATTESTATION", label: "Presence Attestation (Attestation de présence)" },
];

export default function MyDocuments() {
  const { employee_id } = usePermissions();
  const [requesting, setRequesting] = useState(false);
  const [templateCode, setTemplateCode] = useState(DOCUMENT_OPTIONS[0].code);
  const [reason, setReason] = useState("");
  const toast = useToast();

  const { rows: issued, loading: loadingIssued } = useApiList<any>(
    employee_id ? `documents/issued/?employee=${employee_id}` : null
  );

  const { rows: requests, loading: loadingRequests, reload: reloadRequests } = useApiList<any>(
    "documents/requests/"
  );

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

  const submitRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("documents/requests/", {
        template_code: templateCode,
        reason,
      });
      toast.success("Document request submitted to HR");
      setRequesting(false);
      setReason("");
      reloadRequests();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="My Space"
        title="My Documents & Attestations (BN-150, BN-152)"
        subtitle="Download official company documents issued to you and submit online attestation requests to HR."
        actions={
          <button type="button" className="btn-primary" onClick={() => setRequesting(true)}>
            + Request attestation
          </button>
        }
      />

      <div className="space-y-6">
        <Card padded={false} title="Issued documents archive">
          <DataTable
            rows={issued}
            loading={loadingIssued}
            empty="No issued document found."
            columns={[
              { key: "reference", header: "Reference", mono: true, render: (d: any) => <span className="font-semibold text-primary-c">{d.reference}</span> },
              { key: "title", header: "Document title" },
              { key: "issued_at", header: "Date", render: (d: any) => fmt.date(d.issued_at) },
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

        <Card padded={false} title="My pending document requests">
          <DataTable
            rows={requests}
            loading={loadingRequests}
            empty="No pending request."
            columns={[
              { key: "template_code", header: "Requested attestation" },
              { key: "reason", header: "Purpose / Reason" },
              { key: "created_at", header: "Requested on", render: (r: any) => fmt.date(r.created_at) },
              { key: "status", header: "Status", render: (r: any) => <StatusBadge value={r.status} /> },
            ]}
          />
        </Card>
      </div>

      {requesting && (
        <Modal open={true} onClose={() => setRequesting(false)} title="Request an official attestation">
          <form onSubmit={submitRequest} className="space-y-4">
            <label>
              <span className="field-label">Document type</span>
              <select className="input-field" value={templateCode} onChange={(e) => setTemplateCode(e.target.value)}>
                {DOCUMENT_OPTIONS.map((o) => (
                  <option key={o.code} value={o.code}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span className="field-label">Reason / Destination</span>
              <textarea
                className="input-field"
                rows={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Bank loan application, Visa request, Administrative proof"
                required
              />
            </label>

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="btn-secondary" onClick={() => setRequesting(false)}>
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Submit request
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

