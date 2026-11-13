import { useMemo } from "react";
import { useLocation } from "react-router";
import { usePermissions } from "@/context/PermissionsContext";
import { NAVIGATION, QUICK_ACTIONS } from "./navigation";
import type { NavGroup, NavItem, NavRuleContext, QuickAction } from "./navigation";

/** Menu, quick actions and current location, filtered by the rights of the user. */
export function useNavigation() {
  const perms = usePermissions();
  const { pathname } = useLocation();

  const { groups, actions } = useMemo(() => {
    if (perms.loading) return { groups: [] as NavGroup[], actions: [] as QuickAction[] };
    const ctx: NavRuleContext = {
      can: perms.can,
      role: perms.role,
      isManager: perms.isManager,
      employeeId: perms.employee_id,
      canViewSalary: perms.can_view_salary,
    };
    const visible = (item: NavItem) => {
      if (item.roles && !item.roles.includes(perms.role)) return false;
      if (item.module && !perms.can(item.module, item.action)) return false;
      if (item.needsEmployee && !perms.employee_id) return false;
      return item.when ? item.when(ctx) : true;
    };
    return {
      groups: NAVIGATION.map((g) => ({ ...g, items: g.items.filter(visible) })).filter((g) => g.items.length),
      actions: QUICK_ACTIONS.filter((a) => (!a.needsEmployee || !!perms.employee_id) && (!a.when || a.when(ctx))),
    };
  }, [perms.loading, perms.can, perms.role, perms.isManager, perms.employee_id, perms.can_view_salary]);

  // The most specific matching path wins (e.g. /payroll/payslips over /payroll).
  const matches = (path: string) => (path === "/" ? pathname === "/" : pathname === path || pathname.startsWith(`${path}/`));
  let activeItem: NavItem | undefined;
  let activeGroup: NavGroup | undefined;
  for (const group of groups) {
    for (const item of group.items) {
      if (matches(item.path) && (!activeItem || item.path.length > activeItem.path.length)) {
        activeItem = item;
        activeGroup = group;
      }
    }
  }

  return { groups, actions, activeItem, activeGroup, loading: perms.loading };
}
