import { useState, useEffect } from "react";
import { Link } from "react-router";
import { Menu, X, Search, Command } from "lucide-react";
import { LogoMark } from "@/components/brand/Logo";
import { ThemeToggleButton } from "@/components/common/ThemeToggleButton";
import NotificationBell from "@/components/header/NotificationBell";
import UserDropdown from "@/components/header/UserDropdown";
import CommandPalette from "@/components/common/CommandPalette";
import { useSidebar } from "@/context/SidebarContext";
import { usePermissions } from "@/context/PermissionsContext";

const ROLE_LABEL: Record<string, string> = {
  HR_MANAGER: "HR Manager",
  HR_OFFICER: "HR Officer",
  PAYROLL_OFFICER: "Payroll Officer",
  ACCOUNTANT: "Accountant",
  HEAD_OF_DEPARTMENT: "Head of Department",
  EMPLOYEE: "Employee",
  GENERAL_MANAGEMENT: "General Management",
  SYSTEM_ADMINISTRATOR: "System Administrator",
};

const AppHeader: React.FC = () => {
  const { isMobileOpen, toggleSidebar, toggleMobileSidebar } = useSidebar();
  const { role } = usePermissions();
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Shortcut Ctrl+K / Meta+K opens Command Palette
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleToggle = () => {
    if (window.innerWidth >= 1280) toggleSidebar();
    else toggleMobileSidebar();
  };

  const today = new Date().toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  return (
    <>
      <header
        className="sticky top-0 z-40 flex w-full border-b backdrop-blur-md transition-colors"
        style={{
          borderColor: "var(--border-color)",
          background: "color-mix(in srgb, var(--surface) 90%, transparent)",
        }}
      >
        <div className="flex w-full items-center justify-between gap-3 px-4 py-2.5 xl:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors"
              onClick={handleToggle}
              aria-label="Toggle navigation"
            >
              {isMobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>

            <Link to="/" className="xl:hidden" aria-label="Home">
              <LogoMark size={32} />
            </Link>

            {/* Quick Command Palette Search Bar */}
            <button
              type="button"
              onClick={() => setCommandPaletteOpen(true)}
              className="hidden sm:flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-1.5 text-xs text-slate-400 hover:border-slate-300 hover:bg-slate-100 hover:text-slate-600 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-400 dark:hover:border-slate-700 dark:hover:bg-slate-800 transition-all w-52 md:w-64"
            >
              <Search className="h-3.5 w-3.5 text-slate-400" />
              <span className="flex-1 text-left truncate">Quick search…</span>
              <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-semibold text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 shadow-2xs">
                <Command className="h-2.5 w-2.5" />K
              </kbd>
            </button>

            <div className="hidden lg:block pl-2 border-l border-slate-200 dark:border-slate-800">
              <p className="text-[11px] font-medium text-slate-400">{today}</p>
              {role && (
                <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 border border-indigo-200/80 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-950/40 dark:border-indigo-800 dark:text-indigo-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
                  {ROLE_LABEL[role] || role}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-2.5">
            <button
              type="button"
              onClick={() => setCommandPaletteOpen(true)}
              className="sm:hidden flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100 dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800"
              aria-label="Search"
            >
              <Search className="h-4 w-4" />
            </button>
            <ThemeToggleButton />
            <NotificationBell />
            <UserDropdown />
          </div>
        </div>
      </header>

      {/* Global Command Palette */}
      <CommandPalette open={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
    </>
  );
};

export default AppHeader;
