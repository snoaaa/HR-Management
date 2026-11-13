import { useState } from "react";
import { useNavigate } from "react-router";
import api from "@/api/axiosConfig";
import { apiError, fmt, todayISO } from "@/api/helpers";
import CrudSection from "@/components/kit/CrudSection";
import { PromptModal } from "@/components/kit/Form";
import { useApiList, useHashTab } from "@/components/kit/hooks";
import { CONTRACT_TYPES, departmentField, offerField, positionField, siteField, userField } from "@/components/kit/options";
import SearchSelect from "@/components/kit/SearchSelect";
import { Badge, DefinitionList, Modal, PageHeader, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

const STAGES = [
  ["RECEIVED", "Received"],
  ["PRESELECTED", "Pre-selected"],
  ["INTERVIEW", "Interview"],
  ["TEST", "Test"],
  ["SELECTED", "Selected"],
  ["REJECTED", "Rejected"],
  ["HIRED", "Hired"],
];
const NEXT: Record<string, string[]> = {
  RECEIVED: ["PRESELECTED", "REJECTED"],
  PRESELECTED: ["INTERVIEW", "TEST", "REJECTED"],
  INTERVIEW: ["TEST", "SELECTED", "REJECTED"],
  TEST: ["INTERVIEW", "SELECTED", "REJECTED"],
  SELECTED: ["REJECTED"],
  REJECTED: ["RECEIVED"],
  HIRED: [],
};

function Pipeline() {
  const toast = useToast();
  const navigate = useNavigate();
  const { can } = usePermissions();
  const [offer, setOffer] = useState<number | null>(null);
  const { rows, reload } = useApiList<any>("recruitment/applications/", offer ? { offer } : undefined);
  const [open, setOpen] = useState<any>(null);
  const [hiring, setHiring] = useState<any>(null);
  const [score, setScore] = useState("");
  const move = async (app: any, stage: string, score?: string) => {
    try {
      const res = await api.post(`recruitment/applications/${app.id}/move/`, { stage, score });
      setOpen(res.data);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <SearchSelect className="w-80" url="recruitment/offers/" value={offer} label={(o) => `${o.title} – ${o.department_name}`}
          placeholder="All offers – search…" onChange={(v) => setOffer(v ? Number(v) : null)} />
      </div>
      <div className="grid gap-3 overflow-x-auto md:grid-cols-4 xl:grid-cols-7">
        {STAGES.map(([stage, label]) => {
          const items = rows.filter((a) => a.stage === stage);
          return (
            <div key={stage} className="min-w-[12rem] rounded-xl border p-2" style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}>
              <p className="section-label mb-2 flex justify-between">{label}<span>{items.length}</span></p>
              <div className="space-y-2">
                {items.map((a) => (
                  <button key={a.id} type="button" onClick={() => { setOpen(a); setScore(a.score ?? ""); }} className="card w-full p-2 text-start text-sm hover:shadow">
                    <p className="font-semibold text-primary-c">{a.full_name}</p>
                    <p className="truncate text-xs text-muted-c">{a.offer_title || "Spontaneous"}</p>
                    {a.score != null && <Badge tone="teal">{a.score}/100</Badge>}
                    {a.in_pool && <Badge tone="purple">Pool</Badge>}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <Modal open={!!open} title={open?.full_name} onClose={() => setOpen(null)} size="lg"
        footer={open && can("recruitment", "modify") && (
          <>
            {NEXT[open.stage]?.map((s) => (
              <button key={s} type="button" className={s === "REJECTED" ? "btn-danger" : "btn-secondary"} onClick={() => move(open, s, score)}>
                → {STAGES.find((x) => x[0] === s)?.[1]}
              </button>
            ))}
            {open.stage === "SELECTED" && can("recruitment", "validate") && (
              <button type="button" className="btn-teal" onClick={() => setHiring(open)}>Hire</button>
            )}
          </>
        )}>
        {open && (
          <div className="space-y-4">
            <DefinitionList items={[
              ["Offer", open.offer_title || "Spontaneous"], ["Stage", <StatusBadge value={open.stage} label={open.stage_label} />],
              ["E-mail", open.email], ["Phone", open.phone], ["Born on", fmt.date(open.date_of_birth)], ["Nationality", open.nationality || "—"],
              ["CV", open.cv ? <a className="text-brand-600 underline" href={open.cv} target="_blank" rel="noreferrer">Open</a> : "—"],
              ["Employee record", open.employee ? <button type="button" className="text-brand-600 underline" onClick={() => navigate(`/employees/${open.employee}`)}>{open.employee_matriculation}</button> : "—"],
            ]} />
            {open.motivation && <p className="whitespace-pre-line text-sm text-secondary-c">{open.motivation}</p>}
            {can("recruitment", "modify") && (
              <label className="block"><span className="field-label">Score (0-100), saved with the next move</span>
                <input type="number" className="input-field w-32" value={score} onChange={(e) => setScore(e.target.value)} />
              </label>
            )}
            <div>
              <p className="section-label mb-1">History</p>
              <ul className="space-y-1 text-sm">
                {open.events?.map((ev: any) => (
                  <li key={ev.id} className="text-secondary-c">{fmt.datetime(ev.at)} – <b>{ev.stage}</b> {ev.user_name && `by ${ev.user_name}`} {ev.comment && `· ${ev.comment}`}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </Modal>
      <PromptModal
        open={!!hiring}
        title={`Hire ${hiring?.full_name}`}
        message="The employee record is created from the application: nothing is typed again. The onboarding checklist is created."
        extraFields={[
          { name: "date_of_hire", label: "Date of hire", type: "date", required: true },
          departmentField("department", "Department (default: offer)"),
          positionField("position", "Position (default: offer)"),
        ]}
        onClose={() => setHiring(null)}
        onConfirm={async (v) => {
          const res = await api.post(`recruitment/applications/${hiring.id}/hire/`, { ...v, date_of_hire: v.date_of_hire || todayISO() });
          toast.success(`Employee record ${res.data.matriculation_number} created`);
          setOpen(null);
          reload();
          navigate(`/employees/${res.data.employee_id}`);
        }}
      />
    </>
  );
}

/** M-03 – recruitment and onboarding (BN-22 → BN-27). */
export default function Recruitment() {
  const [tab, setTab] = useHashTab("applications");
  const toast = useToast();
  const { can } = usePermissions();
  const [attaching, setAttaching] = useState<{ id: number; reload: () => void } | null>(null);
  const act = async (url: string, reload: () => void, label: string, data?: any) => {
    try {
      await api.post(url, data);
      toast.success(label);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <>
      <PageHeader title="Recruitment" eyebrow="Personnel" subtitle="Needs, job offers, applications, hiring and onboarding."
        actions={<a className="btn-secondary" href="/careers" target="_blank" rel="noreferrer">Public careers page ↗</a>} />
      <Tabs active={tab} onChange={setTab} tabs={[
        { id: "applications", label: "Applications" },
        { id: "needs", label: "Needs" },
        { id: "offers", label: "Job offers" },
        { id: "pool", label: "Candidate pool" },
        { id: "onboarding", label: "Onboarding" },
      ]} />
      {tab === "applications" && <Pipeline />}
      {tab === "needs" && (
        <CrudSection
          endpoint="recruitment/needs/"
          title="Recruitment needs"
          description="Validated by the HR manager then the general management."
          canEdit={(n: any) => ["DRAFT", "MODIFICATION"].includes(n.status)}
          canDelete={(n: any) => n.status === "DRAFT"}
          fields={[
            positionField("position", "Vacant position", true),
            departmentField("department", "Department", true),
            { name: "number_of_posts", label: "Number of posts", type: "number" },
            { name: "contract_type", label: "Contract", type: "select", options: CONTRACT_TYPES },
            { name: "desired_start", label: "Desired start", type: "date" },
            { name: "justification", label: "Justification", type: "textarea", required: true },
            { name: "submit", label: "Submit for approval now", type: "checkbox", alwaysSend: true },
          ]}
          defaults={{ number_of_posts: 1, contract_type: "PERMANENT", submit: true }}
          rowActions={[{ label: "Submit", show: (n: any) => ["DRAFT", "MODIFICATION"].includes(n.status), onClick: (n: any, reload) => act(`recruitment/needs/${n.id}/submit/`, reload, "Submitted") }]}
          columns={[
            { key: "position_title", header: "Position", render: (n: any) => <span className="font-medium text-primary-c">{n.position_title}</span> },
            { key: "department_name", header: "Department" },
            { key: "number_of_posts", header: "Posts", align: "end" },
            { key: "requested_by_name", header: "Requested by" },
            { key: "status", header: "Status", render: (n: any) => <StatusBadge value={n.status} /> },
          ]}
        />
      )}
      {tab === "offers" && (
        <CrudSection
          endpoint="recruitment/offers/"
          title="Job offers"
          modalSize="lg"
          canEdit={can("recruitment", "modify")}
          canDelete={(o: any) => o.status === "DRAFT"}
          fields={[
            { name: "title", label: "Title", required: true, full: true },
            { name: "need", label: "Approved need", type: "select", optionsUrl: "recruitment/needs/?status=APPROVED", optionLabel: (n: any) => `${n.position_title} – ${n.department_name}`, full: true },
            positionField("position", "Position", true),
            departmentField("department", "Department", true),
            siteField("location", "Location"),
            { name: "contract_type", label: "Contract", type: "select", options: CONTRACT_TYPES },
            { name: "closing_date", label: "Closing date", type: "date" },
            { name: "description", label: "Description", type: "textarea", required: true },
            { name: "requirements", label: "Requirements", type: "textarea" },
          ]}
          defaults={{ contract_type: "PERMANENT" }}
          rowActions={[
            { label: "Publish", show: (o: any) => o.status === "DRAFT", onClick: (o: any, reload) => act(`recruitment/offers/${o.id}/publish/`, reload, "Published on the careers page") },
            { label: "Close", show: (o: any) => o.status === "PUBLISHED", onClick: (o: any, reload) => act(`recruitment/offers/${o.id}/close/`, reload, "Closed") },
          ]}
          columns={[
            { key: "title", header: "Offer", render: (o: any) => <span className="font-medium text-primary-c">{o.title}</span> },
            { key: "department_name", header: "Department" },
            { key: "closing_date", header: "Closes", render: (o: any) => fmt.date(o.closing_date) },
            { key: "applications_count", header: "Applications", align: "end" },
            { key: "status", header: "Status", render: (o: any) => <StatusBadge value={o.status === "PUBLISHED" ? "PUBLISHED" : o.status} /> },
          ]}
        />
      )}
      {tab === "pool" && (
        <CrudSection
          endpoint="recruitment/applications/"
          params={{ in_pool: true }}
          title="Pool of candidates"
          description="Good profiles not retained, kept for future needs."
          canCreate={false}
          canDelete={false}
          canEdit={false}
          rowActions={[{ label: "Attach to an offer", onClick: (a: any, reload) => setAttaching({ id: a.id, reload }) }]}
          columns={[
            { key: "full_name", header: "Candidate" },
            { key: "email", header: "E-mail" },
            { key: "offer_title", header: "Last offer" },
            { key: "score", header: "Score", align: "end" },
          ]}
        />
      )}
      {tab === "onboarding" && (
        <CrudSection
          endpoint="recruitment/onboarding/"
          title="Onboarding checklist"
          fields={[
            { name: "employee", label: "Employee", type: "select", required: true, optionsUrl: "employees/", optionLabel: (e: any) => `${e.given_names} ${e.surname} (${e.matriculation_number})` },
            { name: "title", label: "Item", required: true },
            userField("responsible", "Responsible"),
            { name: "due_date", label: "Due", type: "date" },
          ]}
          rowActions={[{ label: "Done / undo", onClick: (t: any, reload) => act(`recruitment/onboarding/${t.id}/toggle/`, reload, t.done ? "Reopened" : "Done") }]}
          columns={[
            { key: "employee_name", header: "Employee" },
            { key: "title", header: "Item" },
            { key: "responsible_name", header: "Responsible" },
            { key: "due_date", header: "Due", render: (t: any) => fmt.date(t.due_date) },
            { key: "done", header: "", render: (t: any) => (t.done ? <Badge tone="green">Done</Badge> : <Badge tone="yellow">To do</Badge>) },
          ]}
        />
      )}
      <PromptModal
        open={!!attaching}
        title="Attach the candidate to an offer"
        extraFields={[{ ...offerField("offer", "Job offer", true), full: true }]}
        onClose={() => setAttaching(null)}
        onConfirm={async (v) => {
          if (attaching) await act(`recruitment/applications/${attaching.id}/attach/`, attaching.reload, "Attached to the offer", v);
        }}
      />
    </>
  );
}
