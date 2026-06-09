import type { CSSProperties, ReactNode } from "react";

/*
 * Stroked line icons — Blue Pulse style (1.8 stroke, round caps).
 * Ported from the design handoff's icons.jsx. Color flows via currentColor.
 *   <Icon name="graph" size={20} />
 */
const ICON_PATHS: Record<string, ReactNode> = {
  table: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18M3 14h18M9 4v16M15 4v16" />
    </>
  ),
  graph: (
    <>
      <circle cx="6" cy="7" r="2.4" />
      <circle cx="18" cy="6" r="2.4" />
      <circle cx="17" cy="17" r="2.4" />
      <circle cx="7" cy="17" r="2.4" />
      <path d="M8.1 8.1l7.8 7.8M8.2 6.6 15.7 6M7 9.4v5.2M16.6 8.2 8.4 15.6" />
    </>
  ),
  categories: (
    <>
      <rect x="3.5" y="4" width="7" height="7" rx="1.6" />
      <rect x="13.5" y="4" width="7" height="7" rx="1.6" />
      <rect x="3.5" y="13.5" width="7" height="6.5" rx="1.6" />
      <rect x="13.5" y="13.5" width="7" height="6.5" rx="1.6" />
    </>
  ),
  vector: (
    <>
      <rect x="2.5" y="9" width="3.4" height="6" rx="1" />
      <rect x="7.3" y="9" width="3.4" height="6" rx="1" />
      <rect x="12.1" y="9" width="3.4" height="6" rx="1" />
      <rect x="16.9" y="9" width="3.4" height="6" rx="1" />
    </>
  ),
  core: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="3.4" />
    </>
  ),
  layers: (
    <>
      <path d="M12 3 3 8l9 5 9-5-9-5Z" />
      <path d="M3 13l9 5 9-5M3 18l9 5 9-5" opacity=".5" />
    </>
  ),
  down: <path d="M12 5v14M6 13l6 6 6-6" />,
  up: <path d="M12 19V5M6 11l6-6 6 6" />,
  arrowRight: <path d="M5 12h14M13 6l6 6-6 6" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.2-3.2" />
    </>
  ),
  export: (
    <>
      <path d="M12 3v12M8 7l4-4 4 4" />
      <path d="M5 14v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5" />
    </>
  ),
  reset: (
    <>
      <path d="M3 12a9 9 0 1 0 3-6.7" />
      <path d="M3 4v4h4" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </>
  ),
  intent: (
    <>
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
      <circle cx="12" cy="12" r="3.2" />
    </>
  ),
  verified: (
    <>
      <path d="m9 12 2 2 4-4" />
      <path d="M12 2.5 14.3 5l3.4-.3.3 3.4L20.5 10.5 19 13.5l1.5 3-2.5 1.4-.3 3.4-3.4-.3L12 23.5l-2.3-2.5-3.4.3-.3-3.4L3.5 16.5 5 13.5 3.5 10.5 6 9.1l.3-3.4 3.4.3Z" />
    </>
  ),
  check: <path d="m5 12 5 5L20 6" />,
  chevDown: <path d="m6 9 6 6 6-6" />,
  chevUp: <path d="m6 15 6-6 6 6" />,
  sliders: (
    <>
      <path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h7M15 18h5" />
      <circle cx="16" cy="6" r="2" />
      <circle cx="8" cy="12" r="2" />
      <circle cx="13" cy="18" r="2" />
    </>
  ),
  spark: (
    <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" />
  ),
  dataset: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18" />
      <circle cx="6.5" cy="6.5" r=".7" fill="currentColor" stroke="none" />
      <circle cx="9" cy="6.5" r=".7" fill="currentColor" stroke="none" />
    </>
  ),
  dot: <circle cx="12" cy="12" r="4" fill="currentColor" stroke="none" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  grip: <path d="M9 6v12M15 6v12" />,
  moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />,
};

export type IconName = keyof typeof ICON_PATHS;

export function Icon({
  name,
  size = 20,
  stroke = 1.8,
  className,
  style,
}: {
  name: string;
  size?: number;
  stroke?: number;
  className?: string;
  style?: CSSProperties;
}) {
  const p = ICON_PATHS[name] ?? ICON_PATHS.dot;
  return (
    <svg
      className={className}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {p}
    </svg>
  );
}
