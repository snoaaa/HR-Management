import { useRef, useState } from "react";
import { Link } from "react-router";
import { useAuth } from "@/context/AuthContext";
import { usePermissions } from "@/context/PermissionsContext";
import { useTheme } from "@/context/ThemeContext";
import { useClickOutside } from "@/hooks/useClickOutside";
import { BellAltIcon, ChevronDownIcon, LogoutIcon, MoonIcon, SunIcon, UserCircleIcon } from "@/icons";
import { roleLabel } from "@/layout/roles";

/** Account menu of the top bar. */
export default function UserDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { user, logout } = useAuth();
  const { role } = usePermissions();
  const { theme, toggleTheme } = useTheme();
  useClickOutside(ref, () => setOpen(false));

  const fullName = user ? (user.first_name || user.last_name ? `${user.first_name} ${user.last_name}`.trim() : user.username) : "User";
  const initials = fullName
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w.charAt(0))
    .join("");
  const close = () => setOpen(false);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2.5 rounded-xl py-1 ps-1 pe-2 transition-colors hover:bg-(--surface-3)"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="avatar h-9 w-9 text-xs">{initials || "U"}</span>
        <span className="hidden text-start leading-tight lg:block">
          <span className="block max-w-36 truncate text-[13px] font-semibold text-primary-c">{fullName}</span>
          <span className="block max-w-36 truncate text-[11px] text-muted-c">{roleLabel(role || user?.role)}</span>
        </span>
        <ChevronDownIcon className={`hidden size-4 text-muted-c transition-transform lg:block ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="menu-panel absolute end-0 z-99999 mt-2 w-64 p-2" role="menu">
          <div className="flex items-center gap-3 px-2.5 py-2">
            <span className="avatar h-10 w-10 text-sm">{initials || "U"}</span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold text-primary-c">{fullName}</span>
              <span className="block truncate text-xs text-muted-c">{user?.email || user?.username}</span>
            </span>
          </div>
          <div className="my-1.5 border-t" style={{ borderColor: "var(--border-color)" }} />
          <Link to="/profile" role="menuitem" className="menu-row" onClick={close}>
            <UserCircleIcon /> My profile & security
          </Link>
          <Link to="/notifications" role="menuitem" className="menu-row" onClick={close}>
            <BellAltIcon /> Notifications
          </Link>
          <button type="button" role="menuitem" className="menu-row" onClick={toggleTheme}>
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            {theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          </button>
          <div className="my-1.5 border-t" style={{ borderColor: "var(--border-color)" }} />
          <button
            type="button"
            role="menuitem"
            className="menu-row !text-error-600 dark:!text-error-400"
            onClick={() => {
              close();
              logout();
            }}
          >
            <LogoutIcon className="!text-current" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
