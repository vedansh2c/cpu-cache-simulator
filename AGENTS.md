# Working instructions

- Keep responses concise. Read `docs/PROGRESS.md` and `docs/PLAN.md` first.
- Implement one tested milestone at a time, following `docs/SPECIFICATION.md`.
- Never fabricate simulation data or describe synthetic test inputs as measurements.
- Use pinned gem5 source interfaces. Reject unsupported models and unknown versions.
- Run `.venv/bin/pytest -q` and `.venv/bin/ruff check backend simulation tests scripts`.
- Phase 1 requires a real `python3 scripts/smoke.py` through Docker Compose before
  being marked complete. Record unavailable validation honestly.
- Preserve raw statistics, workload correctness checks, units, measurement scope,
  and provenance. Host runtime must never replace simulated execution time.
- Do not rebuild gem5 without a simulator/build change; application COPY layers
  deliberately follow its cached build stage.
