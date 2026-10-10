import { useState } from "react";
import { useNavigate } from "react-router";
import { fmt } from "@/api/helpers";
import DataTable from "@/components/kit/DataTable";
import { FormModal } from "@/components/kit/Form";
import { useApiList } from "@/components/kit/hooks";
import { CONTRACT_TYPES } from "@/components/kit/options";
import { Card, PageHeader, StatusBadge } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { contractFields } from "./contractFields";

export interface ContractRow {
  id: number;
  reference: string;
  employee: number;
  employee_name: string;
  employee_matriculation: string;
  contract_type: string;
  contract_type_label: string;
  status: string;
  start_date: string;
  end_date: string | null;
  effective_end_date: string | null;
  position_title: string | null;
  department_name: string | null;
  base_salary: string | null;
  salary_hidden?: boolean;
}

export default function ContractList() {
  const [filters, setFilters] = useState({ status: "", contract_type: "", search: "" });
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
  const { rows, loading, reload } = useApiList<ContractRow>("contracts/", params);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const { can } = usePermissions();

  return (
    <>
      <PageHeader
        eyebrow="Personnel"
        title="Contracts"
        subtitle="Contracts, amendments, renewals, suspensions and terminations (M-04)."
        actions={
          can("contracts", "create") && (
            <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
              + New contract
            </button>
          )
        }
      />
      <Card padded={false}>
        <div className="flex flex-wrap gap-2 border-b p-4" style={{ borderColor: "var(--border-color)" }}>
          <input
            className="input-field max-w-xs"
            placeholder="Search a reference or an employee…"
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
          <select className="input-field max-w-[12rem]" value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">All statuses</option>
            {["DRAFT", "ACTIVE", "SUSPENDED", "TERMINATED", "EXPIRED"].map((s) => (
              <option key={s} value={s}>
                {s.toLowerCase()}
              </option>
            ))}
          </select>
          <select className="input-field max-w-[14rem]" value={filters.contract_type} onChange={(e) => setFilters({ ...filters, contract_type: e.target.value })}>
            <option value="">All types</option>
            {CONTRACT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <DataTable<ContractRow>
          rows={rows}
          loading={loading}
          onRowClick={(c) => navigate(`/contracts/${c.id}`)}
          empty="No contract yet."
          columns={[
            { key: "reference", header: "Reference", mono: true, render: (c) => <span className="font-semibold text-brand-600 dark:text-brand-300">{c.reference}</span> },
            { key: "employee_name", header: "Employee", render: (c) => (
              <div>
                <p className="font-medium text-primary-c">{c.employee_name}</p>
                <p className="mono text-[11px] text-muted-c">{c.employee_matriculation}</p>
              </div>
            ) },
            { key: "contract_type_label", header: "Type" },
            { key: "position_title", header: "Position" },
            { key: "start_date", header: "Start", render: (c) => fmt.date(c.start_date) },
            { key: "effective_end_date", header: "End", render: (c) => fmt.date(c.effective_end_date) },
            { key: "base_salary", header: "Base salary", align: "end", mono: true, render: (c) => (c.salary_hidden ? <span className="text-muted-c">•••••</span> : fmt.money(c.base_salary)) },
            { key: "status", header: "Status", render: (c) => <StatusBadge value={c.status} /> },
          ]}
        />
      </Card>
      <FormModal
        open={creating}
        title="New contract (draft)"
        fields={contractFields()}
        initial={{ contract_type: "PERMANENT", notice_period_days: 30, weekly_hours: 40 }}
        endpoint="contracts/"
        size="lg"
        onClose={() => setCreating(false)}
        onSaved={(data) => {
          reload();
          if (data?.id) navigate(`/contracts/${data.id}`);
        }}
        submitLabel="Create the draft"
      />
    </>
  );
}
