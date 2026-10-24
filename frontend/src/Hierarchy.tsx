import { useMemo, useState } from "react";
import { Background, Controls, ReactFlow, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { type Architecture, type Run, format, metric } from "./lib";

export default function Hierarchy({
  config,
  run,
}: {
  config: Architecture;
  run?: Run;
}) {
  const [selected, setSelected] = useState("cpu");
  const blocks = useMemo(
    () => [
      {
        id: "cpu",
        x: 170,
        y: 0,
        label: config.cpu_model,
        detail: `${config.clock_mhz} MHz · 1 core`,
        fields: {
          IPC: format(metric(run, "ipc")),
          Cycles: format(metric(run, "cycles")),
        },
      },
      {
        id: "l1i",
        x: 20,
        y: 135,
        label: "L1 instruction cache",
        detail: `${config.l1i_kib} KiB · ${config.l1_assoc} way`,
        fields: {
          Latency: `${config.l1_latency_cycles} cycles`,
          "Line size": `${config.line_bytes} B`,
        },
      },
      {
        id: "l1d",
        x: 320,
        y: 135,
        label: "L1 data cache",
        detail: `${config.l1d_kib} KiB · ${config.l1_assoc} way`,
        fields: {
          Latency: `${config.l1_latency_cycles} cycles`,
          "Line size": `${config.line_bytes} B`,
        },
      },
      {
        id: "l2",
        x: 170,
        y: 280,
        label: "Unified L2 cache",
        detail: `${config.l2_kib} KiB · ${config.l2_assoc} way`,
        fields: {
          Latency: `${config.l2_latency_cycles} cycles`,
          Replacement: "LRU",
        },
      },
      {
        id: "controller",
        x: 170,
        y: 420,
        label: "Memory controller",
        detail: "Timing memory requests",
        fields: {
          "Read burst latency": `${format(metric(run, "dram_read_burst_latency"))} ns`,
          Bandwidth: `${format(metric(run, "dram_bandwidth"), 0)} B/s`,
        },
      },
      {
        id: "dram",
        x: 170,
        y: 560,
        label: "DDR3-1600 · 8×8",
        detail: `${config.memory_mib} MiB address range`,
        fields: { Model: config.memory_model },
      },
    ],
    [config, run],
  );
  const nodes: Node[] = blocks.map((b) => ({
    id: b.id,
    position: { x: b.x, y: b.y },
    data: {
      label: (
        <div>
          <strong>{b.label}</strong>
          <small>{b.detail}</small>
          {["l1i", "l1d", "l2"].includes(b.id) && (
            <small>
              Miss rate{" "}
              {metric(run, b.id + "_miss_rate") === null
                ? "—"
                : format(metric(run, b.id + "_miss_rate")! * 100) + "%"}
            </small>
          )}
        </div>
      ),
    },
    style: {
      width: 235,
      background: "#111e30",
      color: "#d7e4f4",
      border: "1px solid #2e4865",
      borderRadius: 10,
      padding: 16,
    },
  }));
  const edges = [
    ["cpu", "l1i"],
    ["cpu", "l1d"],
    ["l1i", "l2"],
    ["l1d", "l2"],
    ["l2", "controller"],
    ["controller", "dram"],
  ].map(([source, target]) => ({
    id: source + target,
    source,
    target,
    style: { stroke: "#4e8fa4", strokeWidth: 2 },
  }));
  const block = blocks.find((b) => b.id === selected)!;
  return (
    <div className="hierarchy-grid">
      <div className="flow">
        <ReactFlow
          key={JSON.stringify(config)}
          nodes={nodes}
          edges={edges}
          fitView
          minZoom={0.3}
          maxZoom={1.5}
          onNodeClick={(_, node) => setSelected(node.id)}
        >
          <Background color="#23354b" gap={24} />
          <Controls />
        </ReactFlow>
      </div>
      <aside className="inspector">
        <p className="eyebrow">COMPONENT INSPECTOR</p>
        <h3>{block.label}</h3>
        <p>{block.detail}</p>
        {Object.entries(block.fields).map(([key, value]) => (
          <div className="kv" key={key}>
            <span>{key}</span>
            <b>{value}</b>
          </div>
        ))}
        {["l1i", "l1d", "l2"].includes(selected) &&
          [
            "accesses",
            "hits",
            "misses",
            "miss_rate",
            "avg_miss_latency_ns",
          ].map((key) => (
            <div className="kv" key={key}>
              <span>{key.replaceAll("_", " ")}</span>
              <b>{format(metric(run, selected + "_" + key))}</b>
            </div>
          ))}
        <p className="muted small">
          Aggregated final statistics. Connections describe the configured
          topology. No individual transaction trace is implied.
        </p>
      </aside>
    </div>
  );
}
