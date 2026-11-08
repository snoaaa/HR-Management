import { useId } from "react";

/**
 * Brand of the application: "Saint Jean HRMS".
 * The emblem is a rounded hexagon (the organisation) with a purple → teal
 * gradient, three people forming an arc (the teams) and a rising teal swoosh
 * (careers and growth). Gloss and inner shadow give it depth.
 */
export function LogoMark({ size = 40, className = "" }: { size?: number; className?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={className}
      role="img"
      aria-label="Saint Jean HRMS"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id={`bg-${id}`} x1="8" y1="4" x2="58" y2="62" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#8a5a7e" />
          <stop offset="0.45" stopColor="#714B67" />
          <stop offset="1" stopColor="#00A09D" />
        </linearGradient>
        <linearGradient id={`rim-${id}`} x1="32" y1="2" x2="32" y2="62" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.55" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={`gloss-${id}`} x1="32" y1="4" x2="32" y2="34" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.35" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={`swoosh-${id}`} x1="10" y1="50" x2="56" y2="30" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#00D4CF" stopOpacity="0.15" />
          <stop offset="0.6" stopColor="#00D4CF" />
          <stop offset="1" stopColor="#7ff5f1" />
        </linearGradient>
        <radialGradient id={`glow-${id}`} cx="32" cy="30" r="22" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.22" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </radialGradient>
        <filter id={`shadow-${id}`} x="-20%" y="-20%" width="140%" height="150%">
          <feDropShadow dx="0" dy="2.2" stdDeviation="2" floodColor="#2d1f29" floodOpacity="0.35" />
        </filter>
        <filter id={`soft-${id}`} x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="1" stdDeviation="0.8" floodColor="#2d1f29" floodOpacity="0.35" />
        </filter>
      </defs>

      {/* Body: rounded hexagon */}
      <g filter={`url(#shadow-${id})`}>
        <path
          d="M32 3.5c1.6 0 3.1.4 4.5 1.2l17.6 10.2c2.8 1.6 4.5 4.6 4.5 7.8v19c0 3.2-1.7 6.2-4.5 7.8L36.5 59.7c-2.8 1.6-6.2 1.6-9 0L9.9 49.5C7.1 47.9 5.4 44.9 5.4 41.7v-19c0-3.2 1.7-6.2 4.5-7.8L27.5 4.7c1.4-.8 2.9-1.2 4.5-1.2z"
          fill={`url(#bg-${id})`}
        />
      </g>
      {/* Inner rim and gloss */}
      <path
        d="M32 6.2c1.2 0 2.4.3 3.4.9l17.1 9.9c2.1 1.2 3.4 3.5 3.4 5.9v18.5c0 2.4-1.3 4.7-3.4 5.9L35.4 57.2c-2.1 1.2-4.7 1.2-6.8 0L11.5 47.3c-2.1-1.2-3.4-3.5-3.4-5.9V22.9c0-2.4 1.3-4.7 3.4-5.9L28.6 7.1c1-.6 2.2-.9 3.4-.9z"
        fill="none"
        stroke={`url(#rim-${id})`}
        strokeWidth="1"
      />
      <path
        d="M11 20.5 29 10c1.9-1.1 4.2-1.1 6 0l18 10.5c.5 6.5-8 11.5-21 11.5S10.5 27 11 20.5z"
        fill={`url(#gloss-${id})`}
      />
      <circle cx="32" cy="30" r="22" fill={`url(#glow-${id})`} />

      {/* Growth swoosh */}
      <path
        d="M10.5 46c9 2.8 19.8 1.6 29.5-4.6 5.1-3.3 9.4-7.7 12.8-13.1l2.2 1.6c-3.1 6.6-7.8 12-13.6 15.6-10.2 6.4-21.9 6.8-30.9 2.5z"
        fill={`url(#swoosh-${id})`}
      />

      {/* People: the organisation */}
      <g filter={`url(#soft-${id})`}>
        <circle cx="19.5" cy="25.5" r="3.6" fill="#ffffff" fillOpacity="0.72" />
        <path d="M12.6 37.2c.5-4.3 3.4-7 6.9-7s6.4 2.7 6.9 7c-2.2.9-4.5 1.3-6.9 1.3s-4.7-.4-6.9-1.3z" fill="#ffffff" fillOpacity="0.72" />
        <circle cx="44.5" cy="25.5" r="3.6" fill="#ffffff" fillOpacity="0.72" />
        <path d="M37.6 37.2c.5-4.3 3.4-7 6.9-7s6.4 2.7 6.9 7c-2.2.9-4.5 1.3-6.9 1.3s-4.7-.4-6.9-1.3z" fill="#ffffff" fillOpacity="0.72" />
        <circle cx="32" cy="20.5" r="4.6" fill="#ffffff" />
        <path d="M23.2 35.6c.6-5.6 4.3-9.1 8.8-9.1s8.2 3.5 8.8 9.1c-2.8 1.2-5.8 1.8-8.8 1.8s-6-.6-8.8-1.8z" fill="#ffffff" />
      </g>
      {/* Link between the teams */}
      <path d="M19.5 40.8c3.6 2 8 3 12.5 3s8.9-1 12.5-3" fill="none" stroke="#ffffff" strokeOpacity="0.55" strokeWidth="1.2" strokeLinecap="round" />
      <circle cx="32" cy="43.8" r="1.5" fill="#00D4CF" />
    </svg>
  );
}

interface LogoProps {
  variant?: "full" | "mark";
  /** "auto" follows the dark mode of the application. */
  tone?: "light" | "dark" | "auto" | "inverse";
  size?: number;
  className?: string;
  subtitle?: boolean;
}

/** Emblem + wordmark lockup. */
export default function Logo({ variant = "full", tone = "auto", size = 40, className = "", subtitle = true }: LogoProps) {
  if (variant === "mark") return <LogoMark size={size} className={className} />;
  const onDark = tone === "inverse" || tone === "dark";
  const title = onDark ? "text-white" : tone === "light" ? "text-gray-900" : "text-gray-900 dark:text-white";
  const sub = onDark ? "text-teal-200" : tone === "light" ? "text-teal-500" : "text-teal-500 dark:text-teal-300";
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark size={size} />
      <span className="flex flex-col leading-none">
        <span className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${sub}`}>Saint Jean</span>
        <span className={`text-[20px] font-extrabold tracking-tight ${title}`}>
          HR<span className="bg-linear-to-r from-brand-300 to-teal-300 bg-clip-text text-transparent">MS</span>
        </span>
        {subtitle && (
          <span className={`mt-0.5 text-[9px] font-medium tracking-wide opacity-70 ${title}`}>Human Resources Suite</span>
        )}
      </span>
    </span>
  );
}
