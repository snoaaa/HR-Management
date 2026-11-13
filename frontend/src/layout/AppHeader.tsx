import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Menu, X, Search, Command } from "lucide-react";
import { LogoMark } from "@/components/brand/Logo";
import CommandPalette from "@/components/header/CommandPalette";
import HelpPanel from "@/components/header/HelpPanel";
import NotificationBell from "@/components/header/NotificationBell";
import QuickCreate from "@/components/header/QuickCreate";
import UserDropdown from "@/components/header/UserDropdown";
import CommandPalette from "@/components/common/CommandPalette";
import { useSidebar } from "@/context/SidebarContext";
import { useTheme } from "@/context/ThemeContext";
import { CloseIcon, MenuIcon, MoonIcon, SearchIcon, SunIcon } from "@/icons";
import { useNavigation } from "./useNavigation";

const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);

const AppHeader: React.FC = () => {
  const { isMobileOpen, toggleSidebar, toggleMobileSidebar } = useSidebar();
  const { theme, toggleTheme } = useTheme();
  const { activeItem, activeGroup } = useNavigation();
  const [searchOpen, setSearchOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  const handleToggle = () => {
    if (window.innerWidth >= 1280) toggleSidebar();
    else toggleMobileSidebar();
  };

  // Ctrl/⌘ + K opens the search from anywhere.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <header className="sticky top-0 z-40 flex h-[68px] w-full border-b" style={{ borderColor: "var(--border-color)", background: "var(--surface)" }}>
      <div className="flex w-full items-center gap-3 px-4 xl:px-6">
        <button type="button" className="topbar-btn shrink-0" onClick={handleToggle} aria-label={isMobileOpen ? "Close the menu" : "Open or collapse the menu"}>
          {isMobileOpen ? <CloseIcon className="size-5" /> : <MenuIcon className="size-5" />}
        </button>
        <Link to="/" className="shrink-0 xl:hidden" aria-label="Back to the dashboard">
          <LogoMark size={36} />
        </Link>

        {/* Where am I? */}
        <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-2 text-[13px] md:flex">
          {activeItem && activeGroup ? (
            <>
              <span className="truncate text-muted-c">{activeGroup.label}</span>
              <span className="text-muted-c" aria-hidden="true">/</span>
              <Link to={activeItem.path} className="truncate font-semibold text-primary-c hover:underline">
                {activeItem.name}
              </Link>
            </>
          ) : (
            <Link to="/" className="font-semibold text-primary-c hover:underline">
              Saint Jean HRMS
            </Link>
          )}
        </nav>

        <div className="ms-auto flex items-center gap-1.5 sm:gap-2">
          <button
            type="button"
            onClick={() => setSearchOpen(true)}
            className="hidden h-10 w-64 items-center gap-2.5 rounded-xl border px-3 text-[13px] text-muted-c transition-colors hover:border-(--border-strong) lg:flex"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
          >
            <SearchIcon className="size-4 fill-current" />
            <span className="flex-1 text-start">Search or jump to…</span>
            <span className="kbd">{isMac ? "⌘K" : "Ctrl K"}</span>
          </button>
          <button type="button" className="topbar-btn lg:hidden" onClick={() => setSearchOpen(true)} aria-label="Search">
            <SearchIcon className="size-5 fill-current" />
          </button>
          <QuickCreate />
          <span className="mx-1 hidden h-6 w-px sm:block" style={{ background: "var(--border-color)" }} />
          <button type="button" className="topbar-btn hidden sm:inline-flex" onClick={toggleTheme} aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"} title={theme === "dark" ? "Light mode" : "Dark mode"}>
            {theme === "dark" ? <SunIcon className="size-5" /> : <MoonIcon className="size-5" />}
          </button>
          <button type="button" className="topbar-btn hidden text-base font-bold sm:inline-flex" onClick={() => setHelpOpen(true)} aria-label="Help" title="Help">
            ?
          </button>
          <NotificationBell />
          <UserDropdown />
        </div>
      </div>
      <CommandPalette open={searchOpen} onClose={() => setSearchOpen(false)} />
      <HelpPanel open={helpOpen} onClose={() => setHelpOpen(false)} />
    </header>
  );
};

export default AppHeader;
