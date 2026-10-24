import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Brush,
  ScatterChart,
  Scatter,
  ZAxis,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import { type Run, metric } from "./lib";
const colors = ["#53d9c4", "#8da4ff", "#f5bd6b"];
export function BenchmarkBars({ runs }: { runs: Run[] }) {
  const data = runs
    .slice(0, 20)
    .map((r) => ({
      name: `${r.benchmark} n=${r.size} ${r.id.slice(0, 4)}`,
      L1I: metric(r, "l1i_miss_rate"),
      L1D: metric(r, "l1d_miss_rate"),
      L2: metric(r, "l2_miss_rate"),
    }));
  return (
    <section className="panel chart">
      <h3>Benchmark / cache miss ratios</h3>
      {data.length ? (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} margin={{ bottom: 40 }}>
            <CartesianGrid stroke="#213147" />
            <XAxis
              dataKey="name"
              angle={-20}
              textAnchor="end"
              tick={{ fill: "#91a4ba", fontSize: 9 }}
              height={65}
            />
            <YAxis domain={[0, 1]} tick={{ fill: "#91a4ba" }} />
            <Tooltip
              contentStyle={{
                background: "#142237",
                border: "1px solid #32445c",
              }}
            />
            <Legend />
            {["L1I", "L1D", "L2"].map((key, i) => (
              <Bar key={key} dataKey={key} fill={colors[i]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="empty">No completed workloads yet.</div>
      )}
      <p className="small muted">
        Latest 20 completed runs. Per-run ratios include all process activity;
        benchmark/input sizes are explicit.
      </p>
    </section>
  );
}
export function Curve({
  runs,
  title,
  x,
  y,
  unit,
}: {
  runs: Run[];
  title: string;
  x: "l1d_kib" | "l2_kib" | "l1_assoc" | "l2_latency_cycles";
  y: string;
  unit: string;
}) {
  const data = runs
    .filter((r) => metric(r, y) !== null)
    .map((r) => ({
      x: r.architecture[x],
      y: metric(r, y),
      run: r.id.slice(0, 8),
    }))
    .sort((a, b) => a.x - b.x);
  return (
    <section className="panel chart">
      <h3>{title}</h3>
      {data.length ? (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ left: 10, right: 20, top: 15 }}>
            <CartesianGrid stroke="#213147" strokeDasharray="3 3" />
            <XAxis
              dataKey="x"
              type="number"
              domain={["dataMin", "dataMax"]}
              tick={{ fill: "#91a4ba" }}
            />
            <YAxis width={70} tick={{ fill: "#91a4ba" }} />
            <Tooltip
              contentStyle={{
                background: "#142237",
                border: "1px solid #32445c",
              }}
              labelFormatter={(v) => `${x}: ${v}`}
              formatter={(v) => [v, unit]}
            />
            <Line
              type="linear"
              dataKey="y"
              stroke={colors[0]}
              strokeWidth={2}
              dot={{ r: 4 }}
              connectNulls={false}
            />
            <Brush dataKey="x" height={20} stroke="#39526d" fill="#101b2a" />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="empty">No completed measurements in this cohort.</div>
      )}
      <p className="muted small">
        Each point is one measured run. Other parameters may differ; inspect
        configurations before attributing causality.
      </p>
    </section>
  );
}
export function Tradeoff({
  runs,
  pareto = [],
}: {
  runs: Run[];
  pareto?: string[];
}) {
  const data = runs
    .filter((r) => metric(r, "cycles") !== null)
    .map((r) => ({
      capacity:
        r.architecture.l1i_kib + r.architecture.l1d_kib + r.architecture.l2_kib,
      cycles: metric(r, "cycles"),
      id: r.id.slice(0, 8),
      frontier: pareto.includes(r.id),
    }));
  return (
    <section className="panel chart">
      <h3>Capacity / execution trade-off</h3>
      {data.length ? (
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 15, left: 15 }}>
            <CartesianGrid stroke="#213147" />
            <XAxis
              type="number"
              dataKey="capacity"
              name="Total cache"
              unit=" KiB"
              tick={{ fill: "#91a4ba" }}
            />
            <YAxis
              type="number"
              dataKey="cycles"
              name="Cycles"
              tick={{ fill: "#91a4ba" }}
              width={85}
            />
            <ZAxis range={[75, 75]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              contentStyle={{
                background: "#142237",
                border: "1px solid #32445c",
              }}
            />
            <Scatter
              data={data.filter((d) => !d.frontier)}
              fill={colors[1]}
              name="Measured"
            />
            <Scatter
              data={data.filter((d) => d.frontier)}
              fill={colors[0]}
              name="Pareto frontier"
            />
          </ScatterChart>
        </ResponsiveContainer>
      ) : (
        <div className="empty">Completed runs will appear here.</div>
      )}
      <p className="small muted">
        Minimize cycles and total cache capacity. Green points are nondominated
        feasible configurations.
      </p>
    </section>
  );
}
