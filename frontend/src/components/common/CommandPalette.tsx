import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router";
import {
  Search,
  Users,
  FileText,
  Clock,
  Calendar,
  Banknote,
  Receipt,
  Settings,
  Shield,
  History,
  X,
  ArrowRight,
} from "lucide-react";
import api from "@/api/axiosConfig";

interface QuickAction {
  id: string;
  name: string;
  category: "Navigation" | "Action";
  path: string;
  icon: typeof Search;
}

const STATIC_ACTIONS: QuickAction[] = [
  { id: "dash", name: "Dashboard", category: "Navigation", path: "/", icon: History },
  { id: "emp", name: "Employee Directory", category: "Navigation", path: "/employees", icon: Users },
  { id: "emp_new", name: "Register New Employee", category: "Action", path: "/employees/new", icon: Users },
  { id: "contracts", name: "Contracts & Amendments", category: "Navigation", path: "/contracts", icon: FileText },
  { id: "attendance", name: "Attendance & Clock In/Out", category: "Navigation", path: "/attendance", icon: Clock },
  { id: "leave", name: "Leave & Absence Management", category: "Navigation", path: "/leave", icon: Calendar },
  { id: "myleave", name: "Request Time Off (My Leave)", category: "Action", path: "/my/leave", icon: Calendar },
  { id: "planning", name: "Shift & Planning Timetable", category: "Navigation", path: "/planning", icon: Clock },
  { id: "payroll", name: "Payroll Periods & Cycles", category: "Navigation", path: "/payroll", icon: Banknote },
  { id: "payslips", name: "Payslip Registry", category: "Navigation", path: "/payroll/payslips", icon: Receipt },
  { id: "simulation", name: "Payroll Net-to-Gross Simulator", category: "Action", path: "/payroll/simulation", icon: Banknote },
  { id: "org", name: "Organisation & Departments", category: "Navigation", path: "/organisation", icon: Settings },
  { id: "permissions", name: "Permission Matrix & RBAC", category: "Navigation", path: "/admin/permissions", icon: Shield },
  { id: "audit", name: "Audit Trail & Compliance Log", category: "Navigation", path: "/audit-trail", icon: History },
];

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [employeeResults, setEmployeeResults] = useState<any[]>([]);
  const navigate = useNavigate();

  // Reset state on open
  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIndex(0);
      setEmployeeResults([]);
    }
  }, [open]);

  // Global keydown for Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (open) onClose();
        else onClose(); // parent handles toggle
      }
      if (e.key === "Escape" && open) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // Search employees when typing
  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setEmployeeResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await api.get(`/api/employees/?search=${encodeURIComponent(query)}`);
        const data = Array.isArray(res.data) ? res.data : res.data?.results || [];
        setEmployeeResults(data.slice(0, 5));
      } catch {
        // quiet error
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  // Filter static actions
  const filteredActions = STATIC_ACTIONS.filter((a) =>
    a.name.toLowerCase().includes(query.toLowerCase()),
  );

  const totalResults = filteredActions.length + employeeResults.length;

  const handleSelect = useCallback(
    (path: string) => {
      onClose();
      navigate(path);
    },
    [navigate, onClose],
  );

  // Arrow key navigation
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!open) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % Math.max(1, totalResults));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + Math.max(1, totalResults)) % Math.max(1, totalResults));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (selectedIndex < filteredActions.length) {
          handleSelect(filteredActions[selectedIndex].path);
        } else {
          const emp = employeeResults[selectedIndex - filteredActions.length];
          if (emp) handleSelect(`/employees/${emp.id}`);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, selectedIndex, totalResults, filteredActions, employeeResults, handleSelect]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-900/60 backdrop-blur-xs animate-fade"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950 animate-scale-in">
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 border-b border-slate-200 px-4 py-3.5 dark:border-slate-800">
          <Search className="h-5 w-5 text-indigo-500 shrink-0" />
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a page, action, or employee name…"
            className="w-full bg-transparent text-sm font-medium text-slate-800 placeholder-slate-400 outline-none dark:text-slate-100"
          />
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2">
          {/* Employee Matches */}
          {employeeResults.length > 0 && (
            <div className="mb-2">
              <p className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Employees
              </p>
              {employeeResults.map((emp, i) => {
                const idx = filteredActions.length + i;
                const isSelected = selectedIndex === idx;
                return (
                  <button
                    key={emp.id}
                    type="button"
                    onClick={() => handleSelect(`/employees/${emp.id}`)}
                    className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-xs transition-colors ${
                      isSelected
                        ? "bg-indigo-50 text-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-200"
                        : "text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-900"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-100 text-indigo-700 font-bold text-[10px] dark:bg-indigo-900/50 dark:text-indigo-300">
                        {emp.first_name?.[0]}
                        {emp.last_name?.[0]}
                      </div>
                      <div>
                        <p className="font-semibold">{emp.first_name} {emp.last_name}</p>
                        <p className="text-[11px] text-slate-400">{emp.matricule || emp.job_title || "Employee"}</p>
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 opacity-60" />
                  </button>
                );
              })}
            </div>
          )}

          {/* Navigation / Actions */}
          {filteredActions.length > 0 && (
            <div>
              <p className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Pages & Commands
              </p>
              {filteredActions.map((item, i) => {
                const isSelected = selectedIndex === i;
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleSelect(item.path)}
                    className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-xs transition-colors ${
                      isSelected
                        ? "bg-indigo-50 text-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-200"
                        : "text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-900"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <span className="font-medium">{item.name}</span>
                    </div>
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                      {item.category}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {totalResults === 0 && (
            <div className="py-8 text-center text-xs text-slate-400">
              No results found for &ldquo;{query}&rdquo;
            </div>
          )}
        </div>

        {/* Footer shortcuts info */}
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-2 text-[11px] text-slate-500 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-400">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span className="font-mono text-[10px]">Saint Jean HRMS</span>
        </div>
      </div>
    </div>
  );
}
