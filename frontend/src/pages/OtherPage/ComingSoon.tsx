import { useLocation } from "react-router";
import PageMeta from "@/components/common/PageMeta";

/** Placeholder for the screens whose backend is ready but whose UI is planned next. */
export default function ComingSoon() {
  const { pathname } = useLocation();
  return (
    <>
      <PageMeta title="Coming soon | HR Management System" description="This screen is being built." />
      <div className="card p-10 text-center">
        <p className="section-label">In progress</p>
        <h1 className="page-title mt-2">This screen is coming soon</h1>
        <p className="mt-2 text-sm text-gray-500">
          The API behind <span className="mono">{pathname}</span> is available; its interface is planned for the next
          iteration.
        </p>
      </div>
    </>
  );
}
