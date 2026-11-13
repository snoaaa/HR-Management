import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { DownloadButton } from "@/components/kit/CrudSection";
import { matchesSearch } from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { useApiItem, useApiList } from "@/components/kit/hooks";
import SearchSelect from "@/components/kit/SearchSelect";
import { Badge, Banner, Card, DefinitionList, KpiTile, PageHeader, Spinner, StatusBadge } from "@/components/kit/ui";
import { useToast } from "@/context/ToastContext";

/** Payslips of every period, searchable by employee. */
export function PayslipList() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const { rows, loading } = useApiList<any>("payroll/payslips/", period ? { period } : undefined);
  return (
    <>
      <PageHeader title="Payslips" eyebrow="Payroll" subtitle="Every consultation of a payslip is recorded in the audit trail." />
      <Card
        padded={false}
        actions={
          <>
            <SearchSelect
              className="w-60"
              url="payroll/periods/"
              value={period}
              label={(p) => `${String(p.month).padStart(2, "0")}/${p.year}`}
              placeholder="All periods – search…"
              onChange={(v) => setPeriod(v ? String(v) : null)}
            />
            <input type="search" className="input-field w-56" placeholder="Search an employee…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </>
        }
      >
        <DataTable exportTitle="Payslips"
          rows={rows.filter((r) => matchesSearch(r, search))}
          loading={loading}
          onRowClick={(p: any) => navigate(`/payroll/payslips/${p.id}`)}
          columns={[
            { key: "period_label", header: "Period" },
            { key: "employee_name", header: "Employee", render: (p: any) => <span className="font-medium text-primary-c">{p.employee_name}</span> },
            { key: "matriculation", header: "Matriculation", mono: true },
            { key: "gross", header: "Gross", align: "end", render: (p: any) => fmt.money(p.gross) },
            { key: "net_payable", header: "Net payable", align: "end", render: (p: any) => fmt.money(p.net_payable) },
            { key: "status", header: "Status", render: (p: any) => <StatusBadge value={p.status} /> },
          ]}
        />
      </Card>
    </>
  );
}

const GROUPS: [string, string[]][] = [
  ["Gains", ["GAIN"]],
  ["Deductions from gross", ["GROSS_DEDUCTION"]],
  ["Social contributions", ["CONTRIBUTION"]],
  ["Taxes withheld", ["TAX"]],
  ["Deductions from net", ["NET_DEDUCTION"]],
];

export function PayslipLines({ lines }: { lines: any[] }) {
  return (
    <div className="space-y-4">
      {GROUPS.map(([title, kinds]) => {
        const group = lines.filter((l) => kinds.includes(l.kind));
        if (!group.length) return null;
        return (
          <div key={title}>
            <p className="section-label mb-1">{title}</p>
            <DataTable
              dense
              rows={group}
              rowKey={(l: any) => `${l.code}-${l.label}-${l.amount}`}
              columns={[
                { key: "label", header: "Item", render: (l: any) => <span>{l.label} <span className="mono text-muted-c">{l.code}</span></span> },
                { key: "base", header: "Base", align: "end", render: (l: any) => (l.base ? fmt.money(l.base) : "") },
                { key: "rate", header: "Qty / rate", align: "end", render: (l: any) => (l.quantity ? fmt.number(l.quantity) : l.rate ? `${fmt.number(l.rate)}` : "") },
                { key: "amount", header: "Amount", align: "end", render: (l: any) => <span className="mono">{fmt.money(l.amount)}</span> },
                { key: "employer_amount", header: "Employer", align: "end", render: (l: any) => (Number(l.employer_amount) ? fmt.money(l.employer_amount) : "") },
              ]}
            />
          </div>
        );
      })}
    </div>
  );
}

/** BN-113: detail of a payslip with printing, duplicate and e-mail. */
export function PayslipDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { data: p } = useApiItem<any>(`payroll/payslips/${id}/`);
  if (!p) return <Spinner />;
  const email = async () => {
    try {
      const res = await api.post(`payroll/payslips/${id}/email/`);
      toast.success(res.data.detail);
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <>
      <PageHeader
        title={`Payslip ${p.period_label} – ${p.employee_name}`}
        eyebrow="Payroll"
        actions={
          <>
            <button type="button" className="btn-ghost" onClick={() => navigate(-1)}>← Back</button>
            <StatusBadge value={p.status} />
            <DownloadButton url={`payroll/payslips/${id}/pdf/`} label="Print" className="btn-primary" />
            <DownloadButton url={`payroll/payslips/${id}/pdf/`} params={{ duplicate: 1 }} label="Duplicate" />
            {p.status === "VALIDATED" && (
              <button type="button" className="btn-secondary" onClick={email}>E-mail (protected PDF)</button>
            )}
          </>
        }
      />
      {p.anomalies?.length > 0 && (
        <div className="mb-4 space-y-2">
          {p.anomalies.map((a: any) => (
            <Banner key={a.code} tone={a.blocking ? "error" : "warning"}>{a.message}</Banner>
          ))}
        </div>
      )}
      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiTile label="Gross" value={fmt.money(p.gross)} />
        <KpiTile label="Contributions + taxes" value={fmt.money(Number(p.employee_contributions) + Number(p.taxes))} accent="#E9730C" />
        <KpiTile label="Net payable" value={fmt.money(p.net_payable)} accent="var(--odoo-teal)" />
        <KpiTile label="Total cost" value={fmt.money(p.total_cost)} accent="#0A6ED1" />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Lines" className="lg:col-span-2">
          <PayslipLines lines={p.lines || []} />
        </Card>
        <Card title="Summary">
          <DefinitionList
            items={[
              ["Matriculation", p.matriculation],
              ["Department", p.department_name],
              ["Days paid", fmt.number(p.paid_days, 0)],
              ["Base salary", fmt.money(p.base_salary)],
              ["Contributory base", fmt.money(p.contributory_base)],
              ["Taxable base", fmt.money(p.taxable_base)],
              ["Employer contributions", fmt.money(p.employer_contributions)],
              ["Benefits in kind", fmt.money(p.benefits_in_kind)],
              ["Payment", `${p.payment_method}${p.bank_name ? ` – ${p.bank_name}` : ""}`],
              ["Leave balance", p.leave_balance != null ? `${fmt.number(p.leave_balance)} day(s)` : "—"],
            ]}
          />
          {p.reversal_of && <div className="mt-3"><Badge tone="orange">Replaces a reversed payslip</Badge></div>}
        </Card>
      </div>
    </>
  );
}
