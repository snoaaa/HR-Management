import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import CrudSection, { DownloadButton, ExportButtons } from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { PromptModal } from "@/components/kit/Form";
import { useApiItem, useApiList, useHashTab } from "@/components/kit/hooks";
import { BODIES, MONTHS, departmentField, elementField, employeeField } from "@/components/kit/options";
import { Badge, Banner, Card, KpiTile, PageHeader, Spinner, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

const STEPS = ["OPENED", "IN_PREPARATION", "CALCULATED", "VERIFIED", "VALIDATED", "PAID", "POSTED", "CLOSED"];
const STEP_LABELS: Record<string, string> = {
  OPENED: "Opened", IN_PREPARATION: "Preparation", CALCULATED: "Calculated", VERIFIED: "Verified",
  VALIDATED: "Validated", PAID: "Paid", POSTED: "Posted", CLOSED: "Closed",
};

function Stepper({ status }: { status: string }) {
  const current = STEPS.indexOf(status);
  return (
    <ol className="mb-5 grid grid-cols-4 gap-2 sm:grid-cols-8">
      {STEPS.map((step, index) => (
        <li
          key={step}
          className="rounded-lg border px-2 py-2 text-center text-xs font-semibold"
          style={{
            borderColor: index <= current ? "var(--odoo-purple)" : "var(--border-color)",
            background: index === current ? "var(--odoo-purple)" : index < current ? "var(--odoo-purple-light)" : "var(--surface)",
            color: index === current ? "#fff" : index < current ? "var(--odoo-purple)" : "var(--text-muted)",
          }}
        >
          {index + 1}. {STEP_LABELS[step]}
        </li>
      ))}
    </ol>
  );
}

/** One payroll period: actions of the cycle and every control (BN-93 → BN-122). */
export default function PeriodCockpit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { can, can_view_salary } = usePermissions();
  const { data: period, reload } = useApiItem<any>(`payroll/periods/${id}/`);
  const [tab, setTab] = useHashTab("payslips");
  const [busy, setBusy] = useState(false);
  const [calcScope, setCalcScope] = useState(false);
  const [reversing, setReversing] = useState(false);
  const [refresh, setRefresh] = useState(0);

  if (!period) return <Spinner />;
  const locked = ["VALIDATED", "PAID", "POSTED", "CLOSED"].includes(period.status);
  const manage = can("payroll", "modify");
  const t = period.totals || {};

  const run = async (label: string, request: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await request();
      toast.success(label);
      reload();
      setRefresh((r) => r + 1);
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };
  const transition = (status: string, label: string) => run(label, () => api.post(`payroll/periods/${id}/transition/`, { status }));

  return (
    <>
      <PageHeader
        title={`Payroll ${MONTHS[period.month - 1]} ${period.year}`}
        eyebrow="Payroll cycle"
        actions={
          <>
            <button type="button" className="btn-ghost" onClick={() => navigate("/payroll")}>← Periods</button>
            {manage && !locked && (
              <>
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => run("Variable elements retrieved", () => api.post(`payroll/periods/${id}/pull_inputs/`))}>
                  Retrieve variables
                </button>
                <button type="button" className="btn-primary" disabled={busy} onClick={() => setCalcScope(true)}>
                  Calculate
                </button>
              </>
            )}
            {manage && period.status === "CALCULATED" && (
              <button type="button" className="btn-secondary" disabled={busy} onClick={() => transition("VERIFIED", "Period verified")}>Mark verified</button>
            )}
            {can("payroll", "validate") && ["CALCULATED", "VERIFIED"].includes(period.status) && (
              <button type="button" className="btn-teal" disabled={busy} onClick={() => run("Payroll validated and posted in accounting", () => api.post(`payroll/periods/${id}/validate/`))}>
                Validate
              </button>
            )}
            {manage && period.status === "VALIDATED" && (
              <button type="button" className="btn-teal" disabled={busy} onClick={() => transition("PAID", "Salaries paid – payment entry posted")}>Mark paid</button>
            )}
            {manage && period.status === "PAID" && (
              <button type="button" className="btn-secondary" disabled={busy} onClick={() => transition("POSTED", "Period posted")}>Mark posted</button>
            )}
            {manage && period.status === "POSTED" && (
              <button type="button" className="btn-secondary" disabled={busy} onClick={() => transition("CLOSED", "Period closed")}>Close</button>
            )}
            {can("payroll", "validate") && ["VALIDATED", "PAID"].includes(period.status) && (
              <button type="button" className="btn-danger" onClick={() => setReversing(true)}>Reverse</button>
            )}
          </>
        }
      />
      <Stepper status={period.status} />
      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <KpiTile label="Payslips" value={t.count ?? 0} />
        <KpiTile label="Gross" value={fmt.money(t.gross)} accent="var(--odoo-teal)" />
        <KpiTile label="Net payable" value={fmt.money(t.net_payable)} accent="#0A6ED1" />
        <KpiTile label="Employer charges" value={fmt.money(t.employer_contributions)} accent="#E9730C" />
        <KpiTile label="Blocking anomalies" value={t.anomalies ?? 0} accent={t.anomalies ? "var(--danger)" : "#107E3E"} />
      </div>
      {locked && <div className="mb-4"><Banner tone="info">The period is validated: nothing can be modified; correct it by a reversal.</Banner></div>}
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "payslips", label: "Payslips" },
          { id: "inputs", label: "Variable elements", hidden: !can_view_salary },
          { id: "anomalies", label: "Anomalies" },
          { id: "comparison", label: "Comparison", hidden: !can_view_salary },
          { id: "declarations", label: "Declarations" },
          { id: "payments", label: "Payments" },
          { id: "documents", label: "Documents" },
          { id: "accounting", label: "Accounting" },
          { id: "history", label: "History" },
        ]}
      />
      {tab === "payslips" && <PeriodPayslips periodId={Number(id)} refresh={refresh} />}
      {tab === "inputs" && (
        <CrudSection
          key={refresh}
          endpoint="payroll/inputs/"
          params={{ period: id }}
          title="Variable elements"
          description="Overtime, absences, leave allowances and back pay are retrieved automatically; add bonuses or deductions here."
          canCreate={manage && !locked}
          canEdit={(r: any) => manage && !locked && r.source === "MANUAL"}
          canDelete={(r: any) => manage && !locked && r.source === "MANUAL"}
          defaults={{ period: id }}
          fields={[
            { name: "period", label: "Period", type: "number", hidden: () => true, alwaysSend: true },
            employeeField(),
            elementField(),
            { name: "quantity", label: "Quantity (hours, days…)", type: "number", step: "0.01" },
            { name: "amount", label: "Amount (overrides the calculation)", type: "number", step: "1" },
            { name: "comment", label: "Comment", full: true },
          ]}
          columns={[
            { key: "employee_name", header: "Employee" },
            { key: "element_name", header: "Element", render: (r: any) => `${r.element_name} (${r.element_code})` },
            { key: "quantity", header: "Quantity", align: "end", render: (r: any) => fmt.number(r.quantity) },
            { key: "amount", header: "Amount", align: "end", render: (r: any) => fmt.money(r.amount) },
            { key: "source", header: "Source", render: (r: any) => <Badge tone={r.source === "MANUAL" ? "blue" : "teal"}>{r.source}</Badge> },
            { key: "comment", header: "Comment" },
          ]}
        />
      )}
      {tab === "anomalies" && <Anomalies periodId={Number(id)} refresh={refresh} />}
      {tab === "comparison" && <Comparison periodId={Number(id)} />}
      {tab === "declarations" && <Declarations periodId={Number(id)} />}
      {tab === "payments" && <Payments periodId={Number(id)} />}
      {tab === "documents" && <PeriodDocuments periodId={Number(id)} />}
      {tab === "accounting" && <Accounting periodId={Number(id)} />}
      {tab === "history" && (
        <Card padded={false} title="Changes of state">
          <DataTable exportTitle="Payroll period history"
            rows={period.transitions || []}
            columns={[
              { key: "at", header: "Date", render: (r: any) => fmt.datetime(r.at) },
              { key: "from_status", header: "From", render: (r: any) => <StatusBadge value={r.from_status} /> },
              { key: "to_status", header: "To", render: (r: any) => <StatusBadge value={r.to_status} /> },
              { key: "user_name", header: "By" },
              { key: "comment", header: "Comment" },
            ]}
          />
        </Card>
      )}
      <PromptModal
        open={calcScope}
        title="Calculate the payroll"
        message="Leave both fields empty to calculate the whole organisation."
        extraFields={[departmentField("department", "Only this department"), employeeField("employee", "Only this employee", false)]}
        onClose={() => setCalcScope(false)}
        onConfirm={async (v) => {
          await api.post(`payroll/periods/${id}/calculate/`, { department: v.department || undefined, employee: v.employee || undefined });
          toast.success("Payroll calculated");
          reload();
          setRefresh((r) => r + 1);
        }}
      />
      <PromptModal
        open={reversing}
        title="Reverse the validated payroll"
        message="The payslips are kept as reversed, the accounting entries are reversed and the period goes back to preparation."
        commentLabel="Reason of the reversal"
        commentRequired
        danger
        confirmLabel="Reverse"
        onClose={() => setReversing(false)}
        onConfirm={async (v) => {
          await api.post(`payroll/periods/${id}/reverse/`, { reason: v.comment });
          toast.success("Payroll reversed");
          reload();
          setRefresh((r) => r + 1);
        }}
      />
    </>
  );
}

