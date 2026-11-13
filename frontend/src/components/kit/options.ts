import type { FieldDef } from "./Form";

/** Reusable select fields pointing to reference lists. */
export const employeeField = (name = "employee", label = "Employee", required = true): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "employees/",
  optionLabel: (e) => `${e.given_names} ${e.surname} (${e.matriculation_number})`,
});

export const departmentField = (name = "department", label = "Department", required = false): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "organisation/departments/",
  optionLabel: (d) => `${d.name} (${d.code})`,
});

export const siteField = (name = "site", label = "Site", required = false): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "organisation/sites/",
  optionLabel: (s) => `${s.name} (${s.code})`,
});

export const positionField = (name = "position", label = "Position", required = false): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "organisation/positions/",
  optionLabel: (p) => `${p.title} (${p.code})`,
});

export const classificationField = (name = "classification", label = "Category / grade", required = false): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "organisation/classifications/",
  optionLabel: (c) => [c.category, c.grade, c.echelon].filter(Boolean).join(" – "),
});

export const userField = (name = "user", label = "User", required = false): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "users/management/",
  optionLabel: (u) => `${u.first_name || ""} ${u.last_name || ""} (${u.username})`.trim(),
});

export const ROLES = [
  { value: "HR_MANAGER", label: "HR Manager" },
  { value: "HR_OFFICER", label: "HR Officer" },
  { value: "PAYROLL_OFFICER", label: "Payroll Officer" },
  { value: "ACCOUNTANT", label: "Accountant" },
  { value: "HEAD_OF_DEPARTMENT", label: "Head of Department" },
  { value: "EMPLOYEE", label: "Employee" },
  { value: "GENERAL_MANAGEMENT", label: "General Management" },
  { value: "SYSTEM_ADMINISTRATOR", label: "System Administrator" },
];

export const CONTRACT_TYPES = [
  { value: "PERMANENT", label: "Permanent contract" },
  { value: "FIXED_TERM", label: "Fixed-term contract" },
  { value: "INTERNSHIP", label: "Internship agreement" },
  { value: "TEMPORARY", label: "Temporary work" },
  { value: "APPRENTICESHIP", label: "Apprenticeship" },
  { value: "SERVICE", label: "Service contract" },
];

export const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export const leaveTypeField = (name = "leave_type", label = "Type of leave", required = true): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "leave/types/",
  optionLabel: (t) => t.name,
});

export const shiftField = (name = "shift", label = "Shift", required = true): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "planning/shifts/",
  optionLabel: (s) => `${s.name} (${String(s.start_time).slice(0, 5)}–${String(s.end_time).slice(0, 5)})`,
});

export const elementField = (name = "element", label = "Salary element", required = true): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "payroll/elements/",
  optionLabel: (e) => `${e.name} (${e.code})`,
});

export const elementCodeField = (name = "bonus_element", label = "Bonus element", required = false): FieldDef => ({
  ...elementField(name, label, required),
  optionValue: (e) => e.code,
});

export const periodField = (name = "period", label = "Payroll period", required = true): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "payroll/periods/",
  optionLabel: (p) => `${String(p.month).padStart(2, "0")}/${p.year} – ${p.status_label || p.status}`,
});

export const accountField = (name = "account", label = "Account", required = false): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "accounting/accounts/",
  optionLabel: (a) => `${a.number} – ${a.name}`,
});

export const skillField = (name = "skill", label = "Skill", required = true): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "training/skills/",
  optionLabel: (s) => s.name,
});

export const offerField = (name = "offer", label = "Job offer", required = false): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "recruitment/offers/",
  optionLabel: (o) => `${o.title} – ${o.department_name || ""}`,
});

export const sessionField = (name = "session", label = "Training session", required = false): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "training/sessions/",
  optionLabel: (s) => `${s.title} (${s.start_date})`,
});

export const costCentreField = (name = "cost_centre", label = "Cost centre", required = false): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "organisation/cost-centres/",
  optionLabel: (c) => `${c.name} (${c.code})`,
});

export const timetableField = (name = "timetable", label = "Timetable", required = true): FieldDef => ({
  name,
  label,
  type: "select",
  required,
  optionsUrl: "planning/timetables/",
  optionLabel: (t) => `${t.name} (${t.department_name})`,
});

export const opt = (pairs: [string, string][]) => pairs.map(([value, label]) => ({ value, label }));

export const BODIES = opt([
  ["CNPS", "Social insurance (CNPS)"],
  ["TAX", "Tax administration (IRPP / CAC)"],
  ["CFC", "Crédit Foncier"],
  ["FNE", "National Employment Fund"],
  ["COMMUNE", "Council (TDL)"],
  ["CRTV", "Audiovisual fee (RAV)"],
]);
