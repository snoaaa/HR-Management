import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import api from "@/api/axiosConfig";
import { asList, fmt } from "@/api/helpers";
import ClockWidget from "@/components/dashboard/ClockWidget";
import { BarList } from "@/components/kit/Charts";
import DataTable from "@/components/kit/DataTable";
import { Avatar, Card, KpiTile, PageHeader, StatusBadge } from "@/components/kit/ui";
import { useAuth } from "@/context/AuthContext";
import { usePermissions } from "@/context/PermissionsContext";
import { ArrowRightIcon, CalenderIcon, CheckLineIcon, DollarLineIcon, FileIcon, GroupIcon, TimeIcon } from "@/icons";
import { roleLabel } from "@/layout/roles";
import { useNavigation } from "@/layout/useNavigation";

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

/** Days until the next anniversary of a date (0 = today). */
function daysUntil(dateIso: string) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const d = new Date(dateIso);
  if (Number.isNaN(d.getTime())) return null;
  const next = new Date(today.getFullYear(), d.getMonth(), d.getDate());
  if (next < today) next.setFullYear(today.getFullYear() + 1);
  return Math.round((next.getTime() - today.getTime()) / 86_400_000);
}

/** Number of years completed at the next anniversary, `days` from today. */
function yearsAtNextAnniversary(dateIso: string, days: number) {
  const next = new Date();
  next.setDate(next.getDate() + days);
  return next.getFullYear() - new Date(dateIso).getFullYear();
}