function PeriodPayslips({ periodId, refresh }: { periodId: number; refresh: number }) {
  const navigate = useNavigate();
  const { can_view_salary } = usePermissions();
  const [selected, setSelected] = useState<(string | number)[]>([]);
  const { rows, loading } = useApiList<any>("payroll/payslips/", { period: periodId, _: refresh });
  if (!can_view_salary) return <Banner tone="info">Your profile gives access to consolidated amounts only.</Banner>;
  return (
    <Card
      padded={false}
      title="Payslips"
      actions={
        <>
          <DownloadButton url={`payroll/periods/${periodId}/batch_payslips/`} method="post" data={{}} label="Print all (one file)" />
          {selected.length > 0 && (
            <DownloadButton url={`payroll/periods/${periodId}/batch_payslips/`} method="post" data={{ employees: rows.filter((r) => selected.includes(r.id)).map((r) => r.employee) }} label={`Print selection (${selected.length})`} className="btn-primary" />
          )}
        </>
      }
    >
      <DataTable exportTitle="Payslips of the period"
        rows={rows}
        loading={loading}
        selectable
        selected={selected}
        onSelect={setSelected}
        onRowClick={(p: any) => navigate(`/payroll/payslips/${p.id}`)}
        columns={[
          { key: "employee_name", header: "Employee", render: (p: any) => <span className="font-medium text-primary-c">{p.employee_name}</span> },
          { key: "department_name", header: "Department" },
          { key: "paid_days", header: "Days", align: "end", render: (p: any) => fmt.number(p.paid_days, 0) },
          { key: "gross", header: "Gross", align: "end", render: (p: any) => fmt.money(p.gross) },
          { key: "taxes", header: "Taxes", align: "end", render: (p: any) => fmt.money(p.taxes) },
          { key: "net_payable", header: "Net payable", align: "end", render: (p: any) => <span className="mono font-semibold">{fmt.money(p.net_payable)}</span> },
          { key: "status", header: "Status", render: (p: any) => (
            <span className="inline-flex gap-1">
              <StatusBadge value={p.status} />
              {p.has_blocking_anomaly && <Badge tone="red">Anomaly</Badge>}
            </span>
          ) },
        ]}
      />
    </Card>
  );
}

