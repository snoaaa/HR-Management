import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import api from "@/api/axiosConfig";
import { apiError } from "@/api/helpers";
import { useToast } from "@/context/ToastContext";
import { cn } from "@/utils";
import { useOptions } from "./hooks";
import type { Option } from "./hooks";
import { Field, Modal } from "./ui";

export type FieldType =
  | "text"
  | "number"
  | "date"
  | "time"
  | "textarea"
  | "select"
  | "checkbox"
  | "json"
  | "color"
  | "file"
  | "password"
  | "email";

export interface FieldDef {
  name: string;
  label: string;
  type?: FieldType;
  required?: boolean;
  options?: Option[];
  /** Load the options of a select from an endpoint. */
  optionsUrl?: string;
  optionLabel?: (row: any) => string;
  optionValue?: (row: any) => any;
  step?: string;
  hint?: ReactNode;
  placeholder?: string;
  full?: boolean;
  rows?: number;
  hidden?: (values: Record<string, any>) => boolean;
  readOnly?: boolean;
}

function SelectInput({ field, value, onChange }: { field: FieldDef; value: any; onChange: (v: any) => void }) {
  const loaded = useOptions(field.optionsUrl, field.optionLabel || ((r) => r.name || r.title || r.full_name || String(r.id)), field.optionValue);
  const options = field.options || loaded;
  return (
    <select
      className="input-field"
      value={value ?? ""}
      required={field.required}
      disabled={field.readOnly}
      onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
    >
      <option value="">{field.placeholder || "— Select —"}</option>
      {options.map((o) => (
        <option key={String(o.value)} value={String(o.value)}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export function FieldInput({ field, value, onChange }: { field: FieldDef; value: any; onChange: (v: any) => void }) {
  const type = field.type || "text";
  if (type === "select") return <SelectInput field={field} value={value} onChange={onChange} />;
  if (type === "checkbox")
    return (
      <span className="flex items-center gap-2 pt-1">
        <input type="checkbox" className="h-4 w-4 accent-brand-500" checked={!!value} disabled={field.readOnly} onChange={(e) => onChange(e.target.checked)} />
        <span className="text-sm text-secondary-c">{field.placeholder || "Yes"}</span>
      </span>
    );
  if (type === "textarea" || type === "json")
    return (
      <textarea
        className={cn("input-field", type === "json" && "mono text-xs")}
        rows={field.rows || (type === "json" ? 6 : 3)}
        required={field.required}
        placeholder={field.placeholder}
        readOnly={field.readOnly}
        value={type === "json" && typeof value !== "string" ? JSON.stringify(value ?? [], null, 2) : value ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  if (type === "file")
    return <input type="file" className="input-field" onChange={(e) => onChange(e.target.files?.[0] || null)} />;
  return (
    <input
      type={type}
      className={cn("input-field", type === "color" && "h-10 p-1")}
      step={field.step}
      required={field.required}
      placeholder={field.placeholder}
      readOnly={field.readOnly}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function FormGrid({ fields, values, onChange }: { fields: FieldDef[]; values: Record<string, any>; onChange: (name: string, v: any) => void }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {fields
        .filter((f) => !f.hidden?.(values))
        .map((f) => (
          <Field
            key={f.name}
            label={f.label}
            hint={f.hint}
            required={f.required}
            className={f.full || f.type === "textarea" || f.type === "json" ? "sm:col-span-2" : ""}
          >
            <FieldInput field={f} value={values[f.name]} onChange={(v) => onChange(f.name, v)} />
          </Field>
        ))}
    </div>
  );
}

/** Convert form values to the payload expected by the API. */
export function toPayload(fields: FieldDef[], values: Record<string, any>) {
  const hasFile = fields.some((f) => f.type === "file" && values[f.name] instanceof File);
  const out: Record<string, any> = {};
  for (const f of fields) {
    if (f.readOnly || f.hidden?.(values)) continue;
    let v = values[f.name];
    if (f.type === "json" && typeof v === "string") {
      try {
        v = JSON.parse(v || "null");
      } catch {
        throw new Error(`${f.label}: invalid JSON.`);
      }
    }
    if (f.type === "number" && (v === "" || v === undefined)) v = null;
    if ((f.type === "date" || f.type === "time" || f.type === "select") && v === "") v = null;
    if (f.type === "file" && !(v instanceof File)) continue;
    out[f.name] = v;
  }
  if (!hasFile) return out;
  const form = new FormData();
  Object.entries(out).forEach(([k, v]) => {
    if (v === null || v === undefined) return;
    form.append(k, v instanceof File ? v : typeof v === "object" ? JSON.stringify(v) : String(v));
  });
  return form;
}

interface FormModalProps {
  open: boolean;
  title: string;
  fields: FieldDef[];
  initial?: Record<string, any>;
  onClose: () => void;
  /** Endpoint for POST (create) or PATCH (when `id` is set). */
  endpoint?: string;
  id?: string | number | null;
  method?: "post" | "patch" | "put";
  onSubmit?: (payload: any, values: Record<string, any>) => Promise<unknown>;
  onSaved?: (data: any) => void;
  submitLabel?: string;
  size?: "sm" | "md" | "lg" | "xl";
  intro?: ReactNode;
}

export function FormModal({
  open,
  title,
  fields,
  initial,
  onClose,
  endpoint,
  id,
  method,
  onSubmit,
  onSaved,
  submitLabel = "Save",
  size = "md",
  intro,
}: FormModalProps) {
  const [values, setValues] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    if (open) {
      const start: Record<string, any> = {};
      fields.forEach((f) => {
        start[f.name] = initial?.[f.name] ?? (f.type === "checkbox" ? false : "");
      });
      setValues(start);
      setError(null);
    }
  }, [open]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = toPayload(fields, values);
      let data: any;
      if (onSubmit) {
        data = await onSubmit(payload, values);
      } else if (endpoint) {
        const verb = method || (id ? "patch" : "post");
        const url = id ? `${endpoint}${id}/` : endpoint;
        data = (await api.request({ url, method: verb, data: payload })).data;
      }
      toast.success("Saved");
      onSaved?.(data);
      onClose();
    } catch (err: any) {
      setError(err instanceof Error && !err.hasOwnProperty("response") ? err.message : apiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title={title}
      onClose={onClose}
      size={size}
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form="kit-form" className="btn-primary" disabled={saving}>
            {saving ? "Saving…" : submitLabel}
          </button>
        </>
      }
    >
      <form id="kit-form" onSubmit={submit} className="space-y-4">
        {intro}
        {error && <div className="error-banner">{error}</div>}
        <FormGrid fields={fields} values={values} onChange={(name, v) => setValues((prev) => ({ ...prev, [name]: v }))} />
      </form>
    </Modal>
  );
}

/** Ask a confirmation, optionally with a mandatory comment. */
export function PromptModal({
  open,
  title,
  message,
  onClose,
  onConfirm,
  confirmLabel = "Confirm",
  danger,
  commentLabel,
  commentRequired,
  extraFields,
}: {
  open: boolean;
  title: string;
  message?: ReactNode;
  onClose: () => void;
  onConfirm: (values: Record<string, any>) => Promise<unknown> | void;
  confirmLabel?: string;
  danger?: boolean;
  commentLabel?: string;
  commentRequired?: boolean;
  extraFields?: FieldDef[];
}) {
  const [values, setValues] = useState<Record<string, any>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (open) {
      setValues({});
      setError(null);
    }
  }, [open]);
  const confirm = async () => {
    if (commentRequired && !values.comment) {
      setError(`${commentLabel || "A comment"} is required.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onConfirm(values);
      onClose();
    } catch (err: any) {
      setError(err?.response ? apiError(err) : err?.message || "Error");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal
      open={open}
      title={title}
      onClose={onClose}
      size="sm"
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className={danger ? "btn-danger" : "btn-primary"} disabled={busy} onClick={confirm}>
            {busy ? "Please wait…" : confirmLabel}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {message && <div className="text-sm text-secondary-c">{message}</div>}
        {error && <div className="error-banner">{error}</div>}
        {extraFields && (
          <FormGrid fields={extraFields} values={values} onChange={(n, v) => setValues((p) => ({ ...p, [n]: v }))} />
        )}
        {commentLabel && (
          <Field label={commentLabel} required={commentRequired}>
            <textarea className="input-field" rows={3} value={values.comment || ""} onChange={(e) => setValues((p) => ({ ...p, comment: e.target.value }))} />
          </Field>
        )}
      </div>
    </Modal>
  );
}
