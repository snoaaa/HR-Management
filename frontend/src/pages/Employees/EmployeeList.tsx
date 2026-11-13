import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import { fmt } from "@/api/helpers";
import { confirmDialog } from "@/components/kit/confirm";
import DataTable from "@/components/kit/DataTable";
import { Avatar, Card, PageHeader, StatusBadge } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";
import { useEmployees } from "@/hooks/useEmployees";
import { PlusIcon, SearchIcon } from "@/icons";
import type { Employee } from "@/types/employee";
import { cn } from "@/utils";

type Row = Employee & { department_name?: string; position_title?: string };

const STATUS_FILTERS = [
  { id: "", label: "All" },
  { id: "ACTIVE", label: "Active" },
  { id: "INACTIVE", label: "Inactive" },
  { id: "ARCHIVED", label: "Archived" },
];

const normalise = (text: string) =>
  text
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");

export default function EmployeeList() {
  const navigate = useNavigate();
  const perms = usePermissions();
  const toast = useToast();
  const { employees, loading, fetchEmployees, archiveEmployee } = useEmployees();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  const rows = employees as Row[];
  const counts = useMemo(() => {
    const result: Record<string, number> = { "": rows.length };
    rows.forEach((e) => (result[e.status] = (result[e.status] || 0) + 1));
    return result;
  }, [rows]);

  const filtered = useMemo(() => {
    const words = normalise(search).split(/\s+/).filter(Boolean);
    return rows.filter((e) => {
      if (status && e.status !== status) return false;
      const text = normalise(
        `${e.surname} ${e.given_names} ${e.matriculation_number || ""} ${e.department_name || ""} ${e.position_title || ""} ${e.professional_email || ""} ${e.phone_number || ""}`,
      );
      return words.every((w) => text.includes(w));
    });
  }, [rows, search, status]);

  const canCreate = perms.can("employees", "create");
  const canModify = perms.can("employees", "modify");

  const archive = async (e: Row) => {
    const ok = await confirmDialog({
      title: `Archive ${e.surname} ${e.given_names}?`,
      message: "The record leaves the active directory but its history is kept. You can still consult it under “Archived”.",
      confirmLabel: "Archive",
      danger: true,
    });
    if (!ok) return;
    try {
      await archiveEmployee(e.id!);
      toast.success("Employee archived");
    } catch {
      toast.error("The employee could not be archived.");
    }
  };

  return (
    <>
      <PageHeader
        title="Employees"
        subtitle="Everyone who works or has worked in the organisation. Click a row to open the full record."
        actions={
          canCreate && (
            <Link to="/employees/new" className="btn-primary">
              <PlusIcon className="size-4" />
              Add an employee
            </Link>
          )
        }
      />

      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter by status">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              role="tab"
              aria-selected={status === f.id}
              onClick={() => setStatus(f.id)}
              className={cn(status === f.id ? "btn-soft ring-1 ring-(--brand)" : "btn-secondary btn-sm")}
            >
              {f.label}
              <span className={cn("text-xs font-medium", status === f.id ? "opacity-70" : "text-muted-c")}>{counts[f.id] || 0}</span>
            </button>
          ))}
        </div>
        <label className="search-box w-full lg:w-80">
          <SearchIcon />
          <input
            type="search"
            className="input-field"
            placeholder="Search a name, number, department…"
            aria-label="Search an employee"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>

      <Card padded={false} className="overflow-hidden">
        <DataTable<Row>
          rows={filtered}
          loading={loading}
          exportTitle="Employees"
          onRowClick={(e) => navigate(`/employees/${e.id}`)}
          empty={
            rows.length === 0
              ? "No employee has been registered yet."
              : "No employee matches your search. Check the spelling or clear the filters."
          }
          columns={[
            {
              key: "surname",
              header: "Employee",
              render: (e) => (
                <div className="flex items-center gap-3">
                  <Avatar name={`${e.surname} ${e.given_names}`} />
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-primary-c">
                      {e.surname} {e.given_names}
                    </p>
                    <p className="truncate text-xs text-muted-c">
                      {[e.matriculation_number, e.position_title].filter(Boolean).join(" · ") || "No position yet"}
                    </p>
                  </div>
                </div>
              ),
            },
            { key: "department_name", header: "Department", render: (e) => <span className="block max-w-44 truncate">{e.department_name || "—"}</span> },
            {
              key: "professional_email",
              header: "Contact",
              render: (e) => (
                <div className="max-w-52 xl:max-w-64">
                  <p className="truncate" title={e.professional_email || e.personal_email || undefined}>{e.professional_email || e.personal_email || "—"}</p>
                  {e.phone_number && <p className="text-xs text-muted-c">{e.phone_number}</p>}
                </div>
              ),
            },
            { key: "date_of_hire", header: "Hired on", render: (e) => (e.date_of_hire ? fmt.date(e.date_of_hire) : "—") },
            { key: "status", header: "Status", render: (e) => <StatusBadge value={e.status} /> },
            {
              key: "__actions",
              header: "",
              align: "end",
              render: (e) => (
                <div className="flex justify-end gap-1" onClick={(event) => event.stopPropagation()}>
                  {canModify ? (
                    <Link to={`/employees/edit/${e.id}`} className="btn-soft">
                      Edit
                    </Link>
                  ) : (
                    <Link to={`/employees/${e.id}`} className="btn-soft">
                      Open
                    </Link>
                  )}
                  {canModify && e.status !== "ARCHIVED" && (
                    <button type="button" className="btn-ghost text-error-600 dark:text-error-400" onClick={() => archive(e)}>
                      Archive
                    </button>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>
    </>
  );
}
