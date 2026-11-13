import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { DownloadButton } from "@/components/kit/CrudSection";
import { useApiItem } from "@/components/kit/hooks";
import { Banner, Card, Field, KpiTile, PageHeader, Spinner, StatusBadge } from "@/components/kit/ui";
import { useAuth } from "@/context/AuthContext";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";

function Scores({ criteria, max, value, onChange, readOnly }: {
  criteria: { code: string; label: string; weight: number }[];
  max: number;
  value: Record<string, number>;
  onChange?: (v: Record<string, number>) => void;
  readOnly?: boolean;
}) {
  return (
    <div className="space-y-2">
      {criteria.map((c) => (
        <div key={c.code} className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="text-primary-c">{c.label} <span className="text-xs text-muted-c">×{c.weight}</span></span>
          <span className="flex gap-1">
            {Array.from({ length: max + 1 }, (_, n) => (
              <button
                key={n}
                type="button"
                disabled={readOnly}
                onClick={() => onChange?.({ ...value, [c.code]: n })}
                className="h-8 w-8 rounded-lg border text-xs font-semibold"
                style={{
                  borderColor: "var(--border-color)",
                  background: value[c.code] === n ? "var(--odoo-purple)" : "var(--surface)",
                  color: value[c.code] === n ? "#fff" : "var(--text-secondary)",
                }}
              >
                {n}
              </button>
            ))}
          </span>
        </div>
      ))}
    </div>
  );
}

