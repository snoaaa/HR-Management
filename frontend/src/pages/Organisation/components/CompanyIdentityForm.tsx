import React, { useEffect, useRef, useState } from "react";
import { confirmDialog } from "@/components/kit/confirm";
import api from "@/api/axiosConfig";
import { apiError } from "@/api/helpers";
import { Banner, Field, Spinner } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

interface CompanyIdentity {
  id?: number;
  corporate_name: string;
  legal_form: string;
  registration_number: string;
  tax_id: string;
  social_insurance_number: string;
  address: string;
  city: string;
  postal_box: string;
  phone: string;
  email: string;
  website: string;
  legal_representative: string;
  legal_representative_title: string;
  logo?: string | null;
}

const EMPTY: CompanyIdentity = {
  corporate_name: "",
  legal_form: "",
  registration_number: "",
  tax_id: "",
  social_insurance_number: "",
  address: "",
  city: "",
  postal_box: "",
  phone: "",
  email: "",
  website: "",
  legal_representative: "",
  legal_representative_title: "",
};

const MAX_LOGO_MB = 2;

/** BN-01: identity of the organisation, printed on every document with its logo. */
export default function CompanyIdentityForm() {
  const toast = useToast();
  const { can } = usePermissions();
  const editable = can("organisation", "modify");
  const [form, setForm] = useState<CompanyIdentity>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .get("organisation/company-identity/")
      .then((res) => {
        const rows = Array.isArray(res.data) ? res.data : res.data.results || [];
        if (rows.length) setForm({ ...EMPTY, ...rows[0] });
      })
      .catch((err) => toast.error(apiError(err)))
      .finally(() => setLoading(false));
  }, []);

  const change = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const { logo: _logo, ...data } = form;
    try {
      const res = form.id
        ? await api.patch(`organisation/company-identity/${form.id}/`, data)
        : await api.post("organisation/company-identity/", data);
      setForm({ ...EMPTY, ...res.data });
      toast.success("Identity of the organisation saved.");
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setSaving(false);
    }
  };

  const upload = async (file: File | undefined) => {
    if (!file || !form.id) return;
    if (!["image/png", "image/jpeg", "image/gif"].includes(file.type)) return toast.error("Choose a PNG, JPEG or GIF image.");
    if (file.size > MAX_LOGO_MB * 1024 * 1024) return toast.error(`The logo must not exceed ${MAX_LOGO_MB} MB.`);
    const data = new FormData();
    data.append("logo", file);
    setUploading(true);
    try {
      const res = await api.post(`organisation/company-identity/${form.id}/logo/`, data);
      setForm({ ...form, logo: res.data.logo });
      toast.success("Logo uploaded: it now appears on every document.");
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const removeLogo = async () => {
    if (!form.id || !(await confirmDialog({ title: "Remove the logo?", message: "The logo of the organisation will no longer appear on documents.", confirmLabel: "Remove", danger: true }))) return;
    try {
      await api.delete(`organisation/company-identity/${form.id}/logo/`);
      setForm({ ...form, logo: null });
      toast.success("Logo removed.");
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  if (loading) return <Spinner />;

  const input = (name: keyof CompanyIdentity, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <Field label={label}>
      <input className="input-field" name={name} value={(form[name] as string) || ""} onChange={change} disabled={!editable} {...props} />
    </Field>
  );

  return (
    <div className="grid max-w-5xl gap-6 lg:grid-cols-3">
      <div className="space-y-3">
        <p className="section-label">Logo</p>
        <div className="flex h-40 items-center justify-center rounded-lg border bg-white p-4 dark:bg-white/5" style={{ borderColor: "var(--border-color)" }}>
          {form.logo ? <img src={form.logo} alt="Logo of the organisation" className="max-h-32 max-w-full object-contain" /> : <span className="text-sm text-muted-c">No logo yet</span>}
        </div>
        <p className="text-xs text-muted-c">
          Printed at the top of every document: payslips, contracts, certificates, accounting books and every list exported as PDF.
          PNG or JPEG, {MAX_LOGO_MB} MB maximum; a transparent PNG gives the best result.
        </p>
        {editable && (
          form.id ? (
            <div className="flex flex-wrap gap-2">
              <input ref={fileInput} type="file" accept="image/png,image/jpeg,image/gif" className="hidden" onChange={(e) => upload(e.target.files?.[0])} />
              <button type="button" className="btn-primary" disabled={uploading} onClick={() => fileInput.current?.click()}>
                {uploading ? "Uploading…" : form.logo ? "Replace the logo" : "Upload the logo"}
              </button>
              {form.logo && <button type="button" className="btn-ghost text-error-600" onClick={removeLogo}>Remove</button>}
            </div>
          ) : (
            <Banner tone="info">Save the identity first, then upload the logo.</Banner>
          )
        )}
      </div>

      <form onSubmit={save} className="space-y-4 lg:col-span-2">
        <p className="section-label">Legal identity</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">{input("corporate_name", "Corporate name *", { required: true, placeholder: "e.g. Saint Jean Services SA" })}</div>
          {input("legal_form", "Legal form *", { required: true, placeholder: "SA, SARL, SAS, GIE…" })}
          {input("registration_number", "Trade register (RCCM)", { placeholder: "RC/DLA/2015/B/1234" })}
          {input("tax_id", "Taxpayer number (NIU)")}
          {input("social_insurance_number", "CNPS employer number")}
          {input("legal_representative", "Legal representative *", { required: true })}
          {input("legal_representative_title", "Title of the representative", { placeholder: "General Manager" })}
        </div>
        <p className="section-label pt-2">Contact details</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Field label="Head office address *">
              <textarea className="input-field" name="address" required rows={2} value={form.address} onChange={change} disabled={!editable} />
            </Field>
          </div>
          {input("city", "City", { placeholder: "Douala" })}
          {input("postal_box", "P.O. Box")}
          {input("phone", "Telephone", { placeholder: "+237 233 42 00 00" })}
          {input("email", "E-mail", { type: "email" })}
          <div className="sm:col-span-2">{input("website", "Website")}</div>
        </div>
        {editable && (
          <div className="flex justify-end">
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Saving…" : "Save the identity"}</button>
          </div>
        )}
      </form>
    </div>
  );
}
