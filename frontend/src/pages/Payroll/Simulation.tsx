import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { FormGrid } from "@/components/kit/Form";
import { MONTHS, classificationField, employeeField } from "@/components/kit/options";
import { Banner, Card, KpiTile, PageHeader, Tabs } from "@/components/kit/ui";
import { PayslipLines } from "./Payslips";

/** BN-105: simulation without any effect (question of an employee, hiring proposal). */
export default function Simulation() {
  const now = new Date();
  const [mode, setMode] = useState("employee");
  const [values, setValues] = useState<Record<string, any>>({ month: now.getMonth() + 1, year: now.getFullYear(), weekly_hours: 40 });
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const overrides: Record<string, any> = {};
      if (values.base_salary_override) overrides.base_salary = values.base_salary_override;
      const payload =
        mode === "employee"
          ? { employee: values.employee, year: values.year, month: values.month, overrides }
          : { base_salary: values.base_salary, classification: values.classification, weekly_hours: values.weekly_hours, year: values.year, month: values.month };
      setResult((await api.post("payroll/simulate/", payload)).data);
    } catch (err) {
      setError(apiError(err));
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  const fields =
    mode === "employee"
      ? [employeeField(), { name: "base_salary_override", label: "What if the base salary were… (optional)", type: "number" as const }]
      : [
          { name: "base_salary", label: "Proposed monthly base salary", type: "number" as const, required: true },
          classificationField(),
          { name: "weekly_hours", label: "Weekly hours", type: "number" as const },
        ];

  return (
    <>
      <PageHeader title="Payroll simulation" eyebrow="Payroll" subtitle="Nothing is saved: the result has no effect on the payroll or the accounts." />
      <Tabs active={mode} onChange={(m) => { setMode(m); setResult(null); }} tabs={[{ id: "employee", label: "An employee" }, { id: "hiring", label: "A hiring proposal" }]} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Parameters">
          <form onSubmit={run} className="space-y-4">
            <FormGrid
              fields={[
                ...fields,
                { name: "month", label: "Month", type: "select", required: true, options: MONTHS.map((m, i) => ({ value: i + 1, label: m })) },
                { name: "year", label: "Year", type: "number", required: true },
              ]}
              values={values}
              onChange={(n, v) => setValues((p) => ({ ...p, [n]: v }))}
            />
            {error && <Banner tone="error">{error}</Banner>}
            <button type="submit" className="btn-primary w-full justify-center" disabled={busy}>
              {busy ? "Calculating…" : "Simulate"}
            </button>
          </form>
        </Card>
        <div className="space-y-4 lg:col-span-2">
          {result && (
            <>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <KpiTile label="Gross" value={fmt.money(result.gross)} />
                <KpiTile label="Net payable" value={fmt.money(result.net_payable)} accent="var(--odoo-teal)" />
                <KpiTile label="Employer charges" value={fmt.money(result.employer_contributions)} accent="#E9730C" />
                <KpiTile label="Total cost" value={fmt.money(result.total_cost)} accent="#0A6ED1" />
              </div>
              {result.anomalies?.map((a: any) => <Banner key={a.code} tone={a.blocking ? "error" : "warning"}>{a.message}</Banner>)}
              <Card title="Detail"><PayslipLines lines={result.lines} /></Card>
            </>
          )}
        </div>
      </div>
    </>
  );
}
