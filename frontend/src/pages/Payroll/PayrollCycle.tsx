import { useState } from "react";
import { useNavigate } from "react-router";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import DataTable from "@/components/kit/DataTable";
import { PromptModal } from "@/components/kit/Form";
import { useApiList } from "@/components/kit/hooks";
import { MONTHS } from "@/components/kit/options";
import { Card, PageHeader, StatusBadge } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

/** BN-93: list of the payroll periods. */
export default function PayrollCycle() {
  const navigate = useNavigate();
  const toast = useToast();
  const { can } = usePermissions();
  const { rows, loading, reload } = useApiList<any>("payroll/periods/");
  const [opening, setOpening] = useState(false);
  const now = new Date();

  return (
    <>
      <PageHeader
        title="Payroll cycle"
        eyebrow="Payroll"
        subtitle="Open a period, retrieve the variable elements, calculate, verify, validate, pay and post."
        actions={
          can("payroll", "modify") && (
            <button type="button" className="btn-primary" onClick={() => setOpening(true)}>
              + Open a period
            </button>
          )
        }
      />
      <Card padded={false}>
        <DataTable exportTitle="Payroll periods"
          rows={rows}
          loading={loading}
          onRowClick={(p: any) => navigate(`/payroll/periods/${p.id}`)}
          columns={[
            { key: "month", header: "Period", render: (p: any) => <span className="font-semibold text-primary-c">{MONTHS[p.month - 1]} {p.year}</span> },
            { key: "status", header: "Status", render: (p: any) => <StatusBadge value={p.status} label={p.status_label} /> },
            { key: "totals.count", header: "Payslips", align: "end", render: (p: any) => p.totals?.count ?? 0 },
            { key: "totals.gross", header: "Gross", align: "end", render: (p: any) => fmt.money(p.totals?.gross) },
            { key: "totals.net_payable", header: "Net payable", align: "end", render: (p: any) => fmt.money(p.totals?.net_payable) },
            { key: "totals.employer_contributions", header: "Employer charges", align: "end", render: (p: any) => fmt.money(p.totals?.employer_contributions) },
            { key: "totals.anomalies", header: "Anomalies", align: "end", render: (p: any) => (p.totals?.anomalies ? <span className="badge-red">{p.totals.anomalies}</span> : "—") },
          ]}
        />
      </Card>
      <PromptModal
        open={opening}
        title="Open a payroll period"
        extraFields={[
          { name: "month", label: "Month", type: "select", required: true, options: MONTHS.map((m, i) => ({ value: i + 1, label: m })) },
          { name: "year", label: "Year", type: "number", required: true },
        ]}
        onClose={() => setOpening(false)}
        onConfirm={async (v) => {
          try {
            const res = await api.post("payroll/periods/", { month: v.month || now.getMonth() + 1, year: v.year || now.getFullYear() });
            reload();
            navigate(`/payroll/periods/${res.data.id}`);
          } catch (err) {
            toast.error(apiError(err));
            throw err;
          }
        }}
      />
    </>
  );
}
