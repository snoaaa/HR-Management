import { useEffect, useState } from "react";
import api from "@/api/axiosConfig";
import { apiError } from "@/api/helpers";
import { Card } from "@/components/kit/ui";
import { useToast } from "@/context/ToastContext";

interface Clocking {
  id: number;
  time_in: string;
  time_out: string | null;
}

/** BN-37: self-recording of entries and exits. */
export default function ClockWidget() {
  const [clockings, setClockings] = useState<Clocking[]>([]);
  const [isIn, setIsIn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(new Date());
  const toast = useToast();

  const load = async () => {
    try {
      const res = await api.get("attendance/clockings/mine/");
      setClockings(res.data.clockings || []);
      setIsIn(!!res.data.is_in);
    } catch {
      /* no employee record */
    }
  };

  useEffect(() => {
    load();
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const clock = async () => {
    setBusy(true);
    try {
      await api.post("attendance/clockings/clock/");
      toast.success(isIn ? "Exit recorded" : "Entry recorded");
      load();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Time clock">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="mono text-3xl font-semibold text-primary-c">
            {now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
          </p>
          <p className="mt-1 text-xs text-muted-c">
            {isIn ? "You are clocked in." : "You are not clocked in."}
          </p>
        </div>
        <button type="button" className={isIn ? "btn-secondary" : "btn-teal"} onClick={clock} disabled={busy}>
          {isIn ? "Clock out" : "Clock in"}
        </button>
      </div>
      {clockings.length > 0 && (
        <ul className="mt-4 space-y-1.5">
          {clockings.map((c) => (
            <li key={c.id} className="flex items-center justify-between rounded-lg px-3 py-2 text-sm" style={{ background: "var(--surface-3)" }}>
              <span className="text-secondary-c">Today</span>
              <span className="mono text-primary-c">
                {c.time_in.slice(0, 5)} → {c.time_out ? c.time_out.slice(0, 5) : "…"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
