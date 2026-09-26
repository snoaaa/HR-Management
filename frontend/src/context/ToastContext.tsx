import React, { createContext, useContext, useState, ReactNode, useEffect } from "react";

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
    }, 4000);
    
    return () => {
      clearTimeout(progressTimer);
      clearTimeout(timer);
    };
  }, [toast.id, remove]);

  const typeConfig = {
    success: { icon: "✓", bg: "bg-success-500", text: "text-success-700", ring: "ring-success-500/20" },
    error: { icon: "✕", bg: "bg-error-500", text: "text-error-700", ring: "ring-error-500/20" },
    warning: { icon: "⚠", bg: "bg-warning-500", text: "text-warning-700", ring: "ring-warning-500/20" },
    info: { icon: "ℹ", bg: "bg-brand-500", text: "text-brand-700", ring: "ring-brand-500/20" },
  };

  const config = typeConfig[toast.type];

  return (
    <div
      className={`relative overflow-hidden flex items-center gap-3 w-80 max-w-[calc(100vw-32px)] 
      rounded-2xl p-4 shadow-2xl ring-1 ${config.ring} 
      bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl transition-all duration-300 ease-out`}
    >
      <div className={`flex items-center justify-center w-8 h-8 rounded-full ${config.bg} text-white font-bold shadow-md`}>
        {config.icon}
      </div>
      <p className="flex-1 text-sm font-medium text-gray-800 dark:text-white/90 pr-4">
        {toast.message}
      </p>
      <button
        onClick={() => remove(toast.id)}
        className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
      >
        <span className="sr-only">Close</span>
        ✕
      </button>
      <div className="absolute bottom-0 left-0 h-1 bg-gray-100 dark:bg-gray-800 w-full">
        <div 
          className={`h-full ${config.bg}`} 
          style={{ width: `${progress}%`, transition: "width 3950ms linear" }}
        />
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
      <div className="fixed bottom-6 right-6 z-[999999] flex flex-col gap-4 pointer-events-none">
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
