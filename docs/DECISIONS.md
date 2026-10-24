# Engineering decisions

1. Start with the Phase 1 acceptance gate from the specification. Avoid a broad
   dashboard that cannot yet produce verified measurements.
2. Use gem5 25.1.0.1 classic caches and the explicit SimObject interface verified
   in the release sources. Do not depend on deprecated `configs/example/se.py`
   flags or host-installed gem5. Unknown simulator versions fail closed.
3. One core, TimingSimpleCPU or advanced O3CPU, one known DDR3 device model with
   bounded exposed address ranges (128 MiB through 2 GiB).
   Multicore is rejected until a defined workload and coherence validation exist.
   The O3 pipeline uses gem5 defaults and is not a calibrated commercial core.
4. Keep HTTP execution separate from the worker process. A SQLite queue is
   sufficient for a local portfolio application; introducing Redis/Celery is
   unnecessary. A scheduler file lock and atomic claims avoid duplicate work.
5. Save architecture snapshots per run; later edits cannot change recorded
   parameters. Store raw statistics and hashes so every published metric can be
   audited. DB records only contain metrics after successful process exit,
   benchmark validation and parser validation.
6. Build the simulator for the native container host; cross-compile static x86-64
   workloads using an explicit compiler. Native macOS executables cannot run in
   X86 Linux syscall emulation. An amd64-emulated Docker override remains available.
   Disable vectorization to simplify interpretation; this is not peak-performance GEMM.
7. Begin with whole-process measurement, explicitly labeled. Add ROI markers and
   warm-up controls as an independently validated extension; mixing scopes in
   comparisons would produce misleading conclusions.
8. Memory counters describe bursts and controller traffic. Retain units and
   scope; do not interpret them as individual CPU requests or trace events.
9. Cancellation wins completion races. Restarted running jobs are failed instead
   of silently retried, which avoids hiding interrupted experimental evidence.
10. The API/worker operate as non-root, share only a results volume, and have no
    Docker socket access. This does not sandbox arbitrary third-party workloads;
    workload uploads and remote exposure are outside this milestone.
