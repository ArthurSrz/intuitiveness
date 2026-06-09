"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useCreateSession } from "@/lib/api/hooks";
import { DEMO_SOURCES, type DemoSource } from "@/lib/api/types";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/StatusBadge";

/*
 * Landing page: pick a demo dataset, create a session, route to it.
 */
export default function HomePage() {
  const router = useRouter();
  const createSession = useCreateSession();
  const [source, setSource] = useState<DemoSource>(DEMO_SOURCES[0].id);

  function handleStart() {
    createSession.mutate(
      { source },
      {
        onSuccess: (state) => {
          router.push(`/session/${state.session_id}`);
        },
      },
    );
  }

  const error = createSession.error as ApiError | null;

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-8 px-4 py-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-fg">Intuitiveness</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Descend L4 → L0 and ascend back, one abstraction level at a time.
          </p>
        </div>
        <StatusBadge />
      </header>

      <section className="rounded-lg border border-border bg-surface p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-fg">Start a session</h2>
        <p className="mt-1 text-sm text-fg-muted">
          Pick a demo dataset to begin.
        </p>

        <div className="mt-5 grid gap-3">
          {DEMO_SOURCES.map((demo) => {
            const selected = demo.id === source;
            return (
              <button
                key={demo.id}
                type="button"
                onClick={() => setSource(demo.id)}
                className={[
                  "flex items-center justify-between rounded-md border px-4 py-3 text-left transition-colors duration-fast ease-standard",
                  selected
                    ? "border-primary bg-surface-muted"
                    : "border-border bg-surface hover:bg-surface-muted",
                ].join(" ")}
              >
                <span className="text-sm font-medium text-fg">
                  {demo.label}
                </span>
                <span className="font-mono text-xs text-fg-muted">
                  {demo.id}
                </span>
              </button>
            );
          })}
        </div>

        <Button
          onClick={handleStart}
          disabled={createSession.isPending}
          className="mt-6 w-full"
        >
          {createSession.isPending ? "Creating…" : "Start"}
        </Button>

        {error && (
          <p className="mt-3 text-xs text-danger">{error.displayMessage}</p>
        )}
      </section>
    </main>
  );
}
