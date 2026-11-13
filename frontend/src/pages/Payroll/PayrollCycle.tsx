import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, downloadFile, fmt } from "@/api/helpers";
import DataTable from "@/components/kit/DataTable";
import { FormModal } from "@/components/kit/Form";
import { useApiList } from "@/components/kit/hooks";
import { Banner, Card, Modal, PageHeader, StatusBadge } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

interface Period {
  id: number;
  year: number;
  month: number;
  status: "OPEN" | "OPENED" | "CALCULATED" | "VALIDATED" | "PAID" | "CLOSED" | "LOCKED";
  status_label: string;
  totals?: {
    employee_count?: number;
    gross?: number;
    net_payable?: number;
    employee_contributions?: number;
    employer_contributions?: number;
    tax?: number;
  };
}

export default function PayrollCycle() {
  const { rows, loading, reload } = useApiList<Period>("payroll/periods/");
  const [opening, setOpening] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);
  const [activeComparison, setActiveComparison] = useState<any>(null);
  const [activeAnomalies, setActiveAnomalies] = useState<any>(null);
  const { can, can_view_salary } = usePermissions();
  const toast = useToast();

  const calculate = async (p: Period) => {
    setBusy(p.id);
    try {
      const res = await api.post(`payroll/periods/${p.id}/calculate/`);
      toast.success(res.data.detail || `Period ${p.month}/${p.year} calculated`);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(null);
    }
  };

  const validatePeriod = async (p: Period) => {
    if (!confirm(`Validate payroll for ${p.month}/${p.year}? This will generate the OHADA accounting entries and finalize the period.`)) {
      return;
    }
    setBusy(p.id);
    try {
      const res = await api.post(`payroll/periods/${p.id}/validate/`);
      toast.success(res.data.detail || `Period ${p.month}/${p.year} validated and posted to accounting`);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(null);
    }
  };

  const lockPeriod = async (p: Period) => {
    if (!confirm(`Lock period ${p.month}/${p.year}? No further calculations or edits will be possible.`)) return;
    setBusy(p.id);
    try {
      await api.post(`payroll/periods/${p.id}/lock/`);
      toast.success(`Period ${p.month}/${p.year} locked`);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(null);
    }
  };

  const checkAnomalies = async (p: Period) => {
    try {
      const res = await api.get(`payroll/periods/${p.id}/anomalies/`);
      setActiveAnomalies({ period: p, data: res.data });
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  const checkComparison = async (p: Period) => {
    try {
      const res = await api.get(`payroll/periods/${p.id}/comparison/`);
      setActiveComparison({ period: p, data: res.data });
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Payroll"
        title="Payroll Cycle (M-11, M-12)"
        subtitle="Manage payroll periods, run statutory calculations, validate cycles and produce accounting entries."
      />

      <Card
        padded={false}
        title="Payroll periods (BN-93)"
        actions={
          can("payroll", "modify") && (
            <button type="button" className="btn-primary" onClick={() => setOpening(true)}>
              + Open new period
            </button>
          )
        }
      >
        <DataTable<Period>
          rows={rows}
          loading={loading}
          empty="No payroll period open yet."
          columns={[
            {
              key: "period",
              header: "Period",
              render: (p) => (
                <span className="font-semibold text-primary-c">
                  {String(p.month).padStart(2, "0")} / {p.year}
                </span>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (p) => <StatusBadge value={p.status} label={p.status_label || p.status} />,
            },
            {
              key: "headcount",
              header: "Employees",
              align: "end",
              mono: true,
              render: (p) => p.totals?.employee_count || "-",
            },
            {
              key: "gross",
              header: "Total Gross",
              align: "end",
              mono: true,
              render: (p) => (can_view_salary && p.totals?.gross ? fmt.money(p.totals.gross) : "-"),
            },
            {
              key: "net",
              header: "Net Payable",
              align: "end",
              mono: true,
              render: (p) => (can_view_salary && p.totals?.net_payable ? <b className="text-primary-c">{fmt.money(p.totals.net_payable)}</b> : "-"),
            },
            {
              key: "actions",
              header: "",
              align: "end",
              render: (p) => (
                <div className="flex flex-wrap items-center justify-end gap-1.5">
                  {(p.status === "OPEN" || p.status === "OPENED") && can("payroll", "modify") && (
                    <button
                      type="button"
                      disabled={busy === p.id}
                      className="btn-primary text-xs"
                      onClick={() => calculate(p)}
                    >
                      {busy === p.id ? "Calculating..." : "Calculate (BN-95)"}
                    </button>
                  )}

                  {p.status === "CALCULATED" && (
                    <>
                      <button type="button" className="btn-ghost text-xs text-amber-600" onClick={() => checkAnomalies(p)}>
                        Anomalies
                      </button>
                      <button type="button" className="btn-ghost text-xs" onClick={() => checkComparison(p)}>
                        Comparison
                      </button>
                      {can("payroll", "validate") && (
                        <button
                          type="button"
                          disabled={busy === p.id}
                          className="btn-primary text-xs bg-emerald-600 hover:bg-emerald-700"
                          onClick={() => validatePeriod(p)}
                        >
                          Validate (BN-108)
                        </button>
                      )}
                    </>
                  )}

                  {(p.status === "VALIDATED" || p.status === "PAID") && can("payroll", "validate") && (
                    <button type="button" className="btn-ghost text-xs text-indigo-600" onClick={() => lockPeriod(p)}>
                      Lock period
                    </button>
                  )}

                  {["CALCULATED", "VALIDATED", "PAID", "LOCKED", "CLOSED"].includes(p.status) && (
                    <div className="flex items-center gap-1 border-l pl-2 ml-1" style={{ borderColor: "var(--border-color)" }}>
                      <button
                        type="button"
                        className="btn-ghost text-xs"
                        title="Download payroll book"
                        onClick={() => downloadFile(`payroll/periods/${p.id}/payroll_book/?file_format=pdf`, { filename: `payroll_book_${p.month}_${p.year}.pdf` })}
                      >
                        Book
                      </button>
                      <button
                        type="button"
                        className="btn-ghost text-xs"
                        title="Batch print all payslips"
                        onClick={() => downloadFile(`payroll/periods/${p.id}/batch_payslips/`, { method: "post", filename: `payslips_${p.month}_${p.year}.pdf` })}
                      >
                        Payslips
                      </button>
                      <button
                        type="button"
                        className="btn-ghost text-xs"
                        title="Download bank transfer order file"
                        onClick={() => downloadFile(`payroll/periods/${p.id}/bank_file/`, { filename: `transfers_${p.month}_${p.year}.csv` })}
                      >
                        Bank CSV
                      </button>
                      <button
                        type="button"
                        className="btn-ghost text-xs"
                        title="Statutory declarations (DIPE / CNPS)"
                        onClick={() => downloadFile(`payroll/periods/${p.id}/declaration_export/?file_format=xlsx`, { filename: `declarations_${p.month}_${p.year}.xlsx` })}
                      >
                        DIPE/CNPS
                      </button>
                    </div>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>

      <FormModal
        open={opening}
        title="Open new payroll period"
        endpoint="payroll/periods/"
        onClose={() => setOpening(false)}
        onSaved={reload}
        fields={[
          {
            name: "month",
            label: "Month",
            type: "select",
            required: true,
            options: Array.from({ length: 12 }, (_, i) => ({ value: String(i + 1), label: String(i + 1).padStart(2, "0") })),
          },
          {
            name: "year",
            label: "Year",
            type: "number",
            required: true,
          },
        ]}
      />

      {activeAnomalies && (
        <Modal open={true} onClose={() => setActiveAnomalies(null)} title={`Anomalies check (${activeAnomalies.period.month}/${activeAnomalies.period.year})`}>
          <div className="space-y-4">
            {Array.isArray(activeAnomalies.data) && activeAnomalies.data.length === 0 ? (
              <Banner tone="success">
                The payroll cycle passed all statutory validation controls (SMIG minimum wage, contract existence, bank verification).
              </Banner>
            ) : (
              <div className="space-y-2">
                <Banner tone="error">
                  Please resolve the identified issues before validating the payroll period.
                </Banner>
                <div className="max-h-60 overflow-y-auto space-y-1 text-xs">
                  {activeAnomalies.data.map((item: any, i: number) => (
                    <div key={i} className="p-2 rounded bg-surface-alt border" style={{ borderColor: "var(--border-color)" }}>
                      <b>{item.employee_name || "Anomaly"}:</b> {item.message || item.detail || JSON.stringify(item)}
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="flex justify-end pt-2">
              <button type="button" className="btn-secondary" onClick={() => setActiveAnomalies(null)}>
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}

      {activeComparison && (
        <Modal open={true} onClose={() => setActiveComparison(null)} title={`Payroll comparison (${activeComparison.period.month}/${activeComparison.period.year})`} size="lg">
          <div className="space-y-4">
            <p className="text-sm text-muted-c">Variation compared to the previous payroll cycle (BN-107):</p>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded border bg-surface-alt" style={{ borderColor: "var(--border-color)" }}>
                <span className="text-xs text-muted-c">Previous cycle</span>
                <p className="text-lg font-bold">{activeComparison.data?.previous_period ? `${activeComparison.data.previous_period.month}/${activeComparison.data.previous_period.year}` : "N/A"}</p>
                <p className="text-xs text-muted-c">Gross: {fmt.money(activeComparison.data?.previous_totals?.gross || 0)}</p>
                <p className="text-xs text-muted-c">Net: {fmt.money(activeComparison.data?.previous_totals?.net_payable || 0)}</p>
              </div>
              <div className="p-4 rounded border bg-surface-alt" style={{ borderColor: "var(--border-color)" }}>
                <span className="text-xs text-muted-c">Current cycle</span>
                <p className="text-lg font-bold">{activeComparison.period.month}/{activeComparison.period.year}</p>
                <p className="text-xs text-muted-c">Gross: {fmt.money(activeComparison.data?.current_totals?.gross || 0)}</p>
                <p className="text-xs text-muted-c">Net: {fmt.money(activeComparison.data?.current_totals?.net_payable || 0)}</p>
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <button type="button" className="btn-secondary" onClick={() => setActiveComparison(null)}>
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}

