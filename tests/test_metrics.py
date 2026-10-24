import pytest
from app.metrics import BEGIN, END, extract_metrics, parse_stats
from app.settings import GEM5_VERSION


def test_units_and_derived_metrics(stats_text):
    metrics = extract_metrics(stats_text, GEM5_VERSION)["values"]
    assert metrics["ipc"]["value"] == 0.25
    assert metrics["cpi"]["value"] == 4
    assert metrics["dram_read_burst_latency"]["value"] == 50
    assert metrics["dram_bandwidth"]["value"] == 96_000_000
    assert metrics["simulated_seconds"]["value"] == 0.000002
    assert metrics["l1d_miss_rate"]["value"] == 0.2
    assert metrics["l1d_avg_miss_latency_ns"]["value"] == 1


def test_final_dump_only(stats_text):
    assert (
        parse_stats(stats_text + stats_text.replace("4000", "8000"))["system.cpu.numCycles"] == 8000
    )


@pytest.mark.parametrize(
    "text", ["", "simSeconds 1", f"{BEGIN}\nsimSeconds 1", f"{BEGIN}\na 1\na 2\n{END}"]
)
def test_malformed_stats_rejected(text):
    with pytest.raises(ValueError):
        parse_stats(text)


def test_truncated_final_dump_rejected(stats_text):
    with pytest.raises(ValueError):
        parse_stats(stats_text + BEGIN)


def test_unavailable_is_null_not_zero():
    values = extract_metrics(
        f"{BEGIN}\nsystem.cpu.numCycles 0\nsystem.cpu.numInsts nan\nsimSeconds inf\n{END}",
        GEM5_VERSION,
    )["values"]
    assert values["cycles"]["value"] == 0
    for key in ("ipc", "cpi", "simulated_seconds", "l1d_miss_rate", "dram_bandwidth"):
        assert values[key]["value"] is None
        assert values[key]["unavailable_reason"]


def test_unknown_version_rejected(stats_text):
    with pytest.raises(ValueError, match="Unsupported gem5 version"):
        extract_metrics(stats_text, "24.0")