function Anomalies({ periodId, refresh }: { periodId: number; refresh: number }) {
  const { rows, loading } = useApiList<any>(`payroll/periods/${periodId}/anomalies/`, { _: refresh });
  return (
    <Card padded={false} title="Anomalies" actions={<span className="text-xs text-muted-c">Blocking anomalies prevent the validation.</span>}>
      <DataTable exportTitle="Payroll anomalies"
        rows={rows}
        loading={loading}
        rowKey={(r: any) => `${r.payslip}-${r.code}`}
        empty="No anomaly."
        columns={[
          { key: "employee", header: "Employee" },
          { key: "code", header: "Control", mono: true },
          { key: "message", header: "Message" },
          { key: "blocking", header: "", render: (r: any) => (r.blocking ? <Badge tone="red">Blocking</Badge> : <Badge tone="yellow">Warning</Badge>) },
        ]}
      />
    </Card>
  );
}

function Comparison({ periodId }: { periodId: number }) {
  const { data, loading } = useApiItem<any>(`payroll/periods/${periodId}/comparison/`);
  const [onlySignificant, setOnlySignificant] = useState(true);
  if (loading || !data) return <Spinner />;
  const rows = (data.rows || []).filter((r: any) => !onlySignificant || r.significant);
  return (
    <Card
      padded={false}
      title={`Comparison with ${data.previous_period || "the previous period"}`}
      actions={
        <label className="flex items-center gap-2 text-sm text-secondary-c">
          <input type="checkbox" className="accent-brand-500" checked={onlySignificant} onChange={(e) => setOnlySignificant(e.target.checked)} />
          Only variations ≥ {data.threshold}%
        </label>
      }
    >
      <DataTable exportTitle="Comparison with the previous period"
        rows={rows}
        rowKey={(r: any) => `${r.employee_id}-${r.code}-${r.label}`}
        empty="No variation."
        columns={[
          { key: "employee", header: "Employee" },
          { key: "label", header: "Item" },
          { key: "previous", header: "Previous", align: "end", render: (r: any) => fmt.money(r.previous) },
          { key: "current", header: "Current", align: "end", render: (r: any) => fmt.money(r.current) },
          { key: "difference", header: "Difference", align: "end", render: (r: any) => fmt.money(r.difference) },
          { key: "variation_percent", header: "%", align: "end", render: (r: any) => (
            <span className={r.significant ? "font-semibold text-error-600" : ""}>{fmt.number(r.variation_percent, 1)}%</span>
          ) },
          { key: "status", header: "", render: (r: any) => <StatusBadge value={r.status} /> },
        ]}
      />
    </Card>
  );
}

