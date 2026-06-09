"use client";

import { useMemo } from "react";
import type { TreeNode, TreeResponse } from "@/lib/api/types";
import { LEVEL_NAMES } from "@/lib/api/types";
import { usePrune, useTimeTravel } from "@/lib/api/hooks";
import { ApiError } from "@/lib/api/client";

/*
 * Renders the move tree from the flat `GET /tree` node list.
 * - Clicking a node time-travels the session's current pointer to it.
 * - Off-current nodes (not the current node, not root) get a prune button.
 *   Prune can 409 if the node is on the current branch; we surface that error.
 */
interface RenderNode extends TreeNode {
  children: RenderNode[];
}

/* Public entry point is <BranchTreeProvider> (below) — it binds the
 * session-scoped time-travel / prune mutations, then renders this inner tree. */
function BranchTreeInner({ tree }: { tree: TreeResponse }) {
  const roots = useMemo(() => buildForest(tree.nodes, tree.root_id), [tree]);
  return (
    <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-fg">Move tree</h3>
      <ul className="flex flex-col gap-1">
        {roots.map((n) => (
          <TreeRow
            key={n.id}
            node={n}
            depth={0}
            currentId={tree.current_id}
            rootId={tree.root_id}
          />
        ))}
      </ul>
    </div>
  );
}

function TreeRow({
  node,
  depth,
  currentId,
  rootId,
}: {
  node: RenderNode;
  depth: number;
  currentId: string;
  rootId: string;
}) {
  const isCurrent = node.id === currentId;
  const isRoot = node.id === rootId;

  return (
    <li>
      <div
        className={[
          "flex items-center gap-2 rounded-md px-2 py-1",
          isCurrent ? "bg-surface-muted" : "",
        ].join(" ")}
        style={{ paddingLeft: `calc(${depth} * var(--space-4))` }}
      >
        <span className={`inline-block h-2 w-2 rounded-full bg-level-${node.level}`} />
        <TreeNodeLabel node={node} isCurrent={isCurrent} />
        {!isCurrent && !isRoot && <PruneButton nodeId={node.id} />}
      </div>
      {node.children.length > 0 && (
        <ul className="flex flex-col gap-1">
          {node.children.map((c) => (
            <TreeRow
              key={c.id}
              node={c}
              depth={depth + 1}
              currentId={currentId}
              rootId={rootId}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function TreeNodeLabel({
  node,
  isCurrent,
}: {
  node: RenderNode;
  isCurrent: boolean;
}) {
  const ctx = useTreeContext();
  return (
    <button
      type="button"
      onClick={() => ctx.timeTravel.mutate(node.id)}
      disabled={isCurrent || ctx.timeTravel.isPending}
      className={[
        "flex-1 truncate text-left text-xs",
        isCurrent ? "font-semibold text-primary" : "text-fg hover:text-primary",
      ].join(" ")}
      title={node.decision_description ?? undefined}
    >
      L{node.level} · {node.level_name ?? LEVEL_NAMES[node.level]}
      {node.action ? ` · ${node.action}` : ""}
    </button>
  );
}

function PruneButton({ nodeId }: { nodeId: string }) {
  const ctx = useTreeContext();
  const error = ctx.prune.error as ApiError | null;
  const isThis = ctx.prune.variables === nodeId;
  return (
    <button
      type="button"
      onClick={() => ctx.prune.mutate(nodeId)}
      disabled={ctx.prune.isPending}
      className="rounded-sm px-2 py-0.5 text-xs text-danger hover:bg-surface-muted"
      title={
        isThis && error ? error.displayMessage : "Prune this node + subtree"
      }
    >
      prune
    </button>
  );
}

// ---- Forest building + context --------------------------------------------

function buildForest(nodes: TreeNode[], rootId: string): RenderNode[] {
  const byId = new Map<string, RenderNode>();
  for (const n of nodes) {
    byId.set(n.id, { ...n, children: [] });
  }
  const roots: RenderNode[] = [];
  for (const n of byId.values()) {
    if (n.parent_id && byId.has(n.parent_id)) {
      byId.get(n.parent_id)!.children.push(n);
    } else {
      roots.push(n);
    }
  }
  // Ensure the declared root sorts first if present.
  roots.sort((a, b) => (a.id === rootId ? -1 : b.id === rootId ? 1 : 0));
  return roots;
}

/*
 * The time-travel / prune mutations need the session id. Rather than thread it
 * through every row, the SessionPage wraps this subtree in a context provider.
 */
import { createContext, useContext } from "react";

interface TreeCtx {
  timeTravel: ReturnType<typeof useTimeTravel>;
  prune: ReturnType<typeof usePrune>;
}

const TreeContext = createContext<TreeCtx | null>(null);

function useTreeContext(): TreeCtx {
  const ctx = useContext(TreeContext);
  if (!ctx) {
    throw new Error("BranchTree must be used within <BranchTreeProvider>");
  }
  return ctx;
}

/** Binds the session-scoped mutations and renders the tree. */
export function BranchTreeProvider({
  sessionId,
  tree,
}: {
  sessionId: string;
  tree: TreeResponse;
}) {
  const timeTravel = useTimeTravel(sessionId);
  const prune = usePrune(sessionId);
  return (
    <TreeContext.Provider value={{ timeTravel, prune }}>
      <BranchTreeInner tree={tree} />
    </TreeContext.Provider>
  );
}
