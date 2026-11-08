import { fmt } from "@/api/helpers";
import CrudSection from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { useApiList, useHashTab } from "@/components/kit/hooks";
import { employeeField } from "@/components/kit/options";
import { Card, PageHeader, StatusBadge, Tabs } from "@/components/kit/ui";

function SalaryElements() {
  return (
    <CrudSection
      endpoint="payroll/elements/"
      title="Salary elements (BN-87, BN-88)"
      modalSize="md"
      columns={[
        {
          key: "name",
          header: "Element",
          render: (e: any) => (
            <div>
              <span className="font-medium text-primary-c">{e.name}</span>
              <span className="block text-[11px] mono text-muted-c">{e.code}</span>
            </div>
          ),
        },
        { key: "kind", header: "Type", render: (e: any) => <StatusBadge value={e.kind} /> },
        { key: "method", header: "Calculation method" },
        { key: "payslip_order", header: "Order", align: "end", mono: true },
        { key: "is_active", header: "Active", render: (e: any) => (e.is_active ? "yes" : "no") },
      ]}
      fields={[
        { name: "code", label: "Code", required: true, placeholder: "e.g. TRANSPORT" },
        { name: "name", label: "Element name", required: true, placeholder: "e.g. Transport Allowance" },
        {
          name: "kind",
          label: "Type",
          type: "select",
          required: true,
          options: [
            { value: "GROSS_ADDITION", label: "Gross addition (allowance/bonus)" },
            { value: "NET_DEDUCTION", label: "Net deduction" },
            { value: "BENEFIT_IN_KIND", label: "Benefit in kind" },
            { value: "EMPLOYER_CHARGE", label: "Employer contribution" },
          ],
        },
        {
          name: "method",
          label: "Method",
          type: "select",
          required: true,
          options: [
            { value: "FIXED", label: "Fixed amount" },
            { value: "PERCENT_OF_BASE", label: "Percentage of base salary" },
            { value: "FORMULA", label: "Formula" },
          ],
        },
        { name: "default_value", label: "Default amount / rate", type: "number" },
        { name: "payslip_order", label: "Print order on payslip", type: "number" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
    />
  );
}

function Parameters() {
  const { rows, loading } = useApiList<any>("payroll/parameters/");
  return (
    <Card padded={false} title="Statutory parameters (Cameroon Labour Code & Tax Regulations) (BN-89)">
      <DataTable
        rows={rows}
        loading={loading}
        columns={[
          {
            key: "name",
            header: "Parameter",
            render: (p: any) => (
              <div>
                <span className="font-semibold text-primary-c">{p.name}</span>
                <span className="block text-[11px] mono text-muted-c">{p.code}</span>
              </div>
            ),
          },
          {
            key: "value",
            header: "Value",
            align: "end",
            mono: true,
            render: (p: any) => (p.unit === "AMOUNT" ? fmt.money(p.value) : p.unit === "PERCENT" ? `${p.value}%` : p.value),
          },
          { key: "unit", header: "Unit" },
          { key: "effective_from", header: "Effective date", render: (p: any) => fmt.date(p.effective_from) },
          { key: "description", header: "Statutory note" },
        ]}
      />
    </Card>
  );
}

function Deductions() {
  const { rows, loading } = useApiList<any>("payroll/deductions/");
  return (
    <Card padded={false} title="Statutory deductions & contributions (CNPS, IRPP, CAC, CFC, FNE, RAV, TDL)">
      <DataTable
        rows={rows}
        loading={loading}
        columns={[
          {
            key: "name",
            header: "Contribution / Tax",
            render: (d: any) => (
              <div>
                <span className="font-semibold text-primary-c">{d.name}</span>
                <span className="block text-[11px] mono text-muted-c">{d.code}</span>
              </div>
            ),
          },
          { key: "employee_rate", header: "Employee rate", align: "end", mono: true, render: (d: any) => `${d.employee_rate || 0}%` },
          { key: "employer_rate", header: "Employer rate", align: "end", mono: true, render: (d: any) => `${d.employer_rate || 0}%` },
          { key: "ceiling", header: "Ceiling", align: "end", mono: true, render: (d: any) => (d.ceiling ? fmt.money(d.ceiling) : "No ceiling") },
          { key: "effective_from", header: "Effective date", render: (d: any) => fmt.date(d.effective_from) },
        ]}
      />
    </Card>
  );
}

function Loans() {
  return (
    <CrudSection
      endpoint="payroll/loans/"
      title="Advances and loans (BN-98)"
      modalSize="md"
      columns={[
        { key: "employee_name", header: "Employee" },
        { key: "kind", header: "Type", render: (l: any) => (l.kind === "SALARY_ADVANCE" ? "Salary Advance" : "Company Loan") },
        { key: "principal", header: "Principal", align: "end", mono: true, render: (l: any) => fmt.money(l.principal) },
        { key: "monthly_deduction", header: "Monthly installment", align: "end", mono: true, render: (l: any) => fmt.money(l.monthly_deduction) },
        { key: "balance", header: "Remaining balance", align: "end", mono: true, render: (l: any) => <b className="text-primary-c">{fmt.money(l.balance ?? l.principal)}</b> },
        { key: "status", header: "Status", render: (l: any) => <StatusBadge value={l.status || "ACTIVE"} /> },
      ]}
      fields={[
        employeeField(),
        {
          name: "kind",
          label: "Type",
          type: "select",
          required: true,
          options: [
            { value: "SALARY_ADVANCE", label: "Salary advance" },
            { value: "LOAN", label: "Company loan" },
          ],
        },
        { name: "principal", label: "Total amount (FCFA)", type: "number", required: true },
        { name: "monthly_deduction", label: "Monthly deduction amount (FCFA)", type: "number", required: true },
        { name: "start_date", label: "Start date", type: "date", required: true },
        { name: "reason", label: "Reason / Purpose" },
      ]}
    />
  );
}

export default function PayrollSettings() {
  const [tab, setTab] = useHashTab("elements");
  return (
    <>
      <PageHeader
        eyebrow="Payroll"
        title="Payroll Configuration"
        subtitle="Manage salary elements, statutory tax & social security scales, and loans repository."
      />
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "elements", label: "Salary elements (BN-87)" },
          { id: "parameters", label: "Statutory parameters (BN-89)" },
          { id: "deductions", label: "Deductions & taxes" },
          { id: "loans", label: "Loans & advances (BN-98)" },
        ]}
      />
      {tab === "elements" && <SalaryElements />}
      {tab === "parameters" && <Parameters />}
      {tab === "deductions" && <Deductions />}
      {tab === "loans" && <Loans />}
    </>
  );
}