function Declarations({ periodId }: { periodId: number }) {
  const { rows, loading } = useApiList<any>(`payroll/periods/${periodId}/declarations/`);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <DownloadButton url={`payroll/periods/${periodId}/contribution_statement/`} label="Statement of contributions (PDF)" />
        {BODIES.map((b) => (
          <DownloadButton key={b.value} url={`payroll/periods/${periodId}/declaration_export/`} params={{ body: b.value }} label={`${b.value} declaration file`} />
        ))}
      </div>
      {loading ? <Spinner /> : rows.map((body: any) => (
        <Card key={body.body} padded={false} title={`${BODIES.find((b) => b.value === body.body)?.label || body.body} – due ${fmt.date(body.due_date)}`}
          actions={<span className="mono text-sm font-semibold">{fmt.money(body.total)}</span>}>
          <DataTable exportTitle="Contribution statement"
            rows={body.items}
            rowKey={(r: any) => r.code}
            columns={[
              { key: "label", header: "Item" },
              { key: "base", header: "Base", align: "end", render: (r: any) => fmt.money(r.base) },
              { key: "employee", header: "Employee share", align: "end", render: (r: any) => fmt.money(r.employee) },
              { key: "employer", header: "Employer share", align: "end", render: (r: any) => fmt.money(r.employer) },
            ]}
          />
        </Card>
      ))}
    </div>
  );
}