export default function Home() {
  const { user } = useAuth();
  const perms = usePermissions();
  const { actions } = useNavigation();
  const hr = perms.can("employees", "modify");
  const payroll = perms.can("payroll", "consult");
  const contracts = perms.can("contracts", "modify");

  const approvals = useData<Approval[]>("notifications/approvals/") || [];
  const alerts = useData<Alert[]>(contracts ? "contracts/alerts/" : null) || [];
  const employees = useData<any[]>(hr || perms.isManager ? "employees/" : null);
  const balance = useData<any>(perms.employee_id ? "leave/requests/balance/" : null, false);
  const periods = useData<any[]>(payroll ? "payroll/periods/" : null);
  const shifts = useData<any[]>(perms.employee_id ? `planning/entries/?employee=${perms.employee_id}&date__gte=${new Date().toISOString().slice(0, 10)}` : null);
  const leaveRequests = useData<any[]>(perms.isManager || hr ? "leave/requests/?status=SUBMITTED" : null);

  const active = useMemo(() => (employees || []).filter((e) => e.status === "ACTIVE"), [employees]);
  const currentPeriod = (periods || [])[0];
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  const byDepartment = useMemo(() => {
    const counts = new Map<string, number>();
    active.forEach((e) => {
      const name = e.department_name || "Not assigned";
      counts.set(name, (counts.get(name) || 0) + 1);
    });
    return [...counts.entries()]
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [active]);

  // Birthdays and work anniversaries of the next 30 days.
  const celebrations = useMemo(() => {
    const list: { id: number; name: string; kind: string; days: number }[] = [];
    active.forEach((e) => {
      const name = e.full_name || `${e.surname || ""} ${e.given_names || ""}`.trim();
      const birthday = e.date_of_birth ? daysUntil(e.date_of_birth) : null;
      if (birthday !== null && birthday <= 30) list.push({ id: e.id, name, kind: "Birthday", days: birthday });
      const hired = e.date_of_hire ? daysUntil(e.date_of_hire) : null;
      const years = hired === null ? 0 : yearsAtNextAnniversary(e.date_of_hire, hired);
      if (hired !== null && hired <= 30 && years > 0) list.push({ id: e.id, name, kind: `${years} year${years > 1 ? "s" : ""} with us`, days: hired });
    });
    return list.sort((a, b) => a.days - b.days).slice(0, 6);
  }, [active]);

  const headline =
    approvals.length > 0
      ? `${approvals.length} request${approvals.length > 1 ? "s are" : " is"} waiting for your decision.`
      : "You are all caught up. Nothing is waiting for you.";

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Here is what needs your attention today." />

      {/* Welcome band: who I am, what is waiting, the main thing I can do. */}
      <section className="hero-band animate-fade-in overflow-hidden rounded-2xl p-6 sm:p-7">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <p className="text-[13px] text-secondary-c">{today}</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-[28px]">
              {greeting}, {user?.first_name || user?.username || ""}
            </h2>
            <p className="mt-2 flex flex-wrap items-center gap-2 text-sm text-secondary-c">
              <span className="hero-chip">{roleLabel(perms.role)}</span>
              {headline}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            {approvals.length > 0 && (
              <Link to="/approvals" className="btn-primary btn-lg">
                Review requests
                <ArrowRightIcon className="size-4 fill-current rtl:rotate-180" />
              </Link>
            )}
            {perms.employee_id && (
              <Link
                to="/my/leave"
                className={approvals.length > 0 ? "btn-secondary btn-lg" : "btn-primary btn-lg"}
              >
                Request leave
              </Link>
            )}
          </div>
        </div>
      </section>

      <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiTile
          label="Waiting for my approval"
          value={approvals.length}
          icon={<CheckLineIcon className="size-5" />}
          hint={<Link to="/approvals" className="link">Open the inbox</Link>}
        />
        {employees && (
          <KpiTile
            label={hr ? "Active employees" : "My team"}
            value={active.length}
            accent="var(--info)"
            icon={<GroupIcon className="size-5" />}
            hint={`${employees.length} records in total`}
          />
        )}
        {contracts && (
          <KpiTile
            label="Contract deadlines"
            value={alerts.length}
            accent="var(--sap-critical)"
            icon={<FileIcon className="size-5" />}
            hint="Ends of contract and trial periods"
          />
        )}
        {balance && (
          <KpiTile
            label="My leave balance"
            value={`${fmt.number(balance.available)} days`}
            accent="var(--success)"
            icon={<CalenderIcon className="size-5" />}
            hint={`${fmt.number(balance.acquired)} acquired · ${fmt.number(balance.taken)} taken`}
          />
        )}
        {payroll && currentPeriod && (
          <KpiTile
            label={`Payroll ${String(currentPeriod.month).padStart(2, "0")}/${currentPeriod.year}`}
            value={<StatusBadge value={currentPeriod.status} label={currentPeriod.status_label} />}
            accent="var(--success)"
            icon={<DollarLineIcon className="size-5" />}
            hint={currentPeriod.totals?.net_payable ? `Net payable ${fmt.money(currentPeriod.totals.net_payable)}` : "Not calculated yet"}
          />
        )}
        {(perms.isManager || hr) && leaveRequests && (
          <KpiTile
            label="Leave requests pending"
            value={leaveRequests.length}
            accent="var(--info)"
            icon={<TimeIcon className="size-5" />}
            hint={<Link to="/leave" className="link">See the requests</Link>}
          />
        )}
      </div>

      {actions.length > 0 && (
        <section className="mt-6">
          <h2 className="mb-3 text-[15px] font-semibold text-primary-c">Quick actions</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {actions.map((action) => (
              <Link
                key={action.name}
                to={action.path}
                className="card group flex items-center gap-3.5 p-4 transition-all hover:border-(--brand) hover:shadow-(--shadow-raised)"
              >
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-brand-c" style={{ background: "var(--brand-soft)" }}>
                  {action.icon}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold text-primary-c">{action.name}</span>
                  <span className="block truncate text-[13px] text-muted-c">{action.description}</span>
                </span>
                <ArrowRightIcon className="size-4 shrink-0 fill-current text-muted-c transition-transform group-hover:translate-x-0.5 group-hover:text-(--brand-strong) rtl:rotate-180" />
              </Link>
            ))}
          </div>
        </section>
      )}

      <div className="mt-6 grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <Card title="Waiting for my decision" actions={<Link to="/approvals" className="btn-ghost">See all</Link>} padded={false}>
            <DataTable<Approval>
              rows={approvals.slice(0, 6)}
              pageSize={0}
              empty="No request is waiting for you. Enjoy the calm!"
              columns={[
                {
                  key: "summary",
                  header: "Request",
                  render: (a) => (
                    <Link to={a.link || "/approvals"} className="font-semibold text-primary-c hover:text-(--brand-strong)">
                      {a.summary}
                    </Link>
                  ),
                },
                { key: "request_type", header: "Type", render: (a) => <StatusBadge value="PENDING" label={a.request_type.replace(/_/g, " ").toLowerCase()} /> },
                { key: "created_at", header: "Received", render: (a) => fmt.datetime(a.created_at) },
              ]}
            />
          </Card>

          {contracts && (
            <Card title="Upcoming contract deadlines" actions={<Link to="/contracts" className="btn-ghost">All contracts</Link>} padded={false}>
              <DataTable<Alert>
                rows={alerts}
                pageSize={8}
                rowKey={(a) => `${a.type}-${a.contract_id}`}
                empty="No contract or trial period ends in the coming weeks."
                columns={[
                  { key: "employee_name", header: "Employee", render: (a) => <Link className="link" to={`/contracts/${a.contract_id}`}>{a.employee_name}</Link> },
                  { key: "type", header: "Deadline", render: (a) => <span className={a.type === "TRIAL_END" ? "badge-blue" : "badge-orange"}>{a.type === "TRIAL_END" ? "End of trial period" : "End of contract"}</span> },
                  { key: "date", header: "Date", render: (a) => fmt.date(a.date) },
                  {
                    key: "days_left",
                    header: "Time left",
                    align: "end",
                    render: (a) => <span className={a.days_left <= 7 ? "font-semibold text-error-600 dark:text-error-400" : ""}>{a.days_left} days</span>,
                  },
                ]}
              />
            </Card>
          )}

          {hr && byDepartment.length > 0 && (
            <Card title="Headcount by department" actions={<Link to="/reports" className="btn-ghost">Reports</Link>}>
              <BarList data={byDepartment} format={(v) => `${v}`} />
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
                <ul className="space-y-2.5">
                  {(shifts || []).slice(0, 5).map((s) => (
                    <li key={s.id} className="flex items-center justify-between gap-3 text-sm">
                      <span className="text-secondary-c">{fmt.date(s.date)}</span>
                      <span className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.shift_color }} />
                        <span className="font-medium text-primary-c">{s.shift_name}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )}
          {hr && (
            <Card title="Celebrations in the next 30 days">
              {celebrations.length === 0 ? (
                <p className="text-sm text-muted-c">No birthday or work anniversary coming up.</p>
              ) : (
                <ul className="space-y-3">
                  {celebrations.map((c) => (
                    <li key={`${c.id}-${c.kind}`} className="flex items-center gap-3">
                      <Avatar name={c.name} size={34} />
                      <span className="min-w-0 flex-1">
                        <Link to={`/employees/${c.id}`} className="block truncate text-sm font-semibold text-primary-c hover:text-(--brand-strong)">
                          {c.name}
                        </Link>
                        <span className="block text-xs text-muted-c">{c.kind}</span>
                      </span>
                      <span className={c.days === 0 ? "badge-brand" : "badge-gray"}>{c.days === 0 ? "Today" : c.days === 1 ? "Tomorrow" : `In ${c.days} days`}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