/** BN-83 / BN-84: one evaluation, completed by the employee then the manager. */
export default function EvaluationForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const { can, employee_id } = usePermissions();
  const { data: e, reload, setData } = useApiItem<any>(`evaluation/evaluations/${id}/`);
  const [self, setSelf] = useState<Record<string, number>>({});
  const [selfComment, setSelfComment] = useState("");
  const [manager, setManager] = useState<Record<string, any>>({ manager_scores: {} });
  const [objectives, setObjectives] = useState<any[]>([]);

  useEffect(() => {
    if (!e) return;
    setSelf(e.self_scores || {});
    setSelfComment(e.self_comment || "");
    setManager({ manager_scores: e.manager_scores || {}, manager_comment: e.manager_comment, strengths: e.strengths,
      improvements: e.improvements, actions_decided: e.actions_decided, proposal: e.proposal, bonus_amount: e.bonus_amount,
      training_subject: e.training_subject });
    setObjectives(e.objectives || []);
  }, [e?.id, e?.status]);

  if (!e) return <Spinner />;
  const isEmployee = e.employee === employee_id && e.status === "SELF_ASSESSMENT";
  const isEvaluator = e.evaluator === user?.id || can("evaluation", "create");
  const post = async (url: string, body: any, label: string) => {
    try {
      setData((await api.post(url, body)).data);
      toast.success(label);
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  const setObjective = (i: number, field: string, value: any) => setObjectives(objectives.map((o, j) => (j === i ? { ...o, [field]: value } : o)));

  return (
    <>
      <PageHeader
        title={`${e.employee_name} – ${e.campaign_name}`}
        eyebrow="Performance evaluation"
        actions={
          <>
            <button type="button" className="btn-ghost" onClick={() => navigate(-1)}>← Back</button>
            <StatusBadge value={e.status === "VALIDATED" ? "VALIDATED" : "PENDING"} label={e.status_label} />
            <DownloadButton url={`evaluation/evaluations/${id}/print_record/`} label="Print the record" />
            {e.status === "COMPLETED" && can("evaluation", "create") && (
              <button type="button" className="btn-teal" onClick={() => post(`evaluation/evaluations/${id}/validate/`, {}, "Evaluation validated: the proposal is transmitted")}>Validate</button>
            )}
          </>
        }
      />
      {e.final_score != null && (
        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <KpiTile label="Final score" value={`${fmt.number(e.final_score, 1)} / 100`} />
          <KpiTile label="Proposal" value={e.proposal} accent="var(--odoo-teal)" />
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Self-evaluation" actions={isEmployee && <button type="button" className="btn-primary" onClick={() => post(`evaluation/evaluations/${id}/self_assessment/`, { scores: self, comment: selfComment }, "Self-evaluation sent to your manager")}>Send</button>}>
          {isEmployee ? <Banner tone="info">Score every criterion, then send your self-evaluation.</Banner> : null}
          <div className="mt-3 space-y-3">
            <Scores criteria={e.criteria} max={e.scale_max} value={self} onChange={setSelf} readOnly={!isEmployee} />
            <Field label="Comment"><textarea className="input-field" rows={3} value={selfComment} readOnly={!isEmployee} onChange={(ev) => setSelfComment(ev.target.value)} /></Field>
          </div>
        </Card>
        <Card title="Objectives" actions={isEvaluator && e.status !== "VALIDATED" && (
          <>
            <button type="button" className="btn-ghost" onClick={() => setObjectives([...objectives, { title: "", weight: 1, target: "", achievement_percent: "" }])}>+ Objective</button>
            <button type="button" className="btn-secondary" onClick={() => post(`evaluation/evaluations/${id}/objectives/`, { objectives: objectives.map((o) => ({ ...o, achievement_percent: o.achievement_percent === "" ? null : o.achievement_percent })) }, "Objectives saved")}>Save</button>
          </>
        )}>
          {objectives.length === 0 && <p className="text-sm text-muted-c">No objective.</p>}
          <div className="space-y-2">
            {objectives.map((o, i) => (
              <div key={i} className="grid grid-cols-12 gap-2">
                <input className="input-field col-span-5" placeholder="Objective" value={o.title} readOnly={!isEvaluator} onChange={(ev) => setObjective(i, "title", ev.target.value)} />
                <input className="input-field col-span-3" placeholder="Target" value={o.target} readOnly={!isEvaluator} onChange={(ev) => setObjective(i, "target", ev.target.value)} />
                <input className="input-field col-span-1" type="number" title="Weight" value={o.weight} readOnly={!isEvaluator} onChange={(ev) => setObjective(i, "weight", ev.target.value)} />
                <input className="input-field col-span-3" type="number" placeholder="Achieved %" value={o.achievement_percent ?? ""} readOnly={!isEvaluator} onChange={(ev) => setObjective(i, "achievement_percent", ev.target.value)} />
              </div>
            ))}
          </div>
        </Card>
        <Card title="Manager evaluation" className="lg:col-span-2" actions={isEvaluator && e.status === "MANAGER_ASSESSMENT" && (
          <button type="button" className="btn-primary" onClick={() => post(`evaluation/evaluations/${id}/manager_assessment/`, manager, "Evaluation completed")}>Complete the evaluation</button>
        )}>
          {e.status === "SELF_ASSESSMENT" && <Banner tone="info">Waiting for the self-evaluation of the employee.</Banner>}
          <div className="mt-3 grid gap-4 lg:grid-cols-2">
            <Scores criteria={e.criteria} max={e.scale_max} value={manager.manager_scores} readOnly={!(isEvaluator && e.status === "MANAGER_ASSESSMENT")}
              onChange={(v) => setManager({ ...manager, manager_scores: v })} />
            <div className="space-y-3">
              {(["manager_comment", "strengths", "improvements", "actions_decided"] as const).map((field) => (
                <Field key={field} label={{ manager_comment: "Comment", strengths: "Strengths", improvements: "To improve", actions_decided: "Actions decided" }[field]}>
                  <textarea className="input-field" rows={2} value={manager[field] || ""} readOnly={!(isEvaluator && e.status === "MANAGER_ASSESSMENT")}
                    onChange={(ev) => setManager({ ...manager, [field]: ev.target.value })} />
                </Field>
              ))}
              <Field label="Proposal">
                <select className="input-field" value={manager.proposal || "NONE"} disabled={!(isEvaluator && e.status === "MANAGER_ASSESSMENT")} onChange={(ev) => setManager({ ...manager, proposal: ev.target.value })}>
                  <option value="NONE">No proposal</option>
                  <option value="PROMOTION">Promotion</option>
                  <option value="TRAINING">Training</option>
                  <option value="BONUS">Performance bonus</option>
                </select>
              </Field>
              {manager.proposal === "BONUS" && <Field label="Bonus amount"><input type="number" className="input-field" value={manager.bonus_amount || ""} onChange={(ev) => setManager({ ...manager, bonus_amount: ev.target.value })} /></Field>}
              {manager.proposal === "TRAINING" && <Field label="Training subject"><input className="input-field" value={manager.training_subject || ""} onChange={(ev) => setManager({ ...manager, training_subject: ev.target.value })} /></Field>}
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}
