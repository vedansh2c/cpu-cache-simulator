"""Original single-core classic-cache SE configuration for gem5 25.1.0.1.

Executed by gem5's embedded Python, never by the API interpreter.
"""

import argparse
import json
from pathlib import Path

import m5
from m5.objects import (
    LRURP,
    X86O3CPU,
    AddrRange,
    Cache,
    DDR3_1600_8x8,
    L2XBar,
    MemCtrl,
    Process,
    Root,
    SEWorkload,
    SrcClockDomain,
    System,
    SystemXBar,
    VoltageDomain,
    X86TimingSimpleCPU,
)

parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True)
parser.add_argument("--binary", required=True)
parser.add_argument("--size", type=int, required=True)
parser.add_argument(
    "--benchmark",
    default="matrix",
    choices=["matrix", "sequential", "random", "traversal", "sorting", "pointer"],
)
parser.add_argument("--max-ticks", type=int, required=True)
args = parser.parse_args()
c = json.loads(Path(args.config).read_text())
if c["cpu_model"] not in ("TimingSimpleCPU", "O3CPU") or c["cores"] != 1:
    raise ValueError("Only one TimingSimpleCPU or O3CPU is supported")
if c["memory_model"] != "DDR3_1600_8x8" or c["memory_mib"] not in (128, 256, 512, 1024, 2048):
    raise ValueError("Unsupported memory configuration")

m5.ticks.setGlobalFrequency("1THz")
system = System()
system.clk_domain = SrcClockDomain(clock=f"{c['clock_mhz']}MHz", voltage_domain=VoltageDomain())
system.mem_mode = "timing"
system.mem_ranges = [AddrRange(f"{c['memory_mib']}MiB")]
system.cache_line_size = c["line_bytes"]
system.cpu = X86TimingSimpleCPU() if c["cpu_model"] == "TimingSimpleCPU" else X86O3CPU()


def cache(size_kib, assoc, latency, mshrs):
    return Cache(
        size=f"{size_kib}KiB",
        assoc=assoc,
        tag_latency=latency,
        data_latency=latency,
        response_latency=latency,
        mshrs=mshrs,
        tgts_per_mshr=20,
        replacement_policy=LRURP(),
    )


system.cpu.icache = cache(c["l1i_kib"], c["l1_assoc"], c["l1_latency_cycles"], 4)
system.cpu.dcache = cache(c["l1d_kib"], c["l1_assoc"], c["l1_latency_cycles"], 4)
system.cpu.icache.is_read_only = True
system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port
system.l2bus = L2XBar()
system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports
system.l2cache = cache(c["l2_kib"], c["l2_assoc"], c["l2_latency_cycles"], 20)
system.l2cache.cpu_side = system.l2bus.mem_side_ports
system.membus = SystemXBar()
system.l2cache.mem_side = system.membus.cpu_side_ports
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports
system.system_port = system.membus.cpu_side_ports
system.mem_ctrl = MemCtrl(dram=DDR3_1600_8x8())
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports
system.workload = SEWorkload.init_compatible(args.binary)
command = (
    [args.binary, str(args.size)]
    if args.benchmark == "matrix"
    else [args.binary, args.benchmark, str(args.size)]
)
process = Process(cmd=command, output="workload.stdout", errout="workload.stderr")
system.cpu.workload = process
system.cpu.createThreads()
root = Root(full_system=False, system=system)
m5.instantiate()
event = m5.simulate(args.max_ticks)
cause, code = event.getCause(), event.getCode()
Path(m5.options.outdir, "exit.json").write_text(
    json.dumps({"cause": cause, "code": code, "tick": int(m5.curTick())})
)
print(f"Simulation exit: {cause}; code={code}; tick={m5.curTick()}", flush=True)
if cause != "exiting with last active thread context" or code != 0:
    raise SystemExit(1)
