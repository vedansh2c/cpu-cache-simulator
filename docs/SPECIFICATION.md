# Project: CPU Cache & Memory Performance Analysis Platform

## Role

Act as a senior Computer Architecture Engineer, Performance Modeling Engineer, and Full-Stack Developer.

Build a production-quality, Dockerized, interactive **CPU Cache & Memory Performance Analysis Platform** using gem5.

This project should demonstrate skills relevant to semiconductor engineering roles involving virtual platforms, SoC architecture, memory systems, performance modeling, simulation, and architecture exploration.

## 1. Technology Stack

- **Simulation Engine:** gem5
- **Backend:** Python, FastAPI, Pydantic
- **Frontend:** React, TypeScript, Tailwind CSS
- **Visualizations:** Recharts and React Flow
- **Database:** SQLite with SQLAlchemy
- **Containerization:** Docker and Docker Compose
- **Automation:** Python
- **Testing:** pytest, Vitest
- **Workloads:** C/C++ programs compiled for the simulated ISA

The entire application must run locally through Docker Compose without requiring gem5 to be installed on the host.

## 2. Core Functionality

### A. Interactive CPU Architecture Configuration

Create a web interface that allows users to configure a simulated computer architecture.

Configuration options:

- CPU model: TimingSimpleCPU initially, with O3CPU as an advanced option.
- CPU clock frequency.
- L1 instruction cache size.
- L1 data cache size.
- L2 cache size.
- Cache associativity.
- Cache line size.
- Cache access latency.
- Main memory size and supported memory model.
- Number of CPU cores, where supported.

Validate all configurations against the selected gem5 version and model capabilities.

Users should be able to save configurations and reuse them.

### B. Simulation Engine

Integrate gem5 as the real simulation backend.

Users should be able to:

1. Select an architecture configuration.
2. Choose a benchmark.
3. Start a simulation.
4. Monitor simulation progress.
5. View simulation logs.
6. Inspect performance statistics.
7. Compare multiple simulation runs.

Implement a Python orchestration service that generates gem5 configuration scripts, launches simulations as isolated processes, captures errors and stores their outputs.

Use actual gem5 simulation results. Never generate fabricated performance statistics.

### C. Benchmark Workloads

Implement these workloads in C/C++:

- Matrix multiplication
- Sequential memory access
- Random memory access
- Array traversal
- Sorting
- Pointer chasing

Each benchmark should have configurable input sizes.

Make the workloads deterministic where practical and validate correctness.

### D. Performance Metrics

Extract performance statistics from gem5 outputs.

Display:

- IPC (instructions per cycle)
- CPI (cycles per instruction)
- Simulated execution cycles
- L1 instruction cache miss rate
- L1 data cache miss rate
- L2 cache miss rate
- Memory access latency, where available
- Memory bandwidth, where measurable
- Total simulated execution time

Implement a version-aware statistics parser.

Clearly label unsupported or unavailable metrics. Do not substitute wall-clock simulation runtime for simulated program execution time.

## 3. Interactive Visualization Dashboard

Develop a modern dashboard resembling a professional semiconductor performance analysis application.

### Visualization 1: CPU and Memory Architecture Diagram

Use React Flow to create an interactive hardware block diagram.

Example:

CPU Core
↓
L1 Instruction Cache / L1 Data Cache
↓
L2 Cache
↓
Memory Controller
↓
DRAM

Display cache sizes, latency parameters, and relevant measured statistics.

Clicking a component should display its configuration and available performance metrics.

### Visualization 2: Cache Performance Dashboard

Create interactive charts for:

- Cache size vs. miss rate
- Cache associativity vs. miss rate
- L2 size vs. IPC
- Cache latency vs. execution cycles
- Benchmark vs. cache performance

Include tooltips, filters, experiment selection, and zooming where appropriate.

### Visualization 3: Memory Hierarchy Explorer

Create a visual representation of the cache hierarchy showing how memory requests pass through the simulated components.

Use aggregated gem5 statistics to display access counts, hits, misses, and average latency where available.

Do not pretend to reconstruct individual memory transactions unless tracing is explicitly enabled.

### Visualization 4: Architecture Comparison

Allow users to compare two or more configurations side by side.

Show differences in:

- IPC
- Cache misses
- Execution cycles
- Memory bandwidth
- Workload performance

Include absolute and percentage differences, with appropriate handling of missing values.

### Visualization 5: Architecture Design Space Exploration

Allow users to define parameter sweeps such as:

- L1 size: 16 KB, 32 KB, 64 KB
- L2 size: 256 KB, 512 KB, 1 MB
- Associativity: 2, 4, 8

Execute each valid configuration automatically.

Display:

- Heatmaps
- Scatter plots
- Performance trade-off charts
- Pareto frontiers

