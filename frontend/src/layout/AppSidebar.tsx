import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router";
import api from "@/api/axiosConfig";
import { asList } from "@/api/helpers";
import Logo, { LogoMark } from "@/components/brand/Logo";
import { useAuth } from "@/context/AuthContext";
import { usePermissions } from "@/context/PermissionsContext";
import { useSidebar } from "@/context/SidebarContext";
import { ChevronDownIcon } from "@/icons";
import { cn } from "../utils";
import { roleLabel } from "./roles";
import { useNavigation } from "./useNavigation";

const COLLAPSED_KEY = "hrms.sidebar.collapsed-groups";

function readCollapsed(): string[] {
  try {
    return JSON.parse(localStorage.getItem(COLLAPSED_KEY) || "[]");
  } catch {
    return [];
  }
}

const AppSidebar: React.FC = () => {
  const { isExpanded, isMobileOpen, isHovered, setIsHovered, setIsMobileOpen } = useSidebar();
  const location = useLocation();
  const { user } = useAuth();
  const perms = usePermissions();
  const { groups, activeItem, activeGroup } = useNavigation();
  const open = isExpanded || isHovered || isMobileOpen;
  const [collapsed, setCollapsed] = useState<string[]>(readCollapsed);
  const [pending, setPending] = useState(0);

  useEffect(() => {
    if (isMobileOpen) setIsMobileOpen(false);
  }, [location.pathname]);

  // Number of requests waiting for a decision, shown next to "Approvals".
  useEffect(() => {
    if (!user) return;
    api
      .get("notifications/approvals/")
      .then((res) => setPending(asList(res.data).length))
      .catch(() => setPending(0));
  }, [user, location.pathname]);

  const toggleGroup = (label: string) => {
    setCollapsed((prev) => {
      const next = prev.includes(label) ? prev.filter((l) => l !== label) : [...prev, label];
      localStorage.setItem(COLLAPSED_KEY, JSON.stringify(next));
      return next;
    });
  };

  const fullName = user ? (user.first_name || user.last_name ? `${user.first_name} ${user.last_name}`.trim() : user.username) : "";
  const initials = fullName
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w.charAt(0))
    .join("");

  return (
    <aside
      className={cn(
        "sidebar-shell fixed inset-s-0 top-0 z-50 flex h-screen flex-col transition-all duration-300 ease-in-out xl:translate-x-0 xl:rtl:translate-x-0",
        open ? "w-72.5" : "w-22.5",
        isMobileOpen ? "translate-x-0" : "-translate-x-full rtl:translate-x-full",
      )}
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      aria-label="Main menu"
    >
      <div className={cn("flex h-[68px] shrink-0 items-center border-b", open ? "px-5" : "justify-center")} style={{ borderColor: "var(--border-color)" }}>
        <Link to="/" aria-label="Back to the dashboard">
          {open ? <Logo size={40} /> : <LogoMark size={40} />}
        </Link>
      </div>

      <nav className="no-scrollbar flex-1 overflow-y-auto px-3 py-4">
        <div className="flex flex-col gap-4">
          {groups.map((group, index) => {
            const isCollapsed = open && collapsed.includes(group.label) && group !== activeGroup;
            return (
              <div key={group.label}>
                {open ? (
                  index === 0 ? null : (
                    <button
                      type="button"
                      onClick={() => toggleGroup(group.label)}
                      className="sidebar-group mb-1.5 flex w-full items-center justify-between rounded-md px-3 py-1 hover:text-(--text-primary)"
                      aria-expanded={!isCollapsed}
                    >
                      {group.label}
                      <ChevronDownIcon className={cn("size-3.5 transition-transform", isCollapsed && "-rotate-90")} />
                    </button>
                  )
                ) : (
                  index > 0 && <div className="mx-auto mb-3 h-px w-8" style={{ background: "var(--border-color)" }} />
                )}
                {!isCollapsed && (
                  <ul className="flex flex-col gap-0.5">
                    {group.items.map((item) => {
                      const active = item === activeItem;
                      const count = item.path === "/approvals" ? pending : 0;
                      return (
                        <li key={item.path}>
                          <Link
                            to={item.path}
                            title={open ? undefined : item.name}
                            aria-current={active ? "page" : undefined}
                            className={cn("sidebar-link", active && "sidebar-link-active", !open && "justify-center px-0")}
                          >
                            <span className="relative shrink-0">
                              {item.icon}
                              {!open && count > 0 && <span className="absolute -end-1 -top-1 h-2 w-2 rounded-full bg-brand-500 ring-2 ring-(--surface)" />}
                            </span>
                            {open && <span className="truncate">{item.name}</span>}
                            {open && count > 0 && <span className="sidebar-count">{count > 99 ? "99+" : count}</span>}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      </nav>

      {user && (
        <Link
          to="/profile"
          title="My profile"
          className={cn(
            "flex shrink-0 items-center gap-3 border-t transition-colors hover:bg-(--surface-3)",
            open ? "px-5 py-3.5" : "justify-center py-3.5",
          )}
          style={{ borderColor: "var(--border-color)" }}
        >
          <span className="avatar h-9 w-9 text-xs">{initials || "U"}</span>
          {open && (
            <span className="min-w-0">
              <span className="block truncate text-[13px] font-semibold text-primary-c">{fullName}</span>
              <span className="block truncate text-[11px] text-muted-c">{roleLabel(perms.role)}</span>
            </span>
          )}
        </Link>
      )}
    </aside>
  );
};

export default AppSidebar;
