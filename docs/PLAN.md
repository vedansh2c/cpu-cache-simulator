# Incremental delivery and acceptance gates

## Phase 1 — real simulation foundation

Structure: `backend/`, `simulation/`, `workloads/`, `tests/`, `scripts/`, `examples/`,
and `docs/`. Deliver a two-level TimingSimpleCPU, a deterministic matrix binary,
version-aware counters, FastAPI, persistent queue, separate worker, and Docker.

Acceptance: host tests and lint pass; both images build; services become healthy;
`python3 scripts/smoke.py` finishes a real simulation and validates all three cache
rates and mandatory execution metrics. Restarting services preserves results.
Any unperformed gate must be listed in PROGRESS.md.

## Phase 2 — experiment infrastructure

Add deterministic sequential/random memory, array traversal, sorting and pointer
chasing with separate correctness checks and size units. Add robust experiment
grouping, bounded parameter-sweep generation, result comparison with missing and
zero-baseline handling, and replay/export. Extend the worker queue rather than
running simulations within HTTP handlers.

Acceptance: `pytest` integration tests and real tiny runs of every workload;
validated sweeps persist every child and report failures; compare results against
raw metrics. Test cancellation/restart with multiple in-flight children.

## Phase 3 — interactive frontend

Add `frontend/` with React, TypeScript, Tailwind, Recharts and React Flow plus an
independent frontend Docker service/proxy. Implement Overview, Configurator,
Workspace, Performance, Comparison, Design Space and History pages. Use measured
data only, component inspector, aggregate hierarchy counters, loading/empty/error
states, accessible inputs and labeled engineering units.

Acceptance: type check, Vitest, production build and browser testing of a real
configure -> submit -> monitor -> measured metrics workflow through Compose.

## Phase 4 — architecture analysis

Add original C++ LRU trace model and deterministic generated traces. Cross-check
hand-calculated compulsory/conflict/capacity cases; document why virtual-address
data traces differ from gem5's physical, instruction, writeback and timing traffic.
Only compare equivalent scope; no claims of transaction reconstruction.
Add heatmaps, scatter plots, latency/capacity tradeoffs, constrained Pareto
frontiers and absolute/percentage comparisons. Test unsupported/missing metrics,
ties and zero baselines. Test larger caches without assuming improvement.

Acceptance: C++ tests, pytest/Vitest analysis tests, real versioned study artifacts
with workload/build hashes and no unsupported extrapolated performance claims.

## Phase 5 — finishing

Add CI gates, dependency auditing/lockfiles, Docker release image digests,
artifact retention, clear recovery diagnostics, and published reproducible study
instructions. Measure before offering O3/multicore/ROI extensions.

Acceptance: fresh Compose build on Linux amd64 and an explicitly documented
Apple Silicon check; full workflow and failure paths; truthful remaining limits.
