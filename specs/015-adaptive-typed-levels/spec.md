# Feature Specification: Adaptive Typed Levels & Unified Redesign Engine

**Feature Branch**: `015-adaptive-typed-levels`
**Created**: 2026-06-07
**Status**: Draft
**Input**: User description: Refactor the intuitiveness package architecture to match the paper's §5.3 (Implementation: the Intuitiveness package), centered on adaptive typed data structures.

## Overview

The intuitiveness package implements the paper's descent–ascent methodology, where a dataset moves between five granularity levels (L4 raw → L0 atomic, and back up). Today the implementation has drifted from the architecture described in the paper's §5.3: only the atomic level remembers how it was produced, three different code paths perform level transitions, two competing structures record session history, branching is disabled by default, and exported sessions omit the actual data. This feature realigns the package with §5.3 so that **every artifact knows its own complete history, every transition passes through a single rule-enforcing gate, and a whole exploration can be exported as a complete, self-contained record** that a separate downstream service can consume.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every artifact carries its complete derivation history (Priority: P1)

A data practitioner navigating a dataset down and back up the granularity levels can, at **any** level, inspect a single artifact and see the complete chain of operations that produced it — from the original raw files to the artifact in hand — without consulting any external log. The same artifact can describe itself (what kind of thing it is, its size/shape) on demand.

**Why this priority**: This is the foundation of the paper's traceability claim and the prerequisite for every other story — branching, export, and downstream synthetic generation all depend on artifacts being self-describing. Without it, provenance is partial (only the atomic value remembers its origin) and the system cannot deliver "audit-grade provenance."

**Independent Test**: Perform a descent from raw data to an intermediate level, then request that artifact's history and self-summary. The history must list every step taken so far with its parameters; the summary must correctly characterize that level's structure. Delivers value as a standalone provenance-inspection capability.

**Acceptance Scenarios**:

1. **Given** a dataset that has descended from raw files through two intermediate levels, **When** the practitioner inspects the current artifact's history, **Then** the history lists every transition from the original raw files to the current artifact, each with the operation type, source and target levels, and the choices made.
2. **Given** an artifact at any of the five levels, **When** the practitioner requests its self-summary, **Then** the artifact returns a correct, level-appropriate description (e.g. a count of source files at the raw level, row/column shape at a table level, the scalar at the atomic level) with no external code inspecting its type.
3. **Given** two artifacts at the same level produced by different choices, **When** their histories are compared, **Then** each history is complete and independent of the other.

---

### User Story 2 - Branching exploration never corrupts sibling trajectories (Priority: P1)

A practitioner exploring "what-if" alternatives can return to any earlier decision point, take a different choice, and produce a sibling trajectory **alongside** the original. Making or extending one trajectory must never alter the history or data of any other trajectory, and the practitioner can travel back to any earlier point and find its full state intact.

**Why this priority**: The paper presents branching and decision-point time-travel as a headline capability that "flat one-shot pipelines cannot offer." It is currently disabled by default. Safe branching is also what makes the export useful to the downstream generator (multiple coherent views of the same data). It depends on Story 1 (artifacts carrying their own frozen history).

**Independent Test**: Build a trajectory to the atomic level, time-travel to an intermediate decision point, take a different choice to spawn a sibling branch, then re-inspect the original branch. The original branch's artifacts and histories must be unchanged. Delivers value as a standalone comparative-exploration capability.

**Acceptance Scenarios**:

1. **Given** a completed trajectory, **When** the practitioner time-travels to an earlier decision point, **Then** the artifact and full state at that point are restored exactly as they were when first created.
2. **Given** a restored decision point, **When** the practitioner takes a different choice to create a sibling branch, **Then** the new branch is recorded alongside the original and the original branch's artifacts and histories are unchanged.
3. **Given** a session with multiple branches, **When** the practitioner asks for the current linear path, **Then** the system returns the path of the active branch (branching is always available, never a mode that must be enabled).

---

### User Story 3 - Export a complete session as a self-contained cross-service record (Priority: P2)

A practitioner can export an entire exploration — every branch, every artifact's data and history, and the decisions that distinguish branches — as a single versioned record. A **separate** downstream service (e.g. synthetic data generation) can later load that record and access every artifact's data and derivation **without** needing the redesign application itself.

**Why this priority**: The persisted record is the contract between this package and a future synthetic-generation service. It must be complete (data, not just structure) and self-contained. It depends on Stories 1 and 2 (artifacts carry data + history; branches are independent). It is P2 because the redesign workflow is usable before the export contract is finalized, but the contract must be right before the downstream service is built.

