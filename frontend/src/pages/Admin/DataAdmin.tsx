import { useState } from "react";
import { confirmDialog } from "@/components/kit/confirm";
import api from "@/api/axiosConfig";
import { apiError, downloadFile, fmt } from "@/api/helpers";
import DataTable from "@/components/kit/DataTable";
import { useApiList } from "@/components/kit/hooks";
import { Banner, Card, Modal, PageHeader, Spinner } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

const IMPORTS = [
  ["employees", "Employees", "Records from the existing files (department and position by their code)."],
  ["contracts", "Contracts", "Contract and agreed salary of each employee (by matriculation); the contract is activated."],
  ["leave_balances", "Leave balances", "Opening balance of each employee for a year."],
  ["salary_elements", "Salary elements", "Individual values of the bonuses and allowances."],
  ["loans", "Loans and advances", "Outstanding balance and monthly instalment."],
];

function Imports() {
  const toast = useToast();
  const [kind, setKind] = useState("employees");
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const run = async (dryRun: boolean) => {
    if (!file) return toast.error("Choose a file (CSV or Excel).");
    const form = new FormData();
    form.append("file", file);
    form.append("dry_run", String(dryRun));
    setBusy(true);
    try {
      setReport((await api.post(`imports/${kind}/`, form)).data);
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card title="Import of the initial data">
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-2">
          {IMPORTS.map(([id, label, help]) => (
            <label key={id} className="flex cursor-pointer items-start gap-2 rounded-lg border p-3" style={{ borderColor: kind === id ? "var(--odoo-purple)" : "var(--border-color)" }}>
              <input type="radio" className="mt-1 accent-brand-500" checked={kind === id} onChange={() => { setKind(id); setReport(null); }} />
              <span><span className="block font-semibold text-primary-c">{label}</span><span className="text-xs text-muted-c">{help}</span></span>
            </label>
          ))}
        </div>
        <div className="space-y-3 lg:col-span-2">
          <button type="button" className="btn-ghost" onClick={() => downloadFile(`imports/${kind}/`, { open: false }).catch((err) => toast.error(err.message))}>
            Download the template (columns expected)
          </button>
          <input type="file" accept=".csv,.xlsx" className="input-field" onChange={(e) => { setFile(e.target.files?.[0] || null); setReport(null); }} />
          <div className="flex gap-2">
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => run(true)}>1. Check (nothing is saved)</button>
            <button type="button" className="btn-primary" disabled={busy || !report || !report.dry_run} onClick={() => run(false)}>2. Import the valid lines</button>
          </div>
          {busy && <Spinner label="Processing…" />}
          {report && (
            <>
              <Banner tone={report.rejected.length ? "warning" : "success"}>
                {report.lines} line(s): {report.dry_run ? `${report.valid} valid` : `${report.imported} imported`}, {report.rejected.length} rejected.
              </Banner>
              {report.rejected.length > 0 && (
                <DataTable exportTitle="Rejected import lines" dense rows={report.rejected} rowKey={(r: any) => r.line} columns={[
                  { key: "line", header: "Line", align: "end" },
                  { key: "reason", header: "Reason of the rejection" },
                  { key: "data", header: "Data", render: (r: any) => <span className="mono text-xs">{Object.values(r.data).slice(0, 4).join(" · ")}</span> },
                ]} />
              )}
            </>
          )}
        </div>
      </div>
    </Card>
  );
}

function Backups() {
  const toast = useToast();
  const { role } = usePermissions();
  const { rows, loading, reload } = useApiList<any>("backups/");
  const [checking, setChecking] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const create = async () => {
    setBusy(true);
    try {
      await api.post("backups/");
      toast.success("Backup created");
      reload();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };
  const check = async (name: string) => {
    try {
      setChecking((await api.get(`backups/${name}/check/`)).data);
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  const restore = async () => {
    if (!(await confirmDialog({ title: "Restore this backup?", message: `ALL the current data will be replaced with ${checking.name}. This cannot be undone.`, confirmLabel: "Replace all data", danger: true }))) return;
    try {
      await api.post(`backups/${checking.name}/restore/`, { confirm: true });
      toast.success("Backup restored: sign in again.");
      setChecking(null);
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <Card padded={false} title="Backups" actions={
      <>
        <span className="text-xs text-muted-c">A backup is also made every day by the daily job.</span>
        <button type="button" className="btn-primary" disabled={busy} onClick={create}>{busy ? "Backing up…" : "Back up now"}</button>
      </>
    }>
      <DataTable rows={rows} loading={loading} rowKey={(b: any) => b.name} empty="No backup yet." columns={[
        { key: "name", header: "Backup", mono: true },
        { key: "created_at", header: "Date", render: (b: any) => fmt.datetime(b.created_at) },
        { key: "size", header: "Size", align: "end", render: (b: any) => `${(b.size / 1024 / 1024).toFixed(2)} MB` },
        { key: "a", header: "", align: "end", render: (b: any) => (
          <span className="flex justify-end gap-1">
            <button type="button" className="btn-ghost text-brand-600" onClick={() => check(b.name)}>Check</button>
            <button type="button" className="btn-ghost text-brand-600" onClick={() => downloadFile(`backups/${b.name}/download/`, { open: false }).catch((err) => toast.error(err.message))}>Download</button>
          </span>
        ) },
      ]} />
      <Modal open={!!checking} title={`Control of ${checking?.name}`} onClose={() => setChecking(null)}
        footer={role === "SYSTEM_ADMINISTRATOR" && <button type="button" className="btn-danger" onClick={restore}>Restore this backup</button>}>
        {checking && (
          <div className="space-y-3 text-sm">
            <Banner tone="success">The archive is valid: {checking.objects} records and {checking.media_files} documents.</Banner>
            <DataTable dense rows={Object.entries(checking.models).map(([model, count]) => ({ id: model, model, count }))} columns={[
              { key: "model", header: "Data", mono: true },
              { key: "count", header: "Records", align: "end" },
            ]} />
          </div>
        )}
      </Modal>
    </Card>
  );
}

/** BN-179 / BN-183: initial data import and backups. */
export default function DataAdmin() {
  return (
    <>
      <PageHeader title="Data: import & backups" eyebrow="Administration" />
      <div className="space-y-4">
        <Imports />
        <Backups />
      </div>
    </>
  );
}
