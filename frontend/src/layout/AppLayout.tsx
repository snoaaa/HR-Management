import { useEffect, useState } from "react";
import { Outlet } from "react-router";
import { SidebarProvider, useSidebar } from "@/context/SidebarContext";
import { cn } from "@/utils";
import AppHeader from "./AppHeader";
import AppSidebar from "./AppSidebar";
import Backdrop from "./Backdrop";

/** True while the browser has no network connection. */
function useOffline() {
  const [offline, setOffline] = useState(typeof navigator !== "undefined" && !navigator.onLine);
  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  return offline;
}

const LayoutContent: React.FC = () => {
  const { isExpanded, isHovered, isMobileOpen } = useSidebar();
  const offline = useOffline();

  return (
    <div className="min-h-screen xl:flex">
      <a href="#main" className="btn-dark sr-only focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:z-999999">
        Skip to the content
      </a>
      <AppSidebar />
      <Backdrop />

      <div
        className={cn(
          "flex min-h-screen min-w-0 flex-1 flex-col transition-[margin] duration-300 ease-in-out",
          isExpanded || isHovered ? "xl:ms-72.5" : "xl:ms-22.5",
          isMobileOpen ? "ms-0" : "",
        )}
      >
        <AppHeader />
        {offline && (
          <div className="warning-banner !rounded-none !border-x-0 !border-t-0" role="status">
            You are offline. You can keep reading, but changes will not be saved until the connection is back.
          </div>
        )}
        <main id="main" className="mx-auto w-full max-w-(--breakpoint-2xl) flex-1 p-4 md:p-6 xl:p-8">
          <Outlet />
        </main>
        <footer className="mx-auto flex w-full max-w-(--breakpoint-2xl) flex-wrap items-center justify-between gap-2 px-4 pb-5 text-xs text-muted-c md:px-6 xl:px-8">
          <span>© {new Date().getFullYear()} Institut Universitaire Saint Jean · HRMS</span>
          <span>
            Press <span className="kbd">Ctrl K</span> to find any screen · click <span className="kbd">?</span> for help
          </span>
        </footer>
      </div>
    </div>
  );
};

const AppLayout: React.FC = () => {
  return (
    <SidebarProvider>
      <LayoutContent />
    </SidebarProvider>
  );
};

export default AppLayout;
