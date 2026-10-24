"""Compare a supplied data-address trace model against a real gem5 cache dump.

Always report scope mismatch; this tool does not assert equivalent traffic.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.metrics import extract_metrics  # noqa: E402
from app.settings import GEM5_VERSION  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
parser.add_argument("--trace", required=True)
parser.add_argument("--stats", required=True)
parser.add_argument("--capacity", required=True, type=int, help="Cache capacity in bytes")
parser.add_argument("--block", default=64, type=int)
parser.add_argument("--ways", default=2, type=int)
args = parser.parse_args()
model = json.loads(
    subprocess.check_output(
        [args.model, str(args.capacity), str(args.block), str(args.ways), args.trace], text=True
    )
)
metrics = extract_metrics(Path(args.stats).read_text(), GEM5_VERSION)["values"]
print(
    json.dumps(
        {
            "trace_model": model,
            "gem5_l1d": {
                key: metrics[f"l1d_{key}"] for key in ("accesses", "hits", "misses", "miss_rate")
            },
            "equivalent_scope": False,
            "interpretation": "Address-only trace versus whole-process physical-cache "
            "traffic: runtime, stack, page mapping, writes and timing can differ. "
            "A rate difference is diagnostic, not proof either model is incorrect.",
        },
        indent=2,
    )
)
