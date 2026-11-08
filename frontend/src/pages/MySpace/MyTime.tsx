import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, fmt, todayISO } from "@/api/helpers";
import DataTable from "@/components/kit/DataTable";
import { useApiList, useOptions } from "@/components/kit/hooks";
import { Card, PageHeader } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

export default function MyTime() {
  const { employee_id } = usePermissions();
  const [swapping, setSwapping] = useState<any>(null);
  const [reason, setReason] = useState("");
  const [replacementId, setReplacementId] = useState("");
  const toast = useToast();

  const colleagues = useOptions(
    "employees/",
    (e) => `${e.full_name || `${e.surname} ${e.given_names}`} (${e.department_name || ""})`,
    (e) => String(e.id) !== String(employee_id)
  );

  const { rows: entries, loading: loadingEntries, reload: reloadEntries } = useApiList<any>(
    employee_id ? `planning/entries/?employee=${employee_id}&date__gte=${todayISO()}` : null
  );

  const { rows: clockings, loading: loadingClockings } = useApiList<any>(
    employee_id ? `attendance/clockings/?employee=${employee_id}` : null
  );

  const submitSwap = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!swapping || !replacementId) return;
    try {
      await api.post("planning/swaps/", {
        entry: swapping.id,
        replacement: Number(replacementId),
        reason,
      });
      toast.success("Shift exchange request submitted to manager");
      setSwapping(null);
      setReason("");
      setReplacementId("");
      reloadEntries();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="My Space"
        title="My Timetable & Shifts (BN-151)"
        subtitle="Consult your upcoming shift roster, clocking history, and request peer shift exchanges."
      />

      <div className="space-y-6">
        <Card padded={false} title="Upcoming planned shifts">
          <DataTable
            rows={entries}
            loading={loadingEntries}
            empty="No upcoming shifts assigned."
            columns={[
              { key: "date", header: "Date", render: (e: any) => fmt.date(e.date) },
              {
                key: "shift",
                header: "Shift",
                render: (e: any) => (
                  <span
                    className="inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold text-white"
                    style={{ backgroundColor: e.shift_color || "#00A09D" }}
                  >
                    {e.shift_name}
                  </span>
                ),
              },
              { key: "hours", header: "Working hours", render: (e: any) => `${e.start_time?.slice(0, 5)} → ${e.end_time?.slice(0, 5)}` },
              { key: "timetable", header: "Timetable", render: (e: any) => e.timetable_name },
              {
                key: "actions",
                header: "",
                align: "end",
                render: (e: any) => (
                  <button type="button" className="btn-ghost text-xs" onClick={() => setSwapping(e)}>
                    Request exchange (BN-65)
                  </button>
                ),
              },
            ]}
          />
        </Card>

        <Card padded={false} title="Recent clockings (IN / OUT)">
          <DataTable
            rows={clockings}
            loading={loadingClockings}
            empty="No clockings recorded recently."
            columns={[
              { key: "timestamp", header: "Date & Time", render: (c: any) => fmt.datetime(c.timestamp) },
              {
                key: "direction",
                header: "Direction",
                render: (c: any) => (
                  <span className={c.direction === "IN" ? "badge-green" : "badge-amber"}>
                    {c.direction === "IN" ? "Entry (IN)" : "Exit (OUT)"}
                  </span>
                ),
              },
              { key: "source", header: "Method", render: (c: any) => c.source || "SELF" },
              { key: "comment", header: "Note" },
            ]}
          />
        </Card>
      </div>

      {swapping && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-surface p-6 shadow-xl border" style={{ borderColor: "var(--border-color)" }}>
            <h3 className="text-lg font-bold">Request shift exchange</h3>
            <p className="text-xs text-muted-c mt-1">
              Shift on {fmt.date(swapping.date)} ({swapping.shift_name})
            </p>
            <form onSubmit={submitSwap} className="space-y-4 mt-4">
              <label>
                <span className="field-label">Substitute colleague</span>
                <select className="input-field" value={replacementId} onChange={(e) => setReplacementId(e.target.value)} required>
                  <option value="">Select colleague...</option>
                  {colleagues.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <span className="field-label">Reason</span>
                <textarea
                  className="input-field"
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="e.g. Personal emergency, mutually agreed exchange"
                  required
                />
              </label>

              <div className="flex justify-end gap-2 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setSwapping(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Submit request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

