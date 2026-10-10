import { useEffect, useState } from "react";
import { Link } from "react-router";
import api from "@/api/axiosConfig";
import { asList, fmt } from "@/api/helpers";
import ClockWidget from "@/components/dashboard/ClockWidget";
import DataTable from "@/components/kit/DataTable";
import { Card, KpiTile, PageHeader, StatusBadge } from "@/components/kit/ui";
import { useAuth } from "@/context/AuthContext";
import { usePermissions } from "@/context/PermissionsContext";

interface Approval {
  id: number;
  request_type: string;
  summary: string;
  created_at: string;
  link: string;
}
interface Alert {
  type: string;
  date: string;
  days_left: number;
  contract_id: number;
  contract_reference: string;
  employee_name: string;
}

function useData<T>(url: string | null, list = true) {
  const [data, setData] = useState<T | null>(null);
  useEffect(() => {
    if (!url) return;
    api
      .get(url)
      .then((res) => setData((list ? asList(res.data) : res.data) as T))
      .catch(() => setData(null));
  }, [url]);
  return data;
}

const PURPLE = "var(--odoo-purple)";
const TEAL = "var(--odoo-teal)";
const SAP_BLUE = "var(--sap-blue)";
const SAP_CRITICAL = "var(--sap-critical)";

export default function Home() {
  const { user } = useAuth();
  const perms = usePermissions();
  const hr = perms.can("employees", "modify");
  const payroll = perms.can("payroll", "consult");

  const approvals = useData<Approval[]>("notifications/approvals/") || [];
  const alerts = useData<Alert[]>(perms.can("contracts", "modify") ? "contracts/alerts/" : null) || [];
  const employees = useData<any[]>(hr || perms.isManager ? "employees/" : null);
  const balance = useData<any>(perms.employee_id ? "leave/requests/balance/" : null, false);
  const periods = useData<any[]>(payroll ? "payroll/periods/" : null);
  const shifts = useData<any[]>(perms.employee_id ? `planning/entries/?employee=${perms.employee_id}&date__gte=${new Date().toISOString().slice(0, 10)}` : null);
  const leaveRequests = useData<any[]>(perms.isManager || hr ? "leave/requests/?status=SUBMITTED" : null);

  const activeEmployees = (employees || []).filter((e) => e.status === "ACTIVE").length;
  const currentPeriod = (periods || [])[0];
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <>
      <PageHeader
        eyebrow="Overview"
        title={`${greeting}, ${user?.first_name || user?.username || ""}`}
        subtitle="Here is what needs your attention today."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiTile label="Waiting for my approval" value={approvals.length} accent={PURPLE} hint={<Link to="/approvals" className="text-brand-500 hover:underline dark:text-brand-300">Open the inbox →</Link>} />
        {employees && <KpiTile label={hr ? "Active employees" : "My team"} value={activeEmployees} accent={TEAL} hint={`${employees.length} records in total`} />}
        {perms.can("contracts", "modify") && <KpiTile label="Contract deadlines" value={alerts.length} accent={SAP_CRITICAL} hint="Ends of contract & trial periods" />}
        {balance && <KpiTile label="My leave balance" value={`${fmt.number(balance.available)} d`} accent={SAP_BLUE} hint={`${fmt.number(balance.acquired)} acquired · ${fmt.number(balance.taken)} taken`} />}
        {payroll && currentPeriod && (
          <KpiTile
            label={`Payroll ${String(currentPeriod.month).padStart(2, "0")}/${currentPeriod.year}`}
            value={<StatusBadge value={currentPeriod.status} label={currentPeriod.status_label} />}
            accent={TEAL}
            hint={currentPeriod.totals?.net_payable ? `Net payable ${fmt.money(currentPeriod.totals.net_payable)}` : "Not calculated yet"}
          />
        )}
        {(perms.isManager || hr) && leaveRequests && (
          <KpiTile label="Leave requests pending" value={leaveRequests.length} accent={PURPLE} />
        )}
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <Card title="My approvals" actions={<Link to="/approvals" className="btn-ghost">See all</Link>} padded={false}>
            <DataTable<Approval>
              rows={approvals.slice(0, 6)}
              empty="No request is waiting for you."
              columns={[
                { key: "summary", header: "Request", render: (a) => <span className="font-medium text-primary-c">{a.summary}</span> },
                { key: "request_type", header: "Type", render: (a) => <StatusBadge value="PENDING" label={a.request_type.replace(/_/g, " ").toLowerCase()} /> },
                { key: "created_at", header: "Received", render: (a) => fmt.datetime(a.created_at) },
              ]}
            />
          </Card>

          {perms.can("contracts", "modify") && (
            <Card title="Upcoming contract deadlines (BN-31)" padded={false}>
              <DataTable<Alert>
                rows={alerts}
                rowKey={(a) => `${a.type}-${a.contract_id}`}
                empty="No deadline in the coming weeks."
                columns={[
                  { key: "employee_name", header: "Employee", render: (a) => <Link className="font-medium text-brand-600 hover:underline dark:text-brand-300" to={`/contracts/${a.contract_id}`}>{a.employee_name}</Link> },
                  { key: "type", header: "Deadline", render: (a) => <span className={a.type === "TRIAL_END" ? "badge-blue" : "badge-orange"}>{a.type === "TRIAL_END" ? "End of trial period" : "End of contract"}</span> },
                  { key: "date", header: "Date", render: (a) => fmt.date(a.date) },
                  { key: "days_left", header: "Days left", align: "end", mono: true },
                ]}
              />
            </Card>
          )}
        </div>

        <div className="space-y-5">
          {perms.employee_id && <ClockWidget />}
          {perms.employee_id && (
            <Card title="My next shifts" actions={<Link to="/my/time" className="btn-ghost">Timetable</Link>}>
              {(shifts || []).length === 0 ? (
                <p className="text-sm text-muted-c">No published shift ahead.</p>
              ) : (
                <ul className="space-y-2">
                  {(shifts || []).slice(0, 5).map((s) => (
                    <li key={s.id} className="flex items-center justify-between gap-3 text-sm">
                      <span className="text-secondary-c">{fmt.date(s.date)}</span>
                      <span className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.shift_color }} />
                        <span className="text-primary-c">{s.shift_name}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )}
          <Card title="Quick links">
            <div className="grid grid-cols-2 gap-2">
              {perms.employee_id && <Link className="btn-secondary" to="/my/leave">Request leave</Link>}
              {perms.employee_id && <Link className="btn-secondary" to="/my/payslips">My payslips</Link>}
              {perms.employee_id && <Link className="btn-secondary" to="/my/documents">Attestations</Link>}
              {hr && <Link className="btn-secondary" to="/employees/new">New employee</Link>}
              {perms.can("contracts", "create") && <Link className="btn-secondary" to="/contracts">Contracts</Link>}
              {payroll && <Link className="btn-secondary" to="/payroll">Payroll</Link>}
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
