# Validation record

Date: 2026-10-24. Implementation proceeded in tested increments from the foundation.

- Backend, workloads, analytical comparison and C++ cache model: 43 host tests
  passed; opt-in real gem5 test skipped until simulator build completes.
- Python lint and frontend TypeScript/production build passed.
- Vitest: 2 tests passed. npm audit after fixed dependency pins: zero vulnerabilities.
- Actual containerized API health, configuration creation and retrieval passed.
- Browser tests against real API: desktop save/queue/navigation and mobile layout passed.
- After Docker stopped, both browser smoke checks were repeated against the latest
  source using a local FastAPI/Vite preview and passed. The submitted run remained
  queued; this is HTTP/UI evidence, not a completed simulator run.
- Seven dashboard pages, six workloads, sweeps/comparison/Pareto, raw artifact
  access and C++ model source are implemented. They are not all simulator-validated yet.
- An amd64-emulated build was cancelled due to compilation cost. The subsequent
  native arm64 build compiled through CPU, Ruby and classic-cache components,
  then Docker Desktop shut down, interrupting BuildKit with an EOF. No gem5
  compiler error was reported before that interruption.
- Docker was restarted once and stopped again immediately after engine startup.
  The host log records `process terminated due to explicit cancel`; its initiator
  has not been established. Docker availability is an external validation blocker.
- The Dockerfile now preserves compiler objects in a version/architecture-specific
  BuildKit cache mount and copies the finished executable outside that mount.
  The recovery build could not start while the Docker socket was unavailable.

Pending acceptance gates: real gem5 exit/checksum/stats, six-workload study,
advanced O3 smoke test, measured browser comparison and sweep, restart persistence.
No performance measurements have been claimed at this stage.
The worker image has not finished building. The application must not be described
as fully tested end to end until the pending real-simulation gates pass.
