"""Idealized data-only addresses for sequential/traversal workloads, not gem5 tracing."""

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("benchmark", choices=["sequential", "traversal"])
parser.add_argument("--size", type=int, default=4096)
args = parser.parse_args()
if not 2 <= args.size <= 262144:
    parser.error("size must be 2..262144")
print(
    "# Idealized data-only virtual addresses; excludes initialization, stack, libc and page mapping"
)
indices = (
    range(args.size)
    if args.benchmark == "sequential"
    else (i for offset in range(64) for i in range(offset, args.size, 64))
)
for index in indices:
    print(hex(0x10000000 + index * 8))
