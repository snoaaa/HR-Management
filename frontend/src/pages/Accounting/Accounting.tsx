import { useState } from "react";
import { confirmDialog } from "@/components/kit/confirm";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { BarList } from "@/components/kit/Charts";
import CrudSection, { DownloadButton, ExportButtons } from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { PromptModal } from "@/components/kit/Form";
import { useApiItem, useApiList, useHashTab } from "@/components/kit/hooks";
import { BODIES, accountField, departmentField, opt, periodField } from "@/components/kit/options";
import { Badge, Banner, Card, DefinitionList, Modal, PageHeader, Spinner, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import AccountingDocuments from "./AccountingDocuments";
import { useToast } from "@/context/ToastContext";

const year = new Date().getFullYear();

function DateRange({ value, onChange }: { value: { start: string; end: string }; onChange: (v: { start: string; end: string }) => void }) {
  return (
    <span className="flex flex-wrap items-center gap-2">
      <input type="date" className="input-field w-40" value={value.start} onChange={(e) => onChange({ ...value, start: e.target.value })} />
      <span className="text-muted-c">→</span>
      <input type="date" className="input-field w-40" value={value.end} onChange={(e) => onChange({ ...value, end: e.target.value })} />
    </span>
  );
}

function Entries() {
  const toast = useToast();
  const { can } = usePermissions();
  const { rows, loading, reload } = useApiList<any>("accounting/entries/");
  const [open, setOpen] = useState<number | null>(null);
  const [action, setAction] = useState<"generate" | "pay" | "settle" | null>(null);
  const { data: entry } = useApiItem<any>(open ? `accounting/entries/${open}/` : null);
  const reverse = async (id: number) => {
    if (!(await confirmDialog({ title: "Post a reversal entry?", message: "A new entry cancels this one. The original entry stays unchanged.", confirmLabel: "Post the reversal" }))) return;
    try {
      await api.post(`accounting/entries/${id}/reverse/`);
      toast.success("Reversal posted");
      setOpen(null);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <Card
      padded={false}
      title="Entries (immutable, numbered per journal)"
      actions={
        <>
          {can("accounting", "create") && (
            <>
              <button type="button" className="btn-secondary" onClick={() => setAction("generate")}>Generate payroll entry</button>
              <button type="button" className="btn-secondary" onClick={() => setAction("pay")}>Payment entry</button>
              <button type="button" className="btn-secondary" onClick={() => setAction("settle")}>Settle a body</button>
            </>
          )}
          {can("accounting", "export") && (
            <>
              <DownloadButton url="accounting/entries/export/" params={{ only_new: "true" }} label="Export new entries" className="btn-primary" />
              <DownloadButton url="accounting/entries/export/" label="Export all" />
            </>
          )}
        </>
      }
    >
      <DataTable
        exportTitle="Accounting entries"
        rows={rows}
        loading={loading}
        onRowClick={(e: any) => setOpen(e.id)}
        columns={[
          { key: "number", header: "Number", mono: true },
          { key: "date", header: "Date", render: (e: any) => fmt.date(e.date) },
          { key: "journal_code", header: "Journal" },
          { key: "label", header: "Label" },
          { key: "source", header: "Type", render: (e: any) => <StatusBadge value={e.source} /> },
          { key: "total_debit", header: "Amount", align: "end", render: (e: any) => fmt.money(e.total_debit) },
          { key: "exported_at", header: "Exported", render: (e: any) => (e.exported_at ? fmt.date(e.exported_at) : "—") },
          { key: "is_reversed", header: "", render: (e: any) => (e.is_reversed ? <Badge tone="red">Reversed</Badge> : null) },
        ]}
      />
      <Modal open={!!open} title={entry ? `${entry.number} – ${entry.label}` : "Entry"} onClose={() => setOpen(null)} size="xl"
        footer={entry && (
          <>
            <DownloadButton url={`accounting/documents/voucher/${entry.id}/`} label="Voucher (PDF)" />
            {!entry.is_reversed && entry.source !== "REVERSAL" && can("accounting", "modify") && (
              <button type="button" className="btn-danger" onClick={() => reverse(entry.id)}>Post a reversal</button>
            )}
          </>
        )}>
        {!entry ? <Spinner /> : (
          <div className="space-y-4">
            <DefinitionList items={[["Date", fmt.date(entry.date)], ["Journal", entry.journal_code], ["Payroll period", entry.payroll_period_label],
              ["Reference", entry.reference || "—"]]} />
            <DataTable
              dense
              rows={entry.lines}
              columns={[
                { key: "account_number", header: "Account", mono: true },
                { key: "account_name", header: "Name" },
                { key: "label", header: "Label" },
                { key: "analytic", header: "Analytic", render: (l: any) => l.department_name || l.cost_centre_name || l.employee_name || "" },
                { key: "debit", header: "Debit", align: "end", render: (l: any) => (Number(l.debit) ? fmt.money(l.debit) : "") },
                { key: "credit", header: "Credit", align: "end", render: (l: any) => (Number(l.credit) ? fmt.money(l.credit) : "") },
              ]}
              footer={
                <tr className="font-semibold">
                  <td className="table-cell" colSpan={4}>Totals</td>
                  <td className="table-cell text-end mono">{fmt.money(entry.total_debit)}</td>
                  <td className="table-cell text-end mono">{fmt.money(entry.total_credit)}</td>
                </tr>
              }
            />
          </div>
        )}
      </Modal>
      <PromptModal
        open={!!action}
        title={action === "generate" ? "Generate the payroll entry" : action === "pay" ? "Entry of payment of salaries" : "Settlement of contributions / taxes"}
        extraFields={[
          periodField("payroll_period"),
          ...(action === "settle" ? [{ name: "body", label: "Body", type: "select" as const, required: true, options: BODIES }, { name: "date", label: "Date of payment", type: "date" as const }] : []),
        ]}
        onClose={() => setAction(null)}
        onConfirm={async (v) => {
          await api.post(`accounting/entries/${action}/`, v);
          toast.success("Entry posted");
          reload();
        }}
      />
    </Card>
  );
}

function Books() {
  const [book, setBook] = useState("trial-balance");
  const [range, setRange] = useState({ start: `${year}-01-01`, end: `${year}-12-31` });
  const [account, setAccount] = useState("");
  const params = { ...range, ...(book === "ledger" && account ? { account } : {}) };
  const { data, loading } = useApiItem<any>(`accounting/books/${book}/?${new URLSearchParams(params as any)}`);
  return (
    <Card
      padded={false}
      title="Accounting books"
      actions={
        <>
          <select className="input-field w-auto" value={book} onChange={(e) => setBook(e.target.value)}>
            <option value="trial-balance">Trial balance</option>
            <option value="ledger">General ledger</option>
            <option value="journal">Journal book</option>
            <option value="balances">Balances per employee and body</option>
          </select>
          {book === "ledger" && <input className="input-field w-36" placeholder="Account (e.g. 42)" value={account} onChange={(e) => setAccount(e.target.value)} />}
          <DateRange value={range} onChange={setRange} />
          <ExportButtons url={`accounting/books/${book}/`} params={params} formats={["pdf", "xlsx", "csv"]} />
        </>
      }
    >
      {loading || !data ? <Spinner /> : book === "trial-balance" ? (
        <DataTable rows={data} rowKey={(r: any) => r.account} columns={[
          { key: "account", header: "Account", mono: true },
          { key: "name", header: "Name" },
          { key: "opening", header: "Opening", align: "end", render: (r: any) => fmt.money(r.opening) },
          { key: "debit", header: "Debit", align: "end", render: (r: any) => fmt.money(r.debit) },
          { key: "credit", header: "Credit", align: "end", render: (r: any) => fmt.money(r.credit) },
          { key: "closing_debit", header: "Closing debit", align: "end", render: (r: any) => (Number(r.closing_debit) ? fmt.money(r.closing_debit) : "") },
          { key: "closing_credit", header: "Closing credit", align: "end", render: (r: any) => (Number(r.closing_credit) ? fmt.money(r.closing_credit) : "") },
        ]} />
      ) : book === "ledger" ? (
        <div className="space-y-4 p-4">
          {data.map((a: any) => (
            <div key={a.account}>
              <p className="mb-1 font-semibold text-primary-c">{a.account} – {a.name} <span className="text-xs text-muted-c">opening {fmt.money(a.opening)} · closing {fmt.money(a.closing)}</span></p>
              <DataTable dense rows={a.lines} rowKey={(l: any) => `${l.entry}-${l.label}-${l.debit}-${l.credit}`} columns={[
                { key: "date", header: "Date", render: (l: any) => fmt.date(l.date) },
                { key: "entry", header: "Entry", mono: true },
                { key: "label", header: "Label" },
                { key: "employee", header: "Employee" },
                { key: "debit", header: "Debit", align: "end", render: (l: any) => (Number(l.debit) ? fmt.money(l.debit) : "") },
                { key: "credit", header: "Credit", align: "end", render: (l: any) => (Number(l.credit) ? fmt.money(l.credit) : "") },
                { key: "balance", header: "Balance", align: "end", render: (l: any) => fmt.money(l.balance) },
              ]} />
            </div>
          ))}
        </div>
      ) : book === "journal" ? (
        <DataTable rows={data} columns={[
          { key: "number", header: "Number", mono: true },
          { key: "date", header: "Date", render: (e: any) => fmt.date(e.date) },
          { key: "label", header: "Label" },
          { key: "total_debit", header: "Debit", align: "end", render: (e: any) => fmt.money(e.total_debit) },
          { key: "total_credit", header: "Credit", align: "end", render: (e: any) => fmt.money(e.total_credit) },
        ]} />
      ) : (
        <div className="grid gap-4 p-4 lg:grid-cols-2">
          <div>
            <p className="section-label mb-2">Personnel (accounts 42, per employee)</p>
            <DataTable dense rows={data.employees} rowKey={(r: any) => `${r.employee_id}-${r.account}`} columns={[
              { key: "employee", header: "Employee" }, { key: "account", header: "Account", mono: true },
              { key: "balance", header: "Balance", align: "end", render: (r: any) => fmt.money(r.balance) },
            ]} empty="All personnel accounts are settled." />
          </div>
          <div>
            <p className="section-label mb-2">Social bodies and State (43, 44)</p>
            <DataTable dense rows={data.bodies} rowKey={(r: any) => r.account} columns={[
              { key: "account", header: "Account", mono: true }, { key: "name", header: "Name" },
              { key: "balance", header: "To pay", align: "end", render: (r: any) => fmt.money(r.balance) },
            ]} />
          </div>
        </div>
      )}
    </Card>
  );
}

function Analysis() {
  const [groupBy, setGroupBy] = useState("department");
  const [range, setRange] = useState({ start: `${year}-01-01`, end: `${year}-12-31` });
  const { rows, loading } = useApiList<any>("accounting/books/analysis/", { ...range, group_by: groupBy });
  const { data: statements } = useApiItem<any>(`accounting/books/financial-statements/?year=${range.start.slice(0, 4)}`);
  const { can } = usePermissions();
  return (
    <div className="space-y-4">
      <Card title="Personnel expenses" actions={
        <>
          <select className="input-field w-auto" value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
            <option value="department">By department</option>
            <option value="cost_centre">By cost centre</option>
            <option value="account">By account</option>
            <option value="month">By month</option>
          </select>
          <DateRange value={range} onChange={setRange} />
          <ExportButtons url="accounting/books/analysis/" params={{ ...range, group_by: groupBy }} formats={["pdf", "xlsx"]} />
        </>
      }>
        {loading ? <Spinner /> : (
          <div className="grid gap-6 lg:grid-cols-2">
            <BarList data={rows.map((r: any) => ({ label: r.key, value: r.amount }))} format={(v) => fmt.money(v)} />
            <DataTable dense rows={rows} rowKey={(r: any) => String(r.key)} columns={[
              { key: "key", header: groupBy === "month" ? "Month" : "Item" },
              { key: "amount", header: "Actual", align: "end", render: (r: any) => fmt.money(r.amount) },
              { key: "budget", header: "Budget", align: "end", render: (r: any) => (r.budget != null ? fmt.money(r.budget) : "—") },
              { key: "variance", header: "Variance", align: "end", render: (r: any) => (r.variance != null ? <span className={Number(r.variance) > 0 ? "text-error-600" : "text-success-600"}>{fmt.money(r.variance)}</span> : "—") },
            ]} />
          </div>
        )}
      </Card>
      <Card title={`Elements for the OHADA financial statements ${range.start.slice(0, 4)}`}
        actions={<ExportButtons url="accounting/books/financial-statements/" params={{ year: range.start.slice(0, 4) }} formats={["pdf", "xlsx"]} />}>
        {statements ? (
          <DefinitionList items={[
            ["Personnel expenses (66)", fmt.money(statements.personnel_expenses_66)],
            ["Taxes on salaries (6413)", fmt.money(statements.taxes_on_salaries_6413)],
            ["Liabilities to the personnel (42)", fmt.money(statements.liabilities_to_personnel_42)],
            ["Liabilities to social bodies (43)", fmt.money(statements.liabilities_to_social_bodies_43)],
            ["Liabilities to the State (44)", fmt.money(statements.liabilities_to_state_44)],
            ["Average headcount (notes)", fmt.number(statements.average_headcount, 1)],
          ]} />
        ) : <Spinner />}
      </Card>
      <CrudSection
        endpoint="accounting/budgets/"
        title="Budgets"
        canCreate={can("accounting", "modify")}
        canEdit={can("accounting", "modify")}
        canDelete={can("accounting", "modify")}
        fields={[{ name: "year", label: "Year", type: "number", required: true }, departmentField(), accountField(), { name: "amount", label: "Amount", type: "number", required: true }]}
        defaults={{ year }}
        columns={[
          { key: "year", header: "Year" },
          { key: "department_name", header: "Department" },
          { key: "account_label", header: "Account" },
          { key: "amount", header: "Budget", align: "end", render: (b: any) => fmt.money(b.amount) },
        ]}
      />
    </div>
  );
}

function ChartOfAccounts() {
  const toast = useToast();
  const { can } = usePermissions();
  const [report, setReport] = useState<any>(null);
  const [key, setKey] = useState(0);
  const upload = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    try {
      setReport((await api.post("accounting/accounts/import/", form)).data);
      setKey((k) => k + 1);
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <div className="space-y-3">
      {report && <Banner tone={report.rejected.length ? "warning" : "success"}>{report.created} created, {report.updated} updated, {report.rejected.length} rejected.</Banner>}
      <CrudSection
        key={key}
        endpoint="accounting/accounts/"
        title="Chart of accounts (SYSCOHADA)"
        canCreate={can("accounting", "modify")}
        canEdit={can("accounting", "modify")}
        canDelete={can("accounting", "modify")}
        toolbar={() =>
          can("accounting", "modify") && (
            <label className="btn-secondary cursor-pointer">
              Import (number;name)
              <input type="file" accept=".csv" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
            </label>
          )
        }
        fields={[{ name: "number", label: "Number", required: true }, { name: "name", label: "Name", required: true }, { name: "is_active", label: "Active", type: "checkbox" }]}
        defaults={{ is_active: true }}
        columns={[
          { key: "number", header: "Number", mono: true },
          { key: "name", header: "Name" },
          { key: "account_class", header: "Class", align: "center" },
          { key: "is_active", header: "", render: (a: any) => (a.is_active ? null : <Badge>Inactive</Badge>) },
        ]}
      />
    </div>
  );
}

const SOURCES = opt([["ELEMENT", "Salary element"], ["DEDUCTION", "Statutory deduction"], ["LOAN", "Loan / advance"], ["THIRD_PARTY", "Third-party deduction"],
  ["NET_PAY", "Net remuneration due"], ["BANK", "Bank"], ["CASH", "Cash"], ["PROVISION", "Leave provision"]]);

function FiscalYears() {
  const toast = useToast();
  const { can } = usePermissions();
  const { rows, reload } = useApiList<any>("accounting/fiscal-years/");
  const act = async (url: string, data?: any) => {
    try {
      await api.post(url, data);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <div className="space-y-4">
      {can("accounting", "modify") && (
        <button type="button" className="btn-secondary" onClick={() => act("accounting/fiscal-years/", { year: (rows[0]?.year || year - 1) + 1 })}>
          + Open the next financial year
        </button>
      )}
      {rows.map((fy: any) => (
        <Card key={fy.id} title={`Financial year ${fy.year}`} actions={
          <>
            <StatusBadge value={fy.status === "CLOSED" ? "CLOSED" : "OPENED"} label={fy.status === "CLOSED" ? "Closed" : "Open"} />
            {fy.status === "OPEN" && can("accounting", "validate") && (
              <button type="button" className="btn-danger" onClick={async () => (await confirmDialog({ title: `Close the financial year ${fy.year}?`, message: "Once closed, no entry can be posted in this year any more.", confirmLabel: "Close the year", danger: true })) && act(`accounting/fiscal-years/${fy.id}/close/`)}>
                Close the year
              </button>
            )}
          </>
        }>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-6 lg:grid-cols-12">
            {fy.periods.map((p: any) => (
              <button
                key={p.id}
                type="button"
                disabled={fy.status === "CLOSED" || !can("accounting", "validate")}
                onClick={() => act(`accounting/fiscal-years/${fy.id}/${p.status === "OPEN" ? "close_period" : "reopen_period"}/`, { month: p.month })}
                className="rounded-lg border px-2 py-2 text-xs font-semibold"
                style={{ borderColor: "var(--border-color)", background: p.status === "CLOSED" ? "var(--surface-3)" : "var(--surface)" }}
                title={p.status === "OPEN" ? "Click to close" : "Click to reopen"}
              >
                {String(p.month).padStart(2, "0")}
                <br />
                <span className={p.status === "OPEN" ? "text-success-600" : "text-muted-c"}>{p.status === "OPEN" ? "open" : "closed"}</span>
              </button>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}

/** M-13 – accounting of the payroll according to OHADA. */
export default function Accounting() {
  const [tab, setTab] = useHashTab("entries");
  const { can } = usePermissions();
  const edit = can("accounting", "modify");
  return (
    <>
      <PageHeader title="Payroll accounting (OHADA)" eyebrow="Accounting" subtitle="Entries generated by the payroll, balanced by construction and exported to the accounting software." />
      <Tabs active={tab} onChange={setTab} tabs={[
        { id: "entries", label: "Entries" },
        { id: "books", label: "Books" },
        { id: "documents", label: "Documents (PDF / Excel)" },
        { id: "analysis", label: "Analysis & budget" },
        { id: "accounts", label: "Chart of accounts" },
        { id: "mappings", label: "Account mapping" },
        { id: "years", label: "Financial years" },
      ]} />
      {tab === "entries" && <Entries />}
      {tab === "books" && <Books />}
      {tab === "documents" && <AccountingDocuments />}
      {tab === "analysis" && <Analysis />}
      {tab === "accounts" && <ChartOfAccounts />}
      {tab === "mappings" && (
        <CrudSection
          endpoint="accounting/mappings/"
          title="Mapping of the payroll items to the accounts"
          description="An empty code is the default of the type. Add a new version with a later date to change a mapping."
          canCreate={edit} canEdit={edit} canDelete={edit} modalSize="lg"
          fields={[
            { name: "source_type", label: "Item", type: "select", required: true, options: SOURCES },
            { name: "source_code", label: "Code (element or deduction)", placeholder: "Empty = default" },
            accountField("debit_account", "Debit account"),
            accountField("credit_account", "Credit account"),
            accountField("employer_debit_account", "Employer share – expense account"),
            accountField("employer_credit_account", "Employer share – body account"),
            { name: "effective_from", label: "From", type: "date", required: true },
          ]}
          columns={[
            { key: "source_type", header: "Item", render: (m: any) => SOURCES.find((s) => s.value === m.source_type)?.label },
            { key: "source_code", header: "Code", mono: true, render: (m: any) => m.source_code || <span className="text-muted-c">default</span> },
            { key: "debit_label", header: "Debit" },
            { key: "credit_label", header: "Credit" },
            { key: "employer", header: "Employer share", render: (m: any) => (m.employer_debit_label ? `${m.employer_debit_label} / ${m.employer_credit_label}` : "") },
            { key: "effective_from", header: "From", render: (m: any) => fmt.date(m.effective_from) },
          ]}
        />
      )}
      {tab === "years" && <FiscalYears />}
    </>
  );
}
