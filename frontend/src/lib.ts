export type Architecture = {
  name: string;
  cpu_model: string;
  cores: number;
  clock_mhz: number;
  l1i_kib: number;
  l1d_kib: number;
  l2_kib: number;
  l1_assoc: number;
  l2_assoc: number;
  line_bytes: number;
  l1_latency_cycles: number;
  l2_latency_cycles: number;
  memory_mib: number;
  memory_model: string;
};
export type Metric = {
  value: number | null;
  unit: string;
  source: string;
  unavailable_reason: string | null;
};
export type Run = {
  id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  created_at: string;
  architecture: Architecture;
  benchmark: string;
  size: number;
  metrics: { values: Record<string, Metric> } | null;
  error: string | null;
  wall_seconds: number | null;
  experiment_id: string | null;
};
export type Configuration = { id: string; architecture: Architecture };
export const baseline: Architecture = {
  name: "Timing baseline",
  cpu_model: "TimingSimpleCPU",
  cores: 1,
  clock_mhz: 2000,
  l1i_kib: 32,
  l1d_kib: 32,
  l2_kib: 256,
  l1_assoc: 2,
  l2_assoc: 8,
  line_bytes: 64,
  l1_latency_cycles: 2,
  l2_latency_cycles: 20,
  memory_mib: 512,
  memory_model: "DDR3_1600_8x8",
};
export const benchmarks = [
  "matrix",
  "sequential",
  "random",
  "traversal",
  "sorting",
  "pointer",
];
export function format(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || !Number.isFinite(value))
    return "—";
  if (value !== 0 && Math.abs(value) < 0.001) return value.toExponential(3);
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
}
export function metric(run: Run | undefined, name: string): number | null {
  return run?.metrics?.values[name]?.value ?? null;
}
export async function api<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch("/api" + path, {
    signal,
    method: body === undefined ? "GET" : "POST",
    ...(body === undefined
      ? {}
      : {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
  });
  if (!response.ok) {
    const detail = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof detail.detail === "string"
        ? detail.detail
        : JSON.stringify(detail.detail),
    );
  }
  return response.status === 204 ||
    response.headers.get("content-length") === "0"
    ? (undefined as T)
    : response.json();
}
export function parseAxis(text: string): number[] {
  const values = text.split(",").map((v) => Number(v.trim()));
  if (
    !text.trim() ||
    values.some((v) => !Number.isInteger(v) || v <= 0) ||
    values.length > 4
  )
    throw new Error(
      "Each sweep axis needs 1–4 positive integers separated by commas.",
    );
  return [...new Set(values)];
}
