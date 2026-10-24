import { useEffect, useState, type FormEvent } from "react";
import Hierarchy from "./Hierarchy";
import { BenchmarkBars, Curve, Tradeoff } from "./Charts";
import {
  api,
  baseline,
  benchmarks,
  format,
  metric,
  parseAxis,
  type Architecture,
  type Configuration,
  type Run,
} from "./lib";

const pages = [
  "Overview",
  "Architecture Configurator",
  "Simulation Workspace",
  "Performance Dashboard",
  "Architecture Comparison",
  "Design Space Explorer",
  "Experiment History",
];
const captions = [
  "Architecture laboratory",
  "Define the machine",
  "Execute & observe",
  "Measured performance",
  "Evaluate alternatives",
  "Search the design space",
  "Reproducible experiments",
];
type Health = { worker_ready: boolean; gem5_version: string };
type Experiment = { id: string; created_at: string };
type Results = {
  runs: Run[];
  total: number;
  finished: number;
  counts: Record<string, number>;
};
type Comparison = {
  baseline_id: string;
  pareto_ids: string[];
  rows: {
    id: string;
    feasible: boolean;
    cache_capacity_kib: number;
    metrics: Record<
      string,
      {
        value: number | null;
        absolute: number | null;
        percent: number | null;
        unit: string;
      }
    >;
  }[];
};

function usePolling<T>(path: string | null, revision: number) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setData(undefined);
    setError("");
    if (!path) return () => controller.abort();
    const poll = async () => {
      try {
        const value = await api<T>(path, undefined, controller.signal);
        if (!controller.signal.aborted) {
          setData(value);
          setError("");
        }
      } catch (e) {
        if (!controller.signal.aborted) setError(String(e));
      }
      if (!controller.signal.aborted) timer = setTimeout(poll, 2500);
    };
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [path, revision]);
  return { data, error };
}

