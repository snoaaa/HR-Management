import type { ReactNode } from "react";
import {
  LayoutDashboard,
  CheckCircle2,
  Bell,
  Users,
  FileText,
  Building2,
  Clock,
  Calendar,
  CalendarDays,
  Banknote,
  Receipt,
  Calculator,
  Sliders,
  FolderArchive,
  Shield,
  History,
  User,
} from "lucide-react";
import type { Action, Module } from "@/context/PermissionsContext";

export interface NavItem {
  name: string;
  path: string;
  icon: ReactNode;
  /** Visible when the user has this permission. */
  module?: Module;
  action?: Action;
  /** Visible only for these roles. */
  roles?: string[];
  /** Visible only for users linked to an employee record. */
  needsEmployee?: boolean;
  /** Custom rule. */
  when?: (ctx: { can: (m: Module, a?: Action) => boolean; role: string; isManager: boolean; employeeId: number | null; canViewSalary: boolean }) => boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

const ICON = "size-4.5 shrink-0";
const ADMIN_ROLES = ["SYSTEM_ADMINISTRATOR", "HR_MANAGER"];

export const NAVIGATION: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { name: "Dashboard", path: "/", icon: <LayoutDashboard className={ICON} /> },
      { name: "Approvals", path: "/approvals", icon: <CheckCircle2 className={ICON} /> },
      { name: "Notifications", path: "/notifications", icon: <Bell className={ICON} /> },
    ],
  },
  {
    label: "Personnel",
    items: [
      {
        name: "Employees",
        path: "/employees",
        icon: <Users className={ICON} />,
        when: ({ can, role, isManager }) =>
          can("employees", "modify") || isManager || ["GENERAL_MANAGEMENT", "PAYROLL_OFFICER", "SYSTEM_ADMINISTRATOR"].includes(role),
      },
      {
        name: "Contracts",
        path: "/contracts",
        icon: <FileText className={ICON} />,
        when: ({ can }) => can("contracts", "modify") || can("contracts", "validate"),
      },
      {
        name: "Organisation",
        path: "/organisation",
        icon: <Building2 className={ICON} />,
        module: "organisation",
        action: "modify",
      },
    ],
  },
  {
    label: "Time & Absence",
    items: [
      {
        name: "Attendance",
        path: "/attendance",
        icon: <Clock className={ICON} />,
        when: ({ can, isManager }) => can("attendance", "modify") || can("attendance", "validate") || isManager,
      },
      {
        name: "Leave",
        path: "/leave",
        icon: <Calendar className={ICON} />,
        when: ({ can, isManager }) => can("leave", "modify") || isManager,
      },
      {
        name: "Planning",
        path: "/planning",
        icon: <CalendarDays className={ICON} />,
        when: ({ can, isManager }) => can("planning", "modify") || isManager,
      },
    ],
  },
  {
    label: "Payroll",
    items: [
      {
        name: "Payroll cycle",
        path: "/payroll",
        icon: <Banknote className={ICON} />,
        when: ({ can }) => can("payroll", "consult"),
      },
      {
        name: "Payslips",
        path: "/payroll/payslips",
        icon: <Receipt className={ICON} />,
        when: ({ can, canViewSalary }) => can("payroll", "consult") && canViewSalary,
      },
      {
        name: "Simulation",
        path: "/payroll/simulation",
        icon: <Calculator className={ICON} />,
        when: ({ can, canViewSalary }) => can("payroll", "modify") && canViewSalary,
      },
      {
        name: "Payroll settings",
        path: "/payroll/settings",
        icon: <Sliders className={ICON} />,
        when: ({ can }) => can("payroll", "modify"),
      },
    ],
  },
  {
    label: "Documents",
    items: [
      {
        name: "Documents",
        path: "/documents",
        icon: <FolderArchive className={ICON} />,
        when: ({ can }) => can("documents", "create"),
      },
    ],
  },
  {
    label: "Administration",
    items: [
      { name: "Users", path: "/users", icon: <Users className={ICON} />, roles: ADMIN_ROLES },
      { name: "Permissions", path: "/admin/permissions", icon: <Shield className={ICON} />, roles: ADMIN_ROLES },
      { name: "Workflow & settings", path: "/admin/settings", icon: <Sliders className={ICON} />, roles: ADMIN_ROLES },
      { name: "Audit trail", path: "/audit-trail", icon: <History className={ICON} />, module: "audit", action: "consult" },
    ],
  },
  {
    label: "My Space",
    items: [
      { name: "My profile", path: "/profile", icon: <User className={ICON} /> },
      { name: "My leave", path: "/my/leave", icon: <Calendar className={ICON} />, needsEmployee: true },
      { name: "My time & timetable", path: "/my/time", icon: <Clock className={ICON} />, needsEmployee: true },
      { name: "My payslips", path: "/my/payslips", icon: <Receipt className={ICON} />, needsEmployee: true },
      { name: "My documents", path: "/my/documents", icon: <FolderArchive className={ICON} />, needsEmployee: true },
    ],
  },
];
