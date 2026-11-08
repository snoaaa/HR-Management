import { Link } from "react-router";
import { LogoMark } from "@/components/brand/Logo";
import { ThemeToggleButton } from "@/components/common/ThemeToggleButton";
import NotificationBell from "@/components/header/NotificationBell";
import UserDropdown from "@/components/header/UserDropdown";
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

  const handleToggle = () => {
    if (window.innerWidth >= 1280) toggleSidebar();
    else toggleMobileSidebar();
  };

  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  return (
    <header
      className="sticky top-0 z-40 flex w-full border-b backdrop-blur-md"
      style={{ borderColor: "var(--border-color)", background: "color-mix(in srgb, var(--surface) 88%, transparent)" }}
    >
      <div className="flex w-full items-center justify-between gap-3 px-4 py-3 xl:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-100 dark:border-gray-800 dark:text-gray-400 dark:hover:bg-white/5"
            onClick={handleToggle}
            aria-label="Toggle the menu"
          >
            {isMobileOpen ? "✕" : "☰"}
          </button>
          <Link to="/" className="xl:hidden" aria-label="Home">
            <LogoMark size={34} />
          </Link>
          <div className="hidden md:block">
            <p className="text-xs text-muted-c">{today}</p>
            {role && <span className="badge-purple mt-0.5">{ROLE_LABEL[role] || role}</span>}
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <ThemeToggleButton />
          <NotificationBell />
          <UserDropdown />
        </div>
      </div>
    </header>
  );
};

export default AppHeader;