**Independent Test**: Export a multi-branch session, then load it in a context that does **not** import the redesign application's internal types, and confirm that every artifact's data and full history are recoverable and that the format declares its version. Delivers value as a standalone interchange artifact.

**Acceptance Scenarios**:

1. **Given** a multi-branch session containing tables, graphs, vectors, and scalars, **When** it is exported, **Then** the export contains the actual data payload and full history for every node, plus the decisions on every branch edge, and declares a schema version.
2. **Given** an exported session, **When** it is loaded by a consumer that does not depend on the redesign application's internal classes, **Then** every artifact's data and history are reconstructable from the record alone.
3. **Given** a session whose branches share a common early prefix, **When** it is exported, **Then** the shared ancestors are stored once and referenced, not duplicated per branch.
4. **Given** the lightweight in-browser session index, **When** a session grows large, **Then** the index stays within the browser storage budget because it holds only a pointer/summary, not the payloads.

---

### User Story 4 - Every transition enforces the framework's rules, regardless of entry path (Priority: P2)

No matter how a level transition is triggered (guided Q&A workflow, direct API use, or programmatic navigation), the framework's rules are enforced identically: moves are only between adjacent levels, the raw level can only be an entry point (never a destination), upward reconstruction never invents or drops records, and a session that has left the raw level can never re-enter it.

**Why this priority**: Today the same rule is checked in up to three places (and one in a soon-to-be-removed record type), while branching/history logic is duplicated across two code paths. Consolidating rule-enforcement removes behavioral divergence between entry paths. It depends on the single-engine consolidation but is observable as consistent rule behavior.

**Independent Test**: Attempt each illegal move (skip a level, target the raw level on the way up, re-enter the raw level after leaving) through each available entry path and confirm identical rejection. Delivers value as consistent, predictable guard-rails.

**Acceptance Scenarios**:

1. **Given** an artifact at any level, **When** a transition is requested that skips a level, **Then** it is rejected with a clear adjacency error, identically across all entry paths.
2. **Given** an upward reconstruction step, **When** the step would change the number of records, **Then** it is rejected as violating record-count preservation.
3. **Given** a session that has descended below the raw level, **When** any re-entry to the raw level is attempted, **Then** it is refused as a session-path violation, while legitimate entry-at-raw-level for a new session is allowed.
4. **Given** an upward move, **When** the requested target is the raw level, **Then** no such transition exists to invoke (the raw level is structurally unreachable as a destination).

---

### User Story 5 - One transition engine, one history structure (Priority: P3)

A maintainer extending or debugging the redesign behavior finds a single place that performs transitions and a single structure that records session history, rather than three parallel transition implementations and two competing history representations.

**Why this priority**: This is primarily an internal-consistency and maintainability outcome. It is the enabling refactor behind Stories 1–4, but on its own it is lower user-visible priority. Capturing it ensures the consolidation is treated as an explicit, verifiable goal rather than an incidental side effect.

**Independent Test**: Trace any transition triggered from the guided workflow and confirm it flows through the same engine and produces the same history structure as a transition triggered programmatically. Delivers value as reduced surface area and eliminated duplicate code paths.

**Acceptance Scenarios**:

1. **Given** the guided Q&A workflow, **When** it performs a transition, **Then** the artifact and history it produces are indistinguishable from one produced by the direct engine for the same inputs.
2. **Given** the codebase after the refactor, **When** searching for code that constructs a level artifact and stamps its history, **Then** exactly one component is responsible for it.

---

### Edge Cases

- **Non-deterministic raw→graph step**: The raw-to-graph transition relies on a non-deterministic model-assisted step. The system MUST retain the actual produced artifact rather than expecting to re-derive it on demand, because replay would yield a different graph than the one the user navigated.
- **Large sessions**: When retained branches and payloads grow large, the system MUST offer an explicit, user-triggered way to prune or archive a branch, and MUST NOT silently drop or truncate retained data.
- **Mixed payload types in one export**: A single session can contain tables, graphs, vectors, and scalars across its nodes; the export MUST faithfully round-trip each payload type.
- **Empty or single-level session**: A session that entered at the raw level but performed no transitions MUST still export and reload as a valid (single-node) record.
- **Shared-ancestor reconstruction on load**: When loading a record whose branches reference shared ancestors, the reconstructed in-memory structure MUST re-link branches to the same ancestor nodes (no accidental divergence).
- **Comparing two branches**: A practitioner MUST be able to identify the decision point at which two trajectories diverge.

## Requirements *(mandatory)*

### Functional Requirements

#### Self-describing artifacts (Story 1)

