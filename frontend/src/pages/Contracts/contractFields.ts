import type { FieldDef } from "@/components/kit/Form";
import {
  CONTRACT_TYPES,
  classificationField,
  departmentField,
  employeeField,
  positionField,
  siteField,
} from "@/components/kit/options";

export const contractFields = (fixedEmployee?: boolean): FieldDef[] => [
  { ...employeeField(), readOnly: fixedEmployee },
  { name: "contract_type", label: "Type of contract", type: "select", options: CONTRACT_TYPES, required: true },
  { name: "start_date", label: "Start date", type: "date", required: true },
  {
    name: "end_date",
    label: "End date",
    type: "date",
    hint: "Required for fixed-term, temporary and internship contracts.",
  },
  { name: "trial_period_end", label: "End of trial period", type: "date" },
  { name: "notice_period_days", label: "Notice (days)", type: "number" },
  { name: "weekly_hours", label: "Weekly working time (h)", type: "number", step: "0.5" },
  { name: "base_salary", label: "Agreed monthly base salary (XAF)", type: "number", step: "1" },
  positionField(),
  classificationField(),
  departmentField(),
  siteField("workplace", "Workplace"),
  { name: "notes", label: "Notes", type: "textarea" },
];

export const amendmentFields: FieldDef[] = [
  { name: "effective_date", label: "Effective date", type: "date", required: true },
  { name: "reason", label: "Reason", required: true },
  { name: "base_salary", label: "New base salary", type: "number", hint: "Leave empty to keep the current value." },
  { ...positionField("position_id", "New position") },
  { ...classificationField("classification_id", "New category / grade") },
  { ...departmentField("department_id", "New department") },
  { ...siteField("workplace_id", "New workplace") },
  { name: "weekly_hours", label: "New weekly working time", type: "number", step: "0.5" },
  { name: "end_date", label: "New end date", type: "date" },
];

export const suspensionFields: FieldDef[] = [
  {
    name: "reason",
    label: "Reason",
    type: "select",
    required: true,
    options: [
      { value: "UNPAID_LEAVE", label: "Unpaid leave" },
      { value: "SECONDMENT", label: "Secondment" },
      { value: "SICK_LEAVE", label: "Sick leave" },
      { value: "DETENTION", label: "Detention" },
      { value: "DISCIPLINARY", label: "Disciplinary suspension" },
      { value: "OTHER", label: "Other" },
    ],
  },
  { name: "start_date", label: "From", type: "date", required: true },
  { name: "end_date", label: "To (empty = open)", type: "date" },
  { name: "is_paid", label: "Salary maintained", type: "checkbox" },
  { name: "counts_for_seniority", label: "Counts for seniority", type: "checkbox" },
  { name: "comment", label: "Comment", type: "textarea" },
];

export const terminationFields: FieldDef[] = [
  {
    name: "reason",
    label: "Reason",
    type: "select",
    required: true,
    options: [
      { value: "RESIGNATION", label: "Resignation" },
      { value: "DISMISSAL", label: "Dismissal" },
      { value: "END_OF_CONTRACT", label: "End of fixed-term contract" },
      { value: "TRIAL_END", label: "End during trial period" },
      { value: "MUTUAL", label: "Mutual agreement" },
      { value: "RETIREMENT", label: "Retirement" },
      { value: "DEATH", label: "Death" },
    ],
  },
  { name: "notification_date", label: "Notified on", type: "date", required: true },
  { name: "termination_date", label: "Last working day", type: "date", required: true },
  { name: "notice_days", label: "Notice (days)", type: "number", hint: "Empty = notice of the contract." },
  { name: "notice_worked", label: "Notice worked", type: "checkbox" },
  { name: "leave_balance_days", label: "Remaining leave (days)", type: "number", hint: "Empty = computed from the leave balance." },
  { name: "comment", label: "Comment", type: "textarea" },
];

/** Remove empty values so that the API keeps the current ones. */
export function compact(payload: Record<string, any>) {
  const out: Record<string, any> = {};
  Object.entries(payload).forEach(([k, v]) => {
    if (v !== null && v !== "" && v !== undefined) out[k] = v;
  });
  return out;
}
