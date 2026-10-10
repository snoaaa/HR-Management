import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { DownloadButton } from "@/components/kit/CrudSection";
import DataTable from "@/components/kit/DataTable";
import { FormModal, PromptModal } from "@/components/kit/Form";
import { useApiItem } from "@/components/kit/hooks";
import { Banner, Card, DefinitionList, PageHeader, Spinner, StatusBadge } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";
import { amendmentFields, compact, contractFields, suspensionFields, terminationFields } from "./contractFields";

type Dialog = null | "edit" | "amend" | "renew" | "suspend" | "resume" | "terminate" | "activate" | "settlement";

export default function ContractDetail() {
  const { id } = useParams();
  const { data: c, loading, reload } = useApiItem<any>(`contracts/${id}/`);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [settlement, setSettlement] = useState<any>(null);
  const { can, can_view_salary } = usePermissions();
  const toast = useToast();
  const navigate = useNavigate();

  if (loading && !c) return <Spinner />;
  if (!c) return <Banner tone="error">This contract cannot be found.</Banner>;

  const money = (v: unknown) => (c.salary_hidden ? "•••••" : fmt.money(v));
  const inForce = ["ACTIVE", "SUSPENDED"].includes(c.status);
  const openSuspension = (c.suspensions || []).find((s: any) => !s.end_date);

  const post = (path: string) => async (payload: any) => {
    const res = await api.post(`contracts/${c.id}/${path}/`, payload);
    return res.data;
  };

  const runSettlement = async () => {
    try {
      const res = await api.post(`payroll/final-settlement/${c.termination.id}/`);
      setSettlement(res.data);
      toast.success("Final settlement computed and sent to the payroll of the month.");
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Contract"
        title={`${c.reference} – ${c.employee_name}`}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <StatusBadge value={c.status} />
            <span>{c.contract_type_label}</span>
            {c.in_force_today && <span className="badge-teal">In force today</span>}
          </span>
        }
        actions={
          <>
            <button type="button" className="btn-ghost" onClick={() => navigate("/contracts")}>
              ← Contracts
            </button>
            {can("contracts", "print") && <DownloadButton url={`contracts/${c.id}/print_contract/`} label="Print the contract" />}
            {c.status === "DRAFT" && can("contracts", "modify") && (
              <button type="button" className="btn-secondary" onClick={() => setDialog("edit")}>
                Edit draft
              </button>
            )}
            {c.status === "DRAFT" && can("contracts", "validate") && (
              <button type="button" className="btn-teal" onClick={() => setDialog("activate")}>
                Activate
              </button>
            )}
          </>
        }
      />

      {c.salary_hidden && <div className="mb-4"><Banner tone="info">Your profile does not give access to the salary of this employee (BN-172).</Banner></div>}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card title="Terms of the contract" className="xl:col-span-2">
          <DefinitionList
            items={[
              ["Employee", <Link className="text-brand-600 hover:underline dark:text-brand-300" to={`/employees/${c.employee}`}>{c.employee_name} ({c.employee_matriculation})</Link>],
              ["Type", c.contract_type_label],
              ["Start", fmt.date(c.start_date)],
              ["End", c.effective_end_date ? fmt.date(c.effective_end_date) : "Indefinite"],
              ["Trial period until", fmt.date(c.trial_period_end)],
              ["Notice", `${c.notice_period_days} days`],
              ["Weekly working time", `${fmt.number(c.weekly_hours)} h`],
              ["Base salary", <span className="mono">{money(c.base_salary)}</span>],
              ["Position", c.position_title],
              ["Category", c.classification_label],
              ["Department", c.department_name],
              ["Workplace", c.workplace_name],
              ["Renewals", c.renewal_count],
            ]}
          />
          {c.notes && <p className="mt-4 text-sm text-secondary-c">{c.notes}</p>}
        </Card>

        <Card title="Actions">
          <div className="flex flex-col gap-2">
            {inForce && can("contracts", "modify") && (
              <button type="button" className="btn-secondary justify-start" onClick={() => setDialog("amend")}>
                ✎ Amendment (salary, position, hours…)
              </button>
            )}
            {inForce && ["FIXED_TERM", "TEMPORARY", "INTERNSHIP"].includes(c.contract_type) && can("contracts", "modify") && (
              <button type="button" className="btn-secondary justify-start" onClick={() => setDialog("renew")}>
                ↻ Renew
              </button>
            )}
            {c.status === "ACTIVE" && can("contracts", "modify") && (
              <button type="button" className="btn-secondary justify-start" onClick={() => setDialog("suspend")}>
                ⏸ Suspend
              </button>
            )}
            {openSuspension && can("contracts", "modify") && (
              <button type="button" className="btn-secondary justify-start" onClick={() => setDialog("resume")}>
                ▶ End the suspension
              </button>
            )}
            {inForce && !c.termination && can("contracts", "validate") && (
              <button type="button" className="btn-danger justify-start" onClick={() => setDialog("terminate")}>
                ⏹ Terminate the contract
              </button>
            )}
            {c.termination && (
              <>
                <DownloadButton url={`contracts/${c.id}/end_certificate/`} label="End-of-contract certificate" className="btn-secondary justify-start" />
                {can_view_salary && can("payroll", "modify") && (
                  <button type="button" className="btn-teal justify-start" onClick={runSettlement}>
                    Compute the final settlement
                  </button>
                )}
              </>
            )}
            {!inForce && !c.termination && c.status !== "DRAFT" && <p className="text-sm text-muted-c">No action available.</p>}
          </div>
        </Card>
      </div>

      {c.termination && (
        <Card title="Termination" className="mt-5">
          <DefinitionList
            items={[
              ["Reason", c.termination.reason_label],
              ["Notified on", fmt.date(c.termination.notification_date)],
              ["Last working day", fmt.date(c.termination.termination_date)],
              ["Notice", `${c.termination.notice_days} days ${c.termination.notice_worked ? "(worked)" : "(not worked)"}`],
              ["Remaining leave", `${fmt.number(c.termination.leave_balance_days)} days`],
            ]}
          />
          {(settlement || c.termination.final_settlement?.items) && (
            <div className="mt-4">
              <p className="section-label mb-2">Final settlement</p>
              <DataTable
                rows={(settlement || c.termination.final_settlement).items}
                rowKey={(r: any) => r.code}
                columns={[
                  { key: "label", header: "Item" },
                  { key: "quantity", header: "Quantity", align: "end", mono: true },
                  { key: "amount", header: "Amount", align: "end", mono: true, render: (r: any) => money(r.amount) },
                ]}
              />
              <p className="mt-2 text-end text-sm font-semibold text-primary-c">
                Total: <span className="mono">{money((settlement || c.termination.final_settlement).total)}</span>
              </p>
            </div>
          )}
        </Card>
      )}

      <Card title="Amendments (versions)" className="mt-5" padded={false}>
        <DataTable
          rows={c.amendments || []}
          empty="No amendment."
          columns={[
            { key: "version", header: "Version", mono: true },
            { key: "effective_date", header: "Effective", render: (a: any) => fmt.date(a.effective_date) },
            { key: "reason", header: "Reason" },
            {
              key: "changes",
              header: "Changes",
              render: (a: any) => (
                <ul className="space-y-0.5 text-xs">
                  {Object.entries(a.new_values || {}).map(([k, v]) => (
                    <li key={k}>
                      <span className="text-muted-c">{k.replace("_id", "").replace("_", " ")}:</span>{" "}
                      <span className="line-through opacity-60">{String(a.previous_values?.[k] ?? "—")}</span> → <b>{String(v)}</b>
                    </li>
                  ))}
                </ul>
              ),
            },
            { key: "created_by_name", header: "By" },
            {
              key: "print",
              header: "",
              align: "end",
              render: (a: any) => <DownloadButton url={`contracts/${c.id}/print-amendment/${a.version}/`} label="Print" className="btn-ghost" />,
            },
          ]}
        />
      </Card>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card title="Renewals" padded={false}>
          <DataTable
            rows={c.renewals || []}
            empty="No renewal."
            columns={[
              { key: "renewal_number", header: "#", mono: true },
              { key: "previous_end_date", header: "Previous end", render: (r: any) => fmt.date(r.previous_end_date) },
              { key: "new_end_date", header: "New end", render: (r: any) => fmt.date(r.new_end_date) },
            ]}
          />
        </Card>
        <Card title="Suspensions" padded={false}>
          <DataTable
            rows={c.suspensions || []}
            empty="No suspension."
            columns={[
              { key: "reason_label", header: "Reason" },
              { key: "start_date", header: "From", render: (s: any) => fmt.date(s.start_date) },
              { key: "end_date", header: "To", render: (s: any) => (s.end_date ? fmt.date(s.end_date) : <span className="badge-orange">open</span>) },
              { key: "is_paid", header: "Paid", render: (s: any) => (s.is_paid ? "Yes" : "No") },
            ]}
          />
        </Card>
      </div>

      <FormModal open={dialog === "edit"} title="Edit the draft" fields={contractFields(true)} initial={c} endpoint="contracts/" id={c.id} size="lg" onClose={() => setDialog(null)} onSaved={reload} />
      <FormModal
        open={dialog === "amend"}
        title="New amendment (BN-30)"
        fields={amendmentFields}
        size="lg"
        intro={<Banner tone="info">Only the values you fill in are changed. A back-dated raise is paid as back pay by the payroll.</Banner>}
        onClose={() => setDialog(null)}
        onSaved={reload}
        onSubmit={(payload) => post("amend")(compact(payload))}
        submitLabel="Create the amendment"
      />
      <FormModal
        open={dialog === "renew"}
        title="Renew the contract (BN-32)"
        fields={[{ name: "new_end_date", label: "New end date", type: "date", required: true }]}
        size="sm"
        onClose={() => setDialog(null)}
        onSaved={reload}
        onSubmit={post("renew")}
        submitLabel="Renew"
      />
      <FormModal open={dialog === "suspend"} title="Suspend the contract (BN-33)" fields={suspensionFields} onClose={() => setDialog(null)} onSaved={reload} onSubmit={(p) => post("suspend")(compact(p))} submitLabel="Suspend" />
      <FormModal
        open={dialog === "resume"}
        title="End of the suspension"
        fields={[{ name: "end_date", label: "Last day of suspension", type: "date", required: true }]}
        size="sm"
        onClose={() => setDialog(null)}
        onSaved={reload}
        onSubmit={post("resume")}
      />
      <FormModal
        open={dialog === "terminate"}
        title="Terminate the contract (BN-34)"
        fields={terminationFields}
        initial={{ notice_worked: true }}
        onClose={() => setDialog(null)}
        onSaved={reload}
        onSubmit={(p) => post("terminate")(compact({ ...p, notice_worked: !!p.notice_worked }))}
        submitLabel="Terminate"
      />
      <PromptModal
        open={dialog === "activate"}
        title="Activate the contract"
        message="The employee record (contract type, position, department, workplace) will be updated from this contract."
        confirmLabel="Activate"
        onClose={() => setDialog(null)}
        onConfirm={async () => {
          await api.post(`contracts/${c.id}/activate/`);
          toast.success("Contract activated");
          reload();
        }}
      />
    </>
  );
}
