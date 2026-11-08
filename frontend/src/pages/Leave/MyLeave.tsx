import { useState } from "react";
import { fmt } from "@/api/helpers";
import { DownloadButton } from "@/components/kit/CrudSection";
import { useApiItem, useApiList } from "@/components/kit/hooks";
import { Card, KpiTile, PageHeader } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import LeaveRequestForm from "./LeaveRequestForm";
import LeaveRequestsTable from "./LeaveRequestsTable";
import type { LeaveRequest } from "./LeaveRequestsTable";

/** BN-149: the employee consults the balance, requests leave and follows it. */
export default function MyLeave() {
  const { employee_id } = usePermissions();
  const { data: balance, reload: reloadBalance } = useApiItem<any>("leave/requests/balance/");
  const { rows, loading, reload } = useApiList<LeaveRequest>(employee_id ? "leave/requests/" : null, employee_id ? { employee: employee_id } : undefined);
  const [creating, setCreating] = useState(false);

  const refresh = () => {
    reload();
    reloadBalance();
  };

  return (
    <>
      <PageHeader
        eyebrow="My space"
        title="My leave"
        subtitle="Your balance is computed automatically every month, according to the rules of the organisation."
        actions={
          <>
            <DownloadButton url="leave/requests/print_balance/" label="Print my balance" />
            <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
              + Request leave
            </button>
          </>
        }
      />
      {balance && (
        <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-5">
          <KpiTile label="Available" value={fmt.number(balance.available)} accent="var(--odoo-teal)" hint="days you can request" />
          <KpiTile label="Carried over" value={fmt.number(balance.carried_over)} accent="var(--odoo-purple-mid)" />
          <KpiTile label="Acquired" value={fmt.number(balance.acquired)} accent="var(--sap-blue)" hint={`in ${balance.year}`} />
          <KpiTile label="Taken" value={fmt.number(balance.taken)} accent="var(--odoo-purple)" />
          <KpiTile label="Pending" value={fmt.number(balance.pending)} accent="var(--sap-critical)" hint="waiting for approval" />
        </div>
      )}
      <Card title="My requests" padded={false}>
        <LeaveRequestsTable rows={rows} loading={loading} reload={refresh} mine />
      </Card>
      <LeaveRequestForm open={creating} onClose={() => setCreating(false)} onSaved={refresh} />
    </>
  );
}
