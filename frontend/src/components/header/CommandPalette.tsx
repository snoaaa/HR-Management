import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router";
import api from "@/api/axiosConfig";
import { asList } from "@/api/helpers";
import { ArrowRightIcon, BoltIcon, SearchIcon, UserCircleIcon } from "@/icons";
import { useNavigation } from "@/layout/useNavigation";

interface Entry {
  id: string;
  section: string;
  label: string;
  hint?: string;
  icon: ReactNode;
  path: string;
  text: string;
}

interface EmployeeRow {
  id: number;
  surname: string;
  given_names: string;
  matriculation_number?: string;
}

const normalise = (text: string) =>
  text
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");

/**
 * "Search or jump to…": one box to reach any screen, start a frequent task or
 * open an employee record, without knowing where it lives in the menu.
 */
export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { groups, actions } = useNavigation();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const [employees, setEmployees] = useState<EmployeeRow[] | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLDivElement>(null);

  const canSeeEmployees = groups.some((g) => g.items.some((i) => i.path === "/employees"));

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setCursor(0);
    window.setTimeout(() => input.current?.focus(), 30);
    if (canSeeEmployees && employees === null) {
      api
        .get("employees/")
        .then((res) => setEmployees(asList<EmployeeRow>(res.data)))
        .catch(() => setEmployees([]));
    }
  }, [open]);

  const entries = useMemo<Entry[]>(() => {
    const words = normalise(query).split(/\s+/).filter(Boolean);
    const match = (e: Entry) => words.every((w) => e.text.includes(w));
    const actionEntries: Entry[] = actions.map((a) => ({
      id: `action:${a.name}`,
      section: "Quick actions",
      label: a.name,
      hint: a.description,
      icon: <BoltIcon className="size-4.5" />,
      path: a.path,
      text: normalise(`${a.name} ${a.description}`),
    }));
    const pageEntries: Entry[] = groups.flatMap((g) =>
      g.items.map((i) => ({
        id: `page:${i.path}`,
        section: "Screens",
        label: i.name,
        hint: g.label,
        icon: i.icon,
        path: i.path,
        text: normalise(`${i.name} ${g.label} ${i.keywords || ""}`),
      })),
    );
    const employeeEntries: Entry[] =
      words.length === 0
        ? []
        : (employees || []).map((e) => ({
            id: `employee:${e.id}`,
            section: "Employees",
            label: `${e.surname} ${e.given_names}`,
            hint: e.matriculation_number,
            icon: <UserCircleIcon className="size-4.5" />,
            path: `/employees/${e.id}`,
            text: normalise(`${e.surname} ${e.given_names} ${e.matriculation_number || ""}`),
          }));
    return [
      ...actionEntries.filter(match),
      ...pageEntries.filter(match),
      ...employeeEntries.filter(match).slice(0, 6),
    ];
  }, [query, groups, actions, employees]);

  useEffect(() => setCursor(0), [query]);
  useEffect(() => {
    list.current?.querySelector('[data-active="true"]')?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  if (!open) return null;

  const go = (entry?: Entry) => {
    if (!entry) return;
    onClose();
    navigate(entry.path);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, entries.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(entries[cursor]);
    } else if (e.key === "Escape") {
      onClose();
    }
  };

  let lastSection = "";
  return (
    <div
      className="modal-overlay !items-start pt-[12vh]"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-label="Search"
    >
      <div className="modal-box max-w-xl overflow-hidden" onKeyDown={onKeyDown}>
        <label className="flex items-center gap-3 border-b px-4" style={{ borderColor: "var(--border-color)" }}>
          <SearchIcon className="size-5 shrink-0 fill-current text-muted-c" />
          <input
            ref={input}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={canSeeEmployees ? "Search a screen, a task or an employee…" : "Search a screen or a task…"}
            className="h-13 w-full !border-0 !bg-transparent text-sm text-primary-c !shadow-none !outline-none !ring-0 placeholder:text-(--text-muted)"
            aria-label="Search"
          />
          <span className="kbd">Esc</span>
        </label>
        <div ref={list} className="custom-scrollbar max-h-[52vh] overflow-y-auto p-2">
          {entries.length === 0 && (
            <p className="px-3 py-8 text-center text-sm text-muted-c">
              Nothing matches “{query}”. Try another word, e.g. “leave” or “payslip”.
            </p>
          )}
          {entries.map((entry, index) => {
            const header = entry.section !== lastSection ? entry.section : null;
            lastSection = entry.section;
            return (
              <div key={entry.id}>
                {header && <p className="section-label px-3 pb-1 pt-3">{header}</p>}
                <button
                  type="button"
                  className="menu-row"
                  data-active={index === cursor}
                  onMouseEnter={() => setCursor(index)}
                  onClick={() => go(entry)}
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-secondary-c" style={{ background: "var(--surface-3)" }}>
                    {entry.icon}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold">{entry.label}</span>
                    {entry.hint && <span className="block truncate text-xs text-muted-c">{entry.hint}</span>}
                  </span>
                  {index === cursor && <ArrowRightIcon className="size-4 fill-current text-muted-c" />}
                </button>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 border-t px-4 py-2.5 text-xs text-muted-c" style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}>
          <span className="flex items-center gap-1.5">
            <span className="kbd">↑</span>
            <span className="kbd">↓</span> to move
          </span>
          <span className="flex items-center gap-1.5">
            <span className="kbd">Enter</span> to open
          </span>
        </div>
      </div>
    </div>
  );
}
