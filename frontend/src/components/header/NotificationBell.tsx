import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import api from "@/api/axiosConfig";
import { asList, fmt } from "@/api/helpers";
import { useClickOutside } from "@/hooks/useClickOutside";
import { BellAltIcon } from "@/icons";

interface Notification {
  id: number;
  title: string;
  message: string;
  link: string;
  category: string;
  is_read: boolean;
  created_at: string;
}

const CATEGORY_TONE: Record<string, string> = {
  APPROVAL: "badge-purple",
  ALERT: "badge-orange",
  REQUEST: "badge-blue",
  PAYROLL: "badge-teal",
  PLANNING: "badge-teal",
  INFO: "badge-gray",
};

/** BN-167: notification centre in the header. */
export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [count, setCount] = useState(0);
  const [items, setItems] = useState<Notification[]>([]);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  useClickOutside(ref, () => setOpen(false));

  const refreshCount = async () => {
    try {
      const res = await api.get("notifications/unread_count/");
      setCount(res.data.count || 0);
    } catch {
      /* ignored */
    }
  };

  useEffect(() => {
    refreshCount();
    const timer = window.setInterval(refreshCount, 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next) {
      const res = await api.get("notifications/");
      setItems(asList<Notification>(res.data).slice(0, 8));
    }
  };

  const openItem = async (n: Notification) => {
    if (!n.is_read) {
      await api.patch(`notifications/${n.id}/`, { is_read: true }).catch(() => undefined);
      refreshCount();
    }
    setOpen(false);
    if (n.link) navigate(n.link);
  };

  const markAll = async () => {
    await api.post("notifications/mark_all_read/");
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setCount(0);
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={toggle}
        className="relative flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:border-gray-800 dark:text-gray-400 dark:hover:bg-white/5"
        aria-label="Notifications"
      >
        <BellAltIcon className="size-5" />
        {count > 0 && (
          <span className="absolute -end-0.5 -top-0.5 flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-teal-500 px-1 text-[10px] font-bold text-white">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>
      {open && (
        <div className="card animate-scale-in absolute end-0 z-99999 mt-3 w-[22rem] max-w-[calc(100vw-2rem)] overflow-hidden shadow-theme-lg">
          <div className="flex items-center justify-between border-b px-4 py-3" style={{ borderColor: "var(--border-color)" }}>
            <p className="text-sm font-semibold text-primary-c">Notifications</p>
            {count > 0 && (
              <button type="button" className="text-xs font-medium text-brand-500 hover:underline dark:text-brand-300" onClick={markAll}>
                Mark all as read
              </button>
            )}
          </div>
          <ul className="max-h-96 overflow-y-auto custom-scrollbar">
            {items.length === 0 && <li className="px-4 py-8 text-center text-sm text-muted-c">You are all caught up.</li>}
            {items.map((n) => (
              <li key={n.id}>
                <button
                  type="button"
                  onClick={() => openItem(n)}
                  className="flex w-full gap-3 border-b px-4 py-3 text-start transition-colors hover:bg-gray-50 dark:hover:bg-white/5"
                  style={{ borderColor: "var(--row-divider)" }}
                >
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.is_read ? "bg-transparent" : "bg-teal-500"}`} />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className={CATEGORY_TONE[n.category] || "badge-gray"}>{n.category.toLowerCase()}</span>
                      <span className="text-[11px] text-muted-c">{fmt.datetime(n.created_at)}</span>
                    </span>
                    <span className="mt-1 block truncate text-sm font-medium text-primary-c">{n.title}</span>
                    {n.message && <span className="block truncate text-xs text-muted-c">{n.message}</span>}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <Link to="/notifications" onClick={() => setOpen(false)} className="block py-2.5 text-center text-xs font-semibold text-brand-500 hover:bg-gray-50 dark:text-brand-300 dark:hover:bg-white/5">
            See all notifications
          </Link>
        </div>
      )}
    </div>
  );
}
