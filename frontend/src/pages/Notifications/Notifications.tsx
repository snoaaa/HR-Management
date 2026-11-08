import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import api from "@/api/axiosConfig";
import { apiError, fmt } from "@/api/helpers";
import { useApiList } from "@/components/kit/hooks";
import { Badge, Card, Empty, PageHeader, Spinner } from "@/components/kit/ui";
import { useToast } from "@/context/ToastContext";

interface Notification {
  id: number;
  title: string;
  message: string;
  link: string;
  category: string;
  is_read: boolean;
  created_at: string;
}

const TONE: Record<string, string> = { APPROVAL: "purple", ALERT: "orange", REQUEST: "blue", PAYROLL: "teal", PLANNING: "teal", INFO: "gray" };

/** BN-167: notification centre and choice of the channels. */
export default function Notifications() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const { rows, loading, reload } = useApiList<Notification>("notifications/", unreadOnly ? { unread: "true" } : undefined);
  const [prefs, setPrefs] = useState<{ in_app: boolean; email: boolean } | null>(null);
  const navigate = useNavigate();
  const toast = useToast();

  useEffect(() => {
    api.get("notifications/preferences/").then((res) => setPrefs(res.data));
  }, []);

  const savePrefs = async (next: { in_app: boolean; email: boolean }) => {
    setPrefs(next);
    try {
      await api.put("notifications/preferences/", next);
      toast.success("Preferences saved");
    } catch (err) {
      toast.error(apiError(err));
    }
  };

  const open = async (n: Notification) => {
    if (!n.is_read) await api.patch(`notifications/${n.id}/`, { is_read: true });
    if (n.link) navigate(n.link);
    else reload();
  };

  return (
    <>
      <PageHeader
        eyebrow="Overview"
        title="Notifications"
        subtitle="Requests, approvals and deadline alerts concerning you."
        actions={
          <>
            <label className="flex items-center gap-2 text-sm text-secondary-c">
              <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
              Unread only
            </label>
            <button
              type="button"
              className="btn-secondary"
              onClick={async () => {
                await api.post("notifications/mark_all_read/");
                reload();
              }}
            >
              Mark all as read
            </button>
          </>
        }
      />
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2" padded={false}>
          {loading ? (
            <Spinner />
          ) : rows.length === 0 ? (
            <Empty>No notification.</Empty>
          ) : (
            <ul>
              {rows.map((n) => (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => open(n)}
                    className="flex w-full items-start gap-3 border-b px-5 py-4 text-start transition-colors hover:bg-gray-50 dark:hover:bg-white/5"
                    style={{ borderColor: "var(--row-divider)" }}
                  >
                    <span className={`mt-2 h-2 w-2 shrink-0 rounded-full ${n.is_read ? "bg-gray-300 dark:bg-gray-700" : "bg-teal-500"}`} />
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <Badge tone={TONE[n.category]}>{n.category.toLowerCase()}</Badge>
                        <span className="text-xs text-muted-c">{fmt.datetime(n.created_at)}</span>
                      </span>
                      <span className={`mt-1 block text-sm ${n.is_read ? "text-secondary-c" : "font-semibold text-primary-c"}`}>{n.title}</span>
                      {n.message && <span className="mt-0.5 block text-sm text-muted-c">{n.message}</span>}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Channels">
          {prefs && (
            <div className="space-y-3">
              <label className="flex items-center justify-between gap-3 text-sm">
                <span className="text-primary-c">In the application</span>
                <input type="checkbox" checked={prefs.in_app} onChange={(e) => savePrefs({ ...prefs, in_app: e.target.checked })} />
              </label>
              <label className="flex items-center justify-between gap-3 text-sm">
                <span className="text-primary-c">By e-mail</span>
                <input type="checkbox" checked={prefs.email} onChange={(e) => savePrefs({ ...prefs, email: e.target.checked })} />
              </label>
              <p className="text-xs text-muted-c">Deadline alerts are always kept in the history even when the in-app channel is off.</p>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
