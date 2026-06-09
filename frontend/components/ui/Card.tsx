import type { ReactNode } from "react";

/** A tokens-only surface card with an optional heading. */
export function Card({
  title,
  subtitle,
  children,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-surface p-5 shadow-sm">
      {(title || subtitle) && (
        <header className="mb-4">
          {title && (
            <h2 className="text-lg font-semibold text-fg">{title}</h2>
          )}
          {subtitle && (
            <p className="mt-1 text-sm text-fg-muted">{subtitle}</p>
          )}
        </header>
      )}
      {children}
    </section>
  );
}
