import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { useOptions } from "@/components/kit/hooks";
import { Card, PageHeader } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

export default function PayrollSimulation() {
  const { can_view_salary } = usePermissions();
  const employees = useOptions("employees/", (e) => `${e.full_name || `${e.surname} ${e.given_names}`} (${e.matriculation})`);
  const toast = useToast();

  const [mode, setMode] = useState<"employee" | "hiring">("employee");
  const [employeeId, setEmployeeId] = useState<string>("");
  const [baseSalary, setBaseSalary] = useState<string>("350000");
  const [month, setMonth] = useState<number>(new Date().getMonth() + 1);
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any>(null);

  const simulate = async () => {
    setLoading(true);
    setResult(null);
    try {
      const payload: any = { year, month };
      if (mode === "employee") {
        if (!employeeId) {
          toast.error("Please select an employee");
          setLoading(false);
          return;
        }
        payload.employee = Number(employeeId);
      } else {
        payload.base_salary = baseSalary;
      }

      const res = await api.post("payroll/simulate/", payload);
      setResult(res.data);
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  if (!can_view_salary) {
    return (
      <div className="p-8 text-center text-muted-c">
        You do not have access to salary data or simulations.
      </div>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Payroll"
        title="Salary Simulation (BN-105)"
        subtitle="Simulate gross-to-net calculations, tax withholdings, and total cost to employer with no permanent effect."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Simulation parameters">
          <div className="space-y-4">
            <div className="flex gap-2 p-1 bg-surface-alt rounded border" style={{ borderColor: "var(--border-color)" }}>
              <button
                type="button"
                className={`flex-1 py-1.5 text-xs font-medium rounded ${mode === "employee" ? "bg-white shadow-xs text-brand-500 font-semibold dark:bg-gray-800" : "text-muted-c"}`}
                onClick={() => setMode("employee")}
              >
                Existing employee
              </button>
              <button
                type="button"
                className={`flex-1 py-1.5 text-xs font-medium rounded ${mode === "hiring" ? "bg-white shadow-xs text-brand-500 font-semibold dark:bg-gray-800" : "text-muted-c"}`}
                onClick={() => setMode("hiring")}
              >
                Hiring estimate
              </button>
            </div>

            {mode === "employee" ? (
              <label>
                <span className="field-label">Select employee</span>
                <select className="input-field" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
                  <option value="">Select...</option>
                  {employees.map((e) => (
                    <option key={e.value} value={e.value}>
                      {e.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label>
                <span className="field-label">Proposed base salary (FCFA)</span>
                <input
                  type="number"
                  className="input-field"
                  value={baseSalary}
                  onChange={(e) => setBaseSalary(e.target.value)}
                  placeholder="e.g. 450000"
                />
              </label>
            )}

            <div className="grid grid-cols-2 gap-2">
              <label>
                <span className="field-label">Month</span>
                <input type="number" min={1} max={12} className="input-field" value={month} onChange={(e) => setMonth(Number(e.target.value))} />
              </label>
              <label>
                <span className="field-label">Year</span>
                <input type="number" className="input-field" value={year} onChange={(e) => setYear(Number(e.target.value))} />
              </label>
            </div>

            <button type="button" className="btn-primary w-full mt-2" disabled={loading} onClick={simulate}>
              {loading ? "Calculating..." : "Run simulation →"}
            </button>
          </div>
        </Card>

        <div className="lg:col-span-2">
          {result ? (
            <Card title="Simulated Result">
              <div className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-4 rounded border bg-surface-alt" style={{ borderColor: "var(--border-color)" }}>
                    <span className="text-xs text-muted-c">Gross Salary</span>
                    <p className="text-xl font-bold text-primary-c mt-1">{fmt.money(result.gross_salary || result.gross || 0)}</p>
                  </div>
                  <div className="p-4 rounded border bg-surface-alt" style={{ borderColor: "var(--border-color)" }}>
                    <span className="text-xs text-muted-c">Total Deductions</span>
                    <p className="text-xl font-bold text-red-500 mt-1">{fmt.money(result.total_employee_deductions || result.employee_deductions || 0)}</p>
                  </div>
                  <div className="p-4 rounded border bg-surface-alt" style={{ borderColor: "var(--border-color)" }}>
                    <span className="text-xs text-muted-c">Net Payable</span>
                    <p className="text-xl font-bold text-green-600 mt-1">{fmt.money(result.net_payable || result.net || 0)}</p>
                  </div>
                </div>

                {result.lines && result.lines.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-c mb-2">Detailed breakdown</h4>
                    <div className="overflow-x-auto rounded border" style={{ borderColor: "var(--border-color)" }}>
                      <table className="min-w-full divide-y text-xs" style={{ borderColor: "var(--border-color)" }}>
                        <thead className="bg-surface-alt">
                          <tr>
                            <th className="p-2.5 text-left font-semibold">Element / Rule</th>
                            <th className="p-2.5 text-right font-semibold">Base</th>
                            <th className="p-2.5 text-right font-semibold">Rate</th>
                            <th className="p-2.5 text-right font-semibold">Gain</th>
                            <th className="p-2.5 text-right font-semibold">Deduction</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y" style={{ borderColor: "var(--border-color)" }}>
                          {result.lines.map((l: any, i: number) => (
                            <tr key={i}>
                              <td className="p-2.5 font-medium">{l.label || l.name || l.code}</td>
                              <td className="p-2.5 text-right mono">{l.base ? fmt.money(l.base) : "-"}</td>
                              <td className="p-2.5 text-right mono">{l.rate ? `${l.rate}%` : "-"}</td>
                              <td className="p-2.5 text-right mono text-green-600 font-medium">{l.gain ? fmt.money(l.gain) : "-"}</td>
                              <td className="p-2.5 text-right mono text-red-500 font-medium">{l.deduction ? fmt.money(l.deduction) : "-"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          ) : (
            <Card>
              <div className="p-12 text-center text-muted-c">
                Fill in the simulation parameters on the left and click <b>Run simulation</b> to compute the estimated payslip and statutory breakdown.
              </div>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

