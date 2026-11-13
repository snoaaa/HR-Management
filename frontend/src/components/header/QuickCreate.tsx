import { useRef, useState } from "react";
import { Link } from "react-router";
import { useClickOutside } from "@/hooks/useClickOutside";
import { PlusIcon } from "@/icons";
import { useNavigation } from "@/layout/useNavigation";

/** "New" button of the top bar: the frequent tasks the user is allowed to start. */
export default function QuickCreate() {
  const { actions } = useNavigation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false));

  if (actions.length === 0) return null;

  return (
    <div className="relative" ref={ref}>
      <button type="button" className="btn-primary" onClick={() => setOpen((o) => !o)} aria-haspopup="menu" aria-expanded={open}>
        <PlusIcon className="size-4" />
        <span className="hidden sm:inline">New</span>
      </button>
      {open && (
        <div className="menu-panel absolute end-0 z-99999 mt-2 w-72 p-2" role="menu">
          <p className="section-label px-2.5 pb-1.5 pt-1">What do you want to do?</p>
          {actions.map((action) => (
            <Link key={action.name} to={action.path} role="menuitem" className="menu-row" onClick={() => setOpen(false)}>
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-brand-c" style={{ background: "var(--brand-soft)" }}>
                {action.icon}
              </span>
              <span className="min-w-0">
                <span className="block font-semibold">{action.name}</span>
                <span className="block truncate text-xs text-muted-c">{action.description}</span>
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
