import { useEffect, useState } from "react";
import api from "@/api/axiosConfig";
import { apiError } from "@/api/helpers";
import { Card, PageHeader, Spinner } from "@/components/kit/ui";
import { usePermissions } from "@/context/PermissionsContext";
import { useToast } from "@/context/ToastContext";
import { cn } from "@/utils";

interface MatrixData {
  modules: string[];
  actions: string[];
  roles: { value: string; label: string }[];
  matrix: Record<string, Record<string, string[]>>;
}

/** BN-170: roles × modules × actions, editable without development. */
export default function PermissionMatrix() {
  const [data, setData] = useState<MatrixData | null>(null);
  const [role, setRole] = useState("EMPLOYEE");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const toast = useToast();
  const { refresh } = usePermissions();

  useEffect(() => {
    api.get("users/permission-matrix/").then((res) => setData(res.data));
  }, []);

  if (!data) return <Spinner />;

  const granted = (module: string, action: string) => (data.matrix[role]?.[module] || []).includes(action);

  const toggle = (module: string, action: string) => {
    const current = data.matrix[role]?.[module] || [];
    const next = current.includes(action) ? current.filter((a) => a !== action) : [...current, action];
    setData({ ...data, matrix: { ...data.matrix, [role]: { ...(data.matrix[role] || {}), [module]: next } } });
    setDirty(true);
  };

  const toggleRow = (module: string) => {
    const all = data.actions.every((a) => granted(module, a));
    setData({ ...data, matrix: { ...data.matrix, [role]: { ...(data.matrix[role] || {}), [module]: all ? [] : [...data.actions] } } });
    setDirty(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      const res = await api.put("users/permission-matrix/", { matrix: data.matrix });
      setData(res.data);
      setDirty(false);
      toast.success("Permissions saved – the change is recorded in the audit trail.");
      refresh();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Roles & permissions"
        subtitle="Fine-grained permissions per module and per action. The visible perimeter (own / team / organisation) follows the role."
        actions={
          <button type="button" className="btn-primary" disabled={!dirty || saving} onClick={save}>
            {saving ? "Saving…" : "Save the matrix"}
          </button>
        }
      />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-4">
        <Card title="Roles" padded={false}>
          <ul className="p-2">
            {data.roles.map((r) => (
              <li key={r.value}>
                <button
                  type="button"
                  onClick={() => setRole(r.value)}
                  className={cn(
                    "w-full rounded-lg px-3 py-2 text-start text-sm transition-colors",
                    role === r.value ? "bg-brand-50 font-semibold text-brand-600 dark:bg-brand-500/15 dark:text-brand-200" : "text-secondary-c hover:bg-gray-50 dark:hover:bg-white/5",
                  )}
                >
                  {r.label}
                </button>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="lg:col-span-3" title={data.roles.find((r) => r.value === role)?.label} padded={false}>
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full min-w-max">
              <thead>
                <tr>
                  <th className="table-header-cell">Module</th>
                  {data.actions.map((a) => (
                    <th key={a} className="table-header-cell text-center">
                      {a}
                    </th>
                  ))}
                  <th className="table-header-cell" />
                </tr>
              </thead>
              <tbody>
                {data.modules.map((m) => (
                  <tr key={m} className="table-row">
                    <td className="table-cell font-medium capitalize text-primary-c">{m}</td>
                    {data.actions.map((a) => (
                      <td key={a} className="table-cell text-center">
                        <input type="checkbox" className="h-4 w-4 accent-brand-500" checked={granted(m, a)} onChange={() => toggle(m, a)} aria-label={`${m} ${a}`} />
                      </td>
                    ))}
                    <td className="table-cell text-end">
                      <button type="button" className="btn-ghost text-xs" onClick={() => toggleRow(m)}>
                        All / none
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </>
  );
}
