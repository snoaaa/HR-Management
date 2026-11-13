import { Link } from "react-router";
import Logo from "@/components/brand/Logo";
import PageMeta from "@/components/common/PageMeta";

export default function NotFound() {
  return (
    <>
      <PageMeta title="Page not found | Saint Jean HRMS" description="This page does not exist." />
      <div className="flex min-h-screen flex-col items-center justify-center p-6 text-center" style={{ background: "var(--surface)" }}>
        <Logo size={48} />
        <p className="mt-10 text-7xl font-extrabold tracking-tight text-brand-500">404</p>
        <h1 className="mt-3 text-2xl font-bold text-primary-c">We could not find this page</h1>
        <p className="mt-2 max-w-md text-sm text-secondary-c">
          The address may be wrong, or the page may have moved. Nothing is lost: go back to your dashboard and continue from there.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-2">
          <Link to="/" className="btn-primary btn-lg">
            Back to the dashboard
          </Link>
          <button type="button" className="btn-secondary btn-lg" onClick={() => window.history.back()}>
            Previous page
          </button>
        </div>
      </div>
    </>
  );
}
