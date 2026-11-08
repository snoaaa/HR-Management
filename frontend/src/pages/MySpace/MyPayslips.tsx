import { downloadFile, fmt } from "@/api/helpers";
import DataTable from "@/components/kit/DataTable";
import { useApiList } from "@/components/kit/hooks";
import { Card, PageHeader } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

export default function MyPayslips() {
  const { employee_id } = usePermissions();
  const { rows, loading } = useApiList<any>(
    employee_id ? `payroll/payslips/?employee=${employee_id}` : null
  );
  const toast = useToast();

  const downloadPdf = async (p: any) => {
    try {
      await downloadFile(`payroll/payslips/${p.id}/pdf/`, {
        filename: `bulletin_${p.period_label || p.id}.pdf`,
        open: true,
      });
    } catch {
      toast.error("Could not download payslip.");
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="My Space"
        title="My Payslips (BN-150)"
        subtitle="Consult and download your monthly statutory payslips."
      />

      <Card padded={false} title="Payslips history">
        <DataTable
          rows={rows}
          loading={loading}
          empty="No payslip available yet."
          columns={[
            { key: "period_label", header: "Period", render: (p: any) => <span className="font-semibold text-primary-c">{p.period_label || `Period #${p.period}`}</span> },
            { key: "gross_salary", header: "Gross salary", align: "end", mono: true, render: (p: any) => fmt.money(p.gross_salary) },
            { key: "total_employee_deductions", header: "Total deductions", align: "end", mono: true, render: (p: any) => fmt.money(p.total_employee_deductions) },
            {
              key: "net_payable",
              header: "Net payable",
              align: "end",
              mono: true,
              render: (p: any) => <b className="text-primary-c">{fmt.money(p.net_payable)}</b>,
            },
            {
              key: "actions",
              header: "",
              align: "end",
              render: (p: any) => (
                <button type="button" className="btn-ghost text-xs" onClick={() => downloadPdf(p)}>
                  Download PDF
                </button>
              ),
            },
          ]}
        />
      </Card>
    </>
  );
}

