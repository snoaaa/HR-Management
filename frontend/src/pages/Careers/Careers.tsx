import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import CrudSection, { DownloadButton } from "@/components/kit/CrudSection";
import { PromptModal } from "@/components/kit/Form";
import type { FieldDef } from "@/components/kit/Form";
import { useApiItem, useHashTab } from "@/components/kit/hooks";
import { classificationField, departmentField, elementCodeField, employeeField, opt, positionField, siteField } from "@/components/kit/options";
import SearchSelect from "@/components/kit/SearchSelect";
import { Badge, Card, Empty, PageHeader, Spinner, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

const TYPES = opt([
  ["PROMOTION", "Promotion"],
  ["TRANSFER", "Transfer / affectation"],
  ["SALARY_REVISION", "Salary revision"],
  ["TEMPORARY_ASSIGNMENT", "Temporary assignment"],
  ["ACTING", "Acting position"],
  ["SECONDMENT", "Secondment"],
  ["DISCIPLINARY", "Disciplinary measure"],
  ["DEPARTURE", "Departure"],
]);
const is = (...types: string[]) => (v: Record<string, any>) => !types.includes(v.act_type);
const SITUATION = ["PROMOTION", "TRANSFER", "TEMPORARY_ASSIGNMENT", "ACTING", "SECONDMENT"];

const ACT_FIELDS: FieldDef[] = [
  employeeField(),
  { name: "act_type", label: "Act", type: "select", required: true, options: TYPES },
  { name: "effective_date", label: "Effective date", type: "date", required: true },
  { name: "end_date", label: "End (automatic return)", type: "date", hidden: is("TEMPORARY_ASSIGNMENT", "ACTING", "SECONDMENT") },
  { ...positionField("new_position", "New position"), hidden: is(...SITUATION) },
  { ...classificationField("new_classification", "New category / grade"), hidden: is("PROMOTION", "ACTING") },
  { ...departmentField("new_department", "Destination department"), hidden: is(...SITUATION) },
  { ...siteField("new_workplace", "Destination site"), hidden: is(...SITUATION) },
  { name: "new_base_salary", label: "New base salary", type: "number", hidden: is("PROMOTION", "SALARY_REVISION", "ACTING") },
  { name: "increase_percent", label: "or increase (%)", type: "number", step: "0.01", hidden: is("PROMOTION", "SALARY_REVISION") },
  { ...elementCodeField("bonus_element", "Bonus revised"), hidden: is("SALARY_REVISION", "PROMOTION") },
  { name: "bonus_value", label: "New bonus value", type: "number", hidden: is("SALARY_REVISION", "PROMOTION") },
  { name: "disciplinary_measure", label: "Measure", type: "select", hidden: is("DISCIPLINARY"),
    options: opt([["WARNING", "Warning"], ["REPRIMAND", "Reprimand"], ["SUSPENSION", "Suspension without pay"], ["DISMISSAL", "Dismissal"]]) },
  { name: "suspension_days", label: "Days of suspension", type: "number", hidden: (v) => v.act_type !== "DISCIPLINARY" || v.disciplinary_measure !== "SUSPENSION" },
  { name: "departure_reason", label: "Reason of departure", type: "select", hidden: is("DEPARTURE"),
    options: opt([["RESIGNATION", "Resignation"], ["DISMISSAL", "Dismissal"], ["END_OF_CONTRACT", "End of contract"], ["RETIREMENT", "Retirement"], ["DEATH", "Death"], ["MUTUAL", "Mutual agreement"]]) },
  { name: "notice_worked", label: "Notice worked", type: "checkbox", hidden: is("DEPARTURE") },
  { name: "decision_reference", label: "Decision reference" },
  { name: "reason", label: "Reason / justification", type: "textarea", required: true },
  { name: "submit", label: "Submit for approval now", type: "checkbox", alwaysSend: true },
];

function Acts() {
  const toast = useToast();
  const { can } = usePermissions();
  const [increase, setIncrease] = useState(false);
  const [key, setKey] = useState(0);
  const act = async (url: string, reload: () => void, label: string) => {
    try {
      await api.post(url);
      toast.success(label);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <>
      <CrudSection
        key={key}
        endpoint="careers/acts/"
        title="Career acts"
        description="Acts with an effect on the payroll are approved by the HR manager, then applied on their effective date (back pay included)."
        createLabel="+ New act"
        modalSize="lg"
        canCreate={can("careers", "create")}
        canEdit={(a: any) => can("careers", "modify") && ["DRAFT", "MODIFICATION"].includes(a.status)}
        canDelete={(a: any) => a.status === "DRAFT" && can("careers", "delete")}
        fields={ACT_FIELDS}
        defaults={{ act_type: "PROMOTION", notice_worked: true, submit: true }}
        toolbar={() => can("careers", "validate") && <button type="button" className="btn-secondary" onClick={() => setIncrease(true)}>General increase</button>}
        rowActions={[
          { label: "Submit", show: (a: any) => ["DRAFT", "MODIFICATION"].includes(a.status), onClick: (a: any, reload) => act(`careers/acts/${a.id}/submit/`, reload, "Submitted") },
          { label: "Cancel", tone: "danger", show: (a: any) => ["DRAFT", "SUBMITTED", "MODIFICATION", "APPROVED"].includes(a.status), onClick: (a: any, reload) => act(`careers/acts/${a.id}/cancel/`, reload, "Cancelled") },
        ]}
        columns={[
          { key: "effective_date", header: "Effective", render: (a: any) => fmt.date(a.effective_date) },
          { key: "employee_name", header: "Employee", render: (a: any) => <span className="font-medium text-primary-c">{a.employee_name}</span> },
          { key: "act_type_label", header: "Act" },
          { key: "summary", header: "Detail", render: (a: any) => [a.new_position_title, a.new_department_name, a.new_classification_label,
            a.new_base_salary ? fmt.money(a.new_base_salary) : a.increase_percent ? `+${a.increase_percent} %` : null,
            a.disciplinary_measure, a.departure_reason].filter(Boolean).join(" · ") },
          { key: "status", header: "Status", render: (a: any) => <StatusBadge value={a.status} label={a.status_label} /> },
          { key: "print", header: "", render: (a: any) => ["APPROVED", "APPLIED", "ENDED"].includes(a.status) && (
            <span onClick={(e) => e.stopPropagation()}><DownloadButton url={`careers/acts/${a.id}/print_decision/`} label="Decision" className="btn-ghost" /></span>
          ) },
        ]}
      />
      <PromptModal
        open={increase}
        title="General increase"
        message="One salary revision is created and applied for each employee of the population."
        extraFields={[
          { name: "increase_percent", label: "Increase (%)", type: "number", required: true, step: "0.01" },
          { name: "effective_date", label: "Effective date", type: "date", required: true },
          departmentField("department", "Only this department"),
          classificationField("classification", "Only this category"),
          { name: "reason", label: "Reason", full: true },
        ]}
        onClose={() => setIncrease(false)}
        onConfirm={async (v) => {
          const res = await api.post("careers/acts/general_increase/", v);
          toast.success(`${res.data.count} employee(s) revised`);
          setKey((k) => k + 1);
        }}
      />
    </>
  );
}

const EVENT_TONES: Record<string, string> = { HIRING: "green", DEPARTURE: "red", PROMOTION: "purple", TRANSFER: "teal",
  SALARY_REVISION: "blue", DISCIPLINARY: "red", TRAINING: "teal", SUSPENSION: "orange" };

function Timeline() {
  const [employee, setEmployee] = useState<number | null>(null);
  const { data, loading } = useApiItem<any[]>(employee ? `careers/acts/timeline/${employee}/` : null);
  return (
    <Card title="Career history" actions={
      <SearchSelect className="w-80" url="employees/" value={employee} onChange={(v) => setEmployee(v ? Number(v) : null)} placeholder="Search an employee by name or matriculation…" />
    }>
      {!employee ? <Empty>Choose an employee.</Empty> : loading || !data ? <Spinner /> : (
        <ol className="relative ms-3 border-s" style={{ borderColor: "var(--border-color)" }}>
          {data.map((event, index) => (
            <li key={index} className="mb-5 ms-5">
              <span className="absolute -start-1.5 mt-1.5 h-3 w-3 rounded-full" style={{ background: "var(--odoo-purple)" }} />
              <p className="text-xs text-muted-c">{fmt.date(event.date)}</p>
              <p className="flex items-center gap-2 font-semibold text-primary-c">
                {event.title} <Badge tone={EVENT_TONES[event.type] || "gray"}>{event.type.replace(/_/g, " ").toLowerCase()}</Badge>
              </p>
              {event.detail && <p className="text-sm text-secondary-c">{event.detail}</p>}
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

interface OrgNode { id: number; name: string; code: string; unit_type: string; manager_name: string; headcount: number; children: OrgNode[] }

function NodeView({ node, depth = 0 }: { node: OrgNode; depth?: number }) {
  return (
    <li className="mt-2" style={{ marginInlineStart: depth ? 20 : 0 }}>
      <div className="inline-flex flex-wrap items-center gap-2 rounded-lg border px-3 py-2" style={{ borderColor: "var(--border-color)", background: "var(--surface)" }}>
        <span className="font-semibold text-primary-c">{node.name}</span>
        <span className="mono text-xs text-muted-c">{node.code}</span>
        <Badge tone="purple">{node.unit_type?.toLowerCase()}</Badge>
        {node.manager_name && <span className="text-xs text-secondary-c">👤 {node.manager_name}</span>}
        <Badge tone="teal">{node.headcount} employee(s)</Badge>
      </div>
      {node.children.length > 0 && <ul className="border-s ps-3" style={{ borderColor: "var(--border-color)" }}>{node.children.map((c) => <NodeView key={c.id} node={c} depth={depth + 1} />)}</ul>}
    </li>
  );
}

function OrgChart() {
  const [date, setDate] = useState("");
  const { data, loading } = useApiItem<OrgNode[]>(`careers/org-chart/${date ? `?date=${date}` : ""}`);
  return (
    <Card title="Organisation chart" actions={
      <>
        <label className="flex items-center gap-2 text-sm text-secondary-c">As at <input type="date" className="input-field w-40" value={date} onChange={(e) => setDate(e.target.value)} /></label>
        <DownloadButton url="careers/org-chart/" params={{ file_format: "pdf", ...(date ? { date } : {}) }} label="Print" />
      </>
    }>
      {loading || !data ? <Spinner /> : data.length === 0 ? <Empty /> : <ul>{data.map((n) => <NodeView key={n.id} node={n} />)}</ul>}
    </Card>
  );
}

/** M-08 – career management. */
export default function Careers() {
  const [tab, setTab] = useHashTab("acts");
  return (
    <>
      <PageHeader title="Careers" eyebrow="Personnel" subtitle="Promotions, transfers, revisions, discipline and departures – traced and reflected in the payroll." />
      <Tabs active={tab} onChange={setTab} tabs={[{ id: "acts", label: "Acts" }, { id: "timeline", label: "Career history" }, { id: "orgchart", label: "Organisation chart" }]} />
      {tab === "acts" && <Acts />}
      {tab === "timeline" && <Timeline />}
      {tab === "orgchart" && <OrgChart />}
    </>
  );
}
