import React from "react";
import Logo, { LogoMark } from "@/components/brand/Logo";
import ThemeTogglerTwo from "@/components/common/ThemeTogglerTwo";

const HIGHLIGHTS = [
  ["Employee records & contracts", "One reliable file for every employee, with its full history."],
  ["Time, leave & planning", "Attendance, balances and timetables always up to date."],
  ["Payroll & OHADA", "Payslips, declarations and accounting entries without re-typing."],
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative z-1 min-h-screen" style={{ background: "var(--surface)" }}>
      <div className="relative flex min-h-screen w-full flex-col lg:flex-row">
        <div className="flex flex-1 flex-col px-6 py-8 sm:px-10">
          <div className="lg:hidden">
            <Logo size={40} />
          </div>
          {children}
          <p className="mt-6 text-center text-xs text-muted-c">
            © {new Date().getFullYear()} Institut Universitaire Saint Jean – HRMS
          </p>
        </div>

        <div className="relative hidden w-1/2 overflow-hidden lg:flex">
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(135deg, #2d1f29 0%, #4a2f42 35%, #714B67 62%, #00A09D 100%)" }}
          />
          <div className="absolute -end-24 -top-24 h-96 w-96 rounded-full bg-teal-400/20 blur-3xl" />
          <div className="absolute -bottom-32 -start-16 h-[28rem] w-[28rem] rounded-full bg-brand-300/20 blur-3xl" />
          <div className="absolute end-10 top-1/2 -translate-y-1/2 opacity-[0.07]">
            <LogoMark size={420} />
          </div>
          <div className="relative z-1 flex w-full flex-col justify-between p-12 text-white">
            <Logo tone="inverse" size={56} />
            <div className="max-w-md">
              <h2 className="text-3xl font-bold leading-tight">
                Every HR process,
                <br />
                <span className="text-teal-200">from hiring to payroll.</span>
              </h2>
              <ul className="mt-8 space-y-4">
                {HIGHLIGHTS.map(([title, text]) => (
                  <li key={title} className="flex gap-3">
                    <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-teal-400/30 text-xs text-teal-100">✓</span>
                    <span>
                      <span className="block text-sm font-semibold">{title}</span>
                      <span className="block text-sm text-white/70">{text}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <p className="text-xs text-white/50">Faculty of Science and Technology – Software Engineering</p>
          </div>
        </div>

        <div className="fixed inset-e-6 bottom-6 z-50 hidden sm:block">
          <ThemeTogglerTwo />
        </div>
      </div>
    </div>
  );
}
