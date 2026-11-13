import type { ReactNode } from "react";
import {
  BellAltIcon,
  BrainIcon,
  ChartAltIcon,
  DataBaseIcon,
  DollarIcon,
  LikeIcon,
  ShootingStarIcon,
  UserAltIcon,
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

export interface NavRuleContext {
  can: (m: Module, a?: Action) => boolean;
  role: string;
  isManager: boolean;
  employeeId: number | null;
  canViewSalary: boolean;
}

export interface NavItem {
  name: string;
  path: string;
  icon: ReactNode;
  /** Plain-language words people may type when they look for this screen. */
  keywords?: string;
  /** Visible when the user has this permission. */
  module?: Module;
  action?: Action;
  /** Visible only for these roles. */
  roles?: string[];
  /** Visible only for users linked to an employee record. */
  needsEmployee?: boolean;
  /** Custom rule. */
  when?: (ctx: NavRuleContext) => boolean;
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
      { name: "Dashboard", path: "/", icon: <GridIcon className={ICON} /> },
      { name: "Approvals", path: "/approvals", keywords: "validate approve refuse inbox requests", icon: <CheckCircleIcon className={ICON} /> },
      { name: "Notifications", path: "/notifications", icon: <BellAltIcon className={ICON} /> },
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
      { name: "Contracts", path: "/contracts", icon: <FileIcon className={ICON} />, when: ({ can }) => can("contracts", "modify") || can("contracts", "validate") },
      { name: "Careers", path: "/careers-management", keywords: "promotion transfer career history org chart", icon: <ShootingStarIcon className={ICON} />, when: ({ can, isManager }) => can("careers", "modify") || can("careers", "validate") || isManager },
      { name: "Recruitment", path: "/recruitment", keywords: "hiring job offers candidates applications", icon: <UserAltIcon className={ICON} />, when: ({ can, isManager }) => can("recruitment", "modify") || can("recruitment", "validate") || isManager },
      { name: "Organisation", path: "/organisation", keywords: "company departments positions structure", icon: <SettingsAltIcon className={ICON} />, module: "organisation", action: "modify" },
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
      { name: "Payroll cycle", path: "/payroll", keywords: "salary pay run period", icon: <DollarLineIcon className={ICON} />, when: ({ can }) => can("payroll", "consult") },
      { name: "Payslips", path: "/payroll/payslips", keywords: "salary slip bulletin", icon: <UserMoneyIcon className={ICON} />, when: ({ can, canViewSalary }) => can("payroll", "consult") && canViewSalary },
      { name: "Simulation", path: "/payroll/simulation", keywords: "estimate net salary calculator", icon: <PieChartIcon className={ICON} />, when: ({ can, canViewSalary }) => can("payroll", "modify") && canViewSalary },
      { name: "Payroll settings", path: "/payroll/settings", icon: <ListIcon className={ICON} />, when: ({ can }) => can("payroll", "modify") },
      { name: "Accounting (OHADA)", path: "/accounting", keywords: "journal ledger entries books", icon: <DollarIcon className={ICON} />, when: ({ can }) => can("accounting", "consult") },
    ],
  },
  {
    label: "Development",
    items: [
      { name: "Evaluation", path: "/evaluation", icon: <LikeIcon className={ICON} />, when: ({ can, isManager }) => can("evaluation", "create") || isManager },
      { name: "Training", path: "/training", icon: <BrainIcon className={ICON} />, when: ({ can, isManager }) => can("training", "modify") || isManager },
    ],
  },
  {
    label: "Steering",
    items: [
      { name: "Reports & indicators", path: "/reports", keywords: "statistics kpi turnover absenteeism dashboard", icon: <ChartAltIcon className={ICON} />, when: ({ can, isManager, role }) => can("reports", "export") || isManager || role === "GENERAL_MANAGEMENT" },
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
      { name: "Users", path: "/users", icon: <GroupIcon className={ICON} />, roles: ADMIN_ROLES },
      { name: "Permissions", path: "/admin/permissions", icon: <LockIcon className={ICON} />, roles: ADMIN_ROLES },
      { name: "Workflow & settings", path: "/admin/settings", keywords: "configuration approval levels parameters", icon: <SettingsAltIcon className={ICON} />, roles: ADMIN_ROLES },
      { name: "Data: import & backups", path: "/admin/data", keywords: "excel upload restore export", icon: <DataBaseIcon className={ICON} />, module: "imports", action: "consult" },
      { name: "Audit trail", path: "/audit-trail", keywords: "history log who did what", icon: <FileIcon className={ICON} />, module: "audit", action: "consult" },
    ],
  },
  {
    label: "My Space",
    items: [
      { name: "My profile", path: "/profile", icon: <UserCircleIcon className={ICON} /> },
      { name: "My leave", path: "/my/leave", keywords: "holiday vacation absence request days off", icon: <CalenderIcon className={ICON} />, needsEmployee: true },
      { name: "My time & timetable", path: "/my/time", keywords: "clock shifts schedule hours", icon: <TimeIcon className={ICON} />, needsEmployee: true },
      { name: "My payslips", path: "/my/payslips", icon: <UserMoneyIcon className={ICON} />, needsEmployee: true },
      { name: "My documents", path: "/my/documents", keywords: "attestation certificate work certificate", icon: <DocsIcon className={ICON} />, needsEmployee: true },
      { name: "My evaluations", path: "/my/evaluations", icon: <LikeIcon className={ICON} />, needsEmployee: true },
      { name: "My training", path: "/my/training", icon: <BrainIcon className={ICON} />, needsEmployee: true },
    ],
  },
];

export interface QuickAction {
  name: string;
  description: string;
  path: string;
  icon: ReactNode;
  needsEmployee?: boolean;
  when?: (ctx: NavRuleContext) => boolean;
}

/** The most frequent tasks, offered by the "New" button and the search. */
export const QUICK_ACTIONS: QuickAction[] = [
  { name: "Request leave", description: "Ask for days off", path: "/my/leave", icon: <CalenderIcon className={ICON} />, needsEmployee: true },
  { name: "Get an attestation", description: "Work or salary certificate", path: "/my/documents", icon: <DocsIcon className={ICON} />, needsEmployee: true },
  { name: "Add an employee", description: "Create a new employee record", path: "/employees/new", icon: <GroupIcon className={ICON} />, when: ({ can }) => can("employees", "create") },
  { name: "Prepare a contract", description: "Draft or renew a contract", path: "/contracts", icon: <FileIcon className={ICON} />, when: ({ can }) => can("contracts", "create") },
  { name: "Run the payroll", description: "Open the current pay period", path: "/payroll", icon: <DollarLineIcon className={ICON} />, when: ({ can }) => can("payroll", "modify") },
  { name: "Publish a job offer", description: "Start a recruitment", path: "/recruitment", icon: <UserAltIcon className={ICON} />, when: ({ can }) => can("recruitment", "create") },
];
