import { useState } from "react";
import api from "@/api/axiosConfig";
import { apiError } from "@/api/helpers";
import CrudSection from "@/components/kit/CrudSection";
import { FormModal } from "@/components/kit/Form";
import type { FieldDef } from "@/components/kit/Form";
import { useApiList, useHashTab } from "@/components/kit/hooks";
import { ROLES } from "@/components/kit/options";
import { Card, PageHeader, Tabs } from "@/components/kit/ui";
import { useToast } from "@/context/ToastContext";

interface Setting {
  id: number;
  key: string;
  value: string;
  description: string;
}

interface Level {
  order: number;
  approver: string;
  substitute: number | null;
  substitute_name?: string;
}
interface Circuit {
  id: number;
  request_type: string;
  name: string;
  levels: Level[];
}

const APPROVERS = [{ value: "LINE_MANAGER", label: "Line manager of the requester" }, ...ROLES];
const REQUEST_TYPES = [
  { value: "LEAVE", label: "Leave request" },
  { value: "OVERTIME", label: "Overtime" },
  { value: "CLOCKING_REGULARISATION", label: "Clocking regularisation" },
  { value: "SHIFT_SWAP", label: "Shift exchange" },
  { value: "CONTRACT_AMENDMENT", label: "Contract amendment" },
];

