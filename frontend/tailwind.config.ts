import type { Config } from "tailwindcss";

/*
 * Every utility class the app uses is wired here to a CSS custom property
 * declared in styles/tokens.css. This is what makes SC-004 hold: components
 * reference theme utilities (bg-bg, text-fg, rounded-md, ...) and never raw
 * values, so editing a token restyles everything.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    // Replace (not extend) the palette so accidental hardcoded Tailwind
    // colors (e.g. `bg-blue-500`) are unavailable — only tokens compile.
    colors: {
      transparent: "transparent",
      current: "currentColor",
      bg: "var(--color-bg)",
      surface: "var(--color-surface)",
      "surface-muted": "var(--color-surface-muted)",
      border: "var(--color-border)",
      fg: "var(--color-fg)",
      "fg-muted": "var(--color-fg-muted)",
      primary: "var(--color-primary)",
      "primary-fg": "var(--color-primary-fg)",
      "primary-hover": "var(--color-primary-hover)",
      accent: "var(--color-accent)",
      success: "var(--color-success)",
      warning: "var(--color-warning)",
      danger: "var(--color-danger)",
      "level-4": "var(--color-level-4)",
      "level-3": "var(--color-level-3)",
      "level-2": "var(--color-level-2)",
      "level-1": "var(--color-level-1)",
      "level-0": "var(--color-level-0)",
    },
    fontFamily: {
      sans: "var(--font-sans)",
      mono: "var(--font-mono)",
    },
    fontSize: {
      xs: "var(--text-xs)",
      sm: "var(--text-sm)",
      base: "var(--text-base)",
      lg: "var(--text-lg)",
      xl: "var(--text-xl)",
      "2xl": "var(--text-2xl)",
      "3xl": "var(--text-3xl)",
      "4xl": "var(--text-4xl)",
    },
    spacing: {
      "0": "0",
      px: "1px",
      "1": "var(--space-1)",
      "2": "var(--space-2)",
      "3": "var(--space-3)",
      "4": "var(--space-4)",
      "5": "var(--space-5)",
      "6": "var(--space-6)",
      "8": "var(--space-8)",
    },
    borderRadius: {
      none: "0",
      sm: "var(--radius-sm)",
      md: "var(--radius-md)",
      lg: "var(--radius-lg)",
      full: "var(--radius-full)",
    },
    boxShadow: {
      none: "none",
      sm: "var(--shadow-sm)",
      md: "var(--shadow-md)",
    },
    extend: {
      transitionDuration: {
        fast: "var(--duration-fast)",
        base: "var(--duration-base)",
        slow: "var(--duration-slow)",
      },
      transitionTimingFunction: {
        standard: "var(--ease-standard)",
        emphasized: "var(--ease-emphasized)",
      },
    },
  },
  plugins: [],
};

export default config;
