import type { ReactNode } from "react";
import {
  BellAltIcon,
  CalenderIcon,
  CheckCircleIcon,
  DocsIcon,
  DollarLineIcon,
  FileIcon,
  GridIcon,
  GroupIcon,
  ListIcon,
  LockIcon,
  PieChartIcon,
  SettingsAltIcon,
  TaskIcon,
  TimeIcon,
  UserCircleIcon,
  UserMoneyIcon,
} from "@/icons";
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

const ICON = "size-5";
const ADMIN_ROLES = ["SYSTEM_ADMINISTRATOR", "HR_MANAGER"];

export const NAVIGATION: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { name: "Dashboard", path: "/", icon: <GridIcon className={ICON} /> },
      { name: "Approvals", path: "/approvals", icon: <CheckCircleIcon className={ICON} /> },
      { name: "Notifications", path: "/notifications", icon: <BellAltIcon className={ICON} /> },
    ],
  },
  {
    label: "Personnel",
    items: [
      {
        name: "Employees",
        path: "/employees",
        icon: <GroupIcon className={ICON} />,
        when: ({ can, role, isManager }) => can("employees", "modify") || isManager || ["GENERAL_MANAGEMENT", "PAYROLL_OFFICER", "SYSTEM_ADMINISTRATOR"].includes(role),
      },
      { name: "Contracts", path: "/contracts", icon: <FileIcon className={ICON} />, when: ({ can }) => can("contracts", "modify") || can("contracts", "validate") },
      { name: "Organisation", path: "/organisation", icon: <SettingsAltIcon className={ICON} />, module: "organisation", action: "modify" },
    ],
  },
  {
    label: "Time & absence",
    items: [
      {
        name: "Attendance",
        path: "/attendance",
        icon: <TimeIcon className={ICON} />,
        when: ({ can, isManager }) => can("attendance", "modify") || can("attendance", "validate") || isManager,
      },
      {
        name: "Leave",
        path: "/leave",
        icon: <CalenderIcon className={ICON} />,
        when: ({ can, isManager }) => can("leave", "modify") || isManager,
      },
      {
        name: "Planning",
        path: "/planning",
        icon: <TaskIcon className={ICON} />,
        when: ({ can, isManager }) => can("planning", "modify") || isManager,
      },
    ],
  },
  {
    label: "Payroll",
    items: [
      { name: "Payroll cycle", path: "/payroll", icon: <DollarLineIcon className={ICON} />, when: ({ can }) => can("payroll", "consult") },
      { name: "Payslips", path: "/payroll/payslips", icon: <UserMoneyIcon className={ICON} />, when: ({ can, canViewSalary }) => can("payroll", "consult") && canViewSalary },
      { name: "Simulation", path: "/payroll/simulation", icon: <PieChartIcon className={ICON} />, when: ({ can, canViewSalary }) => can("payroll", "modify") && canViewSalary },
      { name: "Payroll settings", path: "/payroll/settings", icon: <ListIcon className={ICON} />, when: ({ can }) => can("payroll", "modify") },
    ],
  },
  {
    label: "Documents",
    items: [
      { name: "Documents", path: "/documents", icon: <DocsIcon className={ICON} />, when: ({ can }) => can("documents", "create") },
    ],
  },
  {
    label: "Administration",
    items: [
      { name: "Users", path: "/users", icon: <GroupIcon className={ICON} />, roles: ADMIN_ROLES },
      { name: "Permissions", path: "/admin/permissions", icon: <LockIcon className={ICON} />, roles: ADMIN_ROLES },
      { name: "Workflow & settings", path: "/admin/settings", icon: <SettingsAltIcon className={ICON} />, roles: ADMIN_ROLES },
      { name: "Audit trail", path: "/audit-trail", icon: <FileIcon className={ICON} />, module: "audit", action: "consult" },
    ],
  },
  {
    label: "My space",
    items: [
      { name: "My profile", path: "/profile", icon: <UserCircleIcon className={ICON} /> },
      { name: "My leave", path: "/my/leave", icon: <CalenderIcon className={ICON} />, needsEmployee: true },
      { name: "My time & timetable", path: "/my/time", icon: <TimeIcon className={ICON} />, needsEmployee: true },
      { name: "My payslips", path: "/my/payslips", icon: <UserMoneyIcon className={ICON} />, needsEmployee: true },
      { name: "My documents", path: "/my/documents", icon: <DocsIcon className={ICON} />, needsEmployee: true },
    ],
  },
];