function Payments({ periodId }: { periodId: number }) {
  const { data } = useApiItem<any>(`payroll/periods/${periodId}/payments/`);
  const { data: provisions } = useApiItem<any>(`payroll/periods/${periodId}/provisions/`);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Payment of the salaries" actions={
        <>
          <DownloadButton url={`payroll/periods/${periodId}/payment_order/`} label="Payment orders" />
          <DownloadButton url={`payroll/periods/${periodId}/bank_file/`} label="Bank file" />
          <DownloadButton url={`payroll/periods/${periodId}/cash_list/`} label="Cash list" />
        </>
      }>
        {data ? (
          <dl className="space-y-2 text-sm">
            {Object.entries(data.by_method || {}).map(([method, total]) => (
              <div key={method} className="flex justify-between"><dt>{method}</dt><dd className="mono">{fmt.money(total)}</dd></div>
            ))}
            {Object.entries(data.by_bank || {}).map(([bank, info]: [string, any]) => (
              <div key={bank} className="flex justify-between text-secondary-c"><dt>↳ {bank} ({info.count})</dt><dd className="mono">{fmt.money(info.total)}</dd></div>
            ))}
            <div className="flex justify-between border-t pt-2 font-semibold" style={{ borderColor: "var(--border-color)" }}><dt>Total</dt><dd className="mono">{fmt.money(data.total)}</dd></div>
          </dl>
        ) : <Spinner />}
      </Card>
      <Card title="Provision for leave not taken" padded={false}>
        <DataTable exportTitle="Provision for leave not taken"
          rows={provisions?.rows || []}
          rowKey={(r: any) => r.employee}
          empty="Computed at the validation."
          columns={[
            { key: "employee", header: "Employee" },
            { key: "days", header: "Days", align: "end", render: (r: any) => fmt.number(r.days) },
            { key: "amount", header: "Provision", align: "end", render: (r: any) => fmt.money(r.amount) },
          ]}
        />
      </Card>
    </div>
  );
}

function PeriodDocuments({ periodId }: { periodId: number }) {
  return (
    <Card title="Documents of the period">
      <div className="flex flex-wrap gap-2">
        <DownloadButton url={`payroll/periods/${periodId}/payroll_book/`} label="Payroll book (PDF)" />
        <ExportButtons url={`payroll/periods/${periodId}/payroll_book/`} formats={["xlsx", "csv"]} />
        <DownloadButton url={`payroll/periods/${periodId}/contribution_statement/`} label="Contributions and taxes" />
        <DownloadButton url={`payroll/periods/${periodId}/batch_payslips/`} method="post" data={{}} label="All payslips" />
        <DownloadButton url={`payroll/periods/${periodId}/payment_order/`} label="Payment orders" />
        <DownloadButton url={`payroll/periods/${periodId}/cash_list/`} label="Cash payment list" />
      </div>
    </Card>
  );
}

function Accounting({ periodId }: { periodId: number }) {
  const navigate = useNavigate();
  const { data, loading } = useApiItem<any>(`accounting/entries/reconciliation/?payroll_period=${periodId}`);
  const { rows } = useApiList<any>("accounting/entries/", { payroll_period: periodId });
  return (
    <div className="space-y-4">
      <Card title="Reconciliation payroll ↔ accounting" actions={data && (<>{data.ok ? <Badge tone="green">Reconciled</Badge> : <Badge tone="red">Not reconciled</Badge>}<DownloadButton url={`accounting/documents/reconciliation/${periodId}/`} label="PDF" /></>)}>
        {loading || !data ? <Spinner /> : !data.posted ? <Banner tone="info">The entry is generated at the validation of the payroll.</Banner> : (
          <DataTable
            rows={data.checks}
            rowKey={(r: any) => r.label}
            columns={[
              { key: "label", header: "Control" },
              { key: "payroll", header: "Payroll", align: "end", render: (r: any) => fmt.money(r.payroll) },
              { key: "accounting", header: "Accounting", align: "end", render: (r: any) => fmt.money(r.accounting) },
              { key: "difference", header: "Difference", align: "end", render: (r: any) => <span className={Number(r.difference) ? "text-error-600" : ""}>{fmt.money(r.difference)}</span> },
            ]}
          />
        )}
      </Card>
      <Card padded={false} title="Entries of the period">
        <DataTable exportTitle="Accounting entries of the period"
          rows={rows}
          onRowClick={() => navigate("/accounting#entries")}
          columns={[
            { key: "number", header: "Number", mono: true },
            { key: "date", header: "Date", render: (e: any) => fmt.date(e.date) },
            { key: "label", header: "Label" },
            { key: "source", header: "Type", render: (e: any) => <StatusBadge value={e.source} /> },
            { key: "total_debit", header: "Amount", align: "end", render: (e: any) => fmt.money(e.total_debit) },
            { key: "is_reversed", header: "", render: (e: any) => (e.is_reversed ? <Badge tone="red">Reversed</Badge> : null) },
          ]}
        />
      </Card>
    </div>
  );
}
