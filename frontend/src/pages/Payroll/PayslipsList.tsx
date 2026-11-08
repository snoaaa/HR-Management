import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, downloadFile, fmt } from "@/api/helpers";
import DataTable from "@/components/kit/DataTable";
import { useApiList, useOptions } from "@/components/kit/hooks";
import { Card, PageHeader } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

interface Payslip {
  id: number;
  period: number;
  period_label: string;
  employee: number;
  employee_name: string;
  matriculation: string;
  department_name: string;
  gross_salary: number;
  total_employee_deductions: number;
  net_payable: number;
  payment_method: string;
}

export default function PayslipsList() {
  const [period, setPeriod] = useState<string>("");
  const periods = useOptions("payroll/periods/", (p) => `${String(p.month).padStart(2, "0")}/${p.year} (${p.status})`);
  const params: Record<string, string> = {};
  if (period) params.period = period;

  const { rows, loading } = useApiList<Payslip>("payroll/payslips/", params);
  const { can, can_view_salary } = usePermissions();
  const toast = useToast();

  const printPdf = async (p: Payslip, duplicate = false) => {
    try {
      const url = duplicate ? `payroll/payslips/${p.id}/duplicate/` : `payroll/payslips/${p.id}/pdf/`;
      await downloadFile(url, { filename: `bulletin_${p.matriculation || p.id}.pdf`, open: true });
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  const emailEmployee = async (p: Payslip) => {
    try {
      await api.post(`payroll/payslips/${p.id}/email/`);
      toast.success(`Payslip emailed to ${p.employee_name}`);
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  if (!can_view_salary) {
    return (
      <div className="p-8 text-center text-muted-c">
        You do not have the required security profile to consult individual salaries.
      </div>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Payroll"
        title="Payslips (BN-113, BN-115)"
        subtitle="Consult, duplicate, export, and email individual statutory payslips."
      />

      <Card
        padded={false}
        title="Individual payslips"
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-c">Period:</span>
            <select className="input-field w-auto text-xs" value={period} onChange={(e) => setPeriod(e.target.value)}>
              <option value="">All periods</option>
              {periods.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        }
      >
        <DataTable<Payslip>
          rows={rows}
          loading={loading}
          empty="No payslips generated for this period yet."
          columns={[
            {
              key: "employee",
              header: "Employee",
              render: (p) => (
                <div>
                  <span className="font-medium text-primary-c">{p.employee_name}</span>
                  <span className="block text-[11px] mono text-muted-c">{p.matriculation}</span>
                </div>
              ),
            },
            { key: "period_label", header: "Period", render: (p) => p.period_label || `Period #${p.period}` },
            { key: "department_name", header: "Department" },
            { key: "gross_salary", header: "Gross salary", align: "end", mono: true, render: (p) => fmt.money(p.gross_salary) },
            { key: "total_employee_deductions", header: "Deductions", align: "end", mono: true, render: (p) => fmt.money(p.total_employee_deductions) },
            {
              key: "net_payable",
              header: "Net payable",
              align: "end",
              mono: true,
              render: (p) => <b className="text-primary-c">{fmt.money(p.net_payable)}</b>,
            },
            {
              key: "actions",
              header: "",
              align: "end",
              render: (p) => (
                <div className="flex items-center justify-end gap-1">
                  <button type="button" className="btn-ghost text-xs" onClick={() => printPdf(p, false)}>
                    PDF
                  </button>
                  <button type="button" className="btn-ghost text-xs" title="Print marked DUPLICATE" onClick={() => printPdf(p, true)}>
                    Duplicate
                  </button>
                  {can("payroll", "modify") && (
                    <button type="button" className="btn-ghost text-xs text-brand-500" title="Email protected payslip" onClick={() => emailEmployee(p)}>
                      Email
                    </button>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>
    </>
  );
}