function Stat({
  title,
  value,
  unit,
  source,
}: {
  title: string;
  value: number | null | undefined;
  unit: string;
  source?: string;
}) {
  return (
    <div className="stat" title={source}>
      <span>{title}</span>
      <strong>{format(value)}</strong>
      <small>
        {value == null ? "Unavailable · " : ""}
        {unit}
      </small>
    </div>
  );
}
function Status({ value }: { value: string }) {
  return (
    <span className={"status " + value}>
      <i />
      {value}
    </span>
  );
}
function RunTable({
  runs,
  choose,
  selected,
  toggle,
}: {
  runs: Run[];
  choose: (run: Run) => void;
  selected?: string[];
  toggle?: (id: string) => void;
}) {
  return runs.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {toggle && <th>Select</th>}
            <th>Run / architecture</th>
            <th>Workload</th>
            <th>Status</th>
            <th>IPC</th>
            <th>Cycles</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              {toggle && (
                <td>
                  <input
                    type="checkbox"
                    aria-label={`Compare run ${run.id}`}
                    disabled={run.status !== "completed"}
                    checked={selected?.includes(run.id) || false}
                    onChange={() => toggle(run.id)}
                  />
                </td>
              )}
              <td>
                <button className="link" onClick={() => choose(run)}>
                  {run.architecture.name}
                </button>
                <small className="mono">
                  {run.id.slice(0, 12)} · {run.architecture.l1d_kib}/
                  {run.architecture.l2_kib} KiB
                </small>
              </td>
              <td>
                {run.benchmark}
                <small>n = {run.size}</small>
              </td>
              <td>
                <Status value={run.status} />
              </td>
              <td>{format(metric(run, "ipc"))}</td>
              <td>{format(metric(run, "cycles"), 0)}</td>
              <td className="muted small">
                {new Date(run.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <div className="empty">
      No runs yet. Save an architecture, then launch a benchmark.
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState(0),
    [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [architecture, setArchitecture] = useState<Architecture>({
    ...baseline,
  });
  const [configurationId, setConfigurationId] = useState("");
  const [benchmark, setBenchmark] = useState("matrix"),
    [size, setSize] = useState(32);
  const [activeId, setActiveId] = useState(""),
    [selected, setSelected] = useState<string[]>([]);
  const [cohort, setCohort] = useState("");
  const [axes, setAxes] = useState({
    l1d_kib: "16,32,64",
    l2_kib: "256,512",
    l1_assoc: "2,4",
  });
  const [experimentId, setExperimentId] = useState("");
  const [constraint, setConstraint] = useState("");
  const [comparison, setComparison] = useState<Comparison>();
  const [sweepComparison, setSweepComparison] = useState<Comparison>();
  const health = usePolling<Health>("/health", revision);
  const configs = usePolling<Configuration[]>("/configurations", revision);
  const history = usePolling<Run[]>("/simulations?limit=200", revision);
  const activeDetails = usePolling<Run>(
    activeId ? `/simulations/${activeId}` : null,
    revision,
  );
  const experiments = usePolling<Experiment[]>("/experiments", revision);
  const results = usePolling<Results>(
    experimentId ? `/experiments/${experimentId}/results` : null,
    revision,
  );
  const logs = usePolling<Record<string, { text: string; truncated: boolean }>>(
    activeId ? `/simulations/${activeId}/logs` : null,
    revision,
  );
  const runs = history.data ?? [],
    configurations = configs.data ?? [];
  const active =
    (activeDetails.data?.id === activeId ? activeDetails.data : undefined) ??
    runs.find((r) => r.id === activeId) ??
    (activeId ? undefined : runs[0]);
  const completed = runs.filter((r) => r.status === "completed");
  const latest = completed[0];
  const cohorts = [
    ...new Set(completed.map((r) => `${r.benchmark}:${r.size}`)),
  ];
  const effectiveCohort = cohorts.includes(cohort) ? cohort : cohorts[0];
  const filtered = completed.filter(
    (r) => `${r.benchmark}:${r.size}` === effectiveCohort,
  );
  const preview = active?.architecture ?? architecture;
  const globalError =
    error ||
    history.error ||
    configs.error ||
    health.error ||
    experiments.error;

  async function action(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
      setRevision((v) => v + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  function choose(run: Run) {
    setActiveId(run.id);
    setPage(2);
  }
  function toggle(id: string) {
    setSelected((ids) =>
      ids.includes(id)
        ? ids.filter((i) => i !== id)
        : ids.length < 20
          ? [...ids, id]
          : ids,
    );
    setComparison(undefined);
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    await action(async () => {
      const result = await api<Configuration>("/configurations", architecture);
      setConfigurationId(result.id);
      setNotice("Architecture saved. Ready to simulate.");
    });
  }
  async function launch() {
    await action(async () => {
      const result = await api<Run>("/simulations", {
        configuration_id: configurationId,
        benchmark,
        size,
      });
      setActiveId(result.id);
      setNotice("Simulation queued. The worker will report measured results.");
    });
  }
  async function sweep() {
    await action(async () => {
      const result = await api<Experiment>("/experiments/sweep", {
        configuration_id: configurationId,
        benchmark,
        size,
        l1d_kib: parseAxis(axes.l1d_kib),
        l2_kib: parseAxis(axes.l2_kib),
        l1_assoc: parseAxis(axes.l1_assoc),
      });
      setExperimentId(result.id);
      setSweepComparison(undefined);
      setNotice(
        "Sweep queued. Progress counts finished jobs, including failures.",
      );
    });
  }
  async function compare(ids = selected, forSweep = false) {
    await action(async () => {
      const data = await api<Comparison>("/experiments/compare", {
        simulation_ids: ids,
        max_cache_kib:
          forSweep && constraint.trim() ? Number(constraint) : null,
      });
      if (forSweep) setSweepComparison(data);
      else setComparison(data);
    });
  }
  const selectionControls = (
    <>
      <label>
        Saved architecture
        <select
          value={configurationId}
          onChange={(e) => setConfigurationId(e.target.value)}
        >
          <option value="">Select a configuration</option>
          {configurations.map((c) => (
            <option key={c.id} value={c.id}>
              {c.architecture.name} · {c.architecture.l1d_kib}/
              {c.architecture.l2_kib} KiB · {c.id.slice(0, 6)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Benchmark
        <select
          value={benchmark}
          onChange={(e) => {
            setBenchmark(e.target.value);
            setSize(e.target.value === "matrix" ? 32 : 4096);
          }}
        >
          {benchmarks.map((b) => (
            <option key={b}>{b}</option>
          ))}
        </select>
      </label>
      <label>
        {benchmark === "matrix" ? "Matrix dimension" : "Elements"}
        <input
          type="number"
          min={2}
          max={benchmark === "matrix" ? 128 : 262144}
          value={size}
          onChange={(e) => setSize(Number(e.target.value))}
        />
      </label>
    </>
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">▦</div>
          <div>
            CacheLab<small>ARCHITECTURE SYSTEMS</small>
          </div>
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav>
          {pages.map((name, index) => (
            <button
              key={name}
              className={page === index ? "active" : ""}
              onClick={() => setPage(index)}
            >
              <span className="nav-index">0{index + 1}</span>
              {name}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div>
            <span
              className={"dot " + (health.data?.worker_ready ? "ready" : "")}
            />
            {health.data?.worker_ready
              ? "Simulator ready"
              : "Waiting for worker"}
          </div>
          <small>gem5 {health.data?.gem5_version ?? "25.1.0.1"} · X86 SE</small>
          <small>Local simulation environment</small>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <span>
            CPU & MEMORY / <b>{captions[page]}</b>
          </span>
          <a href="/docs" target="_blank" rel="noreferrer">
            API reference ↗
          </a>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">PERFORMANCE ENGINEERING</p>
              <h1>{pages[page]}</h1>
              <p className="muted">
                Configure. Measure. Understand the memory hierarchy.
              </p>
            </div>
            <span className="environment">● LOCAL LAB</span>
          </div>
          {globalError && (
            <div className="alert" role="alert">
              {globalError}
              <button
                onClick={() => {
                  setError("");
                  setRevision((v) => v + 1);
                }}
              >
                Retry
              </button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              {notice}
            </div>
          )}
          {!history.data && !history.error && (
            <p className="muted" role="status">
              Loading experiment state…
            </p>
          )}

          {page === 0 && (
            <>
              <div className="hero">
                <div>
                  <span className="eyebrow">
                    THE MEMORY HIERARCHY, MEASURED.
                  </span>
                  <h2>
                    Explore the architecture
                    <br />
                    behind the numbers.
                  </h2>
                  <p>
                    Run reproducible workloads on a real gem5 model.
                    <br />
                    Follow the evidence from cache behavior to execution cost.
                  </p>
                  <button onClick={() => setPage(1)}>
                    Configure an architecture <span>↗</span>
                  </button>
                </div>
                <div className="hero-chip">
                  <span>CPU</span>
                  <div>L1I ── L1D</div>
                  <div>↓ L2 ↓</div>
                  <b>DDR3</b>
                  <small>CLASSIC CACHE HIERARCHY</small>
                </div>
              </div>
              <div className="stats">
                <Stat
                  title="Completed runs"
                  value={completed.length}
                  unit="measured · latest 200 runs"
                />
                <Stat
                  title="Latest IPC"
                  value={metric(latest, "ipc")}
                  unit="instructions / cycle"
                />
                <Stat
                  title="Latest L1D miss rate"
                  value={
                    metric(latest, "l1d_miss_rate") === null
                      ? null
                      : metric(latest, "l1d_miss_rate")! * 100
                  }
                  unit="% of overall accesses"
                />
                <Stat
                  title="In flight"
                  value={
                    runs.filter((r) => ["queued", "running"].includes(r.status))
                      .length
                  }
                  unit="queued + running"
                />
              </div>
              <section className="panel">
                <div className="panel-title">
                  <div>
                    <p className="eyebrow">SYSTEM TOPOLOGY</p>
                    <h2>Inside the configured machine</h2>
                  </div>
                  <span className="tag">
                    {active ? "Selected run" : "Configuration preview"}
                  </span>
                </div>
                <Hierarchy config={preview} run={active} />
              </section>
              <section className="panel">
                <div className="panel-title">
                  <h2>Recent experiments</h2>
                  <button className="secondary" onClick={() => setPage(6)}>
                    View history →
                  </button>
                </div>
                <RunTable runs={runs.slice(0, 5)} choose={choose} />
              </section>
            </>
          )}

          {page === 1 && (
            <>
              <div className="two-column">
                <form className="panel" onSubmit={save}>
                  <p className="eyebrow">ARCHITECTURE DEFINITION</p>
                  <h2>Configure your baseline</h2>
                  <label>
                    Reuse saved configuration
                    <select
                      defaultValue=""
                      onChange={(e) => {
                        const c = configurations.find(
                          (c) => c.id === e.target.value,
                        );
                        if (c) {
                          setArchitecture({ ...c.architecture });
                          setConfigurationId(c.id);
                        } else {
                          setArchitecture({ ...baseline });
                          setConfigurationId("");
                        }
                      }}
                    >
                      <option value="">Start from baseline</option>
                      {configurations.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.architecture.name} · {c.id.slice(0, 6)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Configuration name
                    <input
                      required
                      maxLength={80}
                      value={architecture.name}
                      onChange={(e) =>
                        setArchitecture({
                          ...architecture,
                          name: e.target.value,
                        })
                      }
                    />
                  </label>
                  <div className="form-grid">
                    <label>
                      CPU model
                      <select
                        value={architecture.cpu_model}
                        onChange={(e) =>
                          setArchitecture({
                            ...architecture,
                            cpu_model: e.target.value,
                          })
                        }
                      >
                        <option>TimingSimpleCPU</option>
                        <option>O3CPU</option>
                      </select>
                    </label>
                    <label>
                      CPU cores
                      <select disabled value="1">
                        <option>1</option>
                      </select>
                    </label>
                    {(
                      [
                        ["clock_mhz", "CPU / fabric clock (MHz)", 100, 4000],
                        ["l1i_kib", "L1 instruction cache (KiB)", 4, 128],
                        ["l1d_kib", "L1 data cache (KiB)", 4, 128],
                        ["l2_kib", "Unified L2 cache (KiB)", 128, 8192],
                        [
                          "l1_latency_cycles",
                          "L1 tag/data/response (cycles)",
                          1,
                          20,
                        ],
                        [
                          "l2_latency_cycles",
                          "L2 tag/data/response (cycles)",
                          1,
                          100,
                        ],
                      ] as const
                    ).map(([key, label, min, max]) => (
                      <label key={key}>
                        {label}
                        <input
                          required
                          type="number"
                          min={min}
                          max={max}
                          value={architecture[key]}
                          onChange={(e) =>
                            setArchitecture({
                              ...architecture,
                              [key]: Number(e.target.value),
                            })
                          }
                        />
                      </label>
                    ))}
                    {(
                      [
                        ["l1_assoc", "L1 associativity", [1, 2, 4, 8]],
                        ["l2_assoc", "L2 associativity", [1, 2, 4, 8, 16]],
                        ["line_bytes", "Cache line (B)", [32, 64, 128]],
                      ] as const
                    ).map(([key, label, values]) => (
                      <label key={key}>
                        {label}
                        <select
                          value={architecture[key]}
                          onChange={(e) =>
                            setArchitecture({
                              ...architecture,
                              [key]: Number(e.target.value),
                            })
                          }
                        >
                          {values.map((v) => (
                            <option key={v}>{v}</option>
                          ))}
                        </select>
                      </label>
                    ))}
                    <label>
                      Main memory
                      <select
                        value={architecture.memory_mib}
                        onChange={(e) =>
                          setArchitecture({
                            ...architecture,
                            memory_mib: Number(e.target.value),
                          })
                        }
                      >
                        {[128, 256, 512, 1024, 2048].map((v) => (
                          <option key={v} value={v}>
                            {v} MiB · DDR3_1600_8x8
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <p className="muted small">
                    Capacities and set counts must be powers of two. Cache
                    latency applies to tag, data and response stages separately.
                    Replacement: LRU. Prefetch: disabled.
                  </p>
                  <button disabled={busy}>Save architecture</button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setPage(2)}
                  >
                    Open simulation workspace →
                  </button>
                </form>
                <section className="panel">
                  <p className="eyebrow">LIVE CONFIGURATION PREVIEW</p>
                  <Hierarchy config={architecture} />
                </section>
              </div>
            </>
          )}

          {page === 2 && (
            <>
              <section className="panel">
                <div className="panel-title">
                  <h2>Launch a simulation</h2>
                  <span className="tag">No host gem5 required</span>
                </div>
                <div className="launch-grid">
                  {selectionControls}
                  <button
                    disabled={
                      busy ||
                      !configurationId ||
                      !Number.isInteger(size) ||
                      size < 2 ||
                      size > (benchmark === "matrix" ? 128 : 262144)
                    }
                    onClick={() => void launch()}
                  >
                    Run simulation ↗
                  </button>
                </div>
                <p className="muted small">
                  Whole-process statistics include initialization, libc and
                  correctness validation. Larger workloads may reach configured
                  runtime limits.
                </p>
              </section>
              <section className="panel">
                <div className="panel-title">
                  <div>
                    <p className="eyebrow">ACTIVE WORKSPACE</p>
                    <h2>
                      {active
                        ? `${active.benchmark} / n=${active.size}`
                        : "No simulation selected"}
                    </h2>
                    {active && (
                      <span className="mono muted small">{active.id}</span>
                    )}
                  </div>
                  {active && (
                    <div className="actions">
                      <Status value={active.status} />
                      {["queued", "running"].includes(active.status) && (
                        <button
                          className="secondary"
                          disabled={busy}
                          onClick={() =>
                            void action(async () => {
                              await api(`/simulations/${active.id}/cancel`, {});
                            })
                          }
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  )}
                </div>
                {active?.error && <div className="alert">{active.error}</div>}
                <div className="stats">
                  <Stat
                    title="IPC"
                    value={metric(active, "ipc")}
                    unit="instructions / cycle"
                  />
                  <Stat
                    title="CPI"
                    value={metric(active, "cpi")}
                    unit="cycles / instruction"
                  />
                  <Stat
                    title="Execution cycles"
                    value={metric(active, "cycles")}
                    unit="simulated cycles"
                  />
                  <Stat
                    title="Simulated execution"
                    value={metric(active, "simulated_seconds")}
                    unit="seconds · simulated"
                  />
                </div>
                <p className="small muted">
                  Host orchestration runtime: {format(active?.wall_seconds)} s.
                  Progress is reported as queue/process state; simulated
                  completion percentage is unknown.
                </p>
                {active?.status === "completed" && (
                  <div className="actions">
                    <a
                      href={`/api/simulations/${active.id}/artifacts/stats.txt`}
                    >
                      Raw statistics ↗
                    </a>
                    <a
                      href={`/api/simulations/${active.id}/artifacts/manifest.json`}
                    >
                      Run provenance ↗
                    </a>
                    <a
                      href={`/api/simulations/${active.id}/artifacts/config.ini`}
                    >
                      gem5 configuration ↗
                    </a>
                  </div>
                )}
                <h3>Captured simulator output</h3>
                {logs.error && (
                  <div role="alert" className="alert">
                    {logs.error}
                  </div>
                )}
                <pre className="logs">
                  {activeId
                    ? logs.data
                      ? Object.entries(logs.data)
                          .map(
                            ([name, log]) =>
                              `[${name}${log.truncated ? " · tail only" : ""}]\n${log.text}`,
                          )
                          .join("\n\n")
                      : "Loading logs…"
                    : "Select a run below to inspect its logs."}
                </pre>
              </section>
              <section className="panel">
                <RunTable runs={runs.slice(0, 12)} choose={choose} />
              </section>
            </>
          )}

          {page === 3 && (
            <>
              <div className="toolbar">
                <label>
                  Benchmark / input cohort
                  <select
                    value={effectiveCohort ?? ""}
                    onChange={(e) => setCohort(e.target.value)}
                  >
                    {!cohorts.length && (
                      <option value="">No completed runs</option>
                    )}
                    {cohorts.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </label>
                <span className="muted small">
                  {filtered.length} measured runs · matching benchmark and input
                  size
                </span>
              </div>
              <div className="chart-grid">
                <Curve
                  runs={filtered}
                  title="L1D size vs. miss rate"
                  x="l1d_kib"
                  y="l1d_miss_rate"
                  unit="miss ratio"
                />
                <Curve
                  runs={filtered}
                  title="Associativity vs. L1D miss rate"
                  x="l1_assoc"
                  y="l1d_miss_rate"
                  unit="miss ratio"
                />
                <Curve
                  runs={filtered}
                  title="L2 capacity vs. IPC"
                  x="l2_kib"
                  y="ipc"
                  unit="instructions/cycle"
                />
                <Curve
                  runs={filtered}
                  title="L2 latency vs. execution cycles"
                  x="l2_latency_cycles"
                  y="cycles"
                  unit="cycles"
                />
              </div>
              <section className="panel">
                <BenchmarkBars runs={completed} />
                <h2>Cache measurements by benchmark</h2>
                <p className="muted small">
                  Input size and configuration are shown per run; different
                  workloads are not treated as controlled comparisons.
                </p>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Benchmark</th>
                        <th>n</th>
                        <th>L1D / L2 KiB</th>
                        <th>L1I miss ratio</th>
                        <th>L1D miss ratio</th>
                        <th>L2 miss ratio</th>
                        <th>DRAM read burst (ns)</th>
                        <th>DRAM (B/s)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {completed.map((r) => (
                        <tr key={r.id}>
                          <td>{r.benchmark}</td>
                          <td>{r.size}</td>
                          <td>
                            {r.architecture.l1d_kib}/{r.architecture.l2_kib}
                          </td>
                          {[
                            "l1i_miss_rate",
                            "l1d_miss_rate",
                            "l2_miss_rate",
                            "dram_read_burst_latency",
                            "dram_bandwidth",
                          ].map((key) => (
                            <td
                              key={key}
                              title={r.metrics?.values[key]?.source}
                            >
                              {format(metric(r, key))}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}

          {page === 4 && (
            <>
              <section className="panel">
                <div className="panel-title">
                  <div>
                    <h2>Compare measured architectures</h2>
                    <p className="muted small">
                      Select 2–20 completed runs with the same workload and
                      input size. The first selected run is the baseline.
                    </p>
                  </div>
                  <button
                    disabled={busy || selected.length < 2}
                    onClick={() => void compare()}
                  >
                    Compare {selected.length} runs
                  </button>
                </div>
                <RunTable
                  runs={completed}
                  choose={choose}
                  selected={selected}
                  toggle={toggle}
                />
              </section>
              {comparison && (
                <section className="panel">
                  <h2>Differences from {comparison.baseline_id.slice(0, 8)}</h2>
                  <p className="muted small">
                    Δ is candidate − baseline. A missing metric or zero baseline
                    has no percentage difference.
                  </p>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Metric</th>
                          {comparison.rows.map((r) => (
                            <th key={r.id}>{r.id.slice(0, 8)}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {[
                          "ipc",
                          "cpi",
                          "cycles",
                          "l1d_misses",
                          "l2_misses",
                          "dram_bandwidth",
                          "simulated_seconds",
                        ].map((key) => (
                          <tr key={key}>
                            <td>{key.replaceAll("_", " ")}</td>
                            {comparison.rows.map((row) => (
                              <td key={row.id}>
                                {format(row.metrics[key]?.value)}{" "}
                                <small>{row.metrics[key]?.unit}</small>
                                <small>
                                  Δ {format(row.metrics[key]?.absolute)} /{" "}
                                  {format(row.metrics[key]?.percent)}%
                                </small>
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
            </>
          )}

          {page === 5 && (
            <>
              <section className="panel">
                <div className="panel-title">
                  <div>
                    <p className="eyebrow">PARAMETER SWEEP</p>
                    <h2>Explore the design space</h2>
                  </div>
                  <span className="tag">Up to 64 combinations</span>
                </div>
                <div className="launch-grid">{selectionControls}</div>
                <div className="form-grid">
                  {Object.entries(axes).map(([key, value]) => (
                    <label key={key}>
                      {
                        {
                          l1d_kib: "L1D capacities (KiB)",
                          l2_kib: "L2 capacities (KiB)",
                          l1_assoc: "L1 associativities",
                        }[key]
                      }
                      <input
                        value={value}
                        onChange={(e) =>
                          setAxes({ ...axes, [key]: e.target.value })
                        }
                      />
                    </label>
                  ))}
                </div>
                <button
                  disabled={busy || !configurationId}
                  onClick={() => void sweep()}
                >
                  Queue parameter sweep ↗
                </button>
                <p className="muted small">
                  Comma-separated values; invalid combinations reject the entire
                  sweep. Every point uses a real independent simulation.
                </p>
              </section>
              <section className="panel">
                <div className="toolbar">
                  <label>
                    Experiment
                    <select
                      value={experimentId}
                      onChange={(e) => {
                        setExperimentId(e.target.value);
                        setSweepComparison(undefined);
                      }}
                    >
                      <option value="">Select experiment</option>
                      {experiments.data?.map((e) => (
                        <option key={e.id} value={e.id}>
                          {e.id.slice(0, 12)} ·{" "}
                          {new Date(e.created_at).toLocaleString()}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Maximum total cache capacity (KiB)
                    <input
                      type="number"
                      min={1}
                      placeholder="Unconstrained"
                      value={constraint}
                      onChange={(e) => {
                        setConstraint(e.target.value);
                        setSweepComparison(undefined);
                      }}
                    />
                  </label>
                  <button
                    disabled={
                      busy ||
                      (results.data?.runs.filter(
                        (r) => r.status === "completed",
                      ).length ?? 0) < 2
                    }
                    onClick={() =>
                      void compare(
                        results
                          .data!.runs.filter((r) => r.status === "completed")
                          .map((r) => r.id),
                        true,
                      )
                    }
                  >
                    Compute Pareto frontier
                  </button>
                </div>
                {results.error && <div className="alert">{results.error}</div>}
                {results.data && (
                  <>
                    <p>
                      {results.data.finished} / {results.data.total} jobs
                      finished{" "}
                      <span className="muted">
                        ·{" "}
                        {Object.entries(results.data.counts)
                          .map(([key, n]) => `${n} ${key}`)
                          .join(" · ")}
                      </span>
                    </p>
                    <progress
                      value={results.data.finished}
                      max={results.data.total}
                    />
                    <RunTable runs={results.data.runs} choose={choose} />
                  </>
                )}
              </section>
              <Tradeoff
                runs={
                  results.data?.runs.filter((r) => r.status === "completed") ??
                  []
                }
                pareto={sweepComparison?.pareto_ids}
              />
              {sweepComparison && (
                <section className="panel">
                  <h2>Feasible Pareto configurations</h2>
                  <p className="muted small">
                    Minimize total cache capacity and measured execution cycles.
                    Analyzed {sweepComparison.rows.length} completed runs;
                    recompute after more jobs finish. Select a run to inspect
                    its full configuration.
                  </p>
                  {sweepComparison.pareto_ids.length === 0 && (
                    <p>No completed configurations meet this constraint.</p>
                  )}
                  {sweepComparison.pareto_ids.length > 0 && (
                    <RunTable
                      runs={
                        results.data?.runs.filter((r) =>
                          sweepComparison.pareto_ids.includes(r.id),
                        ) ?? []
                      }
                      choose={choose}
                    />
                  )}
                </section>
              )}
              {results.data && (
                <section className="panel">
                  <h2>Measured IPC heatmap</h2>
                  <p className="muted small">
                    Rows retain associativity; each cell is a single measured
                    configuration. Failed or pending runs have no value.
                  </p>
                  <div className="heatmap">
                    {results.data.runs.map((r) => (
                      <div
                        key={r.id}
                        title={r.id}
                        style={{
                          background:
                            metric(r, "ipc") === null
                              ? "#142035"
                              : `rgba(53,190,170,${Math.min(0.8, 0.12 + (metric(r, "ipc") ?? 0) * 0.65)})`,
                        }}
                      >
                        <small>
                          L1D {r.architecture.l1d_kib} / L2{" "}
                          {r.architecture.l2_kib} KiB ·{" "}
                          {r.architecture.l1_assoc} way
                        </small>
                        <b>{format(metric(r, "ipc"))} IPC</b>
                        <small>{r.status}</small>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}

          {page === 6 && (
            <section className="panel">
              <div className="panel-title">
                <div>
                  <h2>Experiment history</h2>
                  <p className="muted small">
                    Latest 200 runs, persisted locally. Full paginated history
                    is available through the API.
                  </p>
                </div>
                <button
                  className="secondary"
                  onClick={() => setRevision((v) => v + 1)}
                >
                  Refresh
                </button>
              </div>
              <RunTable runs={runs} choose={choose} />
            </section>
          )}
          <footer>
            <span>CacheLab / gem5 architecture exploration</span>
            <span>
              Whole-process SE measurements · Unavailable values shown as —
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
