import React from "react";
import Logo from "@/components/brand/Logo";
import ThemeTogglerTwo from "@/components/common/ThemeTogglerTwo";
import { CheckLineIcon } from "@/icons";

const HIGHLIGHTS = [
  ["Employee records & contracts", "One reliable file for every employee, with its full history."],
  ["Time, leave & planning", "Attendance, balances and timetables always up to date."],
  ["Payroll & accounting", "Payslips, declarations and accounting entries without re-typing."],
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative z-1 min-h-screen" style={{ background: "var(--surface)" }}>
      <div className="relative flex min-h-screen w-full flex-col lg:flex-row">
        {/* Brand panel: warm tint in light mode, navy in dark mode; orange and red of the logo as accents. */}
        <div className="auth-panel relative hidden w-[46%] overflow-hidden lg:flex">
          <span className="absolute -end-28 -top-28 h-80 w-80 rounded-full border-[44px] border-brand-500/90" aria-hidden="true" />
          <span className="absolute -bottom-28 -end-20 h-64 w-64 rounded-full bg-accent-500" aria-hidden="true" />
          <span className="absolute bottom-28 end-36 h-14 w-14 rounded-full bg-brand-400" aria-hidden="true" />
          <div className="relative z-1 flex w-full flex-col justify-between p-12 xl:p-16">
            <Logo size={52} />
            <div className="max-w-md">
              <h2 className="text-4xl font-bold leading-[1.15] tracking-tight">
                Every HR process,
                <br />
                <span className="text-brand-600 dark:text-brand-400">from hiring to payroll.</span>
              </h2>
              <ul className="mt-10 space-y-5">
                {HIGHLIGHTS.map(([title, text]) => (
                  <li key={title} className="flex gap-3.5">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-500 text-white">
                      <CheckLineIcon className="size-3.5" />
                    </span>
                    <span>
                      <span className="block text-[15px] font-semibold">{title}</span>
                      <span className="auth-panel-muted mt-0.5 block text-sm">{text}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <p className="auth-panel-muted text-xs">Institut Universitaire Saint Jean · Human Resources</p>
          </div>
        </div>

        <div className="flex flex-1 flex-col px-6 py-8 sm:px-10">
          <div className="lg:hidden">
            <Logo size={44} />
          </div>
          {children}
          <p className="mt-6 text-center text-xs text-muted-c">
            © {new Date().getFullYear()} Institut Universitaire Saint Jean – HRMS
          </p>
        </div>

        <div className="fixed inset-e-6 bottom-6 z-50 hidden sm:block">
          <ThemeTogglerTwo />
        </div>
      </div>
    </div>
  );
}
