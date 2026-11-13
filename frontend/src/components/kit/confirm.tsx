import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { AlertIcon } from "@/icons";
import { Modal } from "./ui";

export interface ConfirmOptions {
  title: string;
  message?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Red confirm button for actions that delete or cannot be undone. */
  danger?: boolean;
}

interface Pending extends ConfirmOptions {
  resolve: (ok: boolean) => void;
}

let show: ((pending: Pending) => void) | null = null;

/**
 * Ask the user to confirm an action in a dialog of the application
 * (replaces the browser pop-up). Resolves to true when confirmed.
 */
export function confirmDialog(options: ConfirmOptions): Promise<boolean> {
  if (!show) return Promise.resolve(window.confirm(options.title));
  return new Promise((resolve) => show?.({ ...options, resolve }));
}

/** Mounted once at the root of the application. */
export function ConfirmHost() {
  const [pending, setPending] = useState<Pending | null>(null);

  useEffect(() => {
    show = setPending;
    return () => {
      show = null;
    };
  }, []);

  const answer = (ok: boolean) => {
    pending?.resolve(ok);
    setPending(null);
  };

  return (
    <Modal
      open={!!pending}
      title={pending?.title || ""}
      onClose={() => answer(false)}
      size="sm"
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={() => answer(false)}>
            {pending?.cancelLabel || "Cancel"}
          </button>
          <button type="button" className={pending?.danger ? "btn-danger" : "btn-primary"} onClick={() => answer(true)} autoFocus>
            {pending?.confirmLabel || "Confirm"}
          </button>
        </>
      }
    >
      <div className="flex items-start gap-3">
        {pending?.danger && (
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-error-50 dark:bg-error-500/15">
            <AlertIcon className="size-5" />
          </span>
        )}
        <p className="text-sm leading-relaxed text-secondary-c">{pending?.message || "Please confirm that you want to continue."}</p>
      </div>
    </Modal>
  );
}
