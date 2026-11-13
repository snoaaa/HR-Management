import { useEffect, useState } from "react";
import axios from "axios";
import { API_URL } from "@/api/baseUrl";
import { apiError, fmt } from "@/api/helpers";
import Logo from "@/components/brand/Logo";
import { Banner, Field, Modal, Spinner } from "@/components/kit/ui";
import PageMeta from "@/components/common/PageMeta";

const API = `${API_URL}recruitment/public/`;

/** Public careers page: published offers and application form (BN-23). */
export default function CareersPage() {
  const [offers, setOffers] = useState<any[] | null>(null);
  const [applying, setApplying] = useState<any>(null);
  const [values, setValues] = useState<Record<string, any>>({});
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}offers/`).then((res) => setOffers(res.data)).catch(() => setOffers([]));
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData();
    Object.entries(values).forEach(([k, v]) => v !== undefined && v !== "" && form.append(k, v as any));
    try {
      const res = await axios.post(`${API}offers/${applying.id}/apply/`, form);
      setDone(res.data.detail);
      setApplying(null);
      setValues({});
    } catch (err) {
      setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };
  const set = (name: string, value: any) => setValues((p) => ({ ...p, [name]: value }));

  return (
    <div className="min-h-screen" style={{ background: "var(--surface-3)" }}>
      <PageMeta title="Careers | Saint Jean HRMS" description="Join our team: open positions." />
      <header className="px-6 py-6 text-white" style={{ background: "var(--odoo-purple)" }}>
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Logo tone="inverse" size={44} />
          <span className="text-sm opacity-80">Careers</span>
        </div>
        <div className="mx-auto mt-8 max-w-5xl">
          <h1 className="text-3xl font-bold">Join our team</h1>
          <p className="mt-2 opacity-80">Discover our open positions and apply online.</p>
        </div>
      </header>
      <main className="mx-auto max-w-5xl space-y-4 px-6 py-8">
        {done && <Banner tone="success">{done}</Banner>}
        {offers === null ? <Spinner /> : offers.length === 0 ? (
          <p className="card p-8 text-center text-secondary-c">No open position at the moment.</p>
        ) : offers.map((offer) => (
          <article key={offer.id} className="card p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-primary-c">{offer.title}</h2>
                <p className="text-sm text-secondary-c">
                  {offer.department_name}{offer.location_name ? ` · ${offer.location_name}` : ""} · {offer.contract_type_label}
                  {offer.closing_date ? ` · until ${fmt.date(offer.closing_date)}` : ""}
                </p>
              </div>
              <button type="button" className="btn-primary" onClick={() => { setApplying(offer); setDone(null); }}>Apply</button>
            </div>
            <p className="mt-3 whitespace-pre-line text-sm text-secondary-c">{offer.description}</p>
            {offer.requirements && <p className="mt-2 whitespace-pre-line text-sm text-secondary-c"><b>Requirements:</b> {offer.requirements}</p>}
          </article>
        ))}
      </main>
      <Modal open={!!applying} title={`Apply – ${applying?.title}`} onClose={() => setApplying(null)} size="lg"
        footer={<button type="submit" form="apply-form" className="btn-primary" disabled={busy}>{busy ? "Sending…" : "Send my application"}</button>}>
        <form id="apply-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          {error && <div className="sm:col-span-2"><Banner tone="error">{error}</Banner></div>}
          <Field label="Surname" required><input className="input-field" required onChange={(e) => set("surname", e.target.value)} /></Field>
          <Field label="Given names" required><input className="input-field" required onChange={(e) => set("given_names", e.target.value)} /></Field>
          <Field label="E-mail" required><input type="email" className="input-field" required onChange={(e) => set("email", e.target.value)} /></Field>
          <Field label="Telephone" required><input className="input-field" required onChange={(e) => set("phone", e.target.value)} /></Field>
          <Field label="Date of birth"><input type="date" className="input-field" onChange={(e) => set("date_of_birth", e.target.value)} /></Field>
          <Field label="Place of birth"><input className="input-field" onChange={(e) => set("place_of_birth", e.target.value)} /></Field>
          <Field label="Sex">
            <select className="input-field" onChange={(e) => set("sex", e.target.value)} defaultValue="">
              <option value="">—</option><option value="M">Male</option><option value="F">Female</option>
            </select>
          </Field>
          <Field label="Nationality"><input className="input-field" onChange={(e) => set("nationality", e.target.value)} /></Field>
          <Field label="Address" className="sm:col-span-2"><input className="input-field" onChange={(e) => set("address", e.target.value)} /></Field>
          <Field label="CV (PDF, Word, 5 MB max)"><input type="file" accept=".pdf,.doc,.docx,.odt" className="input-field" onChange={(e) => set("cv", e.target.files?.[0])} /></Field>
          <Field label="Cover letter"><input type="file" accept=".pdf,.doc,.docx,.odt" className="input-field" onChange={(e) => set("cover_letter", e.target.files?.[0])} /></Field>
          <Field label="Motivation" className="sm:col-span-2"><textarea className="input-field" rows={4} onChange={(e) => set("motivation", e.target.value)} /></Field>
        </form>
      </Modal>
    </div>
  );
}
