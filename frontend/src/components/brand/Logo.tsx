/**
 * Brand of the application: "Saint Jean HRMS".
 * The emblem is the official logo (public/brand/logo-mark.png): three people
 * in orange, navy and red above the letters "HR". The interface takes its
 * colours from it – orange for actions, navy for structure, red as accent.
 */
export function LogoMark({ size = 40, className = "" }: { size?: number; className?: string }) {
  return (
    <img
      src="/brand/logo-mark.png"
      width={size}
      height={size}
      alt="Saint Jean HRMS"
      className={`shrink-0 select-none ${className}`}
      style={{ borderRadius: "23.5%" }}
      draggable={false}
    />
  );
}

interface LogoProps {
  variant?: "full" | "mark";
  /** "auto" follows the dark mode of the application; "inverse" is for navy surfaces. */
  tone?: "light" | "dark" | "auto" | "inverse";
  size?: number;
  className?: string;
  subtitle?: boolean;
}

/** Emblem + wordmark lockup. */
export default function Logo({ variant = "full", tone = "auto", size = 40, className = "", subtitle = false }: LogoProps) {
  if (variant === "mark") return <LogoMark size={size} className={className} />;
  const onDark = tone === "inverse" || tone === "dark";
  const title = onDark ? "text-white" : tone === "light" ? "text-gray-900" : "text-gray-900 dark:text-white";
  const sub = onDark ? "text-white/60" : tone === "light" ? "text-gray-500" : "text-gray-500 dark:text-gray-400";
  return (
    <span className={`inline-flex items-center gap-3 ${className}`}>
      <LogoMark size={size} />
      <span className="flex flex-col leading-none">
        <span className={`text-[10px] font-bold uppercase tracking-[0.2em] ${sub}`}>Saint Jean</span>
        <span className={`mt-1 text-[21px] font-extrabold tracking-tight ${title}`}>
          HR<span className="text-brand-500">MS</span>
        </span>
        {subtitle && <span className={`mt-1 text-[10px] font-medium ${sub}`}>Human Resources Suite</span>}
      </span>
    </span>
  );
}