- **FR-001**: Every level artifact (all five granularity levels) MUST carry the complete, ordered history of operations that produced it, from the original raw entry to itself.
- **FR-002**: Every level artifact MUST expose its history in a uniform way, identical in shape across all five levels (no level may be a special case that lacks history).
- **FR-003**: Every level artifact MUST be able to produce a correct, level-appropriate self-summary without any external component branching on the artifact's type.
- **FR-004**: Each recorded operation MUST capture at minimum: the operation/transition performed, the source and target levels, the choices/parameters applied, and a timestamp; and MAY optionally capture integrity fingerprints of its input and output for tamper detection.

#### Single canonical provenance record (Story 1, Story 5)

- **FR-005**: The system MUST use exactly one type of per-step provenance record, used for both downward and upward transitions; there MUST NOT be separate, parallel record types for the two directions.
- **FR-006**: Direction- or step-specific details (such as the reconstruction method or the analytic dimensions added) MUST be carried within the single record's general parameters rather than requiring a distinct record type.

#### Single transition engine / chokepoint (Story 4, Story 5)

- **FR-007**: The system MUST route all level transitions — regardless of entry path (guided workflow, direct API, programmatic navigation) — through a single transition engine.
- **FR-008**: Exactly one component MUST be responsible for constructing a new level artifact and stamping its history; no other component may construct level artifacts directly.
- **FR-009**: The transition engine MUST expose transitions through explicit, well-typed per-transition entry points with named, validated parameters; it MUST NOT require callers to inject transformation logic as opaque callbacks or untyped keyword bags.
- **FR-010**: The framework's transformation semantics (relationship discovery, domain categorization, enrichment, dimension classification, etc.) MUST remain first-class and reusable, operating on data payloads only, and MUST be invoked by — not duplicated inside — the transition engine.
- **FR-011**: The guided Q&A workflow MUST own no transition logic; it MUST collect user choices and delegate the actual transition to the single engine.

#### Safe lineage on transition (Story 2)

- **FR-012**: When a transition produces a child artifact, the child's history MUST be a copy of the parent's history extended by the new step, such that the child's history is independent of the parent's and of any sibling's.
- **FR-013**: Extending or branching one trajectory MUST NOT mutate the history or data of any other artifact or trajectory.

#### Transition-legality vs path-legality (Story 4)

- **FR-014**: The transition engine MUST enforce transition-legality using only the current artifact and requested step (stateless): adjacency (single-level moves only), structural impossibility of targeting the raw level on an upward move, and record-count preservation on upward moves.
- **FR-015**: The navigation session MUST enforce path-legality using session history (stateful): a session MUST begin only at the raw level, and once a session has departed the raw level it MUST NOT re-enter it.
- **FR-016**: Each rule MUST be enforced in exactly one place; the system MUST NOT check the same rule in multiple components.

#### One always-on history structure with branching (Story 2)

- **FR-017**: The system MUST record session history in a single branching structure that supports branching and time-travel at all times; branching MUST NOT be an optional mode that defaults to off.
- **FR-018**: The system MUST NOT maintain a second, parallel flat history representation; the linear path MUST be derived from the single branching structure.
- **FR-019**: Time-travel to any prior node MUST restore that node's full state (its artifact and history) exactly as originally created.

#### Full-payload nodes & generator-facing queries (Story 2, Story 3)

- **FR-020**: Every node in the history structure MUST retain the complete artifact (data payload, full history, and the decision/parameters on its incoming edge).
- **FR-021**: The history structure MUST provide queries needed by downstream consumers, including at minimum: enumerate all branches, list all nodes at a given level, list a node's siblings, and find the divergence point between two trajectories.
- **FR-022**: The system MUST provide an explicit, user-initiated operation to prune or archive a branch to manage memory, and MUST NOT silently discard retained data.

#### Full-fidelity, versioned, self-contained persistence (Story 3)

- **FR-023**: A session export MUST include the complete history structure with every node's data payload and history, and the decisions on every branch edge.
- **FR-024**: The export MUST faithfully round-trip every supported payload type (multi-table/graph structures, single tables, vectors, and scalars).
- **FR-025**: The export MUST declare a schema version and MUST be loadable by a consumer that does not import the redesign application's internal types.
- **FR-026**: The export MUST store each node once, keyed by identity, with parent references, so that branches sharing ancestors do not duplicate those ancestors.
- **FR-027**: The lightweight in-browser session index MUST hold only a pointer/summary (identity, title, location) so that it remains within the browser storage budget regardless of session size; full payloads MUST be stored via the durable backend, not the browser index.
- **FR-028**: Loading an exported record MUST reconstruct the in-memory branching structure, re-linking branches that share ancestors to the same nodes.

### Key Entities *(include if feature involves data)*

