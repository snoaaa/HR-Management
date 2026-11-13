import React, { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextType {
  addToast: (message: string, type: ToastType) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

let toastIdCount = 0;

const ToastItem = ({ toast, remove }: { toast: Toast; remove: (id: number) => void }) => {
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    // Start depleting progress on mount
    const progressTimer = setTimeout(() => {
      setProgress(0);
    }, 50);

    const timer = setTimeout(() => {
      remove(toast.id);
    }, 5000);
    
    return () => {
      clearTimeout(progressTimer);
      clearTimeout(timer);
    };
  }, [toast.id, remove]);

  const typeConfig = {
    success: { icon: "✓", bg: "bg-success-600", label: "Done" },
    error: { icon: "!", bg: "bg-error-600", label: "Something went wrong" },
    warning: { icon: "!", bg: "bg-warning-500", label: "Please note" },
    info: { icon: "i", bg: "bg-blue-light-600", label: "Information" },
  };

  const config = typeConfig[toast.type];

  return (
    <div
      role={toast.type === "error" ? "alert" : "status"}
      className="menu-panel relative flex w-88 max-w-[calc(100vw-32px)] items-start gap-3 overflow-hidden p-4 pe-10"
      style={{ boxShadow: "var(--shadow-overlay)" }}
    >
      <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${config.bg} text-sm font-bold text-white`}>{config.icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-muted-c">{config.label}</p>
        <p className="mt-0.5 text-sm font-medium text-primary-c">{toast.message}</p>
      </div>
      <button onClick={() => remove(toast.id)} className="btn-icon absolute end-1.5 top-1.5" aria-label="Dismiss">
        ✕
      </button>
      <div className="absolute inset-x-0 bottom-0 h-0.5" style={{ background: "var(--surface-3)" }}>
        <div className={`h-full ${config.bg}`} style={{ width: `${progress}%`, transition: "width 4950ms linear" }} />
      </div>
    </div>
  );
};

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = (message: string, type: ToastType) => {
    setToasts((prev) => [...prev, { id: toastIdCount++, message, type }]);
  };

  const success = (message: string) => addToast(message, "success");
  const error = (message: string) => addToast(message, "error");
  const info = (message: string) => addToast(message, "info");
  const warning = (message: string) => addToast(message, "warning");

  const removeToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast, success, error, info, warning }}>
      {children}
      <div className="pointer-events-none fixed end-4 top-20 z-[999999] flex flex-col gap-3 sm:end-6" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} remove={removeToast} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
};
