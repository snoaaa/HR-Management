import { useState } from "react";
import type { ReactNode } from "react";
import { fmt } from "@/api/helpers";
import { DownloadButton, ExportButtons } from "@/components/kit/CrudSection";
import SearchSelect from "@/components/kit/SearchSelect";
import { Card, Field } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";

const year = new Date().getFullYear();

function DocumentCard({ title, description, children, actions }: {
  title: string;
  /** Internal requirement reference (not displayed). */
  reference?: string;
  description: string;
  children?: ReactNode;
  actions: ReactNode;
}) {
  return (
    <div className="flex flex-col rounded-lg border p-4" style={{ borderColor: "var(--border-color)" }}>
      <div className="mb-1 flex items-start justify-between gap-2">
        <h3 className="font-semibold text-primary-c">{title}</h3>
      </div>
      <p className="mb-3 text-xs text-muted-c">{description}</p>
      {children && <div className="mb-3 space-y-2">{children}</div>}
      <div className="mt-auto flex flex-wrap gap-2">{actions}</div>
    </div>
  );
}

/**
 * BN-141 → BN-145: every accounting document of the payroll, extracted as a
 * PDF in the colours of the organisation, as Excel or as CSV.
 */
export default function AccountingDocuments() {
  const { can } = usePermissions();
  const [range, setRange] = useState({ start: `${year}-01-01`, end: `${year}-12-31` });
  const [account, setAccount] = useState("");
  const [journal, setJournal] = useState<number | null>(null);
  const [groupBy, setGroupBy] = useState("department");
  const [period, setPeriod] = useState<number | null>(null);
  const [entry, setEntry] = useState<number | null>(null);
  const fiscalYear = range.end.slice(0, 4);
  const book = (name: string, params: Record<string, unknown> = {}, formats: ("pdf" | "xlsx" | "csv")[] = ["pdf", "xlsx", "csv"]) => (
    <ExportButtons url={`accounting/books/${name}/`} params={{ ...range, ...params }} formats={formats} />
  );
  return (
    <div className="space-y-4">
      <Card title="Period of the documents">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="From"><input type="date" className="input-field w-44" value={range.start} onChange={(e) => setRange({ ...range, start: e.target.value })} /></Field>
          <Field label="To"><input type="date" className="input-field w-44" value={range.end} onChange={(e) => setRange({ ...range, end: e.target.value })} /></Field>
          <div className="flex flex-wrap gap-1">
            {[["Current year", `${year}-01-01`, `${year}-12-31`], ["Previous year", `${year - 1}-01-01`, `${year - 1}-12-31`]].map(([label, start, end]) => (
              <button key={label} type="button" className="btn-ghost text-xs" onClick={() => setRange({ start, end })}>{label}</button>
            ))}
          </div>
          <p className="text-xs text-muted-c">Every PDF carries the logo and the legal identification of the organisation.</p>
        </div>
      </Card>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <DocumentCard title="Journal book" reference="BN-141" description={`Entries of the period with their lines, in date order (${fmt.date(range.start)} – ${fmt.date(range.end)}).`}
          actions={book("journal", journal ? { journal } : {})}>
          <SearchSelect url="accounting/journals/" value={journal} onChange={setJournal} label={(j: any) => `${j.code} – ${j.name}`} placeholder="All journals" />
        </DocumentCard>
        <DocumentCard title="General ledger" reference="BN-141" description="Movements and running balance of each account, with the opening balance."
          actions={book("ledger", account ? { account } : {})}>
          <input className="input-field" placeholder="Accounts starting with… (e.g. 42, 66)" value={account} onChange={(e) => setAccount(e.target.value.replace(/\D/g, ""))} />
        </DocumentCard>
        <DocumentCard title="Trial balance" reference="BN-141" description="Opening balances, movements and closing balances of every account used by the payroll."
          actions={book("trial-balance")} />
        <DocumentCard title="Personnel and social bodies balances" reference="BN-141" description={`What is owed to each employee (42) and to the CNPS, the tax administration and the councils (43, 44) on ${fmt.date(range.end)}.`}
          actions={book("balances")} />
        <DocumentCard title="Analysis of the personnel expenses" reference="BN-144" description="Expenses of class 66 compared with the budget."
          actions={book("analysis", { group_by: groupBy })}>
          <select className="input-field" value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
            <option value="department">By department</option>
            <option value="cost_centre">By cost centre</option>
            <option value="account">By account</option>
            <option value="month">By month</option>
          </select>
        </DocumentCard>
        <DocumentCard title="Financial statements items" reference="BN-145" description={`Personnel items of the OHADA annual financial statements, financial year ${fiscalYear}.`}
          actions={book("financial-statements", { year: fiscalYear })} />
        <DocumentCard title="List of the entries" reference="BN-138" description="Every entry of the period with its debit and credit totals."
          actions={book("entries")} />
        <DocumentCard title="Payroll / accounting reconciliation" reference="BN-142" description="Control of the payroll of a period against the entries posted."
          actions={<DownloadButton url={`accounting/documents/reconciliation/${period}/`} label="PDF" className="btn-secondary" disabled={!period} />}>
          <SearchSelect url="payroll/periods/" value={period} onChange={setPeriod}
            label={(p: any) => `${String(p.month).padStart(2, "0")}/${p.year} – ${p.status_label || p.status}`} placeholder="Payroll period" />
        </DocumentCard>
        <DocumentCard title="Accounting voucher" reference="BN-138" description="One entry with its lines, analytic breakdown and the signature boxes."
          actions={<DownloadButton url={`accounting/documents/voucher/${entry}/`} label="PDF" className="btn-secondary" disabled={!entry} />}>
          <SearchSelect url="accounting/entries/" value={entry} onChange={setEntry}
            label={(e: any) => `${e.number} – ${e.label} (${fmt.date(e.date)})`} placeholder="Search an entry by number or label" />
        </DocumentCard>
        {can("accounting", "export") && (
          <DocumentCard title="Transfer to the accounting software" reference="BN-143" description="Standard CSV of the entries (journal, account, debit, credit, analytic, third party)."
            actions={
              <>
                <DownloadButton url="accounting/entries/export/" params={{ only_new: "true", date__gte: range.start, date__lte: range.end }} label="New entries" className="btn-primary" />
                <DownloadButton url="accounting/entries/export/" params={{ date__gte: range.start, date__lte: range.end }} label="All the period" />
              </>
            } />
        )}
      </div>
    </div>
  );
}