Help users identify the best-performing configuration under configurable constraints, such as cache capacity.

## 4. Docker Architecture

Create separate services for:

**Frontend container**
- React application
- Serves the interactive UI

**Backend container**
- FastAPI REST API
- Configuration validation
- Experiment management
- Statistics processing

**Simulation worker container**
- gem5 installation
- Workload compilation
- Simulation execution
- Experiment automation

Use Docker Compose to coordinate these services.

Requirements:

- One-command startup with `docker compose up --build`.
- Named volumes for persistent experiment results.
- Health checks and startup dependencies.
- Non-root container execution where practical.
- Resource and timeout limits for simulations.
- Configurable worker concurrency.
- Reproducible gem5 version and build configuration.
- Compatible with Docker Desktop on Apple Silicon Macs where feasible; document any amd64 emulation requirements.

Avoid rebuilding gem5 unnecessarily.

## 5. Backend API

Implement REST endpoints:

- `GET /api/health`
- `GET /api/configurations`
- `POST /api/configurations`
- `GET /api/benchmarks`
- `POST /api/simulations`
- `GET /api/simulations/{id}`
- `GET /api/simulations/{id}/metrics`
- `GET /api/simulations/{id}/logs`
- `POST /api/experiments/sweep`
- `GET /api/experiments/{id}/results`
- `POST /api/experiments/compare`

Use background workers so long-running simulations never block HTTP requests.

Implement simulation status tracking: queued, running, completed, failed, and cancelled.

## 6. Engineering and Validation

This is an engineering project, not merely a visualization application.

Include:

- Unit tests for metrics and parsers.
- Integration tests for the simulation orchestration layer.
- Known-good gem5 configurations.
- Reproducible workloads.
- A simple analytical cache model for cross-checking selected results.
- Validation that increasing cache capacity does not automatically imply better performance for every workload.
- Documented assumptions and simulator limitations.

Build a small original **C++ cache model** supporting configurable cache size, block size, associativity, and LRU replacement. Use memory-access traces to compare its predictions against suitable gem5 cache statistics, explaining differences due to the respective models and traces.

## 7. UI/UX Requirements

Design a professional engineering dashboard.

Pages:

1. Overview
2. Architecture Configurator
3. Simulation Workspace
4. Performance Dashboard
5. Architecture Comparison
6. Design Space Explorer
7. Experiment History

Use a clean dark theme, responsive layout, clearly labeled engineering units, and polished data visualizations.

Include loading states, empty states, errors, and experiment progress indicators.

## 8. Project Deliverables

Generate:

- Complete source code.
- Dockerfiles and `docker-compose.yml`.
- gem5 configuration and integration scripts.
- C/C++ benchmark programs.
- Original C++ cache model.
- FastAPI backend.
- React frontend.
- Database models.
- Automated tests.
- Example experiment configurations.
- Detailed README.
- Architecture diagrams.
- Instructions for reproducing every benchmark.

The README must explain the actual computer architecture concepts demonstrated, not only how to run the software.

## 9. Implementation Strategy

Build the application incrementally.

**Phase 1: Working simulation foundation**

- Dockerized gem5.
- Single CPU configuration.
- One matrix multiplication benchmark.
- Real execution and statistics extraction.
- Minimal FastAPI integration.

**Phase 2: Experiment infrastructure**

- Configuration management.
- Simulation queue.
- Persistent results.
- Multiple benchmarks.
- Reliable experiment orchestration.

**Phase 3: Interactive frontend**

- Architecture configurator.
- Simulation monitoring.
- Performance graphs.
- Interactive memory hierarchy diagram.

**Phase 4: Advanced performance analysis**

- Parameter sweeps.
- Architecture comparisons.
- Pareto analysis.
- Original C++ cache model and validation.

**Phase 5: Production-quality finishing**

- Tests.
- Documentation.
- Error handling.
- Reproducible Docker setup.
- Sample architecture exploration study.

## 10. Important Development Instructions

- Use gem5's current official documentation.
- Pin compatible dependency versions.
- Verify the actual simulator interfaces before implementing integrations.
- Never use hardcoded or mock statistics as actual simulation results.
- Build the smallest working end-to-end implementation first.
- Prefer understandable modular code over unnecessary abstractions.
- Keep the project realistic for a student portfolio.
- Document every major engineering decision.
- Provide commands for testing each phase.
- Do not claim a phase is complete until its core functionality is tested.

**Start by proposing the repository structure and implementing Phase 1 with runnable source code. Continue incrementally rather than generating the entire system in one unverified step.**

## Definition of Success

A user should be able to open the web dashboard, configure L1/L2 caches, select a benchmark, run a real gem5 simulation in Docker, visualize the measured results, and compare architectures to explain why one performs better than another.