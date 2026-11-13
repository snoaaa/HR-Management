import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import api from "@/api/axiosConfig";
import { asList } from "@/api/helpers";
import { useAuth } from "./AuthContext";
import { useToast } from "./ToastContext";

export type Module =
  | "organisation"
  | "employees"
  | "contracts"
  | "attendance"
  | "planning"
  | "leave"
  | "payroll"
  | "documents"
  | "users"
  | "audit"
  | "accounting"
  | "careers"
  | "reports"
  | "evaluation"
  | "recruitment"
  | "training"
  | "imports";
export type Action = "consult" | "create" | "modify" | "delete" | "validate" | "print" | "export";

interface PermissionsState {
  role: string;
  permissions: Partial<Record<Module, Action[]>>;
  can_view_salary: boolean;
  employee_id: number | null;
  manages_departments: number[];
}

interface PermissionsContextType extends PermissionsState {
  loading: boolean;
  can: (module: Module, action?: Action) => boolean;
  isHR: boolean;
  isAdmin: boolean;
  isManager: boolean;
  refresh: () => void;
}

const EMPTY: PermissionsState = {
  role: "",
  permissions: {},
  can_view_salary: false,
  employee_id: null,
  manages_departments: [],
};

const PermissionsContext = createContext<PermissionsContextType | undefined>(undefined);

const ACTIVITY_EVENTS = ["mousemove", "mousedown", "keydown", "scroll", "touchstart"];

/**
 * BN-170: permissions of the logged-in user (role × module × action).
 * BN-174: automatic closing of an inactive session.
 */
export function PermissionsProvider({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const toast = useToast();
  const [state, setState] = useState<PermissionsState>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [timeoutMinutes, setTimeoutMinutes] = useState(15);
  const timer = useRef<number | undefined>(undefined);
  const warnTimer = useRef<number | undefined>(undefined);

  const load = useCallback(async () => {
    if (!user) {
      setState(EMPTY);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await api.get("users/me/permissions/");
      setState({ ...EMPTY, ...res.data });
    } catch {
      setState({ ...EMPTY, role: user.role });
    } finally {
      setLoading(false);
    }
    try {
      const res = await api.get("settings/");
      const row = asList<{ key: string; value: string }>(res.data).find((s) => s.key === "SESSION_INACTIVITY_MINUTES");
      const minutes = Number(row?.value);
      if (minutes > 0) setTimeoutMinutes(minutes);
    } catch {
      /* default value is kept */
    }
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!user) return;
    const reset = () => {
      window.clearTimeout(timer.current);
      window.clearTimeout(warnTimer.current);
      if (timeoutMinutes > 1) {
        warnTimer.current = window.setTimeout(
          () => toast.warning("Are you still there? You will be signed out in one minute unless you move the mouse or press a key."),
          (timeoutMinutes - 1) * 60_000,
        );
      }
      timer.current = window.setTimeout(() => {
        toast.warning("Your session was closed after a period of inactivity.");
        logout();
      }, timeoutMinutes * 60_000);
    };
    reset();
    ACTIVITY_EVENTS.forEach((event) => window.addEventListener(event, reset, { passive: true }));
    return () => {
      window.clearTimeout(timer.current);
      window.clearTimeout(warnTimer.current);
      ACTIVITY_EVENTS.forEach((event) => window.removeEventListener(event, reset));
    };
  }, [user, timeoutMinutes]);

  // The system administrator has access to every module and every action.
  const isSystemAdmin = state.role === "SYSTEM_ADMINISTRATOR";
  const can = useCallback(
    (module: Module, action: Action = "consult") => isSystemAdmin || (state.permissions[module] || []).includes(action),
    [state.permissions, isSystemAdmin],
  );

  const value: PermissionsContextType = {
    ...state,
    loading,
    can,
    isHR: isSystemAdmin || ["HR_MANAGER", "HR_OFFICER"].includes(state.role),
    isAdmin: ["SYSTEM_ADMINISTRATOR", "HR_MANAGER"].includes(state.role),
    isManager: isSystemAdmin || state.role === "HEAD_OF_DEPARTMENT" || state.manages_departments.length > 0,
    refresh: load,
  };

  return <PermissionsContext.Provider value={value}>{children}</PermissionsContext.Provider>;
}

export function usePermissions() {
  const ctx = useContext(PermissionsContext);
  if (!ctx) throw new Error("usePermissions must be used within PermissionsProvider");
  return ctx;
}
