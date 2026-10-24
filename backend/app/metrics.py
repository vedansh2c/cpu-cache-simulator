"""Explicit schema for gem5 25.1.0.1, single CPU, whole-process SE statistics."""

import math

from app.settings import GEM5_VERSION

BEGIN = "---------- Begin Simulation Statistics ----------"
END = "---------- End Simulation Statistics   ----------"


def parse_stats(text: str) -> dict[str, float]:
    blocks = []
    current = None
    for line in text.splitlines():
        if line.strip() == BEGIN:
            current = {}
        elif line.strip() == END:
            if current is not None:
                blocks.append(current)
            current = None
        elif current is not None:
            fields = line.split("#", 1)[0].split()
            if len(fields) < 2:
                continue
            try:
                value = float(fields[1])
            except ValueError:
                continue
            if fields[0] in current:
                raise ValueError(f"Duplicate statistic: {fields[0]}")
            current[fields[0]] = value
    if current is not None or not blocks:
        raise ValueError("Missing or incomplete gem5 statistics block")
    # Never sum cumulative dumps, or merge counters across dump boundaries.
    return blocks[-1]


def extract_metrics(text: str, version: str) -> dict:
    if version != GEM5_VERSION:
        raise ValueError(f"Unsupported gem5 version {version}; expected {GEM5_VERSION}")
    stats = parse_stats(text)

    def get(key):
        value = stats.get(key)
        return value if value is not None and math.isfinite(value) and value >= 0 else None

    def metric(
        value,
        unit,
        source,
        reason="Required counter absent, invalid, or denominator zero in final dump",
    ):
        return {
            "value": value,
            "unit": unit,
            "source": source,
            "unavailable_reason": reason if value is None else None,
        }

    cycles = get("system.cpu.numCycles")
    instructions = get("system.cpu.numInsts")
    ipc = instructions / cycles if instructions is not None and cycles else None
    cpi = cycles / instructions if cycles is not None and instructions else None
    result = {
        "cycles": metric(cycles, "cycles", "system.cpu.numCycles"),
        "instructions": metric(instructions, "instructions", "system.cpu.numInsts"),
        "ipc": metric(ipc, "instructions/cycle", "system.cpu.numInsts / system.cpu.numCycles"),
        "cpi": metric(cpi, "cycles/instruction", "system.cpu.numCycles / system.cpu.numInsts"),
        "simulated_seconds": metric(get("simSeconds"), "s", "simSeconds"),
    }
    ticks = get("simFreq")
    for label, path in [
        ("l1i", "system.cpu.icache"),
        ("l1d", "system.cpu.dcache"),
        ("l2", "system.l2cache"),
    ]:
        for name in ("Accesses", "Hits", "Misses", "MissRate"):
            key = f"{path}.overall{name}::total"
            value = get(key)
            if name == "MissRate" and value is not None and value > 1:
                value = None
            suffix = {
                "Accesses": "accesses",
                "Hits": "hits",
                "Misses": "misses",
                "MissRate": "miss_rate",
            }[name]
            result[f"{label}_{suffix}"] = metric(
                value, "ratio" if name == "MissRate" else "count", key
            )
        latency_key = f"{path}.overallAvgMissLatency::total"
        latency = get(latency_key)
        result[f"{label}_avg_miss_latency_ns"] = metric(
            latency / ticks * 1e9 if latency is not None and ticks else None,
            "ns",
            f"{latency_key} / simFreq * 1e9",
        )
    latency_key = "system.mem_ctrl.dram.avgMemAccLat"
    latency = get(latency_key)
    result["dram_read_burst_latency"] = metric(
        latency / ticks * 1e9 if latency is not None and ticks else None,
        "ns",
        f"{latency_key} / simFreq * 1e9",
    )
    read_key = "system.mem_ctrl.dram.dramBytesRead"
    write_key = "system.mem_ctrl.dram.dramBytesWritten"
    read, written, seconds = get(read_key), get(write_key), get("simSeconds")
    bandwidth = (
        (read + written) / seconds
        if (read is not None and written is not None and seconds)
        else None
    )
    result["dram_bandwidth"] = metric(bandwidth, "B/s", f"({read_key} + {write_key}) / simSeconds")
    return {
        "gem5_version": version,
        "scope": "whole_process_including_runtime_and_validation",
        "statistics_dump": "final_complete",
        "values": result,
    }
