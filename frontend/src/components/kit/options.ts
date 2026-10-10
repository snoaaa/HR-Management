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
