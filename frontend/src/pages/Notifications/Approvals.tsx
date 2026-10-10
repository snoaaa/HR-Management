import { useState } from "react";
import { Link } from "react-router";
import api from "@/api/axiosConfig";
import { fmt } from "@/api/helpers";
import DataTable from "@/components/kit/DataTable";
import { PromptModal } from "@/components/kit/Form";
import { useApiList, useHashTab } from "@/components/kit/hooks";
import { Card, PageHeader, StatusBadge, Tabs } from "@/components/kit/ui";
import { useToast } from "@/context/ToastContext";

interface Task {
  id: number;
  request_type: string;
  object_id: number;
  level: number;
  summary: string;
  status: string;
  comment: string;
  approver_role: string;
  decided_by_name?: string;
  decided_at?: string;
  created_at: string;
  link: string;
}

type Decision = "APPROVED" | "REFUSED" | "MODIFICATION";

const LABEL: Record<Decision, string> = {
  APPROVED: "Approve",
  REFUSED: "Refuse",
  MODIFICATION: "Ask for a modification",
};

/** BN-51 / BN-153: inbox of the requests waiting for a decision. */
export default function Approvals() {
  const [tab, setTab] = useHashTab("pending");
  const { rows, loading, reload } = useApiList<Task>("notifications/approvals/", tab === "history" ? { scope: "history" } : undefined);
  const [action, setAction] = useState<{ task: Task; decision: Decision } | null>(null);
  const toast = useToast();

  const decide = async (values: Record<string, any>) => {
    if (!action) return;
    await api.post(`notifications/approvals/${action.task.id}/decide/`, {
      decision: action.decision,
      comment: values.comment || "",
    });
    toast.success("Decision recorded");
    reload();
  };

  return (
    <>
      <PageHeader eyebrow="Workflow" title="Approvals" subtitle="Leave, overtime, clocking regularisations and shift exchanges waiting for your decision." />
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "pending", label: "Waiting for me" },
          { id: "history", label: "My decisions" },
        ]}
      />
      <Card padded={false}>
        <DataTable<Task>
          rows={rows}
          loading={loading}
          empty={tab === "pending" ? "Nothing is waiting for your decision." : "You have not decided anything yet."}
          columns={[
            {
              key: "summary",
              header: "Request",
              render: (t) => (
                <div>
                  <p className="font-medium text-primary-c">{t.summary}</p>
                  {t.link && (
                    <Link to={t.link} className="text-xs text-brand-500 hover:underline dark:text-brand-300">
                      Open the request
                    </Link>
                  )}
                </div>
              ),
            },
            { key: "request_type", header: "Type", render: (t) => <span className="badge-purple">{t.request_type.replace(/_/g, " ").toLowerCase()}</span> },
            { key: "level", header: "Level", align: "center", mono: true },
            { key: "created_at", header: "Received", render: (t) => fmt.datetime(t.created_at) },
            ...(tab === "history"
              ? [
                  { key: "status", header: "Decision", render: (t: Task) => <StatusBadge value={t.status} /> },
                  { key: "comment", header: "Comment" },
                  { key: "decided_at", header: "Decided", render: (t: Task) => fmt.datetime(t.decided_at) },
                ]
              : [
                  {
                    key: "actions",
                    header: "",
                    align: "end" as const,
                    render: (t: Task) => (
                      <div className="flex justify-end gap-1.5">
                        <button type="button" className="btn-teal btn-sm" onClick={() => setAction({ task: t, decision: "APPROVED" })}>
                          Approve
                        </button>
                        <button type="button" className="btn-secondary btn-sm" onClick={() => setAction({ task: t, decision: "MODIFICATION" })}>
                          Modify
                        </button>
                        <button type="button" className="btn-danger btn-sm" onClick={() => setAction({ task: t, decision: "REFUSED" })}>
                          Refuse
                        </button>
                      </div>
                    ),
                  },
                ]),
          ]}
        />
      </Card>
      <PromptModal
        open={!!action}
        title={action ? LABEL[action.decision] : ""}
        message={action?.task.summary}
        danger={action?.decision === "REFUSED"}
        confirmLabel={action ? LABEL[action.decision] : "Confirm"}
        commentLabel={action?.decision === "APPROVED" ? "Comment (optional)" : "Reason"}
        commentRequired={action?.decision !== "APPROVED"}
        onClose={() => setAction(null)}
        onConfirm={decide}
      />
    </>
  );
}
