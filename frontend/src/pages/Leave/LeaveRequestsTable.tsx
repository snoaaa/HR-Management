import { useState } from "react";
import api from "@/api/axiosConfig";
import { fmt } from "@/api/helpers";
import { DownloadButton } from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { FormModal, PromptModal } from "@/components/kit/Form";
import { StatusBadge } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

export interface LeaveRequest {
  id: number;
  employee: number;
  employee_name: string;
  department_name: string;
  leave_type_name: string;
  leave_type_color: string;
  start_date: string;
  end_date: string;
  effective_end_date: string;
  days: string;
  status: string;
  status_label: string;
  overlap_warning: string;
  decision_comment: string;
  replacement_name: string | null;
  allowance_amount: string | null;
  original_start_date: string | null;
}

type Dialog = { kind: "cancel" | "interrupt" | "postpone" | "submit"; row: LeaveRequest } | null;

/** Leave requests with their life-cycle actions (BN-54, BN-57). */
export default function LeaveRequestsTable({
  rows,
  loading,
  reload,
  mine = false,
}: {
  rows: LeaveRequest[];
  loading: boolean;
  reload: () => void;
  mine?: boolean;
}) {
  const [dialog, setDialog] = useState<Dialog>(null);
  const { can, can_view_salary } = usePermissions();
  const toast = useToast();
  const today = new Date().toISOString().slice(0, 10);

  const act = (path: string, body?: any) => async () => {
    await api.post(`leave/requests/${dialog!.row.id}/${path}/`, body);
    toast.success("Done");
    reload();
  };

  return (
    <>
      <DataTable<LeaveRequest>
        rows={rows}
        loading={loading}
        empty="No leave request."
        columns={[
          ...(!mine
            ? [
                {
                  key: "employee_name",
                  header: "Employee",
                  render: (r: LeaveRequest) => (
                    <div>
                      <p className="font-medium text-primary-c">{r.employee_name}</p>
                      <p className="text-[11px] text-muted-c">{r.department_name}</p>
                    </div>
                  ),
                },
              ]
            : []),
          {
            key: "leave_type_name",
            header: "Type",
            render: (r) => (
              <span className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: r.leave_type_color }} />
                {r.leave_type_name}
              </span>
            ),
          },
          {
            key: "dates",
            header: "Period",
            render: (r) => (
              <div>
                <p>
                  {fmt.date(r.start_date)} → {fmt.date(r.effective_end_date || r.end_date)}
                </p>
                {r.original_start_date && <p className="text-[11px] text-muted-c">postponed from {fmt.date(r.original_start_date)}</p>}
              </div>
            ),
          },
          { key: "days", header: "Days", align: "end", mono: true, render: (r) => fmt.number(r.days) },
          {
            key: "status",
            header: "Status",
            render: (r) => (
              <div className="space-y-1">
                <StatusBadge value={r.status} label={r.status_label} />
                {r.overlap_warning && <p className="max-w-56 text-[11px] text-sap-critical">⚠ {r.overlap_warning}</p>}
                {r.decision_comment && <p className="max-w-56 text-[11px] text-muted-c">“{r.decision_comment}”</p>}
              </div>
            ),
          },
          ...(can_view_salary ? [{ key: "allowance_amount", header: "Allowance", align: "end" as const, mono: true, render: (r: LeaveRequest) => (r.allowance_amount ? fmt.money(r.allowance_amount) : "—") }] : []),
          {
            key: "actions",
            header: "",
            align: "end",
            render: (r) => (
              <div className="flex flex-wrap justify-end gap-1">
                {["DRAFT", "MODIFICATION"].includes(r.status) && (
                  <button type="button" className="btn-teal btn-sm" onClick={() => setDialog({ kind: "submit", row: r })}>
                    Submit
                  </button>
                )}
                {["APPROVED", "INTERRUPTED"].includes(r.status) && (
                  <>
                    <DownloadButton url={`leave/requests/${r.id}/print_decision/`} label="Decision" className="btn-ghost text-xs" />
                    <DownloadButton url={`leave/requests/${r.id}/print_certificate/`} label="Certificate" className="btn-ghost text-xs" />
                  </>
                )}
                {r.status === "APPROVED" && r.start_date > today && (
                  <button type="button" className="btn-ghost text-xs" onClick={() => setDialog({ kind: "postpone", row: r })}>
                    Postpone
                  </button>
                )}
                {r.status === "APPROVED" && r.start_date <= today && r.end_date > today && can("leave", "modify") && (
                  <button type="button" className="btn-ghost text-xs" onClick={() => setDialog({ kind: "interrupt", row: r })}>
                    Interrupt
                  </button>
                )}
                {(["DRAFT", "SUBMITTED", "MODIFICATION"].includes(r.status) || (r.status === "APPROVED" && r.start_date > today)) && (
                  <button type="button" className="btn-ghost text-xs text-error-600" onClick={() => setDialog({ kind: "cancel", row: r })}>
                    Cancel
                  </button>
                )}
              </div>
            ),
          },
        ]}
      />
      <PromptModal
        open={dialog?.kind === "cancel"}
        title="Cancel the request"
        message="The days return to the balance."
        danger
        confirmLabel="Cancel the request"
        onClose={() => setDialog(null)}
        onConfirm={act("cancel")}
      />
      <PromptModal
        open={dialog?.kind === "submit"}
        title="Submit the request"
        message="The request goes to your line manager, then to HR."
        confirmLabel="Submit"
        onClose={() => setDialog(null)}
        onConfirm={act("submit")}
      />
      <FormModal
        open={dialog?.kind === "interrupt"}
        title="Interrupt the leave (BN-54)"
        size="sm"
        fields={[{ name: "last_day", label: "Last day of leave", type: "date", required: true }]}
        onClose={() => setDialog(null)}
        onSaved={reload}
        onSubmit={(p) => api.post(`leave/requests/${dialog!.row.id}/interrupt/`, p)}
        submitLabel="Interrupt"
      />
      <FormModal
        open={dialog?.kind === "postpone"}
        title="Postpone the leave (BN-54)"
        size="sm"
        intro={<p className="text-sm text-secondary-c">The new dates go through the approval circuit again.</p>}
        fields={[
          { name: "start_date", label: "New first day", type: "date", required: true },
          { name: "end_date", label: "New last day", type: "date", required: true },
        ]}
        onClose={() => setDialog(null)}
        onSaved={reload}
        onSubmit={(p) => api.post(`leave/requests/${dialog!.row.id}/postpone/`, p)}
        submitLabel="Postpone"
      />
    </>
  );
}
