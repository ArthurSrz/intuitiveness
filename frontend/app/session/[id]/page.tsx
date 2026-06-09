"use client";

import Link from "next/link";
import { use } from "react";
import { useNode, useSession, useTree } from "@/lib/api/hooks";
import { ApiError } from "@/lib/api/client";
import { LevelView } from "@/components/levels/LevelView";
import { LevelRail } from "@/components/nav/LevelRail";
import { BranchTreeProvider } from "@/components/nav/BranchTree";
import { SessionActions } from "@/components/SessionActions";
import { StatusBadge } from "@/components/StatusBadge";

/*
 * Session workspace: level rail (left), current level view (center),
 * branch tree (right), plus export/import + health badge in the header.
 */
export default function SessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const session = useSession(id);
  const tree = useTree(id);
  const node = useNode(id, session.data?.current_node_id);

  if (session.isError) {
    const err = session.error as ApiError;
    return (
      <Shell>
        <p className="rounded-md border border-border bg-surface px-4 py-3 text-sm text-danger">
          Could not load session: {err.displayMessage}
        </p>
      </Shell>
    );
  }

  return (
    <Shell>
      <header className="mb-6 flex items-center justify-between gap-4">
        <div>
          <Link href="/" className="text-xs text-fg-muted hover:text-primary">
            ← All sessions
          </Link>
          <h1 className="mt-1 text-xl font-semibold text-fg">
            Session{" "}
            <span className="font-mono text-base text-fg-muted">{id}</span>
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <SessionActions sessionId={id} />
          <StatusBadge />
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[260px_1fr_300px]">
        {/* Left: level rail + edge forms. */}
        <div>
          {session.data ? (
            <LevelRail session={session.data} />
          ) : (
            <Placeholder>Loading levels…</Placeholder>
          )}
        </div>

        {/* Center: current level view. */}
        <div>
          {node.isLoading ? (
            <Placeholder>Loading current level…</Placeholder>
          ) : (
            <LevelView
              node={node.data}
              level={session.data?.current_level}
            />
          )}
        </div>

        {/* Right: branch tree. */}
        <div>
          {tree.data ? (
            <BranchTreeProvider sessionId={id} tree={normalizeTree(tree.data)} />
          ) : (
            <Placeholder>Loading tree…</Placeholder>
          )}
        </div>
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5 text-sm text-fg-muted shadow-sm">
      {children}
    </div>
  );
}

/*
 * The /tree endpoint is typed as an open object in the contract; normalize it
 * to the TreeResponse shape the BranchTree expects (defaults guard against a
 * missing nodes array).
 */
import type { TreeResponse } from "@/lib/api/types";
function normalizeTree(raw: unknown): TreeResponse {
  const r = (raw ?? {}) as Partial<TreeResponse>;
  return {
    root_id: r.root_id ?? "",
    current_id: r.current_id ?? "",
    nodes: Array.isArray(r.nodes) ? r.nodes : [],
  };
}
