import { fmt } from "@/api/helpers";
import CrudSection from "@/components/kit/CrudSection";
import { useHashTab } from "@/components/kit/hooks";
import { BODIES, classificationField, departmentField, elementField, employeeField, opt } from "@/components/kit/options";
import { Badge, PageHeader, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";

const KINDS = opt([["GAIN", "Gain"], ["GROSS_DEDUCTION", "Deduction from gross"], ["NET_DEDUCTION", "Deduction from net"]]);
const METHODS = opt([["FIXED", "Fixed amount"], ["RATE", "Rate × base"], ["FORMULA", "Formula"], ["QUANTITY", "Quantity × unit value"]]);
const FORMULA_HINT =
  "Variables: BASE, BASE_FULL, GROSS, TAXABLE, CONTRIBUTORY, CASH_TAXABLE, HOURLY_RATE, SENIORITY_YEARS, CHILDREN, VALUE, QUANTITY, parameter codes… Functions: min, max, round, floor, if_(cond, a, b).";

/** BN-87 → BN-92 and BN-98, BN-99: every payroll setting, dated, without development. */
export default function PayrollSettings() {
  const [tab, setTab] = useHashTab("parameters");
  const { can } = usePermissions();
  const edit = can("payroll", "modify");
  const common = { canCreate: edit, canEdit: edit, canDelete: edit };
  return (
    <>
      <PageHeader
        title="Payroll settings"
        eyebrow="Payroll"
        subtitle="No rate, ceiling or scale is written in the code: add a new version with its effective date when the law changes."
      />
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "parameters", label: "Parameters" },
          { id: "deductions", label: "Contributions & taxes" },
          { id: "scales", label: "Scales" },
          { id: "elements", label: "Salary elements" },
          { id: "values", label: "Element values" },
          { id: "grid", label: "Salary grid" },
          { id: "loans", label: "Loans & advances" },
          { id: "third", label: "Third-party deductions" },
          { id: "history", label: "History" },
        ]}
      />
      {tab === "parameters" && (
        <CrudSection
          {...common}
          endpoint="payroll/parameters/"
          title="Dated parameters"
          description="Several versions of a code can exist: the one in force at the end of the period is used."
          fields={[
            { name: "code", label: "Code", required: true, placeholder: "e.g. SMIG" },
            { name: "name", label: "Name", required: true },
            { name: "value", label: "Value", type: "number", step: "0.0001", required: true },
            { name: "unit", label: "Unit", type: "select", options: opt([["AMOUNT", "Amount"], ["PERCENT", "Percentage"], ["NUMBER", "Number"]]) },
            { name: "effective_from", label: "Effective from", type: "date", required: true },
            { name: "description", label: "Description", type: "textarea" },
          ]}
          defaults={{ unit: "AMOUNT" }}
          columns={[
            { key: "code", header: "Code", mono: true },
            { key: "name", header: "Name" },
            { key: "value", header: "Value", align: "end", render: (p: any) => `${fmt.number(p.value, 4)}${p.unit === "PERCENT" ? " %" : ""}` },
            { key: "effective_from", header: "From", render: (p: any) => fmt.date(p.effective_from) },
            { key: "description", header: "Note" },
          ]}
        />
      )}
      {tab === "deductions" && (
        <CrudSection
          {...common}
          endpoint="payroll/deductions/"
          title="Social contributions and taxes withheld at source"
          modalSize="lg"
          fields={[
            { name: "code", label: "Code", required: true },
            { name: "name", label: "Name", required: true },
            { name: "body", label: "Body", type: "select", required: true, options: [...BODIES, { value: "OTHER", label: "Other" }] },
            { name: "method", label: "Method", type: "select", required: true, options: opt([["RATE", "Rates"], ["SCALE", "Scale"], ["PERCENT_OF", "Percentage of another deduction"]]) },
            { name: "base_formula", label: "Base (formula)", full: true, hint: FORMULA_HINT },
            { name: "employee_rate", label: "Employee rate (%)", type: "number", step: "0.0001" },
            { name: "employer_rate", label: "Employer rate (%)", type: "number", step: "0.0001" },
            { name: "ceiling", label: "Ceiling", type: "number" },
            { name: "floor", label: "Floor", type: "number" },
            { name: "scale_code", label: "Scale code", hidden: (v) => v.method !== "SCALE" },
            { name: "result_divisor", label: "Divide the result by", type: "number", hidden: (v) => v.method !== "SCALE" },
            { name: "percent_of_code", label: "Percentage of (code)", hidden: (v) => v.method !== "PERCENT_OF" },
            { name: "condition_formula", label: "Applies only if (formula)", full: true },
            { name: "order", label: "Order", type: "number" },
            { name: "effective_from", label: "Effective from", type: "date", required: true },
            { name: "on_payslip", label: "On the payslip", type: "checkbox" },
            { name: "is_active", label: "Active", type: "checkbox" },
          ]}
          defaults={{ method: "RATE", base_formula: "CONTRIBUTORY", result_divisor: 1, order: 10, on_payslip: true, is_active: true }}
          columns={[
            { key: "code", header: "Code", mono: true },
            { key: "name", header: "Name" },
            { key: "body_label", header: "Body" },
            { key: "employee_rate", header: "Employee", align: "end", render: (d: any) => (d.method === "SCALE" ? `scale ${d.scale_code}` : `${fmt.number(d.employee_rate, 4)} %`) },
            { key: "employer_rate", header: "Employer", align: "end", render: (d: any) => (d.method === "SCALE" ? "—" : `${fmt.number(d.employer_rate, 4)} %`) },
            { key: "effective_from", header: "From", render: (d: any) => fmt.date(d.effective_from) },
            { key: "is_active", header: "", render: (d: any) => (d.is_active ? null : <Badge>Inactive</Badge>) },
          ]}
        />
      )}
      {tab === "scales" && (
        <CrudSection
          {...common}
          endpoint="payroll/scales/"
          title="Scales (income tax, audiovisual fee, local tax, severance…)"
          modalSize="lg"
          fields={[
            { name: "code", label: "Code", required: true },
            { name: "name", label: "Name", required: true },
            { name: "kind", label: "Kind", type: "select", required: true, options: opt([["PROGRESSIVE", "Progressive rates"], ["FLAT", "Flat amount per bracket"]]) },
            { name: "effective_from", label: "Effective from", type: "date", required: true },
            { name: "brackets", label: "Brackets", type: "json", full: true, rows: 10,
              hint: 'Progressive: [{"from": 0, "to": 2000000, "rate": 10}, …]; flat: [{"from": 0, "to": 50000, "amount": 0}, …]; "to": null = no limit.' },
          ]}
          defaults={{ kind: "PROGRESSIVE", brackets: [] }}
          columns={[
            { key: "code", header: "Code", mono: true },
            { key: "name", header: "Name" },
            { key: "kind", header: "Kind" },
            { key: "brackets", header: "Brackets", align: "end", render: (s: any) => s.brackets?.length },
            { key: "effective_from", header: "From", render: (s: any) => fmt.date(s.effective_from) },
          ]}
        />
      )}
      {tab === "elements" && (
        <CrudSection
          {...common}
          endpoint="payroll/elements/"
          title="Catalogue of salary elements"
          modalSize="lg"
          canDelete={(e: any) => edit && !e.is_system}
          fields={[
            { name: "code", label: "Code", required: true },
            { name: "name", label: "Name", required: true },
            { name: "kind", label: "Kind", type: "select", required: true, options: KINDS },
            { name: "method", label: "Calculation", type: "select", required: true, options: METHODS },
            { name: "default_value", label: "Default value (amount / % / unit)", type: "number", step: "0.0001" },
            { name: "rate_base", label: "Base of the rate (formula)", hidden: (v) => v.method !== "RATE" },
            { name: "formula", label: "Formula", full: true, hint: FORMULA_HINT, hidden: (v) => !["FORMULA", "QUANTITY"].includes(v.method) },
            { name: "periodicity", label: "Periodicity", type: "select", options: opt([["MONTHLY", "Every month"], ["ANNUAL", "Once a year"]]) },
            { name: "payment_month", label: "Month of payment", type: "number", hidden: (v) => v.periodicity !== "ANNUAL" },
            { name: "payslip_order", label: "Order on the payslip", type: "number" },
            { name: "is_contributory", label: "Subject to contributions", type: "checkbox" },
            { name: "is_taxable", label: "Taxable", type: "checkbox" },
            { name: "in_leave_allowance_base", label: "In the leave allowance base", type: "checkbox" },
            { name: "is_benefit_in_kind", label: "Benefit in kind (not paid in cash)", type: "checkbox" },
            { name: "prorated", label: "Pro rata of the days paid", type: "checkbox" },
            { name: "applies_to_all", label: "For every employee", type: "checkbox" },
            { name: "on_payslip", label: "On the payslip", type: "checkbox" },
            { name: "is_active", label: "Active", type: "checkbox" },
          ]}
          defaults={{ kind: "GAIN", method: "FIXED", periodicity: "MONTHLY", payslip_order: 100, is_contributory: true, is_taxable: true,
            in_leave_allowance_base: true, prorated: true, on_payslip: true, is_active: true }}
          columns={[
            { key: "code", header: "Code", mono: true },
            { key: "name", header: "Name" },
            { key: "kind", header: "Kind", render: (e: any) => KINDS.find((k) => k.value === e.kind)?.label },
            { key: "method", header: "Calculation", render: (e: any) => METHODS.find((m) => m.value === e.method)?.label },
            { key: "flags", header: "Subject to", render: (e: any) => (
              <span className="flex flex-wrap gap-1">
                {e.is_contributory && <Badge tone="purple">CNPS</Badge>}
                {e.is_taxable && <Badge tone="blue">Tax</Badge>}
                {e.is_benefit_in_kind && <Badge tone="orange">In kind</Badge>}
                {e.is_system && <Badge tone="teal">Automatic</Badge>}
              </span>
            ) },
          ]}
        />
      )}
      {tab === "values" && (
        <CrudSection
          {...common}
          endpoint="payroll/element-values/"
          title="Values at three levels"
          description="The most specific level wins: employee, then department, then category, then the default value."
          fields={[
            elementField(),
            employeeField("employee", "Employee (individual value)", false),
            departmentField(),
            classificationField(),
            { name: "value", label: "Value", type: "number", step: "0.0001", required: true },
            { name: "effective_from", label: "From", type: "date", required: true },
            { name: "effective_to", label: "To", type: "date" },
            { name: "comment", label: "Comment", full: true },
          ]}
          columns={[
            { key: "element_name", header: "Element", render: (v: any) => `${v.element_name} (${v.element_code})` },
            { key: "level", header: "Level", render: (v: any) => <Badge tone={v.level === "EMPLOYEE" ? "purple" : v.level === "DEPARTMENT" ? "teal" : "blue"}>{v.level}</Badge> },
            { key: "target", header: "For", render: (v: any) => v.employee_name || v.department_name || v.classification_label },
            { key: "value", header: "Value", align: "end", render: (v: any) => fmt.number(v.value, 2) },
            { key: "effective_from", header: "Period", render: (v: any) => `${fmt.date(v.effective_from)} → ${v.effective_to ? fmt.date(v.effective_to) : "…"}` },
          ]}
        />
      )}
      {tab === "grid" && (
        <CrudSection
          {...common}
          endpoint="payroll/grid/"
          title="Salary grid"
          description="The calculated salary cannot be below the grid of the category nor below the minimum wage."
          fields={[classificationField("classification", "Category / grade", true), { name: "base_salary", label: "Base salary", type: "number", required: true }, { name: "effective_from", label: "From", type: "date", required: true }]}
          columns={[
            { key: "classification_label", header: "Category / grade" },
            { key: "base_salary", header: "Base salary", align: "end", render: (g: any) => fmt.money(g.base_salary) },
            { key: "effective_from", header: "From", render: (g: any) => fmt.date(g.effective_from) },
          ]}
        />
      )}
      {tab === "loans" && (
        <CrudSection
          {...common}
          endpoint="payroll/loans/"
          title="Salary advances and loans"
          fields={[
            employeeField(),
            { name: "kind", label: "Kind", type: "select", required: true, options: opt([["LOAN", "Loan"], ["ADVANCE", "Salary advance"]]) },
            { name: "amount", label: "Amount", type: "number", required: true },
            { name: "installment", label: "Monthly instalment", type: "number", required: true },
            { name: "granted_on", label: "Granted on", type: "date", required: true },
            { name: "first_month", label: "First month deducted (1-12)", type: "number", required: true },
            { name: "first_year", label: "Year of the first deduction", type: "number", required: true },
            { name: "comment", label: "Comment", full: true },
          ]}
          defaults={{ kind: "LOAN" }}
          columns={[
            { key: "employee_name", header: "Employee" },
            { key: "kind", header: "Kind" },
            { key: "amount", header: "Amount", align: "end", render: (l: any) => fmt.money(l.amount) },
            { key: "installment", header: "Instalment", align: "end", render: (l: any) => fmt.money(l.installment) },
            { key: "remaining", header: "Remaining", align: "end", render: (l: any) => fmt.money(l.remaining) },
            { key: "status", header: "Status", render: (l: any) => <Badge tone={l.status === "ACTIVE" ? "blue" : "gray"}>{l.status}</Badge> },
          ]}
        />
      )}
      {tab === "third" && (
        <CrudSection
          {...common}
          endpoint="payroll/third-party/"
          title="Garnishments, alimony, union dues"
          fields={[
            employeeField(),
            { name: "kind", label: "Kind", type: "select", required: true, options: opt([["GARNISHMENT", "Garnishment"], ["ALIMONY", "Alimony"], ["UNION", "Union dues"], ["OTHER", "Other"]]) },
            { name: "beneficiary", label: "Beneficiary", required: true },
            { name: "monthly_amount", label: "Monthly amount", type: "number" },
            { name: "rate_of_net", label: "or % of the net", type: "number", step: "0.01" },
            { name: "total_ceiling", label: "Total to deduct", type: "number" },
            { name: "start_date", label: "From", type: "date", required: true },
            { name: "end_date", label: "To", type: "date" },
            { name: "is_active", label: "Active", type: "checkbox" },
          ]}
          defaults={{ is_active: true }}
          columns={[
            { key: "employee_name", header: "Employee" },
            { key: "kind", header: "Kind" },
            { key: "beneficiary", header: "Beneficiary" },
            { key: "monthly_amount", header: "Monthly", align: "end", render: (d: any) => (d.monthly_amount ? fmt.money(d.monthly_amount) : `${d.rate_of_net} %`) },
            { key: "deducted", header: "Deducted", align: "end", render: (d: any) => fmt.money(d.deducted) },
          ]}
        />
      )}
      {tab === "history" && (
        <CrudSection
          endpoint="payroll/history/"
          title="History of the payroll settings"
          canCreate={false}
          canEdit={false}
          canDelete={false}
          columns={[
            { key: "changed_at", header: "Date", render: (h: any) => fmt.datetime(h.changed_at) },
            { key: "author_name", header: "By" },
            { key: "object_type", header: "Setting" },
            { key: "object_code", header: "Code", mono: true },
            { key: "change", header: "Change", render: (h: any) => (
              <span className="mono text-xs">
                {h.previous_value ? "modified" : "created"}
                {h.previous_value && !h.new_value ? " → deleted" : ""}
              </span>
            ) },
          ]}
        />
      )}
    </>
  );
}
