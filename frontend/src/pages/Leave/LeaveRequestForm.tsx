import { useEffect, useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { useOptions } from "@/components/kit/hooks";
import { employeeField } from "@/components/kit/options";
import { Banner, Field, Modal } from "@/components/kit/ui";
import { FieldInput } from "@/components/kit/Form";
import { useToast } from "@/context/ToastContext";

interface Preview {
  days: string;
  balance: { available: string; acquired: string; taken: string; pending: string };
  sufficient: boolean;
  overlap_warning: string;
}

/** BN-50: leave request with automatic control of the balance. */
export default function LeaveRequestForm({
  open,
  onClose,
  onSaved,
  forEmployee = false,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  forEmployee?: boolean;
}) {
  const types = useOptions("leave/types/", (t) => t.name);
  const [values, setValues] = useState<Record<string, any>>({});
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setValues({});
      setPreview(null);
      setError(null);
    }
  }, [open]);

  useEffect(() => {
    const { leave_type, start_date, end_date, employee } = values;
    if (!leave_type || !start_date || !end_date) {
      setPreview(null);
      return;
    }
    const timer = window.setTimeout(async () => {
      try {
        const res = await api.post("leave/requests/preview/", { leave_type, start_date, end_date, ...(employee ? { employee } : {}) });
        setPreview(res.data);
        setError(null);
      } catch (err) {
        setPreview(null);
        setError(apiError(err));
      }
    }, 300);
    return () => window.clearTimeout(timer);
  }, [values.leave_type, values.start_date, values.end_date, values.employee]);

  const set = (name: string, v: any) => setValues((p) => ({ ...p, [name]: v }));

  const submit = async (send: boolean) => {
    setBusy(true);
    setError(null);
    try {
      const hasFile = values.document instanceof File;
      const payload: Record<string, any> = {
        leave_type: values.leave_type,
        start_date: values.start_date,
        end_date: values.end_date,
        reason: values.reason || "",
        submit: send,
      };
      if (values.replacement) payload.replacement = values.replacement;
      if (values.employee) payload.employee = values.employee;
      let body: any = payload;
      if (hasFile) {
        body = new FormData();
        Object.entries(payload).forEach(([k, v]) => body.append(k, String(v)));
        body.append("document", values.document);
      }
      await api.post("leave/requests/", body);
      toast.success(send ? "Request sent for approval" : "Draft saved");
      onSaved();
      onClose();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      title="New leave request"
      onClose={onClose}
      size="lg"
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="btn-secondary" disabled={busy} onClick={() => submit(false)}>
            Save as draft
          </button>
          <button type="button" className="btn-primary" disabled={busy || (preview !== null && !preview.sufficient)} onClick={() => submit(true)}>
            Submit for approval
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <Banner tone="error">{error}</Banner>}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {forEmployee && (
            <Field label="Employee" required className="sm:col-span-2">
              <FieldInput field={employeeField()} value={values.employee} onChange={(v) => set("employee", v)} />
            </Field>
          )}
          <Field label="Type of leave" required className="sm:col-span-2">
            <select className="input-field" value={values.leave_type || ""} onChange={(e) => set("leave_type", e.target.value)}>
              <option value="">— Select —</option>
              {types.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="First day" required>
            <input type="date" className="input-field" value={values.start_date || ""} onChange={(e) => set("start_date", e.target.value)} />
          </Field>
          <Field label="Last day" required>
            <input type="date" className="input-field" value={values.end_date || ""} onChange={(e) => set("end_date", e.target.value)} />
          </Field>
          <Field label="Replaced by" className="sm:col-span-2">
            <FieldInput field={employeeField("replacement", "Replacement", false)} value={values.replacement} onChange={(v) => set("replacement", v)} />
          </Field>
          <Field label="Reason" className="sm:col-span-2">
            <textarea className="input-field" rows={2} value={values.reason || ""} onChange={(e) => set("reason", e.target.value)} />
          </Field>
          <Field label="Supporting document" hint="Required for some types (sick leave, maternity…)." className="sm:col-span-2">
            <input type="file" className="input-field" onChange={(e) => set("document", e.target.files?.[0] || null)} />
          </Field>
        </div>
        {preview && (
          <div className="grid grid-cols-3 gap-3 rounded-xl p-4" style={{ background: "var(--surface-3)" }}>
            <div>
              <p className="section-label">Days counted</p>
              <p className="kpi-value text-xl">{fmt.number(preview.days)}</p>
              <p className="text-[11px] text-muted-c">rest days & holidays excluded</p>
            </div>
            <div>
              <p className="section-label">Available</p>
              <p className="kpi-value text-xl">{fmt.number(preview.balance.available)}</p>
            </div>
            <div>
              <p className="section-label">Balance check</p>
              <p className="mt-1">{preview.sufficient ? <span className="badge-green">Sufficient</span> : <span className="badge-red">Insufficient</span>}</p>
            </div>
          </div>
        )}
        {preview?.overlap_warning && <Banner tone="warning">Team coverage: {preview.overlap_warning}</Banner>}
      </div>
    </Modal>
  );
}
