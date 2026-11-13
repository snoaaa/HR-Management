import { Link } from "react-router";
import { Avatar, Card, DefinitionList, PageHeader } from "@/components/kit/ui";
import Security from "@/components/UserProfile/Security";
import { useAuth } from "@/context/AuthContext";
import { usePermissions } from "@/context/PermissionsContext";
import { roleLabel } from "@/layout/roles";

/** My account: who I am in the system, and the security of my access. */
export default function UserProfiles() {
  const { user } = useAuth();
  const perms = usePermissions();
  const fullName = user ? `${user.first_name || ""} ${user.last_name || ""}`.trim() || user.username : "";

  return (
    <>
      <PageHeader title="My profile" subtitle="Your account in Saint Jean HRMS and the security of your access." />
      <div className="space-y-5">
        <Card>
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <Avatar name={fullName} size={72} />
            <div className="min-w-0 flex-1">
              <h2 className="truncate text-xl font-bold text-primary-c">{fullName}</h2>
              <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-secondary-c">
                <span className="badge-brand">{roleLabel(perms.role || user?.role)}</span>
                <span className="text-muted-c">@{user?.username}</span>
              </p>
            </div>
            {perms.employee_id && (
              <div className="flex flex-wrap gap-2">
                <Link to="/my/leave" className="btn-secondary">
                  My leave
                </Link>
                <Link to="/my/payslips" className="btn-secondary">
                  My payslips
                </Link>
              </div>
            )}
          </div>
          <div className="mt-6 border-t pt-5" style={{ borderColor: "var(--border-color)" }}>
            <DefinitionList
              items={[
                ["First name", user?.first_name || "—"],
                ["Last name", user?.last_name || "—"],
                ["E-mail address", user?.email || "—"],
                ["Username", user?.username],
              ]}
            />
            <p className="mt-5 text-[13px] text-muted-c">
              Is something wrong here? Your name, e-mail and role are managed by the HR department: ask them to correct it.
            </p>
          </div>
        </Card>
        <Security />
      </div>
    </>
  );
}
