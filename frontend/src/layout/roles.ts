const ROLE_LABEL: Record<string, string> = {
  HR_MANAGER: "HR Manager",
  HR_OFFICER: "HR Officer",
  PAYROLL_OFFICER: "Payroll Officer",
  ACCOUNTANT: "Accountant",
  HEAD_OF_DEPARTMENT: "Head of Department",
  EMPLOYEE: "Employee",
  GENERAL_MANAGEMENT: "General Management",
  SYSTEM_ADMINISTRATOR: "System Administrator",
};

/** Readable name of a role code. */
export function roleLabel(role?: string | null) {
  if (!role) return "";
  return ROLE_LABEL[role] || role.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
}
