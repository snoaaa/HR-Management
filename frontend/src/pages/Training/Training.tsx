import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { BarList } from "@/components/kit/Charts";
import CrudSection from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { FormGrid } from "@/components/kit/Form";
import { useApiItem, useHashTab } from "@/components/kit/hooks";
import { departmentField, employeeField, opt, positionField, skillField } from "@/components/kit/options";
import SearchSelect from "@/components/kit/SearchSelect";
import { Badge, Card, Empty, KpiTile, Modal, PageHeader, Spinner, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

const year = new Date().getFullYear();
const LEVELS = opt([["1", "1 – notions"], ["2", "2 – basic"], ["3", "3 – autonomous"], ["4", "4 – expert"], ["5", "5 – reference"]]);

function Plan() {
  const [selected, setSelected] = useState(year);
  const { data } = useApiItem<any>(`training/plans/costs/?year=${selected}`);
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="field-label mb-0">Year</span>
        <input type="number" className="input-field w-28" value={selected} onChange={(e) => setSelected(Number(e.target.value))} />
      </div>
      {!data ? <Spinner /> : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <KpiTile label="Budget" value={fmt.money(data.budget)} />
            <KpiTile label="Spent" value={fmt.money(data.spent)} accent="#E9730C" />
            <KpiTile label="Remaining" value={fmt.money(data.remaining)} accent="var(--odoo-teal)" />
            <KpiTile label="Trained employees" value={data.trained_employees} accent="#0A6ED1" />
            <KpiTile label="Effectiveness" value={data.average_effectiveness ? `${data.average_effectiveness} / 5` : "—"} accent="#107E3E" />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="Cost per department"><BarList data={data.by_department} format={(v) => fmt.money(v)} /></Card>
            <Card title="Cost per employee"><BarList data={data.by_employee.slice(0, 15)} format={(v) => fmt.money(v)} color="#00A09D" /></Card>
          </div>
        </>
      )}
      <CrudSection
        endpoint="training/plans/"
        title="Annual plans"
        fields={[
          { name: "year", label: "Year", type: "number", required: true },
          { name: "budget", label: "Budget", type: "number", required: true },
          { name: "status", label: "Status", type: "select", options: opt([["DRAFT", "Draft"], ["APPROVED", "Approved"]]) },
          { name: "notes", label: "Notes", type: "textarea" },
        ]}
        defaults={{ year, status: "DRAFT" }}
        columns={[
          { key: "year", header: "Year" },
          { key: "budget", header: "Budget", align: "end", render: (p: any) => fmt.money(p.budget) },
          { key: "status", header: "Status", render: (p: any) => <StatusBadge value={p.status === "APPROVED" ? "APPROVED" : "DRAFT"} /> },
        ]}
      />
    </div>
  );
}

