import { useEffect } from "react";
import { Link, useLocation } from "react-router";
import Logo, { LogoMark } from "@/components/brand/Logo";
import { useAuth } from "@/context/AuthContext";
import { usePermissions } from "@/context/PermissionsContext";
import { useSidebar } from "@/context/SidebarContext";
import { cn } from "../utils";
import { NAVIGATION } from "./navigation";
import type { NavItem } from "./navigation";

const AppSidebar: React.FC = () => {
  const { isExpanded, isMobileOpen, isHovered, setIsHovered, setIsMobileOpen } = useSidebar();
  const location = useLocation();
  const { user } = useAuth();
  const perms = usePermissions();
  const open = isExpanded || isHovered || isMobileOpen;

  useEffect(() => {
    if (isMobileOpen) setIsMobileOpen(false);
  }, [location.pathname]);

  const visible = (item: NavItem) => {
    if (item.roles && !item.roles.includes(perms.role)) return false;
    if (item.module && !perms.can(item.module, item.action)) return false;
    if (item.needsEmployee && !perms.employee_id) return false;
    if (item.when)
      return item.when({
        can: perms.can,
        role: perms.role,
        isManager: perms.isManager,
        employeeId: perms.employee_id,
        canViewSalary: perms.can_view_salary,
      });
    return true;
  };

  const isActive = (path: string) =>
    path === "/" ? location.pathname === "/" : location.pathname === path || location.pathname.startsWith(`${path}/`);

  // The most specific matching path wins (e.g. /payroll/payslips over /payroll).
  const allPaths = NAVIGATION.flatMap((g) => g.items.map((i) => i.path));
  const activePath = allPaths.filter(isActive).sort((a, b) => b.length - a.length)[0];

  const groups = perms.loading ? [] : NAVIGATION.map((g) => ({ ...g, items: g.items.filter(visible) })).filter((g) => g.items.length);

  const userInitials = user
    ? ((user.first_name?.[0] || "") + (user.last_name?.[0] || user.username?.[0] || "")).toUpperCase()
    : "HR";

  return (
    <aside
      className={cn(
        "sidebar-shell fixed inset-s-0 top-0 z-50 flex h-screen flex-col px-4 text-white transition-all duration-300 ease-in-out xl:translate-x-0 xl:rtl:translate-x-0",
        open ? "w-72" : "w-20",
        isMobileOpen ? "translate-x-0" : "-translate-x-full rtl:translate-x-full",
      )}
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className={cn("flex items-center py-5", open ? "justify-start ps-1" : "justify-center")}>
        <Link to="/" aria-label="Home">
          {open ? <Logo tone="inverse" size={40} /> : <LogoMark size={36} />}
        </Link>
      </div>

      <nav className="no-scrollbar flex-1 overflow-y-auto pb-6">
        <div className="flex flex-col gap-5">
          {groups.map((group) => (
            <div key={group.label}>
              <h2 className={cn("sidebar-group mb-1.5", open ? "ps-3" : "text-center")}>
                {open ? group.label : "•••"}
              </h2>
              <ul className="flex flex-col gap-0.5">
                {group.items.map((item) => {
                  const isCurrent = item.path === activePath;
                  return (
                    <li key={item.path}>
                      <Link
                        to={item.path}
                        title={item.name}
                        className={cn(
                          "sidebar-link group",
                          isCurrent && "sidebar-link-active",
                          !open && "justify-center px-0",
                        )}
                      >
                        <span
                          className={cn(
                            "transition-colors",
                            isCurrent ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200",
                          )}
                        >
                          {item.icon}
                        </span>
                        {open && <span className="truncate text-xs font-medium">{item.name}</span>}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </nav>

      {user && (
        <div className={cn("mb-4 border-t border-white/10 pt-3", open ? "px-1" : "flex justify-center")}>
          {open ? (
            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-2.5 backdrop-blur-xs">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-xs font-bold text-white shadow-xs">
                {userInitials}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-white">
                  {user.first_name || user.last_name ? `${user.first_name} ${user.last_name}` : user.username}
                </p>
                <p className="truncate text-[11px] font-medium text-indigo-300">
                  {perms.role.replace(/_/g, " ").toLowerCase()}
                </p>
              </div>
            </div>
          ) : (
            <div
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-xs font-bold text-white shadow-xs"
              title={`${user.username} (${perms.role})`}
            >
              {userInitials}
            </div>
          )}
        </div>
      )}
    </aside>
  );
};

export default AppSidebar;
