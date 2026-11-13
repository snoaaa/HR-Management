import { useNavigate } from "react-router";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import CrudSection, { DownloadButton } from "@/components/kit/CrudSection";
import { useHashTab } from "@/components/kit/hooks";
import { PageHeader, StatusBadge, Tabs } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

const DEFAULT_CRITERIA = [
  { code: "QUALITY", label: "Quality of work", weight: 2 },
  { code: "PRODUCTIVITY", label: "Productivity", weight: 2 },
  { code: "TEAMWORK", label: "Team work", weight: 1 },
  { code: "INITIATIVE", label: "Initiative", weight: 1 },
  { code: "DISCIPLINE", label: "Discipline and punctuality", weight: 1 },
];

/** M-10 – evaluation campaigns and evaluations (BN-82 → BN-86). */
export default function Evaluation() {
  const [tab, setTab] = useHashTab("evaluations");
  const navigate = useNavigate();
  const toast = useToast();
  const { can } = usePermissions();
  const hr = can("evaluation", "create");
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
      <PageHeader title="Performance evaluation" eyebrow="Development" subtitle="Campaigns, objectives, self-evaluation, manager evaluation and proposals." />
      <Tabs active={tab} onChange={setTab} tabs={[{ id: "evaluations", label: "Evaluations" }, { id: "campaigns", label: "Campaigns", hidden: !hr }]} />
      {tab === "evaluations" && (
        <CrudSection
          endpoint="evaluation/evaluations/"
          title="Evaluations of my perimeter"
          canCreate={false}
          canEdit={false}
          canDelete={false}
          onRowClick={(e: any) => navigate(`/evaluation/${e.id}`)}
          columns={[
            { key: "campaign_name", header: "Campaign" },
            { key: "employee_name", header: "Employee", render: (e: any) => <span className="font-medium text-primary-c">{e.employee_name}</span> },
            { key: "department_name", header: "Department" },
            { key: "evaluator_name", header: "Evaluator" },
            { key: "final_score", header: "Score", align: "end", render: (e: any) => (e.final_score ? `${fmt.number(e.final_score, 1)} / 100` : "—") },
            { key: "status", header: "Status", render: (e: any) => <StatusBadge value={e.status === "VALIDATED" ? "VALIDATED" : e.status === "COMPLETED" ? "VERIFIED" : "PENDING"} label={e.status_label} /> },
          ]}
        />
      )}
      {tab === "campaigns" && (
        <CrudSection
          endpoint="evaluation/campaigns/"
          title="Campaigns"
          modalSize="lg"
          canEdit={(c: any) => c.status === "DRAFT"}
          canDelete={(c: any) => c.status === "DRAFT"}
          fields={[
            { name: "name", label: "Name", required: true, full: true },
            { name: "year", label: "Year", type: "number", required: true },
            { name: "scale_max", label: "Scores out of", type: "number" },
            { name: "start_date", label: "Start", type: "date", required: true },
            { name: "end_date", label: "End", type: "date", required: true },
            { name: "objectives_weight", label: "Weight of the objectives (%)", type: "number" },
            { name: "departments", label: "Departments (none = whole organisation)", type: "multiselect", full: true,
              optionsUrl: "organisation/departments/", optionLabel: (d: any) => `${d.name} (${d.code})` },
            { name: "criteria", label: "Evaluation form", type: "json", rows: 10, full: true, hint: 'Criteria [{"code", "label", "weight"}].' },
          ]}
          defaults={{ year: new Date().getFullYear(), scale_max: 5, objectives_weight: 50, departments: [], criteria: DEFAULT_CRITERIA }}
          rowActions={[
            { label: "Open", show: (c: any) => c.status === "DRAFT", onClick: (c: any, reload) => act(`evaluation/campaigns/${c.id}/open/`, reload, "Campaign opened: the employees are notified") },
            { label: "Close", show: (c: any) => c.status === "OPEN", onClick: (c: any, reload) => act(`evaluation/campaigns/${c.id}/close/`, reload, "Campaign closed") },
          ]}
          columns={[
            { key: "name", header: "Campaign", render: (c: any) => <span className="font-medium text-primary-c">{c.name}</span> },
            { key: "period", header: "Period", render: (c: any) => `${fmt.date(c.start_date)} → ${fmt.date(c.end_date)}` },
            { key: "department_names", header: "Population", render: (c: any) => (c.department_names.length ? c.department_names.join(", ") : "Whole organisation") },
            { key: "evaluations_count", header: "Evaluations", align: "end" },
            { key: "status", header: "Status", render: (c: any) => <StatusBadge value={c.status === "OPEN" ? "OPENED" : c.status} /> },
            { key: "print", header: "", render: (c: any) => c.status !== "DRAFT" && <span onClick={(e) => e.stopPropagation()}><DownloadButton url={`evaluation/campaigns/${c.id}/print_summary/`} label="Summary" className="btn-ghost" /></span> },
          ]}
        />
      )}
    </>
  );
}