function Settings() {
  const { rows, reload } = useApiList<Setting>("settings/");
  const [edits, setEdits] = useState<Record<number, string>>({});
  const toast = useToast();
  const save = async (s: Setting) => {
    try {
      await api.patch(`settings/${s.id}/`, { value: edits[s.id] });
      toast.success(`${s.key} saved`);
      setEdits((p) => {
        const next = { ...p };
        delete next[s.id];
        return next;
      });
      reload();
    } catch (err) {
      toast.error(apiError(err));
    }
  };
  return (
    <Card title="Reference parameters (BN-178)" padded={false}>
      <table className="w-full">
        <thead>
          <tr>
            <th className="table-header-cell">Parameter</th>
            <th className="table-header-cell">Value</th>
            <th className="table-header-cell" />
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.id} className="table-row">
              <td className="table-cell">
                <p className="font-medium text-primary-c">{s.description || s.key}</p>
                <p className="mono text-[11px] text-muted-c">{s.key}</p>
              </td>
              <td className="table-cell w-64">
                <input className="input-field mono" value={edits[s.id] ?? s.value} onChange={(e) => setEdits((p) => ({ ...p, [s.id]: e.target.value }))} />
              </td>
              <td className="table-cell w-24 text-end">
                {edits[s.id] !== undefined && edits[s.id] !== s.value && (
                  <button type="button" className="btn-primary btn-sm" onClick={() => save(s)}>
                    Save
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function CircuitEditor({ circuit, onClose, onSaved }: { circuit: Circuit | null; onClose: () => void; onSaved: () => void }) {
  const [levels, setLevels] = useState<Level[]>(circuit?.levels || [{ order: 1, approver: "LINE_MANAGER", substitute: null }]);
  const fields: FieldDef[] = [
    { name: "request_type", label: "Type of request", type: "select", options: REQUEST_TYPES, required: true, readOnly: !!circuit },
    { name: "name", label: "Name", required: true },
  ];
  return (
    <FormModal
      open
      title={circuit ? `Circuit – ${circuit.name}` : "New approval circuit"}
      fields={fields}
      initial={circuit || {}}
      size="lg"
      onClose={onClose}
      onSaved={onSaved}
      onSubmit={async (payload) => {
        const body = { ...payload, request_type: circuit?.request_type || payload.request_type, levels: levels.map((l, i) => ({ ...l, order: i + 1 })) };
        return circuit ? api.put(`notifications/circuits/${circuit.id}/`, body) : api.post("notifications/circuits/", body);
      }}
      intro={
        <div className="space-y-2">
          <p className="section-label">Levels of approval</p>
          {levels.map((level, index) => (
            <div key={index} className="flex flex-wrap items-center gap-2 rounded-lg p-2" style={{ background: "var(--surface-3)" }}>
              <span className="badge-purple">Level {index + 1}</span>
              <select
                className="input-field max-w-xs flex-1"
                value={level.approver}
                onChange={(e) => setLevels((prev) => prev.map((l, i) => (i === index ? { ...l, approver: e.target.value } : l)))}
              >
                {APPROVERS.map((a) => (
                  <option key={a.value} value={a.value}>
                    {a.label}
                  </option>
                ))}
              </select>
              <input
                className="input-field w-40"
                placeholder="Substitute user id"
                value={level.substitute ?? ""}
                onChange={(e) => setLevels((prev) => prev.map((l, i) => (i === index ? { ...l, substitute: e.target.value ? Number(e.target.value) : null } : l)))}
              />
              <button type="button" className="btn-icon" onClick={() => setLevels((prev) => prev.filter((_, i) => i !== index))} aria-label="Remove">
                ✕
              </button>
            </div>
          ))}
          <button type="button" className="btn-ghost" onClick={() => setLevels((prev) => [...prev, { order: prev.length + 1, approver: "HR_MANAGER", substitute: null }])}>
            + Add a level
          </button>
          <p className="text-xs text-muted-c">Without any level, the requests of this type are approved automatically.</p>
        </div>
      }
    />
  );
}

function Circuits() {
  const { rows, reload } = useApiList<Circuit>("notifications/circuits/");
  const [editing, setEditing] = useState<Circuit | null | undefined>(undefined);
  const toast = useToast();
  return (
    <>
      <div className="mb-3 flex flex-wrap justify-end gap-2">
        <button
          type="button"
          className="btn-secondary"
          onClick={async () => {
            try {
              await api.post("notifications/run-alerts/");
              toast.success("Deadline alerts processed");
            } catch (err) {
              toast.error(apiError(err));
            }
          }}
        >
          Run the deadline alerts now
        </button>
        <button type="button" className="btn-primary" onClick={() => setEditing(null)}>
          + New circuit
        </button>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {rows.map((c) => (
          <Card key={c.id} title={c.name} actions={<button type="button" className="btn-ghost" onClick={() => setEditing(c)}>Edit</button>}>
            <p className="mono mb-3 text-xs text-muted-c">{c.request_type}</p>
            <ol className="flex flex-wrap items-center gap-2">
              {c.levels.length === 0 && <span className="badge-gray">Automatic approval</span>}
              {c.levels.map((l, i) => (
                <li key={i} className="flex items-center gap-2">
                  {i > 0 && <span className="text-muted-c">→</span>}
                  <span className="badge-purple">{APPROVERS.find((a) => a.value === l.approver)?.label || l.approver}</span>
                  {l.substitute_name && <span className="text-xs text-muted-c">(substitute {l.substitute_name})</span>}
                </li>
              ))}
            </ol>
          </Card>
        ))}
      </div>
      {editing !== undefined && <CircuitEditor circuit={editing} onClose={() => setEditing(undefined)} onSaved={reload} />}
    </>
  );
}

export default function AdminSettings() {
  const [tab, setTab] = useHashTab("settings");
  return (
    <>
      <PageHeader eyebrow="Administration" title="Workflow & settings" subtitle="Configuration of the system without development." />
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "settings", label: "Parameters" },
          { id: "circuits", label: "Approval circuits" },
          { id: "users", label: "Users" },
        ]}
      />
      {tab === "settings" && <Settings />}
      {tab === "circuits" && <Circuits />}
      {tab === "users" && (
        <CrudSection
          endpoint="users/management/"
          title="Accounts"
          description="Individual accounts (BN-169). New accounts receive the password Welcome123! and must change it at first login."
          canDelete
          columns={[
            { key: "username", header: "Username", render: (u: any) => <span className="font-medium text-primary-c">{u.username}</span> },
            { key: "name", header: "Name", render: (u: any) => `${u.first_name} ${u.last_name}` },
            { key: "role", header: "Role", render: (u: any) => <span className="badge-purple">{ROLES.find((r) => r.value === u.role)?.label || u.role}</span> },
            { key: "is_active", header: "Status", render: (u: any) => (u.is_active ? <span className="badge-green">Active</span> : <span className="badge-gray">Deactivated</span>) },
          ]}
          fields={[
            { name: "username", label: "Username", required: true },
            { name: "email", label: "E-mail", type: "email" },
            { name: "first_name", label: "First name" },
            { name: "last_name", label: "Last name" },
            { name: "role", label: "Role", type: "select", options: ROLES, required: true },
            { name: "is_active", label: "Active", type: "checkbox" },
          ]}
          defaults={{ role: "EMPLOYEE", is_active: true }}
        />
      )}
    </>
  );
}
