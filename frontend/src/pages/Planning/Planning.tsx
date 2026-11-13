import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, downloadFile, fmt } from "@/api/helpers";
import CrudSection from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { FormModal, PromptModal } from "@/components/kit/Form";
import { useApiList, useHashTab, useOptions } from "@/components/kit/hooks";
import { departmentField } from "@/components/kit/options";
import { Banner, Card, Modal, PageHeader, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

interface Timetable {
  id: number;
  name: string;
  department: number;
  department_name: string;
  start_date: string;
  end_date: string;
  status: "DRAFT" | "PUBLISHED";
  entries_count: number;
  published_at?: string;
}

function TimetablesList() {
  const { rows, loading, reload } = useApiList<Timetable>("planning/timetables/");
  const [creating, setCreating] = useState(false);
  const [gridTarget, setGridTarget] = useState<Timetable | null>(null);
  const [duplicating, setDuplicating] = useState<Timetable | null>(null);
  const { can } = usePermissions();
  const toast = useToast();

  const publish = async (t: Timetable) => {
    try {
      await api.post(`planning/timetables/${t.id}/publish/`);
      toast.success(`Timetable ${t.name} published`);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  const printPdf = async (t: Timetable) => {
    try {
      await downloadFile(`planning/timetables/${t.id}/print_timetable/`, { filename: `${t.name}.pdf` });
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <>
      <Card
        padded={false}
        title="Timetables (BN-62)"
        actions={
          can("planning", "modify") && (
            <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
              + New timetable
            </button>
          )
        }
      >
        <DataTable<Timetable>
          rows={rows}
          loading={loading}
          empty="No timetable created yet."
          columns={[
            {
              key: "name",
              header: "Name",
              render: (t) => (
                <button type="button" onClick={() => setGridTarget(t)} className="text-left font-medium text-brand-500 hover:underline dark:text-brand-300">
                  {t.name}
                </button>
              ),
            },
            { key: "department_name", header: "Department" },
            { key: "start_date", header: "Period", render: (t) => `${fmt.date(t.start_date)} → ${fmt.date(t.end_date)}` },
            { key: "entries_count", header: "Assigned shifts", align: "end", mono: true },
            { key: "status", header: "Status", render: (t) => <StatusBadge value={t.status} /> },
            {
              key: "actions",
              header: "",
              align: "end",
              render: (t) => (
                <div className="flex items-center justify-end gap-1.5">
                  <button type="button" className="btn-ghost text-xs" onClick={() => setGridTarget(t)}>
                    Grid / Plan
                  </button>
                  <button type="button" className="btn-ghost text-xs" onClick={() => printPdf(t)}>
                    PDF
                  </button>
                  {t.status === "DRAFT" && can("planning", "validate") && (
                    <button type="button" className="btn-ghost text-xs text-green-600 hover:bg-green-50" onClick={() => publish(t)}>
                      Publish
                    </button>
                  )}
                  {can("planning", "modify") && (
                    <button type="button" className="btn-ghost text-xs" onClick={() => setDuplicating(t)}>
                      Duplicate
                    </button>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>

      <FormModal
        open={creating}
        title="Create timetable"
        endpoint="planning/timetables/"
        onClose={() => setCreating(false)}
        onSaved={reload}
        fields={[
          departmentField(),
          { name: "name", label: "Timetable title", required: true, placeholder: "e.g. Schedule Week 46" },
          { name: "start_date", label: "Start date", type: "date", required: true },
          { name: "end_date", label: "End date", type: "date", required: true },
        ]}
      />

      <PromptModal
        open={!!duplicating}
        title={`Duplicate ${duplicating?.name || ""}`}
        message="Choose a new start date for the duplicated timetable:"
        extraFields={[{ name: "start_date", label: "New start date", type: "date", required: true }]}
        confirmLabel="Duplicate"
        onClose={() => setDuplicating(null)}
        onConfirm={async (vals) => {
          if (!duplicating) return;
          try {
            await api.post(`planning/timetables/${duplicating.id}/duplicate/`, { start_date: vals.start_date });
            toast.success("Timetable duplicated");
            reload();
          } catch (err) {
            toast.error(apiError(err));
          }
        }}
      />

      {gridTarget && (
        <TimetableGridModal timetable={gridTarget} onClose={() => setGridTarget(null)} onUpdated={reload} />
      )}
    </>
  );
}

function TimetableGridModal({ timetable, onClose, onUpdated }: { timetable: Timetable; onClose: () => void; onUpdated: () => void }) {
  const [gridData, setGridData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [assigning, setAssigning] = useState<{ employeeId: number; day: string } | null>(null);
  const shifts = useOptions("planning/shifts/", (s) => `${s.code} – ${s.name} (${s.start_time.slice(0, 5)}-${s.end_time.slice(0, 5)})`);
  const toast = useToast();
  const { can } = usePermissions();

  const loadGrid = () => {
    setLoading(true);
    api
      .get(`planning/timetables/${timetable.id}/grid/`)
      .then((res) => {
        setGridData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        toast.error(apiError(err));
        setLoading(false);
      });
  };

  useState(() => {
    loadGrid();
  });

  const removeEntry = async (entryId: number) => {
    try {
      await api.delete(`planning/timetables/${timetable.id}/entries/?entry=${entryId}`);
      toast.success("Shift removed");
      loadGrid();
      onUpdated();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  const addShift = async (shiftId: string, force = false) => {
    if (!assigning) return;
    try {
      await api.post(`planning/timetables/${timetable.id}/entries/`, {
        employee: assigning.employeeId,
        shift: Number(shiftId),
        date: assigning.day,
        force,
      });
      toast.success("Shift assigned");
      setAssigning(null);
      loadGrid();
      onUpdated();
    } catch (err: any) {
      const data = err?.response?.data;
      if (data?.conflict && confirm(`${data.detail}\nDo you want to override and assign anyway?`)) {
        addShift(shiftId, true);
        return;
      }
      toast.error(apiError(err));
    }
  };

  return (
    <Modal open={true} onClose={onClose} title={`${timetable.name} (${timetable.department_name})`} size="xl">
      {loading ? (
        <div className="p-8 text-center text-muted-c">Loading planning grid...</div>
      ) : !gridData ? (
        <div className="p-8 text-center text-red-500">Could not load timetable grid.</div>
      ) : (
        <div className="space-y-4">
          {gridData.conflicts && gridData.conflicts.length > 0 && (
            <Banner tone="error">
              <span className="font-semibold block mb-1">{gridData.conflicts.length} conflict(s) detected:</span>
              <ul className="list-inside list-disc text-xs">
                {gridData.conflicts.slice(0, 5).map((c: any, i: number) => (
                  <li key={i}>{c.message || c.detail || JSON.stringify(c)}</li>
                ))}
              </ul>
            </Banner>
          )}

          <div className="overflow-x-auto rounded border" style={{ borderColor: "var(--border-color)" }}>
            <table className="min-w-full divide-y text-xs" style={{ borderColor: "var(--border-color)" }}>
              <thead className="bg-surface-alt">
                <tr>
                  <th className="p-2 text-left font-semibold">Employee</th>
                  {gridData.days?.map((d: string) => (
                    <th key={d} className="p-2 text-center font-semibold">
                      {d.slice(5)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: "var(--border-color)" }}>
                {gridData.rows?.map((row: any) => (
                  <tr key={row.employee_id || row.employee}>
                    <td className="whitespace-nowrap p-2 font-medium">
                      {row.employee}
                      <span className="block text-[10px] text-muted-c">ID: {row.employee_id}</span>
                    </td>
                    {gridData.days?.map((day: string) => {
                      const cellEntries: any[] = row.cells?.[day] || [];
                      return (
                        <td key={day} className="p-1 text-center align-top border-r border-slate-100 dark:border-slate-800">
                          <div className="flex flex-col gap-1 min-h-[38px] justify-center items-center">
                            {cellEntries.map((entry: any) => (
                              <span
                                key={entry.entry_id}
                                className="group relative inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-semibold text-white shadow-xs"
                                style={{ backgroundColor: entry.color || "#4F46E5" }}
                                title={`${entry.name} (${entry.code})`}
                              >
                                {entry.code}
                                {can("planning", "modify") && timetable.status === "DRAFT" && (
                                  <button
                                    type="button"
                                    onClick={() => removeEntry(entry.entry_id)}
                                    className="ml-0.5 opacity-60 hover:opacity-100"
                                  >
                                    ×
                                  </button>
                                )}
                              </span>
                            ))}
                            {can("planning", "modify") && timetable.status === "DRAFT" && (
                              <button
                                type="button"
                                onClick={() => setAssigning({ employeeId: row.employee_id, day })}
                                className="text-muted-c opacity-40 hover:opacity-100 text-sm hover:text-brand-500"
                              >
                                +
                              </button>
                            )}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex justify-between items-center pt-2">
            <span className="text-xs text-muted-c">Status: <StatusBadge value={timetable.status} /></span>
            <button type="button" className="btn-secondary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      )}

      {assigning && (
        <Modal open={true} onClose={() => setAssigning(null)} title={`Assign shift for ${assigning.day}`}>
          <div className="space-y-4">
            <p className="text-sm text-muted-c">Choose a shift code to schedule:</p>
            <div className="grid grid-cols-1 gap-2">
              {shifts.map((s) => (
                <button
                  key={s.value}
                  type="button"
                  className="btn-secondary text-left flex justify-between items-center py-2 px-3"
                  onClick={() => addShift(String(s.value))}
                >
                  <span>{s.label}</span>
                  <span className="text-xs font-semibold text-brand-500">Select →</span>
                </button>
              ))}
            </div>
            <div className="flex justify-end pt-2">
              <button type="button" className="btn-ghost" onClick={() => setAssigning(null)}>
                Cancel
              </button>
            </div>
          </div>
        </Modal>
      )}
    </Modal>
  );
}

function ShiftsCatalogue() {
  return (
    <CrudSection
      endpoint="planning/shifts/"
      title="Shifts catalogue (BN-59)"
      modalSize="md"
      columns={[
        {
          key: "name",
          header: "Shift",
          render: (s: any) => (
            <span className="flex items-center gap-2">
              <span className="h-3 w-3 rounded" style={{ background: s.color }} />
              <span className="font-medium text-primary-c">{s.name}</span>
              <span className="mono text-[11px] text-muted-c">{s.code}</span>
            </span>
          ),
        },
        { key: "start_time", header: "Hours", render: (s: any) => `${s.start_time?.slice(0, 5)} → ${s.end_time?.slice(0, 5)}` },
        { key: "break_minutes", header: "Break", align: "end", mono: true, render: (s: any) => `${s.break_minutes || 0} min` },
        { key: "is_active", header: "Active", render: (s: any) => (s.is_active ? "yes" : "no") },
      ]}
      fields={[
        { name: "code", label: "Code", required: true, placeholder: "e.g. MORNING" },
        { name: "name", label: "Shift name", required: true, placeholder: "e.g. Morning Shift" },
        { name: "start_time", label: "Start time", type: "time", required: true },
        { name: "end_time", label: "End time", type: "time", required: true },
        { name: "break_minutes", label: "Break (minutes)", type: "number" },
        { name: "color", label: "Color", type: "color" },
        { name: "is_active", label: "Active", type: "checkbox" },
      ]}
    />
  );
}

function ShiftSwaps() {
  const { rows, loading, reload } = useApiList<any>("planning/swaps/");
  const toast = useToast();

  const decide = async (swapId: number, approved: boolean) => {
    try {
      await api.post(`planning/swaps/${swapId}/${approved ? "approve" : "refuse"}/`);
      toast.success(approved ? "Exchange approved" : "Exchange refused");
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <Card padded={false} title="Shift exchange requests (BN-65)">
      <DataTable
        rows={rows}
        loading={loading}
        empty="No exchange request."
        columns={[
          { key: "employee_name", header: "Applicant", render: (s: any) => s.entry_detail?.employee_name || "Employee" },
          { key: "replacement_name", header: "Replacement" },
          { key: "date", header: "Date", render: (s: any) => fmt.date(s.entry_detail?.date) },
          { key: "shift", header: "Shift", render: (s: any) => <span className="font-semibold">{s.entry_detail?.shift_name}</span> },
          { key: "reason", header: "Reason" },
          { key: "status", header: "Status", render: (s: any) => <StatusBadge value={s.status} /> },
          {
            key: "actions",
            header: "",
            align: "end",
            render: (s: any) =>
              s.status === "PENDING" && (
                <div className="flex justify-end gap-1">
                  <button type="button" className="btn-ghost text-xs text-green-600" onClick={() => decide(s.id, true)}>
                    Approve
                  </button>
                  <button type="button" className="btn-ghost text-xs text-red-600" onClick={() => decide(s.id, false)}>
                    Refuse
                  </button>
                </div>
              ),
          },
        ]}
      />
    </Card>
  );
}

export default function Planning() {
  const [tab, setTab] = useHashTab("timetables");
  return (
    <>
      <PageHeader eyebrow="Time & planning" title="Work Planning (M-07)" subtitle="Timetables, rotating shifts, and duty roster planning." />
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "timetables", label: "Timetables (BN-62)" },
          { id: "shifts", label: "Shifts catalogue (BN-59)" },
          { id: "swaps", label: "Exchanges (BN-65)" },
        ]}
      />
      {tab === "timetables" && <TimetablesList />}
      {tab === "shifts" && <ShiftsCatalogue />}
      {tab === "swaps" && <ShiftSwaps />}
    </>
  );
}

