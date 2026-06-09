import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "danger";

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-primary text-primary-fg hover:bg-primary-hover border-transparent",
  secondary:
    "bg-surface text-fg hover:bg-surface-muted border-border",
  danger:
    "bg-surface text-danger hover:bg-surface-muted border-border",
};

/** A tokens-only button. No hardcoded colors or sizes. */
export function Button({
  variant = "primary",
  children,
  className = "",
  ...props
}: {
  variant?: Variant;
  children: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={[
        "inline-flex items-center justify-center gap-2 rounded-md border px-4 py-2 text-sm font-medium",
        "transition-colors duration-fast ease-standard",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variantClasses[variant],
        className,
      ].join(" ")}
    >
      {children}
    </button>
  );
}
