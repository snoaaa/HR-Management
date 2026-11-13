import { useEffect } from "react";
import { Link } from "react-router";
import { ArrowRightIcon, CloseIcon } from "@/icons";
import { useNavigation } from "@/layout/useNavigation";

const COLOURS = [
  ["badge-green", "Approved", "Done, approved or active."],
  ["badge-yellow", "Pending", "Waiting for someone to decide."],
  ["badge-orange", "To review", "Needs a correction or your attention."],
  ["badge-red", "Refused", "Refused, absent or a problem."],
  ["badge-gray", "Draft", "Not sent yet, closed or archived."],
];

const TIPS = [
  ["Find anything", "Press Ctrl K (or click “Search or jump to…”) and type a word such as “leave”, “payslip” or a colleague’s name."],
  ["Sort and page through a list", "Click a column title to sort. Use Previous / Next under the list when it is long."],
  ["Download a list", "The PDF and Excel buttons above a list download exactly what is displayed, including your search."],
  ["Nothing is deleted by mistake", "Deleting, archiving or closing always asks you to confirm first."],
];

/** Side panel with plain-language help for everyday use. */
export default function HelpPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { actions } = useNavigation();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="modal-overlay !items-stretch !justify-end !p-0" role="dialog" aria-modal="true" aria-label="Help" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside className="animate-slide-right flex h-full w-full max-w-md flex-col overflow-hidden border-s" style={{ background: "var(--surface)", borderColor: "var(--border-color)" }}>
        <div className="flex items-center justify-between border-b px-6 py-4" style={{ borderColor: "var(--border-color)" }}>
          <div>
            <h2 className="text-lg font-bold text-primary-c">Help</h2>
            <p className="text-[13px] text-muted-c">The essentials, in a few lines.</p>
          </div>
          <button type="button" className="btn-icon" onClick={onClose} aria-label="Close the help">
            <CloseIcon className="size-5" />
          </button>
        </div>

        <div className="custom-scrollbar flex-1 space-y-7 overflow-y-auto px-6 py-5">
          {actions.length > 0 && (
            <section>
              <h3 className="mb-2 text-sm font-semibold text-primary-c">How do I…</h3>
              <ul className="space-y-1">
                {actions.map((action) => (
                  <li key={action.name}>
                    <Link to={action.path} onClick={onClose} className="menu-row">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-brand-c" style={{ background: "var(--brand-soft)" }}>
                        {action.icon}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block font-semibold">{action.name}</span>
                        <span className="block truncate text-xs text-muted-c">{action.description}</span>
                      </span>
                      <ArrowRightIcon className="size-4 fill-current text-muted-c rtl:rotate-180" />
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h3 className="mb-3 text-sm font-semibold text-primary-c">Good to know</h3>
            <ul className="space-y-3.5">
              {TIPS.map(([title, text]) => (
                <li key={title}>
                  <p className="text-sm font-semibold text-primary-c">{title}</p>
                  <p className="mt-0.5 text-[13px] leading-relaxed text-secondary-c">{text}</p>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h3 className="mb-3 text-sm font-semibold text-primary-c">What the colours mean</h3>
            <ul className="space-y-2.5">
              {COLOURS.map(([tone, label, text]) => (
                <li key={label} className="flex items-center gap-3 text-[13px] text-secondary-c">
                  <span className={`${tone} badge-dot w-24 shrink-0 justify-center`}>{label}</span>
                  {text}
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="border-t px-6 py-4 text-[13px] text-secondary-c" style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}>
          Still stuck, or is some information about you wrong? Contact your HR department: they can correct it or reset your password.
        </div>
      </aside>
    </div>
  );
}