function Sessions() {
  const toast = useToast();
  const [open, setOpen] = useState<number | null>(null);
  const { data: session, reload } = useApiItem<any>(open ? `training/sessions/${open}/` : null);
  const [toRegister, setToRegister] = useState<number | null>(null);
  const [result, setResult] = useState<any>(null);
  const [values, setValues] = useState<Record<string, any>>({});
  const register = async () => {
    try {
      await api.post(`training/sessions/${open}/register/`, { employees: [toRegister] });
      setToRegister(null);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  const saveResult = async () => {
    const form = new FormData();
    Object.entries(values).forEach(([k, v]) => v !== undefined && v !== null && v !== "" && form.append(k, v as any));
    try {
      await api.post(`training/sessions/${open}/result/${result.id}/`, form);
      toast.success("Result recorded – skills and employee record updated");
      setResult(null);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <>
      <CrudSection
        endpoint="training/sessions/"
        title="Sessions"
        modalSize="lg"
        onRowClick={(s: any) => setOpen(s.id)}
        fields={[
          { name: "title", label: "Title", required: true, full: true },
          { name: "plan", label: "Plan", type: "select", optionsUrl: "training/plans/", optionLabel: (p: any) => `Plan ${p.year}` },
          { name: "organiser", label: "Organiser", required: true },
          { name: "trainer", label: "Trainer" },
          { name: "place", label: "Place", required: true },
          { name: "start_date", label: "Start", type: "date", required: true },
          { name: "end_date", label: "End", type: "date", required: true },
          { name: "cost", label: "Total cost", type: "number" },
          { name: "max_participants", label: "Maximum participants", type: "number" },
          { name: "certificate_validity_months", label: "Certificate valid (months)", type: "number" },
          { name: "skills", label: "Skills developed", type: "multiselect", optionsUrl: "training/skills/", optionLabel: (s: any) => s.name, full: true },
          { name: "description", label: "Description", type: "textarea" },
        ]}
        defaults={{ skills: [], cost: 0 }}
        columns={[
          { key: "title", header: "Session", render: (s: any) => <span className="font-medium text-primary-c">{s.title}</span> },
          { key: "dates", header: "Dates", render: (s: any) => `${fmt.date(s.start_date)} → ${fmt.date(s.end_date)}` },
          { key: "place", header: "Place" },
          { key: "participants", header: "Participants", align: "end", render: (s: any) => `${s.participations.length}${s.max_participants ? ` / ${s.max_participants}` : ""}` },
          { key: "cost", header: "Cost", align: "end", render: (s: any) => fmt.money(s.cost) },
          { key: "status", header: "Status", render: (s: any) => <StatusBadge value={s.status === "PLANNED" ? "PENDING" : s.status === "DONE" ? "CLOSED" : s.status} label={s.status} /> },
        ]}
      />
      <Modal open={!!open} title={session?.title || "Session"} onClose={() => setOpen(null)} size="xl"
        footer={session && session.status !== "DONE" && (
          <button type="button" className="btn-secondary" onClick={async () => { await api.post(`training/sessions/${open}/close/`); reload(); }}>Close the session</button>
        )}>
        {!session ? <Spinner /> : (
          <div className="space-y-4">
            <p className="text-sm text-secondary-c">{session.organiser} · {session.place} · {fmt.money(session.cost)} ({fmt.money(session.cost_per_participant)} per participant)
              {session.skill_names.length > 0 && <> · skills: {session.skill_names.join(", ")}</>}</p>
            {session.status !== "DONE" && (
              <div className="flex gap-2">
                <SearchSelect className="flex-1" url="employees/" value={toRegister} onChange={(v) => setToRegister(v ? Number(v) : null)} placeholder="Search an employee to register…" />
                <button type="button" className="btn-primary" disabled={!toRegister} onClick={register}>Register</button>
              </div>
            )}
            <DataTable exportTitle={`Participants – ${session.title}`}
              rows={session.participations}
              columns={[
                { key: "employee_name", header: "Participant" },
                { key: "status", header: "Attendance" },
                { key: "result", header: "Result", render: (p: any) => <Badge tone={p.result === "PASSED" ? "green" : p.result === "FAILED" ? "red" : "gray"}>{p.result}</Badge> },
                { key: "certificate_validity", header: "Certificate valid until", render: (p: any) => fmt.date(p.certificate_validity) },
                { key: "effectiveness", header: "Effect (1-5)", align: "center" },
                { key: "a", header: "", render: (p: any) => <button type="button" className="btn-ghost text-brand-600" onClick={() => { setResult(p); setValues({ status: p.status, result: p.result }); }}>Result</button> },
              ]}
            />
          </div>
        )}
      </Modal>
      <Modal open={!!result} title={`Result – ${result?.employee_name}`} onClose={() => setResult(null)}
        footer={<button type="button" className="btn-primary" onClick={saveResult}>Save</button>}>
        <FormGrid
          fields={[
            { name: "status", label: "Attendance", type: "select", options: opt([["REGISTERED", "Registered"], ["ATTENDED", "Attended"], ["ABSENT", "Absent"], ["CANCELLED", "Cancelled"]]) },
            { name: "result", label: "Result", type: "select", options: opt([["PENDING", "Pending"], ["PASSED", "Passed"], ["FAILED", "Failed"]]) },
            { name: "certificate", label: "Certificate (attached to the employee record)", type: "file" },
            { name: "certificate_validity", label: "Certificate valid until", type: "date" },
            { name: "satisfaction", label: "Satisfaction (1-5)", type: "select", options: LEVELS },
            { name: "effectiveness", label: "Effect observed (1 to 5)", type: "select", options: LEVELS },
            { name: "comment", label: "Comment", type: "textarea" },
          ]}
          values={values}
          onChange={(n, v) => setValues((p) => ({ ...p, [n]: v }))}
        />
      </Modal>
    </>
  );
}

function Skills() {
  const [employee, setEmployee] = useState<number | null>(null);
  const { data: gaps } = useApiItem<any[]>(employee ? `training/gaps/${employee}/` : null);
  return (
    <div className="space-y-4">
      <CrudSection endpoint="training/skills/" title="Repository of skills"
        fields={[{ name: "name", label: "Skill", required: true }, { name: "category", label: "Category" }, { name: "description", label: "Description", type: "textarea" }]}
        columns={[{ key: "name", header: "Skill" }, { key: "category", header: "Category" }]} />
      <CrudSection endpoint="training/position-skills/" title="Profile required by position"
        fields={[positionField("position", "Position", true), skillField(), { name: "required_level", label: "Required level", type: "select", options: LEVELS }]}
        defaults={{ required_level: "3" }}
        columns={[{ key: "position_title", header: "Position" }, { key: "skill_name", header: "Skill" }, { key: "required_level", header: "Level", align: "center" }]} />
      <CrudSection endpoint="training/employee-skills/" title="Skills of the employees"
        fields={[employeeField(), skillField(), { name: "level", label: "Level", type: "select", options: LEVELS }, { name: "assessed_at", label: "Assessed on", type: "date", required: true }]}
        columns={[{ key: "employee_name", header: "Employee" }, { key: "skill_name", header: "Skill" }, { key: "level", header: "Level", align: "center" },
          { key: "assessed_at", header: "Assessed", render: (s: any) => fmt.date(s.assessed_at) }, { key: "source", header: "Source" }]} />
      <Card title="Gaps with the position profile" actions={<SearchSelect className="w-80" url="employees/" value={employee} onChange={(v) => setEmployee(v ? Number(v) : null)} placeholder="Search an employee…" />}>
        {!employee ? <Empty>Choose an employee.</Empty> : !gaps ? <Spinner /> : (
          <DataTable exportTitle="Skill gaps" rows={gaps} rowKey={(g: any) => g.skill} empty="No required skill defined for the position." columns={[
            { key: "skill", header: "Skill" }, { key: "required", header: "Required", align: "center" }, { key: "level", header: "Level", align: "center" },
            { key: "gap", header: "Gap", align: "center", render: (g: any) => (g.gap ? <Badge tone="red">{g.gap}</Badge> : <Badge tone="green">OK</Badge>) },
          ]} />
        )}
      </Card>
    </div>
  );
}

/** M-09 – training and skills. */
export default function Training() {
  const [tab, setTab] = useHashTab("sessions");
  const { can } = usePermissions();
  return (
    <>
      <PageHeader title="Training & skills" eyebrow="Development" subtitle="Skills, needs, annual plan, sessions, results and costs." />
      <Tabs active={tab} onChange={setTab} tabs={[
        { id: "sessions", label: "Sessions" },
        { id: "needs", label: "Needs" },
        { id: "plan", label: "Plan & costs" },
        { id: "skills", label: "Skills" },
      ]} />
      {tab === "sessions" && <Sessions />}
      {tab === "plan" && <Plan />}
      {tab === "skills" && <Skills />}
      {tab === "needs" && (
        <CrudSection
          endpoint="training/needs/"
          title="Training needs"
          description="Collected from managers, employees and evaluations."
          canEdit={can("training", "modify")}
          canDelete={can("training", "modify")}
          fields={[
            { name: "subject", label: "Subject", required: true, full: true },
            employeeField("employee", "Employee", false),
            departmentField(),
            { ...skillField(), required: false },
            { name: "priority", label: "Priority", type: "select", options: opt([["LOW", "Low"], ["MEDIUM", "Medium"], ["HIGH", "High"]]) },
            { name: "year", label: "Year", type: "number", required: true },
            { name: "estimated_cost", label: "Estimated cost", type: "number" },
            { name: "status", label: "Status", type: "select", options: opt([["IDENTIFIED", "Identified"], ["PLANNED", "Planned"], ["DONE", "Done"], ["REJECTED", "Rejected"]]) },
          ]}
          defaults={{ priority: "MEDIUM", year, status: "IDENTIFIED" }}
          columns={[
            { key: "subject", header: "Subject", render: (n: any) => <span className="font-medium text-primary-c">{n.subject}</span> },
            { key: "employee_name", header: "For", render: (n: any) => n.employee_name || n.department_name || "—" },
            { key: "origin", header: "Origin" },
            { key: "priority", header: "Priority", render: (n: any) => <Badge tone={n.priority === "HIGH" ? "red" : n.priority === "MEDIUM" ? "yellow" : "gray"}>{n.priority}</Badge> },
            { key: "estimated_cost", header: "Estimate", align: "end", render: (n: any) => fmt.money(n.estimated_cost) },
            { key: "status", header: "Status", render: (n: any) => <StatusBadge value={n.status === "IDENTIFIED" ? "PENDING" : n.status === "PLANNED" ? "APPROVED" : n.status === "DONE" ? "CLOSED" : "REFUSED"} label={n.status} /> },
          ]}
        />
      )}
    </>
  );
}
