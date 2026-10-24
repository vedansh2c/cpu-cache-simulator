"""Analysis over completed measurements only; never infer missing counters."""


def compare(runs, max_cache_kib=None):
    if len({(r.benchmark, r.size) for r in runs}) != 1:
        raise ValueError("Compare identical benchmark and input size only")
    if any(r.status != "completed" or not r.metrics for r in runs):
        raise ValueError("All compared simulations must be completed")
    baseline = runs[0]
    rows = []
    for run in runs:
        differences = {}
        for key, metric in run.metrics["values"].items():
            value = metric["value"]
            base = baseline.metrics["values"].get(key, {}).get("value")
            difference = value - base if value is not None and base is not None else None
            differences[key] = {
                "value": value,
                "unit": metric["unit"],
                "absolute": difference,
                "percent": difference / base * 100 if difference is not None and base else None,
            }
        capacity = (
            run.architecture["l1i_kib"] + run.architecture["l1d_kib"] + run.architecture["l2_kib"]
        )
        rows.append(
            {
                "id": run.id,
                "architecture": run.architecture,
                "metrics": differences,
                "cache_capacity_kib": capacity,
                "feasible": max_cache_kib is None or capacity <= max_cache_kib,
            }
        )
    candidates = [r for r in rows if r["feasible"] and r["metrics"]["cycles"]["value"] is not None]
    frontier = [
        r["id"]
        for r in candidates
        if not any(
            other["cache_capacity_kib"] <= r["cache_capacity_kib"]
            and other["metrics"]["cycles"]["value"] <= r["metrics"]["cycles"]["value"]
            and (
                other["cache_capacity_kib"] < r["cache_capacity_kib"]
                or other["metrics"]["cycles"]["value"] < r["metrics"]["cycles"]["value"]
            )
            for other in candidates
        )
    ]
    return {
        "baseline_id": baseline.id,
        "benchmark": baseline.benchmark,
        "size": baseline.size,
        "rows": rows,
        "pareto_ids": frontier,
        "pareto_objectives": ["minimize total cache KiB", "minimize execution cycles"],
    }
