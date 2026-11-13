import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { DownloadButton } from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { PromptModal } from "@/components/kit/Form";
import { useApiItem, useApiList } from "@/components/kit/hooks";
import { employeeField, shiftField } from "@/components/kit/options";
import { Banner, Card, Modal, PageHeader, Spinner, StatusBadge, Tabs } from "@/components/kit/ui";
import { FormGrid } from "@/components/kit/Form";
import { useToast } from "@/context/ToastContext";

interface Cell {
  entry_id: number;
  code: string;
  name: string;
  color: string;
  note: string;
}
interface Grid {
  days: string[];
  rows: { employee_id: number; employee: string; cells: Record<string, Cell[]> }[];
  conflicts: { entry_id: number; messages: string[] }[];
}

const WEEKDAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** BN-62 → BN-67: grid of a timetable (employees × days). */
export default function TimetableEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { data: timetable, reload: reloadTimetable } = useApiItem<any>(`planning/timetables/${id}/`);
  const { data: grid, loading, reload } = useApiItem<Grid>(`planning/timetables/${id}/grid/`);
  const { rows: comparison, reload: reloadComparison } = useApiList<any>(`planning/timetables/${id}/comparison/`);
  const [tab, setTab] = useState("grid");
  const [adding, setAdding] = useState<{ employee?: number; date?: string } | null>(null);
  const [values, setValues] = useState<Record<string, any>>({});
  const [conflict, setConflict] = useState<string | null>(null);
  const [duplicating, setDuplicating] = useState(false);

  const conflictByEntry = useMemo(() => {
    const map: Record<number, string[]> = {};
    grid?.conflicts.forEach((c) => (map[c.entry_id] = c.messages));
    return map;
  }, [grid]);

  if (!timetable || (loading && !grid)) return <Spinner />;
  const draft = timetable.status === "DRAFT";
  const refreshAll = () => {
    reload();
    reloadTimetable();
    reloadComparison();
  };

  const add = async (force = false) => {
    try {
      const res = await api.post(`planning/timetables/${id}/entries/`, { ...values, force });
      if (res.data.warnings?.length) toast.info?.(res.data.warnings.join(" "));
      setAdding(null);
      setConflict(null);
      refreshAll();
    } catch (err: any) {
      if (err.response?.data?.conflict) setConflict(err.response.data.detail);
      else toast.error(apiError(err));
    }
  };

  const remove = async (entryId: number) => {
    try {
      await api.delete(`planning/timetables/${id}/entries/`, { params: { entry: entryId } });
      refreshAll();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  const publish = async () => {
    try {
      await api.post(`planning/timetables/${id}/publish/`);
      toast.success("Timetable published: the employees are notified.");
      refreshAll();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <>
      <PageHeader
        title={timetable.name}
        eyebrow="Planning"
        subtitle={`${timetable.department_name} – ${fmt.date(timetable.start_date)} → ${fmt.date(timetable.end_date)}`}
        actions={
          <>
            <button type="button" className="btn-ghost" onClick={() => navigate("/planning")}>
              ← Timetables
            </button>
            <StatusBadge value={timetable.status} />
            <button type="button" className="btn-primary" onClick={() => { setValues({ date: timetable.start_date }); setAdding({}); }}>
              + Assign
            </button>
            <button type="button" className="btn-secondary" onClick={() => setDuplicating(true)}>
              Duplicate
            </button>
            <DownloadButton url={`planning/timetables/${id}/print_timetable/`} label="Print" />
            {draft && (
              <button type="button" className="btn-teal" onClick={publish}>
                Publish
              </button>
            )}
          </>
        }
      />
      {grid && grid.conflicts.length > 0 && (
        <div className="mb-4">
          <Banner tone="warning">{grid.conflicts.length} assignment(s) with a conflict (leave, rest, weekly maximum): hover the red cells.</Banner>
        </div>
      )}
      <Tabs active={tab} onChange={setTab} tabs={[{ id: "grid", label: "Grid" }, { id: "comparison", label: "Planned vs actual" }]} />
      {tab === "grid" && grid && (
        <Card padded={false}>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="table-header-cell sticky start-0 bg-white dark:bg-gray-900">Employee</th>
                  {grid.days.map((d) => {
                    const day = new Date(d);
                    const weekend = day.getDay() === 0 || day.getDay() === 6;
                    return (
                      <th key={d} className="table-header-cell text-center" style={weekend ? { background: "var(--surface-3)" } : undefined}>
                        {WEEKDAY[day.getDay()]}
                        <br />
                        {d.slice(8, 10)}/{d.slice(5, 7)}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {grid.rows.length === 0 && (
                  <tr>
                    <td colSpan={grid.days.length + 1} className="table-cell py-8 text-center text-muted-c">
                      No assignment yet: click “+ Assign”.
                    </td>
                  </tr>
                )}
                {grid.rows.map((row) => (
                  <tr key={row.employee_id} className="table-row">
                    <td className="table-cell sticky start-0 bg-white font-medium text-primary-c dark:bg-gray-900">{row.employee}</td>
                    {grid.days.map((d) => (
                      <td
                        key={d}
                        className="table-cell cursor-pointer p-1 text-center"
                        onClick={() => {
                          setValues({ employee: row.employee_id, date: d });
                          setAdding({ employee: row.employee_id, date: d });
                        }}
                      >
                        {(row.cells[d] || []).map((cell) => {
                          const issues = conflictByEntry[cell.entry_id];
                          return (
                            <span
                              key={cell.entry_id}
                              title={[cell.name, cell.note, ...(issues || [])].filter(Boolean).join("\n")}
                              className="mb-0.5 inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-semibold text-white"
                              style={{ background: cell.color, outline: issues ? "2px solid var(--danger)" : undefined }}
                              onClick={(e) => e.stopPropagation()}
                            >
                              {cell.code}
                              <button type="button" className="opacity-70 hover:opacity-100" onClick={() => remove(cell.entry_id)} aria-label="Remove">
                                ×
                              </button>
                            </span>
                          );
                        })}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {tab === "comparison" && (
        <Card padded={false} title="Planned vs actual">
          <DataTable exportTitle="Planned vs actual"
            rows={comparison}
            rowKey={(r: any) => r.entry_id}
            columns={[
              { key: "date", header: "Date", render: (r: any) => fmt.date(r.date) },
              { key: "employee", header: "Employee" },
              { key: "shift", header: "Shift" },
              { key: "planned_minutes", header: "Planned", render: (r: any) => fmt.minutes(r.planned_minutes) },
              { key: "worked_minutes", header: "Worked", render: (r: any) => fmt.minutes(r.worked_minutes) },
              { key: "late_minutes", header: "Late", render: (r: any) => fmt.minutes(r.late_minutes) },
              { key: "status", header: "Result", render: (r: any) => <StatusBadge value={r.status} /> },
            ]}
          />
        </Card>
      )}
      <Modal
        open={!!adding}
        title="Assign a shift"
        onClose={() => { setAdding(null); setConflict(null); }}
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setAdding(null)}>Cancel</button>
            {conflict && (
              <button type="button" className="btn-danger" onClick={() => add(true)}>Assign anyway</button>
            )}
            <button type="button" className="btn-primary" onClick={() => add(false)}>Assign</button>
          </>
        }
      >
        <div className="space-y-4">
          {conflict && <Banner tone="warning">{conflict}</Banner>}
          <FormGrid
            fields={[
              { ...employeeField(), optionsUrl: `employees/?department=${timetable.department}`, full: true },
              shiftField(),
              { name: "date", label: "Date", type: "date", required: true },
            ]}
            values={values}
            onChange={(n, v) => setValues((p) => ({ ...p, [n]: v }))}
          />
        </div>
      </Modal>
      <PromptModal
        open={duplicating}
        title="Duplicate the timetable"
        message="The same pattern is copied from the new start date."
        extraFields={[
          { name: "start_date", label: "New start date", type: "date", required: true },
          { name: "name", label: "Name of the copy" },
        ]}
        onClose={() => setDuplicating(false)}
        onConfirm={async (v) => {
          const res = await api.post(`planning/timetables/${id}/duplicate/`, v);
          navigate(`/planning/${res.data.id}`);
        }}
      />
    </>
  );
}