- **Level artifact**: A dataset at one of five granularity levels (raw multi-source, linked/graph, single table, vector, atomic scalar). After this feature, every level artifact uniformly carries its data payload, its full derivation history, and the ability to summarize itself. The five levels are symmetric in what they carry, differing only in payload shape.
- **Provenance step**: The single canonical record of one transition — operation performed, source and target levels, choices/parameters, timestamp, and optional integrity fingerprints. Used for both directions.
- **Derivation history**: The ordered chain of provenance steps from the original raw entry to a given artifact, carried denormalized inside that artifact.
- **Transition engine**: The single component that validates transition-legality, invokes the appropriate transformation semantics, constructs the resulting level artifact, and stamps its history. The sole constructor of level artifacts.
- **Transformation semantics**: The reusable, payload-only operations that implement the framework's downward and upward transformations (relationship discovery, domain categorization, enrichment, dimension classification). Invoked by the engine.
- **Navigation session**: The stateful owner of path-legality (entry only at raw level; no re-entry once departed) and the holder of the session's history structure.
- **History structure (branching tree)**: The single, always-on structure recording every node and branch, retaining full artifacts, supporting time-travel and branching, and offering consumer-facing queries.
- **Session export record**: The versioned, self-contained interchange artifact — a flat, identity-keyed map of nodes with parent references and full payloads — that a separate downstream service consumes without depending on the redesign application.
- **Session index entry**: The lightweight in-browser pointer (identity, title, backend location) that locates a durably stored session without holding its payloads.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of level artifacts, at all five levels, can return their complete derivation history from raw origin to themselves (today only the atomic level can).
- **SC-002**: 100% of level artifacts can produce a correct self-summary with zero external type-branching code paths remaining.
- **SC-003**: Exactly one code component constructs level artifacts and stamps history (down from three parallel transition implementations today).
- **SC-004**: Each framework rule is enforced in exactly one location (the duplicated "no raw-level destination" check, currently in up to three places, collapses to one structural guarantee plus one session-path guarantee).
- **SC-005**: After creating a sibling branch from any decision point, the original branch's artifacts and histories are 100% unchanged (verified by equality check before and after).
- **SC-006**: Branching and time-travel are available in 100% of sessions with no mode/flag to enable them (today off by default).
- **SC-007**: A session exported and then reloaded reproduces every node's data payload and history with 100% fidelity across all payload types.
- **SC-008**: An exported session can be fully read by a consumer process that does not import the redesign application's internal types.
- **SC-009**: For a session with branches sharing a common prefix of N ancestors, each shared ancestor appears exactly once in the export (zero per-branch duplication).
- **SC-010**: The in-browser session index for any session stays within the browser storage budget (≈5 MB) irrespective of total session data size.
- **SC-011**: All existing end-to-end descent/ascent journeys for the three reference datasets continue to pass after the refactor (no behavioral regression for users).
- **SC-012**: A practitioner can identify the divergence point between any two trajectories in a session in a single query.

## Assumptions

- **Reference behavior is preserved**: The observable descent/ascent results for the three reference datasets remain the same; this is an internal architecture realignment, not a change to transformation outcomes.
- **Integrity fingerprints are optional**: Per-step integrity fingerprints are populated for normal payloads and may be skipped for very large payloads; their absence does not invalidate a record. (Default: keep them, optional.)
- **Durable backend availability**: A file/blob durable storage backend is available for full-payload session storage; the browser index only locates sessions there.
- **Schema versioning policy**: The export declares a single version identifier; consumers reject unknown future versions rather than guessing. (Default: explicit version field, fail-closed on mismatch.)
- **Memory posture**: Retaining full payloads at every node is an accepted, deliberate cost; bounding it is delegated to explicit user-triggered prune/archive, not automatic eviction.
- **Single-session scope**: A redesign exploration and its branching all occur within one session; cross-session merging of trees is out of scope.
- **Breaking refactor accepted**: This realignment may change internal component contracts (e.g. how transitions are invoked); preserving the *external* end-to-end user journeys (SC-011) is the compatibility guarantee, not preserving every internal API signature.

## Out of Scope

- Building the downstream synthetic-generation service itself; this feature delivers only the persistence contract that service will consume.
- The data.gouv.fr search/import integration is orthogonal and untouched by this refactor.
- Changing the actual transformation outputs (which entities, domains, dimensions are produced) — semantics are relocated and made reusable, not redefined.
- Adding new granularity levels or new transition types beyond the existing adjacent-level set.
- Migrating previously exported (structure-only) session files to the new full-fidelity format.

## Dependencies

- The existing payload serializers (for tables, graphs, and scalar/vector values) are reused as the basis for full-fidelity export.
- The existing durable storage backend is the target for full-payload session records.
- The paper's §5.3 is the authoritative description of the target architecture.
