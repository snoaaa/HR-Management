import { useEffect, useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { BarList, CHART_COLORS, ColumnChart } from "@/components/kit/Charts";
import CrudSection, { ExportButtons } from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { useApiItem, useHashTab } from "@/components/kit/hooks";
import { CONTRACT_TYPES, opt } from "@/components/kit/options";
import SearchSelect from "@/components/kit/SearchSelect";
import { Banner, Card, KpiTile, PageHeader, Spinner, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";

const year = new Date().getFullYear();

interface Filters { start: string; end: string; department?: string | null; site?: string | null; contract_type?: string }

function FilterBar({ value, onChange }: { value: Filters; onChange: (f: Filters) => void }) {
  return (
    <Card>
      <div className="flex flex-wrap items-end gap-3">
        <label><span className="field-label">From</span><input type="date" className="input-field" value={value.start} onChange={(e) => onChange({ ...value, start: e.target.value })} /></label>
        <label><span className="field-label">To</span><input type="date" className="input-field" value={value.end} onChange={(e) => onChange({ ...value, end: e.target.value })} /></label>
        <label className="w-56"><span className="field-label">Department</span>
          <SearchSelect url="organisation/departments/" value={value.department} label={(d) => d.name} placeholder="All" onChange={(v) => onChange({ ...value, department: v ? String(v) : null })} />
        </label>
        <label className="w-56"><span className="field-label">Site</span>
          <SearchSelect url="organisation/sites/" value={value.site} label={(s) => s.name} placeholder="All" onChange={(v) => onChange({ ...value, site: v ? String(v) : null })} />
        </label>
        <label className="w-56"><span className="field-label">Contract type</span>
          <SearchSelect options={CONTRACT_TYPES} value={value.contract_type || null} placeholder="All" onChange={(v) => onChange({ ...value, contract_type: v ? String(v) : "" })} />
        </label>
      </div>
    </Card>
  );
}

function clean(f: Filters) {
  return Object.fromEntries(Object.entries(f).filter(([, v]) => v)) as Record<string, string>;
}

function Indicators() {
  const { can } = usePermissions();
  const [filters, setFilters] = useState<Filters>({ start: `${year}-01-01`, end: new Date().toISOString().slice(0, 10) });
  const qs = new URLSearchParams(clean(filters)).toString();
  const { data: head } = useApiItem<any>(`reports/indicators/headcount/?${qs}`);
  const { data: moves } = useApiItem<any>(`reports/indicators/movements/?${qs}`);
  const { data: time } = useApiItem<any>(`reports/indicators/time/?${qs}`);
  const [group, setGroup] = useState("department");
  const payrollAllowed = ["HR_MANAGER", "PAYROLL_OFFICER", "ACCOUNTANT", "GENERAL_MANAGEMENT"].includes(usePermissions().role);
  const { data: pay } = useApiItem<any>(payrollAllowed ? `reports/indicators/payroll/?${qs}` : null);
  const exportable = can("reports", "export");
  return (
    <div className="space-y-4">
      <FilterBar value={filters} onChange={setFilters} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        <KpiTile label="Headcount" value={head?.total ?? "…"} />
        <KpiTile label="Hires" value={moves?.hires ?? "…"} accent="#107E3E" />
        <KpiTile label="Departures" value={moves?.departures ?? "…"} accent="var(--danger)" />
        <KpiTile label="Turnover" value={moves ? `${fmt.number(moves.turnover_rate, 1)} %` : "…"} accent="#E9730C" />
        <KpiTile label="Absenteeism" value={time ? `${fmt.number(time.absenteeism_rate, 1)} %` : "…"} accent="#0A6ED1" />
        <KpiTile label="Overtime" value={time ? `${fmt.number(time.overtime_hours, 1)} h` : "…"} accent="var(--odoo-teal)" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Headcount" actions={
          <>
            <select className="input-field w-auto" value={group} onChange={(e) => setGroup(e.target.value)}>
              {["department", "position", "category", "contract_type", "sex", "age", "seniority", "site"].map((g) => <option key={g} value={g}>By {g.replace("_", " ")}</option>)}
            </select>
            {exportable && <ExportButtons url="reports/indicators/headcount/" params={{ ...clean(filters), group }} />}
          </>
        }>
          {head ? <BarList data={head[`by_${group}`] || []} /> : <Spinner />}
        </Card>
        <Card title="Movements" actions={exportable && <ExportButtons url="reports/indicators/movements/" params={clean(filters)} />}>
          {moves ? (
            <ColumnChart
              data={moves.series.map((s: any) => ({ ...s, label: s.month.slice(5) }))}
              series={[
                { key: "hires", label: "Hires", color: "#107E3E" },
                { key: "departures", label: "Departures", color: "#BB0000" },
                { key: "promotions", label: "Promotions", color: CHART_COLORS[0] },
                { key: "transfers", label: "Transfers", color: CHART_COLORS[1] },
              ]}
            />
          ) : <Spinner />}
        </Card>
        <Card title="Time and absence" actions={exportable && <ExportButtons url="reports/indicators/time/" params={clean(filters)} />}>
          {time ? (
            <dl className="grid grid-cols-2 gap-3 text-sm">
              {[
                ["Absenteeism rate", `${fmt.number(time.absenteeism_rate, 2)} %`],
                ["Unjustified absence days", time.unjustified_absence_days],
                ["Late arrivals", `${time.lateness_count} (${fmt.minutes(time.lateness_minutes)})`],
                ["Approved overtime", `${fmt.number(time.overtime_hours, 1)} h`],
                ["Overtime to approve", `${time.pending_overtime_days} day(s)`],
                ["Leave taken", `${fmt.number(time.leave_taken_days)} day(s)`],
                ["Leave remaining", `${fmt.number(time.leave_remaining_days)} day(s)`],
              ].map(([k, v]) => <div key={k as string}><dt className="section-label">{k}</dt><dd className="mt-0.5 font-semibold text-primary-c">{v}</dd></div>)}
            </dl>
          ) : <Spinner />}
        </Card>
        {payrollAllowed && (
          <Card title="Payroll" actions={exportable && <ExportButtons url="reports/indicators/payroll/" params={clean(filters)} />}>
            {pay ? (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div><p className="section-label">Total cost</p><p className="font-semibold">{fmt.money(pay.total_cost)}</p></div>
                  <div><p className="section-label">Average / employee</p><p className="font-semibold">{fmt.money(pay.average_cost_per_employee)}</p></div>
                  <div><p className="section-label">Employer charges</p><p className="font-semibold">{fmt.number(pay.employer_charges_weight, 1)} %</p></div>
                </div>
                <ColumnChart data={pay.by_month.map((m: any) => ({ label: m.label.slice(5), value: m.value }))} format={(v) => fmt.money(v)} />
                <BarList data={pay.by_department} format={(v) => fmt.money(v)} color={CHART_COLORS[2]} />
              </div>
            ) : <Spinner />}
          </Card>
        )}
      </div>
    </div>
  );
}

function Builder() {
  const { data: datasets } = useApiItem<Record<string, { value: string; label: string }[]>>("reports/saved/datasets/");
  const [dataset, setDataset] = useState("EMPLOYEES");
  const [fields, setFields] = useState<string[]>([]);
  const [groupBy, setGroupBy] = useState("");
  const [filters, setFilters] = useState<{ field: string; value: string }[]>([]);
  const [name, setName] = useState("");
  const [result, setResult] = useState<{ headers: string[]; rows: any[][] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedKey, setSavedKey] = useState(0);
  const available = datasets?.[dataset] || [];
  useEffect(() => {
    setFields(available.slice(0, 5).map((f) => f.value));
    setGroupBy("");
    setFilters([]);
    setResult(null);
  }, [dataset, datasets]);
  const body = () => ({ name: name || "Report", dataset, fields, group_by: groupBy,
    filters: Object.fromEntries(filters.filter((f) => f.field && f.value).map((f) => [f.field, f.value])) });
  const preview = async () => {
    try {
      setError(null);
      setResult((await api.post("reports/saved/preview/", body())).data);
    } catch (err) {
      setError(apiError(err));
    }
  };
  const save = async () => {
    try {
      await api.post("reports/saved/", { ...body(), name: name || "My report" });
      setSavedKey((k) => k + 1);
    } catch (err) {
      setError(apiError(err));
    }
  };
  return (
    <div className="space-y-4">
      <Card title="Build a report" actions={
        <>
          <button type="button" className="btn-secondary" onClick={preview}>Preview</button>
          <button type="button" className="btn-primary" onClick={save}>Save</button>
        </>
      }>
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-3">
            <label className="block"><span className="field-label">Name</span><input className="input-field" value={name} onChange={(e) => setName(e.target.value)} /></label>
            <label className="block"><span className="field-label">Data</span>
              <SearchSelect options={Object.keys(datasets || {}).map((d) => ({ value: d, label: d.charAt(0) + d.slice(1).toLowerCase() }))} value={dataset} onChange={(v) => setDataset(String(v || "EMPLOYEES"))} />
            </label>
            <label className="block"><span className="field-label">Group by</span>
              <SearchSelect options={available} value={groupBy || null} placeholder="No grouping" onChange={(v) => setGroupBy(v ? String(v) : "")} />
            </label>
          </div>
          <div>
            <span className="field-label">Columns</span>
            <div className="grid max-h-56 grid-cols-1 gap-1 overflow-y-auto rounded-lg border p-2" style={{ borderColor: "var(--border-color)" }}>
              {available.map((f) => (
                <label key={f.value} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" className="accent-brand-500" checked={fields.includes(f.value)}
                    onChange={(e) => setFields(e.target.checked ? [...fields, f.value] : fields.filter((x) => x !== f.value))} />
                  {f.label}
                </label>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <span className="field-label">Filters (equal to)</span>
            {filters.map((f, i) => (
              <div key={i} className="flex gap-2">
                <SearchSelect className="flex-1" options={available} value={f.field || null} onChange={(v) => setFilters(filters.map((x, j) => (j === i ? { ...x, field: String(v || "") } : x)))} />
                <input className="input-field w-32" value={f.value} onChange={(e) => setFilters(filters.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} />
                <button type="button" className="btn-icon" onClick={() => setFilters(filters.filter((_, j) => j !== i))}>✕</button>
              </div>
            ))}
            <button type="button" className="btn-ghost" onClick={() => setFilters([...filters, { field: "", value: "" }])}>+ Filter</button>
          </div>
        </div>
        {error && <div className="mt-3"><Banner tone="error">{error}</Banner></div>}
      </Card>
      {result && (
        <Card padded={false} title={`Result (${result.rows.length} rows)`}>
          <DataTable exportTitle="Report" rows={result.rows.map((r, i) => ({ id: i, r }))} columns={result.headers.map((h, i) => ({ key: String(i), header: h, render: (row: any) => String(row.r[i] ?? "") }))} />
        </Card>
      )}
      <CrudSection
        key={savedKey}
        endpoint="reports/saved/"
        title="Saved reports"
        canCreate={false}
        rowActions={[]}
        fields={[{ name: "name", label: "Name", required: true }, { name: "shared", label: "Shared with the users of the reports", type: "checkbox" }]}
        columns={[
          { key: "name", header: "Name" },
          { key: "dataset", header: "Data" },
          { key: "owner_name", header: "Owner" },
          { key: "run", header: "", render: (r: any) => <span onClick={(e) => e.stopPropagation()}><ExportButtons url={`reports/saved/${r.id}/run/`} /></span> },
        ]}
      />
      <CrudSection
        endpoint="reports/schedules/"
        title="Scheduled sending"
        fields={[
          { name: "report", label: "Report", type: "select", required: true, optionsUrl: "reports/saved/", optionLabel: (r: any) => r.name },
          { name: "frequency", label: "Frequency", type: "select", required: true, options: opt([["DAILY", "Every day"], ["WEEKLY", "Every Monday"], ["MONTHLY", "First day of the month"]]) },
          { name: "file_format", label: "Format", type: "select", options: opt([["xlsx", "Excel"], ["pdf", "PDF"], ["csv", "CSV"]]) },
          { name: "recipients", label: "Recipients (e-mails separated by commas)", type: "textarea", required: true },
          { name: "is_active", label: "Active", type: "checkbox" },
        ]}
        defaults={{ frequency: "WEEKLY", file_format: "xlsx", is_active: true }}
        columns={[
          { key: "report_name", header: "Report" },
          { key: "frequency", header: "Frequency" },
          { key: "recipients", header: "Recipients" },
          { key: "last_sent_at", header: "Last sent", render: (s: any) => fmt.datetime(s.last_sent_at) },
        ]}
      />
    </div>
  );
}

/** M-15 – reporting, dashboards and HR indicators. */
export default function Reports() {
  const [tab, setTab] = useHashTab("indicators");
  return (
    <>
      <PageHeader title="Reports & indicators" eyebrow="Steering" subtitle="Indicators computed from the detailed data, filterable, exportable and printable." />
      <Tabs active={tab} onChange={setTab} tabs={[{ id: "indicators", label: "HR indicators" }, { id: "builder", label: "Custom reports" }]} />
      {tab === "indicators" ? <Indicators /> : <Builder />}
    </>
  );
}
